#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Frame per la gestione delle zone di allenamento.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import re
from typing import Dict, Any, List, Tuple, Optional, Union

from garmin_planner_gui.config import get_config
from garmin_planner_gui.models.zone import (
    Zone, PaceZone, HeartRateZone, PowerZone, ZoneSet
)
from garmin_planner_gui.gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no,
    create_scrollable_frame, validate_pace, validate_power, validate_hr,
    parse_pace_range, parse_power_range
)
from garmin_planner_gui.gui.styles import get_color_for_sport, get_icon_for_sport


class ZonesManagerFrame(ttk.Frame):
    """Frame per la gestione delle zone di allenamento."""
    
    def __init__(self, parent: ttk.Notebook, controller):
        """
        Inizializza il frame delle zone.
        
        Args:
            parent: Widget genitore (notebook)
            controller: Controller principale dell'applicazione
        """
        super().__init__(parent)
        self.parent = parent
        self.controller = controller
        self.config = get_config()
        
        # Creazione dei widget
        self.create_widgets()
        
        # Carica le zone dalla configurazione
        self.load_zones()
    
    def create_widgets(self):
        """Crea i widget del frame."""
        # Frame principale
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pannello diviso: sport a sinistra, zone a destra
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Frame sinistro per la selezione dello sport
        left_frame = ttk.Frame(paned, padding=5)
        paned.add(left_frame, weight=1)
        
        # Frame destro per le zone
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(right_frame, weight=3)
        
        # --- Parte sinistra: Selezione sport ---
        
        # Intestazione
        ttk.Label(left_frame, text="Sport", style="Heading.TLabel").pack(fill=tk.X, pady=(0, 10))
        
        # Lista degli sport
        sport_frame = ttk.Frame(left_frame)
        sport_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea i pulsanti per i diversi sport
        self.sport_var = tk.StringVar(value="running")
        
        # Running
        running_button = ttk.Radiobutton(sport_frame, text="Corsa", 
                                      value="running", 
                                      variable=self.sport_var, 
                                      command=self.on_sport_change)
        running_button.pack(fill=tk.X, pady=(0, 5))
        
        create_tooltip(running_button, "Gestisci le zone per la corsa")
        
        # Cycling
        cycling_button = ttk.Radiobutton(sport_frame, text="Ciclismo", 
                                      value="cycling", 
                                      variable=self.sport_var, 
                                      command=self.on_sport_change)
        cycling_button.pack(fill=tk.X, pady=(0, 5))
        
        create_tooltip(cycling_button, "Gestisci le zone per il ciclismo")
        
        # Swimming
        swimming_button = ttk.Radiobutton(sport_frame, text="Nuoto", 
                                       value="swimming", 
                                       variable=self.sport_var, 
                                       command=self.on_sport_change)
        swimming_button.pack(fill=tk.X)
        
        create_tooltip(swimming_button, "Gestisci le zone per il nuoto")
        
        # Frequenza cardiaca
        hr_frame = ttk.LabelFrame(left_frame, text="Frequenza cardiaca")
        hr_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Grid per allineare i campi
        hr_grid = ttk.Frame(hr_frame)
        hr_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # FC massima
        ttk.Label(hr_grid, text="FC max:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.max_hr_var = tk.StringVar(value=str(self.config.get('heart_rates.max_hr', 180)))
        max_hr_entry = ttk.Entry(hr_grid, textvariable=self.max_hr_var, width=5)
        max_hr_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(hr_grid, text="bpm").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # FC riposo
        ttk.Label(hr_grid, text="FC riposo:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.rest_hr_var = tk.StringVar(value=str(self.config.get('heart_rates.rest_hr', 60)))
        rest_hr_entry = ttk.Entry(hr_grid, textvariable=self.rest_hr_var, width=5)
        rest_hr_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(hr_grid, text="bpm").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # --- Parte destra: Zone ---
        
        # Intestazione
        self.zone_header = ttk.Label(right_frame, text="Zone per la corsa", style="Heading.TLabel")
        self.zone_header.pack(fill=tk.X, pady=(0, 10))
        
        # Notebook per le diverse tipologie di zone
        self.zones_notebook = ttk.Notebook(right_frame)
        self.zones_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab per le zone di passo (corsa, nuoto)
        self.pace_frame = ttk.Frame(self.zones_notebook, padding=10)
        self.zones_notebook.add(self.pace_frame, text="Zone di passo")
        
        # Tab per le zone di potenza (ciclismo)
        self.power_frame = ttk.Frame(self.zones_notebook, padding=10)
        self.zones_notebook.add(self.power_frame, text="Zone di potenza")
        
        # Tab per le zone di frequenza cardiaca (tutti gli sport)
        self.hr_frame = ttk.Frame(self.zones_notebook, padding=10)
        self.zones_notebook.add(self.hr_frame, text="Zone di frequenza cardiaca")
        
        # Pulsanti
        buttons_frame = ttk.Frame(right_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.save_button = ttk.Button(buttons_frame, text="Salva", 
                                    command=self.save_zones)
        self.save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.reset_button = ttk.Button(buttons_frame, text="Ripristina", 
                                     command=self.reset_zones)
        self.reset_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Crea i widget per le zone
        self.create_pace_zones()
        self.create_power_zones()
        self.create_hr_zones()
    
    def create_pace_zones(self):
        """Crea i widget per le zone di passo."""
        # Descrizione
        ttk.Label(self.pace_frame, text="Configura le zone di passo (formato: mm:ss o mm:ss-mm:ss)").pack(fill=tk.X, pady=(0, 10))
        
        # Frame per le zone
        zones_frame = ttk.Frame(self.pace_frame)
        zones_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea la griglia
        ttk.Label(zones_frame, text="Nome", style="Subtitle.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        ttk.Label(zones_frame, text="Passo (min/km)", style="Subtitle.TLabel").grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        ttk.Label(zones_frame, text="Descrizione", style="Subtitle.TLabel").grid(row=0, column=2, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        
        # Separatore
        ttk.Separator(zones_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        # Zone standard
        self.pace_entries = {}
        
        pace_zones = [
            ("Z1", "Zone 1 - Recupero attivo"),
            ("Z2", "Zone 2 - Fondamentale"),
            ("Z3", "Zone 3 - Tempo medio"),
            ("Z4", "Zone 4 - Soglia"),
            ("Z5", "Zone 5 - VO2max"),
            ("recovery", "Recupero"),
            ("threshold", "Soglia anaerobica"),
            ("marathon", "Passo maratona"),
            ("race_pace", "Passo gara"),
        ]
        
        for i, (name, description) in enumerate(pace_zones):
            ttk.Label(zones_frame, text=name).grid(row=i+2, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            
            var = tk.StringVar()
            entry = ttk.Entry(zones_frame, textvariable=var, width=15)
            entry.grid(row=i+2, column=1, sticky=tk.W, padx=(0, 10), pady=2)
            
            self.pace_entries[name] = var
            
            ttk.Label(zones_frame, text=description).grid(row=i+2, column=2, sticky=tk.W, padx=(0, 10), pady=2)
        
        # Frame per i margini
        margins_frame = ttk.LabelFrame(self.pace_frame, text="Margini di tolleranza")
        margins_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Grid per allineare i campi
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Margine più veloce
        ttk.Label(margins_grid, text="Più veloce:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.pace_faster_var = tk.StringVar()
        faster_entry = ttk.Entry(margins_grid, textvariable=self.pace_faster_var, width=5)
        faster_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="min:sec").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Margine più lento
        ttk.Label(margins_grid, text="Più lento:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.pace_slower_var = tk.StringVar()
        slower_entry = ttk.Entry(margins_grid, textvariable=self.pace_slower_var, width=5)
        slower_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="min:sec").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
    
    def create_power_zones(self):
        """Crea i widget per le zone di potenza."""
        # Descrizione
        ttk.Label(self.power_frame, text="Configura le zone di potenza (formato: N-N, N, <N o N+)").pack(fill=tk.X, pady=(0, 10))
        
        # Frame per le zone
        zones_frame = ttk.Frame(self.power_frame)
        zones_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea la griglia
        ttk.Label(zones_frame, text="Nome", style="Subtitle.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        ttk.Label(zones_frame, text="Potenza (watt)", style="Subtitle.TLabel").grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        ttk.Label(zones_frame, text="Descrizione", style="Subtitle.TLabel").grid(row=0, column=2, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        
        # Separatore
        ttk.Separator(zones_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        # FTP
        ttk.Label(zones_frame, text="ftp", style="Subtitle.TLabel").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=2)
        
        self.ftp_var = tk.StringVar()
        ftp_entry = ttk.Entry(zones_frame, textvariable=self.ftp_var, width=15)
        ftp_entry.grid(row=2, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        ttk.Label(zones_frame, text="Potenza di soglia funzionale").grid(row=2, column=2, sticky=tk.W, padx=(0, 10), pady=2)
        
        # Zone standard
        self.power_entries = {}
        
        power_zones = [
            ("Z1", "Zone 1 - Recupero attivo"),
            ("Z2", "Zone 2 - Resistenza"),
            ("Z3", "Zone 3 - Tempo"),
            ("Z4", "Zone 4 - Soglia"),
            ("Z5", "Zone 5 - VO2max"),
            ("Z6", "Zone 6 - Anaerobica"),
            ("recovery", "Recupero"),
            ("threshold", "Soglia"),
            ("sweet_spot", "Sweet Spot"),
        ]
        
        for i, (name, description) in enumerate(power_zones):
            ttk.Label(zones_frame, text=name).grid(row=i+3, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            
            var = tk.StringVar()
            entry = ttk.Entry(zones_frame, textvariable=var, width=15)
            entry.grid(row=i+3, column=1, sticky=tk.W, padx=(0, 10), pady=2)
            
            self.power_entries[name] = var
            
            ttk.Label(zones_frame, text=description).grid(row=i+3, column=2, sticky=tk.W, padx=(0, 10), pady=2)
        
        # Frame per i margini
        margins_frame = ttk.LabelFrame(self.power_frame, text="Margini di tolleranza")
        margins_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Grid per allineare i campi
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Margine superiore
        ttk.Label(margins_grid, text="Superiore:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.power_up_var = tk.StringVar()
        power_up_entry = ttk.Entry(margins_grid, textvariable=self.power_up_var, width=5)
        power_up_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="watt").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Margine inferiore
        ttk.Label(margins_grid, text="Inferiore:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.power_down_var = tk.StringVar()
        power_down_entry = ttk.Entry(margins_grid, textvariable=self.power_down_var, width=5)
        power_down_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="watt").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
    
    def create_hr_zones(self):
        """Crea i widget per le zone di frequenza cardiaca."""
        # Descrizione
        ttk.Label(self.hr_frame, text="Configura le zone di frequenza cardiaca (formato: N-N bpm o N-N% max_hr)").pack(fill=tk.X, pady=(0, 10))
        
        # Frame per le zone
        zones_frame = ttk.Frame(self.hr_frame)
        zones_frame.pack(fill=tk.BOTH, expand=True)
        
        # Crea la griglia
        ttk.Label(zones_frame, text="Nome", style="Subtitle.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        ttk.Label(zones_frame, text="Frequenza cardiaca", style="Subtitle.TLabel").grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        ttk.Label(zones_frame, text="Descrizione", style="Subtitle.TLabel").grid(row=0, column=2, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        
        # Separatore
        ttk.Separator(zones_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=3, sticky=tk.EW, pady=5)
        
        # Zone standard
        self.hr_entries = {}
        
        hr_zones = [
            ("Z1_HR", "Zone 1 - Recupero"),
            ("Z2_HR", "Zone 2 - Aerobica"),
            ("Z3_HR", "Zone 3 - Tempo"),
            ("Z4_HR", "Zone 4 - Soglia"),
            ("Z5_HR", "Zone 5 - Massimale"),
        ]
        
        for i, (name, description) in enumerate(hr_zones):
            ttk.Label(zones_frame, text=name).grid(row=i+2, column=0, sticky=tk.W, padx=(0, 10), pady=2)
            
            var = tk.StringVar()
            entry = ttk.Entry(zones_frame, textvariable=var, width=20)
            entry.grid(row=i+2, column=1, sticky=tk.W, padx=(0, 10), pady=2)
            
            self.hr_entries[name] = var
            
            ttk.Label(zones_frame, text=description).grid(row=i+2, column=2, sticky=tk.W, padx=(0, 10), pady=2)
        
        # Frame per i margini
        margins_frame = ttk.LabelFrame(self.hr_frame, text="Margini di tolleranza")
        margins_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Grid per allineare i campi
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Margine superiore
        ttk.Label(margins_grid, text="Superiore:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.hr_up_var = tk.StringVar()
        hr_up_entry = ttk.Entry(margins_grid, textvariable=self.hr_up_var, width=5)
        hr_up_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="bpm").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Margine inferiore
        ttk.Label(margins_grid, text="Inferiore:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.hr_down_var = tk.StringVar()
        hr_down_entry = ttk.Entry(margins_grid, textvariable=self.hr_down_var, width=5)
        hr_down_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="bpm").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
    
    def on_sport_change(self):
        """Gestisce il cambio di sport."""
        # Ottieni lo sport selezionato
        sport = self.sport_var.get()
        
        # Aggiorna l'intestazione
        if sport == "running":
            self.zone_header.config(text="Zone per la corsa")
        elif sport == "cycling":
            self.zone_header.config(text="Zone per il ciclismo")
        elif sport == "swimming":
            self.zone_header.config(text="Zone per il nuoto")
        
        # Mostra/nascondi le tab appropriate
        if sport == "cycling":
            # Il ciclismo usa le zone di potenza
            if "Zone di potenza" not in self.zones_notebook.tabs():
                self.zones_notebook.add(self.power_frame, text="Zone di potenza")
            
            # Seleziona la tab delle zone di potenza
            tab_idx = self.zones_notebook.index(self.power_frame)
            self.zones_notebook.select(tab_idx)
            
            # Nascondi le tab non utilizzate
            if "Zone di passo" in self.zones_notebook.tabs():
                self.zones_notebook.hide(self.pace_frame)
        else:
            # Corsa e nuoto usano le zone di passo
            if "Zone di passo" not in self.zones_notebook.tabs():
                self.zones_notebook.add(self.pace_frame, text="Zone di passo")
            
            # Seleziona la tab delle zone di passo
            tab_idx = self.zones_notebook.index(self.pace_frame)
            self.zones_notebook.select(tab_idx)
            
            # Nascondi le tab non utilizzate
            if "Zone di potenza" in self.zones_notebook.tabs():
                self.zones_notebook.hide(self.power_frame)
        
        # Carica le zone per il nuovo sport
        self.load_zones()
    
    def load_zones(self):
        """Carica le zone dalla configurazione."""
        # Ottieni lo sport selezionato
        sport = self.sport_var.get()
        
        # Carica la frequenza cardiaca
        max_hr = self.config.get('heart_rates.max_hr', 180)
        rest_hr = self.config.get('heart_rates.rest_hr', 60)
        
        self.max_hr_var.set(str(max_hr))
        self.rest_hr_var.set(str(rest_hr))
        
        # Carica le zone di frequenza cardiaca
        for name, var in self.hr_entries.items():
            value = self.config.get(f'heart_rates.{name}', '')
            var.set(value)
        
        # Carica i margini di frequenza cardiaca
        hr_up = self.config.get('hr_margins.hr_up', 5)
        hr_down = self.config.get('hr_margins.hr_down', 5)
        
        self.hr_up_var.set(str(hr_up))
        self.hr_down_var.set(str(hr_down))
        
        # Carica le zone specifiche per lo sport
        if sport == "running" or sport == "swimming":
            # Zone di passo
            for name, var in self.pace_entries.items():
                value = self.config.get(f'sports.{sport}.paces.{name}', '')
                var.set(value)
            
            # Margini di passo
            faster = self.config.get(f'sports.{sport}.margins.faster', '0:05')
            slower = self.config.get(f'sports.{sport}.margins.slower', '0:05')
            
            self.pace_faster_var.set(faster)
            self.pace_slower_var.set(slower)
            
        elif sport == "cycling":
            # FTP
            ftp = self.config.get('sports.cycling.power_values.ftp', '250')
            self.ftp_var.set(ftp)
            
            # Zone di potenza
            for name, var in self.power_entries.items():
                value = self.config.get(f'sports.cycling.power_values.{name}', '')
                var.set(value)
            
            # Margini di potenza
            power_up = self.config.get('sports.cycling.margins.power_up', 10)
            power_down = self.config.get('sports.cycling.margins.power_down', 10)
            
            self.power_up_var.set(str(power_up))
            self.power_down_var.set(str(power_down))
    
    def save_zones(self):
        """Salva le zone nella configurazione."""
        # Ottieni lo sport selezionato
        sport = self.sport_var.get()
        
        try:
            # Salva la frequenza cardiaca
            try:
                max_hr = int(self.max_hr_var.get())
                rest_hr = int(self.rest_hr_var.get())
                
                if max_hr <= 0 or rest_hr <= 0:
                    raise ValueError("La frequenza cardiaca deve essere maggiore di zero")
                
                self.config.set('heart_rates.max_hr', max_hr)
                self.config.set('heart_rates.rest_hr', rest_hr)
                
            except ValueError:
                show_error("Errore", "La frequenza cardiaca deve essere un numero intero positivo", parent=self)
                return
            
            # Salva le zone di frequenza cardiaca
            for name, var in self.hr_entries.items():
                value = var.get()
                
                if value:
                    if not validate_hr(value):
                        show_error("Errore", f"Formato non valido per la zona {name}", parent=self)
                        return
                    
                    self.config.set(f'heart_rates.{name}', value)
            
            # Salva i margini di frequenza cardiaca
            try:
                hr_up = int(self.hr_up_var.get())
                hr_down = int(self.hr_down_var.get())
                
                if hr_up < 0 or hr_down < 0:
                    raise ValueError("I margini di frequenza cardiaca devono essere maggiori o uguali a zero")
                
                self.config.set('hr_margins.hr_up', hr_up)
                self.config.set('hr_margins.hr_down', hr_down)
                
            except ValueError:
                show_error("Errore", "I margini di frequenza cardiaca devono essere numeri interi non negativi", parent=self)
                return
            
            # Salva le zone specifiche per lo sport
            if sport == "running" or sport == "swimming":
                # Zone di passo
                for name, var in self.pace_entries.items():
                    value = var.get()
                    
                    if value:
                        # Verifica se è un range (MM:SS-MM:SS)
                        if "-" in value:
                            parts = value.split("-")
                            if len(parts) != 2 or not validate_pace(parts[0]) or not validate_pace(parts[1]):
                                show_error("Errore", f"Formato non valido per la zona {name}", parent=self)
                                return
                        # Verifica se è un singolo valore (MM:SS)
                        elif not validate_pace(value):
                            show_error("Errore", f"Formato non valido per la zona {name}", parent=self)
                            return
                        
                        self.config.set(f'sports.{sport}.paces.{name}', value)
                
                # Margini di passo
                faster = self.pace_faster_var.get()
                slower = self.pace_slower_var.get()
                
                if not validate_pace(faster) or not validate_pace(slower):
                    show_error("Errore", "Formato non valido per i margini di passo", parent=self)
                    return
                
                self.config.set(f'sports.{sport}.margins.faster', faster)
                self.config.set(f'sports.{sport}.margins.slower', slower)
                
            elif sport == "cycling":
                # FTP
                try:
                    ftp = int(self.ftp_var.get())
                    
                    if ftp <= 0:
                        raise ValueError("L'FTP deve essere maggiore di zero")
                    
                    self.config.set('sports.cycling.power_values.ftp', ftp)
                    
                except ValueError:
                    show_error("Errore", "L'FTP deve essere un numero intero positivo", parent=self)
                    return
                
                # Zone di potenza
                for name, var in self.power_entries.items():
                    value = var.get()
                    
                    if value:
                        if not validate_power(value):
                            show_error("Errore", f"Formato non valido per la zona {name}", parent=self)
                            return
                        
                        self.config.set(f'sports.cycling.power_values.{name}', value)
                
                # Margini di potenza
                try:
                    power_up = int(self.power_up_var.get())
                    power_down = int(self.power_down_var.get())
                    
                    if power_up < 0 or power_down < 0:
                        raise ValueError("I margini di potenza devono essere maggiori o uguali a zero")
                    
                    self.config.set('sports.cycling.margins.power_up', power_up)
                    self.config.set('sports.cycling.margins.power_down', power_down)
                    
                except ValueError:
                    show_error("Errore", "I margini di potenza devono essere numeri interi non negativi", parent=self)
                    return
            
            # Salva la configurazione
            self.config.save()
            
            # Mostra messaggio di conferma
            show_info("Configurazione salvata", 
                   "Le zone sono state salvate correttamente", 
                   parent=self)
            
            # Aggiorna la barra di stato
            self.controller.set_status("Zone di allenamento salvate")
            
        except Exception as e:
            logging.error(f"Errore nel salvataggio delle zone: {str(e)}")
            show_error("Errore", 
                     f"Impossibile salvare le zone: {str(e)}", 
                     parent=self)
    
    def reset_zones(self):
        """Ripristina le zone ai valori predefiniti."""
        # Chiedi conferma
        if not ask_yes_no("Conferma ripristino", 
                       "Sei sicuro di voler ripristinare le zone ai valori predefiniti?", 
                       parent=self):
            return
        
        # Ottieni lo sport selezionato
        sport = self.sport_var.get()
        
        # Ripristina i valori predefiniti per lo sport specifico
        default_config = self.config.config
        
        if sport == "running":
            # Zone di passo per la corsa
            default_paces = default_config['sports']['running']['paces']
            default_margins = default_config['sports']['running']['margins']
            
            # Imposta i valori
            for name, var in self.pace_entries.items():
                if name in default_paces:
                    var.set(default_paces[name])
            
            # Margini
            self.pace_faster_var.set(default_margins['faster'])
            self.pace_slower_var.set(default_margins['slower'])
            
        elif sport == "cycling":
            # Zone di potenza per il ciclismo
            default_powers = default_config['sports']['cycling']['power_values']
            default_margins = default_config['sports']['cycling']['margins']
            
            # FTP
            self.ftp_var.set(default_powers['ftp'])
            
            # Imposta i valori
            for name, var in self.power_entries.items():
                if name in default_powers:
                    var.set(default_powers[name])
            
            # Margini
            self.power_up_var.set(str(default_margins['power_up']))
            self.power_down_var.set(str(default_margins['power_down']))
            
        elif sport == "swimming":
            # Zone di passo per il nuoto
            default_paces = default_config['sports']['swimming']['paces']
            default_margins = default_config['sports']['swimming']['margins']
            
            # Imposta i valori
            for name, var in self.pace_entries.items():
                if name in default_paces:
                    var.set(default_paces[name])
            
            # Margini
            self.pace_faster_var.set(default_margins['faster'])
            self.pace_slower_var.set(default_margins['slower'])
        
        # Ripristina le zone di frequenza cardiaca
        default_hr = default_config['heart_rates']
        default_hr_margins = default_config['hr_margins']
        
        # FC max e riposo
        self.max_hr_var.set(str(default_hr['max_hr']))
        self.rest_hr_var.set(str(default_hr['rest_hr']))
        
        # Zone
        for name, var in self.hr_entries.items():
            if name in default_hr:
                var.set(default_hr[name])
        
        # Margini
        self.hr_up_var.set(str(default_hr_margins['hr_up']))
        self.hr_down_var.set(str(default_hr_margins['hr_down']))
        
        # Mostra messaggio di conferma
        show_info("Zone ripristinate", 
               "Le zone sono state ripristinate ai valori predefiniti", 
               parent=self)
    
    def on_activate(self):
        """Chiamato quando il frame viene attivato."""
        # Aggiorna le zone
        self.load_zones()


if __name__ == "__main__":
    # Test del frame
    root = tk.Tk()
    root.title("Zones Manager Test")
    root.geometry("1200x800")
    
    # Crea un notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Controller fittizio
    class DummyController:
        def set_status(self, message):
            print(message)
    
    # Crea il frame
    frame = ZonesManagerFrame(notebook, DummyController())
    notebook.add(frame, text="Zone")
    
    root.mainloop()