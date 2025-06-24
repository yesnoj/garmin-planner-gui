#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestione dell'autenticazione a Garmin Connect per l'applicazione GarminPlannerGUI.
"""

import os
import sys
import logging
import time
import threading
import json
from typing import Optional, Callable, Dict, Any, Tuple

import garth

class GarminAuth:
    """
    Gestisce l'autenticazione a Garmin Connect utilizzando la libreria garth.
    """
    
    def __init__(self, oauth_folder: str = '~/.garth'):
        """
        Inizializza l'autenticazione.
        
        Args:
            oauth_folder: Cartella per salvare i token OAuth
        """
        # Espandi il percorso e gestisci percorsi Windows
        self.oauth_folder = os.path.expanduser(oauth_folder)
        
        # Se siamo su Windows e il percorso contiene ancora ~, usa una cartella alternativa
        if sys.platform == 'win32' and '~' in self.oauth_folder:
            # Usa la cartella documenti dell'utente
            documents = os.path.expanduser('~/Documents')
            self.oauth_folder = os.path.join(documents, 'garmin_planner', 'auth')
        
        # Log del percorso che stiamo usando
        logging.info(f"OAuth folder path: {self.oauth_folder}")
        
        # Crea la cartella se non esiste con gestione errori migliorata
        try:
            os.makedirs(self.oauth_folder, exist_ok=True)
            logging.info(f"OAuth folder created/verified: {self.oauth_folder}")
            
            # Verifica che possiamo scrivere nella cartella
            test_file = os.path.join(self.oauth_folder, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logging.info("Write permissions verified for OAuth folder")
            
        except PermissionError:
            logging.error(f"Permission denied creating OAuth folder: {self.oauth_folder}")
            # Prova una cartella alternativa nella directory dell'applicazione
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.oauth_folder = os.path.join(app_dir, 'auth_data')
            logging.info(f"Using alternative OAuth folder: {self.oauth_folder}")
            
            try:
                os.makedirs(self.oauth_folder, exist_ok=True)
            except Exception as e2:
                logging.error(f"Failed to create alternative OAuth folder: {e2}")
                raise Exception(f"Cannot create OAuth folder. Please check permissions or specify a different path in config.yaml")
                
        except Exception as e:
            logging.error(f"Error creating OAuth folder: {e}")
            raise
        
        self.client = None
        self.is_authenticated = False
        self.auth_lock = threading.Lock()
        self.auth_callbacks = []
        self.mfa_required = False
        self.temp_credentials = None  # Memorizza temporaneamente le credenziali per MFA
    
    def login(self, username: str, password: str, callback: Optional[Callable] = None) -> bool:
        """
        Effettua il login a Garmin Connect.
        
        Args:
            username: Nome utente (email)
            password: Password
            callback: Funzione da chiamare al termine del login
        
        Returns:
            True se il login è riuscito, False altrimenti
        """
        def _login_thread():
            with self.auth_lock:
                try:
                    # Resetta l'autenticazione
                    self.is_authenticated = False
                    self.client = None
                    self.mfa_required = False
                    
                    # Salva temporaneamente le credenziali
                    self.temp_credentials = (username, password)
                    
                    # Prepara per intercettare richieste MFA
                    import builtins
                    import sys
                    from io import StringIO
                    
                    # Salva l'input originale
                    original_input = builtins.input
                    mfa_detected = False
                    
                    # Crea una funzione che rileva quando viene richiesto MFA
                    def detect_mfa_input(prompt=""):
                        nonlocal mfa_detected
                        logging.info(f"Input richiesto da garth: {prompt}")
                        if "mfa" in prompt.lower() or "code" in prompt.lower():
                            mfa_detected = True
                            # Solleva un'eccezione speciale per segnalare che è richiesto MFA
                            raise Exception("MFA_REQUIRED")
                        return ""
                    
                    try:
                        # Sostituisci l'input per rilevare richieste MFA
                        builtins.input = detect_mfa_input
                        
                        # Tenta il login
                        garth.login(username, password)
                        
                        # Se arriviamo qui, il login è riuscito senza MFA
                        self._save_session()
                        
                        self.client = GarminClient()
                        self.is_authenticated = True
                        
                        logging.info(f"Logged in as {username}")
                        
                        # Notifica i callback
                        self._notify_auth_callbacks(True, self.client)
                        
                        # Chiama il callback specifico se fornito
                        if callback:
                            callback(True, self.client)
                            
                    except Exception as e:
                        error_msg = str(e)
                        logging.error(f"Login error: {error_msg}")
                        
                        if "MFA_REQUIRED" in error_msg or mfa_detected:
                            # MFA è richiesto
                            self.mfa_required = True
                            logging.info("MFA required for login - showing MFA interface")
                            
                            # Chiama il callback indicando che il login è fallito ma MFA è richiesto
                            if callback:
                                callback(False, None)
                        else:
                            # Altro errore di login
                            self.is_authenticated = False
                            self.mfa_required = False
                            
                            # Notifica i callback
                            self._notify_auth_callbacks(False, None)
                            
                            # Chiama il callback specifico se fornito
                            if callback:
                                callback(False, None)
                    
                    finally:
                        # Ripristina l'input originale
                        builtins.input = original_input
                        
                except Exception as e:
                    # Errore esterno al try interno
                    logging.error(f"Login failed: {str(e)}")
                    self.is_authenticated = False
                    
                    # Notifica i callback
                    self._notify_auth_callbacks(False, None)
                    
                    # Chiama il callback specifico se fornito
                    if callback:
                        callback(False, None)
        
        # Avvia il login in un thread separato
        threading.Thread(target=_login_thread).start()
        return True
    
    def _save_session(self):
        """Salva la sessione con gestione errori migliorata."""
        try:
            # Assicurati che la directory esista
            os.makedirs(self.oauth_folder, exist_ok=True)
            
            # Salva la sessione
            garth.save(self.oauth_folder)
            
            # Verifica che il file sia stato creato
            session_file = os.path.join(self.oauth_folder, 'oauth2_token.json')
            if os.path.exists(session_file):
                logging.info(f"Session saved successfully to: {session_file}")
                # Crea anche un link/copia come session.json per compatibilità
                session_json = os.path.join(self.oauth_folder, 'session.json')
                import shutil
                try:
                    shutil.copy2(session_file, session_json)
                    logging.info(f"Session copied to: {session_json}")
                except:
                    pass
            else:
                logging.warning("Session file not found after save attempt")
                
        except Exception as e:
            logging.error(f"Error saving session: {e}")
            raise
    
    def submit_mfa_code(self, mfa_code: str, callback: Optional[Callable] = None) -> bool:
        """
        Invia il codice MFA per completare il login.
        
        Args:
            mfa_code: Codice MFA ricevuto via email
            callback: Funzione da chiamare al termine
        
        Returns:
            True se l'invio è riuscito, False altrimenti
        """
        def _mfa_thread():
            with self.auth_lock:
                try:
                    if not self.temp_credentials:
                        raise Exception("No credentials stored for MFA")
                    
                    username, password = self.temp_credentials
                    
                    # Garth richiede il codice MFA tramite input(), dobbiamo fornirlo
                    # Creiamo un mock dell'input per fornire il codice
                    import builtins
                    import sys
                    from io import StringIO
                    
                    # Salva l'input originale
                    original_input = builtins.input
                    original_stdin = sys.stdin
                    
                    # Crea una funzione che restituisce il codice MFA quando richiesto
                    def mock_input(prompt=""):
                        logging.info(f"Input richiesto: {prompt}")
                        if "mfa" in prompt.lower() or "code" in prompt.lower():
                            logging.info(f"Fornendo codice MFA: {mfa_code}")
                            return mfa_code
                        return ""
                    
                    try:
                        # Sostituisci l'input con il nostro mock
                        builtins.input = mock_input
                        sys.stdin = StringIO(mfa_code + "\n")
                        
                        # Effettua il login (garth chiederà il codice MFA tramite input())
                        garth.login(username, password)
                        
                        # IMPORTANTE: Salva la sessione dopo il login con MFA
                        self._save_session()
                        
                        # Inizializza il client e aggiorna lo stato
                        self.client = GarminClient()
                        self.is_authenticated = True
                        self.mfa_required = False
                        self.temp_credentials = None  # Pulisci le credenziali temporanee
                        
                        logging.info(f"MFA login successful for {username}")
                        
                        # Notifica i callback
                        self._notify_auth_callbacks(True, self.client)
                        
                        # Chiama il callback specifico se fornito
                        if callback:
                            callback(True, self.client)
                            
                    finally:
                        # Ripristina l'input originale
                        builtins.input = original_input
                        sys.stdin = original_stdin
                        
                except Exception as e:
                    logging.error(f"MFA login failed: {str(e)}")
                    self.is_authenticated = False
                    
                    # Notifica i callback
                    self._notify_auth_callbacks(False, None)
                    
                    # Chiama il callback specifico se fornito
                    if callback:
                        callback(False, None)
        
        # Avvia il login MFA in un thread separato
        threading.Thread(target=_mfa_thread).start()
        return True
    
    def resume(self, callback: Optional[Callable] = None) -> bool:
        """
        Riprende la sessione precedente da token salvati.
        
        Args:
            callback: Funzione da chiamare al termine del resume
        
        Returns:
            True se il resume è riuscito, False altrimenti
        """
        def _resume_thread():
            with self.auth_lock:
                try:
                    # Resetta l'autenticazione
                    self.is_authenticated = False
                    self.client = None
                    self.mfa_required = False
                    
                    # Log dei file nella cartella oauth
                    logging.info(f"Checking OAuth folder: {self.oauth_folder}")
                    if os.path.exists(self.oauth_folder):
                        files = os.listdir(self.oauth_folder)
                        logging.info(f"Files in OAuth folder: {files}")
                    else:
                        logging.warning(f"OAuth folder does not exist: {self.oauth_folder}")
                    
                    # Prova a riprendere la sessione
                    garth.resume(self.oauth_folder)
                    
                    # Verifica che la sessione sia valida
                    response = garth.connectapi("/userprofile-service/socialProfile")
                    if not response:
                        raise Exception("Invalid session")
                    
                    # Inizializza il client e aggiorna lo stato
                    self.client = GarminClient()
                    self.is_authenticated = True
                    
                    logging.info("Session resumed successfully")
                    
                    # Notifica i callback
                    self._notify_auth_callbacks(True, self.client)
                    
                    # Chiama il callback specifico se fornito
                    if callback:
                        callback(True, self.client)
                    
                except Exception as e:
                    logging.error(f"Resume failed: {str(e)}")
                    self.is_authenticated = False
                    
                    # Notifica i callback
                    self._notify_auth_callbacks(False, None)
                    
                    # Chiama il callback specifico se fornito
                    if callback:
                        callback(False, None)
        
        # Verifica se esistono file di sessione (garth potrebbe usare nomi diversi)
        session_files = ['session.json', 'oauth2_token.json', '.garth_cache']
        session_found = False
        
        for filename in session_files:
            session_file = os.path.join(self.oauth_folder, filename)
            if os.path.exists(session_file):
                logging.info(f"Found session file: {session_file}")
                session_found = True
                break
        
        if not session_found:
            logging.warning(f"No session files found in {self.oauth_folder}")
            logging.warning(f"Checked for: {session_files}")
            if callback:
                callback(False, None)
            return False
        
        # Avvia il resume in un thread separato
        threading.Thread(target=_resume_thread).start()
        return True
    
    def logout(self) -> bool:
        """
        Effettua il logout da Garmin Connect.
        
        Returns:
            True se il logout è riuscito, False altrimenti
        """
        with self.auth_lock:
            try:
                # Rimuovi tutti i possibili file di sessione
                session_files = ['session.json', 'oauth2_token.json', '.garth_cache']
                
                for filename in session_files:
                    session_file = os.path.join(self.oauth_folder, filename)
                    if os.path.exists(session_file):
                        os.remove(session_file)
                        logging.info(f"Removed session file: {session_file}")
                
                # Resetta lo stato
                self.is_authenticated = False
                self.client = None
                self.mfa_required = False
                self.temp_credentials = None
                
                logging.info("Logged out successfully")
                
                # Notifica i callback
                self._notify_auth_callbacks(False, None)
                
                return True
            except Exception as e:
                logging.error(f"Logout failed: {str(e)}")
                return False
    
    def register_auth_callback(self, callback: Callable) -> None:
        """
        Registra una funzione da chiamare quando lo stato di autenticazione cambia.
        
        Args:
            callback: Funzione da chiamare (riceve due parametri: is_authenticated e client)
        """
        if callback not in self.auth_callbacks:
            self.auth_callbacks.append(callback)
    
    def unregister_auth_callback(self, callback: Callable) -> None:
        """
        Rimuove una funzione dai callback di autenticazione.
        
        Args:
            callback: Funzione da rimuovere
        """
        if callback in self.auth_callbacks:
            self.auth_callbacks.remove(callback)
    
    def _notify_auth_callbacks(self, is_authenticated: bool, client: Optional['GarminClient']) -> None:
        """
        Notifica tutti i callback registrati.
        
        Args:
            is_authenticated: True se l'autenticazione è riuscita
            client: Client Garmin o None
        """
        for callback in self.auth_callbacks:
            try:
                callback(is_authenticated, client)
            except Exception as e:
                logging.error(f"Error in auth callback: {str(e)}")


class GarminClient:
    """
    Client per interagire con Garmin Connect.
    Wrapper per le funzioni di garth per fornire un'interfaccia più comoda.
    """
    
    def __init__(self):
        """Inizializza il client."""
        pass
    
    def list_workouts(self) -> list:
        """
        Ottiene la lista degli allenamenti.
        
        Returns:
            Lista degli allenamenti
        """
        try:
            response = garth.connectapi(
                '/workout-service/workouts',
                params={'start': 0, 'limit': 999, 'myWorkoutsOnly': True}
            )
            return response
        except Exception as e:
            logging.error(f"Error listing workouts: {str(e)}")
            return []
    
    def get_workout(self, workout_id: str) -> Dict:
        """
        Ottiene i dettagli di un allenamento.
        
        Args:
            workout_id: ID dell'allenamento
            
        Returns:
            Dettagli dell'allenamento
        """
        try:
            response = garth.connectapi(
                f'/workout-service/workout/{workout_id}',
                method="GET"
            )
            return response
        except Exception as e:
            logging.error(f"Error getting workout {workout_id}: {str(e)}")
            return {}
    
    def add_workout(self, workout: Any) -> Dict:
        """
        Aggiunge un nuovo allenamento.
        
        Args:
            workout: Oggetto allenamento
            
        Returns:
            Risposta dell'API
        """
        try:
            response = garth.connectapi(
                '/workout-service/workout',
                method="POST",
                json=workout.garminconnect_json()
            )
            return response
        except Exception as e:
            logging.error(f"Error adding workout: {str(e)}")
            return {}
    
    def update_workout(self, workout_id: str, workout: Any) -> Dict:
        """
        Aggiorna un allenamento esistente.
        
        Args:
            workout_id: ID dell'allenamento
            workout: Oggetto allenamento
            
        Returns:
            Risposta dell'API
        """
        try:
            wo_json = workout.garminconnect_json()
            wo_json['workoutId'] = workout_id
            response = garth.connectapi(
                f'/workout-service/workout/{workout_id}',
                method="PUT",
                json=wo_json
            )
            return response
        except Exception as e:
            logging.error(f"Error updating workout {workout_id}: {str(e)}")
            return {}
    
    def delete_workout(self, workout_id: str) -> Dict:
        """
        Elimina un allenamento.
        
        Args:
            workout_id: ID dell'allenamento
            
        Returns:
            Risposta dell'API
        """
        try:
            response = garth.connectapi(
                f'/workout-service/workout/{workout_id}',
                method="DELETE"
            )
            return response
        except Exception as e:
            logging.error(f"Error deleting workout {workout_id}: {str(e)}")
            return {}
    
    def get_calendar(self, year: int, month: int) -> Dict:
        """
        Ottiene il calendario per un mese specifico.
        
        Args:
            year: Anno
            month: Mese (1-12)
            
        Returns:
            Calendario del mese
        """
        try:
            # Garmin API richiede il mese come 0-11
            api_month = month - 1
            response = garth.connectapi(
                f'/calendar-service/year/{year}/month/{api_month}'
            )
            return response
        except Exception as e:
            logging.error(f"Error getting calendar for {year}-{month}: {str(e)}")
            return {}
    
    def schedule_workout(self, workout_id: str, date: str) -> Dict:
        """
        Pianifica un allenamento per una data specifica.
        
        Args:
            workout_id: ID dell'allenamento
            date: Data nel formato YYYY-MM-DD
            
        Returns:
            Risposta dell'API
        """
        try:
            response = garth.connectapi(
                f'/workout-service/schedule/{workout_id}',
                method="POST",
                json={'date': date}
            )
            return response
        except Exception as e:
            logging.error(f"Error scheduling workout {workout_id} for {date}: {str(e)}")
            return {}
    
    def unschedule_workout(self, schedule_id: str) -> Dict:
        """
        Annulla la pianificazione di un allenamento.
        
        Args:
            schedule_id: ID della pianificazione
            
        Returns:
            Risposta dell'API
        """
        try:
            response = garth.connectapi(
                f'/workout-service/schedule/{schedule_id}',
                method="DELETE"
            )
            return response
        except Exception as e:
            logging.error(f"Error unscheduling workout {schedule_id}: {str(e)}")
            return {}
    
    def get_activities(self, start_date: str = None, end_date: str = None, limit: int = 100) -> list:
        """
        Ottiene le attività in un intervallo di date.
        
        Args:
            start_date: Data di inizio (YYYY-MM-DD)
            end_date: Data di fine (YYYY-MM-DD)
            limit: Numero massimo di attività da restituire
            
        Returns:
            Lista delle attività
        """
        try:
            params = {'start': 0, 'limit': limit}
            
            if start_date:
                params['startDate'] = start_date
            
            if end_date:
                params['endDate'] = end_date
            
            response = garth.connectapi(
                '/activitylist-service/activities/search/activities',
                params=params
            )
            return response
        except Exception as e:
            logging.error(f"Error getting activities: {str(e)}")
            return []
    
    def get_user_profile(self) -> Dict:
        """
        Ottiene il profilo utente.
        
        Returns:
            Profilo utente
        """
        try:
            response = garth.connectapi('/userprofile-service/socialProfile')
            return response
        except Exception as e:
            logging.error(f"Error getting user profile: {str(e)}")
            return {}

# Istanza singleton dell'autenticazione
_auth_instance = None

def get_auth(oauth_folder: str = '~/.garth') -> GarminAuth:
    """
    Ottiene l'istanza singleton dell'autenticazione.
    
    Args:
        oauth_folder: Cartella per salvare i token OAuth
        
    Returns:
        Istanza dell'autenticazione
    """
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = GarminAuth(oauth_folder)
    return _auth_instance

def reset_auth() -> None:
    """Reimposta l'istanza dell'autenticazione."""
    global _auth_instance
    _auth_instance = None