#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dialog per la selezione di una data.
"""

import logging
import tkinter as tk
from tkinter import ttk
import calendar
from datetime import datetime, timedelta
from typing import Optional, Callable

from gui.utils import is_valid_date


class DatePickerDialog(tk.Toplevel):
    """Dialog per la selezione di una data."""
    
    def __init__(self, parent, title: str = "Seleziona data", 
               initial_date: Optional[str] = None,
               callback: Optional[Callable[[str], None]] = None):
        """
        Inizializza il dialog.
        
        Args:
            parent: Widget genitore
            title: Titolo del dialog
            initial_date: Data iniziale nel formato YYYY-MM-DD
            callback: Funzione da chiamare con la data selezionata
        """
        super().__init__(parent)
        self.parent = parent
        self.callback = callback
        
        # Data iniziale
        if initial_date and is_valid_date(initial_date):
            try:
                parts = initial_date.split('-')
                self.current_year = int(parts[0])
                self.current_month = int(parts[1])
                self.current_day = int(parts[2])
            except (ValueError, IndexError):
                self.set_today()
        else:
            self.set_today()
        
        self.selected_date = None
        
        # Configura il dialog
        self.title(title)
        self.geometry("300x350")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        
        # Crea i widget
        self.create_widgets()
        
        # Centra il dialog
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Associa evento di chiusura
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
    
    def set_today(self):
        """Imposta la data corrente."""
        today = datetime.now()
        self.current_year = today.year
        self.current_month = today.month
        self.current_day = today.day
    
    def create_widgets(self):
        """Crea i widget del dialog."""
        # Frame principale con padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Intestazione del calendario
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pulsante mese precedente
        prev_button = ttk.Button(header_frame, text="<", width=3, command=self.previous_month)
        prev_button.pack(side=tk.LEFT)
        
        # Etichetta mese/anno
        self.month_label = ttk.Label(header_frame, text="", font=("Arial", 12, "bold"))
        self.month_label.pack(side=tk.LEFT, expand=True)
        
        # Pulsante mese successivo
        next_button = ttk.Button(header_frame, text=">", width=3, command=self.next_month)
        next_button.pack(side=tk.RIGHT)
        
        # Griglia per i giorni della settimana
        days_frame = ttk.Frame(main_frame)
        days_frame.pack(fill=tk.X)
        
        # Nomi dei giorni della settimana (inizia da lunedì)
        days = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        
        for i, day in enumerate(days):
            ttk.Label(days_frame, text=day, width=4, anchor=tk.CENTER).grid(row=0, column=i)
        
        # Griglia per i giorni del mese
        self.calendar_frame = ttk.Frame(main_frame)
        self.calendar_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pulsanti per i giorni
        self.day_buttons = []
        
        for row in range(6):
            for col in range(7):
                day_button = ttk.Button(self.calendar_frame, text="", width=4,
                                      command=lambda r=row, c=col: self.on_day_click(r, c))
                day_button.grid(row=row, column=col, padx=1, pady=1)
                self.day_buttons.append(day_button)
        
        # Frame per i pulsanti "Oggi" e OK/Annulla
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Pulsante "Oggi"
        today_button = ttk.Button(buttons_frame, text="Oggi", command=self.set_to_today)
        today_button.pack(side=tk.LEFT)
        
        # Pulsanti OK/Annulla
        ttk.Button(buttons_frame, text="OK", command=self.on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="Annulla", command=self.on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Aggiorna il calendario
        self.update_calendar()
    
    def update_calendar(self):
        """Aggiorna la visualizzazione del calendario."""
        # Aggiorna l'etichetta del mese
        month_name = calendar.month_name[self.current_month]
        self.month_label.config(text=f"{month_name} {self.current_year}")
        
        # Ottieni il primo giorno del mese e il numero di giorni
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        
        # Resetta tutti i pulsanti
        for button in self.day_buttons:
            button.config(text="", state="disabled")
        
        # Popola i pulsanti con i giorni del mese
        for i, week in enumerate(cal):
            for j, day in enumerate(week):
                if day != 0:
                    button_index = i * 7 + j
                    if button_index < len(self.day_buttons):
                        # Abilita il pulsante
                        self.day_buttons[button_index].config(text=str(day), state="normal")
                        
                        # Evidenzia il giorno selezionato
                        if day == self.current_day and self.selected_date is None:
                            self.day_buttons[button_index].config(style="Accent.TButton")
                        elif (self.selected_date and 
                              self.selected_date.year == self.current_year and 
                              self.selected_date.month == self.current_month and 
                              self.selected_date.day == day):
                            self.day_buttons[button_index].config(style="Accent.TButton")
                        else:
                            self.day_buttons[button_index].config(style="TButton")
    
    def previous_month(self):
        """Passa al mese precedente."""
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        
        self.update_calendar()
    
    def next_month(self):
        """Passa al mese successivo."""
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        
        self.update_calendar()
    
    def on_day_click(self, row, col):
        """
        Gestisce il click su un giorno.
        
        Args:
            row: Riga del pulsante nella griglia
            col: Colonna del pulsante nella griglia
        """
        # Calcola l'indice del pulsante
        button_index = row * 7 + col
        
        # Ottieni il giorno
        day_text = self.day_buttons[button_index].cget("text")
        
        if day_text:
            # Crea la data selezionata
            self.selected_date = datetime(self.current_year, self.current_month, int(day_text))
            
            # Aggiorna il calendario per evidenziare il giorno selezionato
            self.update_calendar()
    
    def set_to_today(self):
        """Imposta la data odierna."""
        self.set_today()
        self.selected_date = datetime(self.current_year, self.current_month, self.current_day)
        self.update_calendar()
    
    def on_ok(self):
        """Gestisce il click sul pulsante OK."""
        # Se non è stata selezionata una data, usa quella corrente
        if not self.selected_date:
            self.selected_date = datetime(self.current_year, self.current_month, self.current_day)
        
        # Formatta la data nel formato YYYY-MM-DD
        date_str = self.selected_date.strftime("%Y-%m-%d")
        
        # Chiama il callback
        if self.callback:
            self.callback(date_str)
        
        # Chiudi il dialog
        self.destroy()
    
    def on_cancel(self):
        """Gestisce il click sul pulsante Annulla."""
        # Chiama il callback con None
        if self.callback:
            self.callback(None)
        
        # Chiudi il dialog
        self.destroy()


if __name__ == "__main__":
    # Test del dialog
    root = tk.Tk()
    root.withdraw()
    
    def on_date_selected(date):
        """Callback per la selezione della data."""
        if date:
            print(f"Data selezionata: {date}")
        else:
            print("Selezione annullata")
    
    # Crea un dialog con la data corrente
    dialog = DatePickerDialog(root, callback=on_date_selected)
    
    # Avvia il loop
    root.mainloop()