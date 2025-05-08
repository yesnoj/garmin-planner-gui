#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funzioni di utilità per l'interfaccia grafica.
"""

import os
import re
import json
import yaml
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
from typing import Dict, Any, List, Tuple, Optional, Union


def center_window(window: tk.Tk) -> None:
    """
    Centra una finestra sullo schermo.
    
    Args:
        window: Finestra da centrare
    """
    window.update_idletasks()
    width = window.winfo_width()
    height = window.winfo_height()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def format_workout_name(week: int, session: int, description: str) -> str:
    """
    Formatta il nome dell'allenamento secondo lo standard 'W##S## Descrizione'.
    
    Args:
        week: Numero della settimana
        session: Numero della sessione
        description: Descrizione dell'allenamento
        
    Returns:
        Nome formattato dell'allenamento
    """
    return f"W{week:02d}S{session:02d} {description}"


def parse_workout_name(name: str) -> Tuple[Optional[int], Optional[int], str]:
    """
    Analizza un nome di allenamento per estrarre settimana, sessione e descrizione.
    
    Args:
        name: Nome dell'allenamento
        
    Returns:
        Tuple con (settimana, sessione, descrizione)
    """
    pattern = r'^W(\d{2})S(\d{2})\s+(.+)$'
    match = re.match(pattern, name)
    
    if match:
        week = int(match.group(1))
        session = int(match.group(2))
        description = match.group(3)
        return week, session, description
    
    return None, None, name


def show_error(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """
    Mostra un messaggio di errore.
    
    Args:
        title: Titolo della finestra
        message: Messaggio di errore
        parent: Widget genitore (opzionale)
    """
    messagebox.showerror(title, message, parent=parent)


def show_warning(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """
    Mostra un messaggio di avviso.
    
    Args:
        title: Titolo della finestra
        message: Messaggio di avviso
        parent: Widget genitore (opzionale)
    """
    messagebox.showwarning(title, message, parent=parent)


def show_info(title: str, message: str, parent: Optional[tk.Widget] = None) -> None:
    """
    Mostra un messaggio informativo.
    
    Args:
        title: Titolo della finestra
        message: Messaggio informativo
        parent: Widget genitore (opzionale)
    """
    messagebox.showinfo(title, message, parent=parent)


def ask_yes_no(title: str, message: str, parent: Optional[tk.Widget] = None) -> bool:
    """
    Chiede una conferma sì/no.
    
    Args:
        title: Titolo della finestra
        message: Messaggio da mostrare
        parent: Widget genitore (opzionale)
        
    Returns:
        True se l'utente conferma, False altrimenti
    """
    return messagebox.askyesno(title, message, parent=parent)


def create_tooltip(widget: tk.Widget, text: str) -> None:
    """
    Crea un tooltip per un widget.
    
    Args:
        widget: Widget per cui creare il tooltip
        text: Testo del tooltip
    """
    def enter(event):
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25
        
        # Create tooltip window
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(tooltip, text=text, justify=tk.LEFT,
                       background="#FFFFDD", relief=tk.SOLID, borderwidth=1,
                       padding=(5, 2))
        label.pack(ipadx=1)
        
        widget._tooltip = tooltip
    
    def leave(event):
        if hasattr(widget, "_tooltip"):
            widget._tooltip.destroy()
            del widget._tooltip
    
    widget.bind("<Enter>", enter)
    widget.bind("<Leave>", leave)


def create_scrollable_frame(parent: tk.Widget) -> Tuple[ttk.Frame, ttk.Frame]:
    """
    Crea un frame con scrollbar.
    
    Args:
        parent: Widget genitore
        
    Returns:
        Tupla con (frame esterno, frame interno scrollabile)
    """
    # Create a frame to hold the canvas and scrollbar
    outer_frame = ttk.Frame(parent)
    
    # Create a canvas that will hold the scrollable frame
    canvas = tk.Canvas(outer_frame)
    scrollbar = ttk.Scrollbar(outer_frame, orient=tk.VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Pack the scrollbar and canvas
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Create a frame inside the canvas which will be scrolled
    inner_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor=tk.NW)
    
    # Configure the canvas to resize with the frame
    def configure_scroll_region(event):
        canvas.configure(scrollregion=canvas.bbox(tk.ALL))
    
    inner_frame.bind("<Configure>", configure_scroll_region)
    
    # Bind mousewheel events for scrolling
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    return outer_frame, inner_frame


def save_config(config: Dict[str, Any], filename: str = "config.yaml") -> bool:
    """
    Salva la configurazione in un file YAML.
    
    Args:
        config: Dizionario con la configurazione
        filename: Nome del file (default: config.yaml)
        
    Returns:
        True se il salvataggio è riuscito, False altrimenti
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        logging.error(f"Error saving configuration: {e}")
        return False


def load_config(filename: str = "config.yaml") -> Dict[str, Any]:
    """
    Carica la configurazione da un file YAML.
    
    Args:
        filename: Nome del file (default: config.yaml)
        
    Returns:
        Dizionario con la configurazione
    """
    config = {}
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
    
    return config or {}


def validate_pace(pace: str) -> bool:
    """
    Valida un valore di passo (formato: MM:SS).
    
    Args:
        pace: Valore di passo da validare
        
    Returns:
        True se il valore è valido, False altrimenti
    """
    pattern = r'^(\d{1,2}):([0-5]\d)$'
    return bool(re.match(pattern, pace))


def validate_power(power: str) -> bool:
    """
    Valida un valore di potenza (formato: intero o intervallo N-N).
    
    Args:
        power: Valore di potenza da validare
        
    Returns:
        True se il valore è valido, False altrimenti
    """
    # Singolo valore intero
    if re.match(r'^\d+$', power):
        return True
    
    # Intervallo N-N
    if re.match(r'^\d+-\d+$', power):
        parts = power.split('-')
        return int(parts[0]) < int(parts[1])
    
    # Formato speciale <N
    if re.match(r'^<\d+$', power):
        return True
    
    # Formato speciale N+
    if re.match(r'^\d+\+$', power):
        return True
    
    return False


def validate_hr(hr: str) -> bool:
    """
    Valida un valore di frequenza cardiaca (formato: intero o intervallo N-N o N% max_hr).
    
    Args:
        hr: Valore di frequenza cardiaca da validare
        
    Returns:
        True se il valore è valido, False altrimenti
    """
    # Singolo valore intero
    if re.match(r'^\d+$', hr):
        return True
    
    # Intervallo N-N
    if re.match(r'^\d+-\d+$', hr):
        parts = hr.split('-')
        return int(parts[0]) < int(parts[1])
    
    # Formato N% max_hr
    if re.match(r'^\d+%\s*max_hr$', hr):
        perc = int(hr.split('%')[0])
        return 0 < perc <= 100
    
    # Formato N-N% max_hr
    if re.match(r'^\d+-\d+%\s*max_hr$', hr):
        parts = hr.split('-')
        perc1 = int(parts[0])
        perc2 = int(parts[1].split('%')[0])
        return 0 < perc1 < perc2 <= 100
    
    return False


def parse_pace_range(pace_range: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Analizza un intervallo di passo (formato: MM:SS-MM:SS o MM:SS).
    
    Args:
        pace_range: Intervallo di passo da analizzare
        
    Returns:
        Tupla con (passo_lento, passo_veloce)
    """
    if '-' in pace_range:
        parts = pace_range.split('-')
        if len(parts) == 2 and validate_pace(parts[0]) and validate_pace(parts[1]):
            return parts[0], parts[1]
    elif validate_pace(pace_range):
        return pace_range, pace_range
    
    return None, None


def parse_power_range(power_range: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Analizza un intervallo di potenza (formato: N-N o N).
    
    Args:
        power_range: Intervallo di potenza da analizzare
        
    Returns:
        Tupla con (potenza_min, potenza_max)
    """
    if '-' in power_range:
        parts = power_range.split('-')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return int(parts[0]), int(parts[1])
    elif power_range.isdigit():
        power = int(power_range)
        return power, power
    elif power_range.startswith('<') and power_range[1:].isdigit():
        power = int(power_range[1:])
        return 0, power
    elif power_range.endswith('+') and power_range[:-1].isdigit():
        power = int(power_range[:-1])
        return power, 999
    
    return None, None


def get_weeks_from_workouts(workouts: List[Tuple[str, List[Dict[str, Any]]]]) -> List[int]:
    """
    Estrae i numeri di settimana dai nomi degli allenamenti.
    
    Args:
        workouts: Lista di allenamenti (nome, steps)
        
    Returns:
        Lista dei numeri di settimana trovati
    """
    weeks = set()
    for name, _ in workouts:
        week, _, _ = parse_workout_name(name)
        if week is not None:
            weeks.add(week)
    
    return sorted(list(weeks))


def get_sessions_per_week(workouts: List[Tuple[str, List[Dict[str, Any]]]]) -> Dict[int, int]:
    """
    Conta il numero di sessioni per ogni settimana.
    
    Args:
        workouts: Lista di allenamenti (nome, steps)
        
    Returns:
        Dizionario con {settimana: numero_sessioni}
    """
    sessions = {}
    for name, _ in workouts:
        week, session, _ = parse_workout_name(name)
        if week is not None:
            if week not in sessions:
                sessions[week] = 0
            sessions[week] = max(sessions[week], session)
    
    return sessions


def extract_sport_from_steps(steps: List[Dict[str, Any]]) -> str:
    """
    Estrae il tipo di sport dagli step dell'allenamento.
    
    Args:
        steps: Lista degli step dell'allenamento
        
    Returns:
        Tipo di sport (running, cycling, swimming, other)
    """
    for step in steps:
        if isinstance(step, dict) and 'sport_type' in step:
            return step['sport_type']
    
    return "running"  # Default


def extract_date_from_steps(steps: List[Dict[str, Any]]) -> Optional[str]:
    """
    Estrae la data dagli step dell'allenamento.
    
    Args:
        steps: Lista degli step dell'allenamento
        
    Returns:
        Data nel formato YYYY-MM-DD o None
    """
    for step in steps:
        if isinstance(step, dict) and 'date' in step:
            return step['date']
    
    return None


def is_valid_date(date: str) -> bool:
    """
    Verifica se una stringa rappresenta una data valida nel formato YYYY-MM-DD.
    
    Args:
        date: Stringa da verificare
        
    Returns:
        True se la data è valida, False altrimenti
    """
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def date_to_weekday(date: str) -> int:
    """
    Converte una data nel formato YYYY-MM-DD nel giorno della settimana (0-6, dove 0 è lunedì).
    
    Args:
        date: Data nel formato YYYY-MM-DD
        
    Returns:
        Giorno della settimana (0-6)
    """
    try:
        dt = datetime.datetime.strptime(date, '%Y-%m-%d')
        return dt.weekday()
    except ValueError:
        return 0


def seconds_to_pace(seconds: int) -> str:
    """
    Converte un numero di secondi in un passo (formato: MM:SS).
    
    Args:
        seconds: Numero di secondi
        
    Returns:
        Passo nel formato MM:SS
    """
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def pace_to_seconds(pace: str) -> int:
    """
    Converte un passo (formato: MM:SS) in secondi.
    
    Args:
        pace: Passo nel formato MM:SS
        
    Returns:
        Numero di secondi
    """
    if not validate_pace(pace):
        return 0
    
    parts = pace.split(':')
    return int(parts[0]) * 60 + int(parts[1])


def create_new_window(title: str, parent: Optional[tk.Widget] = None, width: int = 500, height: int = 400) -> tk.Toplevel:
    """
    Crea una nuova finestra.
    
    Args:
        title: Titolo della finestra
        parent: Widget genitore (opzionale)
        width: Larghezza della finestra
        height: Altezza della finestra
        
    Returns:
        Nuova finestra
    """
    window = tk.Toplevel(parent)
    window.title(title)
    window.geometry(f"{width}x{height}")
    window.transient(parent)
    window.grab_set()
    
    # Centra la finestra
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")
    
    return window


def lighten_color(hex_color: str, factor: float = 0.3) -> str:
    """
    Schiarisce un colore esadecimale.
    
    Args:
        hex_color: Colore esadecimale (#RRGGBB)
        factor: Fattore di schiarimento (0-1)
        
    Returns:
        Colore schiarito
    """
    # Rimuovi il carattere # se presente
    hex_color = hex_color.lstrip('#')
    
    # Converti in RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Schiarisci
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    
    # Converti in esadecimale
    return f"#{r:02x}{g:02x}{b:02x}"


def darken_color(hex_color: str, factor: float = 0.3) -> str:
    """
    Scurisce un colore esadecimale.
    
    Args:
        hex_color: Colore esadecimale (#RRGGBB)
        factor: Fattore di scurimento (0-1)
        
    Returns:
        Colore scurito
    """
    # Rimuovi il carattere # se presente
    hex_color = hex_color.lstrip('#')
    
    # Converti in RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Scurisci
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    
    # Converti in esadecimale
    return f"#{r:02x}{g:02x}{b:02x}"
