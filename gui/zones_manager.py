#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Frame riorganizzato per la gestione delle zone di allenamento.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import re
from typing import Dict, Any, List, Tuple, Optional, Union

from config import get_config
from models.zone import (
    Zone, PaceZone, HeartRateZone, PowerZone, ZoneSet
)
from gui.utils import (
    create_tooltip, show_error, show_info, show_warning, ask_yes_no,
    create_scrollable_frame, validate_pace, validate_power, validate_hr,
    parse_pace_range, parse_power_range
)
from gui.styles import get_color_for_sport, get_icon_for_sport


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
        
        # Intestazione
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text="Configurazione Zone di Allenamento", 
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        # Notebook per i diversi tipi di zone
        self.zones_notebook = ttk.Notebook(main_frame)
        self.zones_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Tab per le zone di frequenza cardiaca (comune a tutti gli sport)
        self.hr_frame = ttk.Frame(self.zones_notebook, padding=10)
        self.zones_notebook.add(self.hr_frame, text="Frequenza Cardiaca")
        
        # Tab per le zone di passo (corsa, nuoto)
        self.running_pace_frame = ttk.Frame(self.zones_notebook, padding=10)
        self.zones_notebook.add(self.running_pace_frame, text="Passo Corsa")
        
        # Tab per le zone di passo del nuoto
        self.swimming_pace_frame = ttk.Frame(self.zones_notebook, padding=10)
        self.zones_notebook.add(self.swimming_pace_frame, text="Passo Nuoto")
        
        # Tab per le zone di potenza (ciclismo)
        self.power_frame = ttk.Frame(self.zones_notebook, padding=10)
        self.zones_notebook.add(self.power_frame, text="Potenza Ciclismo")
        
        # Frequenza cardiaca nel frame HR
        hr_config_frame = ttk.LabelFrame(self.hr_frame, text="Configurazione FC")
        hr_config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid per allineare i campi
        hr_grid = ttk.Frame(hr_config_frame)
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
        
        # Margini HR
        hr_margins_frame = ttk.LabelFrame(self.hr_frame, text="Margini FC")
        hr_margins_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid per allineare i campi
        hr_margins_grid = ttk.Frame(hr_margins_frame)
        hr_margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Margine superiore
        ttk.Label(hr_margins_grid, text="Superiore:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.hr_up_var = tk.StringVar(value=str(self.config.get('hr_margins.hr_up', 5)))
        hr_up_entry = ttk.Entry(hr_margins_grid, textvariable=self.hr_up_var, width=5)
        hr_up_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(hr_margins_grid, text="bpm").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Margine inferiore
        ttk.Label(hr_margins_grid, text="Inferiore:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.hr_down_var = tk.StringVar(value=str(self.config.get('hr_margins.hr_down', 5)))
        hr_down_entry = ttk.Entry(hr_margins_grid, textvariable=self.hr_down_var, width=5)
        hr_down_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(hr_margins_grid, text="bpm").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Gestione zone HR
        self.create_hr_zones_section(self.hr_frame)
        
        # Zona passo corsa
        self.create_pace_zones_section(self.running_pace_frame, "running")
        
        # Zona passo nuoto
        self.create_pace_zones_section(self.swimming_pace_frame, "swimming")
        
        # Zona potenza ciclismo
        self.create_power_zones_section(self.power_frame)
        
        # Pulsanti per salvataggio e ripristino
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.save_button = ttk.Button(buttons_frame, text="Salva", 
                                    command=self.save_zones)
        self.save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.reset_button = ttk.Button(buttons_frame, text="Ripristina", 
                                     command=self.reset_zones)
        self.reset_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Associa evento di cambio tab
        self.zones_notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def create_hr_zones_section(self, parent_frame):
        """Crea la sezione per gestire le zone di frequenza cardiaca."""
        # Frame per la gestione delle zone
        zones_frame = ttk.LabelFrame(parent_frame, text="Zone di Frequenza Cardiaca")
        zones_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar per la gestione delle zone
        toolbar = ttk.Frame(zones_frame)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        add_button = ttk.Button(toolbar, text="Aggiungi Zona", command=self.add_hr_zone)
        add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.edit_hr_button = ttk.Button(toolbar, text="Modifica Zona", 
                                      command=self.edit_hr_zone, state="disabled")
        self.edit_hr_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_hr_button = ttk.Button(toolbar, text="Elimina Zona", 
                                        command=self.delete_hr_zone, state="disabled")
        self.delete_hr_button.pack(side=tk.LEFT)
        
        # Lista delle zone
        list_frame = ttk.Frame(zones_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Crea il treeview
        columns = ("name", "range", "description")
        self.hr_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        
        # Intestazioni
        self.hr_tree.heading("name", text="Nome")
        self.hr_tree.heading("range", text="Intervallo")
        self.hr_tree.heading("description", text="Descrizione")
        
        # Larghezze colonne
        self.hr_tree.column("name", width=100)
        self.hr_tree.column("range", width=150)
        self.hr_tree.column("description", width=250)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.hr_tree.yview)
        self.hr_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.hr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Binding per la selezione
        self.hr_tree.bind("<<TreeviewSelect>>", self.on_hr_selected)
        
    def create_pace_zones_section(self, parent_frame, sport_type):
        """
        Crea la sezione per gestire le zone di passo.
        
        Args:
            parent_frame: Frame genitore
            sport_type: Tipo di sport (running, swimming)
        """
        # Frame per i margini
        margins_frame = ttk.LabelFrame(parent_frame, text="Margini di Passo")
        margins_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid per allineare i campi
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Margine più veloce
        ttk.Label(margins_grid, text="Più veloce:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        # Aggiungi variabili specifiche per sport
        if sport_type == "running":
            self.running_pace_faster_var = tk.StringVar(value=self.config.get('sports.running.margins.faster', '0:05'))
            faster_entry = ttk.Entry(margins_grid, textvariable=self.running_pace_faster_var, width=5)
        else:  # swimming
            self.swimming_pace_faster_var = tk.StringVar(value=self.config.get('sports.swimming.margins.faster', '0:05'))
            faster_entry = ttk.Entry(margins_grid, textvariable=self.swimming_pace_faster_var, width=5)
        
        faster_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(margins_grid, text="min:sec").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Margine più lento
        ttk.Label(margins_grid, text="Più lento:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        if sport_type == "running":
            self.running_pace_slower_var = tk.StringVar(value=self.config.get('sports.running.margins.slower', '0:05'))
            slower_entry = ttk.Entry(margins_grid, textvariable=self.running_pace_slower_var, width=5)
        else:  # swimming
            self.swimming_pace_slower_var = tk.StringVar(value=self.config.get('sports.swimming.margins.slower', '0:05'))
            slower_entry = ttk.Entry(margins_grid, textvariable=self.swimming_pace_slower_var, width=5)
        
        slower_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(margins_grid, text="min:sec").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Frame per la gestione delle zone
        zones_frame = ttk.LabelFrame(parent_frame, text="Zone di Passo")
        zones_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar per la gestione delle zone
        toolbar = ttk.Frame(zones_frame)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        if sport_type == "running":
            add_button = ttk.Button(toolbar, text="Aggiungi Zona", 
                                 command=lambda: self.add_pace_zone("running"))
            self.edit_pace_run_button = ttk.Button(toolbar, text="Modifica Zona", 
                                               command=lambda: self.edit_pace_zone("running"), 
                                               state="disabled")
            self.delete_pace_run_button = ttk.Button(toolbar, text="Elimina Zona", 
                                                 command=lambda: self.delete_pace_zone("running"), 
                                                 state="disabled")
            
            add_button.pack(side=tk.LEFT, padx=(0, 5))
            self.edit_pace_run_button.pack(side=tk.LEFT, padx=(0, 5))
            self.delete_pace_run_button.pack(side=tk.LEFT)
            
            # Lista delle zone
            list_frame = ttk.Frame(zones_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            # Crea il treeview
            columns = ("name", "range", "description")
            self.running_pace_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
            
            # Intestazioni
            self.running_pace_tree.heading("name", text="Nome")
            self.running_pace_tree.heading("range", text="Intervallo (min/km)")
            self.running_pace_tree.heading("description", text="Descrizione")
            
            # Larghezze colonne
            self.running_pace_tree.column("name", width=100)
            self.running_pace_tree.column("range", width=150)
            self.running_pace_tree.column("description", width=250)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.running_pace_tree.yview)
            self.running_pace_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack
            self.running_pace_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Binding per la selezione
            self.running_pace_tree.bind("<<TreeviewSelect>>", lambda e: self.on_pace_selected(e, "running"))
            
        else:  # swimming
            add_button = ttk.Button(toolbar, text="Aggiungi Zona", 
                                 command=lambda: self.add_pace_zone("swimming"))
            self.edit_pace_swim_button = ttk.Button(toolbar, text="Modifica Zona", 
                                                command=lambda: self.edit_pace_zone("swimming"), 
                                                state="disabled")
            self.delete_pace_swim_button = ttk.Button(toolbar, text="Elimina Zona", 
                                                  command=lambda: self.delete_pace_zone("swimming"), 
                                                  state="disabled")
            
            add_button.pack(side=tk.LEFT, padx=(0, 5))
            self.edit_pace_swim_button.pack(side=tk.LEFT, padx=(0, 5))
            self.delete_pace_swim_button.pack(side=tk.LEFT)
            
            # Lista delle zone
            list_frame = ttk.Frame(zones_frame)
            list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            # Crea il treeview
            columns = ("name", "range", "description")
            self.swimming_pace_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
            
            # Intestazioni
            self.swimming_pace_tree.heading("name", text="Nome")
            self.swimming_pace_tree.heading("range", text="Intervallo (min/100m)")
            self.swimming_pace_tree.heading("description", text="Descrizione")
            
            # Larghezze colonne
            self.swimming_pace_tree.column("name", width=100)
            self.swimming_pace_tree.column("range", width=150)
            self.swimming_pace_tree.column("description", width=250)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.swimming_pace_tree.yview)
            self.swimming_pace_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack
            self.swimming_pace_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Binding per la selezione
            self.swimming_pace_tree.bind("<<TreeviewSelect>>", lambda e: self.on_pace_selected(e, "swimming"))
    
    def create_power_zones_section(self, parent_frame):
        """Crea la sezione per gestire le zone di potenza."""
        # Frame per FTP
        ftp_frame = ttk.LabelFrame(parent_frame, text="FTP (Functional Threshold Power)")
        ftp_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid per allineare i campi
        ftp_grid = ttk.Frame(ftp_frame)
        ftp_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # FTP
        ttk.Label(ftp_grid, text="FTP:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.ftp_var = tk.StringVar(value=str(self.config.get('sports.cycling.power_values.ftp', 250)))
        ftp_entry = ttk.Entry(ftp_grid, textvariable=self.ftp_var, width=5)
        ftp_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(ftp_grid, text="watt").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Frame per i margini
        margins_frame = ttk.LabelFrame(parent_frame, text="Margini di Potenza")
        margins_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid per allineare i campi
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Margine superiore
        ttk.Label(margins_grid, text="Superiore:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.power_up_var = tk.StringVar(value=str(self.config.get('sports.cycling.margins.power_up', 10)))
        power_up_entry = ttk.Entry(margins_grid, textvariable=self.power_up_var, width=5)
        power_up_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="watt").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Margine inferiore
        ttk.Label(margins_grid, text="Inferiore:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.power_down_var = tk.StringVar(value=str(self.config.get('sports.cycling.margins.power_down', 10)))
        power_down_entry = ttk.Entry(margins_grid, textvariable=self.power_down_var, width=5)
        power_down_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="watt").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Frame per la gestione delle zone
        zones_frame = ttk.LabelFrame(parent_frame, text="Zone di Potenza")
        zones_frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar per la gestione delle zone
        toolbar = ttk.Frame(zones_frame)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        
        add_button = ttk.Button(toolbar, text="Aggiungi Zona", command=self.add_power_zone)
        add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.edit_power_button = ttk.Button(toolbar, text="Modifica Zona", 
                                         command=self.edit_power_zone, state="disabled")
        self.edit_power_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.delete_power_button = ttk.Button(toolbar, text="Elimina Zona", 
                                           command=self.delete_power_zone, state="disabled")
        self.delete_power_button.pack(side=tk.LEFT)
        
        # Lista delle zone
        list_frame = ttk.Frame(zones_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Crea il treeview
        columns = ("name", "range", "description")
        self.power_tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        
        # Intestazioni
        self.power_tree.heading("name", text="Nome")
        self.power_tree.heading("range", text="Intervallo (watt)")
        self.power_tree.heading("description", text="Descrizione")
        
        # Larghezze colonne
        self.power_tree.column("name", width=100)
        self.power_tree.column("range", width=150)
        self.power_tree.column("description", width=250)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.power_tree.yview)
        self.power_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.power_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Binding per la selezione
        self.power_tree.bind("<<TreeviewSelect>>", self.on_power_selected)
    
    # Aggiungi i metodi per gestire gli eventi e le azioni delle zone
    
    def on_tab_changed(self, event):
        """Gestisce il cambio di tab."""
        # Nessuna azione specifica necessaria al momento
        pass
    
    def add_hr_zone(self):
        """Aggiunge una nuova zona di frequenza cardiaca."""
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_added(zone):
            # Aggiungi la zona alla configurazione
            self.config.config['heart_rates'][zone.name] = zone.to_string()
            
            # Aggiorna la lista
            self.update_hr_zones_list()
        
        dialog = ZoneEditorDialog(self, "heart_rate", None, on_zone_added)
    
    def edit_hr_zone(self):
        """Modifica la zona di frequenza cardiaca selezionata."""
        # Verifica che sia selezionata una zona
        selection = self.hr_tree.selection()
        if not selection:
            return
        
        # Ottieni la zona selezionata
        item = selection[0]
        zone_name = self.hr_tree.item(item, "values")[0]
        
        # Ottieni i valori attuali
        hr_range = self.config.get(f'heart_rates.{zone_name}', '')
        
        if not hr_range:
            return
        
        # Crea l'oggetto zona
        zone = HeartRateZone.from_string(zone_name, hr_range)
        
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_edited(edited_zone):
            # Controlla se il nome è cambiato
            if edited_zone.name != zone_name:
                # Rimuovi la vecchia zona
                if zone_name in self.config.config['heart_rates']:
                    del self.config.config['heart_rates'][zone_name]
            
            # Aggiorna o aggiungi la zona
            self.config.config['heart_rates'][edited_zone.name] = edited_zone.to_string()
            
            # Aggiorna la lista
            self.update_hr_zones_list()
        
        dialog = ZoneEditorDialog(self, "heart_rate", zone, on_zone_edited)
    
    def delete_hr_zone(self):
        """Elimina la zona di frequenza cardiaca selezionata."""
        # Verifica che sia selezionata una zona
        selection = self.hr_tree.selection()
        if not selection:
            return
        
        # Ottieni la zona selezionata
        item = selection[0]
        zone_name = self.hr_tree.item(item, "values")[0]
        
        # Chiedi conferma
        if not ask_yes_no("Conferma eliminazione", 
                      f"Sei sicuro di voler eliminare la zona '{zone_name}'?", 
                      parent=self):
            return
        
        # Elimina la zona
        if zone_name in self.config.config['heart_rates']:
            del self.config.config['heart_rates'][zone_name]
        
        # Aggiorna la lista
        self.update_hr_zones_list()
    
    def on_hr_selected(self, event):
        """Gestisce la selezione di una zona di frequenza cardiaca."""
        # Abilita/disabilita i pulsanti in base alla selezione
        selection = self.hr_tree.selection()
        if selection:
            self.edit_hr_button.config(state="normal")
            self.delete_hr_button.config(state="normal")
        else:
            self.edit_hr_button.config(state="disabled")
            self.delete_hr_button.config(state="disabled")
    
    def add_pace_zone(self, sport_type):
        """
        Aggiunge una nuova zona di passo.
        
        Args:
            sport_type: Tipo di sport (running, swimming)
        """
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_added(zone):
            # Aggiungi la zona alla configurazione
            self.config.config['sports'][sport_type]['paces'][zone.name] = zone.to_string()
            
            # Aggiorna la lista
            self.update_pace_zones_list(sport_type)
        
        dialog = ZoneEditorDialog(self, "pace", None, on_zone_added)
    
    def edit_pace_zone(self, sport_type):
        """
        Modifica la zona di passo selezionata.
        
        Args:
            sport_type: Tipo di sport (running, swimming)
        """
        # Verifica che sia selezionata una zona
        tree = self.running_pace_tree if sport_type == "running" else self.swimming_pace_tree
        selection = tree.selection()
        if not selection:
            return
        
        # Ottieni la zona selezionata
        item = selection[0]
        zone_name = tree.item(item, "values")[0]
        
        # Ottieni i valori attuali
        pace_range = self.config.get(f'sports.{sport_type}.paces.{zone_name}', '')
        
        if not pace_range:
            return
        
        # Crea l'oggetto zona
        zone = PaceZone.from_string(zone_name, pace_range)
        
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_edited(edited_zone):
            # Controlla se il nome è cambiato
            if edited_zone.name != zone_name:
                # Rimuovi la vecchia zona
                if zone_name in self.config.config['sports'][sport_type]['paces']:
                    del self.config.config['sports'][sport_type]['paces'][zone_name]
            
            # Aggiorna o aggiungi la zona
            self.config.config['sports'][sport_type]['paces'][edited_zone.name] = edited_zone.to_string()
            
            # Aggiorna la lista
            self.update_pace_zones_list(sport_type)
        
        dialog = ZoneEditorDialog(self, "pace", zone, on_zone_edited)
    
    def delete_pace_zone(self, sport_type):
        """
        Elimina la zona di passo selezionata.
        
        Args:
            sport_type: Tipo di sport (running, swimming)
        """
        # Verifica che sia selezionata una zona
        tree = self.running_pace_tree if sport_type == "running" else self.swimming_pace_tree
        selection = tree.selection()
        if not selection:
            return
        
        # Ottieni la zona selezionata
        item = selection[0]
        zone_name = tree.item(item, "values")[0]
        
        # Chiedi conferma
        if not ask_yes_no("Conferma eliminazione", 
                      f"Sei sicuro di voler eliminare la zona '{zone_name}'?", 
                      parent=self):
            return
        
        # Elimina la zona
        if zone_name in self.config.config['sports'][sport_type]['paces']:
            del self.config.config['sports'][sport_type]['paces'][zone_name]
        
        # Aggiorna la lista
        self.update_pace_zones_list(sport_type)
    
    def on_pace_selected(self, event, sport_type):
        """
        Gestisce la selezione di una zona di passo.
        
        Args:
            event: Evento Tkinter
            sport_type: Tipo di sport (running, swimming)
        """
        # Abilita/disabilita i pulsanti in base alla selezione
        if sport_type == "running":
            selection = self.running_pace_tree.selection()
            if selection:
                self.edit_pace_run_button.config(state="normal")
                self.delete_pace_run_button.config(state="normal")
            else:
                self.edit_pace_run_button.config(state="disabled")
                self.delete_pace_run_button.config(state="disabled")
        else:  # swimming
            selection = self.swimming_pace_tree.selection()
            if selection:
                self.edit_pace_swim_button.config(state="normal")
                self.delete_pace_swim_button.config(state="normal")
            else:
                self.edit_pace_swim_button.config(state="disabled")
                self.delete_pace_swim_button.config(state="disabled")
    
    def add_power_zone(self):
        """Aggiunge una nuova zona di potenza."""
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_added(zone):
            # Aggiungi la zona alla configurazione
            self.config.config['sports']['cycling']['power_values'][zone.name] = zone.to_string()
            
            # Aggiorna la lista
            self.update_power_zones_list()
        
        dialog = ZoneEditorDialog(self, "power", None, on_zone_added)
    
    def edit_power_zone(self):
        """Modifica la zona di potenza selezionata."""
        # Verifica che sia selezionata una zona
        selection = self.power_tree.selection()
        if not selection:
            return
        
        # Ottieni la zona selezionata
        item = selection[0]
        zone_name = self.power_tree.item(item, "values")[0]
        
        # Ottieni i valori attuali
        power_range = self.config.get(f'sports.cycling.power_values.{zone_name}', '')
        
        if not power_range:
            return
        
        # Crea l'oggetto zona
        zone = PowerZone.from_string(zone_name, power_range)
        
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_edited(edited_zone):
            # Controlla se il nome è cambiato
            if edited_zone.name != zone_name:
                # Rimuovi la vecchia zona
                if zone_name in self.config.config['sports']['cycling']['power_values']:
                    del self.config.config['sports']['cycling']['power_values'][zone_name]
            
            # Aggiorna o aggiungi la zona
            self.config.config['sports']['cycling']['power_values'][edited_zone.name] = edited_zone.to_string()
            
            # Aggiorna la lista
            self.update_power_zones_list()
        
        dialog = ZoneEditorDialog(self, "power", zone, on_zone_edited)
    
    def delete_power_zone(self):
        """Elimina la zona di potenza selezionata."""
        # Verifica che sia selezionata una zona
        selection = self.power_tree.selection()
        if not selection:
            return
        
        # Ottieni la zona selezionata
        item = selection[0]
        zone_name = self.power_tree.item(item, "values")[0]
        
        # Chiedi conferma
        if not ask_yes_no("Conferma eliminazione", 
                      f"Sei sicuro di voler eliminare la zona '{zone_name}'?", 
                      parent=self):
            return
        
        # Elimina la zona
        if zone_name in self.config.config['sports']['cycling']['power_values']:
            del self.config.config['sports']['cycling']['power_values'][zone_name]
        
        # Aggiorna la lista
        self.update_power_zones_list()
    
    def on_power_selected(self, event):
        """Gestisce la selezione di una zona di potenza."""
        # Abilita/disabilita i pulsanti in base alla selezione
        selection = self.power_tree.selection()
        if selection:
            self.edit_power_button.config(state="normal")
            self.delete_power_button.config(state="normal")
        else:
            self.edit_power_button.config(state="disabled")
            self.delete_power_button.config(state="disabled")
    
    def update_hr_zones_list(self):
        """Aggiorna la lista delle zone di frequenza cardiaca."""
        # Pulisci la lista
        for item in self.hr_tree.get_children():
            self.hr_tree.delete(item)
        
        # Ottieni le zone
        heart_rates = self.config.get('heart_rates', {})
        
        # Aggiungi le zone alla lista
        for name, value in heart_rates.items():
            if name.endswith('_HR') or name in ['max_hr', 'rest_hr']:
                # Descrizione per zone comuni
                description = ""
                if name == 'Z1_HR':
                    description = "Zona di recupero attivo"
                elif name == 'Z2_HR':
                    description = "Zona aerobica di base"
                elif name == 'Z3_HR':
                    description = "Zona aerobica di sviluppo"
                elif name == 'Z4_HR':
                    description = "Zona di soglia anaerobica"
                elif name == 'Z5_HR':
                    description = "Zona di VO2max"
                
                self.hr_tree.insert("", "end", values=(name, value, description))
    
    def update_pace_zones_list(self, sport_type):
        """
        Aggiorna la lista delle zone di passo.
        
        Args:
            sport_type: Tipo di sport (running, swimming)
        """
        # Seleziona il treeview appropriato
        tree = self.running_pace_tree if sport_type == "running" else self.swimming_pace_tree
        
        # Pulisci la lista
        for item in tree.get_children():
            tree.delete(item)
        
        # Ottieni le zone
        paces = self.config.get(f'sports.{sport_type}.paces', {})
        
        # Aggiungi le zone alla lista
        for name, value in paces.items():
            # Descrizione per zone comuni
            description = ""
            if name == 'Z1':
                description = "Zona facile/recuperativa"
            elif name == 'Z2':
                description = "Zona aerobica"
            elif name == 'Z3':
                description = "Zona di soglia aerobica"
            elif name == 'Z4':
                description = "Zona di soglia anaerobica"
            elif name == 'Z5':
                description = "Zona di VO2max"
            elif name == 'recovery':
                description = "Recupero"
            elif name == 'threshold':
                description = "Soglia"
            elif name == 'marathon':
                description = "Passo maratona"
            elif name == 'race_pace':
                description = "Passo gara"
            
            tree.insert("", "end", values=(name, value, description))
    
    def update_power_zones_list(self):
        """Aggiorna la lista delle zone di potenza."""
        # Pulisci la lista
        for item in self.power_tree.get_children():
            self.power_tree.delete(item)
        
        # Ottieni le zone
        power_values = self.config.get('sports.cycling.power_values', {})
        
        # Aggiungi le zone alla lista
        for name, value in power_values.items():
            # Salta FTP, verrà mostrato nel campo dedicato
            if name == 'ftp':
                continue
                
            # Descrizione per zone comuni
            description = ""
            if name == 'Z1':
                description = "Recupero attivo (55-75% FTP)"
            elif name == 'Z2':
                description = "Resistenza/Fondo (76-90% FTP)"
            elif name == 'Z3':
                description = "Tempo/Soglia (91-105% FTP)"
            elif name == 'Z4':
                description = "VO2max (106-120% FTP)"
            elif name == 'Z5':
                description = "Capacità anaerobica (121-150% FTP)"
            elif name == 'Z6':
                description = "Potenza neuromuscolare (>150% FTP)"
            elif name == 'recovery':
                description = "Recupero (<55% FTP)"
            elif name == 'threshold':
                description = "Soglia (95-105% FTP)"
            elif name == 'sweet_spot':
                description = "Sweet Spot (88-94% FTP)"
            
            self.power_tree.insert("", "end", values=(name, value, description))
    
    def load_zones(self):
        """Carica le zone dalla configurazione."""
        # Aggiorna le liste delle zone
        self.update_hr_zones_list()
        self.update_pace_zones_list("running")
        self.update_pace_zones_list("swimming")
        self.update_power_zones_list()
    
    def save_zones(self):
        """Salva le zone nella configurazione."""
        try:
            # Salva i valori di frequenza cardiaca
            try:
                max_hr = int(self.max_hr_var.get())
                rest_hr = int(self.rest_hr_var.get())
                
                if max_hr <= 0 or rest_hr <= 0:
                    raise ValueError("La frequenza cardiaca deve essere maggiore di zero")
                
                self.config.set('heart_rates.max_hr', max_hr)
                self.config.set('heart_rates.rest_hr', rest_hr)
                
            except ValueError:
                show_error("Errore", "La frequenza cardiaca deve essere un intero positivo", parent=self)
                return
            
            # Salva i margini HR
            try:
                hr_up = int(self.hr_up_var.get())
                hr_down = int(self.hr_down_var.get())
                
                if hr_up < 0 or hr_down < 0:
                    raise ValueError("I margini di frequenza cardiaca devono essere maggiori o uguali a zero")
                
                self.config.set('hr_margins.hr_up', hr_up)
                self.config.set('hr_margins.hr_down', hr_down)
                
            except ValueError:
                show_error("Errore", "I margini di frequenza cardiaca devono essere interi non negativi", parent=self)
                return
            
            # Salva i margini di passo per la corsa
            faster = self.running_pace_faster_var.get()
            slower = self.running_pace_slower_var.get()
            
            if not validate_pace(faster) or not validate_pace(slower):
                show_error("Errore", "Formato non valido per i margini di passo della corsa", parent=self)
                return
            
            self.config.set('sports.running.margins.faster', faster)
            self.config.set('sports.running.margins.slower', slower)
            
            # Salva i margini di passo per il nuoto
            faster = self.swimming_pace_faster_var.get()
            slower = self.swimming_pace_slower_var.get()
            
            if not validate_pace(faster) or not validate_pace(slower):
                show_error("Errore", "Formato non valido per i margini di passo del nuoto", parent=self)
                return
            
            self.config.set('sports.swimming.margins.faster', faster)
            self.config.set('sports.swimming.margins.slower', slower)
            
            # Salva FTP
            try:
                ftp = int(self.ftp_var.get())
                
                if ftp <= 0:
                    raise ValueError("FTP deve essere maggiore di zero")
                
                self.config.set('sports.cycling.power_values.ftp', ftp)
                
            except ValueError:
                show_error("Errore", "FTP deve essere un intero positivo", parent=self)
                return
            
            # Salva i margini di potenza
            try:
                power_up = int(self.power_up_var.get())
                power_down = int(self.power_down_var.get())
                
                if power_up < 0 or power_down < 0:
                    raise ValueError("I margini di potenza devono essere maggiori o uguali a zero")
                
                self.config.set('sports.cycling.margins.power_up', power_up)
                self.config.set('sports.cycling.margins.power_down', power_down)
                
            except ValueError:
                show_error("Errore", "I margini di potenza devono essere interi non negativi", parent=self)
                return
            
            # Salva la configurazione
            self.config.save()
            
            # Mostra messaggio di conferma
            show_info("Configurazione salvata", "Le zone sono state salvate con successo", parent=self)
            
            # Aggiorna la barra di stato
            self.controller.set_status("Zone di allenamento salvate")
            
        except Exception as e:
            logging.error(f"Errore nel salvataggio delle zone: {str(e)}")
            show_error("Errore", f"Impossibile salvare le zone: {str(e)}", parent=self)
    
    def reset_zones(self):
        """Ripristina le zone ai valori predefiniti."""
        # Chiedi conferma
        if not ask_yes_no("Conferma ripristino", 
                       "Sei sicuro di voler ripristinare le zone ai valori predefiniti?", 
                       parent=self):
            return
        
        # Ripristina i valori predefiniti
        default_config = get_config(reset=True).config
        
        # Ripristina la frequenza cardiaca
        self.max_hr_var.set(str(default_config['heart_rates']['max_hr']))
        self.rest_hr_var.set(str(default_config['heart_rates']['rest_hr']))
        
        # Ripristina i margini HR
        self.hr_up_var.set(str(default_config['hr_margins']['hr_up']))
        self.hr_down_var.set(str(default_config['hr_margins']['hr_down']))
        
        # Ripristina i margini di passo per la corsa
        self.running_pace_faster_var.set(default_config['sports']['running']['margins']['faster'])
        self.running_pace_slower_var.set(default_config['sports']['running']['margins']['slower'])
        
        # Ripristina i margini di passo per il nuoto
        self.swimming_pace_faster_var.set(default_config['sports']['swimming']['margins']['faster'])
        self.swimming_pace_slower_var.set(default_config['sports']['swimming']['margins']['slower'])
        
        # Ripristina FTP
        self.ftp_var.set(str(default_config['sports']['cycling']['power_values']['ftp']))
        
        # Ripristina i margini di potenza
        self.power_up_var.set(str(default_config['sports']['cycling']['margins']['power_up']))
        self.power_down_var.set(str(default_config['sports']['cycling']['margins']['power_down']))
        
        # Ripristina tutte le zone
        self.config.config['heart_rates'] = default_config['heart_rates'].copy()
        self.config.config['sports']['running']['paces'] = default_config['sports']['running']['paces'].copy()
        self.config.config['sports']['swimming']['paces'] = default_config['sports']['swimming']['paces'].copy()
        self.config.config['sports']['cycling']['power_values'] = default_config['sports']['cycling']['power_values'].copy()
        
        # Aggiorna le liste
        self.load_zones()
        
        # Mostra messaggio di conferma
        show_info("Zone ripristinate", "Le zone sono state ripristinate ai valori predefiniti", parent=self)
    
    def on_activate(self):
        """Chiamato quando il frame viene attivato."""
        # Aggiorna le zone
        self.load_zones()