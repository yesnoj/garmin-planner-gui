#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestione degli stili e temi per l'interfaccia grafica.
"""

import tkinter as tk
from tkinter import ttk
import logging
import platform
from typing import Dict, Any

# Colori per il tema chiaro
LIGHT_COLORS = {
    "bg_light": "#F5F5F5",
    "bg_medium": "#E0E0E0",
    "bg_dark": "#CCCCCC",
    "fg_light": "#505050",
    "fg_dark": "#303030",
    "accent": "#1976D2",
    "accent_light": "#64B5F6",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
    "text_light": "#FFFFFF",
    "text_dark": "#000000",
    "border": "#BDBDBD",
    "selected": "#BBDEFB",
    "hover": "#E3F2FD",
}

# Colori per il tema scuro
DARK_COLORS = {
    "bg_light": "#424242",
    "bg_medium": "#303030",
    "bg_dark": "#212121",
    "fg_light": "#BDBDBD",
    "fg_dark": "#F5F5F5",
    "accent": "#2196F3",
    "accent_light": "#90CAF9",
    "success": "#66BB6A",
    "warning": "#FFCA28",
    "error": "#EF5350",
    "text_light": "#FFFFFF",
    "text_dark": "#E0E0E0",
    "border": "#616161",
    "selected": "#1565C0",
    "hover": "#1E88E5",
}

# Icone per i tipi di sport
SPORT_ICONS = {
    "running": "🏃",
    "cycling": "🚴",
    "swimming": "🏊",
    "other": "🏋️",
    "repeat": "🔄",
    "warmup": "🌡️",
    "cooldown": "❄️",
    "interval": "⏱️",
    "recovery": "💤",
    "rest": "🛌",
}

# Icone per i tipi di step
STEP_ICONS = {
    "warmup": "🔥",
    "cooldown": "❄️",
    "interval": "⏱️",
    "recovery": "💤",
    "rest": "🛌",
    "repeat": "🔄",
    "other": "📝",
}

def get_system_theme() -> str:
    """
    Rileva il tema del sistema operativo.
    
    Returns:
        "dark" se il tema del sistema è scuro, "light" altrimenti
    """
    system = platform.system()
    
    try:
        if system == "Windows":
            # Su Windows si può usare il modulo winreg per leggere il registro
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            reg_keypath = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            reg_key = winreg.OpenKey(registry, reg_keypath)
            
            # AppsUseLightTheme = 0 significa tema scuro
            light_theme = winreg.QueryValueEx(reg_key, "AppsUseLightTheme")[0]
            return "light" if light_theme else "dark"
            
        elif system == "Darwin":  # macOS
            # Su macOS si può usare il comando defaults
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True
            )
            # Se il comando restituisce "Dark", il tema è scuro
            return "dark" if result.stdout.strip() == "Dark" else "light"
            
        else:  # Linux/Altri
            # Su Linux/GNOME si può usare gsettings
            # Questo è un approccio semplificato, è necessario verificare l'ambiente desktop
            import subprocess
            try:
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True,
                    text=True
                )
                return "dark" if "dark" in result.stdout.lower() else "light"
            except:
                # Se non è possibile determinare il tema, usa quello chiaro come fallback
                return "light"
                
    except Exception as e:
        logging.warning(f"Error detecting system theme: {e}")
        return "light"  # Default a tema chiaro

def setup_styles(root: tk.Tk, theme: str = "light") -> None:
    """
    Imposta gli stili per l'interfaccia.
    
    Args:
        root: Finestra principale
        theme: Tema da utilizzare (light, dark, system)
    """
    # Determina il tema effettivo
    if theme == "system":
        effective_theme = get_system_theme()
    else:
        effective_theme = theme
    
    # Seleziona la palette di colori
    colors = LIGHT_COLORS if effective_theme == "light" else DARK_COLORS
    
    # Imposta i colori di sfondo e testo di base
    root.configure(background=colors["bg_medium"])
    
    # Crea o ottieni lo style manager
    style = ttk.Style(root)
    
    # Configura il tema di base
    if effective_theme == "light":
        style.theme_use("clam")  # Clam è più personalizzabile
    else:
        style.theme_use("clam")  # Usa clam anche per il tema scuro
    
    # Configura gli stili di base
    style.configure(".",
                  background=colors["bg_medium"],
                  foreground=colors["fg_dark"],
                  troughcolor=colors["bg_dark"],
                  selectbackground=colors["selected"],
                  selectforeground=colors["text_light"],
                  fieldbackground=colors["bg_light"],
                  font=("Arial", 10),
                  borderwidth=1,
                  relief="flat")
    
    # Frame
    style.configure("TFrame", background=colors["bg_medium"])
    style.configure("Card.TFrame", background=colors["bg_light"], relief="raised", borderwidth=1)
    
    # LabelFrame
    style.configure("TLabelframe", background=colors["bg_medium"], bordercolor=colors["border"])
    style.configure("TLabelframe.Label", background=colors["bg_medium"], foreground=colors["fg_dark"])
    
    # Label
    style.configure("TLabel", background=colors["bg_medium"], foreground=colors["fg_dark"])
    style.configure("Title.TLabel", font=("Arial", 16, "bold"))
    style.configure("Subtitle.TLabel", font=("Arial", 12, "bold"))
    style.configure("Heading.TLabel", font=("Arial", 14, "bold"))
    style.configure("Small.TLabel", font=("Arial", 8))
    style.configure("Status.TLabel", background=colors["bg_dark"], foreground=colors["fg_light"], padding=(5, 2))
    
    # Button
    style.configure("TButton", 
                  background=colors["accent"],
                  foreground=colors["text_light"],
                  padding=(10, 5),
                  relief="raised")
    
    style.map("TButton",
            background=[("active", colors["accent_light"]), ("disabled", colors["bg_dark"])],
            foreground=[("disabled", colors["fg_light"])])
    
    # Pulsanti con colori specifici
    style.configure("Success.TButton", background=colors["success"])
    style.map("Success.TButton", background=[("active", colors["success"])])
    
    style.configure("Warning.TButton", background=colors["warning"])
    style.map("Warning.TButton", background=[("active", colors["warning"])])
    
    style.configure("Error.TButton", background=colors["error"])
    style.map("Error.TButton", background=[("active", colors["error"])])
    
    # Entry
    style.configure("TEntry", fieldbackground=colors["bg_light"], foreground=colors["fg_dark"])
    style.map("TEntry", 
            fieldbackground=[("disabled", colors["bg_dark"])],
            foreground=[("disabled", colors["fg_light"])])
    
    # Combobox
    style.configure("TCombobox", 
                  fieldbackground=colors["bg_light"],
                  background=colors["bg_medium"],
                  foreground=colors["fg_dark"],
                  arrowcolor=colors["fg_dark"])
    
    style.map("TCombobox",
            fieldbackground=[("readonly", colors["bg_light"]), ("disabled", colors["bg_dark"])],
            foreground=[("readonly", colors["fg_dark"]), ("disabled", colors["fg_light"])])
    
    # Notebook
    style.configure("TNotebook", background=colors["bg_medium"], tabmargins=[2, 5, 2, 0])
    style.configure("TNotebook.Tab", 
                  background=colors["bg_dark"],
                  foreground=colors["fg_dark"],
                  padding=(10, 5),
                  font=("Arial", 10, "bold"))
    
    style.map("TNotebook.Tab",
            background=[("selected", colors["accent"]), ("active", colors["accent_light"])],
            foreground=[("selected", colors["text_light"]), ("active", colors["fg_dark"])])
    
    # Scrollbar
    style.configure("TScrollbar", 
                  background=colors["bg_medium"],
                  troughcolor=colors["bg_dark"],
                  arrowcolor=colors["fg_dark"],
                  relief="flat")
    
    style.map("TScrollbar",
            background=[("active", colors["accent_light"]), ("disabled", colors["bg_dark"])])
    
    # Progressbar
    style.configure("TProgressbar", 
                  background=colors["accent"],
                  troughcolor=colors["bg_dark"])
    
    # Treeview (per liste e tabelle)
    style.configure("Treeview", 
                  background=colors["bg_light"],
                  foreground=colors["fg_dark"],
                  fieldbackground=colors["bg_light"],
                  borderwidth=0)
    
    style.configure("Treeview.Heading", 
                  background=colors["bg_dark"],
                  foreground=colors["fg_dark"],
                  font=("Arial", 10, "bold"),
                  relief="flat")
    
    style.map("Treeview",
            background=[("selected", colors["selected"])],
            foreground=[("selected", colors["text_light"])])
    
    # Checkbox e Radiobutton
    style.configure("TCheckbutton", background=colors["bg_medium"], foreground=colors["fg_dark"])
    style.configure("TRadiobutton", background=colors["bg_medium"], foreground=colors["fg_dark"])
    
    # Separator
    style.configure("TSeparator", background=colors["border"])
    
    # Stili specifici per il calendario
    style.configure("Today.TFrame", relief="solid", borderwidth=2, bordercolor=colors["accent"])
    style.configure("Today.TLabel", foreground=colors["accent"], font=("Arial", 10, "bold"))
    
    # Scale (slider)
    style.configure("TScale", 
                  background=colors["bg_medium"],
                  troughcolor=colors["bg_dark"])
    
    # Panedwindow
    style.configure("TPanedwindow", 
                  background=colors["bg_medium"],
                  sashrelief="flat",
                  sashwidth=4)

def get_icon_for_sport(sport_type: str) -> str:
    """
    Restituisce l'icona corrispondente al tipo di sport.
    
    Args:
        sport_type: Tipo di sport (running, cycling, swimming, ecc.)
    
    Returns:
        Emoji corrispondente al tipo di sport
    """
    return SPORT_ICONS.get(sport_type.lower(), SPORT_ICONS["other"])

def get_icon_for_step(step_type: str) -> str:
    """
    Restituisce l'icona corrispondente al tipo di step.
    
    Args:
        step_type: Tipo di step (warmup, cooldown, interval, ecc.)
    
    Returns:
        Emoji corrispondente al tipo di step
    """
    return STEP_ICONS.get(step_type.lower(), STEP_ICONS["other"])

def get_color_for_sport(sport_type: str, theme: str = "light") -> str:
    """
    Restituisce il colore corrispondente al tipo di sport.
    
    Args:
        sport_type: Tipo di sport (running, cycling, swimming, ecc.)
        theme: Tema utilizzato (light o dark)
    
    Returns:
        Codice colore hex corrispondente al tipo di sport
    """
    colors = {
        "running": "#FF5722" if theme == "light" else "#FF8A65",
        "cycling": "#2196F3" if theme == "light" else "#64B5F6",
        "swimming": "#4CAF50" if theme == "light" else "#81C784",
        "other": "#9E9E9E" if theme == "light" else "#BDBDBD",
    }
    
    return colors.get(sport_type.lower(), colors["other"])

def get_color_for_step(step_type: str, theme: str = "light") -> str:
    """
    Restituisce il colore corrispondente al tipo di step.
    
    Args:
        step_type: Tipo di step (warmup, cooldown, interval, ecc.)
        theme: Tema utilizzato (light o dark)
    
    Returns:
        Codice colore hex corrispondente al tipo di step
    """
    colors = {
        "warmup": "#FF9800" if theme == "light" else "#FFB74D",
        "cooldown": "#03A9F4" if theme == "light" else "#4FC3F7",
        "interval": "#E91E63" if theme == "light" else "#F06292",
        "recovery": "#8BC34A" if theme == "light" else "#AED581",
        "rest": "#9C27B0" if theme == "light" else "#BA68C8",
        "repeat": "#607D8B" if theme == "light" else "#90A4AE",
        "other": "#9E9E9E" if theme == "light" else "#BDBDBD",
    }
    
    return colors.get(step_type.lower(), colors["other"])
