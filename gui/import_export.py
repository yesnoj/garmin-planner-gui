#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Frame per l'importazione e l'esportazione di allenamenti.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Dict, Any, List, Tuple, Optional, Callable

from config import get_config
from auth import GarminClient
from models.workout import Workout
from services.yaml_service import YamlService
from services.excel_service import ExcelService
from services.garmin_service import GarminService
from gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no,
    create_scrollable_frame
)
from gui.styles import get_icon_for_sport


class ImportExportFrame(ttk.Frame):
    """Frame per l'importazione e l'esportazione di allenamenti."""
    
    def __init__(self, parent: ttk.Notebook, controller):
        """
        Inizializza il frame di importazione/esportazione.
        
        Args:
            parent: Widget genitore (notebook)
            controller: Controller principale dell'applicazione
        """
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.config = get_config()
        self.garmin_client = None
        self.garmin_service = None
        
        # Variabili
        self.imported_workouts = []  # Lista di tuple (nome, allenamento)
        
        # Creazione dei widget
        self.create_widgets()
    
    def create_widgets(self):
        """Crea i widget del frame."""
        # Frame principale
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pannello diviso: opzioni a sinistra, preview a destra
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Frame sinistro per le opzioni
        left_frame = ttk.Frame(paned, padding=5)
        paned.add(left_frame, weight=1)
        
        # Frame destro per la preview
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(right_frame, weight=2)
        
        # --- Parte sinistra: Opzioni e controlli ---
        
        # Importazione
        import_frame = ttk.LabelFrame(left_frame, text="Importazione")
        import_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Importa da YAML
        yaml_button = ttk.Button(import_frame, text="Importa da YAML...", 
                               command=self.import_yaml)
        yaml_button.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        create_tooltip(yaml_button, "Importa allenamenti da un file YAML")
        
        # Importa da Excel
        excel_button = ttk.Button(import_frame, text="Importa da Excel...", 
                                command=self.import_excel)
        excel_button.pack(fill=tk.X, padx=10, pady=5)
        
        create_tooltip(excel_button, "Importa allenamenti da un file Excel")
        
        # Importa da Garmin Connect
        self.garmin_import_button = ttk.Button(import_frame, text="Importa da Garmin Connect", 
                                            command=self.import_from_garmin,
                                            state="disabled")
        self.garmin_import_button.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        create_tooltip(self.garmin_import_button, "Importa allenamenti da Garmin Connect")
        
        # Esportazione
        export_frame = ttk.LabelFrame(left_frame, text="Esportazione")
        export_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Esporta in YAML
        yaml_export_button = ttk.Button(export_frame, text="Esporta in YAML...", 
                                      command=self.export_yaml)
        yaml_export_button.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        create_tooltip(yaml_export_button, "Esporta allenamenti in un file YAML")
        
        # Esporta in Excel
        excel_export_button = ttk.Button(export_frame, text="Esporta in Excel...", 
                                       command=self.export_excel)
        excel_export_button.pack(fill=tk.X, padx=10, pady=5)
        
        create_tooltip(excel_export_button, "Esporta allenamenti in un file Excel")
        
        # Crea esempio Excel
        excel_example_button = ttk.Button(export_frame, text="Crea Esempio Excel...", 
                                        command=self.create_excel_example)
        excel_example_button.pack(fill=tk.X, padx=10, pady=5)
        
        create_tooltip(excel_example_button, "Crea un file Excel di esempio che può essere modificato e importato")
        
        # Esporta in Garmin Connect
        self.garmin_export_button = ttk.Button(export_frame, text="Esporta in Garmin Connect", 
                                             command=self.export_to_garmin,
                                             state="disabled")
        self.garmin_export_button.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        create_tooltip(self.garmin_export_button, "Esporta allenamenti in Garmin Connect")
        
        # Configurazione
        config_frame = ttk.LabelFrame(left_frame, text="Configurazione")
        config_frame.pack(fill=tk.X)
        
        # Prefisso per i nomi degli allenamenti
        prefix_frame = ttk.Frame(config_frame)
        prefix_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(prefix_frame, text="Prefisso:").pack(side=tk.LEFT)
        
        self.prefix_var = tk.StringVar(value=self.config.get('planning.name_prefix', ''))
        prefix_entry = ttk.Entry(prefix_frame, textvariable=self.prefix_var, width=20)
        prefix_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        create_tooltip(prefix_entry, "Prefisso per i nomi degli allenamenti")
        
        # Pulsante per salvare la configurazione
        save_config_button = ttk.Button(config_frame, text="Salva configurazione", 
                                      command=self.save_configuration)
        save_config_button.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # --- Parte destra: Preview e selezione ---
        
        # Lista degli allenamenti importati o disponibili
        workouts_frame = ttk.LabelFrame(right_frame, text="Allenamenti disponibili")
        workouts_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Filtro
        filter_frame = ttk.Frame(workouts_frame)
        filter_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(filter_frame, text="Filtro:").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=20)
        filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Associa evento di modifica del filtro
        self.filter_var.trace_add("write", lambda *args: self.update_workout_list())
        
        # Lista degli allenamenti
        list_frame = ttk.Frame(workouts_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Crea il treeview
        columns = ("name", "sport", "steps")
        self.workout_tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                                      selectmode="extended")
        
        # Intestazioni
        self.workout_tree.heading("name", text="Nome")
        self.workout_tree.heading("sport", text="Sport")
        self.workout_tree.heading("steps", text="Step")
        
        # Larghezze colonne
        self.workout_tree.column("name", width=300)
        self.workout_tree.column("sport", width=100)
        self.workout_tree.column("steps", width=50)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.workout_tree.yview)
        self.workout_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.workout_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Pulsanti per la gestione della selezione
        selection_frame = ttk.Frame(right_frame)
        selection_frame.pack(fill=tk.X)
        
        self.select_all_button = ttk.Button(selection_frame, text="Seleziona tutti", 
                                         command=self.select_all_workouts)
        self.select_all_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.deselect_all_button = ttk.Button(selection_frame, text="Deseleziona tutti", 
                                           command=self.deselect_all_workouts)
        self.deselect_all_button.pack(side=tk.LEFT)
        
        self.delete_button = ttk.Button(selection_frame, text="Elimina selezionati", 
                                     command=self.delete_selected_workouts)
        self.delete_button.pack(side=tk.RIGHT)
        
        # Dettagli dell'allenamento selezionato
        details_frame = ttk.LabelFrame(right_frame, text="Dettagli")
        details_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Frame per i dettagli
        self.details_content = ttk.Frame(details_frame)
        self.details_content.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(self.details_content, text="Seleziona un allenamento per vedere i dettagli").pack()
        
        # Associa evento di selezione
        self.workout_tree.bind("<<TreeviewSelect>>", self.on_workout_selected)
        self.workout_tree.bind("<Double-1>", lambda e: self.show_workout_details())
    
    def create_excel_example(self):
        """Crea un file Excel di esempio che può essere modificato e importato."""
        # Chiedi dove salvare il file
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Salva file esempio Excel",
            filetypes=[("Excel files", "*.xlsx"), ("Tutti i file", "*.*")],
            defaultextension=".xlsx"
        )
        
        if not file_path:
            return
        
        try:
            from services.excel_service import ExcelService
            from models.workout import Workout, WorkoutStep, Target
            
            # Crea esempi di allenamenti
            example_workouts = []
            
            # Esempio 1: Corsa lunga
            workout1 = Workout("running", "W1D2 - Corsa lunga", "Corsa lunga a ritmo lento")
            
            # Aggiungi step per data
            date_step = WorkoutStep(0, "warmup")
            date_step.date = "2025-01-05"  # Esempio di data
            workout1.add_step(date_step)
            
            # Aggiungi step riscaldamento
            warmup = WorkoutStep(0, "warmup", "Inizia lentamente", "time", 10*60)
            warmup.target = Target("pace.zone", 2.7, 2.5)  # ~ Z2
            warmup.target.target_zone_name = "Z2"
            workout1.add_step(warmup)
            
            # Aggiungi step principale
            main = WorkoutStep(0, "interval", "Mantieni un ritmo costante", "distance", 10000)
            main.target = Target("pace.zone", 2.9, 2.7)  # ~ Z3
            main.target.target_zone_name = "Z3"
            workout1.add_step(main)
            
            # Aggiungi step defaticamento
            cooldown = WorkoutStep(0, "cooldown", "Rallenta gradualmente", "time", 5*60)
            cooldown.target = Target("pace.zone", 2.5, 2.3)  # ~ Z1
            cooldown.target.target_zone_name = "Z1"
            workout1.add_step(cooldown)
            
            # Esempio 2: Interval training
            workout2 = Workout("running", "W1D4 - Interval training", "Allenamento a intervalli ad alta intensità")
            
            # Aggiungi step per data
            date_step = WorkoutStep(0, "warmup")
            date_step.date = "2025-01-07"  # Esempio di data
            workout2.add_step(date_step)
            
            # Aggiungi step riscaldamento
            warmup2 = WorkoutStep(0, "warmup", "Riscaldamento", "time", 10*60)
            warmup2.target = Target("pace.zone", 2.7, 2.5)  # ~ Z2
            warmup2.target.target_zone_name = "Z2"
            workout2.add_step(warmup2)
            
            # Crea un gruppo di ripetizioni
            repeat = WorkoutStep(0, "repeat", "", "iterations", 5)
            
            # Aggiungi interval ad alta intensità
            interval = WorkoutStep(0, "interval", "Ad alta intensità", "distance", 400)
            interval.target = Target("pace.zone", 3.4, 3.2)  # ~ Z4
            interval.target.target_zone_name = "Z4"
            repeat.add_step(interval)
            
            # Aggiungi recupero
            recovery = WorkoutStep(0, "recovery", "Recupero attivo", "distance", 200)
            recovery.target = Target("pace.zone", 2.5, 2.3)  # ~ Z1
            recovery.target.target_zone_name = "Z1"
            repeat.add_step(recovery)
            
            # Aggiungi il gruppo di ripetizioni all'allenamento
            workout2.add_step(repeat)
            
            # Aggiungi defaticamento
            cooldown2 = WorkoutStep(0, "cooldown", "Defaticamento", "time", 5*60)
            cooldown2.target = Target("pace.zone", 2.5, 2.3)  # ~ Z1
            cooldown2.target.target_zone_name = "Z1"
            workout2.add_step(cooldown2)
            
            # Esempio 3: Allenamento in bici
            workout3 = Workout("cycling", "W1D5 - Soglia ciclismo", "Allenamento di soglia per ciclismo")
            
            # Aggiungi step per data
            date_step = WorkoutStep(0, "warmup")
            date_step.date = "2025-01-08"  # Esempio di data
            workout3.add_step(date_step)
            
            # Aggiungi step riscaldamento
            warmup3 = WorkoutStep(0, "warmup", "Riscaldamento progressivo", "time", 15*60)
            warmup3.target = Target("power.zone", 175, 125)  # Z1
            warmup3.target.target_zone_name = "Z1"
            workout3.add_step(warmup3)
            
            # Crea un gruppo di ripetizioni
            repeat3 = WorkoutStep(0, "repeat", "", "iterations", 3)
            
            # Aggiungi interval a soglia
            interval3 = WorkoutStep(0, "interval", "Intervallo a soglia", "time", 8*60)
            interval3.target = Target("power.zone", 265, 235)  # threshold
            interval3.target.target_zone_name = "threshold"
            repeat3.add_step(interval3)
            
            # Aggiungi recupero
            recovery3 = WorkoutStep(0, "recovery", "Recupero", "time", 4*60)
            recovery3.target = Target("power.zone", 175, 125)  # Z1
            recovery3.target.target_zone_name = "Z1"
            repeat3.add_step(recovery3)
            
            # Aggiungi il gruppo di ripetizioni all'allenamento
            workout3.add_step(repeat3)
            
            # Aggiungi defaticamento
            cooldown3 = WorkoutStep(0, "cooldown", "Defaticamento", "time", 10*60)
            cooldown3.target = Target("power.zone", 175, 125)  # Z1
            cooldown3.target.target_zone_name = "Z1"
            workout3.add_step(cooldown3)
            
            # Aggiungi gli allenamenti all'elenco degli esempi
            example_workouts.extend([
                ("W1D2 - Corsa lunga", workout1),
                ("W1D4 - Interval training", workout2),
                ("W1D5 - Soglia ciclismo", workout3)
            ])
            
            # Esporta gli allenamenti in formato Excel
            custom_config = {
                'athlete_name': 'Atleta Esempio',
                'name_prefix': 'Piano esempio',
                'race_day': '06/06/2025',  # Formato GG/MM/AAAA
                'preferred_days': [0, 2, 4]  # Lunedì, Mercoledì, Venerdì
            }
            
            ExcelService.export_workouts(example_workouts, file_path, custom_config)
            
            # Mostra messaggio di conferma
            show_info("Esempio creato", 
                    f"File Excel di esempio creato con successo in {file_path}", 
                    parent=self)
            
        except Exception as e:
            logging.error(f"Errore nella creazione del file Excel di esempio: {str(e)}")
            show_error("Errore", 
                     f"Impossibile creare il file Excel di esempio: {str(e)}", 
                     parent=self)

    def update_workout_list(self):
        """Aggiorna la lista degli allenamenti disponibili."""
        # Ottieni il filtro
        filter_text = self.filter_var.get().lower()
        
        # Pulisci la lista attuale
        for item in self.workout_tree.get_children():
            self.workout_tree.delete(item)
        
        # Filtra gli allenamenti
        filtered_workouts = []
        for name, workout in self.imported_workouts:
            # Applica il filtro
            if filter_text and filter_text not in name.lower():
                continue
            
            # Aggiungi all'elenco filtrato
            filtered_workouts.append((name, workout))
        
        # Aggiungi gli allenamenti filtrati alla lista
        for i, (name, workout) in enumerate(filtered_workouts):
            # Icona in base al tipo di sport
            sport_icon = get_icon_for_sport(workout.sport_type)
            
            # Conta gli step
            step_count = len(workout.workout_steps)
            
            # Aggiungi alla lista
            self.workout_tree.insert("", "end", 
                                  values=(name, f"{sport_icon} {workout.sport_type}", step_count), 
                                  tags=(str(i)))
    
    def on_workout_selected(self, event):
        """
        Gestisce la selezione di un allenamento nella lista.
        
        Args:
            event: Evento Tkinter
        """
        # Ottieni gli item selezionati
        selection = self.workout_tree.selection()
        
        # Aggiorna i pulsanti
        if selection:
            self.delete_button.config(state="normal")
            
            # Se è selezionato un solo allenamento, mostra i dettagli
            if len(selection) == 1:
                item = selection[0]
                index = int(self.workout_tree.item(item, "tags")[0])
                name, workout = self.imported_workouts[index]
                
                # Mostra i dettagli
                self.show_workout_details(workout)
            else:
                # Pulisci i dettagli
                for widget in self.details_content.winfo_children():
                    widget.destroy()
                
                ttk.Label(self.details_content, 
                        text=f"Selezionati {len(selection)} allenamenti").pack()
        else:
            self.delete_button.config(state="disabled")
            
            # Pulisci i dettagli
            for widget in self.details_content.winfo_children():
                widget.destroy()
            
            ttk.Label(self.details_content, 
                    text="Seleziona un allenamento per vedere i dettagli").pack()
    
    def show_workout_details(self, workout=None):
        """
        Mostra i dettagli di un allenamento.
        
        Args:
            workout: Allenamento di cui mostrare i dettagli (opzionale)
        """
        # Se non è specificato un allenamento, usa quello selezionato
        if not workout:
            selection = self.workout_tree.selection()
            if not selection or len(selection) != 1:
                return
            
            item = selection[0]
            index = int(self.workout_tree.item(item, "tags")[0])
            name, workout = self.imported_workouts[index]
        
        # Pulisci i dettagli precedenti
        for widget in self.details_content.winfo_children():
            widget.destroy()
        
        # Mostra i dettagli dell'allenamento
        # Nome e tipo di sport
        header_frame = ttk.Frame(self.details_content)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Icona in base al tipo di sport
        sport_icon = get_icon_for_sport(workout.sport_type)
        
        ttk.Label(header_frame, text=f"{sport_icon} {workout.workout_name}", 
                style="Heading.TLabel").pack(side=tk.LEFT)
        
        ttk.Label(header_frame, text=f"Sport: {workout.sport_type.capitalize()}", 
                style="Subtitle.TLabel").pack(side=tk.RIGHT)

        # Descrizione
        if workout.description:
            desc_frame = ttk.LabelFrame(self.details_content, text="Descrizione")
            desc_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(desc_frame, text=workout.description, 
                    wraplength=400).pack(padx=10, pady=5)
        
        # Step
        steps_frame = ttk.LabelFrame(self.details_content, text="Step")
        steps_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea il treeview per gli step
        columns = ("order", "type", "condition", "value", "description")
        steps_tree = ttk.Treeview(steps_frame, columns=columns, show="headings")
        
        # Intestazioni
        steps_tree.heading("order", text="#")
        steps_tree.heading("type", text="Tipo")
        steps_tree.heading("condition", text="Condizione")
        steps_tree.heading("value", text="Valore")
        steps_tree.heading("description", text="Descrizione")
        
        # Larghezze colonne
        steps_tree.column("order", width=30)
        steps_tree.column("type", width=80)
        steps_tree.column("condition", width=100)
        steps_tree.column("value", width=120)
        steps_tree.column("description", width=200)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(steps_frame, orient=tk.VERTICAL, command=steps_tree.yview)
        steps_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        steps_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # Aggiungi gli step
        self._add_steps_to_tree(steps_tree, "", workout.workout_steps)
    
    def _add_steps_to_tree(self, tree, parent_id, steps):
        """
        Aggiunge gli step a un treeview.
        
        Args:
            tree: Treeview
            parent_id: ID del genitore (stringa vuota per il livello root)
            steps: Lista degli step da aggiungere
        """
        for i, step in enumerate(steps):
            # Formatta i dati
            order = step.order
            step_type = step.step_type.capitalize()
            
            # Condizione di fine
            end_condition = ""
            if step.end_condition == "lap.button":
                end_condition = "Pulsante lap"
            elif step.end_condition == "time":
                end_condition = "Tempo"
            elif step.end_condition == "distance":
                end_condition = "Distanza"
            elif step.end_condition == "iterations":
                end_condition = "Ripetizioni"
            
            # Valore della condizione
            end_value = ""
            if step.end_condition == "time" and step.end_condition_value:
                # Formatta il tempo in minuti:secondi
                if isinstance(step.end_condition_value, (int, float)):
                    seconds = int(step.end_condition_value)
                    minutes = seconds // 60
                    seconds = seconds % 60
                    end_value = f"{minutes}:{seconds:02d} min"
                else:
                    end_value = str(step.end_condition_value)
            elif step.end_condition == "distance" and step.end_condition_value:
                # Formatta la distanza
                if isinstance(step.end_condition_value, (int, float)):
                    if step.end_condition_value >= 1000:
                        end_value = f"{step.end_condition_value / 1000:.1f} km"
                    else:
                        end_value = f"{int(step.end_condition_value)} m"
                else:
                    end_value = str(step.end_condition_value)
            elif step.end_condition == "iterations" and step.end_condition_value:
                end_value = f"{step.end_condition_value} x"
            else:
                end_value = str(step.end_condition_value) if step.end_condition_value else ""
            
            # Target
            if step.target and step.target.target != "no.target":
                target_text = ""
                if hasattr(step.target, 'target_zone_name') and step.target.target_zone_name:
                    target_text = f" @ {step.target.target_zone_name}"
                elif step.target.target == "pace.zone" and step.target.from_value and step.target.to_value:
                    # Calcola i valori di passo
                    min_pace_secs = int(1000 / step.target.from_value)
                    max_pace_secs = int(1000 / step.target.to_value)
                    
                    min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                    max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                    
                    target_text = f" @ {min_pace}-{max_pace}"
                elif step.target.target == "heart.rate.zone" and step.target.from_value and step.target.to_value:
                    target_text = f" @ {step.target.from_value}-{step.target.to_value} bpm"
                elif step.target.target == "power.zone" and step.target.from_value and step.target.to_value:
                    target_text = f" @ {step.target.from_value}-{step.target.to_value} W"
                
                if target_text:
                    end_value += target_text
            
            # Descrizione
            description = step.description
            
            # Aggiungi lo step
            item_id = tree.insert(parent_id, "end", 
                               values=(order, step_type, end_condition, end_value, description))
            
            # Se è un repeat, aggiungi gli step figli
            if step.step_type == "repeat" and step.workout_steps:
                self._add_steps_to_tree(tree, item_id, step.workout_steps)
    
    def select_all_workouts(self):
        """Seleziona tutti gli allenamenti nella lista."""
        for item in self.workout_tree.get_children():
            self.workout_tree.selection_add(item)
    
    def deselect_all_workouts(self):
        """Deseleziona tutti gli allenamenti nella lista."""
        for item in self.workout_tree.selection():
            self.workout_tree.selection_remove(item)
    
    def delete_selected_workouts(self):
        """Elimina gli allenamenti selezionati."""
        # Ottieni gli item selezionati
        selection = self.workout_tree.selection()
        
        if not selection:
            return
        
        # Chiedi conferma
        if not ask_yes_no("Conferma eliminazione", 
                      f"Sei sicuro di voler eliminare {len(selection)} allenamenti?", 
                      parent=self):
            return
        
        # Ottieni gli indici degli allenamenti selezionati
        indices = []
        for item in selection:
            index = int(self.workout_tree.item(item, "tags")[0])
            indices.append(index)
        
        # Ordina gli indici in ordine decrescente
        indices.sort(reverse=True)
        
        # Elimina gli allenamenti
        for index in indices:
            del self.imported_workouts[index]
        
        # Aggiorna la lista
        self.update_workout_list()
        
        # Pulisci i dettagli
        for widget in self.details_content.winfo_children():
            widget.destroy()
        
        ttk.Label(self.details_content, 
                text="Seleziona un allenamento per vedere i dettagli").pack()
        
        # Disabilita il pulsante di eliminazione
        self.delete_button.config(state="disabled")
    
    def import_yaml(self):
        """Importa allenamenti da un file YAML."""
        # Percorso dell'ultimo import
        last_dir = self.config.get('paths.last_import_dir', '')
        
        # Chiedi il file da importare
        file_path = filedialog.askopenfilename(
            title="Importa allenamenti da YAML",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            initialdir=last_dir
        )
        
        if not file_path:
            return
        
        # Salva il percorso
        self.config.set('paths.last_import_dir', os.path.dirname(file_path))
        self.config.save()
        
        try:
            # Importa gli allenamenti
            imported = YamlService.import_workouts(file_path)
            
            # Aggiungi agli allenamenti importati
            self.imported_workouts.extend(imported)
            
            # Aggiorna la lista
            self.update_workout_list()
            
            # Mostra messaggio di conferma
            show_info("Importazione completata", 
                   f"Importati {len(imported)} allenamenti", 
                   parent=self)
            
            # Aggiorna la barra di stato
            self.controller.set_status(f"Importati {len(imported)} allenamenti da {file_path}")
            
            # Notifica il WorkoutEditorFrame
            if hasattr(self.controller, 'workout_editor'):
                self.controller.workout_editor.on_workouts_imported()
            
        except Exception as e:
            logging.error(f"Errore nell'importazione del file YAML: {str(e)}")
            show_error("Errore", 
                     f"Impossibile importare il file YAML: {str(e)}", 
                     parent=self)
    
    def import_excel(self):
        """Importa allenamenti da un file Excel."""
        # Percorso dell'ultimo import
        last_dir = self.config.get('paths.last_import_dir', '')
        
        # Chiedi il file da importare
        file_path = filedialog.askopenfilename(
            title="Importa allenamenti da Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
            initialdir=last_dir
        )
        
        if not file_path:
            return
        
        # Salva il percorso
        self.config.set('paths.last_import_dir', os.path.dirname(file_path))
        self.config.save()
        
        try:
            # Importa gli allenamenti
            imported = ExcelService.import_workouts(file_path)
            
            # Aggiungi agli allenamenti importati
            self.imported_workouts.extend(imported)
            
            # Aggiorna la lista
            self.update_workout_list()
            
            # Mostra messaggio di conferma
            show_info("Importazione completata", 
                   f"Importati {len(imported)} allenamenti", 
                   parent=self)
            
            # Aggiorna la barra di stato
            self.controller.set_status(f"Importati {len(imported)} allenamenti da {file_path}")
            
            # Notifica il WorkoutEditorFrame
            if hasattr(self.controller, 'workout_editor'):
                self.controller.workout_editor.on_workouts_imported()
            
        except Exception as e:
            logging.error(f"Errore nell'importazione del file Excel: {str(e)}")
            show_error("Errore", 
                     f"Impossibile importare il file Excel: {str(e)}", 
                     parent=self)
    
    def import_from_garmin(self):
        """Importa allenamenti da Garmin Connect."""
        # Verifica che il client Garmin sia disponibile
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Ottieni la lista degli allenamenti
            workouts_data = self.garmin_client.list_workouts()
            
            # Verifica che ci siano allenamenti
            if not workouts_data:
                show_info("Nessun allenamento", 
                        "Non ci sono allenamenti su Garmin Connect", 
                        parent=self)
                return
            
            # Chiedi conferma
            if not ask_yes_no("Conferma importazione", 
                          f"Vuoi importare {len(workouts_data)} allenamenti da Garmin Connect?", 
                          parent=self):
                return
            
            # Mostra un progress dialog
            progress_window = tk.Toplevel(self)
            progress_window.title("Importazione in corso")
            progress_window.geometry("300x100")
            progress_window.transient(self)
            progress_window.grab_set()
            
            # Centra la finestra
            progress_window.update_idletasks()
            width = progress_window.winfo_width()
            height = progress_window.winfo_height()
            x = (progress_window.winfo_screenwidth() // 2) - (width // 2)
            y = (progress_window.winfo_screenheight() // 2) - (height // 2)
            progress_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Frame principale
            progress_frame = ttk.Frame(progress_window, padding=20)
            progress_frame.pack(fill=tk.BOTH, expand=True)
            
            # Messaggio
            message_var = tk.StringVar(value="Importazione in corso...")
            message_label = ttk.Label(progress_frame, textvariable=message_var)
            message_label.pack(pady=(0, 10))
            
            # Progressbar
            progress_var = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
            progress_bar.pack(fill=tk.X)
            
            # Funzione per importare gli allenamenti
            def import_thread():
                try:
                    imported = []
                    
                    # Per ogni allenamento
                    for i, workout_data in enumerate(workouts_data):
                        try:
                            # Aggiorna il messaggio
                            workout_name = workout_data.get('workoutName', 'Allenamento')
                            message_var.set(f"Importazione di '{workout_name}'...")
                            
                            # Aggiorna la progressbar
                            progress_var.set((i + 1) / len(workouts_data) * 100)
                            
                            # Ottieni i dettagli dell'allenamento
                            workout_id = str(workout_data.get('workoutId', ''))
                            detailed_data = self.garmin_client.get_workout(workout_id)
                            
                            if not detailed_data:
                                continue
                            
                            # Importa l'allenamento
                            workout = self.garmin_service.import_workout(detailed_data)
                            
                            if workout:
                                imported.append((workout.workout_name, workout))
                            
                        except Exception as e:
                            logging.error(f"Errore nell'importazione dell'allenamento {workout_id}: {str(e)}")
                    
                    # Aggiungi agli allenamenti importati
                    self.imported_workouts.extend(imported)
                    
                    # Aggiorna la lista
                    self.update_workout_list()
                    
                    # Chiudi la finestra di progresso
                    progress_window.destroy()
                    
                    # Mostra messaggio di conferma
                    show_info("Importazione completata", 
                            f"Importati {len(imported)} allenamenti", 
                            parent=self)
                    
                    # Aggiorna la barra di stato
                    self.controller.set_status(f"Importati {len(imported)} allenamenti da Garmin Connect")
                    
                except Exception as e:
                    logging.error(f"Errore nell'importazione da Garmin Connect: {str(e)}")
                    
                    # Chiudi la finestra di progresso
                    progress_window.destroy()
                    
                    # Mostra messaggio di errore
                    show_error("Errore", 
                             f"Impossibile importare gli allenamenti: {str(e)}", 
                             parent=self)
            
            # Avvia il thread di importazione
            threading.Thread(target=import_thread).start()
            
        except Exception as e:
            logging.error(f"Errore nell'importazione da Garmin Connect: {str(e)}")
            show_error("Errore", 
                     f"Impossibile importare gli allenamenti: {str(e)}", 
                     parent=self)
    
    def export_yaml(self):
        """Esporta allenamenti in un file YAML."""
        # Verifica che ci siano allenamenti da esportare
        if not self.imported_workouts:
            show_error("Errore", "Non ci sono allenamenti da esportare", parent=self)
            return
        
        # Ottieni gli allenamenti selezionati
        selection = self.workout_tree.selection()
        
        # Se non ci sono selezioni, usa tutti gli allenamenti
        selected_workouts = []
        if selection:
            for item in selection:
                index = int(self.workout_tree.item(item, "tags")[0])
                selected_workouts.append(self.imported_workouts[index])
        else:
            selected_workouts = self.imported_workouts
        
        # Percorso dell'ultimo export
        last_dir = self.config.get('paths.last_export_dir', '')
        
        # Chiedi il file da esportare
        file_path = filedialog.asksaveasfilename(
            title="Esporta allenamenti in YAML",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            defaultextension=".yaml",
            initialdir=last_dir
        )
        
        if not file_path:
            return
        
        # Salva il percorso
        self.config.set('paths.last_export_dir', os.path.dirname(file_path))
        self.config.save()
        
        try:
            # Crea un dizionario di configurazione
            config = {
                'name_prefix': self.prefix_var.get()
            }
            
            # Esporta gli allenamenti
            YamlService.export_workouts(selected_workouts, file_path, config)
            

            # Salva la configurazione
            self.config.save()

            # Mostra messaggio di conferma
            show_info("Esportazione completata", 
                   f"Esportati {len(selected_workouts)} allenamenti", 
                   parent=self)
            
            # Aggiorna la barra di stato
            self.controller.set_status(f"Esportati {len(selected_workouts)} allenamenti in {file_path}")
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione in YAML: {str(e)}")
            show_error("Errore", 
                     f"Impossibile esportare in YAML: {str(e)}", 
                     parent=self)
    
    def export_excel(self):
        """Esporta allenamenti in un file Excel."""
        # Verifica che ci siano allenamenti da esportare
        if not self.imported_workouts:
            show_error("Errore", "Non ci sono allenamenti da esportare", parent=self)
            return
        
        # Ottieni gli allenamenti selezionati
        selection = self.workout_tree.selection()
        
        # Se non ci sono selezioni, usa tutti gli allenamenti
        selected_workouts = []
        if selection:
            for item in selection:
                index = int(self.workout_tree.item(item, "tags")[0])
                selected_workouts.append(self.imported_workouts[index])
        else:
            selected_workouts = self.imported_workouts
        
        # Percorso dell'ultimo export
        last_dir = self.config.get('paths.last_export_dir', '')
        
        # Chiedi il file da esportare
        file_path = filedialog.asksaveasfilename(
            title="Esporta allenamenti in Excel",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            defaultextension=".xlsx",
            initialdir=last_dir
        )
        
        if not file_path:
            return
        
        # Salva il percorso
        self.config.set('paths.last_export_dir', os.path.dirname(file_path))
        self.config.save()
        
        try:
            # Esporta gli allenamenti
            ExcelService.export_workouts(selected_workouts, file_path)
            
            # Salva la configurazione
            self.config.save()
            
            # Mostra messaggio di conferma
            show_info("Esportazione completata", 
                   f"Esportati {len(selected_workouts)} allenamenti", 
                   parent=self)
            
            # Aggiorna la barra di stato
            self.controller.set_status(f"Esportati {len(selected_workouts)} allenamenti in {file_path}")
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione in Excel: {str(e)}")
            show_error("Errore", 
                     f"Impossibile esportare in Excel: {str(e)}", 
                     parent=self)
    
    def export_to_garmin(self):
        """Esporta allenamenti in Garmin Connect."""
        # Verifica che ci siano allenamenti da esportare
        if not self.imported_workouts:
            show_error("Errore", "Non ci sono allenamenti da esportare", parent=self)
            return
        
        # Verifica che il client Garmin sia disponibile
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        # Ottieni gli allenamenti selezionati
        selection = self.workout_tree.selection()
        
        # Se non ci sono selezioni, usa tutti gli allenamenti
        selected_workouts = []
        if selection:
            for item in selection:
                index = int(self.workout_tree.item(item, "tags")[0])
                selected_workouts.append(self.imported_workouts[index])
        else:
            selected_workouts = self.imported_workouts
        
        # Chiedi conferma
        if not ask_yes_no("Conferma esportazione", 
                      f"Vuoi esportare {len(selected_workouts)} allenamenti in Garmin Connect?", 
                      parent=self):
            return
        
        # Mostra un progress dialog
        progress_window = tk.Toplevel(self)
        progress_window.title("Esportazione in corso")
        progress_window.geometry("400x150")
        progress_window.transient(self)
        progress_window.grab_set()
        
        # Centra la finestra
        progress_window.update_idletasks()
        width = progress_window.winfo_width()
        height = progress_window.winfo_height()
        x = (progress_window.winfo_screenwidth() // 2) - (width // 2)
        y = (progress_window.winfo_screenheight() // 2) - (height // 2)
        progress_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Frame principale
        progress_frame = ttk.Frame(progress_window, padding=20)
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        # Messaggio
        message_var = tk.StringVar(value="Esportazione in corso...")
        message_label = ttk.Label(progress_frame, textvariable=message_var)
        message_label.pack(pady=(0, 10))
        
        # Contatore
        counter_var = tk.StringVar(value="0 / 0")
        counter_label = ttk.Label(progress_frame, textvariable=counter_var)
        counter_label.pack(pady=(0, 10))
        
        # Progressbar
        progress_var = tk.DoubleVar(value=0)
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
        progress_bar.pack(fill=tk.X)
        
        # Lista per tenere traccia degli errori
        errors = []
        
        # Funzione per esportare gli allenamenti
        def export_thread():
            try:
                exported = 0
                total = len(selected_workouts)
                
                # Per ogni allenamento
                for i, (name, workout) in enumerate(selected_workouts):
                    try:
                        # Aggiorna il messaggio
                        message_var.set(f"Esportazione di '{name}'...")
                        counter_var.set(f"{i + 1} / {total}")
                        
                        # Aggiorna la progressbar
                        progress_var.set((i / total) * 100)
                        
                        # Log per debug
                        logging.info(f"Esportazione allenamento {i+1}/{total}: '{name}'")
                        
                        # Esporta l'allenamento
                        response = self.garmin_client.add_workout(workout)
                        
                        if response and 'workoutId' in response:
                            exported += 1
                            logging.info(f"Allenamento '{name}' esportato con successo (ID: {response['workoutId']})")
                        else:
                            error_msg = f"Risposta non valida per '{name}'"
                            errors.append(error_msg)
                            logging.error(error_msg)
                        
                    except Exception as e:
                        error_msg = f"Errore nell'esportazione di '{name}': {str(e)}"
                        errors.append(error_msg)
                        logging.error(error_msg)
                        # Continua con il prossimo allenamento invece di interrompere
                        continue
                
                # Aggiorna la progressbar al 100%
                progress_var.set(100)
                counter_var.set(f"{total} / {total}")
                message_var.set("Esportazione completata")
                
                # Attendi un momento per mostrare il completamento
                time.sleep(0.5)
                
                # Chiudi la finestra di progresso
                progress_window.destroy()
                
                # Mostra il riepilogo
                if exported == total and not errors:
                    # Tutti gli allenamenti esportati con successo
                    show_info("Esportazione completata", 
                            f"Esportati con successo tutti i {exported} allenamenti", 
                            parent=self)
                elif exported > 0:
                    # Alcuni allenamenti esportati con successo
                    error_details = "\n".join(errors[:5])  # Mostra solo i primi 5 errori
                    if len(errors) > 5:
                        error_details += f"\n... e altri {len(errors) - 5} errori"
                    
                    show_warning("Esportazione parziale", 
                               f"Esportati {exported} allenamenti su {total}.\n\n"
                               f"Errori:\n{error_details}", 
                               parent=self)
                else:
                    # Nessun allenamento esportato
                    error_details = "\n".join(errors[:5])
                    if len(errors) > 5:
                        error_details += f"\n... e altri {len(errors) - 5} errori"
                    
                    show_error("Esportazione fallita", 
                             f"Impossibile esportare gli allenamenti.\n\n"
                             f"Errori:\n{error_details}", 
                             parent=self)
                
                # Aggiorna la barra di stato
                self.controller.set_status(f"Esportati {exported} allenamenti su {total} in Garmin Connect")
                
            except Exception as e:
                logging.error(f"Errore critico nell'esportazione in Garmin Connect: {str(e)}")
                
                # Chiudi la finestra di progresso
                try:
                    progress_window.destroy()
                except:
                    pass
                
                # Mostra messaggio di errore
                show_error("Errore critico", 
                         f"Errore critico durante l'esportazione: {str(e)}", 
                         parent=self)
        
        # Avvia il thread di esportazione
        import threading
        import time
        threading.Thread(target=export_thread, daemon=True).start()
    
    def save_configuration(self):
        """Salva la configurazione."""
        # Salva il prefisso
        self.config.set('planning.name_prefix', self.prefix_var.get())
        self.config.save()
        
        # Mostra messaggio di conferma
        show_info("Configurazione salvata", 
               "La configurazione è stata salvata correttamente", 
               parent=self)
    
    def on_login(self, client: GarminClient):
        """
        Gestisce l'evento di login.
        
        Args:
            client: Client Garmin
        """
        self.garmin_client = client
        self.garmin_service = GarminService(client)
        
        # Abilita i pulsanti
        self.garmin_import_button.config(state="normal")
        self.garmin_export_button.config(state="normal")
    
    def on_logout(self):
        """Gestisce l'evento di logout."""
        self.garmin_client = None
        self.garmin_service = None
        
        # Disabilita i pulsanti
        self.garmin_import_button.config(state="disabled")
        self.garmin_export_button.config(state="disabled")
    
    def on_activate(self):
        """Chiamato quando il frame viene attivato."""
        # Aggiorna la lista degli allenamenti
        self.update_workout_list()


if __name__ == "__main__":
    # Test del frame
    root = tk.Tk()
    root.title("Import/Export Test")
    root.geometry("1200x800")
    
    # Crea un notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Controller fittizio
    class DummyController:
        def set_status(self, message):
            print(message)
    
    # Crea il frame
    frame = ImportExportFrame(notebook, DummyController())
    notebook.add(frame, text="Importa/Esporta")
    
    root.mainloop()