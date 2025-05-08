#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestione dell'autenticazione a Garmin Connect per l'applicazione GarminPlannerGUI.
"""

import os
import logging
import time
import threading
import json
from typing import Optional, Callable, Dict, Any

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
        self.oauth_folder = os.path.expanduser(oauth_folder)
        self.client = None
        self.is_authenticated = False
        self.auth_lock = threading.Lock()
        self.auth_callbacks = []
        
        # Crea la cartella se non esiste
        os.makedirs(self.oauth_folder, exist_ok=True)
    
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
                    
                    # Effettua il login
                    garth.login(username, password)
                    garth.save(self.oauth_folder)
                    
                    # Inizializza il client e aggiorna lo stato
                    self.client = GarminClient()
                    self.is_authenticated = True
                    
                    logging.info(f"Logged in as {username}")
                    
                    # Notifica i callback
                    self._notify_auth_callbacks(True, self.client)
                    
                    # Chiama il callback specifico se fornito
                    if callback:
                        callback(True, self.client)
                        
                except Exception as e:
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
        
        # Verifica se esiste il file di sessione
        session_file = os.path.join(self.oauth_folder, 'session.json')
        if not os.path.exists(session_file):
            logging.warning(f"Session file {session_file} not found")
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
                # Cancella i token salvati
                session_file = os.path.join(self.oauth_folder, 'session.json')
                if os.path.exists(session_file):
                    os.remove(session_file)
                
                # Resetta l'autenticazione
                self.is_authenticated = False
                self.client = None
                
                logging.info("Logged out")
                
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
        Notifica tutte le funzioni di callback registrate.
        
        Args:
            is_authenticated: True se autenticato, False altrimenti
            client: Istanza del client Garmin o None
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
