#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Frame per il login a Garmin Connect.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Optional, Dict, Any

from auth import GarminAuth, GarminClient
from gui.utils import create_tooltip, show_error


class LoginFrame(ttk.Frame):
    """Frame per il login a Garmin Connect."""
    
    def __init__(self, parent: ttk.Notebook, auth: GarminAuth):
        """
        Inizializza il frame di login.
        
        Args:
            parent: Widget genitore (notebook)
            auth: Gestore dell'autenticazione
        """
        super().__init__(parent)
        self.parent = parent
        self.auth = auth
        
        # Stato del login
        self.is_logging_in = False
        
        # Carica l'interfaccia
        self.create_widgets()
        
        # Verifica se esistono credenziali salvate
        self.check_saved_credentials()
    
    def create_widgets(self):
        """Crea i widget del frame."""
        # Frame principale
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Intestazione
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text="Login a Garmin Connect", 
                 style="Title.TLabel").pack(side=tk.LEFT)
        
        # Form di login
        form_frame = ttk.LabelFrame(main_frame, text="Inserisci le tue credenziali")
        form_frame.pack(fill=tk.X, padx=50, pady=20)
        
        # Grid per allineare i campi
        form_grid = ttk.Frame(form_frame)
        form_grid.pack(fill=tk.X, padx=20, pady=20)
        
        # Email
        ttk.Label(form_grid, text="Email:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(form_grid, textvariable=self.email_var, width=40)
        self.email_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # Password
        ttk.Label(form_grid, text="Password:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(form_grid, textvariable=self.password_var, show="*", width=40)
        self.password_entry.grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        # Opzioni
        options_frame = ttk.Frame(form_grid)
        options_frame.grid(row=2, column=1, sticky=tk.W, pady=10)
        
        self.save_credentials_var = tk.BooleanVar(value=False)
        self.save_credentials_check = ttk.Checkbutton(
            options_frame, 
            text="Ricorda le credenziali",
            variable=self.save_credentials_var
        )
        self.save_credentials_check.pack(side=tk.LEFT)

        create_tooltip(self.save_credentials_check, 
                     "Salva email e password per il prossimo login.")
        
        # Configura il form per espandersi
        form_grid.columnconfigure(1, weight=1)
        
        # Pulsanti
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.login_button = ttk.Button(buttons_frame, text="Login", command=self.login)
        self.login_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.resume_button = ttk.Button(buttons_frame, text="Riprendi sessione", command=self.resume_session)
        self.resume_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Frame per lo stato
        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill=tk.X, pady=(20, 0))
        
        self.status_var = tk.StringVar(value="Pronto per il login")
        self.status_label = ttk.Label(self.status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # Indicatore di progresso
        self.progress_var = tk.BooleanVar(value=False)
        self.progress = ttk.Progressbar(self.status_frame, mode="indeterminate", length=100)
        
        # Informazioni aggiuntive
        info_frame = ttk.LabelFrame(main_frame, text="Informazioni")
        info_frame.pack(fill=tk.X, padx=50, pady=(20, 0))
        
        info_text = (
            "Per utilizzare questa applicazione è necessario avere un account su Garmin Connect.\n"
            "Se non hai ancora un account, puoi crearne uno gratuitamente sul sito "
            "https://connect.garmin.com\n\n"
            "Le credenziali vengono utilizzate solo per autenticarsi con Garmin Connect e non "
            "vengono mai inviate ad altri server."
        )
        
        info_label = ttk.Label(info_frame, text=info_text, wraplength=600, justify=tk.LEFT)
        info_label.pack(padx=20, pady=20)
    
    def check_saved_credentials(self):
        """Verifica se esistono credenziali salvate."""
        try:
            credentials_file = os.path.expanduser("~/.garmin_planner/credentials.txt")
            if os.path.exists(credentials_file):
                with open(credentials_file, "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 1:
                        email = lines[0].strip()
                        self.email_var.set(email)
                        self.save_credentials_var.set(True)
                        
                        # Carica anche la password se disponibile
                        if len(lines) >= 2:
                            password = lines[1].strip()
                            self.password_var.set(password)
        except Exception as e:
            logging.error(f"Error loading saved credentials: {e}")
    
    def save_credentials(self):
        """Salva le credenziali se richiesto."""
        if self.save_credentials_var.get():
            try:
                credentials_dir = os.path.expanduser("~/.garmin_planner")
                os.makedirs(credentials_dir, exist_ok=True)
                
                credentials_file = os.path.join(credentials_dir, "credentials.txt")
                with open(credentials_file, "w") as f:
                    f.write(self.email_var.get() + "\n")
                    # Salva anche la password
                    f.write(self.password_var.get())
            except Exception as e:
                logging.error(f"Error saving credentials: {e}")
    
    def login(self):
        """Effettua il login a Garmin Connect."""
        # Verifica che non sia già in corso un login
        if self.is_logging_in:
            return
        
        # Ottieni le credenziali
        email = self.email_var.get().strip()
        password = self.password_var.get()
        
        # Verifica che siano state inserite
        if not email or not password:
            show_error("Errore", "Inserisci email e password", parent=self)
            return
        
        # Aggiorna lo stato
        self.is_logging_in = True
        self.status_var.set("Login in corso...")
        self.login_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        
        # Mostra l'indicatore di progresso
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
        self.progress.start()
        
        # Aggiorna l'interfaccia
        self.update_idletasks()
        
        # Salva le credenziali se richiesto
        self.save_credentials()
        
        # Effettua il login in un thread separato
        self.auth.login(email, password, self.on_login_complete)
    
    def resume_session(self):
        """Riprende la sessione precedente."""
        # Verifica che non sia già in corso un login
        if self.is_logging_in:
            return
        
        # Aggiorna lo stato
        self.is_logging_in = True
        self.status_var.set("Ripresa sessione in corso...")
        self.login_button.configure(state="disabled")
        self.resume_button.configure(state="disabled")
        
        # Mostra l'indicatore di progresso
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
        self.progress.start()
        
        # Aggiorna l'interfaccia
        self.update_idletasks()
        
        # Riprendi la sessione in un thread separato
        self.auth.resume(self.on_login_complete)
    
    def on_login_complete(self, success: bool, client: Optional[GarminClient]):
        """
        Callback chiamato al termine del login.
        
        Args:
            success: True se il login è riuscito, False altrimenti
            client: Client Garmin o None
        """
        # Aggiorna lo stato
        self.is_logging_in = False
        
        # Ferma l'indicatore di progresso
        self.progress.stop()
        self.progress.pack_forget()
        
        # Riabilita i pulsanti
        self.login_button.configure(state="normal")
        self.resume_button.configure(state="normal")
        
        # Aggiorna il messaggio di stato
        if success:
            self.status_var.set("Login effettuato con successo")
            
            # Passa alla scheda successiva
            if isinstance(self.parent, ttk.Notebook):
                current_index = self.parent.index(self.parent.select())
                if current_index < len(self.parent.tabs()) - 1:
                    self.parent.select(current_index + 1)
            
        else:
            self.status_var.set("Login fallito")
            messagebox.showerror("Errore", "Login fallito. Verifica le credenziali e riprova.", parent=self)
    
    def on_activate(self):
        """Chiamato quando il frame viene attivato."""
        pass


if __name__ == "__main__":
    # Test del frame
    root = tk.Tk()
    root.title("Login Test")
    root.geometry("800x600")
    
    # Crea un notebook
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Crea il frame di login
    from auth import get_auth
    auth = get_auth()
    
    login_frame = LoginFrame(notebook, auth)
    notebook.add(login_frame, text="Login")
    
    root.mainloop()
