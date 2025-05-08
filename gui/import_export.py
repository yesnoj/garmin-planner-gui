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

from garmin_planner_gui.config import get_config
from garmin_planner_gui.auth import GarminClient
from garmin_planner_gui.models.workout import Workout
from garmin_planner_gui.services.yaml_service import YamlService
from garmin_planner_gui.services.excel_service import ExcelService
from garmin_planner_gui.services.garmin_service import GarminService
from garmin_planner_gui.gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no,
    create_scrollable_frame, get_icon_for_sport
)


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
        steps_tree.column("value", width=80)
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
            end_value = str(step.end_condition_value) if step.end_condition_value else ""
            
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
        message_var = tk.StringVar(value="Esportazione in corso...")
        message_label = ttk.Label(progress_frame, textvariable=message_var)
        message_label.pack(pady=(0, 10))
        
        # Progressbar
        progress_var = tk.DoubleVar(value=0)
        progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
        progress_bar.pack(fill=tk.X)
        
        # Funzione per esportare gli allenamenti
        def export_thread():
            try:
                exported = 0
                
                # Per ogni allenamento
                for i, (name, workout) in enumerate(selected_workouts):
                    try:
                        # Aggiorna il messaggio
                        message_var.set(f"Esportazione di '{name}'...")
                        
                        # Aggiorna la progressbar
                        progress_var.set((i + 1) / len(selected_workouts) * 100)
                        
                        # Esporta l'allenamento
                        response = self.garmin_client.add_workout(workout)
                        
                        if response:
                            exported += 1
                        
                    except Exception as e:
                        logging.error(f"Errore nell'esportazione dell'allenamento '{name}': {str(e)}")
                
                # Chiudi la finestra di progresso
                progress_window.destroy()
                
                # Mostra messaggio di conferma
                show_info("Esportazione completata", 
                        f"Esportati {exported} allenamenti", 
                        parent=self)
                
                # Aggiorna la barra di stato
                self.controller.set_status(f"Esportati {exported} allenamenti in Garmin Connect")
                
            except Exception as e:
                logging.error(f"Errore nell'esportazione in Garmin Connect: {str(e)}")
                
                # Chiudi la finestra di progresso
                progress_window.destroy()
                
                # Mostra messaggio di errore
                show_error("Errore", 
                         f"Impossibile esportare gli allenamenti: {str(e)}", 
                         parent=self)
        
        # Avvia il thread di esportazione
        threading.Thread(target=export_thread).start()
    
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