#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog per la creazione e modifica di un gruppo di ripetizioni.
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, Callable, List, Tuple

from config import get_config
from models.workout import WorkoutStep, Target
from models.zone import PaceZone, HeartRateZone, PowerZone
from gui.utils import (
    create_tooltip, show_error, show_warning, 
    validate_pace, validate_power, validate_hr, pace_to_seconds
)
from gui.dialogs.workout_step import WorkoutStepDialog


class RepeatStepDialog(tk.Toplevel):
    """Dialog per la creazione e modifica di un gruppo di ripetizioni."""
    
    def __init__(self, parent, repeat_step: Optional[WorkoutStep] = None, 
               sport_type: str = "running", callback: Optional[Callable] = None):
        """
        Inizializza il dialog.
        
        Args:
            parent: Widget genitore
            repeat_step: Step ripetizione da modificare (None per crearne uno nuovo)
            sport_type: Tipo di sport (running, cycling, swimming)
            callback: Funzione da chiamare alla conferma
        """
        super().__init__(parent)
        self.parent = parent
        self.repeat_step = repeat_step
        self.sport_type = sport_type
        self.callback = callback
        self.config = get_config()
        
        # Valori predefiniti se non c'è uno step
        if repeat_step:
            self.iterations = repeat_step.end_condition_value or 1
            self.steps = repeat_step.workout_steps.copy()
        else:
            self.iterations = 1
            self.steps = []
        
        # Variabili
        self.iterations_var = tk.StringVar(value=str(self.iterations))
        
        # Configura il dialog
        self.title("Gruppo di ripetizioni")
        self.geometry("600x500")
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

    def create_widgets(self):
        """Crea i widget del dialog."""
        # Frame principale con padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Intestazione
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text=f"Gruppo di ripetizioni", 
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        # Frame per il numero di ripetizioni
        iterations_frame = ttk.LabelFrame(main_frame, text="Numero di ripetizioni")
        iterations_frame.pack(fill=tk.X, pady=(0, 10))
        
        iterations_entry = ttk.Entry(iterations_frame, textvariable=self.iterations_var, 
                                   width=10)
        iterations_entry.pack(side=tk.LEFT, padx=10, pady=10)
        
        create_tooltip(iterations_entry, "Inserisci il numero di ripetizioni")
        
        # Frame per gli step del gruppo
        steps_frame = ttk.LabelFrame(main_frame, text="Step del gruppo")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Toolbar per la gestione degli step
        toolbar = ttk.Frame(steps_frame)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        add_button = ttk.Button(toolbar, text="Aggiungi step...", command=self.add_step)
        add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.edit_button = ttk.Button(toolbar, text="Modifica step...", 
                                    command=self.edit_step, state="disabled")
        self.edit_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_button = ttk.Button(toolbar, text="Elimina step", 
                                      command=self.delete_step, state="disabled")
        self.delete_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.move_up_button = ttk.Button(toolbar, text="Sposta su", 
                                       command=self.move_step_up, state="disabled")
        self.move_up_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.move_down_button = ttk.Button(toolbar, text="Sposta giù", 
                                         command=self.move_step_down, state="disabled")
        self.move_down_button.pack(side=tk.LEFT)
        
        # Lista degli step
        self.steps_list = ttk.Treeview(steps_frame, columns=('step', 'value', 'target'), 
                                     show='headings', height=8)
        self.steps_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Intestazioni
        self.steps_list.heading('step', text='Tipo')
        self.steps_list.heading('value', text='Valore')
        self.steps_list.heading('target', text='Target')
        
        # Larghezze colonne
        self.steps_list.column('step', width=100)
        self.steps_list.column('value', width=150)
        self.steps_list.column('target', width=200)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(steps_frame, orient=tk.VERTICAL, 
                                command=self.steps_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))
        
        self.steps_list.configure(yscrollcommand=scrollbar.set)
        
        # Associa evento di selezione
        self.steps_list.bind('<<TreeviewSelect>>', self.on_step_selected)
        self.steps_list.bind('<Double-1>', lambda e: self.edit_step())
        
        # Popola la lista degli step
        self.update_steps_list()
        
        # Pulsanti
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="Annulla", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
    
    def update_steps_list(self):
        """Aggiorna la lista degli step."""
        # Pulisci la lista attuale
        for item in self.steps_list.get_children():
            self.steps_list.delete(item)
        
        # Nessuno step selezionato
        self.edit_button.config(state="disabled")
        self.delete_button.config(state="disabled")
        self.move_up_button.config(state="disabled")
        self.move_down_button.config(state="disabled")
        
        # Aggiungi gli step
        for i, step in enumerate(self.steps):
            # Formatta il tipo di step
            step_type = step.step_type.capitalize()
            
            # Formatta il valore
            value = ""
            
            if step.end_condition == "lap.button":
                value = "Fino a pulsante lap"
            elif step.end_condition == "time":
                value_str = step.end_condition_value
                if isinstance(value_str, (int, float)):
                    # Converti secondi in mm:ss
                    seconds = int(value_str)
                    minutes = seconds // 60
                    seconds = seconds % 60
                    value_str = f"{minutes}:{seconds:02d}"
                
                value = f"Durata: {value_str}"
            elif step.end_condition == "distance":
                value_str = step.end_condition_value
                if isinstance(value_str, (int, float)):
                    # Converti metri in m o km
                    if value_str >= 1000:
                        value_str = f"{value_str / 1000:.2f}km".replace('.00', '')
                    else:
                        value_str = f"{value_str}m"
                
                value = f"Distanza: {value_str}"
            elif step.end_condition == "iterations":
                value = f"Ripetizioni: {step.end_condition_value}"
            
            # Formatta il target
            target = "Nessun target"
            
            if step.target and step.target.target != "no.target":
                # Verifica se esiste il nome della zona
                if hasattr(step.target, 'target_zone_name') and step.target.target_zone_name:
                    # Usa il nome della zona se disponibile
                    zone_name = step.target.target_zone_name
                    
                    # Distingui i diversi tipi di zone
                    if step.target.target == "pace.zone":
                        target = f"Zona {zone_name}"
                    elif step.target.target == "heart.rate.zone":
                        target = f"Zona FC {zone_name}"
                    elif step.target.target == "power.zone":
                        target = f"Zona Potenza {zone_name}"
                    else:
                        target = f"Zona {zone_name}"
                else:
                    # Otteniamo la configurazione
                    app_config = get_config()
                    
                    if step.target.target == "pace.zone":
                        # Converti da m/s a min/km
                        from_value = step.target.from_value
                        to_value = step.target.to_value
                        
                        if from_value and to_value:
                            # ms a mm:ss/km
                            min_pace_secs = int(1000 / from_value)
                            max_pace_secs = int(1000 / to_value)
                            
                            min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                            max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                            
                            # Cerca la zona corrispondente
                            paces = app_config.get(f'sports.{self.sport_type}.paces', {})
                            zone_name = None
                            
                            for name, pace_range in paces.items():
                                if '-' in pace_range:
                                    pace_min, pace_max = pace_range.split('-')
                                    if pace_min.strip() == min_pace and pace_max.strip() == max_pace:
                                        zone_name = name
                                        break
                                elif pace_range == min_pace and pace_range == max_pace:
                                    zone_name = name
                                    break
                            
                            if zone_name:
                                target = f"Zona {zone_name}"
                            else:
                                target = f"Passo {min_pace}-{max_pace} min/km"
                        
                    elif step.target.target == "heart.rate.zone":
                        from_value = step.target.from_value
                        to_value = step.target.to_value
                        
                        if from_value and to_value:
                            # Cerca la zona corrispondente
                            heart_rates = app_config.get('heart_rates', {})
                            zone_name = None
                            
                            for name, hr_range in heart_rates.items():
                                if name.endswith('_HR'):
                                    # Calcola valori effettivi usando max_hr
                                    max_hr = heart_rates.get('max_hr', 180)
                                    
                                    if '-' in hr_range and 'max_hr' in hr_range:
                                        # Formato: 62-76% max_hr
                                        parts = hr_range.split('-')
                                        min_percent = float(parts[0])
                                        max_percent = float(parts[1].split('%')[0])
                                        hr_min = int(min_percent * max_hr / 100)
                                        hr_max = int(max_percent * max_hr / 100)
                                        
                                        if hr_min <= from_value <= hr_max and hr_min <= to_value <= hr_max:
                                            zone_name = name
                                            break
                            
                            if zone_name:
                                target = f"Zona {zone_name}"
                            else:
                                target = f"FC {from_value}-{to_value} bpm"
                        
                    elif step.target.target == "power.zone":
                        from_value = step.target.from_value
                        to_value = step.target.to_value
                        
                        if from_value and to_value:
                            # Cerca la zona corrispondente
                            power_values = app_config.get('sports.cycling.power_values', {})
                            zone_name = None
                            
                            for name, power_range in power_values.items():
                                if '-' in power_range:
                                    power_min, power_max = power_range.split('-')
                                    if int(power_min) == from_value and int(power_max) == to_value:
                                        zone_name = name
                                        break
                                elif power_range.startswith('<'):
                                    power_val = int(power_range[1:])
                                    if from_value == 0 and to_value == power_val:
                                        zone_name = name
                                        break
                                elif power_range.endswith('+'):
                                    power_val = int(power_range[:-1])
                                    if from_value == power_val and to_value == 9999:
                                        zone_name = name
                                        break
                                else:
                                    power_val = int(power_range)
                                    if from_value == power_val and to_value == power_val:
                                        zone_name = name
                                        break
                            
                            if zone_name:
                                target = f"Zona {zone_name}"
                            else:
                                target = f"Potenza {from_value}-{to_value} W"
            
            # Aggiungi lo step alla lista
            self.steps_list.insert("", "end", values=(step_type, value, target), tags=(str(i),))
    
    def on_step_selected(self, event):
        """
        Gestisce la selezione di uno step nella lista.
        
        Args:
            event: Evento Tkinter
        """
        selection = self.steps_list.selection()
        
        if selection:
            # Ottieni l'indice dello step selezionato
            item = selection[0]
            index = int(self.steps_list.item(item, "tags")[0])
            
            # Abilita i pulsanti
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
            
            # Abilita/disabilita i pulsanti di spostamento
            if index > 0:
                self.move_up_button.config(state="normal")
            else:
                self.move_up_button.config(state="disabled")
            
            if index < len(self.steps) - 1:
                self.move_down_button.config(state="normal")
            else:
                self.move_down_button.config(state="disabled")
        else:
            # Disabilita i pulsanti
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.move_up_button.config(state="disabled")
            self.move_down_button.config(state="disabled")
    
    def add_step(self):
        """Aggiunge un nuovo step al gruppo."""
        # Crea un dialog per lo step
        dialog = WorkoutStepDialog(self, sport_type=self.sport_type, callback=self.on_step_added)
    
    def on_step_added(self, step):
        """
        Callback per l'aggiunta di uno step.
        
        Args:
            step: Step aggiunto
        """
        # Aggiungi lo step alla lista
        self.steps.append(step)
        
        # Aggiorna la lista
        self.update_steps_list()
    
    def edit_step(self):
        """Modifica lo step selezionato."""
        selection = self.steps_list.selection()
        
        if selection:
            # Ottieni l'indice dello step selezionato
            item = selection[0]
            index = int(self.steps_list.item(item, "tags")[0])
            
            # Ottieni lo step
            step = self.steps[index]
            
            # Crea un dialog per lo step
            dialog = WorkoutStepDialog(self, step=step, sport_type=self.sport_type, 
                                      callback=lambda s: self.on_step_edited(index, s))
    
    def on_step_edited(self, index, step):
        """
        Callback per la modifica di uno step.
        
        Args:
            index: Indice dello step modificato
            step: Step modificato
        """
        # Aggiorna lo step nella lista
        self.steps[index] = step
        
        # Aggiorna la lista
        self.update_steps_list()
    
    def delete_step(self):
        """Elimina lo step selezionato."""
        selection = self.steps_list.selection()
        
        if selection:
            # Ottieni l'indice dello step selezionato
            item = selection[0]
            index = int(self.steps_list.item(item, "tags")[0])
            
            # Rimuovi lo step dalla lista
            del self.steps[index]
            
            # Aggiorna la lista
            self.update_steps_list()
    
    def move_step_up(self):
        """Sposta lo step selezionato verso l'alto."""
        selection = self.steps_list.selection()
        
        if selection:
            # Ottieni l'indice dello step selezionato
            item = selection[0]
            index = int(self.steps_list.item(item, "tags")[0])
            
            # Verifica che non sia il primo step
            if index > 0:
                # Scambia gli step
                self.steps[index], self.steps[index - 1] = self.steps[index - 1], self.steps[index]
                
                # Aggiorna la lista
                self.update_steps_list()
                
                # Seleziona lo step spostato
                self.steps_list.selection_set(self.steps_list.get_children()[index - 1])
    
    def move_step_down(self):
        """Sposta lo step selezionato verso il basso."""
        selection = self.steps_list.selection()
        
        if selection:
            # Ottieni l'indice dello step selezionato
            item = selection[0]
            index = int(self.steps_list.item(item, "tags")[0])
            
            # Verifica che non sia l'ultimo step
            if index < len(self.steps) - 1:
                # Scambia gli step
                self.steps[index], self.steps[index + 1] = self.steps[index + 1], self.steps[index]
                
                # Aggiorna la lista
                self.update_steps_list()
                
                # Seleziona lo step spostato
                self.steps_list.selection_set(self.steps_list.get_children()[index + 1])
    
    def validate(self) -> bool:
        """
        Valida i dati inseriti.
        
        Returns:
            True se i dati sono validi, False altrimenti
        """
        # Valida il numero di ripetizioni
        try:
            iterations = int(self.iterations_var.get())  # Assicuriamoci che sia un intero
            
            if iterations <= 0:
                show_error("Errore", "Il numero di ripetizioni deve essere maggiore di zero", parent=self)
                return False
            
        except ValueError:
            show_error("Errore", "Il numero di ripetizioni deve essere un intero", parent=self)
            return False
        
        # Valida che ci sia almeno uno step
        if not self.steps:
            show_error("Errore", "Il gruppo deve contenere almeno uno step", parent=self)
            return False
        
        return True
    
    def on_ok(self):
        """Gestisce il click sul pulsante OK."""
        # Valida i dati
        if not self.validate():
            return
        
        # Ottieni i valori
        iterations = int(self.iterations_var.get())  # Assicurati che sia un intero
        
        # Crea o aggiorna lo step
        if self.repeat_step:
            # Aggiorna lo step esistente
            self.repeat_step.end_condition_value = iterations
            self.repeat_step.workout_steps = self.steps.copy()
        else:
            # Crea un nuovo step
            self.repeat_step = WorkoutStep(
                order=0,
                step_type="repeat",
                end_condition="iterations",
                end_condition_value=iterations
            )
            
            # Aggiungi gli step
            for step in self.steps:
                self.repeat_step.add_step(step)
        
        # Chiama il callback
        if self.callback:
            self.callback(self.repeat_step)
        
        # Chiudi il dialog
        self.destroy()
    
    def on_cancel(self):
        """Gestisce il click sul pulsante Annulla."""
        # Chiudi il dialog senza fare nulla
        self.destroy()


if __name__ == "__main__":
    # Test del dialog
    root = tk.Tk()
    root.withdraw()
    
    def on_repeat_added(repeat_step):
        """Callback per l'aggiunta di un gruppo di ripetizioni."""
        if repeat_step:
            print(f"Gruppo di ripetizioni aggiunto: {repeat_step.end_condition_value} ripetizioni")
            for step in repeat_step.workout_steps:
                print(f"  - {step.step_type}: {step.end_condition_value}")
        else:
            print("Aggiunta annullata")
    
    # Crea un dialog per un nuovo gruppo
    dialog = RepeatStepDialog(root, callback=on_repeat_added)
    
    # Avvia il loop
    root.mainloop()