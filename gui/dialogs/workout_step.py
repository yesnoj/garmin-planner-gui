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
        self.end_condition_value_var = tk.StringVar(value=self.end_condition_value)
        self.target_type_var = tk.StringVar(value=self.target.target)
        
        # Variabile per selezionare una zona predefinita
        self.predefined_zone_var = tk.StringVar()
        
        # Variabili per i valori target
        self.target_min_var = tk.StringVar()
        self.target_max_var = tk.StringVar()
        self.target_zone_var = tk.StringVar()
        
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
        
        if self.target.zone is not None:
            self.target_zone_var.set(str(self.target.zone))
        
        # Configura il dialog
        self.title("Step di allenamento")
        self.geometry("500x550")
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

        # Carica le zone predefinite
        self.load_predefined_zones()
    

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
        
        # Frame per la condizione di fine
        end_condition_frame = ttk.LabelFrame(main_frame, text="Condizione di fine")
        end_condition_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tipi di condizione di fine
        end_conditions = [
            ("Pulsante lap", "lap.button"),
            ("Tempo", "time"),
            ("Distanza", "distance"),
        ]
        
        # Crea i radiobutton per le condizioni di fine
        end_condition_grid = ttk.Frame(end_condition_frame)
        end_condition_grid.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        for i, (label, value) in enumerate(end_conditions):
            rb = ttk.Radiobutton(end_condition_grid, text=label, value=value, 
                               variable=self.end_condition_var, 
                               command=self.on_end_condition_change)
            rb.grid(row=0, column=i, sticky=tk.W, padx=5)
        
        # Frame per il valore della condizione di fine
        self.end_value_frame = ttk.Frame(end_condition_frame)
        self.end_value_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        input_frame = ttk.Frame(self.end_value_frame)
        input_frame.pack(fill=tk.X)

        ttk.Label(input_frame, text="Valore:").pack(side=tk.LEFT, padx=(0, 5))
        self.end_value_entry = ttk.Entry(input_frame, textvariable=self.end_condition_value_var, width=15)
        self.end_value_entry.pack(side=tk.LEFT)
        self.end_value_label = ttk.Label(input_frame, text="")
        self.end_value_label.pack(side=tk.LEFT, padx=(5, 0)) 

        # Frame per il target
        target_frame = ttk.LabelFrame(main_frame, text="Target")
        target_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
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
        
        # Associa evento di selezione della zona
        self.zone_combo.bind("<<ComboboxSelected>>", self.on_predefined_zone_selected)
        
        # Frame per i valori min/max
        self.target_minmax_frame = ttk.Frame(self.target_value_frame)
        self.target_minmax_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(self.target_minmax_frame, text="Min:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.target_min_entry = ttk.Entry(self.target_minmax_frame, 
                                       textvariable=self.target_min_var, 
                                       width=10)
        self.target_min_entry.grid(row=0, column=1, sticky=tk.W)
        
        self.target_min_label = ttk.Label(self.target_minmax_frame, text="")
        self.target_min_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(self.target_minmax_frame, text="Max:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        
        self.target_max_entry = ttk.Entry(self.target_minmax_frame, 
                                       textvariable=self.target_max_var, 
                                       width=10)
        self.target_max_entry.grid(row=1, column=1, sticky=tk.W)
        
        self.target_max_label = ttk.Label(self.target_minmax_frame, text="")
        self.target_max_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
        
        # Pulsanti
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="Annulla", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
    
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
            self.zone_combo['values'] = zone_names
            
            # Seleziona il primo elemento
            if zone_names:
                self.zone_combo.current(0)
                # Aggiorna i valori min/max
                self.on_predefined_zone_selected()
                
    def on_predefined_zone_selected(self, event=None):
        """Handles selection of a predefined zone."""
        zone_name = self.predefined_zone_var.get()
        
        if not zone_name:
            return
                
        target_type = self.target_type_var.get()
        
        # Get the values of the selected zone
        if target_type == "pace.zone":
            # Get the pace zone
            pace_range = self.config.get(f'sports.{self.sport_type}.paces.{zone_name}', '')
            
            if '-' in pace_range:
                # Format mm:ss-mm:ss
                min_pace, max_pace = pace_range.split('-')
            else:
                # Single value format mm:ss - APPLY MARGINS
                min_pace = max_pace = pace_range
                
                # Apply margins for single value
                faster_margin = self.config.get(f'sports.{self.sport_type}.margins.faster', '0:05')
                slower_margin = self.config.get(f'sports.{self.sport_type}.margins.slower', '0:05')
                
                # Calculate new min and max with margins
                min_pace_secs = pace_to_seconds(min_pace)
                faster_secs = pace_to_seconds(faster_margin)
                slower_secs = pace_to_seconds(slower_margin)
                
                min_pace_with_margin = min_pace_secs - faster_secs  # Faster = lower time value
                max_pace_with_margin = min_pace_secs + slower_secs  # Slower = higher time value
                
                # Convert back to mm:ss format
                min_pace = seconds_to_pace(min_pace_with_margin)
                max_pace = seconds_to_pace(max_pace_with_margin)
            
            self.target_min_var.set(min_pace)
            self.target_max_var.set(max_pace)
                    
        elif target_type == "heart.rate.zone":
            # Get the heart rate zone
            hr_range = self.config.get(f'heart_rates.{zone_name}', '')
            
            # Extract numeric values (can be in format NN-NN% max_hr)
            if '-' in hr_range:
                # Format N-N or N-N% max_hr
                if 'max_hr' in hr_range:
                    # Format N-N% max_hr
                    parts = hr_range.split('-')
                    min_hr = parts[0].strip()
                    max_hr = parts[1].split('%')[0].strip()
                    
                    # Convert to absolute values using max_hr
                    max_hr_value = self.config.get('heart_rates.max_hr', 180)
                    min_hr_value = int(float(min_hr) * max_hr_value / 100)
                    max_hr_value = int(float(max_hr) * max_hr_value / 100)
                else:
                    # Format N-N
                    min_hr, max_hr = hr_range.split('-')
                    min_hr_value = int(min_hr)
                    max_hr_value = int(max_hr)
            else:
                # Single value format N or N% max_hr - APPLY MARGINS
                if 'max_hr' in hr_range:
                    # Format N% max_hr
                    hr = hr_range.split('%')[0].strip()
                    max_hr_value = self.config.get('heart_rates.max_hr', 180)
                    hr_value = int(float(hr) * max_hr_value / 100)
                else:
                    # Format N
                    hr_value = int(hr_range)
                
                # Apply margins for single value
                hr_up_margin = self.config.get('hr_margins.hr_up', 5)
                hr_down_margin = self.config.get('hr_margins.hr_down', 5)
                    
                min_hr_value = hr_value - hr_down_margin
                max_hr_value = hr_value + hr_up_margin
            
            self.target_min_var.set(str(min_hr_value))
            self.target_max_var.set(str(max_hr_value))
                    
        elif target_type == "power.zone" and self.sport_type == "cycling":
            # Get the power zone
            power_range = self.config.get(f'sports.cycling.power_values.{zone_name}', '')
            
            if '-' in power_range:
                # Format N-N
                min_power, max_power = power_range.split('-')
                min_power_value = int(min_power)
                max_power_value = int(max_power)
            elif power_range.startswith('<'):
                # Format <N
                power = power_range[1:]
                min_power_value = 0
                max_power_value = int(power)
            elif power_range.endswith('+'):
                # Format N+
                power = power_range[:-1]
                min_power_value = int(power)
                max_power_value = 999
            else:
                # Single value format N - APPLY MARGINS
                power_value = int(power_range)
                
                # Apply margins for single value
                power_up_margin = self.config.get('sports.cycling.margins.power_up', 10)
                power_down_margin = self.config.get('sports.cycling.margins.power_down', 10)
                
                min_power_value = power_value - power_down_margin
                max_power_value = power_value + power_up_margin
            
            self.target_min_var.set(str(min_power_value))
            self.target_max_var.set(str(max_power_value))
    
    def pace_to_seconds(pace):
        """Convert a pace string (mm:ss format) to seconds."""
        parts = pace.split(':')
        if len(parts) != 2:
            return 0
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        except ValueError:
            return 0

    def seconds_to_pace(seconds):
        """Convert seconds to a pace string (mm:ss format)."""
        minutes = int(seconds) // 60
        remaining_seconds = int(seconds) % 60
        return f"{minutes}:{remaining_seconds:02d}"

    def on_step_type_change(self):
        """Gestisce il cambio di tipo di step."""
        step_type = self.step_type_var.get()
        
        # Se è un repeat, cambia la condizione di fine
        if step_type == "repeat":
            self.end_condition_var.set("iterations")
            self.target_type_var.set("no.target")
            self.on_end_condition_change()
            self.on_target_type_change()
    
    def on_end_condition_change(self):
        """Gestisce il cambio di condizione di fine."""
        end_condition = self.end_condition_var.get()
        
        # Mostra/nascondi il frame del valore
        if end_condition == "lap.button":
            self.end_value_entry.config(state="disabled")
            self.end_value_label.config(text="")
        else:
            self.end_value_entry.config(state="normal")
            
            # Aggiorna l'etichetta
            if end_condition == "time":
                self.end_value_label.config(text="(formato mm:ss)")
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
        # Valida la condizione di fine
        end_condition = self.end_condition_var.get()
        
        if end_condition != "lap.button":
            end_value = self.end_condition_value_var.get()
            
            if not end_value:
                show_error("Errore", "Inserisci un valore per la condizione di fine", parent=self)
                return False
            
            if end_condition == "time":
                # Verifica che sia nel formato mm:ss
                if not validate_pace(end_value):
                    show_error("Errore", "Il tempo deve essere nel formato mm:ss (es. 5:30)", parent=self)
                    return False
            
            elif end_condition == "distance":
                # Verifica che sia nel formato Nm o Nkm
                if not re.match(r'^\d+(\.\d+)?[mk]m$', end_value):
                    show_error("Errore", "La distanza deve essere nel formato Nm o Nkm (es. 1000m o 5km)", parent=self)
                    return False
            
            elif end_condition == "iterations":
                # Verifica che sia un numero intero
                try:
                    int(end_value)
                except ValueError:
                    show_error("Errore", "Il numero di ripetizioni deve essere un intero", parent=self)
                    return False
        
        # Valida il target
        target_type = self.target_type_var.get()
        
        if target_type != "no.target":
            if target_type in ["pace.zone", "heart.rate.zone", "power.zone"]:
                min_value = self.target_min_var.get()
                max_value = self.target_max_var.get()
                
                if not min_value or not max_value:
                    show_error("Errore", "Inserisci i valori minimo e massimo per il target", parent=self)
                    return False
                
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
        
        # Crea il target
        target_type = self.target_type_var.get()
        target = None
        
        if target_type != "no.target":
            if target_type in ["pace.zone", "heart.rate.zone", "power.zone"]:
                min_value = self.target_min_var.get()
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