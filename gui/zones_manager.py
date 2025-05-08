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
        """Create widgets for pace zones."""
        # Description
        ttk.Label(self.pace_frame, text="Configure pace zones (format: mm:ss or mm:ss-mm:ss)").pack(fill=tk.X, pady=(0, 10))
        
        # Add a frame for the zone management tools
        tools_frame = ttk.Frame(self.pace_frame)
        tools_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(tools_frame, text="Add Zone", command=self.add_pace_zone).pack(side=tk.LEFT, padx=(0, 5))
        self.edit_pace_button = ttk.Button(tools_frame, text="Edit Zone", command=self.edit_pace_zone, state="disabled")
        self.edit_pace_button.pack(side=tk.LEFT, padx=(0, 5))
        self.delete_pace_button = ttk.Button(tools_frame, text="Delete Zone", command=self.delete_pace_zone, state="disabled")
        self.delete_pace_button.pack(side=tk.LEFT)
        
        # Create a frame for the zones treeview
        zones_frame = ttk.Frame(self.pace_frame)
        zones_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Create the treeview
        columns = ("name", "range", "description")
        self.pace_tree = ttk.Treeview(zones_frame, columns=columns, show="headings", selectmode="browse")
        
        # Set column headings
        self.pace_tree.heading("name", text="Name")
        self.pace_tree.heading("range", text="Pace Range (min/km)")
        self.pace_tree.heading("description", text="Description")
        
        # Set column widths
        self.pace_tree.column("name", width=100)
        self.pace_tree.column("range", width=150)
        self.pace_tree.column("description", width=250)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(zones_frame, orient=tk.VERTICAL, command=self.pace_tree.yview)
        self.pace_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack everything
        self.pace_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.pace_tree.bind("<<TreeviewSelect>>", self.on_pace_selected)
        
        # Frame for the margins
        margins_frame = ttk.LabelFrame(self.pace_frame, text="Tolerance Margins")
        margins_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Grid for aligning fields
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Faster margin
        ttk.Label(margins_grid, text="Faster:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.pace_faster_var = tk.StringVar()
        faster_entry = ttk.Entry(margins_grid, textvariable=self.pace_faster_var, width=5)
        faster_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="min:sec").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Slower margin
        ttk.Label(margins_grid, text="Slower:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.pace_slower_var = tk.StringVar()
        slower_entry = ttk.Entry(margins_grid, textvariable=self.pace_slower_var, width=5)
        slower_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="min:sec").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)
    
    def create_power_zones(self):
        """Create widgets for power zones."""
        # Description
        ttk.Label(self.power_frame, text="Configure power zones (format: N-N, N, <N or N+)").pack(fill=tk.X, pady=(0, 10))
        
        # Add a frame for the zone management tools
        tools_frame = ttk.Frame(self.power_frame)
        tools_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(tools_frame, text="Add Zone", command=self.add_power_zone).pack(side=tk.LEFT, padx=(0, 5))
        self.edit_power_button = ttk.Button(tools_frame, text="Edit Zone", command=self.edit_power_zone, state="disabled")
        self.edit_power_button.pack(side=tk.LEFT, padx=(0, 5))
        self.delete_power_button = ttk.Button(tools_frame, text="Delete Zone", command=self.delete_power_zone, state="disabled")
        self.delete_power_button.pack(side=tk.LEFT)
        
        # Create a frame for the zones treeview
        zones_frame = ttk.Frame(self.power_frame)
        zones_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Create the treeview
        columns = ("name", "range", "description")
        self.power_tree = ttk.Treeview(zones_frame, columns=columns, show="headings", selectmode="browse")
        
        # Set column headings
        self.power_tree.heading("name", text="Name")
        self.power_tree.heading("range", text="Power Range (watts)")
        self.power_tree.heading("description", text="Description")
        
        # Set column widths
        self.power_tree.column("name", width=100)
        self.power_tree.column("range", width=150)
        self.power_tree.column("description", width=250)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(zones_frame, orient=tk.VERTICAL, command=self.power_tree.yview)
        self.power_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack everything
        self.power_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.power_tree.bind("<<TreeviewSelect>>", self.on_power_selected)
        
        # Frame for the margins
        margins_frame = ttk.LabelFrame(self.power_frame, text="Tolerance Margins")
        margins_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Grid for aligning fields
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Upper margin
        ttk.Label(margins_grid, text="Upper:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.power_up_var = tk.StringVar()
        power_up_entry = ttk.Entry(margins_grid, textvariable=self.power_up_var, width=5)
        power_up_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="watts").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Lower margin
        ttk.Label(margins_grid, text="Lower:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.power_down_var = tk.StringVar()
        power_down_entry = ttk.Entry(margins_grid, textvariable=self.power_down_var, width=5)
        power_down_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="watts").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)

    def add_power_zone(self):
        """Add a new power zone."""
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_added(zone):
            # Add the zone to the configuration
            self.config.config['sports']['cycling']['power_values'][zone.name] = zone.to_string()
            
            # Update the zones list
            self.update_power_zones_list()
        
        dialog = ZoneEditorDialog(self, "power", None, on_zone_added)

    def edit_power_zone(self):
        """Edit the selected power zone."""
        # Check if a zone is selected
        selection = self.power_tree.selection()
        if not selection:
            return
        
        # Get the selected zone name
        item = selection[0]
        zone_name = self.power_tree.item(item, "values")[0]
        
        # Get the current zone values
        power_range = self.config.get(f'sports.cycling.power_values.{zone_name}', '')
        
        if not power_range:
            return
        
        # Create a PowerZone object
        zone = PowerZone.from_string(zone_name, power_range)
        
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_edited(edited_zone):
            # Check if the name has changed
            if edited_zone.name != zone_name:
                # Remove the old zone
                if zone_name in self.config.config['sports']['cycling']['power_values']:
                    del self.config.config['sports']['cycling']['power_values'][zone_name]
            
            # Update or add the zone
            self.config.config['sports']['cycling']['power_values'][edited_zone.name] = edited_zone.to_string()
            
            # Update the zones list
            self.update_power_zones_list()
        
        dialog = ZoneEditorDialog(self, "power", zone, on_zone_edited)

    def delete_power_zone(self):
        """Delete the selected power zone."""
        # Check if a zone is selected
        selection = self.power_tree.selection()
        if not selection:
            return
        
        # Get the selected zone name
        item = selection[0]
        zone_name = self.power_tree.item(item, "values")[0]
        
        # Ask for confirmation
        if not ask_yes_no("Confirm Deletion", 
                       f"Are you sure you want to delete the zone '{zone_name}'?", 
                       parent=self):
            return
        
        # Delete the zone from the configuration
        if zone_name in self.config.config['sports']['cycling']['power_values']:
            del self.config.config['sports']['cycling']['power_values'][zone_name]
        
        # Update the zones list
        self.update_power_zones_list()

    def on_power_selected(self, event):
        """Handle the selection of a power zone."""
        # Enable/disable buttons based on selection
        selection = self.power_tree.selection()
        if selection:
            self.edit_power_button.config(state="normal")
            self.delete_power_button.config(state="normal")
        else:
            self.edit_power_button.config(state="disabled")
            self.delete_power_button.config(state="disabled")
        
    def create_hr_zones(self):
        """Create widgets for heart rate zones."""
        # Description
        ttk.Label(self.hr_frame, text="Configure heart rate zones (format: N-N bpm or N-N% max_hr)").pack(fill=tk.X, pady=(0, 10))
        
        # Add a frame for the zone management tools
        tools_frame = ttk.Frame(self.hr_frame)
        tools_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(tools_frame, text="Add Zone", command=self.add_hr_zone).pack(side=tk.LEFT, padx=(0, 5))
        self.edit_hr_button = ttk.Button(tools_frame, text="Edit Zone", command=self.edit_hr_zone, state="disabled")
        self.edit_hr_button.pack(side=tk.LEFT, padx=(0, 5))
        self.delete_hr_button = ttk.Button(tools_frame, text="Delete Zone", command=self.delete_hr_zone, state="disabled")
        self.delete_hr_button.pack(side=tk.LEFT)
        
        # Create a frame for the zones treeview
        zones_frame = ttk.Frame(self.hr_frame)
        zones_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # Create the treeview
        columns = ("name", "range", "description")
        self.hr_tree = ttk.Treeview(zones_frame, columns=columns, show="headings", selectmode="browse")
        
        # Set column headings
        self.hr_tree.heading("name", text="Name")
        self.hr_tree.heading("range", text="Heart Rate Range")
        self.hr_tree.heading("description", text="Description")
        
        # Set column widths
        self.hr_tree.column("name", width=100)
        self.hr_tree.column("range", width=150)
        self.hr_tree.column("description", width=250)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(zones_frame, orient=tk.VERTICAL, command=self.hr_tree.yview)
        self.hr_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack everything
        self.hr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.hr_tree.bind("<<TreeviewSelect>>", self.on_hr_selected)
        
        # Frame for the margins
        margins_frame = ttk.LabelFrame(self.hr_frame, text="Tolerance Margins")
        margins_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Grid for aligning fields
        margins_grid = ttk.Frame(margins_frame)
        margins_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Upper margin
        ttk.Label(margins_grid, text="Upper:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.hr_up_var = tk.StringVar()
        hr_up_entry = ttk.Entry(margins_grid, textvariable=self.hr_up_var, width=5)
        hr_up_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="bpm").grid(row=0, column=2, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Lower margin
        ttk.Label(margins_grid, text="Lower:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        
        self.hr_down_var = tk.StringVar()
        hr_down_entry = ttk.Entry(margins_grid, textvariable=self.hr_down_var, width=5)
        hr_down_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(margins_grid, text="bpm").grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=5)

    def add_hr_zone(self):
        """Add a new heart rate zone."""
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_added(zone):
            # Add the zone to the configuration
            self.config.config['heart_rates'][zone.name] = zone.to_string()
            
            # Update the zones list
            self.update_hr_zones_list()
        
        dialog = ZoneEditorDialog(self, "heart_rate", None, on_zone_added)

    def edit_hr_zone(self):
        """Edit the selected heart rate zone."""
        # Check if a zone is selected
        selection = self.hr_tree.selection()
        if not selection:
            return
        
        # Get the selected zone name
        item = selection[0]
        zone_name = self.hr_tree.item(item, "values")[0]
        
        # Get the current zone values
        hr_range = self.config.get(f'heart_rates.{zone_name}', '')
        
        if not hr_range:
            return
        
        # Create a HeartRateZone object
        zone = HeartRateZone.from_string(zone_name, hr_range)
        
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_edited(edited_zone):
            # Check if the name has changed
            if edited_zone.name != zone_name:
                # Remove the old zone
                if zone_name in self.config.config['heart_rates']:
                    del self.config.config['heart_rates'][zone_name]
            
            # Update or add the zone
            self.config.config['heart_rates'][edited_zone.name] = edited_zone.to_string()
            
            # Update the zones list
            self.update_hr_zones_list()
        
        dialog = ZoneEditorDialog(self, "heart_rate", zone, on_zone_edited)

    def delete_hr_zone(self):
        """Delete the selected heart rate zone."""
        # Check if a zone is selected
        selection = self.hr_tree.selection()
        if not selection:
            return
        
        # Get the selected zone name
        item = selection[0]
        zone_name = self.hr_tree.item(item, "values")[0]
        
        # Ask for confirmation
        if not ask_yes_no("Confirm Deletion", 
                       f"Are you sure you want to delete the zone '{zone_name}'?", 
                       parent=self):
            return
        
        # Delete the zone from the configuration
        if zone_name in self.config.config['heart_rates']:
            del self.config.config['heart_rates'][zone_name]
        
        # Update the zones list
        self.update_hr_zones_list()

    def on_hr_selected(self, event):
        """Handle the selection of a heart rate zone."""
        # Enable/disable buttons based on selection
        selection = self.hr_tree.selection()
        if selection:
            self.edit_hr_button.config(state="normal")
            self.delete_hr_button.config(state="normal")
        else:
            self.edit_hr_button.config(state="disabled")
            self.delete_hr_button.config(state="disabled")

    def add_pace_zone(self):
        """Add a new pace zone."""
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_added(zone):
            # Add the zone to the configuration
            sport = self.sport_var.get()
            self.config.config['sports'][sport]['paces'][zone.name] = zone.to_string()
            
            # Update the zones list
            self.update_pace_zones_list()
        
        dialog = ZoneEditorDialog(self, "pace", None, on_zone_added)

    def edit_pace_zone(self):
        """Edit the selected pace zone."""
        # Check if a zone is selected
        selection = self.pace_tree.selection()
        if not selection:
            return
        
        # Get the selected zone name
        item = selection[0]
        zone_name = self.pace_tree.item(item, "values")[0]
        
        # Get the current zone values
        sport = self.sport_var.get()
        pace_range = self.config.get(f'sports.{sport}.paces.{zone_name}', '')
        
        if not pace_range:
            return
        
        # Create a PaceZone object
        zone = PaceZone.from_string(zone_name, pace_range)
        
        from gui.dialogs.zone_editor import ZoneEditorDialog
        
        def on_zone_edited(edited_zone):
            # Check if the name has changed
            if edited_zone.name != zone_name:
                # Remove the old zone
                if zone_name in self.config.config['sports'][sport]['paces']:
                    del self.config.config['sports'][sport]['paces'][zone_name]
            
            # Update or add the zone
            self.config.config['sports'][sport]['paces'][edited_zone.name] = edited_zone.to_string()
            
            # Update the zones list
            self.update_pace_zones_list()
        
        dialog = ZoneEditorDialog(self, "pace", zone, on_zone_edited)

    def delete_pace_zone(self):
        """Delete the selected pace zone."""
        # Check if a zone is selected
        selection = self.pace_tree.selection()
        if not selection:
            return
        
        # Get the selected zone name
        item = selection[0]
        zone_name = self.pace_tree.item(item, "values")[0]
        
        # Ask for confirmation
        if not ask_yes_no("Confirm Deletion", 
                       f"Are you sure you want to delete the zone '{zone_name}'?", 
                       parent=self):
            return
        
        # Delete the zone from the configuration
        sport = self.sport_var.get()
        if zone_name in self.config.config['sports'][sport]['paces']:
            del self.config.config['sports'][sport]['paces'][zone_name]
        
        # Update the zones list
        self.update_pace_zones_list()

    def on_pace_selected(self, event):
        """Handle the selection of a pace zone."""
        # Enable/disable buttons based on selection
        selection = self.pace_tree.selection()
        if selection:
            self.edit_pace_button.config(state="normal")
            self.delete_pace_button.config(state="normal")
        else:
            self.edit_pace_button.config(state="disabled")
            self.delete_pace_button.config(state="disabled")

    def update_pace_zones_list(self):
        """Update the list of pace zones."""
        # Clear the current list
        for item in self.pace_tree.get_children():
            self.pace_tree.delete(item)
        
        # Get the zones for the current sport
        sport = self.sport_var.get()
        paces = self.config.get(f'sports.{sport}.paces', {})
        
        # Add zones to the list
        for name, value in paces.items():
            description = ""  # We would need to store descriptions somewhere
            self.pace_tree.insert("", "end", values=(name, value, description))

    def update_power_zones_list(self):
        """Update the list of power zones."""
        # Clear the current list
        for item in self.power_tree.get_children():
            self.power_tree.delete(item)
        
        # Get the zones for cycling
        power_values = self.config.get('sports.cycling.power_values', {})
        
        # Add zones to the list
        for name, value in power_values.items():
            description = ""  # We would need to store descriptions somewhere
            self.power_tree.insert("", "end", values=(name, value, description))

    def update_hr_zones_list(self):
        """Update the list of heart rate zones."""
        # Clear the current list
        for item in self.hr_tree.get_children():
            self.hr_tree.delete(item)
        
        # Get the heart rate zones
        heart_rates = self.config.get('heart_rates', {})
        
        # Add zones to the list
        for name, value in heart_rates.items():
            if name.endswith('_HR') or name in ['max_hr', 'rest_hr']:
                description = ""  # We would need to store descriptions somewhere
                self.hr_tree.insert("", "end", values=(name, value, description))

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
        """Load zones from the configuration."""
        # Get the selected sport
        sport = self.sport_var.get()
        
        # Load heart rate
        max_hr = self.config.get('heart_rates.max_hr', 180)
        rest_hr = self.config.get('heart_rates.rest_hr', 60)
        
        self.max_hr_var.set(str(max_hr))
        self.rest_hr_var.set(str(rest_hr))
        
        # Update the zone lists
        self.update_pace_zones_list()
        self.update_power_zones_list()
        self.update_hr_zones_list()
        
        # Load pace/power margins
        if sport == "running" or sport == "swimming":
            # Pace margins
            faster = self.config.get(f'sports.{sport}.margins.faster', '0:05')
            slower = self.config.get(f'sports.{sport}.margins.slower', '0:05')
            
            self.pace_faster_var.set(faster)
            self.pace_slower_var.set(slower)
        elif sport == "cycling":
            # Power margins
            power_up = self.config.get('sports.cycling.margins.power_up', 10)
            power_down = self.config.get('sports.cycling.margins.power_down', 10)
            
            self.power_up_var.set(str(power_up))
            self.power_down_var.set(str(power_down))
        
        # Load heart rate margins
        hr_up = self.config.get('hr_margins.hr_up', 5)
        hr_down = self.config.get('hr_margins.hr_down', 5)
        
        self.hr_up_var.set(str(hr_up))
        self.hr_down_var.set(str(hr_down))
    
    def save_zones(self):
        """Save zones to the configuration."""
        # Get the selected sport
        sport = self.sport_var.get()
        
        try:
            # Save heart rate max and rest
            try:
                max_hr = int(self.max_hr_var.get())
                rest_hr = int(self.rest_hr_var.get())
                
                if max_hr <= 0 or rest_hr <= 0:
                    raise ValueError("Heart rate must be greater than zero")
                
                self.config.set('heart_rates.max_hr', max_hr)
                self.config.set('heart_rates.rest_hr', rest_hr)
                
            except ValueError:
                show_error("Error", "Heart rate must be a positive integer", parent=self)
                return
            
            # Save heart rate zones
            # Check if we're using the new Treeview structure or the old entries
            if hasattr(self, 'hr_tree'):
                # Using Treeview for heart rate zones
                heart_rates = self.config.get('heart_rates', {})
                
                # Make sure we keep max_hr and rest_hr in the config
                heart_rates_to_save = {
                    'max_hr': heart_rates.get('max_hr', max_hr),
                    'rest_hr': heart_rates.get('rest_hr', rest_hr)
                }
                
                # Get values from Treeview
                for item in self.hr_tree.get_children():
                    values = self.hr_tree.item(item, "values")
                    name = values[0]
                    value = values[1]
                    
                    # Skip max_hr and rest_hr as we already handled them
                    if name in ['max_hr', 'rest_hr']:
                        continue
                    
                    heart_rates_to_save[name] = value
                
                self.config.config['heart_rates'] = heart_rates_to_save
                
            elif hasattr(self, 'hr_entries'):
                # Using old entry-based approach
                for name, var in self.hr_entries.items():
                    value = var.get()
                    
                    if value:
                        if not validate_hr(value):
                            show_error("Error", f"Invalid format for zone {name}", parent=self)
                            return
                        
                        self.config.set(f'heart_rates.{name}', value)
            
            # Save heart rate margins
            try:
                hr_up = int(self.hr_up_var.get())
                hr_down = int(self.hr_down_var.get())
                
                if hr_up < 0 or hr_down < 0:
                    raise ValueError("Heart rate margins must be greater than or equal to zero")
                
                self.config.set('hr_margins.hr_up', hr_up)
                self.config.set('hr_margins.hr_down', hr_down)
                
            except ValueError:
                show_error("Error", "Heart rate margins must be non-negative integers", parent=self)
                return
            
            # Save sport-specific zones
            if sport == "running" or sport == "swimming":
                # Pace zones
                if hasattr(self, 'pace_tree'):
                    # Using Treeview for pace zones
                    paces_to_save = {}
                    
                    # Get values from Treeview
                    for item in self.pace_tree.get_children():
                        values = self.pace_tree.item(item, "values")
                        name = values[0]
                        value = values[1]
                        paces_to_save[name] = value
                    
                    self.config.config['sports'][sport]['paces'] = paces_to_save
                    
                elif hasattr(self, 'pace_entries'):
                    # Using old entry-based approach
                    for name, var in self.pace_entries.items():
                        value = var.get()
                        
                        if value:
                            # Verify if it's a range (MM:SS-MM:SS)
                            if "-" in value:
                                parts = value.split("-")
                                if len(parts) != 2 or not validate_pace(parts[0]) or not validate_pace(parts[1]):
                                    show_error("Error", f"Invalid format for zone {name}", parent=self)
                                    return
                            # Verify if it's a single value (MM:SS)
                            elif not validate_pace(value):
                                show_error("Error", f"Invalid format for zone {name}", parent=self)
                                return
                            
                            self.config.set(f'sports.{sport}.paces.{name}', value)
                
                # Pace margins
                faster = self.pace_faster_var.get()
                slower = self.pace_slower_var.get()
                
                if not validate_pace(faster) or not validate_pace(slower):
                    show_error("Error", "Invalid format for pace margins", parent=self)
                    return
                
                self.config.set(f'sports.{sport}.margins.faster', faster)
                self.config.set(f'sports.{sport}.margins.slower', slower)
                
            elif sport == "cycling":
                # FTP
                try:
                    ftp = int(self.ftp_var.get())
                    
                    if ftp <= 0:
                        raise ValueError("FTP must be greater than zero")
                    
                    self.config.set('sports.cycling.power_values.ftp', ftp)
                    
                except ValueError:
                    show_error("Error", "FTP must be a positive integer", parent=self)
                    return
                
                # Power zones
                if hasattr(self, 'power_tree'):
                    # Using Treeview for power zones
                    power_values = {}
                    power_values['ftp'] = str(ftp)  # Make sure FTP is included
                    
                    # Get values from Treeview
                    for item in self.power_tree.get_children():
                        values = self.power_tree.item(item, "values")
                        name = values[0]
                        value = values[1]
                        
                        # Skip ftp as we already handled it
                        if name == 'ftp':
                            continue
                        
                        power_values[name] = value
                    
                    self.config.config['sports']['cycling']['power_values'] = power_values
                    
                elif hasattr(self, 'power_entries'):
                    # Using old entry-based approach
                    for name, var in self.power_entries.items():
                        value = var.get()
                        
                        if value:
                            if not validate_power(value):
                                show_error("Error", f"Invalid format for zone {name}", parent=self)
                                return
                            
                            self.config.set(f'sports.cycling.power_values.{name}', value)
                
                # Power margins
                try:
                    power_up = int(self.power_up_var.get())
                    power_down = int(self.power_down_var.get())
                    
                    if power_up < 0 or power_down < 0:
                        raise ValueError("Power margins must be greater than or equal to zero")
                    
                    self.config.set('sports.cycling.margins.power_up', power_up)
                    self.config.set('sports.cycling.margins.power_down', power_down)
                    
                except ValueError:
                    show_error("Error", "Power margins must be non-negative integers", parent=self)
                    return
            
            # Save the configuration
            self.config.save()
            
            # Show confirmation message
            show_info("Configuration saved", 
                   "Zones have been saved successfully", 
                   parent=self)
            
            # Update the status bar
            self.controller.set_status("Training zones saved")
            
        except Exception as e:
            logging.error(f"Error saving zones: {str(e)}")
            show_error("Error", 
                     f"Unable to save zones: {str(e)}", 
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