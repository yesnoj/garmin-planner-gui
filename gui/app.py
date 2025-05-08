#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Finestra principale dell'applicazione GarminPlannerGUI.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any

from garmin_planner_gui.config import get_config
from garmin_planner_gui.auth import get_auth, GarminClient
from garmin_planner_gui.gui.styles import setup_styles
from garmin_planner_gui.gui.login_frame import LoginFrame
from garmin_planner_gui.gui.workout_editor import WorkoutEditorFrame
from garmin_planner_gui.gui.calendar_view import CalendarFrame
from garmin_planner_gui.gui.zones_manager import ZonesManagerFrame
from garmin_planner_gui.gui.import_export import ImportExportFrame
from garmin_planner_gui.gui.utils import center_window


class GarminPlannerApp:
    """Classe principale dell'applicazione GarminPlannerGUI."""
    
    def __init__(self, root: tk.Tk, config_path: str = 'config.yaml'):
        """
        Inizializza l'applicazione.
        
        Args:
            root: Finestra principale Tkinter
            config_path: Percorso del file di configurazione
        """
        self.root = root
        self.root.title("GarminPlannerGUI")
        self.root.geometry("1200x800")
        
        # Carica la configurazione
        self.config = get_config(config_path)
        
        # Ottieni il gestore dell'autenticazione
        self.auth = get_auth(oauth_folder=self.config.get('oauth_folder', '~/.garth'))
        
        # Imposta gli stili
        setup_styles(self.root, theme=self.config.get('ui.theme', 'light'))
        
        # Crea l'interfaccia
        self._create_ui()
        
        # Prova a riprendere la sessione precedente
        self.auth.register_auth_callback(self._on_auth_change)
        self.auth.resume()
        
        # Centra la finestra
        center_window(self.root)
        
        # Collega l'evento di chiusura
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_ui(self) -> None:
        """Crea l'interfaccia utente."""
        # Frame principale
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Barra di stato
        self.status_frame = ttk.Frame(self.root, relief=tk.SUNKEN)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="Pronto")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var, padding=(5, 2))
        self.status_label.pack(side=tk.LEFT)
        
        self.auth_status_var = tk.StringVar(value="Non connesso")
        self.auth_status_label = ttk.Label(self.status_frame, textvariable=self.auth_status_var, padding=(5, 2))
        self.auth_status_label.pack(side=tk.RIGHT)
        
        # Crea il notebook per le diverse sezioni
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame di login
        self.login_frame = LoginFrame(self.notebook, self.auth)
        self.notebook.add(self.login_frame, text="Login")
        
        # Frame per l'editor di allenamenti
        self.workout_editor = WorkoutEditorFrame(self.notebook, self)
        self.notebook.add(self.workout_editor, text="Editor Allenamenti")
        
        # Frame per il calendario
        self.calendar_frame = CalendarFrame(self.notebook, self)
        self.notebook.add(self.calendar_frame, text="Calendario")
        
        # Frame per la gestione delle zone
        self.zones_manager = ZonesManagerFrame(self.notebook, self)
        self.notebook.add(self.zones_manager, text="Zone")
        
        # Frame per importazione/esportazione
        self.import_export = ImportExportFrame(self.notebook, self)
        self.notebook.add(self.import_export, text="Importa/Esporta")
        
        # Aggiungi il menu
        self._create_menu()
        
        # Associa evento di cambio tab
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
    
    def _create_menu(self) -> None:
        """Crea il menu dell'applicazione."""
        self.menu = tk.Menu(self.root)
        self.root.config(menu=self.menu)
        
        # Menu File
        file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Importa YAML...", command=self._on_import_yaml)
        file_menu.add_command(label="Importa Excel...", command=self._on_import_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Esporta YAML...", command=self._on_export_yaml)
        file_menu.add_command(label="Esporta Excel...", command=self._on_export_excel)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self._on_close)
        
        # Menu Visualizza
        view_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Visualizza", menu=view_menu)
        
        # Sottomenu per i temi
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Tema", menu=theme_menu)
        
        self.theme_var = tk.StringVar(value=self.config.get('ui.theme', 'light'))
        theme_menu.add_radiobutton(label="Chiaro", variable=self.theme_var, value="light", command=self._on_theme_change)
        theme_menu.add_radiobutton(label="Scuro", variable=self.theme_var, value="dark", command=self._on_theme_change)
        theme_menu.add_radiobutton(label="Sistema", variable=self.theme_var, value="system", command=self._on_theme_change)
        
        # Menu Allenamenti
        workout_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Allenamenti", menu=workout_menu)
        workout_menu.add_command(label="Nuovo...", command=self._on_new_workout)
        workout_menu.add_command(label="Pianifica...", command=self._on_schedule_workout)
        workout_menu.add_command(label="Sincronizza con Garmin Connect", command=self._on_sync_workouts)
        
        # Menu Aiuto
        help_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Aiuto", menu=help_menu)
        help_menu.add_command(label="Manuale utente", command=self._on_help)
        help_menu.add_command(label="Informazioni su...", command=self._on_about)
    
    def _on_auth_change(self, is_authenticated: bool, client: Optional[GarminClient]) -> None:
        """
        Gestisce il cambio di stato dell'autenticazione.
        
        Args:
            is_authenticated: True se autenticato, False altrimenti
            client: Client Garmin o None
        """
        if is_authenticated and client:
            self.auth_status_var.set("Connesso a Garmin Connect")
            
            # Ottieni informazioni sull'utente
            try:
                profile = client.get_user_profile()
                if profile and 'fullName' in profile:
                    self.auth_status_var.set(f"Connesso come {profile['fullName']}")
                    
                    # Aggiorna il nome dell'atleta nella configurazione
                    if self.config.get('athlete_name', '') == '':
                        self.config.set('athlete_name', profile['fullName'])
                        self.config.save()
            except Exception as e:
                logging.error(f"Error getting user profile: {str(e)}")
            
            # Abilita funzionalità che richiedono l'autenticazione
            self._enable_auth_features()
            
            # Notifica i frame
            self.workout_editor.on_login(client)
            self.calendar_frame.on_login(client)
            self.import_export.on_login(client)
            
        else:
            self.auth_status_var.set("Non connesso")
            
            # Disabilita funzionalità che richiedono l'autenticazione
            self._disable_auth_features()
            
            # Notifica i frame
            self.workout_editor.on_logout()
            self.calendar_frame.on_logout()
            self.import_export.on_logout()
    
    def _enable_auth_features(self) -> None:
        """Abilita le funzionalità che richiedono l'autenticazione."""
        pass  # Le funzionalità vengono abilitate nei singoli frame
    
    def _disable_auth_features(self) -> None:
        """Disabilita le funzionalità che richiedono l'autenticazione."""
        pass  # Le funzionalità vengono disabilitate nei singoli frame
    
    def _on_tab_changed(self, event) -> None:
        """
        Gestisce il cambio di tab nel notebook.
        
        Args:
            event: Evento Tkinter
        """
        tab_id = self.notebook.select()
        tab_text = self.notebook.tab(tab_id, "text")
        
        # Aggiorna la barra di stato
        self.status_var.set(f"Sezione: {tab_text}")
        
        # Notifica il frame attivo
        frame = self.notebook.nametowidget(tab_id)
        if hasattr(frame, 'on_activate'):
            frame.on_activate()
    
    def _on_close(self) -> None:
        """Gestisce la chiusura dell'applicazione."""
        # Salva la configurazione
        self.config.save()
        
        # Chiudi l'applicazione
        self.root.destroy()
    
    def _on_import_yaml(self) -> None:
        """Importa allenamenti da file YAML."""
        # Passa la richiesta al frame ImportExport
        self.notebook.select(self.import_export)
        self.import_export.import_yaml()
    
    def _on_import_excel(self) -> None:
        """Importa allenamenti da file Excel."""
        # Passa la richiesta al frame ImportExport
        self.notebook.select(self.import_export)
        self.import_export.import_excel()
    
    def _on_export_yaml(self) -> None:
        """Esporta allenamenti in file YAML."""
        # Passa la richiesta al frame ImportExport
        self.notebook.select(self.import_export)
        self.import_export.export_yaml()
    
    def _on_export_excel(self) -> None:
        """Esporta allenamenti in file Excel."""
        # Passa la richiesta al frame ImportExport
        self.notebook.select(self.import_export)
        self.import_export.export_excel()
    
    def _on_theme_change(self) -> None:
        """Gestisce il cambio di tema."""
        theme = self.theme_var.get()
        setup_styles(self.root, theme)
        self.config.set('ui.theme', theme)
        self.config.save()
    
    def _on_new_workout(self) -> None:
        """Crea un nuovo allenamento."""
        # Passa la richiesta al frame WorkoutEditor
        self.notebook.select(self.workout_editor)
        self.workout_editor.new_workout()
    
    def _on_schedule_workout(self) -> None:
        """Pianifica gli allenamenti."""
        # Passa la richiesta al frame WorkoutEditor
        self.notebook.select(self.workout_editor)
        self.workout_editor.schedule_workouts_dialog()
    
    def _on_sync_workouts(self) -> None:
        """Sincronizza gli allenamenti con Garmin Connect."""
        # Verifica che l'utente sia autenticato
        if not self.auth.is_authenticated:
            messagebox.showerror("Errore", "Devi prima effettuare il login a Garmin Connect")
            self.notebook.select(self.login_frame)
            return
        
        # Passa la richiesta al frame WorkoutEditor
        self.notebook.select(self.workout_editor)
        self.workout_editor.sync_with_garmin()
    
    def _on_help(self) -> None:
        """Mostra il manuale utente."""
        messagebox.showinfo("Manuale utente", 
                           "Il manuale utente è disponibile nella cartella 'docs' dell'applicazione.")
    
    def _on_about(self) -> None:
        """Mostra informazioni sull'applicazione."""
        messagebox.showinfo("Informazioni su GarminPlannerGUI", 
                           "GarminPlannerGUI\n"
                           "Versione 1.0.0\n\n"
                           "Applicazione per la gestione avanzata di allenamenti su Garmin Connect.\n\n"
                           "© 2025 - GarminPlannerGUI Team")
    
    def set_status(self, message: str) -> None:
        """
        Imposta il messaggio nella barra di stato.
        
        Args:
            message: Messaggio da visualizzare
        """
        self.status_var.set(message)
