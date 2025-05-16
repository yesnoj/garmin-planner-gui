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
from datetime import datetime

from config import get_config
from auth import GarminClient
from models.workout import Workout, WorkoutStep, Target
from gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no,
    create_scrollable_frame, is_valid_date, convert_date_for_garmin, is_valid_display_date
)
from gui.styles import get_icon_for_sport, get_icon_for_step, get_color_for_step


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
        
        # Carica la data della gara dal config e memorizza il formato interno
        self._internal_race_day = self.config.get('planning.race_day', '')
        self._internal_date = None
        
        # Lista degli allenamenti disponibili
        self.workouts = []
        
        # Lista degli allenamenti importati
        self.imported_workouts = []
        
        # Allenamento corrente
        self.current_workout = None
        self.current_workout_id = None
        self.current_workout_modified = False
        
        # Step selezionato
        self.selected_step_index = None
        
        # Creazione dei widget
        self.create_widgets()
    

    def select_race_day(self):
        """Mostra un selettore di date per la data della gara."""
        # Importa qui per evitare import circolari
        from gui.dialogs.date_picker import DatePickerDialog
        
        def on_date_selected(date):
            """Callback per la selezione della data."""
            if date:
                # Memorizza la data interna in formato YYYY-MM-DD
                self._internal_race_day = date
                
                # Converti per la visualizzazione in formato DD/MM/YYYY
                try:
                    year, month, day = date.split('-')
                    formatted_date = f"{day}/{month}/{year}"
                    self.race_day_var.set(formatted_date)
                except:
                    # In caso di errore, usa il formato originale
                    self.race_day_var.set(date)
        
        # Ottieni la data iniziale (potrebbe essere già in formato YYYY-MM-DD)
        initial_date = getattr(self, '_internal_race_day', None)
        if not initial_date:
            # Prova a convertire da DD/MM/YYYY a YYYY-MM-DD
            current_date = self.race_day_var.get()
            initial_date = convert_date_for_garmin(current_date)
        
        # Mostra il dialog
        date_picker = DatePickerDialog(self, 
                                    title="Seleziona la data della gara",
                                    initial_date=initial_date,
                                    callback=on_date_selected)

    def save_planning_config(self):
        """Salva la configurazione di pianificazione."""
        # Salva il nome atleta
        self.config.set('athlete_name', self.athlete_name_var.get())
        
        # Salva la data della gara
        race_day_display = self.race_day_var.get()
        
        # Converti da GG/MM/AAAA a YYYY-MM-DD per il salvataggio
        race_day_internal = convert_date_for_garmin(race_day_display)
        
        # Verifica che la data sia valida
        if race_day_internal and not is_valid_date(race_day_internal):
            show_error("Errore", "Il formato della data non è valido", parent=self)
            return
        
        # Salva la data in formato YYYY-MM-DD
        self.config.set('planning.race_day', race_day_internal)
        
        # Memorizza anche il formato interno
        self._internal_race_day = race_day_internal
        
        # Salva i giorni preferiti
        preferred_days = []
        for i, var in enumerate(self.pref_days_vars):
            if var.get():
                preferred_days.append(i)
        
        self.config.set('planning.preferred_days', preferred_days)
        self.config.save()
        
        # Mostra messaggio di conferma
        show_info("Configurazione salvata", 
                 "La configurazione di pianificazione è stata salvata", 
                 parent=self)


    def plan_workout_dates(self):
        """Pianifica le date degli allenamenti."""
        # Verifica che ci sia una data gara
        race_day = self.race_day_var.get()
        if not race_day:
            show_error("Errore", "Imposta prima la data della gara", parent=self)
            return
        
        # Ottieni la data interna in formato YYYY-MM-DD
        race_day_internal = None
        if '/' in race_day:
            try:
                day, month, year = race_day.split('/')
                race_day_internal = f"{year}-{month}-{day}"
            except:
                race_day_internal = race_day
        else:
            race_day_internal = race_day
        
        # Verifica che la data gara sia valida
        if not is_valid_date(race_day_internal):
            show_error("Errore", "Il formato della data non è valido", parent=self)
            return
        
        # Verifica che ci siano giorni preferiti
        preferred_days = []
        for i, var in enumerate(self.pref_days_vars):
            if var.get():
                preferred_days.append(i)
        
        if not preferred_days:
            show_error("Errore", "Seleziona almeno un giorno preferito", parent=self)
            return
        
        # Ottieni la lista degli allenamenti
        source = self.source_var.get()
        workouts_to_plan = []
        
        if source == "garmin":
            # Usa gli allenamenti da Garmin
            for wid, wdata in self.workouts:
                if isinstance(wdata, dict):
                    workouts_to_plan.append((wid, wdata))
        else:  # source == "imported"
            # Usa gli allenamenti importati
            import_export_frame = self.controller.import_export
            for i, (name, workout) in enumerate(import_export_frame.imported_workouts):
                workout_id = f"imported_{i}"
                # Crea un dict simile agli allenamenti Garmin
                wdata = {
                    'workoutId': workout_id,
                    'workoutName': name,
                    'sportType': {'sportTypeKey': workout.sport_type},
                    'description': workout.description,
                    'imported': True,
                    'workout': workout  # Memorizza l'oggetto workout per semplicità
                }
                workouts_to_plan.append((workout_id, wdata))
        
        if not workouts_to_plan:
            show_error("Errore", "Non ci sono allenamenti da pianificare", parent=self)
            return
        
        # Analizza i nomi degli allenamenti per trovare il pattern W##S##
        week_sessions = {}  # Dizionario settimana -> lista di sessioni
        
        for _, wdata in workouts_to_plan:
            name = wdata.get('workoutName', '')
            if 'W' in name and 'S' in name or 'D' in name:
                # Prova a estrarre la settimana e la sessione
                pattern = r'W(\d+)[SD](\d+)'
                match = re.search(pattern, name)
                if match:
                    week = int(match.group(1))
                    session = int(match.group(2))
                    
                    if week not in week_sessions:
                        week_sessions[week] = []
                    
                    week_sessions[week].append(session)
        
        # Verifica se il numero di sessioni è compatibile con i giorni preferiti
        max_sessions = 0
        for week, sessions in week_sessions.items():
            max_sessions = max(max_sessions, max(sessions))
        
        if max_sessions > len(preferred_days):
            show_warning("Attenzione", 
                       f"Ci sono settimane con {max_sessions} sessioni, ma solo {len(preferred_days)} giorni preferiti", 
                       parent=self)
        
        # Calcola le date degli allenamenti
        race_date = datetime.datetime.strptime(race_day_internal, '%Y-%m-%d').date()       

        # Pianifica all'indietro a partire dalla data della gara
        dates = {}  # Dizionario settimana,sessione -> data
        
        # Ordina le settimane in ordine decrescente (a partire dalla gara)
        weeks = sorted(week_sessions.keys(), reverse=True)
        
        current_date = race_date
        
        # Per ogni settimana, in ordine decrescente
        for week in weeks:
            sessions = sorted(week_sessions[week])
            
            # Per ogni sessione, in ordine decrescente
            for session in sorted(sessions, reverse=True):
                # Trova il giorno preferito più vicino
                days_to_subtract = 0
                current_weekday = current_date.weekday()
                
                # Trova il giorno preferito più vicino all'indietro
                while days_to_subtract < 7:
                    check_day = (current_weekday - days_to_subtract) % 7
                    if check_day in preferred_days:
                        break
                    days_to_subtract += 1
                
                # Calcola la data dell'allenamento
                workout_date = current_date - datetime.timedelta(days=days_to_subtract)
                
                # Salva la data
                dates[(week, session)] = workout_date
                
                # Vai al giorno precedente per la prossima sessione
                current_date = workout_date - datetime.timedelta(days=1)
        
        # Associa le date agli allenamenti
        updated_workouts = []
        
        for wid, wdata in workouts_to_plan:
            name = wdata.get('workoutName', '')
            match = re.search(r'W(\d+)[SD](\d+)', name)
            
            if match:
                week = int(match.group(1))
                session = int(match.group(2))
                
                if (week, session) in dates:
                    # Formatta la data in YYYY-MM-DD
                    workout_date = dates[(week, session)].strftime('%Y-%m-%d')
                    
                    # Se è un allenamento importato
                    if 'imported' in wdata:
                        # Trova l'allenamento originale
                        if source == "imported":
                            import_export_frame = self.controller.import_export
                            idx = int(wid.split('_')[1])
                            if idx < len(import_export_frame.imported_workouts):
                                _, workout = import_export_frame.imported_workouts[idx]
                                
                                # Cerca uno step con la data o ne crea uno nuovo
                                date_step = None
                                for step in workout.workout_steps:
                                    if hasattr(step, 'date') and step.date:
                                        date_step = step
                                        date_step.date = workout_date
                                        break
                                
                                if not date_step:
                                    date_step = WorkoutStep(0, "warmup")
                                    date_step.date = workout_date
                                    workout.workout_steps.insert(0, date_step)
                                
                                updated_workouts.append((week, session, name))
                                
                                # Importante: aggiorna anche il campo 'date' nei dati importati caricati
                                for i, (imported_id, imported_data) in enumerate(self.imported_workouts):
                                    if imported_id == wid and isinstance(imported_data, dict):
                                        imported_data['date'] = workout_date
                                        self.imported_workouts[i] = (imported_id, imported_data)
                    else:
                        # È un allenamento Garmin, aggiorna il campo 'date'
                        for i, (garmin_id, garmin_data) in enumerate(self.workouts):
                            if garmin_id == wid and isinstance(garmin_data, dict):
                                garmin_data['date'] = workout_date
                                self.workouts[i] = (garmin_id, garmin_data)
                                updated_workouts.append((week, session, name))
                        
                        # Se l'allenamento è caricato nell'editor, aggiorna la data
                        if self.current_workout and hasattr(self, 'current_workout_id') and self.current_workout_id == wid:
                            self.date_var.set(workout_date)
                            
                            # Aggiorna anche lo step della data
                            date_step = None
                            for step in self.current_workout.workout_steps:
                                if hasattr(step, 'date') and step.date:
                                    date_step = step
                                    date_step.date = workout_date
                                    break
                            
                            if not date_step:
                                date_step = WorkoutStep(0, "warmup")
                                date_step.date = workout_date
                                self.current_workout.workout_steps.insert(0, date_step)
                                
                            # Aggiorna la lista degli step
                            self.update_steps_list()
        
        # Forza il ricaricamento degli allenamenti importati se è la fonte attuale
        if source == "imported":
            self.load_imported_workouts()
        
        # Mostra un messaggio di conferma
        if updated_workouts:
            # Formatta il messaggio
            message = f"Pianificate le date per {len(updated_workouts)} allenamenti."
            
            # Se ci sono più di 3 allenamenti, mostra solo i primi 3
            if len(updated_workouts) > 3:
                message += "\n\nEsempi:"
                for i in range(3):
                    week, session, name = updated_workouts[i]
                    date = dates[(week, session)].strftime('%d/%m/%Y')
                    message += f"\n- {name}: {date}"
                message += f"\n... e altri {len(updated_workouts) - 3} allenamenti"
            else:
                message += "\n"
                for week, session, name in updated_workouts:
                    date = dates[(week, session)].strftime('%d/%m/%Y')
                    message += f"\n- {name}: {date}"
            
            show_info("Pianificazione completata", message, parent=self)
        else:
            show_warning("Nessun allenamento pianificato", 
                       "Non è stato possibile pianificare alcun allenamento", 
                       parent=self)
        
        # Aggiorna la lista degli allenamenti
        self.update_workout_list()

    def clear_workout_dates(self):
        """Cancella le date degli allenamenti."""
        # Chiedi conferma
        if not ask_yes_no("Conferma", 
                       "Sei sicuro di voler cancellare tutte le date degli allenamenti?", 
                       parent=self):
            return
        
        # Determina la fonte degli allenamenti
        source = self.source_var.get()
        cleared_count = 0
        
        if source == "garmin":
            # Usa gli allenamenti da Garmin
            for i, (wid, wdata) in enumerate(self.workouts):
                if isinstance(wdata, dict):
                    # Cancella il campo 'date' nel dizionario
                    if 'date' in wdata:
                        wdata['date'] = ""
                        cleared_count += 1
                    
                    # Aggiorna l'elemento nella lista workouts
                    self.workouts[i] = (wid, wdata)
        else:  # source == "imported"
            # Usa gli allenamenti importati
            import_export_frame = self.controller.import_export
            
            if hasattr(import_export_frame, 'imported_workouts'):
                for i, (name, workout) in enumerate(import_export_frame.imported_workouts):
                    # Cerca uno step con la data
                    date_steps = []
                    for j, step in enumerate(workout.workout_steps):
                        if hasattr(step, 'date') and step.date:
                            date_steps.append(j)
                    
                    # Rimuovi gli step della data
                    for j in sorted(date_steps, reverse=True):
                        del workout.workout_steps[j]
                        cleared_count += 1
                
                # Forza il ricaricamento degli allenamenti importati
                self.imported_workouts = []
                self.load_imported_workouts()
        
        # Se l'allenamento è caricato nell'editor, aggiorna la data
        if self.current_workout:
            # Cerca e rimuovi gli step della data
            date_steps = []
            for i, step in enumerate(self.current_workout.workout_steps):
                if hasattr(step, 'date') and step.date:
                    date_steps.append(i)
            
            # Rimuovi gli step della data se ce ne sono
            if date_steps:
                for i in sorted(date_steps, reverse=True):
                    del self.current_workout.workout_steps[i]
                    cleared_count += 1
                
                # Reimposta il campo data
                self.date_var.set("")
                
                # Aggiorna la lista degli step
                self.update_steps_list()
                
                # Segna come modificato
                self.current_workout_modified = True
        
        # Mostra un messaggio di conferma
        if cleared_count > 0:
            show_info("Date cancellate", 
                   f"Cancellate le date di {cleared_count} allenamenti", 
                   parent=self)
        else:
            show_info("Nessuna data trovata", 
                   "Non sono state trovate date da cancellare", 
                   parent=self)

        # Aggiorna la lista degli allenamenti
        self.update_workout_list()


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
        
        # Frame per la configurazione della pianificazione
        planning_frame = ttk.LabelFrame(right_frame, text="Configurazione Pianificazione")
        planning_frame.pack(fill=tk.X, pady=(0, 10))

        # Nome atleta
        athlete_frame = ttk.Frame(planning_frame)
        athlete_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(athlete_frame, text="Nome Atleta:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.athlete_name_var = tk.StringVar(value=self.config.get('athlete_name', ''))
        athlete_entry = ttk.Entry(athlete_frame, textvariable=self.athlete_name_var, width=30)
        athlete_entry.grid(row=0, column=1, sticky=tk.W+tk.E)

        # Data gara
        race_frame = ttk.Frame(planning_frame)
        race_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(race_frame, text="Data Gara:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        # Converti la data interna per la visualizzazione
        race_day_display = ""
        if hasattr(self, '_internal_race_day') and self._internal_race_day:
            try:
                year, month, day = self._internal_race_day.split('-')
                race_day_display = f"{day}/{month}/{year}"
            except:
                race_day_display = self._internal_race_day
        
        self.race_day_var = tk.StringVar(value=race_day_display)
        race_entry = ttk.Entry(race_frame, textvariable=self.race_day_var, width=15)
        race_entry.grid(row=0, column=1, sticky=tk.W)
        race_picker = ttk.Button(race_frame, text="Seleziona...", command=self.select_race_day)
        race_picker.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        create_tooltip(race_entry, "Data della gara nel formato GG/MM/AAAA")

        # Giorni preferiti
        days_frame = ttk.Frame(planning_frame)
        days_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        ttk.Label(days_frame, text="Giorni Preferiti:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))

        # Checkbutton per ogni giorno
        self.pref_days_vars = []
        days = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        preferred_days = self.config.get('planning.preferred_days', [1, 3, 5])

        for i, day in enumerate(days):
            var = tk.BooleanVar(value=i in preferred_days)
            cb = ttk.Checkbutton(days_frame, text=day, variable=var)
            cb.grid(row=0, column=i+1, padx=2)
            self.pref_days_vars.append(var)

        # Pulsanti per la pianificazione
        plan_buttons_frame = ttk.Frame(planning_frame)
        plan_buttons_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(plan_buttons_frame, text="Pianifica Date", command=self.plan_workout_dates).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(plan_buttons_frame, text="Cancella Date", command=self.clear_workout_dates).pack(side=tk.LEFT)
        ttk.Button(plan_buttons_frame, text="Salva Configurazione", command=self.save_planning_config).pack(side=tk.RIGHT)

        # --- Parte sinistra: Lista degli allenamenti ---
        
        # Frame per selezionare la fonte degli allenamenti
        source_frame = ttk.Frame(left_frame)
        source_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(source_frame, text="Fonte:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Variabile per la fonte degli allenamenti
        self.source_var = tk.StringVar(value="garmin")
        
        # Radio buttons per le fonti
        sources_frame = ttk.Frame(source_frame)
        sources_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Radiobutton(sources_frame, text="Garmin Connect", value="garmin", 
                       variable=self.source_var, command=self.on_source_change).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Radiobutton(sources_frame, text="Importati", value="imported", 
                       variable=self.source_var, command=self.on_source_change).pack(side=tk.LEFT)
        
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
        columns = ("name", "sport", "date", "steps")
        self.workout_tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                                      selectmode="extended")
        
        # Intestazioni
        self.workout_tree.heading("name", text="Nome")
        self.workout_tree.heading("sport", text="Sport")
        self.workout_tree.heading("date", text="Data")
        self.workout_tree.heading("steps", text="Step")
        
        # Larghezze colonne
        self.workout_tree.column("name", width=150)
        self.workout_tree.column("sport", width=70)
        self.workout_tree.column("date", width=80)
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
        
        export_frame = ttk.Frame(buttons_frame)
        export_frame.pack(side=tk.LEFT, padx=(20, 0))

        ttk.Button(export_frame, text="Esporta YAML", 
                 command=self.export_selected_yaml).pack(side=tk.LEFT, padx=(0, 5))
                 
        ttk.Button(export_frame, text="Esporta Excel", 
                 command=self.export_selected_excel).pack(side=tk.LEFT)
        
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
        
        # Data dell'allenamento
        ttk.Label(workout_header, text="Data:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        
        date_frame = ttk.Frame(workout_header)
        date_frame.grid(row=2, column=1, sticky=tk.W)
        
        self.date_var = tk.StringVar()
        date_entry = ttk.Entry(date_frame, textvariable=self.date_var, width=15)
        date_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        date_picker_button = ttk.Button(date_frame, text="Seleziona...", command=self.select_date)
        date_picker_button.pack(side=tk.LEFT)
        
        create_tooltip(date_entry, "Data dell'allenamento nel formato YYYY-MM-DD")
        
        # Descrizione
        ttk.Label(workout_header, text="Descrizione:").grid(row=3, column=0, sticky=tk.W, padx=(0, 5))
        
        self.description_var = tk.StringVar()
        description_entry = ttk.Entry(workout_header, textvariable=self.description_var, width=40)
        description_entry.grid(row=3, column=1, sticky=tk.W+tk.E)
        
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
        
        # Inizializza la lista degli allenamenti importati
        self.imported_workouts = []


    def edit_step(self):
        """Modifica lo step selezionato."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Ottieni lo step da modificare
        step = None
        
        if self.selected_step_path and len(self.selected_step_path) > 1:
            # È uno step nidificato, naviga l'albero per trovarlo
            current = self.current_workout.workout_steps[self.selected_step_path[0]]
            for i in range(1, len(self.selected_step_path)):
                if hasattr(current, 'workout_steps') and 0 <= self.selected_step_path[i] < len(current.workout_steps):
                    current = current.workout_steps[self.selected_step_path[i]]
                else:
                    # Indice non valido
                    return
            step = current
        elif self.selected_step_index is not None:
            # È uno step di primo livello
            step = self.current_workout.workout_steps[self.selected_step_index]
        else:
            # Nessuno step selezionato
            return
        
        # Verifica che non sia uno step speciale con la data
        if hasattr(step, 'date') and step.date:
            show_info("Informazione", "Non è possibile modificare lo step della data. "
                    "Usa il campo data in alto per modificare la data dell'allenamento.", parent=self)
            return
        
        # Verifica il tipo di step
        if step.step_type == "repeat":
            # Importa qui per evitare import circolari
            from gui.dialogs.repeat_step import RepeatStepDialog
            
            # Callback per la modifica del gruppo
            def on_repeat_edited(edited_step):
                # Aggiorna lo step nell'allenamento
                if edited_step:
                    if self.selected_step_path and len(self.selected_step_path) > 1:
                        # È uno step nidificato, naviga l'albero per trovare il genitore
                        parent = self.current_workout.workout_steps[self.selected_step_path[0]]
                        for i in range(1, len(self.selected_step_path) - 1):
                            parent = parent.workout_steps[self.selected_step_path[i]]
                        # Aggiorna lo step
                        parent.workout_steps[self.selected_step_path[-1]] = edited_step
                    else:
                        # È uno step di primo livello
                        self.current_workout.workout_steps[self.selected_step_index] = edited_step
                    
                    # Segna come modificato
                    self.current_workout_modified = True
                    
                    # Aggiorna la lista degli step
                    self.update_steps_list()
            
            # Crea il dialog
            dialog = RepeatStepDialog(self, repeat_step=step, sport_type=self.sport_var.get(), 
                                   callback=on_repeat_edited)
        else:
            # Importa qui per evitare import circolari
            from gui.dialogs.workout_step import WorkoutStepDialog
            
            # Callback per la modifica dello step
            def on_step_edited(edited_step):
                # Aggiorna lo step nell'allenamento
                if edited_step:
                    if self.selected_step_path and len(self.selected_step_path) > 1:
                        # È uno step nidificato, naviga l'albero per trovare il genitore
                        parent = self.current_workout.workout_steps[self.selected_step_path[0]]
                        for i in range(1, len(self.selected_step_path) - 1):
                            parent = parent.workout_steps[self.selected_step_path[i]]
                        # Aggiorna lo step
                        parent.workout_steps[self.selected_step_path[-1]] = edited_step
                    else:
                        # È uno step di primo livello
                        self.current_workout.workout_steps[self.selected_step_index] = edited_step
                    
                    # Segna come modificato
                    self.current_workout_modified = True
                    
                    # Aggiorna la lista degli step
                    self.update_steps_list()
            
            # Crea il dialog
            dialog = WorkoutStepDialog(self, step=step, sport_type=self.sport_var.get(), 
                                    callback=on_step_edited)


    def delete_step(self):
        """Elimina lo step selezionato."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Verifica che ci sia uno step selezionato
        if self.selected_step_index is None:
            return
        
        # Ottieni lo step
        step = self.current_workout.workout_steps[self.selected_step_index]
        
        # Verifica che non sia uno step speciale con la data
        if hasattr(step, 'date') and step.date:
            show_info("Informazione", "Non è possibile eliminare lo step della data. "
                    "Usa il campo data in alto per modificare la data dell'allenamento.", parent=self)
            return
        
        # Chiedi conferma
        if not ask_yes_no("Conferma", "Sei sicuro di voler eliminare questo step?", parent=self):
            return
        
        # Rimuovi lo step
        del self.current_workout.workout_steps[self.selected_step_index]
        
        # Segna come modificato
        self.current_workout_modified = True
        
        # Aggiorna la lista degli step
        self.update_steps_list()
        
        # Resetta la selezione
        self.selected_step_index = None
        self.edit_button.config(state="disabled")
        self.delete_step_button.config(state="disabled")
        self.move_up_button.config(state="disabled")
        self.move_down_button.config(state="disabled")


    def move_step_up(self):
        """Sposta lo step selezionato verso l'alto."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Verifica che ci sia uno step selezionato
        if self.selected_step_index is None:
            return
        
        # Verifica che non sia il primo step
        if self.selected_step_index <= 0:
            return
        
        # Ottieni lo step corrente e il precedente
        step = self.current_workout.workout_steps[self.selected_step_index]
        prev_step = self.current_workout.workout_steps[self.selected_step_index - 1]
        
        # Verifica che il precedente non sia uno step speciale con la data
        if hasattr(prev_step, 'date') and prev_step.date:
            show_info("Informazione", "Non è possibile spostare uno step sopra lo step della data.", parent=self)
            return
        
        # Scambia gli step
        self.current_workout.workout_steps[self.selected_step_index - 1] = step
        self.current_workout.workout_steps[self.selected_step_index] = prev_step
        
        # Aggiorna l'indice selezionato
        self.selected_step_index -= 1
        
        # Segna come modificato
        self.current_workout_modified = True
        
        # Aggiorna la lista degli step
        self.update_steps_list()
        
        # Seleziona il nuovo step
        # Dobbiamo trovare l'indice dell'interfaccia corrispondente all'indice originale
        visible_index = None
        for i, orig_idx in enumerate(self.step_index_map):
            if orig_idx == self.selected_step_index:
                visible_index = i
                break
        
        if visible_index is not None:
            self.on_step_selected(visible_index)

    # E analogo aggiornamento per move_step_down
    def move_step_down(self):
        """Sposta lo step selezionato verso il basso."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Verifica che ci sia uno step selezionato
        if self.selected_step_index is None:
            return
        
        # Verifica che non sia l'ultimo step
        if self.selected_step_index >= len(self.current_workout.workout_steps) - 1:
            return
        
        # Ottieni lo step corrente e il successivo
        step = self.current_workout.workout_steps[self.selected_step_index]
        next_step = self.current_workout.workout_steps[self.selected_step_index + 1]
        
        # Verifica che lo step corrente non sia uno step speciale con la data
        if hasattr(step, 'date') and step.date:
            show_info("Informazione", "Non è possibile spostare lo step della data.", parent=self)
            return
        
        # Scambia gli step
        self.current_workout.workout_steps[self.selected_step_index + 1] = step
        self.current_workout.workout_steps[self.selected_step_index] = next_step
        
        # Aggiorna l'indice selezionato
        self.selected_step_index += 1
        
        # Segna come modificato
        self.current_workout_modified = True
        
        # Aggiorna la lista degli step
        self.update_steps_list()
        
        # Seleziona il nuovo step
        # Dobbiamo trovare l'indice dell'interfaccia corrispondente all'indice originale
        visible_index = None
        for i, orig_idx in enumerate(self.step_index_map):
            if orig_idx == self.selected_step_index:
                visible_index = i
                break
        
        if visible_index is not None:
            self.on_step_selected(visible_index)


    def add_step(self):
        """Aggiunge un nuovo step all'allenamento corrente."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Importa qui per evitare import circolari
        from gui.dialogs.workout_step import WorkoutStepDialog
        
        # Callback per l'aggiunta dello step
        def on_step_added(step):
            # Aggiungi lo step all'allenamento solo se è stato creato
            if step:
                self.current_workout.add_step(step)
                
                # Segna come modificato
                self.current_workout_modified = True
                
                # Aggiorna la lista degli step
                self.update_steps_list()
        
        # Crea il dialog
        dialog = WorkoutStepDialog(self, sport_type=self.sport_var.get(), callback=on_step_added)


    def add_repeat(self):
        """Aggiunge un nuovo gruppo di ripetizioni all'allenamento corrente."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Importa qui per evitare import circolari
        from gui.dialogs.repeat_step import RepeatStepDialog
        
        # Callback per l'aggiunta del gruppo
        def on_repeat_added(repeat_step):
            # Aggiungi lo step all'allenamento solo se è stato creato
            if repeat_step:
                self.current_workout.add_step(repeat_step)
                
                # Segna come modificato
                self.current_workout_modified = True
                
                # Aggiorna la lista degli step
                self.update_steps_list()
        
        # Crea il dialog
        dialog = RepeatStepDialog(self, sport_type=self.sport_var.get(), callback=on_repeat_added)


    def export_selected_yaml(self):
        """Esporta gli allenamenti selezionati in un file YAML."""
        # Verifica che ci siano allenamenti selezionati
        selection = self.workout_tree.selection()
        if not selection:
            show_warning("Attenzione", "Seleziona almeno un allenamento da esportare", parent=self)
            return
        
        # Chiedi dove salvare il file
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Esporta allenamenti in YAML",
            filetypes=[("YAML files", "*.yaml"), ("Tutti i file", "*.*")],
            defaultextension=".yaml"
        )
        
        if not file_path:
            return
        
        try:
            # Ottieni gli allenamenti selezionati
            export_workouts = []
            
            # Determina la fonte degli allenamenti
            source = self.source_var.get()
            
            if source == "garmin":
                # Verifica che ci sia un client Garmin
                if not self.garmin_client:
                    show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
                    return
                
                for item in selection:
                    # Ottieni l'ID dell'allenamento
                    workout_id = self.workout_tree.item(item, "tags")[0]
                    workout_name = self.workout_tree.item(item, "values")[0]
                    
                    # Ottieni i dettagli dell'allenamento
                    workout_data = self.garmin_client.get_workout(workout_id)
                    
                    # Importa l'allenamento
                    from services.garmin_service import GarminService
                    service = GarminService(self.garmin_client)
                    
                    workout = service.import_workout(workout_data)
                    
                    if workout:
                        export_workouts.append((workout_name, workout))
            else:  # source == "imported"
                # Usa gli allenamenti importati
                import_export_frame = self.controller.import_export
                
                for item in selection:
                    # Ottieni l'ID dell'allenamento
                    workout_id = self.workout_tree.item(item, "tags")[0]
                    workout_name = self.workout_tree.item(item, "values")[0]
                    
                    if workout_id.startswith("imported_"):
                        index = int(workout_id.split("_")[1])
                        if index < len(import_export_frame.imported_workouts):
                            name, workout = import_export_frame.imported_workouts[index]
                            export_workouts.append((name, workout))
            
            # Esporta gli allenamenti
            if export_workouts:
                # Crea una configurazione personalizzata con i valori correnti dell'interfaccia utente
                export_config = {
                    'name_prefix': self.config.get('planning.name_prefix', '')
                }
                
                # Aggiungi i valori dell'interfaccia utente se disponibili
                if hasattr(self, 'athlete_name_var'):
                    export_config['athlete_name'] = self.athlete_name_var.get()
                else:
                    export_config['athlete_name'] = self.config.get('athlete_name', '')
                    
                if hasattr(self, 'race_day_var'):
                    race_day = self.race_day_var.get()
                    if race_day and is_valid_date(race_day):
                        export_config['race_day'] = race_day
                    else:
                        export_config['race_day'] = self.config.get('planning.race_day', '')
                else:
                    export_config['race_day'] = self.config.get('planning.race_day', '')
                    
                if hasattr(self, 'pref_days_vars'):
                    preferred_days = []
                    for i, var in enumerate(self.pref_days_vars):
                        if var.get():
                            preferred_days.append(i)
                        
                    if preferred_days:
                        export_config['preferred_days'] = preferred_days
                    else:
                        export_config['preferred_days'] = self.config.get('planning.preferred_days', [1, 3, 5])
                else:
                    export_config['preferred_days'] = self.config.get('planning.preferred_days', [1, 3, 5])
                
                # Importa il servizio YAML
                from services.yaml_service import YamlService
                
                # Esporta gli allenamenti con la configurazione personalizzata
                YamlService.export_workouts(export_workouts, file_path, export_config)
                
                # Mostra messaggio di conferma
                show_info("Esportazione completata", 
                       f"{len(export_workouts)} allenamenti esportati in {file_path}", 
                       parent=self)
            else:
                show_warning("Attenzione", "Nessun allenamento da esportare", parent=self)
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione degli allenamenti: {str(e)}")
            show_error("Errore", 
                     f"Impossibile esportare gli allenamenti: {str(e)}", 
                     parent=self)


    def export_selected_excel(self):
        """Esporta gli allenamenti selezionati in un file Excel."""
        # Verifica che ci siano allenamenti selezionati
        selection = self.workout_tree.selection()
        if not selection:
            show_warning("Attenzione", "Seleziona almeno un allenamento da esportare", parent=self)
            return
        
        # Chiedi dove salvare il file
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Esporta allenamenti in Excel",
            filetypes=[("Excel files", "*.xlsx"), ("Tutti i file", "*.*")],
            defaultextension=".xlsx"
        )
        
        if not file_path:
            return
        
        try:
            # Ottieni gli allenamenti selezionati
            export_workouts = []
            
            # Determina la fonte degli allenamenti
            source = self.source_var.get()
            
            if source == "garmin":
                # Verifica che ci sia un client Garmin
                if not self.garmin_client:
                    show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
                    return
                
                for item in selection:
                    # Ottieni l'ID dell'allenamento
                    workout_id = self.workout_tree.item(item, "tags")[0]
                    workout_name = self.workout_tree.item(item, "values")[0]
                    
                    # Ottieni i dettagli dell'allenamento
                    workout_data = self.garmin_client.get_workout(workout_id)
                    
                    # Importa l'allenamento
                    from services.garmin_service import GarminService
                    service = GarminService(self.garmin_client)
                    
                    workout = service.import_workout(workout_data)
                    
                    if workout:
                        export_workouts.append((workout_name, workout))
            else:  # source == "imported"
                # Usa gli allenamenti importati
                import_export_frame = self.controller.import_export
                
                for item in selection:
                    # Ottieni l'ID dell'allenamento
                    workout_id = self.workout_tree.item(item, "tags")[0]
                    workout_name = self.workout_tree.item(item, "values")[0]
                    
                    if workout_id.startswith("imported_"):
                        index = int(workout_id.split("_")[1])
                        if index < len(import_export_frame.imported_workouts):
                            name, workout = import_export_frame.imported_workouts[index]
                            export_workouts.append((name, workout))
            
            custom_config = None
            if hasattr(self, 'athlete_name_var') and hasattr(self, 'race_day_var') and hasattr(self, 'pref_days_vars'):
                custom_config = {
                    'athlete_name': self.athlete_name_var.get(),
                    'name_prefix': self.config.get('planning.name_prefix', ''),
                    'race_day': self.race_day_var.get(),
                    'preferred_days': [i for i, var in enumerate(self.pref_days_vars) if var.get()]
                }
            
            # Esporta gli allenamenti
            from services.excel_service import ExcelService
            ExcelService.export_workouts(export_workouts, file_path, custom_config)
            
            # Mostra messaggio di conferma
            show_info("Esportazione completata", 
                   f"{len(export_workouts)} allenamenti esportati in {file_path}", 
                   parent=self)
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione degli allenamenti: {str(e)}")
            show_error("Errore", 
                     f"Impossibile esportare gli allenamenti: {str(e)}", 
                     parent=self)

    def select_date(self):
        """Mostra un selettore di date."""
        # Importa qui per evitare import circolari
        from gui.dialogs.date_picker import DatePickerDialog
        
        def on_date_selected(date):
            """Callback per la selezione della data."""
            if date:
                # Salva internamente nel formato YYYY-MM-DD
                self._internal_date = date
                
                # Converti per la visualizzazione in formato DD/MM/YYYY
                try:
                    year, month, day = date.split('-')
                    formatted_date = f"{day}/{month}/{year}"
                    self.date_var.set(formatted_date)
                    # Segna come modificato
                    self.current_workout_modified = True
                except:
                    self.date_var.set(date)
                    self.current_workout_modified = True
        
        # Se c'è una data interna memorizzata, usala per l'inizializzazione
        initial_date = getattr(self, '_internal_date', None)
        if not initial_date:
            # Prova a convertire da DD/MM/YYYY a YYYY-MM-DD
            current_date = self.date_var.get()
            initial_date = convert_date_for_garmin(current_date)
        
        # Mostra il dialog
        date_picker = DatePickerDialog(self, 
                                    title="Seleziona la data dell'allenamento",
                                    initial_date=initial_date,
                                    callback=on_date_selected)

    def delete_workout(self):
        """Elimina gli allenamenti selezionati."""
        # Verifica che ci siano allenamenti selezionati
        selection = self.workout_tree.selection()
        if not selection:
            return
        
        # Chiedi conferma
        if len(selection) == 1:
            workout_id = self.workout_tree.item(selection[0], "tags")[0]
            workout_name = self.workout_tree.item(selection[0], "values")[0]
            message = f"Sei sicuro di voler eliminare l'allenamento '{workout_name}'?"
        else:
            message = f"Sei sicuro di voler eliminare {len(selection)} allenamenti selezionati?"
        
        if not ask_yes_no("Conferma eliminazione", message, parent=self):
            return
        
        # Determina la fonte dell'allenamento
        source = self.source_var.get()
        
        if source == "garmin":
            # Verifica che ci sia un client Garmin
            if not self.garmin_client:
                show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
                return
            
            eliminated = 0
            local_eliminated = 0
            workout_ids_to_remove = []
            
            for item in selection:
                workout_id = self.workout_tree.item(item, "tags")[0]
                workout_name = self.workout_tree.item(item, "values")[0]
                
                # Verifica se è un allenamento locale
                is_local = False
                for i, (wid, wdata) in enumerate(self.workouts):
                    if wid == workout_id:
                        if wdata.get('local', False):
                            is_local = True
                            # Rimuovi dalla lista locale
                            workout_ids_to_remove.append(workout_id)
                            local_eliminated += 1
                        break
                
                if not is_local:
                    try:
                        # Elimina l'allenamento da Garmin Connect
                        response = self.garmin_client.delete_workout(workout_id)
                        # Se l'eliminazione ha avuto successo, aggiungi l'ID alla lista per la rimozione
                        if response or response == {}:  # A volte l'API restituisce un dict vuoto in caso di successo
                            workout_ids_to_remove.append(workout_id)
                            eliminated += 1
                    except Exception as e:
                        logging.error(f"Errore nell'eliminazione dell'allenamento: {str(e)}")
                        show_error("Errore", 
                                 f"Impossibile eliminare l'allenamento '{workout_name}': {str(e)}", 
                                 parent=self)
            
            # Rimuovi gli allenamenti dalla lista workouts
            self.workouts = [(wid, wdata) for wid, wdata in self.workouts if wid not in workout_ids_to_remove]
            
            # Rimuovi gli elementi selezionati dalla vista dell'albero
            for item in selection:
                self.workout_tree.delete(item)
            
            # Se è stato eliminato l'allenamento attualmente caricato nell'editor, pulisci l'editor
            if self.current_workout_id and self.current_workout_id in workout_ids_to_remove:
                self.current_workout = None
                self.current_workout_id = None
                self.current_workout_modified = False
                
                # Pulisci i campi dell'editor
                self.name_var.set("")
                self.sport_var.set("running")
                self.date_var.set("")
                self.description_var.set("")
                
                # Aggiorna la lista degli step (la svuota)
                self.update_steps_list()
                
                # Disabilita i pulsanti
                self.save_button.config(state="disabled")
                self.send_button.config(state="disabled")
                self.discard_button.config(state="disabled")
            
            # Mostra messaggio di conferma
            if eliminated > 0 and local_eliminated > 0:
                show_info("Allenamenti eliminati", 
                       f"Eliminati {eliminated} allenamenti da Garmin Connect e {local_eliminated} allenamenti locali", 
                       parent=self)
            elif eliminated > 0:
                show_info("Allenamenti eliminati", 
                       f"Eliminati {eliminated} allenamenti da Garmin Connect", 
                       parent=self)
            elif local_eliminated > 0:
                show_info("Allenamenti eliminati", 
                       f"Eliminati {local_eliminated} allenamenti locali", 
                       parent=self)
                    
        else:  # source == "imported"
            import_export_frame = self.controller.import_export
            
            # Salva gli indici degli allenamenti da eliminare
            indices_to_remove = []
            
            for item in selection:
                workout_id = self.workout_tree.item(item, "tags")[0]
                
                if workout_id.startswith("imported_"):
                    index = int(workout_id.split("_")[1])
                    indices_to_remove.append(index)
            
            # Ordina gli indici in ordine decrescente per evitare problemi
            indices_to_remove.sort(reverse=True)
            
            # Elimina gli allenamenti
            for index in indices_to_remove:
                if index < len(import_export_frame.imported_workouts):
                    del import_export_frame.imported_workouts[index]
            
            # Rimuovi gli elementi selezionati dalla vista dell'albero
            for item in selection:
                self.workout_tree.delete(item)
            
            # Ricarica la lista degli allenamenti importati (necessario per aggiornare gli indici)
            self.load_imported_workouts()
            
            # Se è stato eliminato l'allenamento attualmente caricato nell'editor, pulisci l'editor
            if self.current_workout_id and self.current_workout_id.startswith("imported_"):
                try:
                    index = int(self.current_workout_id.split("_")[1])
                    if index in indices_to_remove:
                        self.current_workout = None
                        self.current_workout_id = None
                        self.current_workout_modified = False
                        
                        # Pulisci i campi dell'editor
                        self.name_var.set("")
                        self.sport_var.set("running")
                        self.date_var.set("")
                        self.description_var.set("")
                        
                        # Aggiorna la lista degli step (la svuota)
                        self.update_steps_list()
                        
                        # Disabilita i pulsanti
                        self.save_button.config(state="disabled")
                        self.send_button.config(state="disabled")
                        self.discard_button.config(state="disabled")
                except (ValueError, IndexError):
                    pass
            
            # Mostra messaggio di conferma
            show_info("Allenamenti eliminati", 
                   f"Eliminati {len(indices_to_remove)} allenamenti dalla lista degli importati", 
                   parent=self)


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
    

    def on_step_selected(self, index, path=None):
        """
        Gestisce la selezione di uno step nella lista.
        
        Args:
            index: Indice dello step selezionato nella lista visualizzata
            path: Percorso completo nell'albero degli step per step nidificati
        """
        # Converti l'indice dell'interfaccia nell'indice originale
        if hasattr(self, 'step_index_map') and 0 <= index < len(self.step_index_map):
            original_index = self.step_index_map[index]
        else:
            original_index = index
        
        # Salva l'indice selezionato e il percorso
        self.selected_step_index = original_index
        self.selected_step_path = path
        
        # Abilita i pulsanti
        self.edit_button.config(state="normal")
        self.delete_step_button.config(state="normal")
        
        # Abilita/disabilita i pulsanti di spostamento
        if original_index > 0:
            prev_step = self.current_workout.workout_steps[original_index - 1]
            if hasattr(prev_step, 'date') and prev_step.date:
                # Se lo step precedente è uno step della data, disabilita il pulsante
                self.move_up_button.config(state="disabled")
            else:
                self.move_up_button.config(state="normal")
        else:
            self.move_up_button.config(state="disabled")
        
        if original_index < len(self.current_workout.workout_steps) - 1:
            self.move_down_button.config(state="normal")
        else:
            self.move_down_button.config(state="disabled")
        
    
    def on_source_change(self):
        """Gestisce il cambio di fonte degli allenamenti."""
        source = self.source_var.get()
        
        if source == "garmin":
            # Abilita il pulsante di refresh solo se siamo connessi a Garmin
            if self.garmin_client:
                self.refresh_button.config(state="normal")
            else:
                self.refresh_button.config(state="disabled")
            
            # Carica gli allenamenti da Garmin se disponibili
            if self.garmin_client and not self.workouts:
                self.refresh_workouts()
        else:  # source == "imported"
            # Disabilita il pulsante di refresh
            self.refresh_button.config(state="disabled")
            
            # Carica gli allenamenti importati
            self.load_imported_workouts()
        
        # Aggiorna la lista
        self.update_workout_list()

    def load_imported_workouts(self):
        """Carica gli allenamenti importati dall'ImportExportFrame."""
        # Accedi all'ImportExportFrame tramite il controller
        import_export_frame = self.controller.import_export
        
        if hasattr(import_export_frame, 'imported_workouts') and import_export_frame.imported_workouts:
            # Converti gli allenamenti importati nel formato usato dal WorkoutEditorFrame
            self.imported_workouts = []
            
            for idx, (name, workout) in enumerate(import_export_frame.imported_workouts):
                # Trova la data dell'allenamento se presente
                workout_date = None
                for step in workout.workout_steps:
                    if hasattr(step, 'date') and step.date:
                        workout_date = step.date
                        break
                
                # Crea un dizionario che simula il formato degli allenamenti di Garmin
                workout_data = {
                    'workoutId': f"imported_{idx}",
                    'workoutName': name,
                    'date': workout_date if workout_date else "",  # Assicurati che sia una stringa vuota se None
                    'sportType': {
                        'sportTypeKey': workout.sport_type
                    },
                    'description': workout.description,
                    'workoutSegments': [
                        {
                            'workoutSteps': workout.workout_steps
                        }
                    ],
                    'source': 'imported'
                }
                
                self.imported_workouts.append((workout_data['workoutId'], workout_data))
        else:
            # Nessun allenamento importato
            self.imported_workouts = []
            
            # Mostra un messaggio se non ci sono allenamenti importati
            if self.source_var.get() == "imported":
                show_info("Nessun allenamento importato", 
                        "Non ci sono allenamenti importati. Importa allenamenti dalla scheda 'Importa/Esporta'.", 
                        parent=self)

    def update_workout_list(self):
        """Aggiorna la lista degli allenamenti disponibili."""
        # Ottieni il filtro
        filter_text = self.filter_var.get().lower()
        
        # Pulisci la lista attuale
        for item in self.workout_tree.get_children():
            self.workout_tree.delete(item)
        
        # Determina la fonte degli allenamenti
        source = self.source_var.get()
        
        # Scegli la lista appropriata in base alla fonte
        if source == "garmin":
            workouts_list = self.workouts
        else:  # source == "imported"
            workouts_list = getattr(self, 'imported_workouts', [])
        
        # Filtra gli allenamenti
        filtered_workouts = []
        for workout_id, workout_data in workouts_list:
            # Estrai i dati dell'allenamento
            if isinstance(workout_data, dict):
                name = workout_data.get('workoutName', '')
            else:
                name = workout_data.workout_name
            
            # Applica il filtro
            if filter_text and filter_text not in name.lower():
                continue
            
            # Aggiungi all'elenco filtrato
            filtered_workouts.append((workout_id, workout_data))
        
        # Aggiungi gli allenamenti filtrati alla lista
        for workout_id, workout_data in filtered_workouts:
            # Estrai il tipo di sport correttamente in base al tipo di dati
            if isinstance(workout_data, dict):
                # Se è un dizionario (come nel caso dei dati importati o di Garmin)
                sport_type = workout_data.get('sportType', {}).get('sportTypeKey', 'running')
                sport_icon = get_icon_for_sport(sport_type)
                
                # Per il conteggio degli step - ESCLUDIAMO QUELLI CON DATA
                step_count = 0
                if 'workoutSegments' in workout_data and workout_data['workoutSegments']:
                    steps = workout_data.get('workoutSegments', [{}])[0].get('workoutSteps', [])
                    # Contiamo solo gli step che non hanno data
                    for step in steps:
                        if isinstance(step, dict) and not ('date' in step and step['date']):
                            step_count += 1
                        elif hasattr(step, 'date') and not step.date:
                            step_count += 1
                
                # Nome dell'allenamento
                name = workout_data.get('workoutName', '')
                
                # Gestione data per dizionari
                date_display = ""
                if workout_data.get('date') and workout_data.get('date').strip():
                    date_str = workout_data.get('date')
                    # Tenta di formattare se nel formato YYYY-MM-DD
                    try:
                        year, month, day = date_str.split('-')
                        date_display = f"{day}/{month}/{year}"
                    except:
                        date_display = date_str
                        
                # Verifica se è un allenamento locale
                is_local = workout_data.get('local', False)
                name_prefix = "[Local] " if is_local else ""
                displayed_name = name_prefix + name
            else:
                # Se è un oggetto Workout
                sport_type = workout_data.sport_type
                sport_icon = get_icon_for_sport(sport_type)
                
                # Conteggio step escludendo quelli con data
                step_count = 0
                for step in workout_data.workout_steps:
                    if not (hasattr(step, 'date') and step.date):
                        step_count += 1
                        
                name = workout_data.workout_name
                displayed_name = name
                
                # Gestione data per oggetti Workout
                date_display = ""
                for step in workout_data.workout_steps:
                    if hasattr(step, 'date') and step.date and step.date.strip():
                        # Converti da YYYY-MM-DD a DD/MM/YYYY
                        try:
                            year, month, day = step.date.split('-')
                            date_display = f"{day}/{month}/{year}"
                        except:
                            date_display = step.date
                        break
            
            # Aggiungi alla lista
            self.workout_tree.insert("", "end", 
                                   values=(displayed_name, f"{sport_icon} {sport_type}", date_display, step_count), 
                                   tags=(workout_id,))   

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
        
        # Determina la fonte dell'allenamento
        source = self.source_var.get()
        
        if source == "garmin":
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
                
                # Trova la data dell'allenamento se presente
                workout_date = ""
                for step in workout.workout_steps:
                    if hasattr(step, 'date') and step.date:
                        # Converti la data da YYYY-MM-DD a DD/MM/YYYY per la visualizzazione
                        try:
                            year, month, day = step.date.split('-')
                            workout_date = f"{day}/{month}/{year}"
                        except:
                            workout_date = step.date
                        break
                
                # Aggiorna i campi
                self.name_var.set(workout.workout_name)
                self.sport_var.set(workout.sport_type)
                self.date_var.set(workout_date)
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
        else:  # source == "imported"
            try:
                # Trova l'allenamento importato
                import_export_frame = self.controller.import_export
                
                # L'ID per gli allenamenti importati è nel formato "imported_X"
                if workout_id.startswith("imported_"):
                    index = int(workout_id.split("_")[1])
                    if index < len(import_export_frame.imported_workouts):
                        name, workout = import_export_frame.imported_workouts[index]
                        
                        # Imposta l'allenamento corrente
                        self.current_workout = workout
                        self.current_workout_id = workout_id  # Memorizza l'ID importato
                        self.current_workout_modified = False
                        
                        # Trova la data dell'allenamento se presente
                        workout_date = ""
                        for step in workout.workout_steps:
                            if hasattr(step, 'date') and step.date:
                                workout_date = step.date
                                break
                        
                        # Aggiorna i campi
                        self.name_var.set(workout.workout_name)
                        self.sport_var.set(workout.sport_type)
                        if workout_date:
                            try:
                                year, month, day = workout_date.split('-')
                                self.date_var.set(f"{day}/{month}/{year}")
                            except:
                                self.date_var.set(workout_date)
                        else:
                            self.date_var.set("")

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
                        self.controller.set_status(f"Allenamento importato '{workout.workout_name}' caricato")
                        return
                    
                # Se arriviamo qui, l'allenamento non è stato trovato
                show_error("Errore", "Allenamento importato non trovato", parent=self)
            
            except Exception as e:
                logging.error(f"Errore nel caricamento dell'allenamento importato: {str(e)}")
                show_error("Errore", 
                        f"Impossibile caricare l'allenamento: {str(e)}", 
                        parent=self)

    def on_workouts_imported(self):
        """Chiamato quando vengono importati nuovi allenamenti."""
        # Se siamo nella visualizzazione degli allenamenti importati, aggiorna la lista
        if self.source_var.get() == "imported":
            self.load_imported_workouts()
            self.update_workout_list()
    
    def refresh_workouts(self):
        """Aggiorna la lista degli allenamenti da Garmin Connect."""
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Aggiorna lo stato per informare l'utente
            self.controller.set_status("Aggiornamento allenamenti da Garmin Connect...")
            
            # Ottieni la lista degli allenamenti
            workouts_data = self.garmin_client.list_workouts()
            
            # Conserva gli allenamenti locali
            local_workouts = [(wid, wdata) for wid, wdata in self.workouts if wid.startswith("local_") or (isinstance(wdata, dict) and wdata.get('local', False))]
            
            # Trasforma in una lista di tuple (id, data)
            garmin_workouts = []
            for workout in workouts_data:
                workout_id = str(workout.get('workoutId', ''))
                garmin_workouts.append((workout_id, workout))
            
            # Unisci gli allenamenti Garmin con quelli locali
            self.workouts = garmin_workouts + local_workouts
            
            # Aggiorna la lista solo se siamo in modalità Garmin
            if self.source_var.get() == "garmin":
                self.update_workout_list()
            
            # Mostra messaggio di conferma
            count_garmin = len(garmin_workouts)
            count_local = len(local_workouts)
            
            msg_status = f"Allenamenti aggiornati da Garmin Connect: {count_garmin} remoti, {count_local} locali"
            self.controller.set_status(msg_status)
            
        except Exception as e:
            logging.error(f"Errore nell'aggiornamento degli allenamenti: {str(e)}")
            show_error("Errore", 
                     f"Impossibile aggiornare gli allenamenti: {str(e)}", 
                     parent=self)
            self.controller.set_status("Errore nell'aggiornamento degli allenamenti")


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
        self.date_var.set("")  # Nessuna data per il nuovo allenamento
        
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
        steps_to_show = [s for s in self.current_workout.workout_steps if not (hasattr(s, 'date') and s.date)]
        
        if not steps_to_show:
            ttk.Label(self.steps_container, text="L'allenamento non ha step").pack()
            return
        
        # Crea una mappa degli indici dalla lista filtrata alla lista originale
        self.step_index_map = []
        for i, step in enumerate(self.current_workout.workout_steps):
            if not (hasattr(step, 'date') and step.date):
                self.step_index_map.append(i)
        
        # Crea i widget per gli step
        for i, step in enumerate(steps_to_show):
            self.create_step_widget(self.steps_container, step, i)
    
    def create_step_widget(self, parent, step, index, indent=0, parent_indices=None):
        """
        Crea un widget per uno step.
        
        Args:
            parent: Widget genitore
            step: Step da visualizzare
            index: Indice dello step nella lista filtrata
            indent: Livello di indentazione (per step nidificati)
            parent_indices: Lista di indici per step nidificati (percorso completo nell'albero degli step)
        """
        # Se parent_indices è None, inizializza con una lista vuota
        if parent_indices is None:
            parent_indices = []
        
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
            app_config = get_config()
            target_text = "Target: "
            
            # MODIFICATO: Cerca di trovare la zona corrispondente ai valori
            if hasattr(step.target, 'target_zone_name') and step.target.target_zone_name:
                # Già abbiamo il nome della zona, usiamolo direttamente
                target_text += f"Zona {step.target.target_zone_name}"
            elif step.target.target == "pace.zone":
                from_value = step.target.from_value
                to_value = step.target.to_value
                
                if from_value and to_value:
                    # Converti da m/s a min/km per visualizzazione
                    min_pace_secs = int(1000 / from_value)
                    max_pace_secs = int(1000 / to_value)
                    
                    min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                    max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                    
                    # Cerca la zona corrispondente
                    paces = app_config.get(f'sports.{self.current_workout.sport_type}.paces', {})
                    zone_name = None
                    
                    for name, pace_range in paces.items():
                        if '-' in pace_range:
                            pace_min, pace_max = pace_range.split('-')
                            pace_min = pace_min.strip()
                            pace_max = pace_max.strip()
                            
                            # Controllo se i passi corrispondono alla zona (con tolleranza di alcuni secondi)
                            min_secs = self._pace_to_seconds(pace_min)
                            max_secs = self._pace_to_seconds(pace_max)
                            step_min_secs = min_pace_secs
                            step_max_secs = max_pace_secs
                            
                            # Usiamo una tolleranza di 5 secondi per ogni valore
                            if (abs(min_secs - step_min_secs) <= 5 and 
                                abs(max_secs - step_max_secs) <= 5):
                                zone_name = name
                                break
                    
                    if zone_name:
                        # Se abbiamo trovato una zona corrispondente, usiamola
                        target_text += f"Zona {zone_name}"
                        # Aggiorniamo anche l'oggetto target per usi futuri
                        step.target.target_zone_name = zone_name
                    else:
                        # Altrimenti mostriamo i valori numerici
                        target_text += f"Passo {min_pace}-{max_pace} min/km"
                    
                elif from_value:  # Solo valore minimo
                    min_pace_secs = int(1000 / from_value)
                    min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                    target_text += f"Passo {min_pace} min/km"
                elif to_value:  # Solo valore massimo
                    max_pace_secs = int(1000 / to_value)
                    max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                    target_text += f"Passo {max_pace} min/km"
                    
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
                                
                                # Controllo con tolleranza
                                if (abs(hr_min - from_value) <= 3 and 
                                    abs(hr_max - to_value) <= 3):
                                    zone_name = name.replace('_HR', '')
                                    break
                    
                    if zone_name:
                        target_text += f"Zona {zone_name}"
                        # Aggiorniamo anche l'oggetto target per usi futuri
                        step.target.target_zone_name = zone_name
                    else:
                        target_text += f"FC {from_value}-{to_value} bpm"
                
                elif from_value:  # Solo valore minimo
                    target_text += f"FC > {from_value} bpm"
                elif to_value:  # Solo valore massimo
                    target_text += f"FC < {to_value} bpm"
                    
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
                            if (abs(int(power_min) - from_value) <= 2 and 
                                abs(int(power_max) - to_value) <= 2):
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
                        target_text += f"Zona {zone_name}"
                        # Aggiorniamo anche l'oggetto target per usi futuri
                        step.target.target_zone_name = zone_name
                    else:
                        target_text += f"Potenza {from_value}-{to_value} W"
                
                elif from_value:  # Solo valore minimo
                    target_text += f"Potenza > {from_value} W"
                elif to_value:  # Solo valore massimo
                    target_text += f"Potenza < {to_value} W"
            
            ttk.Label(details_frame, text="  •  " + target_text).pack(side=tk.LEFT)
        
        # Descrizione
        if step.description:
            ttk.Label(details_frame, text=f"  •  {step.description}").pack(side=tk.LEFT)
        
        # Costruisci il percorso completo per questo step
        current_path = parent_indices + [self.step_index_map[index]]
        
        # Step ripetizioni
        if step.step_type == "repeat" and step.workout_steps:
            # Crea un frame per gli step figli
            child_frame = ttk.Frame(parent)
            child_frame.pack(fill=tk.X, padx=(indent * 20 + 20, 0), pady=0)
            
            # Crea una mappa degli indici per gli step interni della ripetizione
            child_index_map = []
            for i, child_step in enumerate(step.workout_steps):
                child_index_map.append(i)
            
            # Crea i widget per gli step figli
            for i, child_step in enumerate(step.workout_steps):
                # Costruisci il percorso per questo figlio
                child_path = current_path + [i]
                # Nota: per gli step figli, passiamo -1 come indice perché non sono nella mappa principale
                self.create_child_step_widget(child_frame, child_step, i, indent + 1, child_path, child_index_map)
        
        # Associa eventi
        content_frame.bind("<Button-1>", lambda e, idx=index, path=current_path: self.on_step_selected(idx, path))
        header_frame.bind("<Button-1>", lambda e, idx=index, path=current_path: self.on_step_selected(idx, path))
        details_frame.bind("<Button-1>", lambda e, idx=index, path=current_path: self.on_step_selected(idx, path))
        
        # Doppio click per modificare
        content_frame.bind("<Double-1>", lambda e: self.edit_step())
        header_frame.bind("<Double-1>", lambda e: self.edit_step())
        details_frame.bind("<Double-1>", lambda e: self.edit_step())


    # Metodo di supporto per convertire una stringa di passo (formato "m:ss") in secondi totali
    def _pace_to_seconds(self, pace_str):
        """Converte una stringa di passo formato m:ss in secondi totali."""
        if not pace_str or ':' not in pace_str:
            return 0
        try:
            minutes, seconds = pace_str.split(':')
            return int(minutes.strip()) * 60 + int(seconds.strip())
        except (ValueError, TypeError):
            return 0

    def create_child_step_widget(self, parent, step, index, indent=0, path=None, index_map=None):
        """
        Crea un widget per uno step figlio all'interno di una ripetizione.
        
        Args:
            parent: Widget genitore
            step: Step da visualizzare
            index: Indice dello step nella lista del genitore
            indent: Livello di indentazione
            path: Percorso completo nell'albero degli step
            index_map: Mappa degli indici per questo livello
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
            app_config = get_config()
            target_text = "Target: "
            
            # MODIFICATO: Cerca di trovare la zona corrispondente ai valori
            if hasattr(step.target, 'target_zone_name') and step.target.target_zone_name:
                # Già abbiamo il nome della zona, usiamolo direttamente
                target_text += f"Zona {step.target.target_zone_name}"
            elif step.target.target == "pace.zone":
                from_value = step.target.from_value
                to_value = step.target.to_value
                
                if from_value and to_value:
                    # Converti da m/s a min/km per visualizzazione
                    min_pace_secs = int(1000 / from_value)
                    max_pace_secs = int(1000 / to_value)
                    
                    min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                    max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                    
                    # Cerca la zona corrispondente
                    paces = app_config.get(f'sports.{self.current_workout.sport_type}.paces', {})
                    zone_name = None
                    
                    for name, pace_range in paces.items():
                        if '-' in pace_range:
                            pace_min, pace_max = pace_range.split('-')
                            pace_min = pace_min.strip()
                            pace_max = pace_max.strip()
                            
                            # Controllo se i passi corrispondono alla zona (con tolleranza di alcuni secondi)
                            min_secs = self._pace_to_seconds(pace_min)
                            max_secs = self._pace_to_seconds(pace_max)
                            step_min_secs = min_pace_secs
                            step_max_secs = max_pace_secs
                            
                            # Usiamo una tolleranza di 5 secondi per ogni valore
                            if (abs(min_secs - step_min_secs) <= 5 and 
                                abs(max_secs - step_max_secs) <= 5):
                                zone_name = name
                                break
                    
                    if zone_name:
                        # Se abbiamo trovato una zona corrispondente, usiamola
                        target_text += f"Zona {zone_name}"
                        # Aggiorniamo anche l'oggetto target per usi futuri
                        step.target.target_zone_name = zone_name
                    else:
                        # Altrimenti mostriamo i valori numerici
                        target_text += f"Passo {min_pace}-{max_pace} min/km"
                    
                elif from_value:  # Solo valore minimo
                    min_pace_secs = int(1000 / from_value)
                    min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                    target_text += f"Passo {min_pace} min/km"
                elif to_value:  # Solo valore massimo
                    max_pace_secs = int(1000 / to_value)
                    max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                    target_text += f"Passo {max_pace} min/km"
                    
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
                                
                                # Controllo con tolleranza
                                if (abs(hr_min - from_value) <= 3 and 
                                    abs(hr_max - to_value) <= 3):
                                    zone_name = name.replace('_HR', '')
                                    break
                    
                    if zone_name:
                        target_text += f"Zona {zone_name}"
                        # Aggiorniamo anche l'oggetto target per usi futuri
                        step.target.target_zone_name = zone_name
                    else:
                        target_text += f"FC {from_value}-{to_value} bpm"
                
                elif from_value:  # Solo valore minimo
                    target_text += f"FC > {from_value} bpm"
                elif to_value:  # Solo valore massimo
                    target_text += f"FC < {to_value} bpm"
                    
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
                            if (abs(int(power_min) - from_value) <= 2 and 
                                abs(int(power_max) - to_value) <= 2):
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
                        target_text += f"Zona {zone_name}"
                        # Aggiorniamo anche l'oggetto target per usi futuri
                        step.target.target_zone_name = zone_name
                    else:
                        target_text += f"Potenza {from_value}-{to_value} W"
                
                elif from_value:  # Solo valore minimo
                    target_text += f"Potenza > {from_value} W"
                elif to_value:  # Solo valore massimo
                    target_text += f"Potenza < {to_value} W"
            
            ttk.Label(details_frame, text="  •  " + target_text).pack(side=tk.LEFT)
        
        # Descrizione
        if step.description:
            ttk.Label(details_frame, text=f"  •  {step.description}").pack(side=tk.LEFT)
        
        # Associa eventi - nota che passiamo il percorso completo
        content_frame.bind("<Button-1>", lambda e, p=path: self.on_nested_step_selected(p))
        header_frame.bind("<Button-1>", lambda e, p=path: self.on_nested_step_selected(p))
        details_frame.bind("<Button-1>", lambda e, p=path: self.on_nested_step_selected(p))
        
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

    def on_nested_step_selected(self, path):
        """
        Gestisce la selezione di uno step nidificato (figlio di una ripetizione).
        
        Args:
            path: Percorso completo nell'albero degli step
        """
        # Salva il percorso selezionato
        self.selected_step_path = path
        self.selected_step_index = None  # Impostiamo a None perché non è un indice diretto
        
        # Abilita i pulsanti di modifica
        self.edit_button.config(state="normal")
        self.delete_step_button.config(state="normal")
        
        # Disabilita i pulsanti di spostamento per step nidificati
        self.move_up_button.config(state="disabled")
        self.move_down_button.config(state="disabled")

    def save_workout(self):
        """Salva le modifiche all'allenamento corrente."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Ottieni la data dall'interfaccia e verificala
        display_date_str = self.date_var.get()
        if display_date_str and not is_valid_display_date(display_date_str):
            show_error("Errore", "La data deve essere nel formato GG/MM/AAAA", parent=self)
            return
        
        # Converti la data nel formato interno YYYY-MM-DD
        date_str = convert_date_for_garmin(display_date_str)
        
        # Aggiorna i dati dell'allenamento dai campi
        self.current_workout.workout_name = self.name_var.get()
        self.current_workout.sport_type = self.sport_var.get()
        self.current_workout.description = self.description_var.get()
        
        # Gestisci la data dell'allenamento
        date_step = None
        
        # Cerca uno step esistente con la data
        for step in self.current_workout.workout_steps:
            if hasattr(step, 'date') and step.date:
                date_step = step
                break
        
        # Se c'è una data nel campo
        if date_str:
            if date_step:
                # Aggiorna lo step esistente
                date_step.date = date_str
            else:
                # Crea un nuovo step con la data
                date_step = WorkoutStep(0, "warmup")
                date_step.date = date_str
                # Aggiungi come primo step
                self.current_workout.workout_steps.insert(0, date_step)
        elif date_step:
            # Rimuovi lo step della data se il campo è vuoto
            self.current_workout.workout_steps.remove(date_step)
        
        # Determina la fonte degli allenamenti
        source = self.source_var.get()
        
        if source == "garmin":
            # Salva nella lista locale senza inviare a Garmin Connect
            # Assegna un ID temporaneo se non esiste
            if not self.current_workout_id:
                self.current_workout_id = f"local_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                
            # Aggiorna la lista degli allenamenti
            workout_found = False
            for i, (workout_id, workout_data) in enumerate(self.workouts):
                if workout_id == self.current_workout_id:
                    # Aggiorna l'allenamento esistente
                    workout_data_updated = {
                        'workoutId': self.current_workout_id,
                        'workoutName': self.current_workout.workout_name,
                        'sportType': {'sportTypeKey': self.current_workout.sport_type},
                        'description': self.current_workout.description,
                        'date': date_str,
                        'local': True  # Indica che è un allenamento locale
                    }
                    self.workouts[i] = (self.current_workout_id, workout_data_updated)
                    workout_found = True
                    break
            
            if not workout_found:
                # Aggiungi un nuovo allenamento
                workout_data = {
                    'workoutId': self.current_workout_id,
                    'workoutName': self.current_workout.workout_name,
                    'sportType': {'sportTypeKey': self.current_workout.sport_type},
                    'description': self.current_workout.description,
                    'date': date_str,
                    'local': True  # Indica che è un allenamento locale
                }
                self.workouts.append((self.current_workout_id, workout_data))
            
            # Resetta il flag di modifica
            self.current_workout_modified = False
            
            # Aggiorna la lista
            self.update_workout_list()
            
            # Mostra messaggio di conferma
            show_info("Allenamento salvato", 
                   f"L'allenamento '{self.current_workout.workout_name}' è stato salvato localmente", 
                   parent=self)
            
        else:  # source == "imported"
            # Salva nella lista degli importati
            import_export_frame = self.controller.import_export
            if not hasattr(import_export_frame, 'imported_workouts'):
                import_export_frame.imported_workouts = []
            
            # Cerca se l'allenamento è già presente
            found = False
            if self.current_workout_id and self.current_workout_id.startswith("imported_"):
                index = int(self.current_workout_id.split("_")[1])
                if index < len(import_export_frame.imported_workouts):
                    # Aggiorna l'allenamento esistente
                    import_export_frame.imported_workouts[index] = (self.current_workout.workout_name, self.current_workout)
                    found = True
            
            if not found:
                # Aggiungi un nuovo allenamento
                import_export_frame.imported_workouts.append((self.current_workout.workout_name, self.current_workout))
                # Assegna un ID importato
                self.current_workout_id = f"imported_{len(import_export_frame.imported_workouts) - 1}"
            
            # Resetta il flag di modifica
            self.current_workout_modified = False
            
            # Aggiorna la lista degli allenamenti
            self.load_imported_workouts()
            self.update_workout_list()
            
            # Mostra messaggio di conferma
            show_info("Allenamento salvato", 
                   f"L'allenamento '{self.current_workout.workout_name}' è stato salvato nella lista degli importati", 
                   parent=self)
        
    def send_to_garmin(self):
        """Invia l'allenamento corrente a Garmin Connect."""
        # Verifica che ci sia un allenamento corrente
        if not self.current_workout:
            return
        
        # Ottieni la data dall'interfaccia
        display_date_str = self.date_var.get()
        
        # Verifica che la data sia in un formato valido (GG/MM/AAAA o YYYY-MM-DD)
        if display_date_str and not is_valid_display_date(display_date_str):
            show_error("Errore", "La data deve essere nel formato GG/MM/AAAA", parent=self)
            return
        
        # Converti la data nel formato richiesto da Garmin Connect (YYYY-MM-DD)
        date_str = convert_date_for_garmin(display_date_str)
        
        # Aggiorna i dati dell'allenamento dai campi
        self.current_workout.workout_name = self.name_var.get()
        self.current_workout.sport_type = self.sport_var.get()
        self.current_workout.description = self.description_var.get()
        
        # Gestisci la data dell'allenamento
        date_step = None
        
        # Cerca uno step esistente con la data
        for step in self.current_workout.workout_steps:
            if hasattr(step, 'date') and step.date:
                date_step = step
                break
        
        # Se c'è una data nel campo
        if display_date_str:
            if date_step:
                # Aggiorna lo step esistente con la data convertita
                date_step.date = date_str
            else:
                # Crea un nuovo step con la data convertita
                date_step = WorkoutStep(0, "warmup")
                date_step.date = date_str
                # Aggiungi come primo step
                self.current_workout.workout_steps.insert(0, date_step)
        elif date_step:
            # Rimuovi lo step della data se il campo è vuoto
            self.current_workout.workout_steps.remove(date_step)
        
        # Verifica che ci sia un client Garmin
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Informare l'utente che l'invio è in corso
            self.controller.set_status("Invio dell'allenamento a Garmin Connect in corso...")
            
            # Crea un nuovo allenamento su Garmin Connect
            response = self.garmin_client.add_workout(self.current_workout)
            
            # Ottieni l'ID del nuovo allenamento
            if response and 'workoutId' in response:
                new_workout_id = str(response['workoutId'])
                
                # Informare l'utente che l'allenamento è stato creato
                self.controller.set_status(f"Allenamento creato su Garmin Connect (ID: {new_workout_id})")
                
                # Se era un allenamento locale, rimuovilo dalla lista locale
                if self.current_workout_id and self.current_workout_id.startswith("local_"):
                    for i, (workout_id, workout_data) in enumerate(self.workouts):
                        if workout_id == self.current_workout_id:
                            # Rimuovi il vecchio allenamento dalla lista workouts
                            self.workouts.pop(i)
                            break
                
                # Aggiorna l'ID corrente
                old_workout_id = self.current_workout_id
                self.current_workout_id = new_workout_id
                
                # Pianifica l'allenamento se è specificata una data
                if date_str:
                    self.controller.set_status(f"Pianificazione dell'allenamento per {display_date_str}...")
                    schedule_response = self.garmin_client.schedule_workout(new_workout_id, date_str)
                    if not schedule_response:
                        logging.warning(f"Impossibile pianificare l'allenamento per la data {date_str}")
                        self.controller.set_status("Allenamento creato ma non pianificato")
                    else:
                        self.controller.set_status(f"Allenamento pianificato per {display_date_str}")
                
                # Resetta il flag di modifica
                self.current_workout_modified = False
                
                # Aggiorna la lista degli allenamenti da Garmin Connect
                self.controller.set_status("Aggiornamento della lista allenamenti...")
                workouts_data = self.garmin_client.list_workouts()
                
                # Conserva gli allenamenti locali
                local_workouts = [(wid, wdata) for wid, wdata in self.workouts if wid.startswith("local_") or (isinstance(wdata, dict) and wdata.get('local', False))]
                
                # Trasforma in una lista di tuple (id, data)
                garmin_workouts = []
                for workout in workouts_data:
                    workout_id = str(workout.get('workoutId', ''))
                    garmin_workouts.append((workout_id, workout))
                
                # Unisci gli allenamenti Garmin con quelli locali
                self.workouts = garmin_workouts + local_workouts
                
                # Cancella completamente la lista visibile
                for item in self.workout_tree.get_children():
                    self.workout_tree.delete(item)
                    
                # Aggiungi tutti gli allenamenti alla UI
                self.update_workout_list()
                
                # Seleziona il nuovo allenamento nell'albero
                for item in self.workout_tree.get_children():
                    if self.workout_tree.item(item, "tags")[0] == new_workout_id:
                        self.workout_tree.selection_set(item)
                        self.workout_tree.see(item)  # Assicura che sia visibile
                        break
                
                # Mostra messaggio di conferma
                if date_str:
                    show_info("Allenamento inviato e pianificato", 
                           f"L'allenamento '{self.current_workout.workout_name}' è stato inviato a Garmin Connect e pianificato per il {display_date_str}", 
                           parent=self)
                    self.controller.set_status(f"Allenamento '{self.current_workout.workout_name}' inviato e pianificato per {display_date_str}")
                else:
                    show_info("Allenamento inviato", 
                           f"L'allenamento '{self.current_workout.workout_name}' è stato inviato a Garmin Connect", 
                           parent=self)
                    self.controller.set_status(f"Allenamento '{self.current_workout.workout_name}' inviato a Garmin Connect")
            else:
                raise ValueError("Risposta non valida da Garmin Connect")
            
        except Exception as e:
            logging.error(f"Errore nell'invio dell'allenamento: {str(e)}")
            show_error("Errore", 
                     f"Impossibile inviare l'allenamento: {str(e)}", 
                     parent=self)
            self.controller.set_status(f"Errore: {str(e)}")
        
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
            source = self.source_var.get()
            
            if source == "garmin":
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
                    
                    # Trova la data dell'allenamento se presente
                    workout_date = ""
                    for step in workout.workout_steps:
                        if hasattr(step, 'date') and step.date:
                            workout_date = step.date
                            break
                    
                    # Aggiorna i campi
                    self.name_var.set(workout.workout_name)
                    self.sport_var.set(workout.sport_type)
                    self.date_var.set(workout_date)
                    self.description_var.set(workout.description or "")
                    
                    # Aggiorna la lista degli step
                    self.update_steps_list()
                    
                except Exception as e:
                    logging.error(f"Errore nel recupero dell'allenamento: {str(e)}")
                    show_error("Errore", 
                             f"Impossibile recuperare l'allenamento: {str(e)}", 
                             parent=self)
            else:  # source == "imported"
                try:
                    # Trova l'allenamento importato
                    import_export_frame = self.controller.import_export
                    
                    if self.current_workout_id.startswith("imported_"):
                        index = int(self.current_workout_id.split("_")[1])
                        if index < len(import_export_frame.imported_workouts):
                            name, workout = import_export_frame.imported_workouts[index]
                            
                            # Imposta l'allenamento corrente
                            self.current_workout = workout
                            self.current_workout_modified = False
                            
                            # Trova la data dell'allenamento se presente
                            workout_date = ""
                            for step in workout.workout_steps:
                                if hasattr(step, 'date') and step.date:
                                    workout_date = step.date
                                    break
                            
                            # Aggiorna i campi
                            self.name_var.set(workout.workout_name)
                            self.sport_var.set(workout.sport_type)
                            self.date_var.set(workout_date)
                            self.description_var.set(workout.description or "")
                            
                            # Aggiorna la lista degli step
                            self.update_steps_list()
                except Exception as e:
                    logging.error(f"Errore nel recupero dell'allenamento importato: {str(e)}")
                    show_error("Errore", 
                             f"Impossibile recuperare l'allenamento: {str(e)}", 
                             parent=self)
        else:
            # È un nuovo allenamento, crea uno vuoto
            self.new_workout()


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
        self.date_var.set("")
        
        # Aggiorna la lista degli step
        self.update_steps_list()
        
        # Disabilita i pulsanti
        self.save_button.config(state="disabled")
        self.send_button.config(state="disabled")
        self.discard_button.config(state="disabled")
        
        # Aggiorna lo stato
        self.controller.set_status("Disconnesso da Garmin Connect")
    
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