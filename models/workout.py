#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Classi per la gestione degli allenamenti.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union
from config import get_config

class Target:
    """Classe per i target degli step."""
    
    def __init__(self, target: str = "no.target", to_value: Optional[float] = None, 
               from_value: Optional[float] = None, zone: Optional[int] = None):
        """
        Inizializza un target.
        
        Args:
            target: Tipo di target
            to_value: Valore massimo
            from_value: Valore minimo
            zone: Zona (per target di tipo 'zone')
        """
        self.target = target
        self.to_value = to_value
        self.from_value = from_value
        self.zone = zone
        self.target_zone_name = None  # Nome della zona
        self.original_to_value = to_value  # Valore originale prima delle correzioni
        self.original_from_value = from_value  # Valore originale prima delle correzioni
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il target in un dizionario.
        
        Returns:
            Dizionario con i dati del target
        """
        result = {
            'target': self.target,
            'to_value': self.to_value,
            'from_value': self.from_value,
            'zone': self.zone
        }
        
        # Aggiungi target_zone_name se presente
        if hasattr(self, 'target_zone_name') and self.target_zone_name:
            result['target_zone_name'] = self.target_zone_name
            
        return result
    
    def garminconnect_json(self) -> Dict[str, Any]:
        """
        Converte il target in formato JSON per Garmin Connect.
        
        Returns:
            Dizionario JSON per l'API di Garmin Connect
        """
        # Mappatura dei tipi di target
        target_types = {
            "no.target": 1,
            "power.zone": 2,
            "cadence.zone": 3,
            "heart.rate.zone": 4,
            "speed.zone": 5,
            "pace.zone": 6  # Metri per secondo
        }
        
        # Se abbiamo un target di tipo pace.zone, dobbiamo assicurarci che i valori to_value e from_value
        # siano corretti e includano i margini appropriati
        target_values = self._get_adjusted_target_values()
        to_value, from_value = target_values
        
        return {
            "targetType": {
                "workoutTargetTypeId": target_types.get(self.target, 1),
                "workoutTargetTypeKey": self.target
            },
            "targetValueOne": to_value,
            "targetValueTwo": from_value,
            "zoneNumber": self.zone
        }


    def _get_adjusted_target_values(self):
        """
        Restituisce i valori target eventualmente adattati con i margini.
        
        Returns:
            Tupla (to_value, from_value) con i valori adattati
        """
        # Se non è un target di tipo pace, restituisci i valori originali
        if self.target != "pace.zone":
            return (self.to_value, self.from_value)
        
        # Se i valori sono diversi (intervallo già specificato), restituiscili così come sono
        if self.to_value != self.from_value and self.to_value is not None and self.from_value is not None:
            return (self.to_value, self.from_value)
        
        # Se abbiamo un solo valore o valori uguali, dobbiamo applicare i margini
        # Ottieni i margini dalla configurazione
        from config import get_config
        config = get_config()
        
        # Determina il tipo di sport
        sport_type = getattr(self, 'sport_type', 'running')  # Default a corsa
        
        # Se abbiamo un nome di zona, cerca di identificare lo sport da esso
        if hasattr(self, 'target_zone_name') and self.target_zone_name:
            # Cerca in quale configurazione di sport esiste questa zona
            for sport in ["running", "cycling", "swimming"]:
                paces = config.get(f'sports.{sport}.paces', {})
                if self.target_zone_name in paces:
                    sport_type = sport
                    break
        
        # Ottieni i margini per questo sport
        margins = config.get(f'sports.{sport_type}.margins', {})
        faster_margin = margins.get('faster', '0:05')
        slower_margin = margins.get('slower', '0:05')
        
        # Converti i margini in secondi
        from gui.utils import pace_to_seconds
        faster_seconds = pace_to_seconds(faster_margin)
        slower_seconds = pace_to_seconds(slower_margin)
        
        # Calcola i valori di passo con i margini
        # Prendi il valore di base (solitamente to_value)
        base_pace_ms = self.to_value if self.to_value is not None else self.from_value
        
        # Se abbiamo un valore di base, applica i margini
        if base_pace_ms:
            # Tempo per km in secondi
            seconds_per_km = 1000 / base_pace_ms
            
            # Applica i margini
            fast_seconds_per_km = seconds_per_km - faster_seconds
            slow_seconds_per_km = seconds_per_km + slower_seconds
            
            # Converti in m/s (attenzione: più veloce = valore più grande in m/s)
            fast_pace_ms = 1000 / fast_seconds_per_km if fast_seconds_per_km > 0 else base_pace_ms
            slow_pace_ms = 1000 / slow_seconds_per_km if slow_seconds_per_km > 0 else base_pace_ms
            
            # Valori per Garmin Connect: to_value è il limite superiore, from_value è il limite inferiore
            return (fast_pace_ms, slow_pace_ms)
        
        # Se non abbiamo abbastanza informazioni, restituisci i valori originali
        return (self.to_value, self.from_value)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Target':
        """
        Crea un target da un dizionario.
        
        Args:
            data: Dizionario con i dati del target
            
        Returns:
            Target creato
        """
        target = cls(
            target=data.get('target', 'no.target'),
            to_value=data.get('to_value'),
            from_value=data.get('from_value'),
            zone=data.get('zone')
        )
        
        # Ripristina target_zone_name se presente
        if 'target_zone_name' in data:
            target.target_zone_name = data['target_zone_name']
            
        return target
    
    def __repr__(self) -> str:
        zone_info = f", zone={self.zone}" if self.zone is not None else ""
        zone_name_info = f", zone_name={self.target_zone_name}" if hasattr(self, 'target_zone_name') and self.target_zone_name else ""
        return f"Target({self.target}, from={self.from_value}, to={self.to_value}{zone_info}{zone_name_info})"


class WorkoutStep:
    """Classe per gli step degli allenamenti."""
    
    def __init__(self, order: int, step_type: str, description: str = "", 
               end_condition: str = "lap.button", end_condition_value: Optional[Union[str, int, float]] = None, 
               target: Optional[Target] = None, date: Optional[str] = None):
        """
        Inizializza uno step.
        
        Args:
            order: Ordine dello step nell'allenamento
            step_type: Tipo di step (warmup, cooldown, interval, repeat, ...)
            description: Descrizione dello step
            end_condition: Condizione di fine (lap.button, time, distance, ...)
            end_condition_value: Valore della condizione di fine
            target: Target dello step
            date: Data dell'allenamento (solo per step speciali)
        """
        self.order = order
        self.step_type = step_type
        self.description = description
        self.end_condition = end_condition
        self.end_condition_value = end_condition_value
        self.target = target or Target()
        self.workout_steps = []
        self.date = date
        
        # Attributi specifici del tipo di sport
        self.sport_type = ""
    
    def add_step(self, step: 'WorkoutStep') -> None:
        """
        Aggiunge uno step figlio (per repeat).
        
        Args:
            step: Step da aggiungere
        """
        # Aggiorna l'ordine
        step.order = len(self.workout_steps)
        
        # Aggiungi lo step
        self.workout_steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte lo step in un dizionario.
        
        Returns:
            Dizionario con i dati dello step
        """
        data = {
            'order': self.order,
            'type': self.step_type,
            'description': self.description,
            'end_condition': self.end_condition,
            'end_condition_value': self.end_condition_value,
            'target': self.target.to_dict() if self.target else None
        }
        
        # Aggiungi la data se presente
        if hasattr(self, 'date') and self.date:
            data['date'] = self.date
        
        # Aggiungi gli step figli se presenti
        if self.workout_steps:
            data['workout_steps'] = [step.to_dict() for step in self.workout_steps]
        
        return data
    
    def garminconnect_json(self) -> Dict[str, Any]:
        """
        Converte lo step in formato JSON per Garmin Connect.
        
        Returns:
            Dizionario JSON per l'API di Garmin Connect
        """
        # Mappatura dei tipi di step
        step_types = {
            "warmup": 1,
            "cooldown": 2,
            "interval": 3,
            "recovery": 4,
            "rest": 5,
            "repeat": 6,
            "other": 7
        }
        
        # Mappatura delle condizioni di fine
        end_conditions = {
            "lap.button": 1,
            "time": 2,
            "distance": 3,
            "iterations": 7
        }
        
        # Determina se si tratta di un gruppo di ripetizioni o di uno step normale
        if self.step_type == "repeat":
            # JSON per un gruppo di ripetizioni
            step_json = {
                "type": "RepeatGroupDTO",
                "stepId": None,
                "stepOrder": self.order,
                "childStepId": 1,  # Valore fisso per i gruppi di ripetizioni
                "stepType": {
                    "stepTypeId": step_types.get(self.step_type, 7),
                    "stepTypeKey": self.step_type
                },
                "endCondition": {
                    "conditionTypeKey": self.end_condition,
                    "conditionTypeId": end_conditions.get(self.end_condition, 1)
                },
                "endConditionValue": self._parse_end_condition_value(),
                "smartRepeat": True,
                "numberOfIterations": self.end_condition_value,
                "workoutSteps": [step.garminconnect_json() for step in self.workout_steps]
            }
        else:
            # JSON per uno step normale
            step_json = {
                "type": "ExecutableStepDTO",
                "stepId": None,
                "stepOrder": self.order,
                "childStepId": None,
                "stepType": {
                    "stepTypeId": step_types.get(self.step_type, 7),
                    "stepTypeKey": self.step_type
                },
                "endCondition": {
                    "conditionTypeKey": self.end_condition,
                    "conditionTypeId": end_conditions.get(self.end_condition, 1)
                },
                "endConditionValue": self._parse_end_condition_value(),
                "description": self.description or "",
                "preferredEndConditionUnit": self._get_end_condition_unit(),
                "endConditionCompare": None,
                "endConditionZone": None
            }
            
            # Aggiungi le informazioni sul target
            if self.target:
                # Se abbiamo un target di tipo pace.zone, assicuriamoci che abbia informazioni sullo sport
                if self.target.target == "pace.zone":
                    # Passa lo sport_type al target
                    self.target.sport_type = getattr(self, 'sport_type', 'running')
                    
                    # Se abbiamo un nome di zona, passiamolo anche al target
                    if hasattr(self.target, 'target_zone_name') and self.target.target_zone_name:
                        # Il nome della zona è già impostato, non facciamo nulla
                        pass
                
                # Aggiungi il JSON del target
                target_json = self.target.garminconnect_json()
                step_json.update(target_json)
        
        return step_json

    def _parse_end_condition_value(self):
        """
        Analizza il valore della condizione di fine e lo converte nel formato appropriato.
        
        Returns:
            Valore processato della condizione di fine
        """
        if not self.end_condition_value:
            return None
        
        # Se è una stringa, processa in base al tipo di condizione
        if isinstance(self.end_condition_value, str):
            # Distanza nel formato "1000m" o "5km"
            if self.end_condition == "distance":
                if "km" in self.end_condition_value:
                    # Converte da km a m
                    value = self.end_condition_value.replace("km", "").strip()
                    try:
                        return float(value) * 1000
                    except ValueError:
                        return 0
                elif "m" in self.end_condition_value:
                    # Estrae la distanza in metri
                    value = self.end_condition_value.replace("m", "").strip()
                    try:
                        return float(value)
                    except ValueError:
                        return 0
                else:
                    # Assume che sia già in metri
                    try:
                        return float(self.end_condition_value)
                    except ValueError:
                        return 0
            
            # Tempo nel formato "mm:ss"
            elif self.end_condition == "time":
                if ":" in self.end_condition_value:
                    # Converte da mm:ss a secondi
                    parts = self.end_condition_value.split(":")
                    if len(parts) == 2:
                        try:
                            return int(parts[0]) * 60 + int(parts[1])
                        except ValueError:
                            return 0
                else:
                    # Assume che sia già in secondi
                    try:
                        return int(self.end_condition_value)
                    except ValueError:
                        return 0
        
        # Per le ripetizioni o altri tipi, usa il valore direttamente
        if self.end_condition == "iterations":
            try:
                return int(self.end_condition_value)
            except (ValueError, TypeError):
                return 1
        
        # Se non è processabile, restituisce il valore originale
        return self.end_condition_value

    def _get_end_condition_unit(self):
        """
        Determina l'unità della condizione di fine.
        
        Returns:
            Dizionario con l'unità o None se non applicabile
        """
        if self.end_condition == "distance":
            if isinstance(self.end_condition_value, str) and "km" in self.end_condition_value:
                return {"unitKey": "kilometer"}
            else:
                return {"unitKey": "meter"}
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkoutStep':
        """
        Crea uno step da un dizionario.
        
        Args:
            data: Dizionario con i dati dello step
            
        Returns:
            Step creato
        """
        # Crea lo step
        step = cls(
            order=data.get('order', 0),
            step_type=data.get('type', ''),
            description=data.get('description', ''),
            end_condition=data.get('end_condition', 'lap.button'),
            end_condition_value=data.get('end_condition_value'),
            date=data.get('date')
        )
        
        # Aggiungi il target se presente
        if 'target' in data and data['target']:
            step.target = Target.from_dict(data['target'])
        
        # Aggiungi gli step figli se presenti
        if 'workout_steps' in data and data['workout_steps']:
            for child_data in data['workout_steps']:
                child_step = WorkoutStep.from_dict(child_data)
                step.add_step(child_step)
        
        return step
    
    def __repr__(self) -> str:
        return f"WorkoutStep({self.step_type}, {self.end_condition}={self.end_condition_value})"


class Workout:
    """Classe per gli allenamenti."""
    
    def __init__(self, sport_type: str, workout_name: str, description: str = ""):
        """
        Inizializza un allenamento.
        
        Args:
            sport_type: Tipo di sport (running, cycling, swimming, ...)
            workout_name: Nome dell'allenamento
            description: Descrizione dell'allenamento
        """
        self.sport_type = sport_type
        self.workout_name = workout_name
        self.description = description
        self.workout_steps = []
    
    def add_step(self, step: WorkoutStep) -> None:
        """
        Aggiunge uno step all'allenamento.
        
        Args:
            step: Step da aggiungere
        """
        # Aggiorna l'ordine se non è un ripetizione (già con ordine e step figli)
        if not step.workout_steps:
            step.order = len(self.workout_steps)
        
        # Imposta il tipo di sport
        step.sport_type = self.sport_type
        
        # Imposta il tipo di sport anche per gli step figli
        for child_step in step.workout_steps:
            child_step.sport_type = self.sport_type
        
        # Aggiungi lo step
        self.workout_steps.append(step)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte l'allenamento in un dizionario.
        
        Returns:
            Dizionario con i dati dell'allenamento
        """
        return {
            'sport_type': self.sport_type,
            'workout_name': self.workout_name,
            'description': self.description,
            'workout_steps': [step.to_dict() for step in self.workout_steps]
        }


    def garminconnect_json(self) -> Dict[str, Any]:
        """
        Converte l'allenamento in formato JSON per Garmin Connect.
        
        Returns:
            Dizionario JSON per l'API di Garmin Connect
        """
        # Ottieni gli sport_type_id mappati correttamente
        sport_type_id = self._get_sport_type_id(self.sport_type)
        
        # Filtra gli step di data
        steps = [s for s in self.workout_steps if not (hasattr(s, 'date') and s.date)]
        
        # Formato JSON da inviare a Garmin Connect
        workout_json = {
            "sportType": {
                "sportTypeId": sport_type_id,
                "sportTypeKey": self.sport_type
            },
            "workoutName": self.workout_name,
            "description": self.description or "",
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {
                        "sportTypeId": sport_type_id,
                        "sportTypeKey": self.sport_type
                    },
                    "workoutSteps": [step.garminconnect_json() for step in steps]
                }
            ]
        }
        
        return workout_json

    def _get_sport_type_id(self, sport_type: str) -> int:
        """
        Converte il tipo di sport in un ID numerico per Garmin Connect.
        
        Args:
            sport_type: Tipo di sport
            
        Returns:
            ID del tipo di sport
        """
        sport_type_ids = {
            "running": 1,
            "cycling": 2,
            "swimming": 5,
            "fitness_equipment": 4,
            "other": 3
        }
        return sport_type_ids.get(sport_type.lower(), 3)  # Default: other


    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workout':
        """
        Crea un allenamento da un dizionario.
        
        Args:
            data: Dizionario con i dati dell'allenamento
            
        Returns:
            Allenamento creato
        """
        # Crea l'allenamento
        workout = cls(
            sport_type=data.get('sport_type', ''),
            workout_name=data.get('workout_name', ''),
            description=data.get('description', '')
        )
        
        # Aggiungi gli step
        if 'workout_steps' in data and data['workout_steps']:
            for step_data in data['workout_steps']:
                step = WorkoutStep.from_dict(step_data)
                workout.add_step(step)
        
        return workout
    
    def __repr__(self) -> str:
        return f"Workout({self.workout_name}, {self.sport_type}, {len(self.workout_steps)} steps)"


def create_workout_from_yaml(yaml_data: Dict[str, Any], workout_name: str) -> Workout:
    """
    Crea un allenamento da dati YAML.
    
    Args:
        yaml_data: Dati YAML
        workout_name: Nome dell'allenamento
        
    Returns:
        Allenamento creato
        
    Raises:
        ValueError: Se i dati non sono validi
    """
    try:
        # Ottieni i dati dell'allenamento
        workout_data = yaml_data.get(workout_name)
        
        if not workout_data or not isinstance(workout_data, list):
            raise ValueError(f"Dati non validi per l'allenamento '{workout_name}'")
        
        # Tipo di sport
        sport_type = "running"  # Default
        
        # Trova lo step sport_type
        for step in workout_data:
            if 'sport_type' in step:
                sport_type = step.get('sport_type', 'running')
                break
        
        # Crea l'allenamento
        workout = Workout(sport_type, workout_name)
        
        # Processa gli step
        for item in workout_data:
            # Skip sport_type (già processato)
            if 'sport_type' in item:
                continue
            
            # Cerca attributi speciali
            if 'date' in item:
                # Crea uno step speciale con la data
                date_step = WorkoutStep(0, "warmup")
                date_step.date = item['date']
                workout.add_step(date_step)
                continue
            
            # Processa gli step normali
            for step_type, value in item.items():
                if step_type == 'repeat':
                    # Crea un gruppo di ripetizioni
                    repeat_step = WorkoutStep(
                        order=0,
                        step_type='repeat',
                        end_condition='iterations',
                        end_condition_value=value
                    )
                    
                    # Aggiungi gli step figli
                    steps = item.get('steps', [])
                    for child_item in steps:
                        for child_type, child_value in child_item.items():
                            if child_type in ['warmup', 'cooldown', 'interval', 'recovery', 'rest', 'other']:
                                # Crea lo step figlio
                                child_step = parse_step(child_type, child_value)
                                child_step.sport_type = sport_type
                                repeat_step.add_step(child_step)
                    
                    # Aggiungi il gruppo all'allenamento
                    workout.add_step(repeat_step)
                
                elif step_type in ['warmup', 'cooldown', 'interval', 'recovery', 'rest', 'other']:
                    # Crea lo step
                    step = parse_step(step_type, value)
                    step.sport_type = sport_type
                    workout.add_step(step)
        
        return workout
        
    except Exception as e:
        logging.error(f"Errore nella creazione dell'allenamento da YAML: {str(e)}")
        raise ValueError(f"Errore nella creazione dell'allenamento da YAML: {str(e)}")


def parse_step(step_type: str, value: str) -> WorkoutStep:
    """
    Analizza un valore di step dal YAML.
    
    Args:
        step_type: Tipo di step
        value: Valore dello step
        
    Returns:
        Step creato
        
    Raises:
        ValueError: Se il valore non è valido
    """
    # Importazione necessaria
    from config import get_config
    
    # Valori di default
    end_condition = "lap.button"
    end_condition_value = None
    target_type = "no.target"
    target_from = None
    target_to = None
    description = ""
    
    # Estrai la descrizione se presente
    if ' -- ' in value:
        value, description = value.split(' -- ', 1)
    
    # Variabile per tenere traccia del nome della zona
    yaml_target_zone = None
    
    # Estrai il target se presente
    if ' @ ' in value:
        value, target = value.split(' @ ', 1)
        
        # Salva il nome della zona originale per riferimento
        yaml_target_zone = target
        
        # Determina il tipo di target
        if target.startswith('Z') and '_HR' in target:
            # Zona di frequenza cardiaca (Z1_HR, Z2_HR, ecc.)
            target_type = "heart.rate.zone"
            
            # Ottieni i valori HR dalla configurazione
            app_config = get_config()
            heart_rates = app_config.get('heart_rates', {})
            max_hr = heart_rates.get('max_hr', 180)
            
            # Cerca la zona corrispondente
            if target in heart_rates:
                hr_range = heart_rates[target]
                
                if '-' in hr_range and 'max_hr' in hr_range:
                    # Formato: 62-76% max_hr
                    parts = hr_range.split('-')
                    min_percent = float(parts[0])
                    max_percent = float(parts[1].split('%')[0])
                    
                    # Converti in valori assoluti
                    target_from = int(min_percent * max_hr / 100)
                    target_to = int(max_percent * max_hr / 100)
            else:
                # Default se la zona non è trovata
                target_from = 120
                target_to = 140
        
        elif target.startswith('Z') or target in ['recovery', 'threshold', 'marathon', 'race_pace']:
            # Zona di passo (Z1, Z2, recovery, threshold, ecc.)
            target_type = "pace.zone"
            
            # Ottieni i valori del passo dalla configurazione
            app_config = get_config()
            paces = app_config.get('paces', {})
            
            # Cerca la zona corrispondente
            if target in paces:
                pace_range = paces[target]
                
                if '-' in pace_range:
                    # Formato: min:sec-min:sec
                    min_pace, max_pace = pace_range.split('-')
                    min_pace = min_pace.strip()
                    max_pace = max_pace.strip()
                else:
                    # Formato: min:sec (valore singolo)
                    min_pace = max_pace = pace_range.strip()
                
                # Converti da min:sec a secondi
                def pace_to_seconds(pace_str):
                    parts = pace_str.split(':')
                    return int(parts[0]) * 60 + int(parts[1])
                
                min_pace_secs = pace_to_seconds(min_pace)
                max_pace_secs = pace_to_seconds(max_pace)
                
                # Converti da secondi a m/s (inverti min e max)
                target_from = 1000 / max_pace_secs  # Passo più veloce
                target_to = 1000 / min_pace_secs    # Passo più lento
            else:
                # Default se la zona non è trovata
                target_from = 3.0  # ~5:30 min/km
                target_to = 2.5    # ~6:40 min/km
        
        elif target in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'recovery', 'threshold', 'sweet_spot']:
            # Zona di potenza (per ciclismo)
            target_type = "power.zone"
            
            # Ottieni i valori di potenza dalla configurazione
            app_config = get_config()
            power_values = app_config.get('power_values', {})
            
            # Cerca la zona corrispondente
            if target in power_values:
                power_range = power_values[target]
                
                if isinstance(power_range, str):
                    if '-' in power_range:
                        # Formato: N-N
                        min_power, max_power = power_range.split('-')
                        target_from = int(min_power.strip())
                        target_to = int(max_power.strip())
                    elif power_range.startswith('<'):
                        # Formato: <N
                        power_val = int(power_range[1:].strip())
                        target_from = 0
                        target_to = power_val
                    elif power_range.endswith('+'):
                        # Formato: N+
                        power_val = int(power_range[:-1].strip())
                        target_from = power_val
                        target_to = 9999  # Valore alto per "infinito"
                    else:
                        # Valore singolo
                        power_val = int(power_range.strip())
                        target_from = power_val
                        target_to = power_val
                else:
                    # Valore numerico
                    target_from = power_values[target]
                    target_to = power_values[target]
            else:
                # Default se la zona non è trovata
                target_from = 200
                target_to = 250
                
        elif '@hr' in target:
            # Frequenza cardiaca
            target_type = "heart.rate.zone"
            target = target.replace('@hr', '').strip()
            
            # Estrai i valori se è un intervallo
            if '-' in target:
                min_hr, max_hr = target.split('-')
                target_from = int(min_hr.strip())
                target_to = int(max_hr.strip().split(' ')[0])  # Rimuovi "bpm" se presente
            else:
                # Valore singolo
                hr_val = int(target.strip().split(' ')[0])  # Rimuovi "bpm" se presente
                target_from = hr_val
                target_to = hr_val
                
        elif '@pwr' in target:
            # Potenza
            target_type = "power.zone"
            target = target.replace('@pwr', '').strip()
            
            # Estrai i valori se è un intervallo
            if '-' in target:
                min_power, max_power = target.split('-')
                target_from = int(min_power.strip())
                target_to = int(max_power.strip().split(' ')[0])  # Rimuovi "W" se presente
            else:
                # Valore singolo
                power_val = int(target.strip().split(' ')[0])  # Rimuovi "W" se presente
                target_from = power_val
                target_to = power_val
        
        else:
            # Cerca di interpretare il target come un passo o un valore numerico
            target_type = "pace.zone"
            
            # Verifica se il formato è min:sec-min:sec
            if '-' in target and ':' in target:
                min_pace, max_pace = target.split('-')
                
                # Converti da min:sec a secondi
                def parse_pace(pace_str):
                    parts = pace_str.strip().split(':')
                    return int(parts[0]) * 60 + int(parts[1])
                
                try:
                    min_pace_secs = parse_pace(min_pace)
                    max_pace_secs = parse_pace(max_pace)
                    
                    # Converti da secondi a m/s (inverti min e max)
                    target_from = 1000 / max_pace_secs  # Passo più veloce
                    target_to = 1000 / min_pace_secs    # Passo più lento
                except (ValueError, IndexError):
                    # Default se non riesce a interpretare
                    target_from = 3.0  # ~5:30 min/km
                    target_to = 2.5    # ~6:40 min/km
            else:
                # Default se non è un formato riconoscibile
                target_from = 3.0
                target_to = 2.5
    
    # Analizza la condizione di fine
    if value == "lap-button":
        end_condition = "lap.button"
    elif value.endswith('min'):
        # Formato: Nmin o N:SSmin
        end_condition = "time"
        
        if ':' in value:
            # Formato: N:SSmin
            time_value = value[:-3]  # Rimuovi "min"
            try:
                minutes, seconds = time_value.split(':')
                end_condition_value = int(minutes) * 60 + int(seconds)  # Converti in secondi
            except (ValueError, IndexError):
                end_condition_value = 60  # Default: 1 minuto
        else:
            # Formato: Nmin
            try:
                minutes = int(value[:-3])
                end_condition_value = minutes * 60  # Secondi
            except ValueError:
                end_condition_value = 60  # Default: 1 minuto
    elif value.endswith('s'):
        # Formato: Ns
        end_condition = "time"
        try:
            end_condition_value = int(value[:-1])  # Secondi
        except ValueError:
            end_condition_value = 30  # Default: 30 secondi
    elif value.endswith('km'):
        # Formato: N.Nkm
        end_condition = "distance"
        try:
            end_condition_value = float(value[:-2]) * 1000  # Metri
        except ValueError:
            end_condition_value = 1000  # Default: 1 km
    elif value.endswith('m'):
        # Formato: Nm
        end_condition = "distance"
        try:
            end_condition_value = int(value[:-1])  # Metri
        except ValueError:
            end_condition_value = 100  # Default: 100 m
    
    # Crea il target
    target = Target(target_type, target_to, target_from)
    
    # Imposta il nome della zona
    if yaml_target_zone and yaml_target_zone in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z1_HR', 'Z2_HR', 'Z3_HR', 'Z4_HR', 'Z5_HR', 
                 'recovery', 'threshold', 'marathon', 'race_pace', 'sweet_spot', 'sprint']:
        target.target_zone_name = yaml_target_zone
    
    # Crea lo step
    step = WorkoutStep(
        order=0,
        step_type=step_type,
        description=description,
        end_condition=end_condition,
        end_condition_value=end_condition_value,
        target=target
    )
    
    # Salva il nome della zona originale come attributo temporaneo
    if yaml_target_zone:
        step.yaml_target_zone = yaml_target_zone
    
    return step