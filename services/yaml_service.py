#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servizio per la gestione dei file YAML.
"""

import logging
import re
import yaml
from typing import Dict, Any, List, Tuple, Optional

from models.workout import Workout, WorkoutStep, Target, create_workout_from_yaml


class YamlService:
    """Servizio per la gestione dei file YAML."""
    
    @staticmethod
    def load_yaml(file_path: str) -> Dict[str, Any]:
        """
        Carica un file YAML.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Dizionario con i dati del file
            
        Raises:
            IOError: Se il file non può essere letto
            yaml.YAMLError: Se il file non è un YAML valido
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Errore nel caricamento del file YAML: {str(e)}")
            raise
    
    @staticmethod
    def save_yaml(data: Dict[str, Any], file_path: str) -> None:
        """
        Salva un dizionario in un file YAML.
        
        Args:
            data: Dizionario da salvare
            file_path: Percorso del file
            
        Raises:
            IOError: Se il file non può essere scritto
            yaml.YAMLError: Se i dati non possono essere convertiti in YAML
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            logging.error(f"Errore nel salvataggio del file YAML: {str(e)}")
            raise
    
    @staticmethod
    def import_workouts(file_path: str) -> List[Tuple[str, Workout]]:
        """
        Importa allenamenti da un file YAML.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Lista di tuple (nome, allenamento)
            
        Raises:
            IOError: Se il file non può essere letto
            yaml.YAMLError: Se il file non è un YAML valido
            ValueError: Se il file non contiene allenamenti validi
        """
        try:
            # Carica il file
            yaml_data = YamlService.load_yaml(file_path)
            
            # Verifica che sia un dizionario
            if not isinstance(yaml_data, dict):
                raise ValueError("Il file YAML non contiene un dizionario")
            
            # Estrai la configurazione se presente
            config_data = yaml_data.pop('config', {})
            name_prefix = config_data.get('name_prefix', '')
            
            # Nomi speciali da ignorare
            ignore_keys = ['config', 'heart_rates', 'paces', 'margins']
            
            # Lista degli allenamenti importati
            imported_workouts = []
            
            # Per ogni sezione, crea un allenamento
            for name, steps in yaml_data.items():
                if name in ignore_keys:
                    continue
                
                # Se il nome comincia con il prefisso, usa solo la parte finale
                if name_prefix and name.startswith(name_prefix):
                    display_name = name[len(name_prefix):].strip()
                else:
                    display_name = name
                
                # Crea l'allenamento
                workout = create_workout_from_yaml(yaml_data, name)
                
                # Aggiungi alla lista
                imported_workouts.append((display_name, workout))
            
            return imported_workouts
            
        except Exception as e:
            logging.error(f"Errore nell'importazione degli allenamenti: {str(e)}")
            raise
    
    @staticmethod
    def export_workouts(workouts: List[Tuple[str, Workout]], file_path: str, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Esporta allenamenti in un file YAML.
        
        Args:
            workouts: Lista di tuple (nome, allenamento)
            file_path: Percorso del file
            config: Configurazione aggiuntiva (opzionale)
            
        Raises:
            IOError: Se il file non può essere scritto
            yaml.YAMLError: Se i dati non possono essere convertiti in YAML
        """
        try:
            # Crea il dizionario per il YAML
            yaml_data = {'config': config or {}}
            
            # Per ogni allenamento
            for name, workout in workouts:
                # Converti l'allenamento in steps per il YAML
                steps = YamlService.workout_to_yaml_steps(workout)
                
                # Aggiungi al dizionario
                yaml_data[name] = steps
            
            # Salva il file
            YamlService.save_yaml(yaml_data, file_path)
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione degli allenamenti: {str(e)}")
            raise
    
    @staticmethod
    def workout_to_yaml_steps(workout: Workout) -> List[Dict[str, Any]]:
        """
        Converte un allenamento in steps per il YAML.
        
        Args:
            workout: Allenamento da convertire
            
        Returns:
            Lista di steps nel formato YAML
        """
        # Lista degli steps
        steps = []
        
        # Aggiungi il tipo di sport come metadato
        steps.append({
            'sport_type': workout.sport_type
        })
        
        # Per ogni step dell'allenamento
        for step in workout.workout_steps:
            # Converti lo step
            yaml_step = YamlService.step_to_yaml(step)
            if yaml_step:
                steps.append(yaml_step)
        
        return steps
    
    @staticmethod
    def step_to_yaml(step: WorkoutStep) -> Optional[Dict[str, Any]]:
        """
        Converte uno step in formato YAML.
        
        Args:
            step: Step da convertire
            
        Returns:
            Step nel formato YAML o None se fallisce
        """
        try:
            # Caso speciale: repeat
            if step.step_type == 'repeat':
                # Crea un gruppo di ripetizioni
                repeat_steps = []
                
                # Per ogni step figlio
                for child_step in step.workout_steps:
                    # Converti lo step
                    yaml_child = YamlService.step_to_yaml(child_step)
                    if yaml_child:
                        repeat_steps.append(yaml_child)
                
                # Crea lo step ripetizione
                return {
                    f'repeat {step.end_condition_value}': repeat_steps
                }
            
            # Step normale
            value = ""
            
            # Formatta il valore in base alla condizione di fine
            if step.end_condition == 'lap.button':
                value = "lap-button"
            elif step.end_condition == 'time':
                # Formatta il tempo
                if isinstance(step.end_condition_value, str) and ":" in step.end_condition_value:
                    # Già nel formato mm:ss
                    value = step.end_condition_value
                elif isinstance(step.end_condition_value, (int, float)):
                    # Converti secondi in min per valori > 60s
                    seconds = int(step.end_condition_value)
                    if seconds >= 60:
                        value = f"{seconds // 60}min"
                    else:
                        value = f"{seconds}s"
                else:
                    value = str(step.end_condition_value)
            elif step.end_condition == 'distance':
                # Formatta la distanza
                if isinstance(step.end_condition_value, str):
                    value = step.end_condition_value
                elif isinstance(step.end_condition_value, (int, float)):
                    # Converti metri in m o km
                    if step.end_condition_value >= 1000:
                        value = f"{step.end_condition_value / 1000:.1f}km".replace('.0', '')
                    else:
                        value = f"{int(step.end_condition_value)}m"
                else:
                    value = str(step.end_condition_value)
            elif step.end_condition == 'iterations':
                value = str(step.end_condition_value)
            
            # Aggiungi il target se presente
            if step.target and step.target.target != 'no.target':
                if step.target.target == 'pace.zone' and step.target.from_value and step.target.to_value:
                    # Converti da m/s a min/km
                    min_pace_secs = int(1000 / step.target.from_value)
                    max_pace_secs = int(1000 / step.target.to_value)
                    
                    min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                    max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                    
                    if min_pace == max_pace:
                        value += f" @ {min_pace}"
                    else:
                        value += f" @ {min_pace}-{max_pace}"
                elif step.target.target == 'heart.rate.zone' and step.target.from_value and step.target.to_value:
                    value += f" @hr {step.target.from_value}-{step.target.to_value}"
                elif step.target.target == 'power.zone' and step.target.from_value and step.target.to_value:
                    value += f" @pwr {step.target.from_value}-{step.target.to_value}"
            
            # Aggiungi la descrizione se presente
            if step.description:
                value += f" -- {step.description}"
            
            # Crea lo step YAML
            return {step.step_type: value}
            
        except Exception as e:
            logging.error(f"Errore nella conversione dello step: {str(e)}")
            return None