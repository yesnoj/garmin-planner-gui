#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servizio per la gestione dei file YAML.
"""

import logging
import re
import yaml
from typing import Dict, Any, List, Tuple, Optional

from config import get_config  # Assicuriamoci che questa importazione sia a livello di file
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
        try:
            # Carica il file
            yaml_data = YamlService.load_yaml(file_path)
            
            # Verifica che sia un dizionario
            if not isinstance(yaml_data, dict):
                raise ValueError("Il file YAML non contiene un dizionario")
            
            # Estrai la configurazione se presente
            config_data = yaml_data.pop('config', {})
            name_prefix = config_data.get('name_prefix', '')
            
            # Ottieni istanza di configurazione
            app_config = get_config()
            
            # Importa i parametri di configurazione
            if 'athlete_name' in config_data:
                app_config.set('athlete_name', config_data['athlete_name'])
            
            if 'race_day' in config_data:
                app_config.set('planning.race_day', config_data['race_day'])
            
            if 'preferred_days' in config_data:
                # Converti in lista se è una stringa
                if isinstance(config_data['preferred_days'], str):
                    try:
                        import ast
                        days_list = ast.literal_eval(config_data['preferred_days'])
                        app_config.set('planning.preferred_days', days_list)
                    except:
                        pass
                elif isinstance(config_data['preferred_days'], (list, tuple)):
                    app_config.set('planning.preferred_days', list(config_data['preferred_days']))
            
            # Importa i margini
            if 'margins' in config_data:
                margins = config_data['margins']
                if 'faster' in margins:
                    app_config.set('sports.running.margins.faster', margins['faster'])
                    app_config.set('sports.swimming.margins.faster', margins['faster'])
                if 'slower' in margins:
                    app_config.set('sports.running.margins.slower', margins['slower'])
                    app_config.set('sports.swimming.margins.slower', margins['slower'])
                if 'power_up' in margins:
                    app_config.set('sports.cycling.margins.power_up', margins['power_up'])
                if 'power_down' in margins:
                    app_config.set('sports.cycling.margins.power_down', margins['power_down'])
                if 'hr_up' in margins:
                    app_config.set('hr_margins.hr_up', margins['hr_up'])
                if 'hr_down' in margins:
                    app_config.set('hr_margins.hr_down', margins['hr_down'])
            
            # Importa i parametri di heart_rates
            if 'heart_rates' in yaml_data:
                heart_rates = yaml_data.pop('heart_rates')
                for key, value in heart_rates.items():
                    app_config.set(f'heart_rates.{key}', value)
            
            # Importa i parametri di pace per la corsa
            if 'paces' in yaml_data:
                paces = yaml_data.pop('paces')
                for key, value in paces.items():
                    app_config.set(f'sports.running.paces.{key}', value)
            
            # Importa i parametri di power per il ciclismo
            if 'power_values' in yaml_data:
                power_values = yaml_data.pop('power_values')
                for key, value in power_values.items():
                    app_config.set(f'sports.cycling.power_values.{key}', value)
            
            # Importa i parametri di pace per il nuoto
            if 'swim_paces' in yaml_data:
                swim_paces = yaml_data.pop('swim_paces')
                for key, value in swim_paces.items():
                    app_config.set(f'sports.swimming.paces.{key}', value)
            
            # Salva le modifiche alla configurazione
            app_config.save()
            
            # Nomi speciali da ignorare 
            ignore_keys = ['config', 'paces', 'swim_paces', 'power_values', 'margins', 'athlete_name', 'heart_rates']
            
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
                
                # Assicurati che tutti gli step dell'allenamento abbiano correttamente il target_zone_name
                for step in workout.workout_steps:
                    if step.target and step.target.target != "no.target":
                        # Se lo step ha un target, verifica se possiamo ricavare il nome della zona dal YAML
                        if hasattr(step, 'yaml_target_zone') and step.yaml_target_zone:
                            step.target.target_zone_name = step.yaml_target_zone
                    
                    # Gestisci anche gli step ripetuti
                    if step.step_type == 'repeat' and step.workout_steps:
                        for child_step in step.workout_steps:
                            if child_step.target and child_step.target.target != "no.target":
                                if hasattr(child_step, 'yaml_target_zone') and child_step.yaml_target_zone:
                                    child_step.target.target_zone_name = child_step.yaml_target_zone
                
                # Aggiungi alla lista
                imported_workouts.append((display_name, workout))
            
            return imported_workouts
            
        except Exception as e:
            logging.error(f"Errore nell'importazione degli allenamenti: {str(e)}")
            raise

    @staticmethod
    def export_workouts(workouts: List[Tuple[str, Workout]], file_path: str, config: Optional[Dict[str, Any]] = None) -> None:
        try:
            # Ottieni le impostazioni complete di configurazione
            app_config = get_config()
            
            # Crea il dizionario per il YAML
            yaml_data = {'config': config or {}}
            
            # Aggiungi informazioni complete nella configurazione
            yaml_data['config'].update({
                'margins': {
                    'faster': app_config.get('sports.running.margins.faster', '0:05'),
                    'slower': app_config.get('sports.running.margins.slower', '0:05'),
                    'power_up': app_config.get('sports.cycling.margins.power_up', 10),
                    'power_down': app_config.get('sports.cycling.margins.power_down', 10),
                    'hr_up': app_config.get('hr_margins.hr_up', 5),
                    'hr_down': app_config.get('hr_margins.hr_down', 5),
                },
                'athlete_name': app_config.get('athlete_name', ''),
                'race_day': app_config.get('planning.race_day', ''),
                'preferred_days': str(app_config.get('planning.preferred_days', [1, 3, 5])),
            })
            
            # Aggiungi heart_rates al livello principale
            yaml_data['heart_rates'] = {}
            heart_rates = app_config.get('heart_rates', {})
            for name, value in heart_rates.items():
                yaml_data['heart_rates'][name] = value
            
            # Aggiungi i paces, swim_paces e power_values
            yaml_data['paces'] = app_config.get('sports.running.paces', {})
            yaml_data['swim_paces'] = app_config.get('sports.swimming.paces', {})
            yaml_data['power_values'] = app_config.get('sports.cycling.power_values', {})
            
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
        
        # Per ogni step dell'allenamento, trova la data se presente
        date_step = None
        for step in workout.workout_steps:
            if hasattr(step, 'date') and step.date:
                date_step = {
                    'date': step.date
                }
                break
        
        # Aggiungi la data se trovata
        if date_step:
            steps.append(date_step)
        
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
                    'repeat': step.end_condition_value,
                    'steps': repeat_steps
                }
            
            # Skip date step (handled separately)
            if hasattr(step, 'date') and step.date:
                return None
                
            # Step normale
            value = ""
            
            # Formatta il valore in base alla condizione di fine
            if step.end_condition == 'lap.button':
                value = "lap-button"
            elif step.end_condition == 'time':
                # Formatta il tempo MANTENENDO I SECONDI
                if isinstance(step.end_condition_value, str) and ":" in step.end_condition_value:
                    # Già nel formato mm:ss - MANTIENI IL FORMATO ORIGINALE
                    min_sec = step.end_condition_value.split(':')
                    minutes = int(min_sec[0])
                    seconds = int(min_sec[1]) if len(min_sec) > 1 else 0
                    
                    if seconds > 0:
                        value = f"{minutes}:{seconds:02d}min"  # Formato mm:ssmin
                    else:
                        value = f"{minutes}min"
                elif isinstance(step.end_condition_value, (int, float)):
                    # Converti secondi in mm:ss per valori > 60s
                    seconds = int(step.end_condition_value)
                    if seconds >= 60:
                        minutes = seconds // 60
                        remaining_seconds = seconds % 60
                        
                        if remaining_seconds > 0:
                            value = f"{minutes}:{remaining_seconds:02d}min"  # Formato mm:ssmin
                        else:
                            value = f"{minutes}min"
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
                # Determina il tipo di sport per scegliere il set di zone
                sport_type = step.sport_type if hasattr(step, "sport_type") else "running"
                
                # Verifica se è presente la zona memorizzata
                # Questo è un campo che potrebbe non essere presente in versioni precedenti
                if hasattr(step.target, 'target_zone_name') and step.target.target_zone_name:
                    value += f" @ {step.target.target_zone_name}"
                
                # Altrimenti, usa un approccio drastico basato sui valori numerici
                else:
                    # Ottieni i valori target
                    has_values = False
                    
                    if step.target.target == 'heart.rate.zone' and step.target.from_value and step.target.to_value:
                        from_value = int(step.target.from_value)
                        to_value = int(step.target.to_value)
                        has_values = True
                        
                        # Usa una mappatura diretta per zone HR (approccio drastico)
                        HR_ZONE_RANGES = {
                            'Z1_HR': (100, 140),  # Approx 55-75% of max HR
                            'Z2_HR': (135, 155),  # Approx 75-85% of max HR
                            'Z3_HR': (150, 165),  # Approx 85-90% of max HR
                            'Z4_HR': (165, 175),  # Approx 90-95% of max HR
                            'Z5_HR': (170, 190)   # Approx 95-100% of max HR
                        }
                        
                        # Trova la zona più vicina
                        avg_value = (from_value + to_value) / 2
                        closest_zone = None
                        closest_diff = float('inf')
                        
                        for zone_name, (zone_min, zone_max) in HR_ZONE_RANGES.items():
                            zone_avg = (zone_min + zone_max) / 2
                            diff = abs(avg_value - zone_avg)
                            
                            if diff < closest_diff:
                                closest_diff = diff
                                closest_zone = zone_name
                        
                        if closest_zone:
                            value += f" @ {closest_zone}"
                        else:
                            value += f" @ {from_value}-{to_value} bpm"
                    
                    elif step.target.target == 'pace.zone' and step.target.from_value and step.target.to_value:
                        # Converti da m/s a min/km
                        from_pace_secs = 1000.0 / step.target.from_value
                        to_pace_secs = 1000.0 / step.target.to_value
                        has_values = True
                        
                        # Formatta per la visualizzazione
                        from_pace_mins = int(from_pace_secs / 60)
                        from_pace_s = round(from_pace_secs % 60)
                        if from_pace_s == 60:
                            from_pace_mins += 1
                            from_pace_s = 0
                            
                        to_pace_mins = int(to_pace_secs / 60)
                        to_pace_s = round(to_pace_secs % 60)
                        if to_pace_s == 60:
                            to_pace_mins += 1
                            to_pace_s = 0
                        
                        # Assicurati di avere l'ordine corretto (più veloce -> più lento)
                        if from_pace_secs > to_pace_secs:
                            from_pace_secs, to_pace_secs = to_pace_secs, from_pace_secs
                            from_pace_mins, to_pace_mins = to_pace_mins, from_pace_mins
                            from_pace_s, to_pace_s = to_pace_s, from_pace_s
                        
                        # Mappatura diretta per zone di passo
                        if sport_type == "running":
                            # Valori approssimativi per le zone in min/km
                            PACE_ZONE_RANGES = {
                                'Z1': (6, 7),       # Zona di recupero facile
                                'Z2': (5.5, 6.5),   # Zona aerobica
                                'Z3': (5, 6),       # Zona tempo 
                                'Z4': (4.5, 5.5),   # Zona soglia
                                'Z5': (4, 5),       # Zona VO2max
                                'recovery': (6.5, 7.5),
                                'threshold': (4.7, 5.3),
                                'marathon': (5, 5.5),
                                'race_pace': (4.5, 5)
                            }
                        elif sport_type == "swimming":
                            # Valori per nuoto in min/100m
                            PACE_ZONE_RANGES = {
                                'Z1': (2, 2.5),  
                                'Z2': (1.8, 2.2),
                                'Z3': (1.7, 2),
                                'Z4': (1.5, 1.8),
                                'Z5': (1.3, 1.6),
                                'recovery': (2.3, 2.7),
                                'threshold': (1.8, 2),
                                'sprint': (1.2, 1.5)
                            }
                        else:
                            # Default a running se non riconosciuto
                            PACE_ZONE_RANGES = {
                                'Z1': (6, 7),
                                'Z2': (5.5, 6.5),
                                'Z3': (5, 6),
                                'Z4': (4.5, 5.5),
                                'Z5': (4, 5)
                            }
                        
                        # Trova la zona più vicina
                        avg_pace_mins = (from_pace_mins + to_pace_mins) / 2
                        avg_pace_s = (from_pace_s + to_pace_s) / 2
                        avg_pace = avg_pace_mins + (avg_pace_s / 60)
                        
                        closest_zone = None
                        closest_diff = float('inf')
                        
                        for zone_name, (zone_min, zone_max) in PACE_ZONE_RANGES.items():
                            zone_avg = (zone_min + zone_max) / 2
                            diff = abs(avg_pace - zone_avg)
                            
                            if diff < closest_diff:
                                closest_diff = diff
                                closest_zone = zone_name
                        
                        if closest_zone:
                            value += f" @ {closest_zone}"
                        else:
                            from_pace = f"{from_pace_mins}:{from_pace_s:02d}"
                            to_pace = f"{to_pace_mins}:{to_pace_s:02d}"
                            value += f" @ {from_pace}-{to_pace}"
                    
                    elif step.target.target == 'power.zone' and step.target.from_value and step.target.to_value:
                        from_value = int(step.target.from_value)
                        to_value = int(step.target.to_value)
                        has_values = True
                        
                        # Assicurati di avere l'ordine corretto
                        if from_value > to_value:
                            from_value, to_value = to_value, from_value
                        
                        # Usare una mappatura diretta per zone di potenza
                        # Basata su zone FTP tipiche
                        POWER_ZONE_RANGES = {
                            'Z1': (100, 175),       # 40-70% FTP - Recupero attivo
                            'Z2': (175, 215),       # 70-85% FTP - Endurance
                            'Z3': (215, 250),       # 85-100% FTP - Tempo
                            'Z4': (250, 300),       # 100-120% FTP - Soglia/VO2
                            'Z5': (300, 375),       # 120-150% FTP - VO2max/Anaerobico
                            'Z6': (375, 450),       # 150%+ FTP - Anaerobico/Neuromuscolare
                            'recovery': (0, 125),   # <50% FTP 
                            'threshold': (235, 265), # 95-105% FTP
                            'sweet_spot': (220, 235) # 88-94% FTP
                        }
                        
                        # Trova la zona più vicina
                        avg_value = (from_value + to_value) / 2
                        closest_zone = None
                        closest_diff = float('inf')
                        
                        for zone_name, (zone_min, zone_max) in POWER_ZONE_RANGES.items():
                            zone_avg = (zone_min + zone_max) / 2
                            diff = abs(avg_value - zone_avg)
                            
                            if diff < closest_diff:
                                closest_diff = diff
                                closest_zone = zone_name
                        
                        if closest_zone:
                            value += f" @ {closest_zone}"
                        else:
                            value += f" @ {from_value}-{to_value}W"
                    
                    elif not has_values:
                        # Caso generico se non abbiamo valori
                        value += " @ Z2"  # Default generico
            
            # Aggiungi la descrizione se presente
            if step.description:
                value += f" -- {step.description}"
            
            # Crea lo step YAML
            return {step.step_type: value}
            
        except Exception as e:
            logging.error(f"Errore nella conversione dello step: {str(e)}")
            return None


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
        
        # Estrai il target se presente
        if ' @ ' in value:
            value, target = value.split(' @ ', 1)
            
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
        # Aggiungi il nome della zona se riconosciuto
        if ' @ ' in value:
            _, zone_name = value.split(' @ ', 1)
            if zone_name in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z1_HR', 'Z2_HR', 'Z3_HR', 'Z4_HR', 'Z5_HR', 
                             'recovery', 'threshold', 'marathon', 'race_pace', 'sweet_spot', 'sprint']:
                if hasattr(target, 'target_zone_name'):
                    target.target_zone_name = zone_name
        
        # Crea lo step
        step = WorkoutStep(
            order=0,
            step_type=step_type,
            description=description,
            end_condition=end_condition,
            end_condition_value=end_condition_value,
            target=target
        )
        
        return step