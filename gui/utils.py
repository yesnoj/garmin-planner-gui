#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility per la GUI.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
import re
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Tuple


def is_valid_date(date_str: str) -> bool:
    """
    Verifica che una stringa sia una data valida nel formato YYYY-MM-DD.
    
    Args:
        date_str: Stringa da verificare
        
    Returns:
        True se la stringa è una data valida, False altrimenti
    """
    if not date_str:
        return True
    
    # Verifica il formato
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    
    try:
        # Converte in data
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def create_tooltip(widget, text: str) -> None:
    """
    Crea un tooltip per un widget.
    
    Args:
        widget: Widget per cui creare il tooltip
        text: Testo del tooltip
    """
    tooltip = TooltipWindow(widget)
    tooltip.set_text(text)



def convert_date_for_garmin(date_str: str) -> str:
    """
    Converte una data dal formato GG/MM/AAAA al formato YYYY-MM-DD richiesto da Garmin.
    Se la data è già nel formato YYYY-MM-DD, la restituisce invariata.
    
    Args:
        date_str: Data nel formato GG/MM/AAAA o YYYY-MM-DD
        
    Returns:
        Data nel formato YYYY-MM-DD
    """
    if not date_str:
        return ""
        
    # Se è già nel formato YYYY-MM-DD, restituiscila invariata
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
        
    # Se è nel formato GG/MM/AAAA, convertila
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
        try:
            day, month, year = date_str.split('/')
            # Assicuriamoci che giorno e mese siano di due cifre
            day = day.zfill(2)
            month = month.zfill(2)
            return f"{year}-{month}-{day}"
        except:
            return date_str
            
    # Se il formato non è riconosciuto, restituisci la stringa originale
    return date_str


def is_valid_display_date(date_str: str) -> bool:
    """
    Verifica che una stringa sia una data valida nel formato GG/MM/AAAA o YYYY-MM-DD.
    
    Args:
        date_str: Stringa da verificare
        
    Returns:
        True se la stringa è una data valida, False altrimenti
    """
    if not date_str:
        return True
    
    # Verifica il formato GG/MM/AAAA
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
        try:
            day, month, year = date_str.split('/')
            day = int(day)
            month = int(month)
            year = int(year)
            
            # Verifica che i valori siano validi
            if month < 1 or month > 12 or day < 1:
                return False
                
            # Verifica il numero di giorni nel mese
            import calendar
            max_days = calendar.monthrange(year, month)[1]
            return day <= max_days
        except (ValueError, TypeError):
            return False
    
    # Verifica il formato YYYY-MM-DD
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        try:
            # Converte in data
            from datetime import datetime
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    # Formato non riconosciuto
    return False


def create_scrollable_frame(parent) -> Tuple[ttk.Frame, ttk.Frame]:
    """
    Crea un frame con scrollbar.
    
    Args:
        parent: Widget genitore
        
    Returns:
        Tuple con il frame esterno e il frame interno
    """
    # Frame esterno
    outer_frame = ttk.Frame(parent)
    
    # Canvas
    canvas = tk.Canvas(outer_frame)
    scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
    
    # Frame interno
    inner_frame = ttk.Frame(canvas)
    inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    
    # Crea la finestra del canvas
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Layout
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Aggiungi anche lo scroll con la rotella del mouse
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
    
    return outer_frame, inner_frame


def show_error(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """
    Mostra un messaggio di errore.
    
    Args:
        title: Titolo del messaggio
        message: Testo del messaggio
        parent: Widget genitore del dialogo
    """
    messagebox.showerror(title, message, parent=parent)


def show_warning(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """
    Mostra un messaggio di avviso.
    
    Args:
        title: Titolo del messaggio
        message: Testo del messaggio
        parent: Widget genitore del dialogo
    """
    messagebox.showwarning(title, message, parent=parent)


def show_info(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """
    Mostra un messaggio informativo.
    
    Args:
        title: Titolo del messaggio
        message: Testo del messaggio
        parent: Widget genitore del dialogo
    """
    messagebox.showinfo(title, message, parent=parent)


def ask_yes_no(title: str, message: str, parent: Optional[tk.Widget] = None) -> bool:
    """
    Mostra una domanda Si/No.
    
    Args:
        title: Titolo del messaggio
        message: Testo del messaggio
        parent: Widget genitore del dialogo
        
    Returns:
        True se l'utente ha risposto "Sì", False altrimenti
    """
    return messagebox.askyesno(title, message, parent=parent)


def validate_pace(pace: str) -> bool:
    """
    Verifica che un passo sia nel formato mm:ss.
    
    Args:
        pace: Passo da verificare
        
    Returns:
        True se il passo è valido, False altrimenti
    """
    if not pace:
        return False
    
    # Verifica il formato
    if not re.match(r'^\d+:\d{2}$', pace):
        return False
    
    # Verifica i valori
    try:
        minutes, seconds = pace.split(':')
        minutes = int(minutes)
        seconds = int(seconds)
        
        if seconds >= 60:
            return False
        
        return True
    except ValueError:
        return False


def validate_hr(hr: str) -> bool:
    """
    Verifica che una frequenza cardiaca sia un numero intero.
    
    Args:
        hr: Frequenza cardiaca da verificare
        
    Returns:
        True se la frequenza cardiaca è valida, False altrimenti
    """
    if not hr:
        return False
    
    try:
        hr_val = int(hr)
        return hr_val > 0
    except ValueError:
        return False


def validate_power(power: str) -> bool:
    """
    Verifica che una potenza sia un numero intero.
    
    Args:
        power: Potenza da verificare
        
    Returns:
        True se la potenza è valida, False altrimenti
    """
    if not power:
        return False
    
    try:
        power_val = int(power)
        return power_val >= 0
    except ValueError:
        return False


def pace_to_seconds(pace: str) -> int:
    """
    Converte un passo nel formato mm:ss in secondi.
    
    Args:
        pace: Passo da convertire
        
    Returns:
        Secondi totali
    """
    try:
        minutes, seconds = pace.split(':')
        return int(minutes) * 60 + int(seconds)
    except (ValueError, IndexError):
        return 0


def seconds_to_pace(seconds: int) -> str:
    """
    Converte secondi in un passo nel formato mm:ss.
    
    Args:
        seconds: Secondi da convertire
        
    Returns:
        Passo nel formato mm:ss
    """
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"


def date_to_weekday(date_str: str) -> int:
    """
    Converte una data in giorno della settimana (0=lunedì, 6=domenica).
    
    Args:
        date_str: Data nel formato YYYY-MM-DD
        
    Returns:
        Giorno della settimana (0-6)
    """
    try:
        # Converte in data
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Restituisce il giorno della settimana (0=lunedì, 6=domenica)
        # datetime.weekday() restituisce 0 per lunedì, 6 per domenica
        return date_obj.weekday()
    except ValueError:
        # In caso di errore restituisce 0 (lunedì)
        return 0

def date_to_weekday(date_str: str) -> int:
    """
    Converte una data in giorno della settimana (0=lunedì, 6=domenica).
    
    Args:
        date_str: Data nel formato YYYY-MM-DD
        
    Returns:
        Giorno della settimana (0-6)
    """
    try:
        # Converte in data
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Restituisce il giorno della settimana (0=lunedì, 6=domenica)
        # datetime.weekday() restituisce 0 per lunedì, 6 per domenica
        return date_obj.weekday()
    except ValueError:
        # In caso di errore restituisce 0 (lunedì)
        return 0


def parse_pace_range(pace_range: str) -> Tuple[str, str]:
    """
    Analizza un intervallo di passo nel formato 'min:sec-min:sec' o 'min:sec'.
    
    Args:
        pace_range: Intervallo di passo da analizzare
        
    Returns:
        Tuple con passo minimo e massimo nel formato mm:ss
    """
    if not pace_range:
        return ('0:00', '0:00')
    
    # Se è un intervallo diviso da trattino
    if '-' in pace_range:
        try:
            min_pace, max_pace = pace_range.split('-')
            min_pace = min_pace.strip()
            max_pace = max_pace.strip()
            
            # Verifica che siano nel formato corretto
            if not validate_pace(min_pace):
                min_pace = '0:00'
            if not validate_pace(max_pace):
                max_pace = '0:00'
                
            return (min_pace, max_pace)
        except Exception:
            return ('0:00', '0:00')
    else:
        # Se è un singolo valore
        pace = pace_range.strip()
        
        # Verifica che sia nel formato corretto
        if not validate_pace(pace):
            pace = '0:00'
            
        return (pace, pace)


def parse_pace_range(pace_range: str) -> Tuple[str, str]:
    """
    Analizza un intervallo di passo nel formato 'min:sec-min:sec' o 'min:sec'.
    
    Args:
        pace_range: Intervallo di passo da analizzare
        
    Returns:
        Tuple con passo minimo e massimo nel formato mm:ss
    """
    if not pace_range:
        return ('0:00', '0:00')
    
    # Se è un intervallo diviso da trattino
    if '-' in pace_range:
        try:
            min_pace, max_pace = pace_range.split('-')
            min_pace = min_pace.strip()
            max_pace = max_pace.strip()
            
            # Verifica che siano nel formato corretto
            if not validate_pace(min_pace):
                min_pace = '0:00'
            if not validate_pace(max_pace):
                max_pace = '0:00'
                
            return (min_pace, max_pace)
        except Exception:
            return ('0:00', '0:00')
    else:
        # Se è un singolo valore
        pace = pace_range.strip()
        
        # Verifica che sia nel formato corretto
        if not validate_pace(pace):
            pace = '0:00'
            
        return (pace, pace)

def center_window(window, width=None, height=None) -> None:
    """
    Centra una finestra Tkinter sullo schermo.
    
    Args:
        window: Finestra da centrare
        width: Larghezza della finestra (opzionale)
        height: Altezza della finestra (opzionale)
    """
    # Aggiorna la UI per ottenere le dimensioni corrette
    window.update_idletasks()
    
    # Ottieni le dimensioni dello schermo
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Usa le dimensioni fornite o quelle attuali della finestra
    win_width = width or window.winfo_width()
    win_height = height or window.winfo_height()
    
    # Calcola la posizione centrale
    x = (screen_width - win_width) // 2
    y = (screen_height - win_height) // 2
    
    # Configura la geometry
    window.geometry(f"{win_width}x{win_height}+{x}+{y}")


def parse_power_range(power_range: str) -> Tuple[int, int]:
    """
    Analizza un intervallo di potenza nel formato 'N-N', '<N', 'N+' o 'N'.
    
    Args:
        power_range: Intervallo di potenza da analizzare
        
    Returns:
        Tuple con potenza minima e massima
    """
    if not power_range:
        return (0, 0)
    
    power_range = power_range.strip()
    
    # Caso 1: intervallo (es. "200-250")
    if '-' in power_range:
        try:
            min_power, max_power = power_range.split('-')
            min_power = int(min_power.strip())
            max_power = int(max_power.strip())
            return (min_power, max_power)
        except (ValueError, IndexError):
            return (0, 0)
    
    # Caso 2: minore di (es. "<125")
    elif power_range.startswith('<'):
        try:
            max_power = int(power_range[1:].strip())
            return (0, max_power)
        except ValueError:
            return (0, 0)
    
    # Caso 3: maggiore di (es. "375+")
    elif power_range.endswith('+'):
        try:
            min_power = int(power_range[:-1].strip())
            return (min_power, 9999)  # Valore alto per "infinito"
        except ValueError:
            return (0, 0)
    
    # Caso 4: valore singolo (es. "250")
    else:
        try:
            power = int(power_range.strip())
            return (power, power)
        except ValueError:
            return (0, 0)

class TooltipWindow:
    """Classe per i tooltip."""
    
    def __init__(self, widget):
        """
        Inizializza un tooltip.
        
        Args:
            widget: Widget a cui associare il tooltip
        """
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.text = ""
        
        # Associa eventi
        widget.bind("<Enter>", self.on_enter)
        widget.bind("<Leave>", self.on_leave)
        widget.bind("<ButtonPress>", self.on_leave)
    
    def set_text(self, text: str) -> None:
        """
        Imposta il testo del tooltip.
        
        Args:
            text: Testo del tooltip
        """
        self.text = text
    
    def on_enter(self, event=None) -> None:
        """
        Gestisce l'evento di entrata nel widget.
        
        Args:
            event: Evento Tkinter
        """
        if self.tipwindow or not self.text:
            return
        
        # Posizione del tooltip
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        
        # Crea il tooltip
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        
        # Crea il contenuto
        label = tk.Label(tw, text=self.text, justify="left",
                      background="#ffffe0", relief="solid", borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
    
    def on_leave(self, event=None) -> None:
        """
        Gestisce l'evento di uscita dal widget.
        
        Args:
            event: Evento Tkinter
        """
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


