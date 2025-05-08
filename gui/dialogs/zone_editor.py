#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog for adding and editing training zones.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any

from models.zone import Zone, PaceZone, HeartRateZone, PowerZone
from gui.utils import (
    create_tooltip, show_error, validate_pace,
    validate_power, validate_hr
)


class ZoneEditorDialog(tk.Toplevel):
    """Dialog for adding and editing training zones."""
    
    def __init__(self, parent, zone_type: str, zone: Optional[Zone] = None,
                 callback: Optional[Callable] = None):
        """
        Initialize the dialog.
        
        Args:
            parent: Parent widget
            zone_type: Type of zone (pace, power, heart_rate)
            zone: Zone to edit (None for adding a new zone)
            callback: Function to call on confirmation (receives the zone)
        """
        super().__init__(parent)
        self.parent = parent
        self.zone_type = zone_type
        self.zone = zone
        self.callback = callback
        
        # Store reference to entry widgets
        self.min_value_entry = None
        self.max_value_entry = None
        
        # Default values if no zone is provided
        if zone:
            self.name = zone.name
            self.description = zone.description or ""
            
            if isinstance(zone, PaceZone):
                self.min_value = zone.min_pace
                self.max_value = zone.max_pace
            elif isinstance(zone, HeartRateZone):
                self.min_value = str(zone.min_hr)
                self.max_value = str(zone.max_hr)
            elif isinstance(zone, PowerZone):
                self.min_value = str(zone.min_power)
                self.max_value = str(zone.max_power)
            else:
                self.min_value = ""
                self.max_value = ""
        else:
            self.name = ""
            self.description = ""
            self.min_value = ""
            self.max_value = ""
        
        # Variables
        self.name_var = tk.StringVar(value=self.name)
        self.description_var = tk.StringVar(value=self.description)
        self.min_value_var = tk.StringVar(value=self.min_value)
        self.max_value_var = tk.StringVar(value=self.max_value)
        self.single_value_var = tk.BooleanVar(value=self.min_value == self.max_value and self.min_value != '')
        
        # Configure the dialog
        self.title("Edit Zone" if zone else "Add Zone")
        self.geometry("450x350")  # Increased height for new widgets
        self.transient(parent)
        self.grab_set()
        
        # Create widgets
        self.create_widgets()
        
        # Center the dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Add callbacks
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def create_widgets(self):
        """Create the dialog widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_text = "Edit Zone" if self.zone else "Add Zone"
        ttk.Label(header_frame, text=title_text, style="Title.TLabel").pack(side=tk.LEFT)
        
        # Zone details frame
        details_frame = ttk.Frame(main_frame)
        details_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Name
        ttk.Label(details_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        name_entry = ttk.Entry(details_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # Description
        ttk.Label(details_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        desc_entry = ttk.Entry(details_frame, textvariable=self.description_var, width=30)
        desc_entry.grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        # Note about margins
        margin_note = ""
        if self.zone_type == "pace":
            margin_note = "Note: When using a single value, pace margins will be applied in workouts"
        elif self.zone_type == "heart_rate":
            margin_note = "Note: When using a single value, heart rate margins will be applied in workouts"
        elif self.zone_type == "power":
            margin_note = "Note: When using a single value, power margins will be applied in workouts"
        
        if margin_note:
            ttk.Label(details_frame, text=margin_note, font=("Arial", 8, "italic")).grid(
                row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Value labels depend on zone type
        if self.zone_type == "pace":
            min_label = "Min Pace (mm:ss):"
            max_label = "Max Pace (mm:ss):"
            create_tooltip(name_entry, "Enter a name for this pace zone (e.g., 'Easy', 'Tempo')")
        elif self.zone_type == "heart_rate":
            min_label = "Min Heart Rate (bpm):"
            max_label = "Max Heart Rate (bpm):"
            create_tooltip(name_entry, "Enter a name for this heart rate zone (e.g., 'Aerobic', 'Threshold')")
        elif self.zone_type == "power":
            min_label = "Min Power (watts):"
            max_label = "Max Power (watts):"
            create_tooltip(name_entry, "Enter a name for this power zone (e.g., 'Recovery', 'Threshold')")
        else:
            min_label = "Min Value:"
            max_label = "Max Value:"
        
        # Min value
        ttk.Label(details_frame, text=min_label).grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.min_value_entry = ttk.Entry(details_frame, textvariable=self.min_value_var, width=15)
        self.min_value_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Max value
        ttk.Label(details_frame, text=max_label).grid(row=4, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.max_value_entry = ttk.Entry(details_frame, textvariable=self.max_value_var, width=15)
        self.max_value_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Add tooltips to min/max entries
        tooltip_text = "For a single value zone, enter the same value in both fields or use the checkbox below"
        create_tooltip(self.min_value_entry, tooltip_text)  # Corrected to use self.min_value_entry
        create_tooltip(self.max_value_entry, tooltip_text)  # Corrected to use self.max_value_entry
        
        # Single value checkbox
        single_value_check = ttk.Checkbutton(
            details_frame, 
            text="Use single value (margins will be applied in workouts)",
            variable=self.single_value_var,
            command=self.on_single_value_changed
        )
        single_value_check.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        # Configure the grid
        details_frame.columnconfigure(1, weight=1)
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Save", command=self.on_save).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Update based on single value status
        self.on_single_value_changed()
        
        # Set focus to name entry
        name_entry.focus_set()
    
    def on_single_value_changed(self):
        """Handle changes to the single value checkbox."""
        if self.single_value_var.get():
            # When single value is checked, make max value match min value
            if self.min_value_var.get():
                self.max_value_var.set(self.min_value_var.get())
                self.max_value_entry.config(state="disabled")
            else:
                # If min is empty, use max value for both
                if self.max_value_var.get():
                    self.min_value_var.set(self.max_value_var.get())
                    self.max_value_entry.config(state="disabled")
        else:
            # When unchecked, enable max value entry
            self.max_value_entry.config(state="normal")
    
    def validate(self) -> bool:
        """
        Validate the entered data.
        
        Returns:
            True if the data is valid, False otherwise
        """
        # Validate name
        name = self.name_var.get().strip()
        if not name:
            show_error("Error", "Please enter a zone name", parent=self)
            return False
        
        # Validate values based on zone type
        min_value = self.min_value_var.get().strip()
        max_value = self.max_value_var.get().strip()
        
        if not min_value or not max_value:
            show_error("Error", "Please enter both minimum and maximum values", parent=self)
            return False
        
        if self.zone_type == "pace":
            if not validate_pace(min_value):
                show_error("Error", "Min pace must be in mm:ss format (e.g., 5:30)", parent=self)
                return False
            
            if not validate_pace(max_value):
                show_error("Error", "Max pace must be in mm:ss format (e.g., 5:00)", parent=self)
                return False
        
        elif self.zone_type == "heart_rate":
            if not validate_hr(min_value):
                show_error("Error", "Min heart rate must be a valid number", parent=self)
                return False
            
            if not validate_hr(max_value):
                show_error("Error", "Max heart rate must be a valid number", parent=self)
                return False
        
        elif self.zone_type == "power":
            if not validate_power(min_value):
                show_error("Error", "Min power must be a valid number", parent=self)
                return False
            
            if not validate_power(max_value):
                show_error("Error", "Max power must be a valid number", parent=self)
                return False
        
        return True
    
    def on_save(self):
        """Handle the Save button click."""
        # Validate the data
        if not self.validate():
            return
        
        # Get the values
        name = self.name_var.get().strip()
        description = self.description_var.get().strip()
        min_value = self.min_value_var.get().strip()
        
        # For single value, use min_value for both
        if self.single_value_var.get():
            max_value = min_value
        else:
            max_value = self.max_value_var.get().strip()
        
        # Create or update the zone
        if self.zone_type == "pace":
            zone = PaceZone(name, min_value, max_value, description)
        elif self.zone_type == "heart_rate":
            zone = HeartRateZone(name, min_value, max_value, description)
        elif self.zone_type == "power":
            zone = PowerZone(name, min_value, max_value, description)
        else:
            zone = Zone(name, description)
        
        # Call the callback
        if self.callback:
            self.callback(zone)
        
        # Close the dialog
        self.destroy()
    
    def on_cancel(self):
        """Handle the Cancel button click."""
        # Close the dialog without doing anything
        self.destroy()