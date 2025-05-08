#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Frame per la visualizzazione del calendario degli allenamenti.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import calendar
import datetime
from typing import Dict, Any, List, Tuple, Optional, Union, Callable

from garmin_planner_gui.config import get_config
from garmin_planner_gui.auth import GarminClient
from garmin_planner_gui.models.calendar import Calendar, CalendarMonth, CalendarDay, CalendarItem
from garmin_planner_gui.services.garmin_service import GarminService
from garmin_planner_gui.gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no, 
    is_valid_date, date_to_weekday, create_scrollable_frame
)
from garmin_planner_gui.gui.styles import get_color_for_sport, get_icon_for_sport
from garmin_planner_gui.gui.dialogs.date_picker import DatePickerDialog


class CalendarFrame(ttk.Frame):
    """Frame per la visualizzazione del calendario degli allenamenti."""
    
    def __init__(self, parent: ttk.Notebook, controller):
        """
        Inizializza il frame del calendario.
        
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
        
        # Calendario
        self.calendar = Calendar()
        
        # Data corrente
        self.current_date = datetime.date.today()
        
        # Creazione dei widget
        self.create_widgets()
        
        # Carica il mese corrente
        self.load_current_month()
    
    def create_widgets(self):
        """Crea i widget del frame."""
        # Frame principale
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame superiore per la navigazione
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pulsanti di navigazione
        nav_frame = ttk.Frame(top_frame)
        nav_frame.pack(side=tk.LEFT)
        
        ttk.Button(nav_frame, text="<<", width=3, 
                 command=lambda: self.change_month(-12)).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(nav_frame, text="<", width=3, 
                 command=lambda: self.change_month(-1)).pack(side=tk.LEFT, padx=(0, 5))
        
        # Titolo del mese
        self.month_var = tk.StringVar()
        ttk.Label(nav_frame, textvariable=self.month_var, style="Heading.TLabel").pack(side=tk.LEFT, padx=10)
        
        ttk.Button(nav_frame, text=">", width=3, 
                 command=lambda: self.change_month(1)).pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Button(nav_frame, text=">>", width=3, 
                 command=lambda: self.change_month(12)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Pulsante per andare al mese corrente
        ttk.Button(nav_frame, text="Oggi", 
                 command=self.go_to_today).pack(side=tk.LEFT, padx=(20, 0))
        
        # Frame per le opzioni di visualizzazione
        options_frame = ttk.Frame(top_frame)
        options_frame.pack(side=tk.RIGHT)
        
        # Pulsanti per l'aggiornamento del calendario
        self.refresh_button = ttk.Button(options_frame, text="Aggiorna", 
                                      command=self.refresh_calendar, state="disabled")
        self.refresh_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Frame per il calendario
        calendar_frame = ttk.LabelFrame(main_frame, text="Calendario")
        calendar_frame.pack(fill=tk.BOTH, expand=True)
        
        # Intestazione dei giorni della settimana
        days_frame = ttk.Frame(calendar_frame)
        days_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Determina il primo giorno della settimana (0 = lunedì, 6 = domenica)
        first_day = self.config.get('ui.calendar_first_day', 0)
        
        # Nomi dei giorni
        days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        
        # Aggiunge i giorni della settimana con il primo giorno configurato
        for i in range(7):
            day_idx = (i + first_day) % 7
            ttk.Label(days_frame, text=days[day_idx], width=15, 
                    anchor="center", style="Subtitle.TLabel").grid(row=0, column=i, padx=1, pady=1)
        
        # Frame per il contenuto del calendario
        self.calendar_content = ttk.Frame(calendar_frame)
        self.calendar_content.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Frame per i dettagli
        details_frame = ttk.LabelFrame(main_frame, text="Dettagli")
        details_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Placeholder per i dettagli (verrà popolato in show_day_details)
        self.details_content = ttk.Frame(details_frame)
        self.details_content.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(self.details_content, text="Seleziona un giorno per vedere i dettagli").pack(pady=10)
    
    def update_month_title(self):
        """Aggiorna il titolo del mese."""
        month_names = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        
        self.month_var.set(f"{month_names[self.current_date.month - 1]} {self.current_date.year}")
    
    def change_month(self, delta: int):
        """
        Cambia il mese visualizzato.
        
        Args:
            delta: Numero di mesi da aggiungere (positivo) o sottrarre (negativo)
        """
        # Calcola il nuovo mese
        year = self.current_date.year
        month = self.current_date.month + delta
        
        # Aggiusta l'anno se necessario
        while month > 12:
            year += 1
            month -= 12
        
        while month < 1:
            year -= 1
            month += 12
        
        # Imposta la nuova data
        self.current_date = datetime.date(year, month, 1)
        
        # Aggiorna il calendario
        self.load_current_month()
    
    def go_to_today(self):
        """Va al mese corrente."""
        self.current_date = datetime.date.today()
        self.load_current_month()
    
    def load_current_month(self):
        """Carica e visualizza il mese corrente."""
        # Aggiorna il titolo
        self.update_month_title()
        
        # Ottieni il mese dal calendario
        year = self.current_date.year
        month = self.current_date.month
        
        # Verifica se il mese è già caricato
        month_obj = self.calendar.get_month(year, month)
        
        if not month_obj:
            # Se è disponibile il servizio Garmin, carica da Garmin Connect
            if self.garmin_service:
                month_obj = self.garmin_service.get_calendar_month(year, month)
                
                if month_obj:
                    self.calendar.add_month(month_obj)
            
            # Se non è disponibile o non è stato possibile caricare, crea un mese vuoto
            if not month_obj:
                month_obj = self.calendar.get_or_create_month(year, month)
        
        # Visualizza il calendario
        self.display_calendar(month_obj)
    
    def display_calendar(self, month_obj: CalendarMonth):
        """
        Visualizza il calendario del mese.
        
        Args:
            month_obj: Mese da visualizzare
        """
        # Pulisci il contenuto precedente
        for widget in self.calendar_content.winfo_children():
            widget.destroy()
        
        # Determina il primo giorno della settimana (0 = lunedì, 6 = domenica)
        first_day_of_week = self.config.get('ui.calendar_first_day', 0)
        
        # Ottieni il primo giorno del mese
        first_day = datetime.date(month_obj.year, month_obj.month, 1)
        
        # Calcola il giorno della settimana del primo giorno del mese (0 = lunedì, 6 = domenica)
        first_weekday = first_day.weekday()
        
        # Calcola quanti giorni includere dal mese precedente
        days_from_prev_month = (first_weekday - first_day_of_week) % 7
        
        # Calcola la data del primo giorno da visualizzare
        start_date = first_day - datetime.timedelta(days=days_from_prev_month)
        
        # Calcola l'ultimo giorno del mese
        last_day = datetime.date(month_obj.year, month_obj.month, 
                                calendar.monthrange(month_obj.year, month_obj.month)[1])
        
        # Calcola il giorno della settimana dell'ultimo giorno
        last_weekday = last_day.weekday()
        
        # Calcola quanti giorni includere dal mese successivo
        days_from_next_month = (6 - last_weekday + first_day_of_week) % 7
        
        # Calcola la data dell'ultimo giorno da visualizzare
        end_date = last_day + datetime.timedelta(days=days_from_next_month)
        
        # Crea la griglia del calendario
        current_date = start_date
        row = 0
        col = 0
        
        while current_date <= end_date:
            # Crea il frame per il giorno
            day_frame = ttk.Frame(self.calendar_content, style="Card.TFrame")
            day_frame.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
            
            # Configura il frame per espandersi
            day_frame.rowconfigure(1, weight=1)
            day_frame.columnconfigure(0, weight=1)
            
            # Formatta la data come stringa
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Ottieni il giorno dal calendario
            day_obj = month_obj.get_day(date_str)
            
            # Intestazione del giorno
            header_frame = ttk.Frame(day_frame)
            header_frame.grid(row=0, column=0, sticky="new")
            
            # Verifica se è il giorno corrente
            is_today = current_date == datetime.date.today()
            
            # Verifica se è nel mese corrente
            is_current_month = current_date.month == month_obj.month
            
            # Stile per il numero del giorno
            day_style = "Today.TLabel" if is_today else "TLabel"
            day_fg = None if is_today else "#999999" if not is_current_month else None
            
            # Numero del giorno
            day_label = ttk.Label(header_frame, text=str(current_date.day), 
                                style=day_style, foreground=day_fg)
            day_label.pack(side=tk.LEFT, padx=5)
            
            # Contenuto del giorno
            content_frame = ttk.Frame(day_frame)
            content_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
            
            # Aggiungi gli item del giorno
            if day_obj:
                for item in day_obj.items:
                    self.create_day_item(content_frame, item)
            
            # Associa eventi per selezionare il giorno
            day_frame.bind("<Button-1>", lambda e, d=date_str: self.show_day_details(d))
            header_frame.bind("<Button-1>", lambda e, d=date_str: self.show_day_details(d))
            content_frame.bind("<Button-1>", lambda e, d=date_str: self.show_day_details(d))
            
            # Passa al giorno successivo
            current_date += datetime.timedelta(days=1)
            
            # Incrementa la colonna
            col += 1
            
            # Se abbiamo completato una settimana, passa alla riga successiva
            if col > 6:
                col = 0
                row += 1
        
        # Configura le righe e colonne per espandersi uniformemente
        for i in range(7):
            self.calendar_content.columnconfigure(i, weight=1)
        
        for i in range(row + 1):
            self.calendar_content.rowconfigure(i, weight=1)
    
    def create_day_item(self, parent: ttk.Frame, item: CalendarItem):
        """
        Crea un widget per un item del giorno.
        
        Args:
            parent: Widget genitore
            item: Item da visualizzare
        """
        # Frame per l'item
        item_frame = ttk.Frame(parent, style="Card.TFrame")
        item_frame.pack(fill=tk.X, pady=1)
        
        # Colore in base al tipo di sport
        sport_color = get_color_for_sport(item.sport_type, self.config.get('ui.theme', 'light'))
        
        # Icona in base al tipo di sport
        sport_icon = get_icon_for_sport(item.sport_type)
        
        # Titolo dell'item
        title = item.title
        if len(title) > 20:
            title = title[:18] + "..."
        
        # Label con l'icona e il titolo
        item_label = ttk.Label(item_frame, text=f"{sport_icon} {title}", 
                              foreground=sport_color)
        item_label.pack(side=tk.LEFT, padx=2)
        
        # Associa eventi per selezionare l'item
        item_frame.bind("<Button-1>", lambda e, i=item: self.show_item_details(i))
        item_label.bind("<Button-1>", lambda e, i=item: self.show_item_details(i))
    
    def show_day_details(self, date_str: str):
        """
        Mostra i dettagli di un giorno.
        
        Args:
            date_str: Data nel formato YYYY-MM-DD
        """
        # Pulisci i dettagli precedenti
        for widget in self.details_content.winfo_children():
            widget.destroy()
        
        # Ottieni il mese
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        month_obj = self.calendar.get_month(date_obj.year, date_obj.month)
        
        if not month_obj:
            ttk.Label(self.details_content, text=f"Nessun dato disponibile per {date_str}").pack(pady=10)
            return
        
        # Ottieni il giorno
        day_obj = month_obj.get_day(date_str)
        
        # Se non ci sono item, mostra un messaggio
        if not day_obj or not day_obj.items:
            # Header con la data
            header_frame = ttk.Frame(self.details_content)
            header_frame.pack(fill=tk.X, pady=(10, 5))
            
            # Formatta la data in modo più leggibile (es. "Lunedì, 1 Gennaio 2025")
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            weekdays = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
            months = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                     "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
            
            weekday = weekdays[date_obj.weekday()]
            month = months[date_obj.month - 1]
            
            formatted_date = f"{weekday}, {date_obj.day} {month} {date_obj.year}"
            
            ttk.Label(header_frame, text=formatted_date, style="Heading.TLabel").pack(side=tk.LEFT)
            
            # Pulsanti per aggiungere allenamenti
            if self.garmin_client:
                ttk.Button(header_frame, text="Pianifica allenamento...", 
                         command=lambda: self.schedule_workout(date_str)).pack(side=tk.RIGHT, padx=(5, 0))
            
            ttk.Label(self.details_content, text="Nessun allenamento o attività pianificata").pack(pady=10)
            return
        
        # Header con la data
        header_frame = ttk.Frame(self.details_content)
        header_frame.pack(fill=tk.X, pady=(10, 5))
        
        # Formatta la data in modo più leggibile (es. "Lunedì, 1 Gennaio 2025")
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        weekdays = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        months = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                 "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        
        weekday = weekdays[date_obj.weekday()]
        month = months[date_obj.month - 1]
        
        formatted_date = f"{weekday}, {date_obj.day} {month} {date_obj.year}"
        
        ttk.Label(header_frame, text=formatted_date, style="Heading.TLabel").pack(side=tk.LEFT)
        
        # Pulsanti per aggiungere allenamenti
        if self.garmin_client:
            ttk.Button(header_frame, text="Pianifica allenamento...", 
                     command=lambda: self.schedule_workout(date_str)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Lista degli item
        items_frame = ttk.Frame(self.details_content)
        items_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Intestazione
        ttk.Label(items_frame, text="Titolo", style="Subtitle.TLabel").grid(row=0, column=0, sticky="w", padx=(5, 10))
        ttk.Label(items_frame, text="Tipo", style="Subtitle.TLabel").grid(row=0, column=1, sticky="w", padx=(5, 10))
        ttk.Label(items_frame, text="Sport", style="Subtitle.TLabel").grid(row=0, column=2, sticky="w", padx=(5, 10))
        ttk.Label(items_frame, text="Azioni", style="Subtitle.TLabel").grid(row=0, column=3, sticky="w", padx=(5, 10))
        
        # Separatore
        ttk.Separator(items_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)
        
        # Aggiungi gli item
        for i, item in enumerate(day_obj.items):
            # Titolo
            ttk.Label(items_frame, text=item.title).grid(row=i+2, column=0, sticky="w", padx=(5, 10), pady=2)
            
            # Tipo (workout o activity)
            type_text = "Allenamento" if item.item_type == "workout" else "Attività"
            ttk.Label(items_frame, text=type_text).grid(row=i+2, column=1, sticky="w", padx=(5, 10), pady=2)
            
            # Sport
            sport_icon = get_icon_for_sport(item.sport_type)
            sport_text = item.sport_type.capitalize()
            ttk.Label(items_frame, text=f"{sport_icon} {sport_text}").grid(row=i+2, column=2, sticky="w", padx=(5, 10), pady=2)
            
            # Pulsanti per le azioni
            actions_frame = ttk.Frame(items_frame)
            actions_frame.grid(row=i+2, column=3, sticky="w", padx=(5, 10), pady=2)
            
            # Pulsante per i dettagli
            ttk.Button(actions_frame, text="Dettagli", width=10, 
                     command=lambda i=item: self.show_item_details(i)).pack(side=tk.LEFT, padx=(0, 5))
            
            # Se è un workout, mostra pulsanti per modificare o eliminare
            if item.item_type == "workout" and self.garmin_client:
                # Pulsante per ripianificare
                ttk.Button(actions_frame, text="Ripianifica", width=10, 
                         command=lambda i=item: self.reschedule_workout(i)).pack(side=tk.LEFT, padx=(0, 5))
                
                # Pulsante per annullare la pianificazione
                ttk.Button(actions_frame, text="Annulla", width=10, 
                         command=lambda i=item: self.unschedule_workout(i)).pack(side=tk.LEFT)
    
    def show_item_details(self, item: CalendarItem):
        """
        Mostra i dettagli di un item.
        
        Args:
            item: Item da visualizzare
        """
        # Crea una nuova finestra
        details_window = tk.Toplevel(self)
        details_window.title(f"Dettagli - {item.title}")
        details_window.geometry("600x400")
        details_window.transient(self)
        details_window.grab_set()
        
        # Centra la finestra
        details_window.update_idletasks()
        width = details_window.winfo_width()
        height = details_window.winfo_height()
        x = (details_window.winfo_screenwidth() // 2) - (width // 2)
        y = (details_window.winfo_screenheight() // 2) - (height // 2)
        details_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Frame principale
        main_frame = ttk.Frame(details_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Intestazione
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Icona in base al tipo di sport
        sport_icon = get_icon_for_sport(item.sport_type)
        
        title_label = ttk.Label(header_frame, text=f"{sport_icon} {item.title}", 
                              style="Title.TLabel")
        title_label.pack(side=tk.LEFT)
        
        # Tipo (workout o activity)
        type_text = "Allenamento" if item.item_type == "workout" else "Attività"
        type_label = ttk.Label(header_frame, text=type_text, style="Subtitle.TLabel")
        type_label.pack(side=tk.RIGHT)
        
        # Dettagli
        details_frame = ttk.LabelFrame(main_frame, text="Dettagli")
        details_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid per allineare i dettagli
        grid_frame = ttk.Frame(details_frame)
        grid_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Data
        ttk.Label(grid_frame, text="Data:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        ttk.Label(grid_frame, text=item.date).grid(row=0, column=1, sticky="w", pady=2)
        
        # Sport
        ttk.Label(grid_frame, text="Sport:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        ttk.Label(grid_frame, text=item.sport_type.capitalize()).grid(row=1, column=1, sticky="w", pady=2)
        
        # Descrizione
        ttk.Label(grid_frame, text="Descrizione:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=2)
        
        description_text = item.description if item.description else "Nessuna descrizione disponibile"
        ttk.Label(grid_frame, text=description_text, wraplength=400).grid(row=2, column=1, sticky="w", pady=2)
        
        # Fonte
        ttk.Label(grid_frame, text="Fonte:").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=2)
        ttk.Label(grid_frame, text=item.source.capitalize()).grid(row=3, column=1, sticky="w", pady=2)
        
        # ID
        ttk.Label(grid_frame, text="ID:").grid(row=4, column=0, sticky="w", padx=(0, 10), pady=2)
        ttk.Label(grid_frame, text=item.item_id).grid(row=4, column=1, sticky="w", pady=2)
        
        # Per i workout, mostra pulsanti per modificare o eliminare
        if item.item_type == "workout" and self.garmin_client:
            actions_frame = ttk.Frame(main_frame)
            actions_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Button(actions_frame, text="Modifica", 
                     command=lambda: self.edit_workout(item)).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(actions_frame, text="Ripianifica", 
                     command=lambda: self.reschedule_workout(item)).pack(side=tk.LEFT, padx=(0, 5))
            
            ttk.Button(actions_frame, text="Annulla pianificazione", 
                     command=lambda: self.unschedule_workout(item)).pack(side=tk.LEFT)
        
        # Pulsante per chiudere
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(buttons_frame, text="Chiudi", 
                 command=details_window.destroy).pack(side=tk.RIGHT)
    
    def schedule_workout(self, date_str: str):
        """
        Pianifica un allenamento per una data specifica.
        
        Args:
            date_str: Data nel formato YYYY-MM-DD
        """
        # Verifica che il client Garmin sia disponibile
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        try:
            # Ottieni la lista degli allenamenti
            workouts_data = self.garmin_client.list_workouts()
            
            # Verifica che ci siano allenamenti
            if not workouts_data:
                show_error("Errore", "Nessun allenamento disponibile", parent=self)
                return
            
            # Crea una nuova finestra
            schedule_window = tk.Toplevel(self)
            schedule_window.title(f"Pianifica allenamento per {date_str}")
            schedule_window.geometry("600x500")
            schedule_window.transient(self)
            schedule_window.grab_set()
            
            # Centra la finestra
            schedule_window.update_idletasks()
            width = schedule_window.winfo_width()
            height = schedule_window.winfo_height()
            x = (schedule_window.winfo_screenwidth() // 2) - (width // 2)
            y = (schedule_window.winfo_screenheight() // 2) - (height // 2)
            schedule_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Frame principale
            main_frame = ttk.Frame(schedule_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Intestazione
            header_frame = ttk.Frame(main_frame)
            header_frame.pack(fill=tk.X, pady=(0, 20))
            
            ttk.Label(header_frame, text=f"Pianifica allenamento per {date_str}", 
                    style="Title.TLabel").pack(side=tk.LEFT)
            
            # Filtro
            filter_frame = ttk.Frame(main_frame)
            filter_frame.pack(fill=tk.X, pady=(0, 10))
            
            ttk.Label(filter_frame, text="Filtro:").pack(side=tk.LEFT)
            
            filter_var = tk.StringVar()
            filter_entry = ttk.Entry(filter_frame, textvariable=filter_var, width=30)
            filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            # Lista degli allenamenti
            list_frame = ttk.Frame(main_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Crea il treeview
            columns = ("name", "sport", "steps")
            workout_tree = ttk.Treeview(list_frame, columns=columns, show="headings", 
                                      selectmode="browse")
            
            # Intestazioni
            workout_tree.heading("name", text="Nome")
            workout_tree.heading("sport", text="Sport")
            workout_tree.heading("steps", text="Step")
            
            # Larghezze colonne
            workout_tree.column("name", width=300)
            workout_tree.column("sport", width=100)
            workout_tree.column("steps", width=50)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=workout_tree.yview)
            workout_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack
            workout_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Popola la lista
            for workout in workouts_data:
                # Estrai i dati dell'allenamento
                name = workout.get('workoutName', '')
                
                # Ottieni il tipo di sport
                sport_type = 'running'  # Default
                if 'sportType' in workout and 'sportTypeKey' in workout['sportType']:
                    sport_type = workout['sportType']['sportTypeKey']
                
                # Conta gli step
                step_count = 0
                for segment in workout.get('workoutSegments', []):
                    step_count += len(segment.get('workoutSteps', []))
                
                # Aggiungi alla lista
                workout_tree.insert("", "end", 
                                  values=(name, sport_type, step_count), 
                                  tags=(str(workout.get('workoutId', ''))))
            
            # Funzione per filtrare la lista
            def filter_workouts(*args):
                # Ottieni il filtro
                filter_text = filter_var.get().lower()
                
                # Pulisci la lista attuale
                for item in workout_tree.get_children():
                    workout_tree.delete(item)
                
                # Filtra gli allenamenti
                filtered_workouts = []
                for workout in workouts_data:
                    # Estrai i dati dell'allenamento
                    name = workout.get('workoutName', '')
                    
                    # Applica il filtro
                    if filter_text and filter_text not in name.lower():
                        continue
                    
                    # Aggiungi all'elenco filtrato
                    filtered_workouts.append(workout)
                
                # Aggiungi gli allenamenti filtrati alla lista
                for workout in filtered_workouts:
                    # Estrai i dati dell'allenamento
                    name = workout.get('workoutName', '')
                    
                    # Ottieni il tipo di sport
                    sport_type = 'running'  # Default
                    if 'sportType' in workout and 'sportTypeKey' in workout['sportType']:
                        sport_type = workout['sportType']['sportTypeKey']
                    
                    # Conta gli step
                    step_count = 0
                    for segment in workout.get('workoutSegments', []):
                        step_count += len(segment.get('workoutSteps', []))
                    
                    # Aggiungi alla lista
                    workout_tree.insert("", "end", 
                                     values=(name, sport_type, step_count), 
                                     tags=(str(workout.get('workoutId', ''))))
            
            # Associa evento di modifica del filtro
            filter_var.trace_add("write", filter_workouts)
            
            # Pulsanti
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Button(buttons_frame, text="Annulla", 
                     command=schedule_window.destroy).pack(side=tk.RIGHT, padx=(5, 0))
            
            ttk.Button(buttons_frame, text="Pianifica", 
                     command=lambda: schedule_selected()).pack(side=tk.RIGHT, padx=(5, 0))
            
            # Funzione per pianificare l'allenamento selezionato
            def schedule_selected():
                # Ottieni l'allenamento selezionato
                selection = workout_tree.selection()
                if not selection:
                    show_error("Errore", "Seleziona un allenamento", parent=schedule_window)
                    return
                
                # Ottieni l'ID dell'allenamento
                workout_id = workout_tree.item(selection[0], "tags")[0]
                
                # Pianifica l'allenamento
                response = self.garmin_client.schedule_workout(workout_id, date_str)
                
                if response:
                    show_info("Successo", "Allenamento pianificato correttamente", parent=schedule_window)
                    
                    # Aggiorna il calendario
                    self.refresh_calendar()
                    
                    # Chiudi la finestra
                    schedule_window.destroy()
                else:
                    show_error("Errore", "Impossibile pianificare l'allenamento", parent=schedule_window)
        
        except Exception as e:
            logging.error(f"Errore nella pianificazione dell'allenamento: {str(e)}")
            show_error("Errore", 
                     f"Impossibile pianificare l'allenamento: {str(e)}", 
                     parent=self)
    
    def reschedule_workout(self, item: CalendarItem):
        """
        Ripianifica un allenamento.
        
        Args:
            item: Item da ripianificare
        """
        # Verifica che il client Garmin sia disponibile
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        # Verifica che sia un workout
        if item.item_type != "workout":
            show_error("Errore", "Puoi ripianificare solo gli allenamenti", parent=self)
            return
        
        # Ottieni la data attuale
        current_date = item.date
        
        # Funzione di callback per la selezione della data
        def on_date_selected(date):
            if not date:
                return
            
            try:
                # Annulla la pianificazione corrente
                self.garmin_client.unschedule_workout(item.item_id)
                
                # Pianifica l'allenamento per la nuova data
                response = self.garmin_client.schedule_workout(item.source_id, date)
                
                if response:
                    show_info("Successo", "Allenamento ripianificato correttamente", parent=self)
                    
                    # Aggiorna il calendario
                    self.refresh_calendar()
                else:
                    show_error("Errore", "Impossibile ripianificare l'allenamento", parent=self)
            
            except Exception as e:
                logging.error(f"Errore nella ripianificazione dell'allenamento: {str(e)}")
                show_error("Errore", 
                         f"Impossibile ripianificare l'allenamento: {str(e)}", 
                         parent=self)
        
        # Mostra il dialog per selezionare la data
        date_picker = DatePickerDialog(self, 
                                    title="Seleziona la nuova data", 
                                    initial_date=current_date, 
                                    callback=on_date_selected)
    
    def unschedule_workout(self, item: CalendarItem):
        """
        Annulla la pianificazione di un allenamento.
        
        Args:
            item: Item da annullare
        """
        # Verifica che il client Garmin sia disponibile
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        # Verifica che sia un workout
        if item.item_type != "workout":
            show_error("Errore", "Puoi annullare solo gli allenamenti", parent=self)
            return
        
        # Chiedi conferma
        if not ask_yes_no("Conferma", 
                       f"Sei sicuro di voler annullare la pianificazione dell'allenamento '{item.title}'?", 
                       parent=self):
            return
        
        try:
            # Annulla la pianificazione
            self.garmin_client.unschedule_workout(item.item_id)
            
            show_info("Successo", "Pianificazione annullata correttamente", parent=self)
            
            # Aggiorna il calendario
            self.refresh_calendar()
            
        except Exception as e:
            logging.error(f"Errore nell'annullamento della pianificazione: {str(e)}")
            show_error("Errore", 
                     f"Impossibile annullare la pianificazione: {str(e)}", 
                     parent=self)
    
    def edit_workout(self, item: CalendarItem):
        """
        Modifica un allenamento.
        
        Args:
            item: Item da modificare
        """
        # Verifica che il client Garmin sia disponibile
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        # Verifica che sia un workout
        if item.item_type != "workout":
            show_error("Errore", "Puoi modificare solo gli allenamenti", parent=self)
            return
        
        # Passa all'editor di allenamenti
        try:
            # Trova l'editor di allenamenti nel controller
            workout_editor = self.controller.workout_editor
            
            # Seleziona la scheda dell'editor
            self.controller.notebook.select(workout_editor)
            
            # Carica l'allenamento
            workout_editor.load_workout_by_id(item.source_id)
            
        except Exception as e:
            logging.error(f"Errore nell'apertura dell'editor di allenamenti: {str(e)}")
            show_error("Errore", 
                     f"Impossibile aprire l'editor di allenamenti: {str(e)}", 
                     parent=self)
    
    def refresh_calendar(self):
        """Aggiorna il calendario."""
        # Verifica che il client Garmin sia disponibile
        if not self.garmin_client:
            show_error("Errore", "Devi prima effettuare il login a Garmin Connect", parent=self)
            return
        
        # Ottieni l'anno e il mese correnti
        year = self.current_date.year
        month = self.current_date.month
        
        try:
            # Ottieni il mese dal servizio Garmin
            month_obj = self.garmin_service.get_calendar_month(year, month)
            
            if month_obj:
                # Aggiungi al calendario
                self.calendar.add_month(month_obj)
                
                # Visualizza il calendario
                self.display_calendar(month_obj)
                
                # Pulisci i dettagli
                for widget in self.details_content.winfo_children():
                    widget.destroy()
                
                ttk.Label(self.details_content, text="Seleziona un giorno per vedere i dettagli").pack(pady=10)
                
                # Aggiorna la barra di stato
                self.controller.set_status(f"Calendario aggiornato: {month_obj.month}/{month_obj.year}")
            else:
                show_error("Errore", "Impossibile ottenere i dati del calendario", parent=self)
            
        except Exception as e:
            logging.error(f"Errore nell'aggiornamento del calendario: {str(e)}")
            show_error("Errore", 
                     f"Impossibile aggiornare il calendario: {str(e)}", 
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
        self.refresh_button.config(state="normal")
        
        # Aggiorna il calendario
        self.refresh_calendar()
    
    def on_logout(self):
        """Gestisce l'evento di logout."""
        self.garmin_client = None
        self.garmin_service = None
        
        # Disabilita i pulsanti
        self.refresh_button.config(state="disabled")
        
        # Pulisci il calendario
        self.calendar = Calendar()
        
        # Carica il mese corrente (vuoto)
        self.load_current_month()
    
    def on_activate(self):
        """Chiamato quando il frame viene attivato."""
        # Aggiorna il calendario solo se è disponibile il client Garmin
        if self.garmin_client:
            self.refresh_calendar()
        else:
            # Carica comunque il mese corrente (vuoto)
            self.load_current_month()


if __name__ == "__main__":
    # Test del frame
    root = tk.Tk()
    root.title("Calendar View Test")
    root.geometry("1200x800")
    
    # Crea un notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Controller fittizio
    class DummyController:
        def set_status(self, message):
            print(message)
    
    # Crea il frame
    frame = CalendarFrame(notebook, DummyController())
    notebook.add(frame, text="Calendario")
    
    root.mainloop()