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
                    
                    logging.info(f"--- Analisi Target ---")
                    logging.info(f"Target type: {target_type}")
                    logging.info(f"Target values: {target_value_one}, {target_value_two}")
                    
                    target = Target(target_type, target_value_one, target_value_two, zone_number)
                    
                    # Identifica il nome della zona in base ai valori
                    from config import get_config
                    config = get_config()
                    
                    if target_type == 'pace.zone' and target_value_one is not None and target_value_two is not None:
                        # Ottieni le zone di passo per questo sport
                        sport_type = getattr(step, 'sport_type', 'running')
                        paces = config.get(f'sports.{sport_type}.paces', {})
                        
                        logging.info(f"Sport type: {sport_type}")
                        logging.info(f"Zone configurate: {paces}")
                        
                        # Ottieni i margini per questo sport
                        margins = config.get(f'sports.{sport_type}.margins', {})
                        faster_margin = margins.get('faster', '0:02')
                        slower_margin = margins.get('slower', '0:02')
                        
                        logging.info(f"Margini: faster={faster_margin}, slower={slower_margin}")
                        
                        # Converti i margini in secondi
                        def pace_to_seconds(pace):
                            if ':' in pace:
                                mins, secs = pace.split(':')
                                return int(mins) * 60 + int(secs)
                            return 0
                        
                        def seconds_to_pace(seconds):
                            mins = seconds // 60
                            secs = seconds % 60
                            return f"{mins}:{secs:02d}"
                        
                        faster_secs = pace_to_seconds(faster_margin)
                        slower_secs = pace_to_seconds(slower_margin)
                        
                        logging.info(f"Margini in secondi: faster={faster_secs}s, slower={slower_secs}s")
                        
                        # Converti i valori target da m/s a secondi/km
                        # In Garmin, valori più alti in m/s = più veloce
                        pace_one_secs = int(1000 / target_value_one) if target_value_one > 0 else 0
                        pace_two_secs = int(1000 / target_value_two) if target_value_two > 0 else 0
                        
                        logging.info(f"Valori di passo in secondi/km: {pace_one_secs}s, {pace_two_secs}s")
                        logging.info(f"Valori di passo formattati: {seconds_to_pace(pace_one_secs)}, {seconds_to_pace(pace_two_secs)}")
                        
                        # Determina qual è il più veloce e il più lento
                        fast_pace_secs = min(pace_one_secs, pace_two_secs)  # Valore più basso = più veloce
                        slow_pace_secs = max(pace_one_secs, pace_two_secs)  # Valore più alto = più lento
                        
                        logging.info(f"Passo più veloce: {seconds_to_pace(fast_pace_secs)}, più lento: {seconds_to_pace(slow_pace_secs)}")
                        
                        # Rimuovi i margini per trovare il valore centrale
                        # Il valore più veloce dovrebbe aumentare (sottrarre i margini)
                        # Il valore più lento dovrebbe diminuire (aggiungere i margini)
                        adjusted_fast_pace_secs = fast_pace_secs + faster_secs
                        adjusted_slow_pace_secs = slow_pace_secs - slower_secs
                        central_pace_secs = (adjusted_fast_pace_secs + adjusted_slow_pace_secs) // 2
                        
                        logging.info(f"Passo veloce corretto: {seconds_to_pace(adjusted_fast_pace_secs)}")
                        logging.info(f"Passo lento corretto: {seconds_to_pace(adjusted_slow_pace_secs)}")
                        logging.info(f"Passo centrale: {seconds_to_pace(central_pace_secs)}")
                        
                        # Cerca la zona che corrisponde a questo valore centrale
                        logging.info(f"Ricerca della zona corrispondente...")
                        
                        for zone_name, pace_value in paces.items():
                            # Rimuovi eventuali spazi
                            pace_value = pace_value.strip()
                            
                            # Se è un intervallo, confronta con il centro dell'intervallo
                            if '-' in pace_value:
                                min_p, max_p = pace_value.split('-')
                                min_p = min_p.strip()
                                max_p = max_p.strip()
                                min_secs = pace_to_seconds(min_p)
                                max_secs = pace_to_seconds(max_p)
                                zone_central_secs = (min_secs + max_secs) // 2
                                logging.info(f"  Zona {zone_name}: {min_p}-{max_p}, centro: {seconds_to_pace(zone_central_secs)}")
                            else:
                                # È un valore singolo
                                zone_central_secs = pace_to_seconds(pace_value)
                                logging.info(f"  Zona {zone_name}: {pace_value}, centro: {seconds_to_pace(zone_central_secs)}")
                            
                            # Verifica la corrispondenza con tolleranza
                            tolerance = 5  # 5 secondi di tolleranza
                            diff = abs(central_pace_secs - zone_central_secs)
                            logging.info(f"  Differenza: {diff}s (tolleranza: {tolerance}s)")
                            
                            if diff <= tolerance:
                                target.target_zone_name = zone_name
                                logging.info(f"  MATCH! Zona corrispondente: {zone_name}")
                                break
                            else:
                                logging.info(f"  No match")
                        
                        if not hasattr(target, 'target_zone_name') or not target.target_zone_name:
                            logging.info("Nessuna zona corrispondente trovata!")
                    
                    elif target_type == 'heart.rate.zone' and target_value_one is not None and target_value_two is not None:
                        # Per le zone HR dobbiamo anche determinare qual è il valore minimo e massimo
                        min_hr = min(target_value_one, target_value_two)
                        max_hr = max(target_value_one, target_value_two)
                        
                        logging.info(f"Valori HR: min={min_hr}, max={max_hr}")
                        
                        # Ottieni i margini
                        heart_rates = config.get('heart_rates', {})
                        hr_margins = config.get('hr_margins', {})
                        hr_up = hr_margins.get('hr_up', 5)
                        hr_down = hr_margins.get('hr_down', 5)
                        
                        logging.info(f"Margini HR: up={hr_up}, down={hr_down}")
                        
                        # Rimuovi i margini per trovare il valore centrale
                        adjusted_min_hr = min_hr + hr_down
                        adjusted_max_hr = max_hr - hr_up
                        central_hr = (adjusted_min_hr + adjusted_max_hr) // 2
                        
                        logging.info(f"HR min corretto: {adjusted_min_hr}")
                        logging.info(f"HR max corretto: {adjusted_max_hr}")
                        logging.info(f"HR centrale: {central_hr}")
                        
                        # Cerca la zona corrispondente
                        logging.info(f"Ricerca della zona HR corrispondente...")
                        
                        for zone_name, hr_range in heart_rates.items():
                            if zone_name.endswith('_HR'):
                                max_hr_config = heart_rates.get('max_hr', 180)
                                
                                if '-' in hr_range and 'max_hr' in hr_range:
                                    # Formato: 62-76% max_hr
                                    parts = hr_range.split('-')
                                    min_percent = float(parts[0])
                                    max_percent = float(parts[1].split('%')[0])
                                    hr_min = int(min_percent * max_hr_config / 100)
                                    hr_max = int(max_percent * max_hr_config / 100)
                                    zone_central_hr = (hr_min + hr_max) // 2
                                    logging.info(f"  Zona {zone_name}: {hr_min}-{hr_max}, centro: {zone_central_hr}")
                                else:
                                    # Valore singolo
                                    try:
                                        if 'max_hr' in hr_range:
                                            percent = float(hr_range.split('%')[0])
                                            zone_central_hr = int(percent * max_hr_config / 100)
                                        else:
                                            zone_central_hr = int(hr_range)
                                        logging.info(f"  Zona {zone_name}: valore singolo, centro: {zone_central_hr}")
                                    except (ValueError, TypeError):
                                        continue
                                
                                # Verifica con tolleranza
                                tolerance = 5  # 5 bpm di tolleranza
                                diff = abs(central_hr - zone_central_hr)
                                logging.info(f"  Differenza: {diff} (tolleranza: {tolerance})")
                                
                                if diff <= tolerance:
                                    target.target_zone_name = zone_name
                                    logging.info(f"  MATCH! Zona corrispondente: {zone_name}")
                                    break
                                else:
                                    logging.info(f"  No match")
                    
                    elif target_type == 'power.zone' and target_value_one is not None and target_value_two is not None:
                        # Per le zone di potenza dobbiamo anche determinare qual è il valore minimo e massimo
                        min_power = min(target_value_one, target_value_two)
                        max_power = max(target_value_one, target_value_two)
                        
                        logging.info(f"Valori Power: min={min_power}, max={max_power}")
                        
                        # Ottieni i margini
                        power_values = config.get('sports.cycling.power_values', {})
                        margins = config.get('sports.cycling.margins', {})
                        power_up = margins.get('power_up', 10)
                        power_down = margins.get('power_down', 10)
                        
                        logging.info(f"Margini Power: up={power_up}, down={power_down}")
                        
                        # Rimuovi i margini per trovare il valore centrale
                        adjusted_min_power = min_power + power_down
                        adjusted_max_power = max_power - power_up
                        central_power = (adjusted_min_power + adjusted_max_power) // 2
                        
                        logging.info(f"Power min corretto: {adjusted_min_power}")
                        logging.info(f"Power max corretto: {adjusted_max_power}")
                        logging.info(f"Power centrale: {central_power}")
                        
                        # Cerca la zona corrispondente
                        logging.info(f"Ricerca della zona Power corrispondente...")
                        
                        for zone_name, power_range in power_values.items():
                            if zone_name == 'ftp':  # Salta FTP, non è una zona
                                continue
                            
                            # Calcola il centro della zona
                            if '-' in power_range:
                                min_p, max_p = power_range.split('-')
                                min_power_zone = int(min_p.strip())
                                max_power_zone = int(max_p.strip())
                                zone_central_power = (min_power_zone + max_power_zone) // 2
                                logging.info(f"  Zona {zone_name}: {min_power_zone}-{max_power_zone}, centro: {zone_central_power}")
                            elif power_range.startswith('<'):
                                max_power_zone = int(power_range[1:].strip())
                                zone_central_power = max_power_zone // 2  # Approssimazione
                                logging.info(f"  Zona {zone_name}: <{max_power_zone}, centro approx: {zone_central_power}")
                            elif power_range.endswith('+'):
                                min_power_zone = int(power_range[:-1].strip())
                                zone_central_power = min_power_zone + 50  # Approssimazione
                                logging.info(f"  Zona {zone_name}: {min_power_zone}+, centro approx: {zone_central_power}")
                            else:
                                # Valore singolo
                                try:
                                    zone_central_power = int(power_range)
                                    logging.info(f"  Zona {zone_name}: valore singolo {zone_central_power}")
                                except (ValueError, TypeError):
                                    continue
                            
                            # Verifica con tolleranza
                            tolerance = 10  # 10 watt di tolleranza
                            diff = abs(central_power - zone_central_power)
                            logging.info(f"  Differenza: {diff} (tolleranza: {tolerance})")
                            
                            if diff <= tolerance:
                                target.target_zone_name = zone_name
                                logging.info(f"  MATCH! Zona corrispondente: {zone_name}")
                                break
                            else:
                                logging.info(f"  No match")
                    
                    # Log finale per confermare il nome della zona assegnato
                    if hasattr(target, 'target_zone_name') and target.target_zone_name:
                        logging.info(f"Target zone name assegnato: {target.target_zone_name}")
                    else:
                        logging.info("Nessun target_zone_name assegnato!")
                    
                    step.target = target
            
            return step
            
        except Exception as e:
            logging.error(f"Errore nell'importazione dello step: {str(e)}")
            logging.exception("Stack trace:")
            return None