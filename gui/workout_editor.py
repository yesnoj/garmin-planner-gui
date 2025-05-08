#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Frame per l'editor grafico di allenamenti.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
import json
import datetime
from typing import Dict, Any, List, Tuple, Optional

from config import get_config
from auth import GarminClient
from models.workout import Workout, WorkoutStep, Target
from gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no,
    create_scrollable_frame
)
from gui.styles import get_icon_for_sport, get_icon_for_step


class WorkoutEditorFrame(ttk.Frame):
    """Frame per l'editor grafico di allenamenti."""
    
    def __init__(self, parent: ttk.Notebook, controller):
        """
        Inizializza il frame dell'editor di allenamenti.
        
        Args:
            parent: Widget genitore (notebook)
            controller: Controller principale dell'applicazione
        """
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.config = get_config()
        self.garmin_client = None
        
        # Lista degli allenamenti disponibili
        self.workouts = []
        
        # Allenamento corrente
        self.current_workout = None
        self.current_workout_id = None
        self.current_workout_modified = False
        
        # Step selezionato
        self.selected_step_index = None
        
        # Creazione dei widget
        self.create_widgets()
    
    def create_widgets(self):
        """Crea i widget del frame."""
        # Frame principale
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pannello diviso: lista a sinistra, editor a destra
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Frame sinistro per la lista degli allenamenti
        left_frame = ttk.Frame(paned, padding=5)
        paned.add(left_frame, weight=1)
        
        # Frame destro per l'editor
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(right_frame, weight=3)
        
        # --- Parte sinistra: Lista degli allenamenti ---
        
        # Filtro
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="Filtro:").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=20)
        filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Associa evento di modifica del filtro
        self.filter_var.trace_add("write", lambda *args: self.update_workout_list())
        
        # Lista degli allenamenti
        list_frame = ttk.LabelFrame(left_frame, text="Allenamenti disponibili")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea il treeview
        columns = ("name", "sport", "steps")
        self.workout_tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                                      selectmode="browse")
        
        # Intestazioni
        self.workout_tree.heading("name", text="Nome")
        self.workout_tree.heading("sport", text="Sport")
        self.workout_tree.heading("steps", text="Step")
        
        # Larghezze colonne
        self.workout_tree.column("name", width=150)
        self.workout_tree.column("sport", width=70)
        self.workout_tree.column("steps", width=50)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.workout_tree.yview)
        self.workout_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.workout_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Associa evento di selezione
        self.workout_tree.bind("<<TreeviewSelect>>", self.on_workout_selected)
        self.workout_tree.bind("<Double-1>", lambda e: self.load_workout())
        
        # Pulsanti per la gestione degli allenamenti
        buttons_frame = ttk.Frame(left_frame)
        buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        new_button = ttk.Button(buttons_frame, text="Nuovo", command=self.new_workout)
        new_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_button = ttk.Button(buttons_frame, text="Elimina", 
                                     command=self.delete_workout, state="disabled")
        self.delete_button.pack(side=tk.LEFT)
        
        self.refresh_button = ttk.Button(buttons_frame, text="Aggiorna", 
                                      command=self.refresh_workouts)
        self.refresh_button.pack(side=tk.RIGHT)
        
        # --- Parte destra: Editor dell'allenamento ---
        
        # Frame per il titolo e le proprietà dell'allenamento
        workout_header = ttk.Frame(right_frame)
        workout_header.pack(fill=tk.X, pady=(0, 10))
        
        # Nome dell'allenamento
        self.name_var = tk.StringVar()
        ttk.Label(workout_header, text="Nome:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        name_entry = ttk.Entry(workout_header, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, sticky=tk.W+tk.E)
        
        # Tipo di sport
        ttk.Label(workout_header, text="Sport:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        
        self.sport_var = tk.StringVar(value="running")
        sport_combo = ttk.Combobox(workout_header, textvariable=self.sport_var, values=["running", "cycling", "swimming"], 
                                 width=20, state="readonly")
        sport_combo.grid(row=1, column=1, sticky=tk.W)
        
        # Descrizione
        ttk.Label(workout_header, text="Descrizione:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        
        self.description_var = tk.StringVar()
        description_entry = ttk.Entry(workout_header, textvariable=self.description_var, width=40)
        description_entry.grid(row=2, column=1, sticky=tk.W+tk.E)
        
        # Configurazione della grid
        workout_header.columnconfigure(1, weight=1)
        
        # Frame per gli step dell'allenamento
        steps_frame = ttk.LabelFrame(right_frame, text="Step dell'allenamento")
        steps_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar per la gestione degli step
        toolbar = ttk.Frame(steps_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        add_button = ttk.Button(toolbar, text="Aggiungi step...", command=self.add_step)
        add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        add_repeat_button = ttk.Button(toolbar, text="Aggiungi ripetizione...", 
                                     command=self.add_repeat)
        add_repeat_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.edit_button = ttk.Button(toolbar, text="Modifica step...", 
                                    command=self.edit_step, state="disabled")
        self.edit_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_step_button = ttk.Button(toolbar, text="Elimina step", 
                                         command=self.delete_step, state="disabled")
        self.delete_step_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.move_up_button = ttk.Button(toolbar, text="Sposta su", 
                                      command=self.move_step_up, state="disabled")
        self.move_up_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.move_down_button = ttk.Button(toolbar, text="Sposta giù", 
                                        command=self.move_step_down, state="disabled")
        self.move_down_button.pack(side=tk.LEFT)
        
        # Lista degli step
        self.steps_frame, self.steps_container = create_scrollable_frame(steps_frame)
        self.steps_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Placeholder per gli step (verrà popolato in update_steps_list)
        ttk.Label(self.steps_container, text="Nessun allenamento selezionato").pack()
        
        # Pulsanti per salvare/annullare
        save_frame = ttk.Frame(right_frame)
        save_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.save_button = ttk.Button(save_frame, text="Salva", 
                                    command=self.save_workout, state="disabled")
        self.save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.send_button = ttk.Button(save_frame, text="Invia a Garmin Connect", 
                                    command=self.send_to_garmin, state="disabled")
        self.send_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.discard_button = ttk.Button(save_frame, text="Annulla modifiche", 
                                      command=self.discard_changes, state="disabled")
        self.discard_button.pack(side=tk.RIGHT, padx=(5, 0))

    def update_workout_list(self):
        """Aggiorna la lista degli allenamenti disponibili."""
        # Ottieni il filtro
        filter_text = self.filter_var.get().lower()
        
        # Pulisci la lista attuale
        for item in self.workout_tree.get_children():
            self.workout_tree.delete(item)
        
        # Filtra gli allenamenti
        filtered_workouts = []
        for workout_id, workout_data in self.workouts:
            # Estrai i dati dell'allenamento
            name = workout_data.get('workoutName', '')
            
            # Applica il filtro
            if filter_text and filter_text not in name.lower():
                continue
            
            # Aggiungi all'elenco filtrato
            filtered_workouts.append((workout_id, workout_data))
        
        # Aggiungi gli allenamenti filtrati alla lista
        for workout_id, workout_data in filtered_workouts:
            # Estrai i dati dell'allenamento
            name = workout_data.get('workoutName', '')
            
            # Ottieni il tipo di sport
            sport_type = 'running'  # Default
            if 'sportType' in workout_data and 'sportTypeKey' in workout_data['sportType']:
                sport_type = workout_data['sportType']['sportTypeKey']
            
            # Conta gli step
            step_count = 0
            for segment in workout_data.get('workoutSegments', []):
                step_count += len(segment.get('workoutSteps', []))
            
            # Aggiungi alla lista
            self.workout_tree.insert("", "end", 
                                  values=(name, sport_type, step_count), 
                                  tags=(workout_id,))
    
    def on_workout_selected(self, event):
        """
        Gestisce la selezione di un allenamento nella lista.
        
        Args:
            event: Evento Tkinter
        """
        # Ottieni l'item selezionato
        selection = self.workout_tree.selection()
        
        if selection:
            # Abilita il pulsante per eliminare
            self.delete_button.config(state="normal")
        else:
            # Disabilita il pulsante per eliminare
            self.delete_button.config(state="disabled")
    
    def on_step_selected(self, index):
        """
        Gestisce la selezione di uno step nella lista.
        
        Args:
            index: Indice dello step selezionato
        """
        # Salva l'indice selezionato
        self.selected_step_index = index
        
        # Abilita i pulsanti
        self.edit_button.config(state="normal")
        self.delete_step_button.config(state="normal")
        
        # Abilita/disabilita i pulsanti di spostamento
        if index > 0:
            self.move_up_button.config(state="normal")
        else:
            self.move_up_button.config(state="disabled")
        
        if index < len(self.current_workout.workout_steps) - 1:
            self.move_down_button.config(state="normal")
        else:
            self.move_down_button.config(state="disabled")
    
    def refresh_workouts(self):
        """Aggiorna la lista degli allenamenti da Garmin Connect."""
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Ottieni la lista degli allenamenti
            workouts_data = self.garmin_client.list_workouts()
            
            # Trasforma in una lista di tuple (id, data)
            self.workouts = []
            for workout in workouts_data:
                workout_id = str(workout.get('workoutId', ''))
                self.workouts.append((workout_id, workout))
            
            # Aggiorna la lista
            self.update_workout_list()
            
            # Mostra messaggio di conferma
            self.controller.set_status("Allenamenti aggiornati da Garmin Connect")
            
        except Exception as e:
            logging.error(f"Errore nell'aggiornamento degli allenamenti: {str(e)}")
            show_error("Errore", 
                     f"Impossibile aggiornare gli allenamenti: {str(e)}", 
                     parent=self)
    
    def load_workout(self):
        """Carica l'allenamento selezionato nell'editor."""
        # Verifica che sia selezionato un allenamento
        selection = self.workout_tree.selection()
        if not selection:
            return
        
        # Verifica che non ci siano modifiche non salvate
        if self.current_workout_modified:
            if not ask_yes_no("Modifiche non salvate", 
                          "Ci sono modifiche non salvate. Vuoi continuare e perdere le modifiche?", 
                          parent=self):
                return
        
        # Ottieni l'ID dell'allenamento
        item = selection[0]
        workout_id = self.workout_tree.item(item, "tags")[0]
        
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Ottieni i dettagli dell'allenamento
            workout_data = self.garmin_client.get_workout(workout_id)
            
            if not workout_data:
                raise ValueError(f"Allenamento non trovato: {workout_id}")
            
            # Importa l'allenamento
            from services.garmin_service import GarminService
            service = GarminService(self.garmin_client)
            
            workout = service.import_workout(workout_data)
            
            if not workout:
                raise ValueError(f"Impossibile importare l'allenamento: {workout_id}")
            
            # Imposta l'allenamento corrente
            self.current_workout = workout
            self.current_workout_id = workout_id
            self.current_workout_modified = False
            
            # Aggiorna i campi
            self.name_var.set(workout.workout_name)
            self.sport_var.set(workout.sport_type)
            self.description_var.set(workout.description or "")
            
            # Aggiorna la lista degli step
            self.update_steps_list()
            
            # Abilita i pulsanti
            self.save_button.config(state="normal")
            self.send_button.config(state="normal")
            self.discard_button.config(state="normal")
            
            # Resetta lo step selezionato
            self.selected_step_index = None
            self.edit_button.config(state="disabled")
            self.delete_step_button.config(state="disabled")
            self.move_up_button.config(state="disabled")
            self.move_down_button.config(state="disabled")
            
            # Mostra messaggio di conferma
            self.controller.set_status(f"Allenamento '{workout.workout_name}' caricato")
            
        except Exception as e:
            logging.error(f"Errore nel caricamento dell'allenamento: {str(e)}")
            show_error("Errore", 
                     f"Impossibile caricare l'allenamento: {str(e)}", 
                     parent=self)
    
    def new_workout(self):
        """Crea un nuovo allenamento."""
        # Verifica che non ci siano modifiche non salvate
        if self.current_workout_modified:
            if not ask_yes_no("Modifiche non salvate", 
                          "Ci sono modifiche non salvate. Vuoi continuare e perdere le modifiche?", 
                          parent=self):
                return
        
        # Crea un nuovo allenamento
        self.current_workout = Workout("running", "Nuovo allenamento")
        self.current_workout_id = None
        self.current_workout_modified = True
        
        # Imposta i campi
        self.name_var.set(self.current_workout.workout_name)
        self.sport_var.set(self.current_workout.sport_type)
        self.description_var.set(self.current_workout.description or "")
        
        # Aggiorna la lista degli step
        self.update_steps_list()
        
        # Abilita i pulsanti
        self.save_button.config(state="normal")
        self.send_button.config(state="normal")
        self.discard_button.config(state="normal")
        
        # Resetta lo step selezionato
        self.selected_step_index = None
        self.edit_button.config(state="disabled")
        self.delete_step_button.config(state="disabled")
        self.move_up_button.config(state="disabled")
        self.move_down_button.config(state="disabled")
        
        # Mostra messaggio di conferma
        self.controller.set_status("Nuovo allenamento creato")
    
    def update_steps_list(self):
        """Aggiorna la lista degli step dell'allenamento corrente."""
        # Pulisci il contenitore degli step
        for widget in self.steps_container.winfo_children():
            widget.destroy()
        
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            ttk.Label(self.steps_container, text="Nessun allenamento selezionato").pack()
            return
        
        # Verifica che ci siano step
        if not self.current_workout.workout_steps:
            ttk.Label(self.steps_container, text="L'allenamento non ha step").pack()
            return
        
        # Crea i widget per gli step
        for i, step in enumerate(self.current_workout.workout_steps):
            self.create_step_widget(self.steps_container, step, i)
    
    def create_step_widget(self, parent, step, index, indent=0):
        """
        Crea un widget per uno step.
        
        Args:
            parent: Widget genitore
            step: Step da visualizzare
            index: Indice dello step
            indent: Livello di indentazione (per step nidificati)
        """
        # Crea un frame per lo step
        step_frame = ttk.Frame(parent)
        step_frame.pack(fill=tk.X, padx=(indent * 20, 0), pady=2)
        
        # Colore dello step
        step_color = get_color_for_step(step.step_type, self.config.get('ui.theme', 'light'))
        
        # Crea un frame per il contenuto dello step con sfondo colorato
        content_frame = ttk.Frame(step_frame, style="Card.TFrame")
        content_frame.pack(fill=tk.X)
        
        # Intestazione dello step
        header_frame = ttk.Frame(content_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Icona e tipo di step
        icon = get_icon_for_step(step.step_type)
        ttk.Label(header_frame, text=f"{icon} {step.step_type.capitalize()}", 
                foreground=step_color, font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        # Dettagli dello step
        details_frame = ttk.Frame(content_frame)
        details_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Condizione di fine
        end_condition_text = ""
        
        if step.end_condition == "lap.button":
            end_condition_text = "Fino a pulsante lap"
        elif step.end_condition == "time":
            value = step.end_condition_value
            if isinstance(value, (int, float)):
                # Converti secondi in mm:ss
                seconds = int(value)
                minutes = seconds // 60
                seconds = seconds % 60
                value = f"{minutes}:{seconds:02d}"
            
            end_condition_text = f"Durata: {value}"
        elif step.end_condition == "distance":
            value = step.end_condition_value
            if isinstance(value, (int, float)):
                # Converti metri in m o km
                if value >= 1000:
                    value = f"{value / 1000:.2f}km".replace('.00', '')
                else:
                    value = f"{value}m"
            
            end_condition_text = f"Distanza: {value}"
        elif step.end_condition == "iterations":
            end_condition_text = f"Ripetizioni: {step.end_condition_value}"
        
        ttk.Label(details_frame, text=end_condition_text).pack(side=tk.LEFT)
        
        # Target
        if step.target and step.target.target != "no.target":
            target_text = "Target: "
            
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
                    
                    target_text += f"Passo {min_pace}-{max_pace} min/km"
                
            elif step.target.target == "heart.rate.zone":
                from_value = step.target.from_value
                to_value = step.target.to_value
                
                if from_value and to_value:
                    target_text += f"FC {from_value}-{to_value} bpm"
                
            elif step.target.target == "power.zone":
                from_value = step.target.from_value
                to_value = step.target.to_value
                
                if from_value and to_value:
                    target_text += f"Potenza {from_value}-{to_value} W"
            
            ttk.Label(details_frame, text="  •  " + target_text).pack(side=tk.LEFT)
        
        # Descrizione
        if step.description:
            ttk.Label(details_frame, text=f"  •  {step.description}").pack(side=tk.LEFT)
        
        # Step ripetizioni
        if step.step_type == "repeat" and step.workout_steps:
            # Crea un frame per gli step figli
            child_frame = ttk.Frame(parent)
            child_frame.pack(fill=tk.X, padx=(indent * 20 + 20, 0), pady=0)
            
            # Crea i widget per gli step figli
            for i, child_step in enumerate(step.workout_steps):
                self.create_step_widget(child_frame, child_step, -1, indent + 1)
        
        # Associa eventi
        content_frame.bind("<Button-1>", lambda e, idx=index: self.on_step_selected(idx))
        header_frame.bind("<Button-1>", lambda e, idx=index: self.on_step_selected(idx))
        details_frame.bind("<Button-1>", lambda e, idx=index: self.on_step_selected(idx))
        
        # Doppio click per modificare
        content_frame.bind("<Double-1>", lambda e: self.edit_step())
        header_frame.bind("<Double-1>", lambda e: self.edit_step())
        details_frame.bind("<Double-1>", lambda e: self.edit_step())

    def add_step(self):
        """Aggiunge un nuovo step all'allenamento corrente."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
         return
        
        # Importa qui per evitare import circolari
        from gui.dialogs.workout_step import WorkoutStepDialog
        
        # Callback per l'aggiunta dello step
        def on_step_added(step):
         # Aggiungi lo step all'allenamento
         self.current_workout.add_step(step)
         
         # Segna come modificato
         self.current_workout_modified = True
         
         # Aggiorna la lista degli step
         self.update_steps_list()
        
        # Crea il dialog
        dialog = WorkoutStepDialog(self, callback=on_step_added, sport_type=self.sport_var.get())
    
    def add_repeat(self):
        """Aggiunge un nuovo gruppo di ripetizioni all'allenamento corrente."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Importa qui per evitare import circolari
        from gui.dialogs.repeat_step import RepeatStepDialog
        
        # Callback per l'aggiunta del gruppo
        def on_repeat_added(repeat_step):
            # Aggiungi lo step all'allenamento
            self.current_workout.add_step(repeat_step)
            
            # Segna come modificato
            self.current_workout_modified = True
            
            # Aggiorna la lista degli step
            self.update_steps_list()
        
        # Crea il dialog
        dialog = RepeatStepDialog(self, callback=on_repeat_added, sport_type=self.sport_var.get())
    
    def edit_step(self):
        """Modifica lo step selezionato."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None:
            return
        
        # Ottieni lo step
        step = self.current_workout.workout_steps[self.selected_step_index]
        
        # Verifica il tipo di step
        if step.step_type == "repeat":
            # Importa qui per evitare import circolari
            from gui.dialogs.repeat_step import RepeatStepDialog
            
            # Callback per l'aggiornamento dello step
            def on_repeat_updated(repeat_step):
                # Aggiorna lo step
                self.current_workout.workout_steps[self.selected_step_index] = repeat_step
                
                # Segna come modificato
                self.current_workout_modified = True
                
                # Aggiorna la lista degli step
                self.update_steps_list()
            
            # Crea il dialog
            dialog = RepeatStepDialog(self, repeat_step=step, callback=on_repeat_updated, 
                                     sport_type=self.sport_var.get())
        else:
            # Importa qui per evitare import circolari
            from gui.dialogs.workout_step import WorkoutStepDialog
            
            # Callback per l'aggiornamento dello step
            def on_step_updated(updated_step):
                # Aggiorna lo step
                self.current_workout.workout_steps[self.selected_step_index] = updated_step
                
                # Segna come modificato
                self.current_workout_modified = True
                
                # Aggiorna la lista degli step
                self.update_steps_list()
            
            # Crea il dialog
            dialog = WorkoutStepDialog(self, step=step, callback=on_step_updated, 
                                     sport_type=self.sport_var.get())
    
    def delete_step(self):
        """Elimina lo step selezionato."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None:
            return
        
        # Chiedi conferma
        step = self.current_workout.workout_steps[self.selected_step_index]
        if not ask_yes_no("Conferma eliminazione", 
                       f"Sei sicuro di voler eliminare questo step?", 
                       parent=self):
            return
        
        # Elimina lo step
        del self.current_workout.workout_steps[self.selected_step_index]
        
        # Segna come modificato
        self.current_workout_modified = True
        
        # Aggiorna la lista degli step
        self.update_steps_list()
        
        # Resetta lo step selezionato
        self.selected_step_index = None
        self.edit_button.config(state="disabled")
        self.delete_step_button.config(state="disabled")
        self.move_up_button.config(state="disabled")
        self.move_down_button.config(state="disabled")
    
    def move_step_up(self):
        """Sposta lo step selezionato verso l'alto."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None or self.selected_step_index == 0:
            return
        
        # Scambia gli step
        self.current_workout.workout_steps[self.selected_step_index], self.current_workout.workout_steps[self.selected_step_index - 1] = \
            self.current_workout.workout_steps[self.selected_step_index - 1], self.current_workout.workout_steps[self.selected_step_index]
        
        # Aggiorna l'indice selezionato
        self.selected_step_index -= 1
        
        # Segna come modificato
        self.current_workout_modified = True
        
        # Aggiorna la lista degli step
        self.update_steps_list()
    
    def move_step_down(self):
        """Sposta lo step selezionato verso il basso."""
        # Verifica che sia selezionato uno step
        if self.selected_step_index is None or self.selected_step_index >= len(self.current_workout.workout_steps) - 1:
            return
        
        # Scambia gli step
        self.current_workout.workout_steps[self.selected_step_index], self.current_workout.workout_steps[self.selected_step_index + 1] = \
            self.current_workout.workout_steps[self.selected_step_index + 1], self.current_workout.workout_steps[self.selected_step_index]
        
        # Aggiorna l'indice selezionato
        self.selected_step_index += 1
        
        # Segna come modificato
        self.current_workout_modified = True
        
        # Aggiorna la lista degli step
        self.update_steps_list()
    
    def save_workout(self):
        """Salva le modifiche all'allenamento corrente."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Aggiorna i dati dell'allenamento dai campi
        self.current_workout.workout_name = self.name_var.get()
        self.current_workout.sport_type = self.sport_var.get()
        self.current_workout.description = self.description_var.get()
        
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Aggiorna o crea l'allenamento su Garmin Connect
            if self.current_workout_id:
                # Aggiorna l'allenamento esistente
                response = self.garmin_client.update_workout(self.current_workout_id, self.current_workout)
            else:
                # Crea un nuovo allenamento
                response = self.garmin_client.add_workout(self.current_workout)
                
                # Ottieni l'ID del nuovo allenamento
                if response and 'workoutId' in response:
                    self.current_workout_id = str(response['workoutId'])
            
            # Resetta il flag di modifica
            self.current_workout_modified = False
            
            # Aggiorna la lista degli allenamenti
            self.refresh_workouts()
            
            # Mostra messaggio di conferma
            show_info("Allenamento salvato", 
                   f"L'allenamento '{self.current_workout.workout_name}' è stato salvato su Garmin Connect", 
                   parent=self)
            
        except Exception as e:
            logging.error(f"Errore nel salvataggio dell'allenamento: {str(e)}")
            show_error("Errore", 
                     f"Impossibile salvare l'allenamento: {str(e)}", 
                     parent=self)
    
    def send_to_garmin(self):
        """Invia l'allenamento corrente a Garmin Connect."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Aggiorna i dati dell'allenamento dai campi
        self.current_workout.workout_name = self.name_var.get()
        self.current_workout.sport_type = self.sport_var.get()
        self.current_workout.description = self.description_var.get()
        
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Crea un nuovo allenamento
            response = self.garmin_client.add_workout(self.current_workout)
            
            # Ottieni l'ID del nuovo allenamento
            if response and 'workoutId' in response:
                workout_id = str(response['workoutId'])
                
                # Aggiorna l'ID corrente solo se è un nuovo allenamento
                if not self.current_workout_id:
                    self.current_workout_id = workout_id
                
                # Resetta il flag di modifica
                self.current_workout_modified = False
                
                # Aggiorna la lista degli allenamenti
                self.refresh_workouts()
                
                # Mostra messaggio di conferma
                show_info("Allenamento inviato", 
                       f"L'allenamento '{self.current_workout.workout_name}' è stato inviato a Garmin Connect", 
                       parent=self)
            else:
                raise ValueError("Risposta non valida da Garmin Connect")
            
        except Exception as e:
            logging.error(f"Errore nell'invio dell'allenamento: {str(e)}")
            show_error("Errore", 
                     f"Impossibile inviare l'allenamento: {str(e)}", 
                     parent=self)
    
    def discard_changes(self):
        """Annulla le modifiche all'allenamento corrente."""
        # Verifica che ci sia un allenamento corrente e modifiche
        if not self.current_workout or not self.current_workout_modified:
            return
        
        # Chiedi conferma
        if not ask_yes_no("Conferma", 
                       "Sei sicuro di voler annullare le modifiche?", 
                       parent=self):
            return
        
        # Se è un allenamento esistente, ricaricalo
        if self.current_workout_id:
            try:
                # Ottieni i dettagli dell'allenamento
                workout_data = self.garmin_client.get_workout(self.current_workout_id)
                
                # Importa l'allenamento
                from services.garmin_service import GarminService
                service = GarminService(self.garmin_client)
                
                workout = service.import_workout(workout_data)
                
                # Imposta l'allenamento corrente
                self.current_workout = workout
                self.current_workout_modified = False
                
                # Aggiorna i campi
                self.name_var.set(workout.workout_name)
                self.sport_var.set(workout.sport_type)
                self.description_var.set(workout.description or "")
                
                # Aggiorna la lista degli step
                self.update_steps_list()
                
            except Exception as e:
                logging.error(f"Errore nel recupero dell'allenamento: {str(e)}")
                show_error("Errore", 
                         f"Impossibile recuperare l'allenamento: {str(e)}", 
                         parent=self)
        else:
            # È un nuovo allenamento, crea uno vuoto
            self.new_workout()
    
    def delete_workout(self):
        """Elimina l'allenamento selezionato da Garmin Connect."""
        # Verifica che sia selezionato un allenamento
        selection = self.workout_tree.selection()
        if not selection:
            return
        
        # Ottieni l'ID dell'allenamento
        item = selection[0]
        workout_id = self.workout_tree.item(item, "tags")[0]
        
        # Ottieni il nome dell'allenamento
        values = self.workout_tree.item(item, "values")
        name = values[0]
        
        # Chiedi conferma
        if not ask_yes_no("Conferma eliminazione", 
                       f"Sei sicuro di voler eliminare l'allenamento '{name}'?", 
                       parent=self):
            return
        
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Elimina l'allenamento
            self.garmin_client.delete_workout(workout_id)
            
            # Se è l'allenamento corrente, resettalo
            if self.current_workout_id == workout_id:
                self.current_workout = None
                self.current_workout_id = None
                self.current_workout_modified = False
                
                # Pulisci i campi
                self.name_var.set("")
                self.sport_var.set("running")
                self.description_var.set("")
                
                # Aggiorna la lista degli step
                self.update_steps_list()
                
                # Disabilita i pulsanti
                self.save_button.config(state="disabled")
                self.send_button.config(state="disabled")
                self.discard_button.config(state="disabled")
            
            # Aggiorna la lista degli allenamenti
            self.refresh_workouts()
            
            # Mostra messaggio di conferma
            show_info("Allenamento eliminato", 
                   f"L'allenamento '{name}' è stato eliminato da Garmin Connect", 
                   parent=self)
            
        except Exception as e:
            logging.error(f"Errore nell'eliminazione dell'allenamento: {str(e)}")
            show_error("Errore", 
                     f"Impossibile eliminare l'allenamento: {str(e)}", 
                     parent=self)
    
    def schedule_workouts_dialog(self):
        """Mostra il dialog per la pianificazione degli allenamenti."""
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Ottieni la lista degli allenamenti
            workouts_data = self.garmin_client.list_workouts()
            
            # Trasforma in una lista di tuple (nome, workout)
            workouts = []
            
            # Per ogni allenamento
            for workout_data in workouts_data:
                # Importa l'allenamento
                from services.garmin_service import GarminService
                service = GarminService(self.garmin_client)
                
                workout = service.import_workout(workout_data)
                
                if workout:
                    workouts.append((workout.workout_name, workout))
            
            # Crea il dialog
            from gui.planning import ScheduleDialog
            
            dialog = ScheduleDialog(self, workouts)
            self.wait_window(dialog)
            
            # Se ci sono allenamenti pianificati, chiedi se inviarli a Garmin Connect
            if hasattr(dialog, 'scheduled_workouts') and dialog.scheduled_workouts:
                if ask_yes_no("Pianificazione completata", 
                          f"Pianificati {len(dialog.scheduled_workouts)} allenamenti. Vuoi inviarli a Garmin Connect?", 
                          parent=self):
                    self.send_scheduled_workouts(dialog.scheduled_workouts)
            
        except Exception as e:
            logging.error(f"Errore nella pianificazione degli allenamenti: {str(e)}")
            show_error("Errore", 
                     f"Impossibile pianificare gli allenamenti: {str(e)}", 
                     parent=self)
    
    def send_scheduled_workouts(self, scheduled_workouts):
        """
        Invia gli allenamenti pianificati a Garmin Connect.
        
        Args:
            scheduled_workouts: Lista di tuple (nome, workout) con le date pianificate
        """
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Per ogni allenamento
            for name, workout in scheduled_workouts:
                # Estrai la data
                date = None
                for step in workout.workout_steps:
                    if hasattr(step, 'date') and step.date:
                        date = step.date
                        break
                
                if not date:
                    continue
                
                # Invia l'allenamento
                response = self.garmin_client.add_workout(workout)
                
                # Ottieni l'ID del nuovo allenamento
                if response and 'workoutId' in response:
                    workout_id = str(response['workoutId'])
                    
                    # Pianifica l'allenamento
                    self.garmin_client.schedule_workout(workout_id, date)
            
            # Aggiorna la lista degli allenamenti
            self.refresh_workouts()
            
            # Mostra messaggio di conferma
            show_info("Allenamenti pianificati", 
                   f"Gli allenamenti sono stati pianificati su Garmin Connect", 
                   parent=self)
            
        except Exception as e:
            logging.error(f"Errore nell'invio degli allenamenti pianificati: {str(e)}")
            show_error("Errore", 
                     f"Impossibile inviare gli allenamenti pianificati: {str(e)}", 
                     parent=self)
    
    def sync_with_garmin(self):
        """Sincronizza gli allenamenti con Garmin Connect."""
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        # Aggiorna la lista degli allenamenti
        self.refresh_workouts()
    
    def on_login(self, client: GarminClient):
        """
        Gestisce l'evento di login.
        
        Args:
            client: Client Garmin
        """
        self.garmin_client = client
        
        # Abilita i pulsanti
        self.refresh_button.config(state="normal")
        
        # Aggiorna la lista degli allenamenti
        self.refresh_workouts()
    
    def on_logout(self):
        """Gestisce l'evento di logout."""
        self.garmin_client = None
        
        # Disabilita i pulsanti
        self.refresh_button.config(state="disabled")
        
        # Pulisci la lista degli allenamenti
        self.workouts = []
        self.update_workout_list()
        
        # Pulisci l'allenamento corrente
        self.current_workout = None
        self.current_workout_id = None
        self.current_workout_modified = False
        
        # Pulisci i campi
        self.name_var.set("")
        self.sport_var.set("running")
        self.description_var.set("")
        
        # Aggiorna la lista degli step
        self.update_steps_list()
        
        # Disabilita i pulsanti
        self.save_button.config(state="disabled")
        self.send_button.config(state="disabled")
        self.discard_button.config(state="disabled")
    
    def on_activate(self):
        """Chiamato quando il frame viene attivato."""
        pass


if __name__ == "__main__":
    # Test del frame
    root = tk.Tk()
    root.title("Workout Editor Test")
    root.geometry("1200x800")
    
    # Crea un notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Crea il frame
    frame = WorkoutEditorFrame(notebook, None)
    notebook.add(frame, text="Editor Allenamenti")
    
    root.mainloop()