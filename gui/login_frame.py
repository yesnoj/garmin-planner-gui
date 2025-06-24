#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Frame per il login a Garmin Connect con supporto MFA e selezione cartella autenticazione.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import Optional, Dict, Any

from auth import GarminAuth, GarminClient, get_auth, reset_auth
from gui.utils import create_tooltip, show_error
from config import get_config


class LoginFrame(ttk.Frame):
    """Frame per il login a Garmin Connect con supporto MFA."""
    
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
        self.config = get_config()
        
        # Stato del login
        self.is_logging_in = False
        self.mfa_mode = False
        
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
        
        # Frame per il login normale
        self.login_frame = ttk.LabelFrame(main_frame, text="Inserisci le tue credenziali")
        self.login_frame.pack(fill=tk.X, padx=50, pady=20)
        
        # Grid per allineare i campi
        form_grid = ttk.Frame(self.login_frame)
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
        
        # Frame per la cartella di autenticazione
        auth_folder_frame = ttk.LabelFrame(main_frame, text="Cartella dati autenticazione")
        auth_folder_frame.pack(fill=tk.X, padx=50, pady=(0, 20))
        
        auth_folder_content = ttk.Frame(auth_folder_frame)
        auth_folder_content.pack(fill=tk.X, padx=20, pady=15)
        
        # Mostra il percorso corrente
        current_path = self.config.get('oauth_folder', '~/.garth')
        self.auth_folder_var = tk.StringVar(value=os.path.expanduser(current_path))
        
        ttk.Label(auth_folder_content, text="Percorso:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.auth_folder_entry = ttk.Entry(auth_folder_content, textvariable=self.auth_folder_var, width=50)
        self.auth_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.browse_button = ttk.Button(auth_folder_content, text="Sfoglia...", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT)
        
        create_tooltip(self.auth_folder_entry, 
                     "Cartella dove verranno salvati i token di autenticazione.\n"
                     "Cambiare questa cartella richiederà un nuovo login.")
        
        # Frame per MFA (inizialmente nascosto)
        self.mfa_frame = ttk.LabelFrame(main_frame, text="Autenticazione a due fattori")
        
        # Contenuto del frame MFA
        mfa_content = ttk.Frame(self.mfa_frame)
        mfa_content.pack(fill=tk.X, padx=20, pady=20)
        
        # Istruzioni MFA
        mfa_info = ttk.Label(mfa_content, 
                            text="È stata inviata un'email con il codice di verifica.\n"
                                 "Inserisci il codice ricevuto per completare il login.",
                            justify=tk.CENTER)
        mfa_info.pack(pady=(0, 15))
        
        # Campo per il codice MFA
        mfa_grid = ttk.Frame(mfa_content)
        mfa_grid.pack(fill=tk.X)
        
        ttk.Label(mfa_grid, text="Codice di verifica:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        self.mfa_code_var = tk.StringVar()
        self.mfa_code_entry = ttk.Entry(mfa_grid, textvariable=self.mfa_code_var, width=20)
        self.mfa_code_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        create_tooltip(self.mfa_code_entry, 
                     "Inserisci il codice a 6 cifre ricevuto via email")
        
        # Pulsante per inviare il codice MFA
        self.mfa_submit_button = ttk.Button(mfa_content, text="Verifica codice", command=self.submit_mfa_code)
        self.mfa_submit_button.pack(pady=(15, 0))
        
        # Pulsante per annullare MFA
        self.mfa_cancel_button = ttk.Button(mfa_content, text="Annulla", command=self.cancel_mfa)
        self.mfa_cancel_button.pack(pady=(5, 0))
        
        # Pulsanti principali
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
            "vengono mai inviate ad altri server.\n\n"
            "Se hai abilitato l'autenticazione a due fattori, riceverai un codice via email "
            "che dovrai inserire per completare il login."
        )
        
        info_label = ttk.Label(info_frame, text=info_text, wraplength=600, justify=tk.LEFT)
        info_label.pack(padx=20, pady=20)
    
    def browse_folder(self):
        """Apre il dialogo per selezionare la cartella di autenticazione."""
        current_path = os.path.expanduser(self.auth_folder_var.get())
        
        # Se il percorso corrente esiste, usa quello come iniziale
        if not os.path.exists(current_path):
            current_path = os.path.expanduser("~")
        
        folder_selected = filedialog.askdirectory(
            title="Seleziona cartella per i dati di autenticazione",
            initialdir=current_path,
            parent=self
        )
        
        if folder_selected:
            # Crea una sottocartella garmin_auth nella cartella selezionata
            auth_folder = os.path.join(folder_selected, "garmin_auth")
            self.auth_folder_var.set(auth_folder)
            
            # Salva la nuova configurazione
            self.config.set('oauth_folder', auth_folder)
            self.config.save()
            
            # Aggiorna l'istanza di autenticazione
            self.update_auth_folder()
            
            messagebox.showinfo("Cartella aggiornata", 
                              f"La cartella di autenticazione è stata impostata su:\n{auth_folder}\n\n"
                              "Nota: se avevi già effettuato il login, dovrai farlo nuovamente.",
                              parent=self)
    
    def update_auth_folder(self):
        """Aggiorna la cartella di autenticazione nell'oggetto auth."""
        new_folder = self.auth_folder_var.get()
        if new_folder != self.auth.oauth_folder:
            # Resetta l'autenticazione e crea una nuova istanza con la nuova cartella
            reset_auth()
            self.auth = get_auth(oauth_folder=new_folder)
            # Aggiorna il riferimento nell'app principale se necessario
            if hasattr(self.parent.master, 'auth'):
                self.parent.master.auth = self.auth
    
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
    
    def show_mfa_mode(self):
        """Mostra l'interfaccia per l'inserimento del codice MFA."""
        self.mfa_mode = True
        
        # Nascondi il frame di login normale e cartella auth
        self.login_frame.pack_forget()
        for widget in self.master.winfo_children():
            if isinstance(widget, ttk.LabelFrame) and widget.cget("text") == "Cartella dati autenticazione":
                widget.pack_forget()
        
        # Mostra il frame MFA
        self.mfa_frame.pack(fill=tk.X, padx=50, pady=20)
        
        # Pulisci il campo del codice
        self.mfa_code_var.set("")
        
        # Focus sul campo del codice
        self.mfa_code_entry.focus()
        
        # Aggiorna lo stato
        self.status_var.set("Inserisci il codice MFA ricevuto via email")
    
    def hide_mfa_mode(self):
        """Nasconde l'interfaccia MFA e mostra quella normale."""
        self.mfa_mode = False
        
        # Nascondi il frame MFA
        self.mfa_frame.pack_forget()
        
        # Mostra il frame di login normale
        self.login_frame.pack(fill=tk.X, padx=50, pady=20)
        
        # Aggiorna lo stato
        self.status_var.set("Pronto per il login")
    
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
        
        # Aggiorna la cartella di autenticazione se necessario
        self.update_auth_folder()
        
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
    
    def submit_mfa_code(self):
        """Invia il codice MFA per completare il login."""
        # Ottieni il codice
        mfa_code = self.mfa_code_var.get().strip()
        
        # Verifica che sia stato inserito
        if not mfa_code:
            show_error("Errore", "Inserisci il codice di verifica", parent=self)
            return
        
        # Verifica che sia un codice valido (generalmente 6 cifre)
        if not mfa_code.isdigit() or len(mfa_code) != 6:
            show_error("Errore", "Il codice deve essere composto da 6 cifre", parent=self)
            return
        
        # Aggiorna lo stato
        self.status_var.set("Verifica codice in corso...")
        self.mfa_submit_button.configure(state="disabled")
        self.mfa_cancel_button.configure(state="disabled")
        
        # Mostra l'indicatore di progresso
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
        self.progress.start()
        
        # Invia il codice
        self.auth.submit_mfa_code(mfa_code, self.on_mfa_complete)
    
    def cancel_mfa(self):
        """Annulla il processo MFA e torna al login normale."""
        # Resetta lo stato
        self.is_logging_in = False
        
        # Ferma l'indicatore di progresso
        self.progress.stop()
        self.progress.pack_forget()
        
        # Riabilita i pulsanti
        self.login_button.configure(state="normal")
        self.resume_button.configure(state="normal")
        self.mfa_submit_button.configure(state="normal")
        self.mfa_cancel_button.configure(state="normal")
        
        # Torna alla modalità normale
        self.hide_mfa_mode()
    
    def resume_session(self):
        """Riprende la sessione precedente."""
        # Verifica che non sia già in corso un login
        if self.is_logging_in:
            return
        
        # Aggiorna la cartella di autenticazione se necessario
        self.update_auth_folder()
        
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
        
        # Controlla se è richiesto MFA
        logging.info(f"Login complete - Success: {success}, MFA Required: {self.auth.mfa_required}")
        
        # Gestisci il risultato
        if not success and self.auth.mfa_required:
            logging.info("Showing MFA interface")
            # Mostra l'interfaccia MFA
            self.show_mfa_mode()
        elif success:
            self.status_var.set("Login effettuato con successo")
            
            # Passa alla scheda successiva
            if isinstance(self.parent, ttk.Notebook):
                current_index = self.parent.index(self.parent.select())
                if current_index < len(self.parent.tabs()) - 1:
                    self.parent.select(current_index + 1)
            
        else:
            self.status_var.set("Login fallito")
            messagebox.showerror("Errore", "Login fallito. Verifica le credenziali e riprova.", parent=self)
    
    def on_mfa_complete(self, success: bool, client: Optional[GarminClient]):
        """
        Callback chiamato al termine della verifica MFA.
        
        Args:
            success: True se la verifica è riuscita
            client: Client Garmin o None
        """
        # Ferma l'indicatore di progresso
        self.progress.stop()
        self.progress.pack_forget()
        
        # Riabilita i pulsanti
        self.mfa_submit_button.configure(state="normal")
        self.mfa_cancel_button.configure(state="normal")
        
        if success:
            self.status_var.set("Login con MFA effettuato con successo")
            
            # Nascondi l'interfaccia MFA
            self.hide_mfa_mode()
            
            # Passa alla scheda successiva
            if isinstance(self.parent, ttk.Notebook):
                current_index = self.parent.index(self.parent.select())
                if current_index < len(self.parent.tabs()) - 1:
                    self.parent.select(current_index + 1)
            
        else:
            self.status_var.set("Verifica MFA fallita")
            messagebox.showerror("Errore", "Codice MFA non valido. Riprova.", parent=self)
    
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