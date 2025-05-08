#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog per la selezione di una data.
"""

import logging
import tkinter as tk
from tkinter import ttk
import datetime
from typing import Optional, Callable

try:
    from tkcalendar import Calendar
    TKCALENDAR_AVAILABLE = True
except ImportError:
    TKCALENDAR_AVAILABLE = False

from garmin_planner_gui.gui.utils import (
    is_valid_date, show_error
)


class DatePickerDialog(tk.Toplevel):
    """Dialog per la selezione di una data."""
    
    def __init__(self, parent, title: str = "Seleziona data", 
               initial_date: Optional[str] = None, 
               callback: Optional[Callable] = None):
        """
        Inizializza il dialog.
        
        Args:
            parent: Widget genitore
            title: Titolo della finestra
            initial_date: Data iniziale (formato YYYY-MM-DD)
            callback: Funzione da chiamare alla conferma (riceve la data selezionata)
        """
        super().__init__(parent)
        self.parent = parent
        self.callback = callback
        
        # Imposta la data iniziale
        if initial_date and is_valid_date(initial_date):
            self.initial_date = initial_date
        else:
            self.initial_date = datetime.date.today().strftime("%Y-%m-%d")
        
        # Variabili
        self.selected_date = None
        
        # Configura il dialog
        self.title(title)
        self.geometry("300x350")
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
        
        # Aggiungi i callback
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def create_widgets(self):
        """Crea i widget del dialog."""
        # Frame principale con padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Se tkcalendar è disponibile, usa il widget Calendar
        if TKCALENDAR_AVAILABLE:
            # Ottieni anno, mese e giorno dalla data iniziale
            try:
                year, month, day = map(int, self.initial_date.split('-'))
            except:
                today = datetime.date.today()
                year, month, day = today.year, today.month, today.day
            
            # Crea il calendario
            self.calendar = Calendar(main_frame, selectmode='day', 
                                  year=year, month=month, day=day, 
                                  date_pattern="yyyy-mm-dd")
            self.calendar.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # Formatta la data selezionata come YYYY-MM-DD
            self.selected_date = self.calendar.get_date()
            
        # Altrimenti usa un'interfaccia semplice
        else:
            # Frame per la selezione della data
            date_frame = ttk.Frame(main_frame)
            date_frame.pack(fill=tk.X, pady=(0, 20))
            
            # Anno
            ttk.Label(date_frame, text="Anno:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=5)
            
            current_year = datetime.date.today().year
            years = list(range(current_year - 5, current_year + 10))
            
            self.year_var = tk.StringVar(value=self.initial_date.split('-')[0] if self.initial_date else str(current_year))
            self.year_combo = ttk.Combobox(date_frame, textvariable=self.year_var, 
                                        values=years, width=10, state="readonly")
            self.year_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
            
            # Mese
            ttk.Label(date_frame, text="Mese:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=5)
            
            months = [
                "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
            ]
            
            month = int(self.initial_date.split('-')[1]) if self.initial_date else datetime.date.today().month
            
            self.month_var = tk.StringVar(value=months[month - 1])
            self.month_combo = ttk.Combobox(date_frame, textvariable=self.month_var, 
                                         values=months, width=15, state="readonly")
            self.month_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
            
            # Giorno
            ttk.Label(date_frame, text="Giorno:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=5)
            
            days = list(range(1, 32))
            
            day = int(self.initial_date.split('-')[2]) if self.initial_date else datetime.date.today().day
            
            self.day_var = tk.StringVar(value=str(day))
            self.day_combo = ttk.Combobox(date_frame, textvariable=self.day_var, 
                                       values=days, width=10, state="readonly")
            self.day_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
            
            # Associa eventi per aggiornare i giorni disponibili
            self.year_combo.bind("<<ComboboxSelected>>", self.update_days)
            self.month_combo.bind("<<ComboboxSelected>>", self.update_days)
            
            # Formatta la data selezionata come YYYY-MM-DD
            self.selected_date = self.format_date()
        
        # Pulsanti
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="Annulla", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
    
    def update_days(self, event=None):
        """
        Aggiorna i giorni disponibili in base al mese e all'anno selezionati.
        
        Args:
            event: Evento Tkinter (opzionale)
        """
        # Solo se tkcalendar non è disponibile
        if TKCALENDAR_AVAILABLE:
            return
        
        # Ottieni anno e mese
        year = int(self.year_var.get())
        
        # Converti il nome del mese in numero
        months = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        month = months.index(self.month_var.get()) + 1
        
        # Ottieni il numero di giorni nel mese
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        # Aggiusta febbraio per gli anni bisestili
        if month == 2 and ((year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)):
            days_in_month[1] = 29
        
        # Aggiorna i valori disponibili
        days = list(range(1, days_in_month[month - 1] + 1))
        self.day_combo.config(values=days)
        
        # Verifica che il giorno sia valido
        try:
            day = int(self.day_var.get())
            if day > days_in_month[month - 1]:
                self.day_var.set(str(days_in_month[month - 1]))
        except ValueError:
            self.day_var.set("1")
    
    def format_date(self) -> str:
        """
        Formatta la data selezionata come YYYY-MM-DD.
        
        Returns:
            Data nel formato YYYY-MM-DD
        """
        # Solo se tkcalendar non è disponibile
        if TKCALENDAR_AVAILABLE:
            return self.calendar.get_date()
        
        # Ottieni anno, mese e giorno
        year = int(self.year_var.get())
        
        # Converti il nome del mese in numero
        months = [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
        ]
        month = months.index(self.month_var.get()) + 1
        
        day = int(self.day_var.get())
        
        # Formatta la data
        return f"{year:04d}-{month:02d}-{day:02d}"
    
    def validate(self) -> bool:
        """
        Valida la data selezionata.
        
        Returns:
            True se la data è valida, False altrimenti
        """
        # Ottieni la data selezionata
        if TKCALENDAR_AVAILABLE:
            date_str = self.calendar.get_date()
        else:
            date_str = self.format_date()
        
        # Verifica che sia una data valida
        if not is_valid_date(date_str):
            show_error("Errore", "Data non valida", parent=self)
            return False
        
        return True
    
    def on_ok(self):
        """Gestisce il click sul pulsante OK."""
        # Valida la data
        if not self.validate():
            return
        
        # Ottieni la data selezionata
        if TKCALENDAR_AVAILABLE:
            self.selected_date = self.calendar.get_date()
        else:
            self.selected_date = self.format_date()
        
        # Chiama il callback
        if self.callback:
            self.callback(self.selected_date)
        
        # Chiudi il dialog
        self.destroy()
    
    def on_cancel(self):
        """Gestisce il click sul pulsante Annulla."""
        # Reset della data selezionata
        self.selected_date = None
        
        # Chiama il callback con None
        if self.callback:
            self.callback(None)
        
        # Chiudi il dialog
        self.destroy()


if __name__ == "__main__":
    # Test del dialog
    root = tk.Tk()
    root.withdraw()
    
    # Crea il dialog
    def on_date_selected(date):
        if date:
            print(f"Data selezionata: {date}")
        else:
            print("Nessuna data selezionata")
    
    dialog = DatePickerDialog(root, callback=on_date_selected)
    
    # Avvia il loop
    root.mainloop()