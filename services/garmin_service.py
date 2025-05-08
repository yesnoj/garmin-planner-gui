#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servizio per interagire con Garmin Connect.
"""

import logging
import datetime
import calendar
from typing import Dict, Any, List, Tuple, Optional

from auth import GarminClient
from models.workout import Workout, WorkoutStep, Target
from models.calendar import Calendar, CalendarMonth, CalendarDay, CalendarItem


class GarminService:
    """Servizio per interagire con Garmin Connect."""
    
    def __init__(self, client: GarminClient):
        """
        Inizializza il servizio.
        
        Args:
            client: Client Garmin
        """
        self.client = client
    
    def get_workouts(self) -> List[Dict[str, Any]]:
        """
        Ottiene la lista degli allenamenti da Garmin Connect.
        
        Returns:
            Lista degli allenamenti
        """
        try:
            return self.client.list_workouts()
        except Exception as e:
            logging.error(f"Errore nel recupero degli allenamenti: {str(e)}")
            return []
    
    def get_workout(self, workout_id: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene i dettagli di un allenamento da Garmin Connect.
        
        Args:
            workout_id: ID dell'allenamento
            
        Returns:
            Dettagli dell'allenamento o None se non trovato
        """
        try:
            return self.client.get_workout(workout_id)
        except Exception as e:
            logging.error(f"Errore nel recupero dell'allenamento {workout_id}: {str(e)}")
            return None
    
    def add_workout(self, workout: Workout) -> Optional[Dict[str, Any]]:
        """
        Aggiunge un allenamento a Garmin Connect.
        
        Args:
            workout: Allenamento da aggiungere
            
        Returns:
            Risposta di Garmin Connect o None se fallisce
        """
        try:
            return self.client.add_workout(workout)
        except Exception as e:
            logging.error(f"Errore nell'aggiunta dell'allenamento: {str(e)}")
            return None
    
    def update_workout(self, workout_id: str, workout: Workout) -> Optional[Dict[str, Any]]:
        """
        Aggiorna un allenamento su Garmin Connect.
        
        Args:
            workout_id: ID dell'allenamento
            workout: Allenamento aggiornato
            
        Returns:
            Risposta di Garmin Connect o None se fallisce
        """
        try:
            return self.client.update_workout(workout_id, workout)
        except Exception as e:
            logging.error(f"Errore nell'aggiornamento dell'allenamento {workout_id}: {str(e)}")
            return None
    
    def delete_workout(self, workout_id: str) -> bool:
        """
        Elimina un allenamento da Garmin Connect.
        
        Args:
            workout_id: ID dell'allenamento
            
        Returns:
            True se l'eliminazione è riuscita, False altrimenti
        """
        try:
            self.client.delete_workout(workout_id)
            return True
        except Exception as e:
            logging.error(f"Errore nell'eliminazione dell'allenamento {workout_id}: {str(e)}")
            return False
    
    def get_calendar(self, year: int, month: int) -> Optional[Dict[str, Any]]:
        """
        Ottiene il calendario di un mese da Garmin Connect.
        
        Args:
            year: Anno
            month: Mese (1-12)
            
        Returns:
            Calendario del mese o None se fallisce
        """
        try:
            return self.client.get_calendar(year, month)
        except Exception as e:
            logging.error(f"Errore nel recupero del calendario {year}-{month}: {str(e)}")
            return None
    
    def get_calendar_month(self, year: int, month: int) -> Optional[CalendarMonth]:
        """
        Ottiene un mese del calendario da Garmin Connect.
        
        Args:
            year: Anno
            month: Mese (1-12)
            
        Returns:
            Mese del calendario o None se fallisce
        """
        # Ottieni i dati del mese
        data = self.get_calendar(year, month)
        
        if not data:
            return None
        
        # Crea il mese
        month_obj = CalendarMonth.from_garmin_data(year, month, data)
        
        # Aggiungi le attività
        # Calcola il primo e l'ultimo giorno del mese
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        
        # Ottieni le attività per questo mese
        activities = self.client.get_activities(start_date, end_date)
        
        # Aggiungi le attività al mese
        for activity in activities:
            calendar_item = CalendarItem.from_garmin_activity(activity)
            month_obj.add_item(calendar_item)
        
        return month_obj
    
    def get_activities(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Ottiene le attività in un intervallo di date da Garmin Connect.
        
        Args:
            start_date: Data di inizio (formato YYYY-MM-DD)
            end_date: Data di fine (formato YYYY-MM-DD)
            
        Returns:
            Lista delle attività
        """
        try:
            return self.client.get_activities(start_date, end_date)
        except Exception as e:
            logging.error(f"Errore nel recupero delle attività: {str(e)}")
            return []
    
    def schedule_workout(self, workout_id: str, date: str) -> Optional[Dict[str, Any]]:
        """
        Pianifica un allenamento su Garmin Connect.
        
        Args:
            workout_id: ID dell'allenamento
            date: Data nel formato YYYY-MM-DD
            
        Returns:
            Risposta di Garmin Connect o None se fallisce
        """
        try:
            return self.client.schedule_workout(workout_id, date)
        except Exception as e:
            logging.error(f"Errore nella pianificazione dell'allenamento {workout_id} per {date}: {str(e)}")
            return None
    
    def unschedule_workout(self, schedule_id: str) -> bool:
        """
        Annulla la pianificazione di un allenamento su Garmin Connect.
        
        Args:
            schedule_id: ID della pianificazione
            
        Returns:
            True se l'annullamento è riuscito, False altrimenti
        """
        try:
            self.client.unschedule_workout(schedule_id)
            return True
        except Exception as e:
            logging.error(f"Errore nell'annullamento della pianificazione {schedule_id}: {str(e)}")
            return False
    
    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Ottiene il profilo utente da Garmin Connect.
        
        Returns:
            Profilo utente o None se fallisce
        """
        try:
            return self.client.get_user_profile()
        except Exception as e:
            logging.error(f"Errore nel recupero del profilo utente: {str(e)}")
            return None
    
    def import_workout(self, workout_data: Dict[str, Any]) -> Optional[Workout]:
        """
        Importa un allenamento da dati di Garmin Connect.
        
        Args:
            workout_data: Dati dell'allenamento
            
        Returns:
            Allenamento importato o None se fallisce
        """
        try:
            # Estrai i dati di base
            name = workout_data.get('workoutName', 'Allenamento')
            description = workout_data.get('description')
            
            # Estrai il tipo di sport
            sport_type = 'running'  # Default
            if 'sportType' in workout_data and 'sportTypeKey' in workout_data['sportType']:
                sport_type = workout_data['sportType']['sportTypeKey']
            
            # Crea l'allenamento
            workout = Workout(sport_type, name, description)
            
            # Aggiungi gli step
            segments = workout_data.get('workoutSegments', [])
            for segment in segments:
                for step_data in segment.get('workoutSteps', []):
                    # Importa lo step
                    step = self.import_step(step_data)
                    if step:
                        workout.add_step(step)
            
            return workout
            
        except Exception as e:
            logging.error(f"Errore nell'importazione dell'allenamento: {str(e)}")
            return None
    
    def import_step(self, step_data: Dict[str, Any]) -> Optional[WorkoutStep]:
        """
        Importa uno step da dati di Garmin Connect.
        
        Args:
            step_data: Dati dello step
            
        Returns:
            Step importato o None se fallisce
        """
        try:
            # Estrai i dati di base
            step_type_info = step_data.get('stepType', {})
            step_type = step_type_info.get('stepTypeKey', 'other')
            
            description = step_data.get('description', '')
            
            # Estrai la condizione di fine
            end_condition_info = step_data.get('endCondition', {})
            end_condition = end_condition_info.get('conditionTypeKey', 'lap.button')
            
            end_condition_value = step_data.get('endConditionValue')
            
            # Estrai l'ordine
            order = step_data.get('stepOrder', 0)
            
            # Crea lo step
            step = WorkoutStep(order, step_type, description, end_condition, end_condition_value)
            
            # Se è un repeat, aggiungi gli step figli
            if step_type == 'repeat' and 'workoutSteps' in step_data:
                for child_data in step_data['workoutSteps']:
                    child_step = self.import_step(child_data)
                    if child_step:
                        step.add_step(child_step)
            else:
                # Estrai il target
                target_info = step_data.get('targetType', {})
                target_type = target_info.get('workoutTargetTypeKey', 'no.target')
                
                if target_type != 'no.target':
                    target_value_one = step_data.get('targetValueOne')
                    target_value_two = step_data.get('targetValueTwo')
                    zone_number = step_data.get('zoneNumber')
                    
                    target = Target(target_type, target_value_one, target_value_two, zone_number)
                    step.target = target
            
            return step
            
        except Exception as e:
            logging.error(f"Errore nell'importazione dello step: {str(e)}")
            return None