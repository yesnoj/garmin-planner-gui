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
                # Usa il nuovo metodo replace_section per sostituire completamente la sezione
                heart_rates = yaml_data.pop('heart_rates')
                app_config.replace_section('heart_rates', heart_rates)
                
                # Log dei valori importati
                for key, value in heart_rates.items():
                    logging.info(f"Importato heart rate: {key} = {value}")
            
            # Importa i parametri di pace per la corsa
            if 'paces' in yaml_data:
                # Sostituisci completamente la sezione
                paces = yaml_data.pop('paces')
                app_config.replace_section('sports.running.paces', paces)
                
                # Log dei valori importati
                for key, value in paces.items():
                    logging.info(f"Importato running pace: {key} = {value}")
            
            # Importa i parametri di power per il ciclismo
            if 'power_values' in yaml_data:
                # Sostituisci completamente la sezione
                power_values = yaml_data.pop('power_values')
                app_config.replace_section('sports.cycling.power_values', power_values)
                
                # Log dei valori importati
                for key, value in power_values.items():
                    logging.info(f"Importato cycling power: {key} = {value}")
            
            # Importa i parametri di pace per il nuoto
            if 'swim_paces' in yaml_data:
                # Sostituisci completamente la sezione
                swim_paces = yaml_data.pop('swim_paces')
                app_config.replace_section('sports.swimming.paces', swim_paces)
                
                # Log dei valori importati
                for key, value in swim_paces.items():
                    logging.info(f"Importato swimming pace: {key} = {value}")
            
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
                'date_format': 'YYYY-MM-DD',  # Nota sul formato delle date utilizzato
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
        Converte un singolo step in formato YAML.
        
        Args:
            step: Step da convertire
            
        Returns:
            Dizionario con lo step in formato YAML
        """
        try:
            # Salta gli step con la data
            if hasattr(step, 'date') and step.date:
                return None
            
            # Gestione speciale per repeat
            if step.step_type == 'repeat':
                # Crea la struttura per il repeat
                repeat_data = {
                    'repeat': step.end_condition_value,
                    'steps': []
                }
                
                # Aggiungi gli step figli
                for child_step in step.workout_steps:
                    child_yaml = YamlService.step_to_yaml(child_step)
                    if child_yaml:
                        repeat_data['steps'].append(child_yaml)
                
                return repeat_data
            
            # Gestione per altri tipi di step
            else:
                # Formatta il valore
                value = ""
                
                # Condizione di fine
                if step.end_condition == 'lap.button':
                    value = "lap-button"
                elif step.end_condition == 'time':
                    # Formato tempo
                    if isinstance(step.end_condition_value, (int, float)):
                        seconds = int(step.end_condition_value)
                        if seconds >= 60:
                            minutes = seconds // 60
                            remaining_seconds = seconds % 60
                            if remaining_seconds == 0:
                                value = f"{minutes}min"
                            else:
                                value = f"{minutes}:{remaining_seconds:02d}min"
                        else:
                            value = f"{seconds}s"
                    else:
                        value = str(step.end_condition_value)
                elif step.end_condition == 'distance':
                    # Formato distanza
                    if isinstance(step.end_condition_value, (int, float)):
                        if step.end_condition_value >= 1000:
                            km = step.end_condition_value / 1000
                            # Rimuovi .0 se è un numero intero
                            if km == int(km):
                                value = f"{int(km)}km"
                            else:
                                value = f"{km:.1f}km"
                        else:
                            value = f"{int(step.end_condition_value)}m"
                    else:
                        value = str(step.end_condition_value)
                else:
                    # Altri tipi
                    value = str(step.end_condition_value) if step.end_condition_value else "lap-button"
                
                # Aggiungi il target
                if step.target and step.target.target != 'no.target':
                    # Verifica se abbiamo un nome di zona salvato
                    if hasattr(step.target, 'target_zone_name') and step.target.target_zone_name:
                        value += f" @ {step.target.target_zone_name}"
                    
                    # Altrimenti, genera il target dai valori
                    elif step.target.from_value is not None and step.target.to_value is not None:
                        from_value = step.target.from_value
                        to_value = step.target.to_value
                        
                        if step.target.target == 'heart.rate.zone':
                            # Frequenza cardiaca
                            if from_value == to_value:
                                value += f" @ {int(from_value)} bpm"
                            else:
                                value += f" @ {int(from_value)}-{int(to_value)} bpm"
                        
                        elif step.target.target == 'pace.zone':
                            # Passo
                            # Converti da m/s a min/km
                            from_pace_secs = int(1000 / from_value) if from_value > 0 else 0
                            to_pace_secs = int(1000 / to_value) if to_value > 0 else 0
                            
                            from_pace_mins = from_pace_secs // 60
                            from_pace_s = from_pace_secs % 60
                            
                            to_pace_mins = to_pace_secs // 60
                            to_pace_s = to_pace_secs % 60
                            
                            from_pace = f"{from_pace_mins}:{from_pace_s:02d}"
                            to_pace = f"{to_pace_mins}:{to_pace_s:02d}"
                            
                            # Se i passi sono uguali, è un passo singolo
                            if from_pace == to_pace:
                                value += f" @ {from_pace}"
                            else:
                                value += f" @ {from_pace}-{to_pace}"
                        
                        elif step.target.target == 'power.zone':
                            # Potenza
                            from_value = int(from_value)
                            to_value = int(to_value)
                            
                            # Gestione casi speciali
                            if from_value == 0 and to_value < 9999:
                                value += f" @ <{to_value}W"
                            elif from_value > 0 and to_value >= 9999:
                                value += f" @ {from_value}+W"
                            elif from_value == to_value:
                                value += f" @ {from_value}W"
                            else:
                                value += f" @ {from_value}-{to_value}W"
                
                # Aggiungi la descrizione se presente
                if step.description:
                    value += f" -- {step.description}"
                
                # Crea lo step YAML
                return {step.step_type: value}
                
        except Exception as e:
            logging.error(f"Errore nella conversione dello step: {str(e)}")
            return None

    @staticmethod
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
                
                # Ottieni i valori di passo dalla configurazione
                app_config = get_config()
                paces = app_config.get('sports.running.paces', {})
                
                # Cerca la zona corrispondente
                if target in paces:
                    pace_range = paces[target]
                    
                    if '-' in pace_range:
                        # Formato: min:sec-min:sec
                        min_pace, max_pace = pace_range.split('-')
                        
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
                        # Valore singolo
                        try:
                            pace_parts = pace_range.strip().split(':')
                            pace_secs = int(pace_parts[0]) * 60 + int(pace_parts[1])
                            # Per un valore singolo, usa lo stesso valore per from e to
                            target_from = 1000 / pace_secs
                            target_to = 1000 / pace_secs
                        except (ValueError, IndexError):
                            # Default se non riesce a interpretare
                            target_from = 3.0
                            target_to = 3.0
                else:
                    # Default se la zona non è trovata
                    target_from = 3.0  # ~5:30 min/km
                    target_to = 2.5    # ~6:40 min/km
            
            elif '-' in target and 'W' in target:
                # Range di potenza (es. 125-175W o 175+ W)
                target_type = "power.zone"
                
                # Rimuovi 'W' e spazi
                target_clean = target.replace('W', '').strip()
                
                if '+' in target_clean:
                    # Formato: 375+
                    power_val = int(target_clean.replace('+', '').strip())
                    target_from = power_val
                    target_to = 9999  # Valore molto alto per rappresentare +
                elif '<' in target_clean:
                    # Formato: <125
                    power_val = int(target_clean.replace('<', '').strip())
                    target_from = 0
                    target_to = power_val
                elif '-' in target_clean:
                    # Formato: 125-175
                    min_power, max_power = target_clean.split('-')
                    target_from = int(min_power.strip())
                    target_to = int(max_power.strip())
                else:
                    # Valore singolo
                    power_val = int(target_clean.strip())
                    target_from = power_val
                    target_to = power_val
            
            elif '-' in target and 'bpm' in target:
                # Range di frequenza cardiaca (es. 120-140 bpm)
                target_type = "heart.rate.zone"
                
                # Rimuovi 'bpm' e spazi
                target_clean = target.replace('bpm', '').strip()
                
                # Estrai i valori se è un intervallo
                if '-' in target_clean:
                    min_hr, max_hr = target_clean.split('-')
                    target_from = int(min_hr.strip())
                    target_to = int(max_hr.strip())
                else:
                    # Valore singolo
                    hr_val = int(target_clean.strip())
                    target_from = hr_val
                    target_to = hr_val
            
            elif 'W' in target:
                # Potenza singola o range (es. 250W)
                target_type = "power.zone"
                
                # Rimuovi 'W' e spazi
                target_clean = target.replace('W', '').strip()
                
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
                # Cerca di interpretare il target come un passo specifico (es. "6:00")
                target_type = "pace.zone"
                
                # Verifica se il formato è min:sec o min:sec-min:sec
                if ':' in target:
                    if '-' in target:
                        # Formato: min:sec-min:sec
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
                        # Formato: min:sec (passo singolo)
                        try:
                            parts = target.strip().split(':')
                            pace_secs = int(parts[0]) * 60 + int(parts[1])
                            
                            # Per un passo singolo, usa lo stesso valore per from e to
                            pace_ms = 1000 / pace_secs
                            target_from = pace_ms
                            target_to = pace_ms
                            
                            # Non è una zona predefinita, quindi non impostiamo yaml_target_zone
                            yaml_target_zone = None
                        except (ValueError, IndexError):
                            # Default se non riesce a interpretare
                            target_from = 3.0
                            target_to = 2.5
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
        
        # Imposta il nome della zona solo se è una zona predefinita
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