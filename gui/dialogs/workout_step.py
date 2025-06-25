#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog per la creazione e modifica di uno step di allenamento.
"""

import logging
import tkinter as tk
import re
from tkinter import ttk
from typing import Dict, Any, Optional, Callable

from config import get_config
from models.workout import WorkoutStep, Target
from models.zone import PaceZone, HeartRateZone, PowerZone
from gui.utils import (
    create_tooltip, show_error, validate_pace,
    validate_power, validate_hr, pace_to_seconds, seconds_to_pace
)


class WorkoutStepDialog(tk.Toplevel):
    """Dialog per la creazione e modifica di uno step di allenamento."""
    
    def __init__(self, parent, step: Optional[WorkoutStep] = None, 
               sport_type: str = "running", callback: Optional[Callable] = None):
        """
        Inizializza il dialog.
        
        Args:
            parent: Widget genitore
            step: Step da modificare (None per crearne uno nuovo)
            sport_type: Tipo di sport (running, cycling, swimming)
            callback: Funzione da chiamare alla conferma
        """
        super().__init__(parent)
        self.parent = parent
        self.step = step
        self.sport_type = sport_type
        self.callback = callback
        self.config = get_config()
        
        # Valori predefiniti se non c'è uno step
        if step:
            self.step_type = step.step_type
            self.description = step.description
            self.end_condition = step.end_condition
            self.end_condition_value = step.end_condition_value or ""
            self.target = step.target
        else:
            self.step_type = "interval"
            self.description = ""
            self.end_condition = "lap.button"
            self.end_condition_value = ""
            self.target = Target()
        
        # Variabili
        self.step_type_var = tk.StringVar(value=self.step_type)
        self.description_var = tk.StringVar(value=self.description)
        self.end_condition_var = tk.StringVar(value=self.end_condition)
        
        # Conversione del tempo da secondi a formato mm:ss per l'interfaccia
        if isinstance(self.end_condition_value, (int, float)) and self.end_condition == "time":
            # Converti secondi a mm:ss
            seconds = int(self.end_condition_value)
            minutes = seconds // 60
            seconds = seconds % 60
            self.end_condition_value = f"{minutes}:{seconds:02d}"
        
        self.end_condition_value_var = tk.StringVar(value=self.end_condition_value)
        self.target_type_var = tk.StringVar(value=self.target.target)
        
        # Variabile per selezionare una zona predefinita
        self.predefined_zone_var = tk.StringVar()
        
        # Variabili per i valori target
        self.target_min_var = tk.StringVar()
        self.target_max_var = tk.StringVar()
        self.target_zone_var = tk.StringVar()
        
        # NUOVA: Variabile per passo singolo
        self.single_pace_var = tk.BooleanVar(value=False)
        
        # Flag per evitare loop di aggiornamenti
        self.updating_values = False
        
        # Imposta i valori target
        if self.target.from_value is not None:
            if self.target.target == "pace.zone":
                # Converti da m/s a min/km
                from_pace_secs = int(1000 / self.target.from_value)
                from_pace = f"{from_pace_secs // 60}:{from_pace_secs % 60:02d}"
                self.target_min_var.set(from_pace)
            else:
                self.target_min_var.set(str(self.target.from_value))
        
        if self.target.to_value is not None:
            if self.target.target == "pace.zone":
                # Converti da m/s a min/km
                to_pace_secs = int(1000 / self.target.to_value)
                to_pace = f"{to_pace_secs // 60}:{to_pace_secs % 60:02d}"
                self.target_max_var.set(to_pace)
            else:
                self.target_max_var.set(str(self.target.to_value))
        
        # NUOVO: Controlla se è un passo singolo (valori uguali)
        if (self.target.from_value is not None and self.target.to_value is not None and
            self.target.from_value == self.target.to_value and self.target.target == "pace.zone"):
            self.single_pace_var.set(True)
        
        if self.target.zone is not None:
            self.target_zone_var.set(str(self.target.zone))
        
        # Configura il dialog
        self.title("Step di allenamento")
        self.geometry("500x650")
        self.transient(parent)
        self.grab_set()
        
        # Crea i widget
        self.create_widgets()
        
        # Centra il dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Aggiungi i callback
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # Aggiorna l'interfaccia in base alle selezioni
        self.on_step_type_change()
        self.on_end_condition_change()
        self.on_target_type_change()
        
        # Carica le zone predefinite e imposta la zona corretta
        # Nota: mettiamo un breve ritardo per assicurarci che tutti i widget siano pronti
        self.after(100, self.initialize_zones)
        
        # Aggiungi listener per modifiche manuali ai valori
        self.target_min_var.trace('w', self.on_target_value_changed)
        self.target_max_var.trace('w', self.on_target_value_changed)
    
    def on_target_value_changed(self, *args):
        """Gestisce le modifiche manuali ai valori target."""
        if self.updating_values:
            return
            
        # Se l'utente sta modificando manualmente i valori, verifica se corrispondono ancora a una zona
        self.check_zone_match()
    
    def check_zone_match(self):
        """Verifica se i valori attuali corrispondono a una zona predefinita."""
        if self.updating_values:
            return
            
        target_type = self.target_type_var.get()
        if target_type != "pace.zone":
            return
            
        min_value = self.target_min_var.get()
        max_value = self.target_max_var.get()
        
        if not min_value or not max_value:
            return
        
        # Ottieni le zone di passo
        paces = self.config.get(f'sports.{self.sport_type}.paces', {})
        
        # Verifica se corrisponde a una zona esistente
        found_zone = None
        for zone_name, pace_range in paces.items():
            if '-' in pace_range:
                zone_min, zone_max = pace_range.split('-')
                zone_min = zone_min.strip()
                zone_max = zone_max.strip()
                
                if zone_min == min_value and zone_max == max_value:
                    found_zone = zone_name
                    break
            else:
                # Zona a valore singolo
                if pace_range.strip() == min_value and min_value == max_value:
                    found_zone = zone_name
                    break
        
        # Aggiorna la selezione della zona
        self.updating_values = True
        if found_zone:
            self.predefined_zone_var.set(found_zone)
        else:
            # Nessuna zona corrisponde, rimuovi la selezione
            self.predefined_zone_var.set("")
        self.updating_values = False
    
    def create_widgets(self):
        """Crea i widget del dialog."""
        # Frame principale con padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Intestazione
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text=f"Step di allenamento", 
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        # Frame per il tipo di step
        step_type_frame = ttk.LabelFrame(main_frame, text="Tipo di step")
        step_type_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tipi di step
        step_types = [
            ("Riscaldamento", "warmup"),
            ("Defaticamento", "cooldown"),
            ("Intervallo", "interval"),
            ("Recupero", "recovery"),
            ("Riposo", "rest"),
            ("Altro", "other"),
        ]
        
        # Crea i radiobutton per i tipi di step
        step_type_grid = ttk.Frame(step_type_frame)
        step_type_grid.pack(fill=tk.X, padx=10, pady=10)
        
        for i, (label, value) in enumerate(step_types):
            row = i // 3
            col = i % 3
            
            rb = ttk.Radiobutton(step_type_grid, text=label, value=value, 
                               variable=self.step_type_var, 
                               command=self.on_step_type_change)
            rb.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
        
        # Frame per la descrizione
        description_frame = ttk.LabelFrame(main_frame, text="Descrizione")
        description_frame.pack(fill=tk.X, pady=(0, 10))
        
        description_entry = ttk.Entry(description_frame, textvariable=self.description_var, 
                                   width=50)
        description_entry.pack(fill=tk.X, padx=10, pady=10)
        create_tooltip(description_entry, "Inserisci una descrizione opzionale per questo step")
        
        # Frame per la condizione di fine
        end_condition_frame = ttk.LabelFrame(main_frame, text="Condizione di fine")
        end_condition_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tipi di condizione di fine
        end_conditions = [
            ("Pulsante lap", "lap.button"),
            ("Tempo", "time"),
            ("Distanza", "distance"),
        ]
        
        # Frame per i radiobutton
        end_condition_grid = ttk.Frame(end_condition_frame)
        end_condition_grid.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        for i, (label, value) in enumerate(end_conditions):
            rb = ttk.Radiobutton(end_condition_grid, text=label, value=value, 
                               variable=self.end_condition_var, 
                               command=self.on_end_condition_change)
            rb.grid(row=0, column=i, sticky=tk.W, padx=5)
        
        # Frame per il valore della condizione
        self.end_condition_value_frame = ttk.Frame(end_condition_frame)
        self.end_condition_value_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Label(self.end_condition_value_frame, text="Valore:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.end_value_entry = ttk.Entry(self.end_condition_value_frame, 
                                       textvariable=self.end_condition_value_var, 
                                       width=15)
        self.end_value_entry.pack(side=tk.LEFT)
        
        self.end_value_label = ttk.Label(self.end_condition_value_frame, text="")
        self.end_value_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Frame per il target
        target_frame = ttk.LabelFrame(main_frame, text="Target")
        target_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tipi di target
        target_types = [
            ("Nessun target", "no.target"),
            ("Zona di passo", "pace.zone"),
            ("Zona di frequenza cardiaca", "heart.rate.zone"),
        ]
        
        # Se il tipo di sport è ciclismo, aggiungi la zona di potenza
        if self.sport_type == "cycling":
            target_types.append(("Zona di potenza", "power.zone"))
        
        # Crea i radiobutton per i tipi di target
        target_type_grid = ttk.Frame(target_frame)
        target_type_grid.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        for i, (label, value) in enumerate(target_types):
            rb = ttk.Radiobutton(target_type_grid, text=label, value=value, 
                               variable=self.target_type_var, 
                               command=self.on_target_type_change)
            rb.grid(row=i // 2, column=i % 2, sticky=tk.W, padx=5, pady=2)
        
        # Frame per i valori del target
        self.target_value_frame = ttk.Frame(target_frame)
        self.target_value_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Frame per la selezione di una zona predefinita
        self.predefined_zone_frame = ttk.Frame(self.target_value_frame)
        self.predefined_zone_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.predefined_zone_frame, text="Zona predefinita:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.zone_combo = ttk.Combobox(self.predefined_zone_frame, 
                                     textvariable=self.predefined_zone_var, 
                                     width=20, state="readonly")
        self.zone_combo.pack(side=tk.LEFT)
        
        # Nota per valori personalizzati
        self.custom_note = ttk.Label(self.predefined_zone_frame, 
                                   text="(lascia vuoto per passo personalizzato)", 
                                   font=('TkDefaultFont', 9, 'italic'))
        self.custom_note.pack(side=tk.LEFT, padx=(10, 0))
        
        # Associa evento di selezione della zona
        self.zone_combo.bind("<<ComboboxSelected>>", self.on_predefined_zone_selected)
        
        # Frame per i valori min/max
        self.target_minmax_frame = ttk.Frame(self.target_value_frame)
        self.target_minmax_frame.pack(fill=tk.X, pady=(0, 10))
        
        # NUOVO: Checkbox per passo singolo (solo per zone di passo)
        self.single_pace_check = ttk.Checkbutton(
            self.target_minmax_frame,
            text="Usa passo singolo",
            variable=self.single_pace_var,
            command=self.on_single_pace_changed
        )
        self.single_pace_check.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        self.min_label = ttk.Label(self.target_minmax_frame, text="Min:")
        self.min_label.grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        
        self.target_min_entry = ttk.Entry(self.target_minmax_frame, 
                                       textvariable=self.target_min_var, 
                                       width=10)
        self.target_min_entry.grid(row=1, column=1, sticky=tk.W)
        
        self.target_min_label = ttk.Label(self.target_minmax_frame, text="")
        self.target_min_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
        
        self.max_label = ttk.Label(self.target_minmax_frame, text="Max:")
        self.max_label.grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        
        self.target_max_entry = ttk.Entry(self.target_minmax_frame, 
                                       textvariable=self.target_max_var, 
                                       width=10)
        self.target_max_entry.grid(row=2, column=1, sticky=tk.W)
        
        self.target_max_label = ttk.Label(self.target_minmax_frame, text="")
        self.target_max_label.grid(row=2, column=2, sticky=tk.W, padx=(5, 0))
        
        # Pulsanti
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="Annulla", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        
        # NUOVO: Aggiorna lo stato iniziale del checkbox passo singolo
        self.on_single_pace_changed()
    
    def on_single_pace_changed(self):
        """Gestisce il cambio del checkbox passo singolo."""
        if self.single_pace_var.get():
            # Se è selezionato passo singolo, copia il valore min nel max e disabilita il campo max
            if self.target_min_var.get():
                self.target_max_var.set(self.target_min_var.get())
            self.target_max_entry.config(state="disabled")
            
            # Cambia l'etichetta di Min in "Passo:"
            self.min_label.config(text="Passo:")
            # Nascondi la riga del Max
            self.max_label.grid_remove()
            self.target_max_entry.grid_remove()
            self.target_max_label.grid_remove()
        else:
            # Se non è selezionato, abilita il campo max
            self.target_max_entry.config(state="normal")
            
            # Ripristina l'etichetta di Min
            self.min_label.config(text="Min:")
            # Mostra la riga del Max
            self.max_label.grid()
            self.target_max_entry.grid()
            self.target_max_label.grid()
    
    def initialize_zones(self):
        """Inizializza le zone e imposta la zona corretta."""
        # Carichiamo prima le zone disponibili
        self.load_predefined_zones()
        
        # Verifichiamo di nuovo che la zona sia impostata correttamente
        if hasattr(self.target, 'target_zone_name') and self.target.target_zone_name:
            # Verifica se la zona salvata corrisponde ancora ai valori attuali
            self.check_zone_match()
            
            # Se dopo il check c'è ancora una zona, selezionala
            if self.predefined_zone_var.get():
                # La zona è valida
                pass
            else:
                # La zona non corrisponde più ai valori, non selezionare nulla
                self.predefined_zone_var.set("")
    
    def load_predefined_zones(self):
        """Carica le zone predefinite dalla configurazione."""
        # Pulisci la lista attuale
        self.zone_combo['values'] = []
        
        target_type = self.target_type_var.get()
        
        if target_type == "no.target":
            self.predefined_zone_frame.pack_forget()
            return
        else:
            self.predefined_zone_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Ottieni le zone appropriate in base al tipo di target e sport
        zones = []
        
        if target_type == "pace.zone":
            # Ottieni le zone di passo per lo sport corrente
            paces = self.config.get(f'sports.{self.sport_type}.paces', {})
            zones = [(name, value) for name, value in paces.items()]
            
        elif target_type == "heart.rate.zone":
            # Ottieni le zone di frequenza cardiaca
            heart_rates = self.config.get('heart_rates', {})
            zones = [(name, value) for name, value in heart_rates.items() 
                   if name.endswith('_HR')]
            
        elif target_type == "power.zone" and self.sport_type == "cycling":
            # Ottieni le zone di potenza per il ciclismo
            power_values = self.config.get('sports.cycling.power_values', {})
            zones = [(name, value) for name, value in power_values.items()]
        
        # Aggiorna la combo
        if zones:
            zone_names = [name for name, _ in zones]
            # Aggiungi opzione vuota all'inizio per passo personalizzato
            zone_names_with_empty = [""] + zone_names
            self.zone_combo['values'] = zone_names_with_empty
            
            # Verifica i valori attuali e seleziona la zona corrispondente
            self.check_zone_match()

    def on_predefined_zone_selected(self, event=None):
        """Gestisce la selezione di una zona predefinita."""
        zone_name = self.predefined_zone_var.get()
        
        # Se è stata selezionata l'opzione vuota, non fare nulla
        if not zone_name:
            return
        
        target_type = self.target_type_var.get()
        
        # Imposta il flag per evitare trigger del check_zone_match
        self.updating_values = True
        
        if target_type == "pace.zone":
            # Ottieni i valori della zona di passo
            paces = self.config.get(f'sports.{self.sport_type}.paces', {})
            if zone_name in paces:
                pace_range = paces[zone_name]
                if '-' in pace_range:
                    min_pace, max_pace = pace_range.split('-')
                    self.target_min_var.set(min_pace.strip())
                    self.target_max_var.set(max_pace.strip())
                    self.single_pace_var.set(False)
                else:
                    # Se è un valore singolo, usa lo stesso per min e max
                    self.target_min_var.set(pace_range.strip())
                    self.target_max_var.set(pace_range.strip())
                    self.single_pace_var.set(True)
                
                self.on_single_pace_changed()
                
        elif target_type == "heart.rate.zone":
            # Ottieni i valori HR dalla configurazione
            heart_rates = self.config.get('heart_rates', {})
            max_hr = heart_rates.get('max_hr', 180)
            
            if zone_name in heart_rates:
                hr_range = heart_rates[zone_name]
                
                if '-' in hr_range and 'max_hr' in hr_range:
                    # Formato: 62-76% max_hr
                    parts = hr_range.split('-')
                    min_percent = float(parts[0])
                    max_percent = float(parts[1].split('%')[0])
                    
                    # Converti in valori assoluti
                    min_hr = int(min_percent * max_hr / 100)
                    max_hr = int(max_percent * max_hr / 100)
                    
                    self.target_min_var.set(str(min_hr))
                    self.target_max_var.set(str(max_hr))
                    
        elif target_type == "power.zone" and self.sport_type == "cycling":
            # Ottieni i valori di potenza
            power_values = self.config.get('sports.cycling.power_values', {})
            
            if zone_name in power_values:
                power_range = power_values[zone_name]
                
                if '-' in power_range:
                    # Range di potenza
                    min_power, max_power = power_range.split('-')
                    self.target_min_var.set(min_power.strip())
                    self.target_max_var.set(max_power.strip())
                elif power_range.startswith('<'):
                    # Sotto una certa potenza
                    max_power = power_range[1:].strip()
                    self.target_min_var.set("0")
                    self.target_max_var.set(max_power)
                elif power_range.endswith('+'):
                    # Sopra una certa potenza
                    min_power = power_range[:-1].strip()
                    self.target_min_var.set(min_power)
                    self.target_max_var.set("9999")
                else:
                    # Valore singolo
                    self.target_min_var.set(power_range.strip())
                    self.target_max_var.set(power_range.strip())
        
        # Rimuovi il flag
        self.updating_values = False
    
    def on_step_type_change(self):
        """Gestisce il cambio di tipo di step."""
        # Per ora non fa nulla, ma può essere esteso in futuro
        pass
    
    def on_end_condition_change(self):
        """Gestisce il cambio di condizione di fine."""
        end_condition = self.end_condition_var.get()
        
        if end_condition == "lap.button":
            # Nascondi il frame del valore
            self.end_condition_value_frame.pack_forget()
        else:
            # Mostra il frame del valore
            self.end_condition_value_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # Aggiorna l'etichetta
            if end_condition == "time":
                self.end_value_label.config(text="(mm:ss)")
                create_tooltip(self.end_value_entry, "Inserisci il tempo nel formato mm:ss (es. 5:30)")
            elif end_condition == "distance":
                self.end_value_label.config(text="(es. 1000m o 5km)")
                create_tooltip(self.end_value_entry, "Inserisci la distanza in metri (es. 1000m) o chilometri (es. 5km)")
            elif end_condition == "iterations":
                self.end_value_label.config(text="ripetizioni")
                create_tooltip(self.end_value_entry, "Inserisci il numero di ripetizioni")
    
    def on_target_type_change(self):
        """Gestisce il cambio di tipo di target."""
        target_type = self.target_type_var.get()
        
        # Nascondi tutti i frame
        self.predefined_zone_frame.pack_forget()
        self.target_minmax_frame.pack_forget()
        
        # Mostra/nascondi il checkbox passo singolo
        if target_type == "pace.zone":
            self.single_pace_check.grid()
        else:
            self.single_pace_check.grid_remove()
            self.single_pace_var.set(False)
            self.on_single_pace_changed()
        
        # Mostra il frame appropriato
        if target_type == "no.target":
            pass
        elif target_type in ["pace.zone", "heart.rate.zone", "power.zone"]:
            # Prima la selezione zona, poi i valori min/max
            self.predefined_zone_frame.pack(fill=tk.X, pady=(0, 10))
            self.target_minmax_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Aggiorna le etichette
            if target_type == "pace.zone":
                self.target_min_label.config(text="min/km")
                self.target_max_label.config(text="min/km")
                create_tooltip(self.target_min_entry, "Inserisci il passo minimo nel formato mm:ss (es. 4:30)")
                create_tooltip(self.target_max_entry, "Inserisci il passo massimo nel formato mm:ss (es. 5:00)")
            elif target_type == "heart.rate.zone":
                self.target_min_label.config(text="bpm")
                self.target_max_label.config(text="bpm")
                create_tooltip(self.target_min_entry, "Inserisci la frequenza cardiaca minima in bpm")
                create_tooltip(self.target_max_entry, "Inserisci la frequenza cardiaca massima in bpm")
            elif target_type == "power.zone":
                self.target_min_label.config(text="watt")
                self.target_max_label.config(text="watt")
                create_tooltip(self.target_min_entry, "Inserisci la potenza minima in watt")
                create_tooltip(self.target_max_entry, "Inserisci la potenza massima in watt")
                
            # Carica le zone predefinite
            self.load_predefined_zones()
    
    def validate(self) -> bool:
        """
        Valida i dati inseriti.
        
        Returns:
            True se i dati sono validi, False altrimenti
        """
        # Verifica la condizione di fine
        end_condition = self.end_condition_var.get()
        
        if end_condition != "lap.button":
            value = self.end_condition_value_var.get()
            
            if not value:
                show_error("Errore", "Inserisci un valore per la condizione di fine", parent=self)
                return False
            
            if end_condition == "time":
                # Verifica formato mm:ss
                if ':' not in value:
                    show_error("Errore", "Il tempo deve essere nel formato mm:ss (es. 5:30)", parent=self)
                    return False
                
                try:
                    minutes, seconds = map(int, value.split(':'))
                    if seconds >= 60:
                        show_error("Errore", "I secondi devono essere inferiori a 60", parent=self)
                        return False
                except ValueError:
                    show_error("Errore", "Il tempo deve essere nel formato mm:ss (es. 5:30)", parent=self)
                    return False
                    
            elif end_condition == "distance":
                # Verifica formato distanza (numero seguito da m o km)
                pattern = r'^(\d+(?:\.\d+)?)\s*(m|km)$'
                match = re.match(pattern, value.lower())
                
                if not match:
                    show_error("Errore", "La distanza deve essere nel formato '1000m' o '5km'", parent=self)
                    return False
                    
            elif end_condition == "iterations":
                # Verifica che sia un numero intero
                try:
                    int(value)
                except ValueError:
                    show_error("Errore", "Le ripetizioni devono essere un numero intero", parent=self)
                    return False
        
        # Verifica il target
        target_type = self.target_type_var.get()
        
        if target_type != "no.target":
            if target_type in ["pace.zone", "heart.rate.zone", "power.zone"]:
                min_value = self.target_min_var.get()
                max_value = self.target_max_var.get()
                
                # MODIFICATO: Se è passo singolo, usa solo min_value
                if self.single_pace_var.get() and target_type == "pace.zone":
                    if not min_value:
                        show_error("Errore", "Inserisci il valore del passo", parent=self)
                        return False
                    
                    if not validate_pace(min_value):
                        show_error("Errore", "Il passo deve essere nel formato mm:ss (es. 6:30)", parent=self)
                        return False
                else:
                    # Validazione normale per range
                    if not min_value or not max_value:
                        show_error("Errore", "Inserisci entrambi i valori minimo e massimo", parent=self)
                        return False
                    
                    # Verifica il formato in base al tipo
                    if target_type == "pace.zone":
                        # Verifica che siano nel formato mm:ss
                        if not validate_pace(min_value):
                            show_error("Errore", "Il passo minimo deve essere nel formato mm:ss (es. 4:30)", parent=self)
                            return False
                        
                        if not validate_pace(max_value):
                            show_error("Errore", "Il passo massimo deve essere nel formato mm:ss (es. 5:00)", parent=self)
                            return False
                    
                    elif target_type == "heart.rate.zone":
                        # Verifica che siano numeri interi
                        if not validate_hr(min_value):
                            show_error("Errore", "La frequenza cardiaca minima deve essere un numero intero", parent=self)
                            return False
                        
                        if not validate_hr(max_value):
                            show_error("Errore", "La frequenza cardiaca massima deve essere un numero intero", parent=self)
                            return False
                    
                    elif target_type == "power.zone":
                        # Verifica che siano numeri interi
                        if not validate_power(min_value):
                            show_error("Errore", "La potenza minima deve essere un numero intero", parent=self)
                            return False
                        
                        if not validate_power(max_value):
                            show_error("Errore", "La potenza massima deve essere un numero intero", parent=self)
                            return False
        
        return True
    
    def on_ok(self):
        """Gestisce il click sul pulsante OK."""
        # Valida i dati
        if not self.validate():
            return
        
        # Ottieni i valori
        step_type = self.step_type_var.get()
        description = self.description_var.get()
        end_condition = self.end_condition_var.get()
        end_condition_value = self.end_condition_value_var.get() if end_condition != "lap.button" else None
        
        # Converti il tempo da mm:ss a secondi
        if end_condition == "time" and end_condition_value and ":" in end_condition_value:
            try:
                minutes, seconds = map(int, end_condition_value.split(":"))
                end_condition_value = minutes * 60 + seconds
            except (ValueError, TypeError):
                # Fallback se il formato non è valido
                pass
        
        # Crea il target
        target_type = self.target_type_var.get()
        target = None

        if target_type != "no.target":
            if target_type in ["pace.zone", "heart.rate.zone", "power.zone"]:
                min_value = self.target_min_var.get()
                
                # MODIFICATO: Gestione passo singolo
                if self.single_pace_var.get() and target_type == "pace.zone":
                    max_value = min_value  # Usa lo stesso valore per min e max
                else:
                    max_value = self.target_max_var.get()
                
                # Converti i valori
                if target_type == "pace.zone":
                    # Converti da min/km a m/s
                    min_secs = pace_to_seconds(min_value)
                    max_secs = pace_to_seconds(max_value)
                    
                    from_value = 1000 / max_secs  # Passo più veloce
                    to_value = 1000 / min_secs    # Passo più lento
                else:
                    # Per gli altri target usa i valori direttamente
                    try:
                        from_value = float(min_value)
                        to_value = float(max_value)
                    except ValueError:
                        # Fallback a valori predefiniti
                        from_value = 0
                        to_value = 0
                
                target = Target(target_type, to_value, from_value)
                
                # IMPORTANTE: Imposta il nome della zona SOLO se è stata selezionata una zona predefinita
                # e i valori corrispondono ancora
                zone_name = self.predefined_zone_var.get()
                if zone_name:
                    # Verifica che i valori corrispondano ancora alla zona selezionata
                    if target_type == "pace.zone":
                        paces = self.config.get(f'sports.{self.sport_type}.paces', {})
                        if zone_name in paces:
                            pace_range = paces[zone_name]
                            if '-' in pace_range:
                                zone_min, zone_max = pace_range.split('-')
                                if zone_min.strip() == min_value and zone_max.strip() == max_value:
                                    target.target_zone_name = zone_name
                            else:
                                # Valore singolo
                                if pace_range.strip() == min_value and min_value == max_value:
                                    target.target_zone_name = zone_name
                # Se non c'è zona selezionata o i valori non corrispondono, target_zone_name rimane None
                    
            elif target_type == "zone":
                # Usa la zona predefinita
                zone = int(self.target_zone_var.get()) if self.target_zone_var.get() else None
                target = Target(target_type, zone=zone)

        # Se non è stato creato un target, usa il valore predefinito
        if not target:
            target = Target()
        
        # Aggiorna o crea lo step
        if self.step:
            # Aggiorna lo step esistente
            self.step.step_type = step_type
            self.step.description = description
            self.step.end_condition = end_condition
            self.step.end_condition_value = end_condition_value
            self.step.target = target
        else:
            # Crea un nuovo step
            self.step = WorkoutStep(
                order=0,
                step_type=step_type,
                description=description,
                end_condition=end_condition,
                end_condition_value=end_condition_value,
                target=target
            )
        
        # Chiama il callback
        if self.callback:
            self.callback(self.step)
        
        # Chiudi il dialog
        self.destroy()
    
    def on_cancel(self):
        """Gestisce il click sul pulsante Annulla."""
        # Chiudi il dialog senza fare nulla
        self.destroy()


import re  # Importazione necessaria per la validazione della distanza

if __name__ == "__main__":
    # Test del dialog
    root = tk.Tk()
    root.withdraw()
    
    # Crea un dialog con uno step nuovo
    dialog = WorkoutStepDialog(root)
    
    # Avvia il loop
    root.mainloop()