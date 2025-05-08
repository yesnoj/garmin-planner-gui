#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modello per gli allenamenti.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union, Tuple

# Tipi di sport supportati
SPORT_TYPES = {
    "running": 1,
    "cycling": 2,
    "swimming": 4,
}

# Tipi di step
STEP_TYPES = {
    "warmup": 1,
    "cooldown": 2,
    "interval": 3,
    "recovery": 4,
    "rest": 5,
    "repeat": 6,
    "other": 7
}

# Condizioni di fine
END_CONDITIONS = {
    "lap.button": 1,
    "time": 2,
    "distance": 3,
    "iterations": 7,
}

# Tipi di target
TARGET_TYPES = {
    "no.target": 1,
    "power.zone": 2,
    "cadence.zone": 3,
    "heart.rate.zone": 4,
    "speed.zone": 5,
    "pace.zone": 6,  # metri al secondo
}


class Workout:
    """
    Rappresenta un allenamento.
    """
    
    def __init__(self, sport_type: str, name: str, description: Optional[str] = None):
        """
        Inizializza un allenamento.
        
        Args:
            sport_type: Tipo di sport (running, cycling, swimming)
            name: Nome dell'allenamento
            description: Descrizione dell'allenamento (opzionale)
        """
        self.sport_type = sport_type
        self.workout_name = name
        self.description = description
        self.workout_steps = []
    
    def add_step(self, step: 'WorkoutStep') -> None:
        """
        Aggiunge uno step all'allenamento.
        
        Args:
            step: Step da aggiungere
        """
        if step.order == 0:
            step.order = len(self.workout_steps) + 1
        self.workout_steps.append(step)
    
    def dist_to_time(self) -> None:
        """
        Converte gli step con condizione di fine distanza e target passo in condizione di fine tempo.
        
        Questa conversione è utile per gli allenamenti su tapis roulant, dove è difficile stimare il passo.
        """
        for ws in self.workout_steps:
            ws.dist_to_time()
    
    def garminconnect_json(self) -> Dict[str, Any]:
        """
        Converte l'allenamento in formato JSON per Garmin Connect.
        
        Returns:
            Dizionario con l'allenamento in formato JSON
        """
        return {
            "sportType": {
                "sportTypeId": SPORT_TYPES[self.sport_type],
                "sportTypeKey": self.sport_type,
            },
            "workoutName": self.workout_name,
            "description": self.description,
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {
                        "sportTypeId": SPORT_TYPES[self.sport_type],
                        "sportTypeKey": self.sport_type,
                    },
                    "workoutSteps": [step.garminconnect_json() for step in self.workout_steps],
                }
            ],
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte l'allenamento in un dizionario per l'importazione/esportazione.
        
        Returns:
            Dizionario con l'allenamento
        """
        return {
            "sport_type": self.sport_type,
            "name": self.workout_name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.workout_steps]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workout':
        """
        Crea un allenamento da un dizionario.
        
        Args:
            data: Dizionario con i dati dell'allenamento
            
        Returns:
            Istanza di Workout
        """
        sport_type = data.get('sport_type', 'running')
        name = data.get('name', 'Allenamento')
        description = data.get('description')
        
        workout = cls(sport_type, name, description)
        
        for step_data in data.get('steps', []):
            step = WorkoutStep.from_dict(step_data)
            workout.add_step(step)
        
        return workout


class WorkoutStep:
    """
    Rappresenta uno step di allenamento.
    """
    
    def __init__(
        self,
        order: int,
        step_type: str,
        description: str = '',
        end_condition: str = "lap.button",
        end_condition_value: Optional[Union[str, int]] = None,
        target: Optional['Target'] = None,
    ):
        """
        Inizializza uno step di allenamento.
        
        Args:
            order: Ordine dello step nell'allenamento
            step_type: Tipo di step (warmup, cooldown, interval, recovery, rest, repeat, other)
            description: Descrizione dello step
            end_condition: Condizione di fine (lap.button, time, distance, iterations)
            end_condition_value: Valore della condizione di fine
            target: Target dello step (opzionale)
        """
        """Valid end condition values:
        - distance: '2.0km', '1.125km', '1.6km'
        - time: 0:40, 4:20
        - lap.button
        """
        self.order = order
        self.step_type = step_type
        self.description = description
        self.end_condition = end_condition
        self.end_condition_value = end_condition_value
        self.target = target or Target()
        self.child_step_id = 1 if self.step_type == 'repeat' else None
        self.workout_steps = []
    
    def add_step(self, step: 'WorkoutStep') -> None:
        """
        Aggiunge uno step figlio (per gli step di tipo repeat).
        
        Args:
            step: Step figlio da aggiungere
        """
        step.child_step_id = self.child_step_id
        if step.order == 0:
            step.order = len(self.workout_steps) + 1
        self.workout_steps.append(step)
    
    def end_condition_unit(self) -> Optional[Dict[str, str]]:
        """
        Restituisce l'unità della condizione di fine.
        
        Returns:
            Dizionario con l'unità o None
        """
        if self.end_condition and self.end_condition == "distance":
            if isinstance(self.end_condition_value, str) and self.end_condition_value.endswith("km"):
                return {"unitKey": "kilometer"}
            else:
                return {"unitKey": "meter"}
        return None
    
    def parsed_end_condition_value(self) -> Optional[Union[int, float]]:
        """
        Analizza il valore della condizione di fine.
        
        Returns:
            Valore analizzato o None
        """
        if self.end_condition == 'distance':
            # Formato distanza: '2.0km', '1.125km', '1.6km'
            if isinstance(self.end_condition_value, str):
                if self.end_condition_value.endswith("km"):
                    dist_str = self.end_condition_value.replace("km", "")
                    try:
                        return int(float(dist_str) * 1000)
                    except ValueError:
                        pass
                elif self.end_condition_value.endswith("m"):
                    dist_str = self.end_condition_value.replace("m", "")
                    try:
                        return int(float(dist_str))
                    except ValueError:
                        pass
            # Già convertito in numero
            elif isinstance(self.end_condition_value, (int, float)):
                return int(self.end_condition_value)
        
        elif self.end_condition == 'time':
            # Formato tempo: '0:40', '4:20'
            if isinstance(self.end_condition_value, str) and ":" in self.end_condition_value:
                parts = self.end_condition_value.split(":")
                if len(parts) == 2:
                    try:
                        minutes = int(parts[0])
                        seconds = int(parts[1])
                        return minutes * 60 + seconds
                    except ValueError:
                        pass
            # Già convertito in numero (secondi)
            elif isinstance(self.end_condition_value, (int, float)):
                return int(self.end_condition_value)
        
        elif self.end_condition == 'iterations':
            # Numero di iterazioni per gli step di tipo repeat
            if isinstance(self.end_condition_value, (int, float)):
                return int(self.end_condition_value)
            elif isinstance(self.end_condition_value, str) and self.end_condition_value.isdigit():
                return int(self.end_condition_value)
        
        # Default
        return self.end_condition_value
    
    def dist_to_time(self) -> None:
        """
        Converte lo step da condizione di fine distanza a condizione di fine tempo.
        
        Utile per gli allenamenti su tapis roulant, dove è difficile stimare il passo.
        """
        if self.end_condition == 'distance' and self.target.target == 'pace.zone':
            # Calcola il passo medio target
            target_pace_ms = (self.target.from_value + self.target.to_value) / 2
            if target_pace_ms == 0:
                return
            
            # Calcola il tempo necessario
            distance_m = self.parsed_end_condition_value()
            if distance_m is None:
                return
            
            end_condition_sec = int(distance_m / target_pace_ms)
            
            # Arrotonda a 10 secondi
            end_condition_sec = int(round(end_condition_sec / 10) * 10)
            
            # Aggiorna lo step
            self.end_condition = 'time'
            self.end_condition_value = str(end_condition_sec)
            
        elif self.end_condition == 'iterations' and self.workout_steps:
            # Converti tutti gli step figli
            for ws in self.workout_steps:
                ws.dist_to_time()
    
    def garminconnect_json(self) -> Dict[str, Any]:
        """
        Converte lo step in formato JSON per Garmin Connect.
        
        Returns:
            Dizionario con lo step in formato JSON
        """
        base_json = {
            "type": 'RepeatGroupDTO' if self.step_type == 'repeat' else 'ExecutableStepDTO',
            "stepId": None,
            "stepOrder": self.order,
            "childStepId": self.child_step_id,
            "stepType": {
                "stepTypeId": STEP_TYPES[self.step_type],
                "stepTypeKey": self.step_type,
            },
            "endCondition": {
                "conditionTypeKey": self.end_condition,
                "conditionTypeId": END_CONDITIONS[self.end_condition],
            },
            "endConditionValue": self.parsed_end_condition_value(),
        }
        
        if self.workout_steps:
            base_json["workoutSteps"] = [step.garminconnect_json() for step in self.workout_steps]
        
        if self.step_type == 'repeat':
            base_json['smartRepeat'] = True
            base_json['numberOfIterations'] = self.end_condition_value
        else:
            base_json.update({
                "description": self.description,
                "preferredEndConditionUnit": self.end_condition_unit(),
                "endConditionCompare": None,
                "endConditionZone": None,
                **self.target.garminconnect_json(),
            })
        
        return base_json
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte lo step in un dizionario per l'importazione/esportazione.
        
        Returns:
            Dizionario con lo step
        """
        result = {
            "order": self.order,
            "step_type": self.step_type,
            "description": self.description,
            "end_condition": self.end_condition,
            "end_condition_value": self.end_condition_value,
        }
        
        if self.target and self.target.target != "no.target":
            result["target"] = self.target.to_dict()
        
        if self.workout_steps:
            result["steps"] = [step.to_dict() for step in self.workout_steps]
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkoutStep':
        """
        Crea uno step da un dizionario.
        
        Args:
            data: Dizionario con i dati dello step
            
        Returns:
            Istanza di WorkoutStep
        """
        order = data.get('order', 0)
        step_type = data.get('step_type', 'other')
        description = data.get('description', '')
        end_condition = data.get('end_condition', 'lap.button')
        end_condition_value = data.get('end_condition_value')
        
        # Crea lo step
        step = cls(
            order=order,
            step_type=step_type,
            description=description,
            end_condition=end_condition,
            end_condition_value=end_condition_value
        )
        
        # Aggiungi il target se presente
        if 'target' in data:
            step.target = Target.from_dict(data['target'])
        
        # Aggiungi gli step figli se presenti
        for child_data in data.get('steps', []):
            child_step = cls.from_dict(child_data)
            step.add_step(child_step)
        
        return step


class Target:
    """
    Rappresenta un target per uno step.
    """
    
    def __init__(
        self,
        target: str = "no.target",
        to_value: Optional[Union[int, float]] = None,
        from_value: Optional[Union[int, float]] = None,
        zone: Optional[int] = None
    ):
        """
        Inizializza un target.
        
        Args:
            target: Tipo di target (no.target, power.zone, cadence.zone, heart.rate.zone, speed.zone, pace.zone)
            to_value: Valore massimo del target
            from_value: Valore minimo del target
            zone: Numero di zona
        """
        self.target = target
        self.to_value = to_value
        self.from_value = from_value
        self.zone = zone
    
    def garminconnect_json(self) -> Dict[str, Any]:
        """
        Converte il target in formato JSON per Garmin Connect.
        
        Returns:
            Dizionario con il target in formato JSON
        """
        return {
            "targetType": {
                "workoutTargetTypeId": TARGET_TYPES[self.target],
                "workoutTargetTypeKey": self.target,
            },
            "targetValueOne": self.to_value,
            "targetValueTwo": self.from_value,
            "zoneNumber": self.zone,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il target in un dizionario per l'importazione/esportazione.
        
        Returns:
            Dizionario con il target
        """
        result = {
            "target": self.target
        }
        
        if self.to_value is not None:
            result["to_value"] = self.to_value
        
        if self.from_value is not None:
            result["from_value"] = self.from_value
        
        if self.zone is not None:
            result["zone"] = self.zone
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Target':
        """
        Crea un target da un dizionario.
        
        Args:
            data: Dizionario con i dati del target
            
        Returns:
            Istanza di Target
        """
        target = data.get('target', 'no.target')
        to_value = data.get('to_value')
        from_value = data.get('from_value')
        zone = data.get('zone')
        
        return cls(
            target=target,
            to_value=to_value,
            from_value=from_value,
            zone=zone
        )


def seconds_to_mmss(seconds: int) -> str:
    """
    Converte un tempo in secondi in formato mm:ss.
    
    Args:
        seconds: Tempo in secondi
        
    Returns:
        Tempo in formato mm:ss
    """
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


def hhmmss_to_seconds(time_str: str) -> int:
    """
    Converte un tempo in formato mm:ss o hh:mm:ss in secondi.
    
    Args:
        time_str: Tempo in formato mm:ss o hh:mm:ss
        
    Returns:
        Tempo in secondi
        
    Raises:
        ValueError: Se il formato non è valido
    """
    parts = time_str.split(':')
    
    if len(parts) == 2:
        # Formato mm:ss
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        except ValueError:
            raise ValueError(f"Formato non valido per mm:ss: {time_str}")
            
    elif len(parts) == 3:
        # Formato hh:mm:ss
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            raise ValueError(f"Formato non valido per hh:mm:ss: {time_str}")
            
    else:
        raise ValueError(f"Formato non valido per il tempo: {time_str}")


def parse_yaml_workout(workout_data: Dict[str, Any], name: str) -> Workout:
    """
    Analizza un allenamento dal formato YAML importato.
    
    Args:
        workout_data: Dati dell'allenamento dal YAML
        name: Nome dell'allenamento
        
    Returns:
        Istanza di Workout
    """
    # Estrai il tipo di sport
    sport_type = 'running'  # Default
    
    # Cerca metadati
    meta_steps = []
    regular_steps = []
    
    for step in workout_data:
        if isinstance(step, dict):
            if 'sport_type' in step:
                sport_type = step['sport_type']
                meta_steps.append(step)
            elif 'date' in step:
                meta_steps.append(step)
            else:
                regular_steps.append(step)
    
    # Crea l'allenamento
    workout = Workout(sport_type, name)
    
    # Aggiungi gli step
    for step in regular_steps:
        workout_step = parse_step(step)
        if workout_step:
            workout.add_step(workout_step)
    
    return workout


def parse_step(step_data: Dict[str, Any]) -> Optional[WorkoutStep]:
    """
    Analizza uno step dal formato YAML importato.
    
    Args:
        step_data: Dati dello step dal YAML
        
    Returns:
        Istanza di WorkoutStep o None
    """
    if not isinstance(step_data, dict):
        return None
    
    # Caso particolare: step di tipo repeat
    if 'repeat' in step_data and 'steps' in step_data:
        repeat_count = step_data['repeat']
        substeps = step_data['steps']
        
        repeat_step = WorkoutStep(
            order=0,
            step_type='repeat',
            end_condition='iterations',
            end_condition_value=repeat_count
        )
        
        for substep in substeps:
            sub = parse_step(substep)
            if sub:
                repeat_step.add_step(sub)
        
        return repeat_step
    
    # Step normale
    if len(step_data) != 1:
        return None
    
    step_type = list(step_data.keys())[0]
    step_value = step_data[step_type]
    
    # Estrai descrizione
    description = ''
    if ' -- ' in step_value:
        parts = step_value.split(' -- ', 1)
        step_value = parts[0]
        description = parts[1]
    
    # Estrai target
    target = None
    for target_type in [' @ ', ' @spd ', ' @hr ', ' @pwr ']:
        if target_type in step_value:
            parts = step_value.split(target_type, 1)
            step_value = parts[0]
            target_value = parts[1]
            
            if target_type == ' @ ':
                target = Target(target='pace.zone')  # Valori da impostare successivamente
            elif target_type == ' @spd ':
                target = Target(target='speed.zone')
            elif target_type == ' @hr ':
                target = Target(target='heart.rate.zone')
            elif target_type == ' @pwr ':
                target = Target(target='power.zone')
            
            break
    
    # Estrai condizione di fine e valore
    end_condition = 'lap.button'
    end_value = None
    
    # Formati possibili:
    # - 5min, 10s, 30min (tempo)
    # - 1000m, 5km (distanza)
    # - 5 (numero di ripetizioni)
    # - lap-button (pulsante lap)
    
    step_value = step_value.strip()
    
    if step_value == 'lap-button':
        end_condition = 'lap.button'
    elif re.match(r'^\d+$', step_value):
        end_condition = 'iterations'
        end_value = int(step_value)
    elif re.match(r'^\d+[ms]$', step_value) or re.match(r'^\d+min$', step_value):
        end_condition = 'time'
        
        if step_value.endswith('s'):
            end_value = step_value[:-1]  # Secondi
        elif step_value.endswith('m'):
            end_value = str(int(step_value[:-1]) * 60)  # Minuti in secondi
        elif step_value.endswith('min'):
            end_value = str(int(step_value[:-3]) * 60)  # Minuti in secondi
    elif re.match(r'^\d+:\d{2}$', step_value):
        end_condition = 'time'
        try:
            minutes, seconds = map(int, step_value.split(':'))
            end_value = str(minutes * 60 + seconds)  # mm:ss in secondi
        except ValueError:
            pass
    elif re.match(r'^\d+(?:\.\d+)?(?:m|km)$', step_value):
        end_condition = 'distance'
        end_value = step_value
    
    return WorkoutStep(
        order=0,
        step_type=step_type,
        description=description,
        end_condition=end_condition,
        end_condition_value=end_value,
        target=target
    )


def create_workout_from_yaml(yaml_data: Dict[str, List[Dict[str, Any]]], name: str) -> Workout:
    """
    Crea un allenamento dal formato YAML.
    
    Args:
        yaml_data: Dati dell'allenamento dal YAML
        name: Nome dell'allenamento
        
    Returns:
        Istanza di Workout
    """
    # Estrai gli step
    steps = yaml_data.get(name, [])
    
    return parse_yaml_workout(steps, name)


if __name__ == "__main__":
    # Test
    workout = Workout("running", "Test Workout", "Test description")
    
    # Aggiungi warmup
    warmup = WorkoutStep(1, "warmup", "Riscaldamento", "time", "10:00")
    workout.add_step(warmup)
    
    # Aggiungi un gruppo di ripetizioni
    repeat = WorkoutStep(2, "repeat", "Ripetizioni", "iterations", 5)
    
    # Aggiungi gli step all'interno del gruppo
    interval = WorkoutStep(1, "interval", "Intervallo", "distance", "400m", Target("pace.zone", 3.5, 3.3))
    repeat.add_step(interval)
    
    recovery = WorkoutStep(2, "recovery", "Recupero", "time", "1:00")
    repeat.add_step(recovery)
    
    workout.add_step(repeat)
    
    # Aggiungi cooldown
    cooldown = WorkoutStep(3, "cooldown", "Defaticamento", "time", "5:00")
    workout.add_step(cooldown)
    
    # Stampa il JSON per Garmin Connect
    import json
    print(json.dumps(workout.garminconnect_json(), indent=2))