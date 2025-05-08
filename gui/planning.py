#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog e utility per la pianificazione degli allenamenti.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import calendar
import datetime
import re
from typing import Dict, Any, List, Tuple, Optional, Callable

from garmin_planner_gui.config import get_config
from garmin_planner_gui.models.workout import Workout
from garmin_planner_gui.gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no,
    format_workout_name, parse_workout_name, get_weeks_from_workouts,
    get_sessions_per_week, extract_sport_from_steps, date_to_weekday
)
from garmin_planner_gui.gui.styles import get_color_for_sport, get_icon_for_sport
from garmin_planner_gui.gui.dialogs.date_picker import DatePickerDialog


class ScheduleDialog(tk.Toplevel):
    """Dialog per pianificare gli allenamenti."""
    
    def __init__(self, parent, workouts: List[Tuple[str, Workout]]):
        """
        Inizializza il dialog.
        
        Args:
            parent: Widget genitore
            workouts: Lista di tuple (nome, allenamento)
        """
        super().__init__(parent)
        self.parent = parent
        self.workouts = workouts
        self.config = get_config()
        
        # Lista degli allenamenti pianificati
        self.scheduled_workouts = []
        
        # Configurazione preesistente
        self.race_day = self.config.get('planning.race_day', '')
        self.preferred_days = self.config.get('planning.preferred_days', [1, 3, 5])  # Default: Lun, Mer, Ven
        
        # Configura il dialog
        self.title("Pianificazione allenamenti")
        self.geometry("800x600")
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
        
        # Analizza i workouts per trovare le settimane disponibili
        self.analyze_workouts()
        
        # Aggiungi i callback
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        """Crea i widget del dialog."""
        # Frame principale con padding
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Intestazione
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text="Pianificazione allenamenti", 
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        # Configurazione della pianificazione
        config_frame = ttk.LabelFrame(main_frame, text="Configurazione")
        config_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Grid per allineare i campi
        grid_frame = ttk.Frame(config_frame)
        grid_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Data della gara
        ttk.Label(grid_frame, text="Data della gara:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        race_day_frame = ttk.Frame(grid_frame)
        race_day_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        self.race_day_var = tk.StringVar(value=self.race_day)
        self.race_day_entry = ttk.Entry(race_day_frame, textvariable=self.race_day_var, width=15)
        self.race_day_entry.pack(side=tk.LEFT)
        
        create_tooltip(self.race_day_entry, "Data della gara nel formato YYYY-MM-DD")
        
        ttk.Button(race_day_frame, text="Seleziona...", 
                 command=self.select_race_day).pack(side=tk.LEFT, padx=(5, 0))
        
        # Giorni preferiti
        ttk.Label(grid_frame, text="Giorni preferiti:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        days_frame = ttk.Frame(grid_frame)
        days_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        days = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        
        self.day_vars = []
        for i, day in enumerate(days):
            var = tk.BooleanVar(value=i in self.preferred_days)
            self.day_vars.append(var)
            
            check = ttk.Checkbutton(days_frame, text=day, variable=var)
            check.pack(side=tk.LEFT, padx=(0 if i == 0 else 5, 0))
        
        # Pianificazione
        planning_frame = ttk.LabelFrame(main_frame, text="Pianificazione")
        planning_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Pulsanti di azione
        buttons_frame = ttk.Frame(planning_frame)
        buttons_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(buttons_frame, text="Seleziona la settimana:").pack(side=tk.LEFT)
        
        self.week_var = tk.StringVar()
        self.week_combo = ttk.Combobox(buttons_frame, textvariable=self.week_var, 
                                     width=10, state="readonly")
        self.week_combo.pack(side=tk.LEFT, padx=5)
        
        # Associa evento di selezione della settimana
        self.week_combo.bind("<<ComboboxSelected>>", self.on_week_selected)
        
        ttk.Button(buttons_frame, text="Pianifica settimana", 
                 command=self.schedule_week).pack(side=tk.LEFT, padx=(20, 5))
        
        ttk.Button(buttons_frame, text="Pianifica tutto", 
                 command=self.schedule_all).pack(side=tk.LEFT)
        
        ttk.Button(buttons_frame, text="Cancella pianificazione", 
                 command=self.clear_schedule).pack(side=tk.RIGHT)
        
        # Lista degli allenamenti pianificati
        list_frame = ttk.Frame(planning_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Crea il treeview
        columns = ("date", "name", "sport", "day")
        self.schedule_tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                                        selectmode="browse")
        
        # Intestazioni
        self.schedule_tree.heading("date", text="Data")
        self.schedule_tree.heading("name", text="Nome")
        self.schedule_tree.heading("sport", text="Sport")
        self.schedule_tree.heading("day", text="Giorno")
        
        # Larghezze colonne
        self.schedule_tree.column("date", width=100)
        self.schedule_tree.column("name", width=300)
        self.schedule_tree.column("sport", width=100)
        self.schedule_tree.column("day", width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.schedule_tree.yview)
        self.schedule_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.schedule_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Pulsanti
        dialog_buttons_frame = ttk.Frame(main_frame)
        dialog_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(dialog_buttons_frame, text="OK", 
                 command=self.on_ok, width=10).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(dialog_buttons_frame, text="Annulla", 
                 command=self.on_cancel, width=10).pack(side=tk.RIGHT, padx=(5, 0))
    
    def analyze_workouts(self):
        """Analizza gli allenamenti per trovare le settimane disponibili."""
        # Estrai le settimane dai nomi degli allenamenti
        self.weeks = get_weeks_from_workouts(self.workouts)
        
        # Conta il numero di sessioni per ogni settimana
        self.sessions_per_week = get_sessions_per_week(self.workouts)
        
        # Aggiorna la combo delle settimane
        if self.weeks:
            self.week_combo['values'] = [f"Week {w:02d}" for w in self.weeks]
            self.week_combo.current(0)
            
            # Seleziona la prima settimana
            self.on_week_selected()
        else:
            self.week_combo['values'] = []
            self.week_var.set("")
    
    def select_race_day(self):
        """Seleziona la data della gara."""
        def on_date_selected(date):
            if date:
                self.race_day_var.set(date)
        
        # Mostra il dialog per selezionare la data
        date_picker = DatePickerDialog(self, 
                                    title="Seleziona la data della gara", 
                                    initial_date=self.race_day_var.get(),
                                    callback=on_date_selected)
    
    def on_week_selected(self, event=None):
        """
        Gestisce la selezione di una settimana.
        
        Args:
            event: Evento Tkinter (opzionale)
        """
        # Ottieni la settimana selezionata
        week_str = self.week_var.get()
        if not week_str:
            return
        
        # Estrai il numero di settimana
        week = int(week_str.split()[-1])
        
        # Filtra gli allenamenti per questa settimana
        self.current_week_workouts = []
        for name, workout in self.workouts:
            parsed_week, _, _ = parse_workout_name(name)
            if parsed_week == week:
                self.current_week_workouts.append((name, workout))
    
    def schedule_week(self):
        """Pianifica gli allenamenti per la settimana selezionata."""
        # Verifica che sia selezionata una settimana
        week_str = self.week_var.get()
        if not week_str:
            show_error("Errore", "Seleziona una settimana", parent=self)
            return
        
        # Verifica che ci sia una data di gara
        race_day = self.race_day_var.get()
        if not race_day:
            show_error("Errore", "Inserisci la data della gara", parent=self)
            return
        
        # Verifica che la data sia valida
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', race_day):
            show_error("Errore", "La data della gara deve essere nel formato YYYY-MM-DD", parent=self)
            return
        
        # Estrai il numero di settimana
        week = int(week_str.split()[-1])
        
        # Filtra gli allenamenti per questa settimana
        week_workouts = []
        for name, workout in self.workouts:
            parsed_week, _, _ = parse_workout_name(name)
            if parsed_week == week:
                week_workouts.append((name, workout))
        
        # Verifica che ci siano allenamenti
        if not week_workouts:
            show_error("Errore", f"Non ci sono allenamenti per la settimana {week}", parent=self)
            return
        
        # Calcola la data di inizio della settimana
        race_date = datetime.datetime.strptime(race_day, '%Y-%m-%d').date()
        
        # La settimana 0 è quella della gara, le altre settimane sono a ritroso
        week_start = race_date - datetime.timedelta(days=race_date.weekday() + 7 * week)
        
        # Giorni preferiti (0 = lunedì, 6 = domenica)
        preferred_days = []
        for i, var in enumerate(self.day_vars):
            if var.get():
                preferred_days.append(i)
        
        # Verifica che ci siano giorni preferiti
        if not preferred_days:
            show_error("Errore", "Seleziona almeno un giorno preferito", parent=self)
            return
        
        # Ordina gli allenamenti per nome
        week_workouts.sort(key=lambda x: x[0])
        
        # Pianifica gli allenamenti
        scheduled = []
        
        # Usa i giorni preferiti per assegnare le date
        for i, (name, workout) in enumerate(week_workouts):
            # Ottieni la sessione dall'allenamento
            _, session, _ = parse_workout_name(name)
            
            if session is None:
                # Se non c'è il numero di sessione nel nome, usa l'indice
                session = i + 1
            
            # Calcola il giorno nella settimana
            day_idx = i % len(preferred_days)
            weekday = preferred_days[day_idx]
            
            # Calcola la data
            days_to_add = (weekday - week_start.weekday()) % 7
            workout_date = week_start + datetime.timedelta(days=days_to_add)
            
            # Se questa data è già stata usata, prova il giorno successivo
            used_dates = [date for date, _, _ in scheduled]
            while workout_date in used_dates:
                workout_date += datetime.timedelta(days=1)
            
            # Aggiungi alla lista
            scheduled.append((workout_date, name, workout))
        
        # Aggiungi agli allenamenti pianificati
        for date, name, workout in scheduled:
            # Aggiungi la data all'allenamento
            date_str = date.strftime('%Y-%m-%d')
            
            # Verifica se c'è già un allenamento per questa data
            for i, (existing_date, existing_name, existing_workout) in enumerate(self.scheduled_workouts):
                if existing_date == date_str:
                    # Chiedi se sovrascrivere
                    if not ask_yes_no("Sovrascrivere", 
                                    f"C'è già un allenamento '{existing_name}' pianificato per {date_str}. Vuoi sostituirlo?", 
                                    parent=self):
                        continue
                    
                    # Rimuovi l'allenamento esistente
                    self.scheduled_workouts.pop(i)
                    break
            
            # Crea una copia dell'allenamento
            workout_copy = Workout(workout.sport_type, workout.workout_name, workout.description)
            
            # Copia gli step
            for step in workout.workout_steps:
                workout_copy.add_step(step)
            
            # Aggiungi uno step fittizio con la data
            first_step = workout_copy.workout_steps[0]
            first_step.date = date_str
            
            # Aggiungi alla lista
            self.scheduled_workouts.append((date_str, name, workout_copy))
        
        # Aggiorna la lista
        self.update_schedule_list()
        
        # Mostra messaggio di conferma
        show_info("Pianificazione completata", 
               f"Pianificati {len(scheduled)} allenamenti per la settimana {week}", 
               parent=self)
    
    def schedule_all(self):
        """Pianifica tutti gli allenamenti."""
        # Verifica che ci sia una data di gara
        race_day = self.race_day_var.get()
        if not race_day:
            show_error("Errore", "Inserisci la data della gara", parent=self)
            return
        
        # Verifica che la data sia valida
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', race_day):
            show_error("Errore", "La data della gara deve essere nel formato YYYY-MM-DD", parent=self)
            return
        
        # Verifica che ci siano settimane
        if not self.weeks:
            show_error("Errore", "Non ci sono settimane disponibili", parent=self)
            return
        
        # Per ogni settimana
        for week in self.weeks:
            # Seleziona la settimana
            self.week_var.set(f"Week {week:02d}")
            self.on_week_selected()
            
            # Pianifica la settimana
            self.schedule_week()
    
    def clear_schedule(self):
        """Cancella la pianificazione."""
        # Chiedi conferma
        if not ask_yes_no("Conferma", 
                       "Sei sicuro di voler cancellare tutta la pianificazione?", 
                       parent=self):
            return
        
        # Pulisci la lista
        self.scheduled_workouts = []
        
        # Aggiorna la lista
        self.update_schedule_list()
    
    def update_schedule_list(self):
        """Aggiorna la lista degli allenamenti pianificati."""
        # Pulisci la lista
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)
        
        # Ordina per data
        sorted_workouts = sorted(self.scheduled_workouts, key=lambda x: x[0])
        
        # Giorni della settimana
        days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        
        # Aggiungi gli allenamenti
        for date_str, name, workout in sorted_workouts:
            # Icona in base al tipo di sport
            sport_icon = get_icon_for_sport(workout.sport_type)
            
            # Calcola il giorno della settimana
            weekday = date_to_weekday(date_str)
            
            # Aggiungi alla lista
            self.schedule_tree.insert("", "end", 
                                    values=(date_str, name, f"{sport_icon} {workout.sport_type}", days[weekday]), 
                                    tags=(date_str,))
    
    def on_ok(self):
        """Gestisce il click sul pulsante OK."""
        # Salva la data della gara nella configurazione
        self.config.set('planning.race_day', self.race_day_var.get())
        
        # Salva i giorni preferiti
        preferred_days = []
        for i, var in enumerate(self.day_vars):
            if var.get():
                preferred_days.append(i)
        
        self.config.set('planning.preferred_days', preferred_days)
        
        # Salva la configurazione
        self.config.save()
        
        # Chiudi il dialog
        self.destroy()
    
    def on_cancel(self):
        """Gestisce il click sul pulsante Annulla."""
        # Pulisci la lista degli allenamenti pianificati
        self.scheduled_workouts = []
        
        # Chiudi il dialog
        self.destroy()
    
    def on_close(self):
        """Gestisce la chiusura del dialog."""
        # Chiedi conferma solo se ci sono allenamenti pianificati
        if self.scheduled_workouts:
            if not ask_yes_no("Conferma", 
                          "Ci sono allenamenti pianificati. Sei sicuro di voler chiudere?", 
                          parent=self):
                return
            
            # Pulisci la lista
            self.scheduled_workouts = []
        
        # Chiudi il dialog
        self.destroy()


if __name__ == "__main__":
    # Test del dialog
    root = tk.Tk()
    root.withdraw()
    
    # Crea alcuni allenamenti di test
    workouts = []
    for i in range(1, 5):
        for j in range(1, 4):
            name = format_workout_name(i, j, f"Test workout {i}.{j}")
            workout = Workout("running", name)
            workouts.append((name, workout))
    
    # Crea il dialog
    dialog = ScheduleDialog(root, workouts)
    
    # Avvia il loop
    root.mainloop()