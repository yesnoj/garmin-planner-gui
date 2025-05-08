#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog per la creazione e modifica di un gruppo di ripetizioni.
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List, Optional, Callable

from garmin_planner_gui.config import get_config
from garmin_planner_gui.models.workout import WorkoutStep
from garmin_planner_gui.gui.utils import (
    create_tooltip, show_error, show_warning, ask_yes_no
)
from garmin_planner_gui.gui.styles import get_icon_for_step


class RepeatStepDialog(tk.Toplevel):
    """Dialog per la creazione e modifica di un gruppo di ripetizioni."""
    
    def __init__(self, parent, repeat_step: Optional[WorkoutStep] = None, 
               sport_type: str = "running", callback: Optional[Callable] = None):
        """
        Inizializza il dialog.
        
        Args:
            parent: Widget genitore
            repeat_step: Step di ripetizione da modificare (None per crearne uno nuovo)
            sport_type: Tipo di sport (running, cycling, swimming)
            callback: Funzione da chiamare alla conferma
        """
        super().__init__(parent)
        self.parent = parent
        self.repeat_step = repeat_step
        self.sport_type = sport_type
        self.callback = callback
        self.config = get_config()
        
        # Lista degli step interni
        if repeat_step and repeat_step.workout_steps:
            self.steps = repeat_step.workout_steps.copy()
        else:
            self.steps = []
        
        # Valori predefiniti
        if repeat_step:
            self.iterations = repeat_step.end_condition_value or 1
        else:
            self.iterations = 3  # Valore predefinito
        
        # Variabili
        self.iterations_var = tk.StringVar(value=str(self.iterations))
        
        # Step selezionato
        self.selected_step_index = None
        
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
        
        ttk.Label(header_frame, text="Gruppo di ripetizioni", 
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        # Frame per il numero di ripetizioni
        iterations_frame = ttk.LabelFrame(main_frame, text="Numero di ripetizioni")
        iterations_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(iterations_frame, text="Ripetizioni:").pack(side=tk.LEFT, padx=(10, 5), pady=10)
        
        iterations_entry = ttk.Entry(iterations_frame, textvariable=self.iterations_var, 
                                  width=5)
        iterations_entry.pack(side=tk.LEFT, pady=10)
        
        # Frame per la lista degli step
        steps_frame = ttk.LabelFrame(main_frame, text="Step da ripetere")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Toolbar per la gestione degli step
        toolbar = ttk.Frame(steps_frame)
        toolbar.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Button(toolbar, text="Aggiungi step...", 
                 command=self.add_step).pack(side=tk.LEFT, padx=(0, 5))
        
        self.edit_button = ttk.Button(toolbar, text="Modifica step...", 
                                    command=self.edit_step, state="disabled")
        self.edit_button.pack(side=tk.LEFT, padx=5)
        
        self.delete_button = ttk.Button(toolbar, text="Elimina step", 
                                     command=self.delete_step, state="disabled")
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        self.move_up_button = ttk.Button(toolbar, text="Sposta su", 
                                      command=self.move_step_up, state="disabled")
        self.move_up_button.pack(side=tk.LEFT, padx=5)
        
        self.move_down_button = ttk.Button(toolbar, text="Sposta giù", 
                                        command=self.move_step_down, state="disabled")
        self.move_down_button.pack(side=tk.LEFT, padx=5)
        
        # Lista degli step
        list_frame = ttk.Frame(steps_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        # Crea il treeview
        columns = ("type", "condition", "value", "description")
        self.steps_tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                                     selectmode="browse")
        
        # Intestazioni
        self.steps_tree.heading("type", text="Tipo")
        self.steps_tree.heading("condition", text="Condizione")
        self.steps_tree.heading("value", text="Valore")
        self.steps_tree.heading("description", text="Descrizione")
        
        # Larghezze colonne
        self.steps_tree.column("type", width=100)
        self.steps_tree.column("condition", width=100)
        self.steps_tree.column("value", width=100)
        self.steps_tree.column("description", width=250)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.steps_tree.yview)
        self.steps_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Associa evento di selezione
        self.steps_tree.bind("<<TreeviewSelect>>", self.on_step_selected)
        self.steps_tree.bind("<Double-1>", lambda e: self.edit_step())
        
        # Pulsanti
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="Annulla", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Popola la lista
        self.populate_steps_list()
    
    def populate_steps_list(self):
        """Popola la lista degli step."""
        # Pulisci la lista
        for item in self.steps_tree.get_children():
            self.steps_tree.delete(item)
        
        # Aggiungi gli step
        for i, step in enumerate(self.steps):
            # Ottieni i valori da visualizzare
            step_type = step.step_type
            
            # Condizione di fine
            end_condition = step.end_condition
            
            # Valore
            if end_condition == "lap.button":
                value = "Lap button"
            elif end_condition == "time":
                # Formatta il tempo
                if isinstance(step.end_condition_value, str) and ":" in step.end_condition_value:
                    value = step.end_condition_value
                elif isinstance(step.end_condition_value, (int, float)):
                    # Converti secondi in mm:ss
                    seconds = int(step.end_condition_value)
                    minutes = seconds // 60
                    seconds = seconds % 60
                    value = f"{minutes}:{seconds:02d}"
                else:
                    value = str(step.end_condition_value)
            elif end_condition == "distance":
                # Formatta la distanza
                if isinstance(step.end_condition_value, str):
                    value = step.end_condition_value
                elif isinstance(step.end_condition_value, (int, float)):
                    # Converti metri in m o km
                    if step.end_condition_value >= 1000:
                        value = f"{step.end_condition_value / 1000:.2f}km".replace('.00', '')
                    else:
                        value = f"{int(step.end_condition_value)}m"
                else:
                    value = str(step.end_condition_value)
            else:
                value = str(step.end_condition_value) if step.end_condition_value is not None else ""
            
            # Descrizione
            description = step.description
            
            # Aggiungi alla lista
            self.steps_tree.insert("", "end", 
                                 values=(step_type, end_condition, value, description), 
                                 tags=(str(i)))
    
    def on_step_selected(self, event):
        """
        Gestisce la selezione di uno step.
        
        Args:
            event: Evento Tkinter
        """
        # Ottieni l'item selezionato
        selection = self.steps_tree.selection()
        
        if selection:
            # Abilita i pulsanti
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
            
            # Ottieni l'indice
            item = selection[0]
            index = int(self.steps_tree.item(item, "tags")[0])
            self.selected_step_index = index
            
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
            self.selected_step_index = None
    
    def add_step(self):
        """Aggiunge un nuovo step."""
        # Importa qui per evitare import circolari
        from garmin_planner_gui.gui.dialogs.workout_step import WorkoutStepDialog
        
        # Crea un nuovo step
        def on_step_added(step):
            self.steps.append(step)
            self.populate_steps_list()
        
        # Crea il dialog
        dialog = WorkoutStepDialog(self, callback=on_step_added, sport_type=self.sport_type)
    
    def edit_step(self):
        """Modifica lo step selezionato."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None:
            return
        
        # Importa qui per evitare import circolari
        from garmin_planner_gui.gui.dialogs.workout_step import WorkoutStepDialog
        
        # Ottieni lo step
        step = self.steps[self.selected_step_index]
        
        # Crea il dialog
        def on_step_edited(step):
            self.steps[self.selected_step_index] = step
            self.populate_steps_list()
        
        # Crea il dialog
        dialog = WorkoutStepDialog(self, step=step, callback=on_step_edited, sport_type=self.sport_type)
    
    def delete_step(self):
        """Elimina lo step selezionato."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None:
            return
        
        # Chiedi conferma
        if not ask_yes_no("Conferma eliminazione", 
                        "Sei sicuro di voler eliminare questo step?", 
                        parent=self):
            return
        
        # Elimina lo step
        del self.steps[self.selected_step_index]
        
        # Aggiorna la lista
        self.populate_steps_list()
        
        # Deseleziona
        self.selected_step_index = None
        self.edit_button.config(state="disabled")
        self.delete_button.config(state="disabled")
        self.move_up_button.config(state="disabled")
        self.move_down_button.config(state="disabled")
    
    def move_step_up(self):
        """Sposta lo step selezionato verso l'alto."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None or self.selected_step_index == 0:
            return
        
        # Scambia gli step
        self.steps[self.selected_step_index], self.steps[self.selected_step_index - 1] = \
            self.steps[self.selected_step_index - 1], self.steps[self.selected_step_index]
        
        # Aggiorna l'indice selezionato
        self.selected_step_index -= 1
        
        # Aggiorna la lista
        self.populate_steps_list()
        
        # Seleziona lo step spostato
        items = self.steps_tree.get_children("")
        if 0 <= self.selected_step_index < len(items):
            self.steps_tree.selection_set(items[self.selected_step_index])
            self.steps_tree.see(items[self.selected_step_index])
    
    def move_step_down(self):
        """Sposta lo step selezionato verso il basso."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None or self.selected_step_index >= len(self.steps) - 1:
            return
        
        # Scambia gli step
        self.steps[self.selected_step_index], self.steps[self.selected_step_index + 1] = \
            self.steps[self.selected_step_index + 1], self.steps[self.selected_step_index]
        
        # Aggiorna l'indice selezionato
        self.selected_step_index += 1
        
        # Aggiorna la lista
        self.populate_steps_list()
        
        # Seleziona lo step spostato
        items = self.steps_tree.get_children("")
        if 0 <= self.selected_step_index < len(items):
            self.steps_tree.selection_set(items[self.selected_step_index])
            self.steps_tree.see(items[self.selected_step_index])
    
    def validate(self) -> bool:
        """
        Valida i dati inseriti.
        
        Returns:
            True se i dati sono validi, False altrimenti
        """
        # Verifica che il numero di ripetizioni sia valido
        try:
            iterations = int(self.iterations_var.get())
            if iterations <= 0:
                show_error("Errore", "Il numero di ripetizioni deve essere maggiore di zero", parent=self)
                return False
        except ValueError:
            show_error("Errore", "Il numero di ripetizioni deve essere un numero intero", parent=self)
            return False
        
        # Verifica che ci siano degli step
        if not self.steps:
            show_error("Errore", "Aggiungi almeno uno step da ripetere", parent=self)
            return False
        
        return True
    
    def on_ok(self):
        """Gestisce il click sul pulsante OK."""
        # Valida i dati
        if not self.validate():
            return
        
        # Ottieni il numero di ripetizioni
        iterations = int(self.iterations_var.get())
        
        # Crea o aggiorna lo step di ripetizione
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
    
    # Crea un dialog con uno step nuovo
    dialog = RepeatStepDialog(root)
    
    # Avvia il loop
    root.mainloop()