#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servizio per la gestione dei file Excel.
"""

import logging
import re
import os
from typing import Dict, Any, List, Tuple, Optional

try:
    import pandas as pd
    import openpyxl
    from openpyxl.styles import Alignment
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from config import get_config
from models.workout import Workout, WorkoutStep, Target


class ExcelService:
    """Servizio per la gestione dei file Excel."""
    
    @staticmethod
    def check_pandas():
        """
        Verifica che pandas sia disponibile.
        
        Raises:
            ImportError: Se pandas non è disponibile
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas e openpyxl sono richiesti per gestire i file Excel")
    
    @staticmethod
    def import_workouts(file_path: str) -> List[Tuple[str, Workout]]:
        """
        Importa allenamenti da un file Excel con multipli fogli.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            Lista di tuple (nome, allenamento)
            
        Raises:
            ImportError: Se pandas non è disponibile
            IOError: Se il file non può essere letto
            ValueError: Se il file non contiene allenamenti validi
        """
        # Verifica che pandas sia disponibile
        ExcelService.check_pandas()
        
        try:
            # Carica il file
            xls = pd.ExcelFile(file_path)
            
            # Ottieni istanza di configurazione
            config = get_config()
            
            # Carica la configurazione se presente
            if 'Config' in xls.sheet_names:
                config_df = pd.read_excel(file_path, sheet_name='Config')
                
                # Verifica che le colonne necessarie siano presenti
                if 'Parametro' in config_df.columns and 'Valore' in config_df.columns:
                    # Importa i valori di configurazione
                    for _, row in config_df.iterrows():
                        param = row.get('Parametro')
                        value = row.get('Valore')
                        
                        if param and pd.notna(value):
                            if param == 'athlete_name':
                                config.set('athlete_name', value)
                            elif param == 'name_prefix':
                                config.set('planning.name_prefix', value)
                            elif param == 'race_day':
                                config.set('planning.race_day', value)
                            elif param == 'preferred_days':
                                # Converti in lista se è una stringa
                                if isinstance(value, str):
                                    try:
                                        import ast
                                        days_list = ast.literal_eval(value)
                                        config.set('planning.preferred_days', days_list)
                                    except:
                                        pass
                                elif isinstance(value, (list, tuple)):
                                    config.set('planning.preferred_days', list(value))
                            elif param.startswith('margin.'):
                                # Gestione margini
                                margin_type = param.split('.')[1]
                                if margin_type == 'faster':
                                    config.set('sports.running.margins.faster', value)
                                    config.set('sports.swimming.margins.faster', value)
                                elif margin_type == 'slower':
                                    config.set('sports.running.margins.slower', value)
                                    config.set('sports.swimming.margins.slower', value)
                                elif margin_type == 'power_up':
                                    config.set('sports.cycling.margins.power_up', value)
                                elif margin_type == 'power_down':
                                    config.set('sports.cycling.margins.power_down', value)
                                elif margin_type == 'hr_up':
                                    config.set('hr_margins.hr_up', value)
                                elif margin_type == 'hr_down':
                                    config.set('hr_margins.hr_down', value)
                                    
                    logging.info("Configurazione importata con successo")
            
            # Carica i valori di passo, nuoto e potenza se presenti
            if 'Paces' in xls.sheet_names:
                paces_df = pd.read_excel(file_path, sheet_name='Paces')
                
                logging.info(f"Foglio 'Paces' trovato. Colonne: {paces_df.columns.tolist()}")
                
                # Verifica l'esistenza delle sezioni
                sections = paces_df[paces_df['Value'].isna() & ~paces_df['Name'].isna()]['Name'].tolist()
                logging.info(f"Sezioni trovate: {sections}")
                
                run_section = "RITMI PER LA CORSA"
                cycle_section = "POTENZA PER IL CICLISMO"
                swim_section = "PASSI VASCA PER IL NUOTO"
                
                current_section = None
                
                # Processa riga per riga
                for idx, row in paces_df.iterrows():
                    name = row.get('Name')
                    value = row.get('Value')
                    
                    # Stampa ogni riga per il debug
                    logging.debug(f"Riga {idx}: name='{name}', value='{value}'")
                    
                    # Cambiamento di sezione
                    if pd.isna(value) and pd.notna(name):
                        for section_name, section_type in [(run_section, "running"), 
                                                          (cycle_section, "cycling"), 
                                                          (swim_section, "swimming")]:
                            if section_name in str(name):
                                current_section = section_type
                                logging.info(f"Sezione trovata: {current_section}")
                                break
                        continue
                    
                    # Ignora righe senza nome o valore
                    if pd.isna(name) or pd.isna(value):
                        continue
                    
                    # Importa i valori in base alla sezione
                    if current_section == "running":
                        # Assicurati che il valore sia una stringa
                        str_value = str(value)
                        config.set(f'sports.running.paces.{name}', str_value)
                        logging.info(f"Importato running pace: {name} = {str_value}")
                    elif current_section == "cycling":
                        str_value = str(value)
                        if name == "ftp":
                            config.set(f'sports.cycling.power_values.{name}', str_value)
                        else:
                            config.set(f'sports.cycling.power_values.{name}', str_value)
                        logging.info(f"Importato cycling power: {name} = {str_value}")
                    elif current_section == "swimming":
                        str_value = str(value)
                        config.set(f'sports.swimming.paces.{name}', str_value)
                        logging.info(f"Importato swimming pace: {name} = {str_value}")
                
                logging.info("Valori di pace/potenza importati con successo")
            
            # Carica i valori di frequenza cardiaca se presenti
            if 'HeartRates' in xls.sheet_names:
                hr_df = pd.read_excel(file_path, sheet_name='HeartRates')
                
                logging.info(f"Foglio 'HeartRates' trovato. Colonne: {hr_df.columns.tolist()}")
                
                # Verifica che le colonne necessarie siano presenti
                if 'Name' in hr_df.columns and 'Value' in hr_df.columns:
                    for _, row in hr_df.iterrows():
                        name = row.get('Name')
                        value = row.get('Value')
                        
                        if pd.notna(name) and pd.notna(value):
                            str_value = str(value)
                            if name == 'max_hr' or name == 'rest_hr':
                                config.set(f'heart_rates.{name}', str_value)
                                logging.info(f"Importato heart rate: {name} = {str_value}")
                            elif name.endswith('_HR'):
                                config.set(f'heart_rates.{name}', str_value)
                                logging.info(f"Importato heart rate zone: {name} = {str_value}")
                
                logging.info("Valori di frequenza cardiaca importati con successo")
            
            # Salva le modifiche alla configurazione
            config.save()
            
            # Lista degli allenamenti importati
            imported_workouts = []
            
            # Importa gli allenamenti se presenti
            if 'Workouts' in xls.sheet_names:
                workouts_df = pd.read_excel(file_path, sheet_name='Workouts')
                
                logging.info(f"Foglio 'Workouts' trovato. Colonne: {workouts_df.columns.tolist()}")
                logging.info(f"Numero di righe nel foglio: {len(workouts_df)}")
                
                # Verifica che ci siano le colonne necessarie
                required_columns = ['Week', 'Date', 'Session', 'Sport', 'Description', 'Steps']
                missing_columns = [col for col in required_columns if col not in workouts_df.columns]
                
                if missing_columns:
                    logging.warning(f"Foglio 'Workouts' non valido: mancano le colonne {', '.join(missing_columns)}")
                    return []
                
                # Trova le righe con i nomi degli allenamenti - guardiamo sia Week che Sport
                # Questo è più permissivo: consideriamo una riga valida se ha un valore in "Week" OPPURE in "Sport"
                workout_rows = workouts_df[(workouts_df['Week'].notna()) | (workouts_df['Sport'].notna())].index.tolist()
                
                if not workout_rows:
                    logging.warning(f"Foglio 'Workouts' non contiene allenamenti validi")
                    # Analizziamo il contenuto per diagnostica
                    if not workouts_df.empty:
                        logging.info(f"Primi 5 record nel foglio Workouts:\n{workouts_df.head().to_string()}")
                    return []
                
                logging.info(f"Trovate {len(workout_rows)} righe di allenamenti")
                
                # Per ogni allenamento nel foglio
                for i, row_idx in enumerate(workout_rows):
                    try:
                        # Ottieni i dati dell'allenamento
                        week = workouts_df.loc[row_idx, 'Week']
                        date = workouts_df.loc[row_idx, 'Date']
                        session = workouts_df.loc[row_idx, 'Session']
                        sport_type = workouts_df.loc[row_idx, 'Sport']
                        description = workouts_df.loc[row_idx, 'Description'] if pd.notna(workouts_df.loc[row_idx, 'Description']) else ''
                        steps_text = workouts_df.loc[row_idx, 'Steps'] if pd.notna(workouts_df.loc[row_idx, 'Steps']) else ''
                        
                        logging.info(f"Processando allenamento: W{week}D{session} - {description}")
                        logging.info(f"Sport: {sport_type}, Date: {date}")
                        logging.debug(f"Steps: {steps_text}")
                        
                        # Verifica e converti il tipo di sport
                        if pd.isna(sport_type):
                            sport_type = 'running'  # Default
                        else:
                            sport_type = str(sport_type).lower()
                            if 'running' in sport_type:
                                sport_type = 'running'
                            elif 'cycling' in sport_type:
                                sport_type = 'cycling'
                            elif 'swimming' in sport_type:
                                sport_type = 'swimming'
                            else:
                                sport_type = 'running'  # Default
                        
                        # Costruisci il nome dell'allenamento
                        workout_name = f"W{week}D{session} - {description}"
                        
                        # Data dell'allenamento
                        workout_date = None
                        if pd.notna(date):
                            if isinstance(date, pd.Timestamp):
                                workout_date = date.strftime('%Y-%m-%d')
                            else:
                                workout_date = str(date)
                        
                        # Creare l'allenamento
                        workout = Workout(sport_type, workout_name, description)
                        
                        # Se c'è una data, aggiungi uno step speciale con la data
                        if workout_date:
                            date_step = WorkoutStep(0, "warmup")
                            date_step.date = workout_date
                            workout.add_step(date_step)
                        
                        # Verifica che gli steps siano validi
                        if not pd.isna(steps_text) and steps_text:
                            # Parsa gli step
                            logging.info(f"Parsing steps per '{workout_name}'")
                            steps_lines = str(steps_text).strip().split('\n')
                            
                            # Tieni traccia dello stato corrente del parsing
                            current_repeat = None
                            indent_level = 0
                            
                            for line_num, line in enumerate(steps_lines, 1):
                                # Salta linee vuote
                                if not line.strip():
                                    continue
                                
                                logging.debug(f"Processing line {line_num}: {line}")
                                
                                # Calcola il livello di indentazione
                                line_indent = len(line) - len(line.lstrip())
                                
                                # Normalizza la linea
                                line = line.strip()
                                
                                # Controlla se è una ripetizione
                                if line.startswith('repeat'):
                                    try:
                                        # Rimuovi i due punti alla fine se presenti
                                        line_clean = line.replace(':', '')
                                        
                                        # Usa una regex per estrarre il numero
                                        import re
                                        numbers = re.findall(r'\d+', line_clean)
                                        if numbers:
                                            iterations = int(numbers[0])
                                        else:
                                            iterations = 1
                                            logging.warning(f"Nessun numero trovato in '{line}', usando 1 ripetizione")
                                    except Exception as e:
                                        iterations = 1
                                        logging.warning(f"Impossibile estrarre il numero di ripetizioni da '{line}': {str(e)}, usando 1")
                                    
                                    logging.debug(f"Creato repeat step con {iterations} ripetizioni")
                                    current_repeat = WorkoutStep(
                                        order=0,
                                        step_type='repeat',
                                        end_condition='iterations',
                                        end_condition_value=iterations
                                    )
                                    
                                    # Aggiungi all'allenamento
                                    workout.add_step(current_repeat)
                                    indent_level = line_indent
                                
                                # Controlla se è la fine di una ripetizione
                                elif current_repeat and line_indent <= indent_level:
                                    # Se siamo a un livello di indentazione uguale o inferiore a quello del repeat,
                                    # significa che siamo usciti dal blocco repeat
                                    logging.debug(f"Fine ripetizione (indent {line_indent} <= {indent_level})")
                                    
                                    # Salviamo l'indentazione corrente per questo step non in repeat
                                    current_line_indent = line_indent
                                    
                                    # Chiudiamo il repeat
                                    current_repeat = None
                                    indent_level = 0
                                    
                                    # Ora procediamo normalmente con questo step al livello superiore
                                    try:
                                        # Determina il tipo di step
                                        if ':' not in line:
                                            logging.warning(f"Linea '{line}' non contiene ':' - saltata")
                                            continue
                                        
                                        step_type, step_data = line.split(':', 1)
                                        step_type = step_type.strip()
                                        step_data = step_data.strip()
                                        
                                        logging.debug(f"Tipo di step: {step_type}, Dati: {step_data}")
                                        
                                        # Parsa i dati dello step
                                        end_condition = "lap.button"
                                        end_condition_value = None
                                        description = ""
                                        target = None
                                        
                                        # Estrai la descrizione se presente
                                        if '--' in step_data:
                                            step_data, description = step_data.split('--', 1)
                                            step_data = step_data.strip()
                                            description = description.strip()
                                        
                                        # Estrai il target se presente
                                        target_zone_name = None
                                        if '@' in step_data:
                                            step_data, target_info = step_data.split('@', 1)
                                            step_data = step_data.strip()
                                            target_info = target_info.strip()
                                            
                                            # Imposta il tipo di target in base al tipo di sport
                                            if 'HR' in target_info or 'hr' in target_info:
                                                target_type = 'heart.rate.zone'
                                                target_zone_name = target_info
                                            elif sport_type == 'cycling' and ('pwr' in target_info or target_info in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'recovery', 'threshold', 'sweet_spot']):
                                                target_type = 'power.zone'
                                                target_zone_name = target_info
                                            else:
                                                target_type = 'pace.zone'
                                                target_zone_name = target_info
                                            
                                            # Crea oggetto target
                                            target = Target(target_type)
                                            
                                            # Aggiungi il nome della zona al target
                                            if hasattr(target, 'target_zone_name'):
                                                target.target_zone_name = target_zone_name
                                            
                                            # Calcola i valori target in base al tipo e alla configurazione
                                            if target_type == 'heart.rate.zone' and target_zone_name:
                                                if target_zone_name.startswith('Z') and '_HR' in target_zone_name:
                                                    # Zona di frequenza cardiaca
                                                    heart_rates = config.get('heart_rates', {})
                                                    max_hr = heart_rates.get('max_hr', 180)
                                                    
                                                    if target_zone_name in heart_rates:
                                                        hr_range = heart_rates[target_zone_name]
                                                        
                                                        if '-' in hr_range and 'max_hr' in hr_range:
                                                            # Formato: 62-76% max_hr
                                                            parts = hr_range.split('-')
                                                            min_percent = float(parts[0])
                                                            max_percent = float(parts[1].split('%')[0])
                                                            
                                                            target.from_value = int(min_percent * max_hr / 100)
                                                            target.to_value = int(max_percent * max_hr / 100)
                                                elif '-' in target_info and 'bpm' in target_info.lower():
                                                    # Formato esplicito "140-160 bpm"
                                                    try:
                                                        parts = target_info.split('-')
                                                        min_hr = parts[0].strip()
                                                        max_hr = parts[1].split('bpm')[0].strip()
                                                        target.from_value = int(min_hr)
                                                        target.to_value = int(max_hr)
                                                    except:
                                                        logging.warning(f"Impossibile parsare il target HR: {target_info}")
                                            
                                            elif target_type == 'pace.zone' and target_zone_name:
                                                # Zona di passo
                                                paces = config.get(f'sports.{sport_type}.paces', {})
                                                if target_zone_name in paces:
                                                    pace_range = paces[target_zone_name]
                                                    
                                                    if '-' in pace_range:
                                                        # Formato: min:sec-min:sec
                                                        min_pace, max_pace = pace_range.split('-')
                                                    else:
                                                        # Formato: min:sec
                                                        min_pace = max_pace = pace_range
                                                    
                                                    # Funzione per convertire mm:ss in secondi
                                                    def pace_to_seconds(pace_str):
                                                        try:
                                                            parts = pace_str.strip().split(':')
                                                            return int(parts[0]) * 60 + int(parts[1])
                                                        except:
                                                            return 0
                                                    
                                                    min_secs = pace_to_seconds(min_pace)
                                                    max_secs = pace_to_seconds(max_pace)
                                                    
                                                    if min_secs > 0 and max_secs > 0:
                                                        # Converti da secondi/km a m/s
                                                        target.from_value = 1000 / max_secs
                                                        target.to_value = 1000 / min_secs
                                            
                                            elif target_type == 'power.zone' and target_zone_name:
                                                # Zona di potenza
                                                power_values = config.get('sports.cycling.power_values', {})
                                                if target_zone_name in power_values:
                                                    power_range = power_values[target_zone_name]
                                                    
                                                    if isinstance(power_range, str):
                                                        if '-' in power_range:
                                                            # Formato: N-N
                                                            min_power, max_power = power_range.split('-')
                                                            try:
                                                                target.from_value = int(min_power.strip())
                                                                target.to_value = int(max_power.strip())
                                                            except:
                                                                logging.warning(f"Impossibile parsare il range di potenza: {power_range}")
                                                        elif power_range.startswith('<'):
                                                            # Formato: <N
                                                            try:
                                                                power_val = int(power_range[1:].strip())
                                                                target.from_value = 0
                                                                target.to_value = power_val
                                                            except:
                                                                logging.warning(f"Impossibile parsare il valore di potenza: {power_range}")
                                                        elif power_range.endswith('+'):
                                                            # Formato: N+
                                                            try:
                                                                power_val = int(power_range[:-1].strip())
                                                                target.from_value = power_val
                                                                target.to_value = 9999
                                                            except:
                                                                logging.warning(f"Impossibile parsare il valore di potenza: {power_range}")
                                                        else:
                                                            # Valore singolo
                                                            try:
                                                                power_val = int(power_range.strip())
                                                                target.from_value = power_val
                                                                target.to_value = power_val
                                                            except:
                                                                logging.warning(f"Impossibile parsare il valore di potenza: {power_range}")
                                        
                                        # Parsa la condizione di fine e il valore
                                        if 'lap-button' in step_data:
                                            end_condition = 'lap.button'
                                        elif 'min' in step_data:
                                            end_condition = 'time'
                                            # Estrai il tempo in minuti/secondi
                                            time_part = step_data.split(' ')[0]
                                            logging.debug(f"Parte tempo: {time_part}")
                                            
                                            # Rimuovi 'min' se presente
                                            if 'min' in time_part:
                                                time_part = time_part.replace('min', '')
                                            
                                            if ':' in time_part:
                                                # Formato mm:ss
                                                try:
                                                    mins, secs = time_part.split(':')
                                                    end_condition_value = int(mins.strip()) * 60 + int(secs.strip())
                                                    logging.debug(f"Tempo parsato: {mins}:{secs} = {end_condition_value}s")
                                                except Exception as e:
                                                    end_condition_value = 60
                                                    logging.warning(f"Errore nel parsing del tempo '{time_part}': {e}")
                                            else:
                                                # Formato mm (solo minuti)
                                                try:
                                                    mins = time_part.strip()
                                                    end_condition_value = int(mins) * 60
                                                    logging.debug(f"Tempo parsato: {mins}min = {end_condition_value}s")
                                                except Exception as e:
                                                    end_condition_value = 60
                                                    logging.warning(f"Errore nel parsing del tempo '{time_part}': {e}")
                                        elif step_data.strip().endswith('m') and not step_data.strip().endswith('km'):
                                            # Metri
                                            end_condition = 'distance'
                                            try:
                                                # Rimuovi 'm' alla fine
                                                distance_part = step_data.split(' ')[0].replace('m', '')
                                                distance = float(distance_part.strip())
                                                end_condition_value = distance
                                                logging.debug(f"Distanza parsata: {distance}m")
                                            except Exception as e:
                                                end_condition_value = 100
                                                logging.warning(f"Errore nel parsing della distanza '{step_data}': {e}")
                                        elif 'km' in step_data:
                                            end_condition = 'distance'
                                            try:
                                                # Rimuovi 'km' alla fine
                                                distance_part = step_data.split(' ')[0].replace('km', '')
                                                distance = float(distance_part.strip())
                                                end_condition_value = distance * 1000  # Converti in metri
                                                logging.debug(f"Distanza parsata: {distance}km = {end_condition_value}m")
                                            except Exception as e:
                                                end_condition_value = 1000
                                                logging.warning(f"Errore nel parsing della distanza '{step_data}': {e}")
                                        
                                        # Crea lo step
                                        step = WorkoutStep(
                                            order=0,
                                            step_type=step_type,
                                            description=description,
                                            end_condition=end_condition,
                                            end_condition_value=end_condition_value,
                                            target=target
                                        )
                                        
                                        logging.debug(f"Creato step: {step}")
                                        
                                        # Questo step va aggiunto all'allenamento principale, NON al repeat
                                        # (che abbiamo già chiuso)
                                        workout.add_step(step)
                                        logging.debug(f"Step aggiunto all'allenamento (fuori dal repeat)")
                                        
                                    except Exception as e:
                                        logging.error(f"Errore nel parsing dello step '{line}': {str(e)}")
                                
                                # Altrimenti è uno step normale
                                else:
                                    try:
                                        # Determina il tipo di step
                                        if ':' not in line:
                                            logging.warning(f"Linea '{line}' non contiene ':' - saltata")
                                            continue
                                        
                                        step_type, step_data = line.split(':', 1)
                                        step_type = step_type.strip()
                                        step_data = step_data.strip()
                                        
                                        logging.debug(f"Tipo di step: {step_type}, Dati: {step_data}")
                                        
                                        # Parsa i dati dello step
                                        end_condition = "lap.button"
                                        end_condition_value = None
                                        description = ""
                                        target = None
                                        
                                        # Estrai la descrizione se presente
                                        if '--' in step_data:
                                            step_data, description = step_data.split('--', 1)
                                            step_data = step_data.strip()
                                            description = description.strip()
                                        
                                        # Estrai il target se presente
                                        target_zone_name = None
                                        if '@' in step_data:
                                            step_data, target_info = step_data.split('@', 1)
                                            step_data = step_data.strip()
                                            target_info = target_info.strip()
                                            
                                            # Imposta il tipo di target in base al tipo di sport
                                            if 'HR' in target_info or 'hr' in target_info:
                                                target_type = 'heart.rate.zone'
                                                target_zone_name = target_info
                                            elif sport_type == 'cycling' and ('pwr' in target_info or target_info in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'recovery', 'threshold', 'sweet_spot']):
                                                target_type = 'power.zone'
                                                target_zone_name = target_info
                                            else:
                                                target_type = 'pace.zone'
                                                target_zone_name = target_info
                                            
                                            # Crea oggetto target
                                            target = Target(target_type)
                                            
                                            # Aggiungi il nome della zona al target
                                            if hasattr(target, 'target_zone_name'):
                                                target.target_zone_name = target_zone_name
                                            
                                            # Calcola i valori target in base al tipo e alla configurazione
                                            if target_type == 'heart.rate.zone' and target_zone_name:
                                                if target_zone_name.startswith('Z') and '_HR' in target_zone_name:
                                                    # Zona di frequenza cardiaca
                                                    heart_rates = config.get('heart_rates', {})
                                                    max_hr = heart_rates.get('max_hr', 180)
                                                    
                                                    if target_zone_name in heart_rates:
                                                        hr_range = heart_rates[target_zone_name]
                                                        
                                                        if '-' in hr_range and 'max_hr' in hr_range:
                                                            # Formato: 62-76% max_hr
                                                            parts = hr_range.split('-')
                                                            min_percent = float(parts[0])
                                                            max_percent = float(parts[1].split('%')[0])
                                                            
                                                            target.from_value = int(min_percent * max_hr / 100)
                                                            target.to_value = int(max_percent * max_hr / 100)
                                                elif '-' in target_info and 'bpm' in target_info.lower():
                                                    # Formato esplicito "140-160 bpm"
                                                    try:
                                                        parts = target_info.split('-')
                                                        min_hr = parts[0].strip()
                                                        max_hr = parts[1].split('bpm')[0].strip()
                                                        target.from_value = int(min_hr)
                                                        target.to_value = int(max_hr)
                                                    except:
                                                        logging.warning(f"Impossibile parsare il target HR: {target_info}")
                                            
                                            elif target_type == 'pace.zone' and target_zone_name:
                                                # Zona di passo
                                                paces = config.get(f'sports.{sport_type}.paces', {})
                                                if target_zone_name in paces:
                                                    pace_range = paces[target_zone_name]
                                                    
                                                    if '-' in pace_range:
                                                        # Formato: min:sec-min:sec
                                                        min_pace, max_pace = pace_range.split('-')
                                                    else:
                                                        # Formato: min:sec
                                                        min_pace = max_pace = pace_range
                                                    
                                                    # Funzione per convertire mm:ss in secondi
                                                    def pace_to_seconds(pace_str):
                                                        try:
                                                            parts = pace_str.strip().split(':')
                                                            return int(parts[0]) * 60 + int(parts[1])
                                                        except:
                                                            return 0
                                                    
                                                    min_secs = pace_to_seconds(min_pace)
                                                    max_secs = pace_to_seconds(max_pace)
                                                    
                                                    if min_secs > 0 and max_secs > 0:
                                                        # Converti da secondi/km a m/s
                                                        target.from_value = 1000 / max_secs
                                                        target.to_value = 1000 / min_secs
                                            
                                            elif target_type == 'power.zone' and target_zone_name:
                                                # Zona di potenza
                                                power_values = config.get('sports.cycling.power_values', {})
                                                if target_zone_name in power_values:
                                                    power_range = power_values[target_zone_name]
                                                    
                                                    if isinstance(power_range, str):
                                                        if '-' in power_range:
                                                            # Formato: N-N
                                                            min_power, max_power = power_range.split('-')
                                                            try:
                                                                target.from_value = int(min_power.strip())
                                                                target.to_value = int(max_power.strip())
                                                            except:
                                                                logging.warning(f"Impossibile parsare il range di potenza: {power_range}")
                                                        elif power_range.startswith('<'):
                                                            # Formato: <N
                                                            try:
                                                                power_val = int(power_range[1:].strip())
                                                                target.from_value = 0
                                                                target.to_value = power_val
                                                            except:
                                                                logging.warning(f"Impossibile parsare il valore di potenza: {power_range}")
                                                        elif power_range.endswith('+'):
                                                            # Formato: N+
                                                            try:
                                                                power_val = int(power_range[:-1].strip())
                                                                target.from_value = power_val
                                                                target.to_value = 9999
                                                            except:
                                                                logging.warning(f"Impossibile parsare il valore di potenza: {power_range}")
                                                        else:
                                                            # Valore singolo
                                                            try:
                                                                power_val = int(power_range.strip())
                                                                target.from_value = power_val
                                                                target.to_value = power_val
                                                            except:
                                                                logging.warning(f"Impossibile parsare il valore di potenza: {power_range}")
                                        
                                        # Parsa la condizione di fine e il valore
                                        if 'lap-button' in step_data:
                                            end_condition = 'lap.button'
                                        elif 'min' in step_data:
                                            end_condition = 'time'
                                            # Estrai il tempo in minuti/secondi
                                            time_part = step_data.split(' ')[0]
                                            logging.debug(f"Parte tempo: {time_part}")
                                            
                                            # Rimuovi 'min' se presente
                                            if 'min' in time_part:
                                                time_part = time_part.replace('min', '')
                                            
                                            if ':' in time_part:
                                                # Formato mm:ss
                                                try:
                                                    mins, secs = time_part.split(':')
                                                    end_condition_value = int(mins.strip()) * 60 + int(secs.strip())
                                                    logging.debug(f"Tempo parsato: {mins}:{secs} = {end_condition_value}s")
                                                except Exception as e:
                                                    end_condition_value = 60
                                                    logging.warning(f"Errore nel parsing del tempo '{time_part}': {e}")
                                            else:
                                                # Formato mm (solo minuti)
                                                try:
                                                    mins = time_part.strip()
                                                    end_condition_value = int(mins) * 60
                                                    logging.debug(f"Tempo parsato: {mins}min = {end_condition_value}s")
                                                except Exception as e:
                                                    end_condition_value = 60
                                                    logging.warning(f"Errore nel parsing del tempo '{time_part}': {e}")
                                        elif step_data.strip().endswith('m') and not step_data.strip().endswith('km'):
                                            # Metri
                                            end_condition = 'distance'
                                            try:
                                                # Rimuovi 'm' alla fine
                                                distance_part = step_data.split(' ')[0].replace('m', '')
                                                distance = float(distance_part.strip())
                                                end_condition_value = distance
                                                logging.debug(f"Distanza parsata: {distance}m")
                                            except Exception as e:
                                                end_condition_value = 100
                                                logging.warning(f"Errore nel parsing della distanza '{step_data}': {e}")
                                        elif 'km' in step_data:
                                            end_condition = 'distance'
                                            try:
                                                # Rimuovi 'km' alla fine
                                                distance_part = step_data.split(' ')[0].replace('km', '')
                                                distance = float(distance_part.strip())
                                                end_condition_value = distance * 1000  # Converti in metri
                                                logging.debug(f"Distanza parsata: {distance}km = {end_condition_value}m")
                                            except Exception as e:
                                                end_condition_value = 1000
                                                logging.warning(f"Errore nel parsing della distanza '{step_data}': {e}")
                                        
                                        # Crea lo step
                                        step = WorkoutStep(
                                            order=0,
                                            step_type=step_type,
                                            description=description,
                                            end_condition=end_condition,
                                            end_condition_value=end_condition_value,
                                            target=target
                                        )
                                        
                                        logging.debug(f"Creato step: {step}")
                                        
                                        # Aggiungi lo step al gruppo corrente o all'allenamento
                                        if current_repeat and line_indent > indent_level:
                                            current_repeat.add_step(step)
                                            logging.debug(f"Step aggiunto al repeat")
                                        else:
                                            workout.add_step(step)
                                            logging.debug(f"Step aggiunto all'allenamento")
                                        
                                    except Exception as e:
                                        logging.error(f"Errore nel parsing dello step '{line}': {str(e)}")
                        
                        # Aggiungi l'allenamento alla lista degli importati
                        imported_workouts.append((workout_name, workout))
                        logging.info(f"Allenamento '{workout_name}' importato con successo, con {len(workout.workout_steps)} step")
                        
                    except Exception as e:
                        logging.error(f"Errore nell'importazione dell'allenamento alla riga {row_idx}: {str(e)}")
                        raise ValueError(f"Errore nell'importazione dell'allenamento alla riga {row_idx}: {str(e)}")
            
            # Log del risultato
            logging.info(f"Importati {len(imported_workouts)} allenamenti")
            return imported_workouts
            
        except Exception as e:
            logging.error(f"Errore nell'importazione degli allenamenti da Excel: {str(e)}")
            raise

    @staticmethod
    def export_workouts(workouts: List[Tuple[str, Workout]], file_path: str) -> None:
        """
        Esporta allenamenti in un file Excel con multipli fogli.
        
        Args:
            workouts: Lista di tuple (nome, allenamento)
            file_path: Percorso del file
            
        Raises:
            ImportError: Se pandas non è disponibile
            IOError: Se il file non può essere scritto
        """
        # Verifica che pandas sia disponibile
        ExcelService.check_pandas()
        
        try:
            # Ottieni la configurazione
            config = get_config()
            
            # Crea i DataFrame per ogni foglio
            config_df = pd.DataFrame(columns=['Parametro', 'Valore', 'Descrizione'])
            paces_df = pd.DataFrame(columns=['Name', 'Value', 'Note'])
            heart_rates_df = pd.DataFrame(columns=['Name', 'Value', 'Description'])
            workouts_df = pd.DataFrame(columns=['Week', 'Date', 'Session', 'Sport', 'Description', 'Steps'])
            examples_df = pd.DataFrame(columns=['Type', 'Example', 'Description'])
            
            # Popola il DataFrame della configurazione
            config_rows = [
                {'Parametro': 'athlete_name', 'Valore': config.get('athlete_name', ''), 
                 'Descrizione': 'Nome dell\'atleta'},
                {'Parametro': 'name_prefix', 'Valore': config.get('planning.name_prefix', ''), 
                 'Descrizione': 'Prefisso per i nomi degli allenamenti'},
                {'Parametro': 'race_day', 'Valore': config.get('planning.race_day', ''), 
                 'Descrizione': 'Data della gara (YYYY-MM-DD)'},
                {'Parametro': 'preferred_days', 'Valore': str(config.get('planning.preferred_days', [1, 3, 5])), 
                 'Descrizione': 'Giorni preferiti per gli allenamenti [0=Lunedì, 6=Domenica]'},
                {'Parametro': 'margin.faster', 'Valore': config.get('sports.running.margins.faster', '0:05'), 
                 'Descrizione': 'Margine più veloce per corsa/nuoto'},
                {'Parametro': 'margin.slower', 'Valore': config.get('sports.running.margins.slower', '0:05'), 
                 'Descrizione': 'Margine più lento per corsa/nuoto'},
                {'Parametro': 'margin.power_up', 'Valore': config.get('sports.cycling.margins.power_up', 10), 
                 'Descrizione': 'Margine potenza superiore per ciclismo'},
                {'Parametro': 'margin.power_down', 'Valore': config.get('sports.cycling.margins.power_down', 10), 
                 'Descrizione': 'Margine potenza inferiore per ciclismo'},
                {'Parametro': 'margin.hr_up', 'Valore': config.get('hr_margins.hr_up', 5), 
                 'Descrizione': 'Margine superiore frequenza cardiaca'},
                {'Parametro': 'margin.hr_down', 'Valore': config.get('hr_margins.hr_down', 5), 
                 'Descrizione': 'Margine inferiore frequenza cardiaca'},
            ]
            config_df = pd.DataFrame(config_rows)
            
            # Popola il DataFrame dei paces
            paces_rows = []
            
            # Aggiungi titolo per la sezione dei ritmi di corsa
            paces_rows.append({'Name': 'RITMI PER LA CORSA (min/km)', 'Value': None, 'Note': None})
            
            # Aggiungi i ritmi per la corsa
            running_paces = config.get('sports.running.paces', {})
            for name, value in running_paces.items():
                description = ""
                if name == 'Z1':
                    description = "Ritmo facile (zona 1, recupero)"
                elif name == 'Z2':
                    description = "Ritmo aerobico (zona 2, endurance)"
                elif name == 'Z3':
                    description = "Ritmo medio (zona 3, soglia aerobica)"
                elif name == 'Z4':
                    description = "Ritmo soglia (zona 4, soglia anaerobica)"
                elif name == 'Z5':
                    description = "Ritmo VO2max (zona 5, anaerobico)"
                elif name == 'recovery':
                    description = "Ritmo recupero (molto lento)"
                elif name == 'threshold':
                    description = "Ritmo soglia personalizzato"
                elif name == 'marathon':
                    description = "Ritmo maratona personalizzato"
                elif name == 'race_pace':
                    description = "Ritmo gara personalizzato"
                
                paces_rows.append({'Name': name, 'Value': value, 'Note': description})
            
            # Aggiungi una riga vuota per separazione
            paces_rows.append({'Name': None, 'Value': None, 'Note': None})
            
            # Aggiungi titolo per la sezione potenza ciclismo
            paces_rows.append({'Name': 'POTENZA PER IL CICLISMO (Watt)', 'Value': None, 'Note': None})
            
            # Aggiungi i valori di potenza per il ciclismo
            power_values = config.get('sports.cycling.power_values', {})
            for name, value in power_values.items():
                description = ""
                if name == 'ftp':
                    description = "Functional Threshold Power (W)"
                elif name == 'Z1':
                    description = "Recupero attivo (55-70% FTP)"
                elif name == 'Z2':
                    description = "Endurance (70-85% FTP)"
                elif name == 'Z3':
                    description = "Tempo/Soglia (85-100% FTP)"
                elif name == 'Z4':
                    description = "VO2max (100-120% FTP)"
                elif name == 'Z5':
                    description = "Capacità anaerobica (120-150% FTP)"
                elif name == 'Z6':
                    description = "Potenza neuromuscolare (>150% FTP)"
                elif name == 'recovery':
                    description = "Recupero (<55% FTP)"
                elif name == 'threshold':
                    description = "Soglia (94-106% FTP)"
                elif name == 'sweet_spot':
                    description = "Sweet Spot (88-94% FTP)"
                
                paces_rows.append({'Name': name, 'Value': value, 'Note': description})
            
            # Aggiungi una riga vuota per separazione
            paces_rows.append({'Name': None, 'Value': None, 'Note': None})
            
            # Aggiungi titolo per la sezione passi vasca
            paces_rows.append({'Name': 'PASSI VASCA PER IL NUOTO (min/100m)', 'Value': None, 'Note': None})
            
            # Aggiungi i passi vasca per il nuoto
            swim_paces = config.get('sports.swimming.paces', {})
            for name, value in swim_paces.items():
                description = ""
                if name == 'Z1':
                    description = "Ritmo facile (zona 1)"
                elif name == 'Z2':
                    description = "Ritmo aerobico (zona 2)"
                elif name == 'Z3':
                    description = "Ritmo medio (zona 3)"
                elif name == 'Z4':
                    description = "Ritmo soglia (zona 4)"
                elif name == 'Z5':
                    description = "Ritmo VO2max (zona 5)"
                elif name == 'recovery':
                    description = "Ritmo recupero"
                elif name == 'threshold':
                    description = "Ritmo soglia personalizzato"
                elif name == 'sprint':
                    description = "Ritmo sprint"
                
                paces_rows.append({'Name': name, 'Value': value, 'Note': description})
            
            # Crea il DataFrame dai dati raccolti
            paces_df = pd.DataFrame(paces_rows)
            
            # Popola il DataFrame delle frequenze cardiache
            hr_rows = []
            heart_rates = config.get('heart_rates', {})
            for name, value in heart_rates.items():
                description = ""
                if name == 'max_hr':
                    description = "Frequenza cardiaca massima"
                elif name == 'rest_hr':
                    description = "Frequenza cardiaca a riposo"
                elif name == 'Z1_HR':
                    description = "Zona 1 (recupero attivo)"
                elif name == 'Z2_HR':
                    description = "Zona 2 (fondo facile)"
                elif name == 'Z3_HR':
                    description = "Zona 3 (fondo medio)"
                elif name == 'Z4_HR':
                    description = "Zona 4 (soglia anaerobica)"
                elif name == 'Z5_HR':
                    description = "Zona 5 (massimale)"
                
                hr_rows.append({'Name': name, 'Value': value, 'Description': description})
            
            # Crea il DataFrame dai dati raccolti
            heart_rates_df = pd.DataFrame(hr_rows)
            
            # Popola il DataFrame degli esempi
            examples_rows = [
                {'Type': 'CONFIGURAZIONE', 'Example': '', 'Description': 'Esempi di configurazione'},
                {'Type': 'Preferred Days', 'Example': '[1, 3, 5]', 'Description': 'Giorni preferiti: Lunedi=0, Martedi=1, ...'},
                {'Type': 'Race Day', 'Example': '2025-06-15', 'Description': 'Data della gara in formato YYYY-MM-DD'},
                {'Type': '', 'Example': '', 'Description': ''},
                {'Type': 'STEP ALLENAMENTO', 'Example': '', 'Description': 'Esempi di step degli allenamenti'},
                {'Type': 'Riscaldamento', 'Example': 'warmup: 10min @ Z2', 'Description': 'Riscaldamento di 10 minuti in Zona 2'},
                {'Type': 'Intervallo', 'Example': 'interval: 400m @ Z4', 'Description': 'Intervallo di 400m in Zona 4'},
                {'Type': 'Recupero', 'Example': 'recovery: 2min @ Z1', 'Description': 'Recupero di 2 minuti in Zona 1'},
                {'Type': 'Defaticamento', 'Example': 'cooldown: 5min @ Z1_HR', 'Description': 'Defaticamento di 5 min in Zona HR 1'},
                {'Type': 'Repeat', 'Example': 'repeat 4:', 'Description': 'Ripeti 4 volte gli step indentati'},
                {'Type': 'Descrizione', 'Example': 'interval: 1km @ Z3 -- Run Strong', 'Description': 'Aggiungere descrizione dopo --'},
                {'Type': '', 'Example': '', 'Description': ''},
                {'Type': 'TARGET', 'Example': '', 'Description': 'Esempi di target'},
                {'Type': 'Pace Zone', 'Example': '@ Z2', 'Description': 'Target pace in Zona 2'},
                {'Type': 'Heart Rate', 'Example': '@ Z2_HR', 'Description': 'Target frequenza cardiaca in Zona 2'},
                {'Type': 'Power', 'Example': '@ threshold', 'Description': 'Target potenza a soglia'},
                {'Type': 'Specifico HR', 'Example': '@ 140-150 bpm', 'Description': 'Target frequenza specifica'},
                {'Type': 'Specifico Pace', 'Example': '@ 5:00-5:30', 'Description': 'Target pace specifico (min:sec per km)'},
                {'Type': 'Specifico Power', 'Example': '@ 250W', 'Description': 'Target potenza specifica (Watt)'},
                {'Type': '', 'Example': '', 'Description': ''},
                {'Type': 'DURATA', 'Example': '', 'Description': 'Esempi di durata'},
                {'Type': 'Tempo', 'Example': '10min', 'Description': '10 minuti'},
                {'Type': 'Tempo con sec', 'Example': '5:30min', 'Description': '5 minuti e 30 secondi'},
                {'Type': 'Distanza', 'Example': '400m', 'Description': '400 metri'},
                {'Type': 'Distanza km', 'Example': '5km', 'Description': '5 chilometri'},
                {'Type': 'Lap Button', 'Example': 'lap-button', 'Description': 'Terminato manualmente'},
            ]
            examples_df = pd.DataFrame(examples_rows)
            
            # Popola il DataFrame degli allenamenti
            workout_rows = []
            
            for name, workout in workouts:
                # Estrai informazioni dal nome (se disponibile)
                week = None
                session = None
                description = workout.workout_name
                
                if workout.workout_name.startswith('W') and 'D' in workout.workout_name:
                    try:
                        parts = workout.workout_name.split('D')
                        week_part = parts[0].strip()
                        week = int(week_part[1:])
                        
                        rest_parts = parts[1].split('-', 1)
                        session = int(rest_parts[0].strip())
                        
                        if len(rest_parts) > 1:
                            description = rest_parts[1].strip()
                    except:
                        pass
                        
                # Trova la data dell'allenamento (se presente)
                workout_date = None
                for step in workout.workout_steps:
                    if hasattr(step, 'date') and step.date:
                        workout_date = step.date
                        break
                
                # Converti gli step in formato testo
                steps_text = ExcelService.format_steps_for_export(workout)
                
                # Aggiungi al DataFrame
                workout_rows.append({
                    'Week': week,
                    'Date': workout_date,
                    'Session': session,
                    'Sport': workout.sport_type.capitalize(),
                    'Description': description,
                    'Steps': steps_text
                })
            
            # Crea il DataFrame dai dati raccolti
            workouts_df = pd.DataFrame(workout_rows)
            
            # Salva i DataFrame in un file Excel
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                config_df.to_excel(writer, sheet_name='Config', index=False)
                paces_df.to_excel(writer, sheet_name='Paces', index=False)
                heart_rates_df.to_excel(writer, sheet_name='HeartRates', index=False)
                workouts_df.to_excel(writer, sheet_name='Workouts', index=False)
                examples_df.to_excel(writer, sheet_name='Examples', index=False)
                
                # Ottieni il workbook e i worksheet
                workbook = writer.book
                
                # Formatta il foglio Config
                config_sheet = writer.sheets['Config']
                value_col_idx = 2  # La colonna "Valore" è la seconda colonna (B)
                
                # Imposta la larghezza delle colonne
                config_sheet.column_dimensions['A'].width = 25  # Parametro
                config_sheet.column_dimensions['B'].width = 30  # Valore
                config_sheet.column_dimensions['C'].width = 40  # Descrizione
                
                # Imposta il formato delle celle nella colonna "Valore" come testo
                for row in range(2, len(config_df) + 2):  # +2 perché openpyxl parte da 1 e c'è l'intestazione
                    cell = config_sheet.cell(row=row, column=value_col_idx)
                    cell.number_format = '@'  # Imposta il formato come testo
                    
                    # Se il valore è numerico, convertilo esplicitamente in stringa
                    if cell.value is not None:
                        cell.value = str(cell.value)
                
                # Formatta il foglio Paces
                paces_sheet = writer.sheets['Paces']
                
                # Imposta la larghezza delle colonne
                paces_sheet.column_dimensions['A'].width = 25  # Name
                paces_sheet.column_dimensions['B'].width = 20  # Value
                paces_sheet.column_dimensions['C'].width = 40  # Note
                
                # Imposta il formato delle celle nella colonna "Value" come testo
                for row in range(2, len(paces_df) + 2):
                    cell = paces_sheet.cell(row=row, column=value_col_idx)
                    cell.number_format = '@'  # Imposta il formato come testo
                    
                    # Se il valore è numerico, convertilo esplicitamente in stringa
                    if cell.value is not None:
                        cell.value = str(cell.value)
                
                # Formatta il foglio HeartRates
                hr_sheet = writer.sheets['HeartRates']
                
                # Imposta la larghezza delle colonne
                hr_sheet.column_dimensions['A'].width = 25  # Name
                hr_sheet.column_dimensions['B'].width = 20  # Value
                hr_sheet.column_dimensions['C'].width = 40  # Description
                
                for row in range(2, len(heart_rates_df) + 2):
                    cell = hr_sheet.cell(row=row, column=value_col_idx)
                    cell.number_format = '@'  # Imposta il formato come testo
                    
                    # Se il valore è numerico, convertilo esplicitamente in stringa
                    if cell.value is not None:
                        cell.value = str(cell.value)
                
                # Formatta il foglio Workouts
                workouts_sheet = writer.sheets['Workouts']
                
                # Imposta la larghezza delle colonne
                workouts_sheet.column_dimensions['A'].width = 15  # Week
                workouts_sheet.column_dimensions['B'].width = 15  # Date
                workouts_sheet.column_dimensions['C'].width = 15  # Session
                workouts_sheet.column_dimensions['D'].width = 15  # Sport
                workouts_sheet.column_dimensions['E'].width = 30  # Description
                workouts_sheet.column_dimensions['F'].width = 80  # Steps
                
                # Adatta righe e formatta cella Steps
                for row in range(2, len(workouts_df) + 2):
                    # Abilita il text wrapping per tutte le celle nella colonna Steps
                    steps_cell = workouts_sheet.cell(row=row, column=6)  # La colonna F è la sesta colonna
                    steps_cell.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical='top')
                    
                    # Imposta una altezza maggiore per la riga
                    workouts_sheet.row_dimensions[row].height = 150  # Altezza in punti
                
                # Formatta il foglio Examples
                examples_sheet = writer.sheets['Examples']
                
                # Imposta la larghezza delle colonne
                examples_sheet.column_dimensions['A'].width = 25  # Type
                examples_sheet.column_dimensions['B'].width = 30  # Example
                examples_sheet.column_dimensions['C'].width = 50  # Description
                
                # Adatta le righe al contenuto per tutti i fogli
                for sheet in [config_sheet, paces_sheet, hr_sheet, examples_sheet]:
                    # Prima assicuriamoci che tutte le celle abbiano word wrap abilitato
                    for row in sheet.iter_rows():
                        for cell in row:
                            if cell.value is not None:
                                current_alignment = cell.alignment
                                # Creiamo un nuovo oggetto Alignment che preserva le proprietà esistenti
                                # ma imposta wrap_text=True
                                new_alignment = openpyxl.styles.Alignment(
                                    horizontal=current_alignment.horizontal,
                                    vertical=current_alignment.vertical,
                                    textRotation=current_alignment.textRotation,
                                    wrapText=True,
                                    shrinkToFit=current_alignment.shrinkToFit,
                                    indent=current_alignment.indent,
                                    relativeIndent=current_alignment.relativeIndent,
                                    justifyLastLine=current_alignment.justifyLastLine,
                                    readingOrder=current_alignment.readingOrder
                                )
                                cell.alignment = new_alignment
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione degli allenamenti in Excel: {str(e)}")
            raise

    @staticmethod
    def format_steps_for_export(workout: Workout, indent_level: int = 0) -> str:
        """
        Formatta gli step di un allenamento per l'esportazione in Excel.
        
        Args:
            workout: Allenamento da formattare
            indent_level: Livello di indentazione corrente
            
        Returns:
            Testo formattato degli step
        """
        steps_text = []
        
        # Aggiungi gli step (salta gli step con la data)
        steps_to_add = [s for s in workout.workout_steps if not (hasattr(s, 'date') and s.date)]
        
        for step in steps_to_add:
            # Indentazione
            indent = "    " * indent_level  # Uso 4 spazi per l'indentazione per maggiore chiarezza
            
            # Caso speciale: repeat
            if step.step_type == 'repeat':
                steps_text.append(f"{indent}repeat {step.end_condition_value}:")
                
                # Aggiungi gli step figli con indentazione aumentata
                for child_step in step.workout_steps:
                    child_text = ExcelService.format_step_for_export(child_step, indent_level + 1)
                    steps_text.append(child_text)
            else:
                # Step normale
                step_text = ExcelService.format_step_for_export(step, indent_level)
                steps_text.append(step_text)
        
        return "\n".join(steps_text)

    @staticmethod
    def format_step_for_export(step: WorkoutStep, indent_level: int = 0) -> str:
        """
        Formatta un singolo step per l'esportazione in Excel.
        
        Args:
            step: Step da formattare
            indent_level: Livello di indentazione
            
        Returns:
            Testo formattato dello step
        """
        # Indentazione
        indent = "    " * indent_level  # Uso 4 spazi per l'indentazione per maggiore chiarezza
        
        # Nome del tipo di step
        step_type = step.step_type
        
        # Valore della durata
        duration = ""
        
        if step.end_condition == 'lap.button':
            duration = "lap-button"
        elif step.end_condition == 'time':
            # Formatta il tempo
            if isinstance(step.end_condition_value, (int, float)):
                seconds = int(step.end_condition_value)
                minutes = seconds // 60
                seconds = seconds % 60
                
                if seconds > 0:
                    duration = f"{minutes}:{seconds:02d}min"
                else:
                    duration = f"{minutes}min"
            else:
                duration = str(step.end_condition_value)
        elif step.end_condition == 'distance':
            # Formatta la distanza
            if isinstance(step.end_condition_value, (int, float)):
                if step.end_condition_value >= 1000:
                    duration = f"{step.end_condition_value / 1000:.1f}km".replace('.0', '')
                else:
                    duration = f"{int(step.end_condition_value)}m"
            else:
                duration = str(step.end_condition_value)
        
        # Target
        target_text = ""
        if step.target and step.target.target != 'no.target':
            if hasattr(step.target, 'target_zone_name') and step.target.target_zone_name:
                target_text = f" @ {step.target.target_zone_name}"
            else:
                # Determina il tipo di target
                if step.target.target == 'heart.rate.zone' and step.target.from_value and step.target.to_value:
                    from_value = int(step.target.from_value)
                    to_value = int(step.target.to_value)
                    target_text = f" @ {from_value}-{to_value} bpm"
                
                elif step.target.target == 'pace.zone' and step.target.from_value and step.target.to_value:
                    # Converti da m/s a min/km
                    from_pace_secs = int(1000 / step.target.from_value) if step.target.from_value > 0 else 0
                    to_pace_secs = int(1000 / step.target.to_value) if step.target.to_value > 0 else 0
                    
                    from_pace_mins = from_pace_secs // 60
                    from_pace_s = from_pace_secs % 60
                    
                    to_pace_mins = to_pace_secs // 60
                    to_pace_s = to_pace_secs % 60
                    
                    from_pace = f"{from_pace_mins}:{from_pace_s:02d}"
                    to_pace = f"{to_pace_mins}:{to_pace_s:02d}"
                    
                    target_text = f" @ {from_pace}-{to_pace}"
                
                elif step.target.target == 'power.zone' and step.target.from_value and step.target.to_value:
                    from_value = int(step.target.from_value)
                    to_value = int(step.target.to_value)
                    
                    if from_value == 0 and to_value > 0:
                        target_text = f" @ <{to_value}W"
                    elif from_value > 0 and to_value == 9999:
                        target_text = f" @ {from_value}W+"
                    elif from_value == to_value:
                        target_text = f" @ {from_value}W"
                    else:
                        target_text = f" @ {from_value}-{to_value}W"
        
        # Descrizione
        description_text = ""
        if step.description:
            description_text = f" -- {step.description}"
        
        # Combina tutto
        return f"{indent}{step_type}: {duration}{target_text}{description_text}"
    
    @staticmethod
    def add_steps_to_dataframe(df: 'pd.DataFrame', steps: List[WorkoutStep], start_row: int, indent: str = '') -> int:
        """
        Aggiunge step a un dataframe.
        
        Args:
            df: Dataframe da popolare
            steps: Lista di step da aggiungere
            start_row: Indice di riga iniziale
            indent: Indentazione per gli step nidificati
            
        Returns:
            Indice della prossima riga libera
        """
        row_idx = start_row
        
        # Ottieni la configurazione per convertire i valori in nomi di zone
        config = get_config()
        
        # Per ogni step
        for step in steps:
            # Caso speciale: repeat
            if step.step_type == 'repeat':
                # Aggiungi la riga repeat
                df.loc[row_idx] = {
                    'Nome': '',
                    'Sport': '',
                    'Data': '',
                    'Tipo': f"{indent}repeat",
                    'Condizione di fine': 'iterations',
                    'Valore': step.end_condition_value,
                    'Descrizione': '',
                    'Target': ''
                }
                
                row_idx += 1
                
                # Aggiungi gli step figli con indentazione
                row_idx = ExcelService.add_steps_to_dataframe(df, step.workout_steps, row_idx, indent + '  ')
                
                # Aggiungi la riga end_repeat
                df.loc[row_idx] = {
                    'Nome': '',
                    'Sport': '',
                    'Data': '',
                    'Tipo': f"{indent}end_repeat",
                    'Condizione di fine': '',
                    'Valore': '',
                    'Descrizione': '',
                    'Target': ''
                }
                
                row_idx += 1
                
            else:
                # Step normale
                # Formatta il valore della condizione di fine
                end_value = ''
                
                if step.end_condition == 'lap.button':
                    end_value = 'lap-button'
                elif step.end_condition == 'time':
                    # Formatta il tempo
                    if isinstance(step.end_condition_value, str) and ":" in step.end_condition_value:
                        # Già nel formato mm:ss
                        end_value = step.end_condition_value
                    elif isinstance(step.end_condition_value, (int, float)):
                        # Converti secondi in mm:ss
                        seconds = int(step.end_condition_value)
                        minutes = seconds // 60
                        seconds = seconds % 60
                        end_value = f"{minutes}:{seconds:02d}"
                    else:
                        end_value = str(step.end_condition_value)
                elif step.end_condition == 'distance':
                    # Formatta la distanza
                    if isinstance(step.end_condition_value, str):
                        end_value = step.end_condition_value
                    elif isinstance(step.end_condition_value, (int, float)):
                        # Converti metri in m o km
                        if step.end_condition_value >= 1000:
                            end_value = f"{step.end_condition_value / 1000:.2f}km".replace('.00', '')
                        else:
                            end_value = f"{int(step.end_condition_value)}m"
                    else:
                        end_value = str(step.end_condition_value)
                else:
                    end_value = str(step.end_condition_value) if step.end_condition_value is not None else ''
                
                # Formatta il target
                target_str = ''
                
                if step.target and step.target.target != 'no.target':
                    # Converti valori numerici in nomi di zone
                    if step.target.target == 'pace.zone' and step.target.from_value and step.target.to_value:
                        # Cerca la zona di passo corrispondente
                        paces = config.get(f'sports.{step.sport_type if hasattr(step, "sport_type") else "running"}.paces', {})
                        zone_name = None
                        
                        # Converti da m/s a min/km
                        min_pace_secs = int(1000 / step.target.from_value)
                        max_pace_secs = int(1000 / step.target.to_value)
                        
                        min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                        max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                        
                        # Cerca la zona corrispondente
                        for name, pace_range in paces.items():
                            if '-' in pace_range:
                                pace_min, pace_max = pace_range.split('-')
                                if pace_min.strip() == min_pace and pace_max.strip() == max_pace:
                                    zone_name = name
                                    break
                            elif pace_range == min_pace and pace_range == max_pace:
                                zone_name = name
                                break
                        
                        if zone_name:
                            target_str = f"@ {zone_name}"
                        else:
                            if min_pace == max_pace:
                                target_str = f"{min_pace}"
                            else:
                                target_str = f"{min_pace}-{max_pace}"
                    
                    elif step.target.target == 'heart.rate.zone' and step.target.from_value and step.target.to_value:
                        # Cerca la zona HR corrispondente
                        heart_rates = config.get('heart_rates', {})
                        zone_name = None
                        
                        # Valori numerici della zona
                        from_value = int(step.target.from_value)
                        to_value = int(step.target.to_value)
                        
                        # Cerca la zona corrispondente
                        for name, hr_range in heart_rates.items():
                            if name.endswith('_HR'):
                                # Calcola valori effettivi usando max_hr
                                max_hr = heart_rates.get('max_hr', 180)
                                
                                if '-' in hr_range and 'max_hr' in hr_range:
                                    # Formato: 62-76% max_hr
                                    parts = hr_range.split('-')
                                    min_percent = float(parts[0])
                                    max_percent = float(parts[1].split('%')[0])
                                    hr_min = int(min_percent * max_hr / 100)
                                    hr_max = int(max_percent * max_hr / 100)
                                    
                                    if hr_min <= from_value <= hr_max and hr_min <= to_value <= hr_max:
                                        zone_name = name
                                        break
                        
                        if zone_name:
                            target_str = f"@ {zone_name}"
                        else:
                            target_str = f"{from_value}-{to_value} bpm"
                    
                    elif step.target.target == 'power.zone' and step.target.from_value and step.target.to_value:
                        # Cerca la zona di potenza corrispondente
                        power_values = config.get('sports.cycling.power_values', {})
                        zone_name = None
                        
                        # Valori numerici della zona
                        from_value = int(step.target.from_value)
                        to_value = int(step.target.to_value)
                        
                        # Cerca la zona corrispondente
                        for name, power_range in power_values.items():
                            if '-' in power_range:
                                power_min, power_max = power_range.split('-')
                                if int(power_min) == from_value and int(power_max) == to_value:
                                    zone_name = name
                                    break
                            elif power_range.startswith('<'):
                                power_val = int(power_range[1:])
                                if from_value == 0 and to_value == power_val:
                                    zone_name = name
                                    break
                            elif power_range.endswith('+'):
                                power_val = int(power_range[:-1])
                                if from_value == power_val and to_value == 9999:
                                    zone_name = name
                                    break
                            else:
                                power_val = int(power_range)
                                if from_value == power_val and to_value == power_val:
                                    zone_name = name
                                    break
                        
                        if zone_name:
                            target_str = f"@ {zone_name}"
                        else:
                            target_str = f"{from_value}-{to_value} W"
                
                # Aggiungi lo step al dataframe
                df.loc[row_idx] = {
                    'Nome': '',
                    'Sport': '',
                    'Data': '',
                    'Tipo': f"{indent}{step.step_type}",
                    'Condizione di fine': step.end_condition,
                    'Valore': end_value,
                    'Descrizione': step.description,
                    'Target': target_str
                }
                
                row_idx += 1
        
        return row_idx