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
        Importa allenamenti da un file Excel.
        
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
            
            # Lista degli allenamenti importati
            imported_workouts = []
            
            # Per ogni foglio
            for sheet_name in xls.sheet_names:
                # Leggi il foglio
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Verifica che ci siano le colonne necessarie
                required_columns = ['Nome', 'Sport', 'Tipo', 'Condizione di fine', 'Valore']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    logging.warning(f"Foglio '{sheet_name}' non valido: mancano le colonne {', '.join(missing_columns)}")
                    continue
                
                # Trova le righe con il nome dell'allenamento (prima colonna non vuota)
                workout_rows = df[df['Nome'].notna() & ~df['Nome'].str.contains('^#')].index.tolist()
                
                if not workout_rows:
                    logging.warning(f"Foglio '{sheet_name}' non contiene allenamenti validi")
                    continue
                
                # Per ogni allenamento nel foglio
                for i, row_idx in enumerate(workout_rows):
                    try:
                        # Nome dell'allenamento
                        workout_name = df.loc[row_idx, 'Nome']
                        
                        # Tipo di sport
                        sport_type = df.loc[row_idx, 'Sport'].lower() if pd.notna(df.loc[row_idx, 'Sport']) else 'running'
                        
                        # Data dell'allenamento (se presente)
                        workout_date = None
                        if 'Data' in df.columns and pd.notna(df.loc[row_idx, 'Data']):
                            workout_date = df.loc[row_idx, 'Data']
                            # Converti in stringa nel formato YYYY-MM-DD
                            if isinstance(workout_date, pd.Timestamp):
                                workout_date = workout_date.strftime('%Y-%m-%d')
                                
                        # Righe degli step
                        next_workout_row = workout_rows[i + 1] if i + 1 < len(workout_rows) else len(df)
                        step_rows = range(row_idx + 1, next_workout_row)
                        
                        # Crea l'allenamento
                        workout = Workout(sport_type, workout_name)
                        
                        # Per ogni step
                        current_repeat = None
                        
                        # Se c'è una data, aggiungi uno step speciale con la data
                        if workout_date:
                            date_step = WorkoutStep(0, "warmup")
                            date_step.date = workout_date
                            workout.add_step(date_step)
                        
                        for step_idx in step_rows:
                            # Verifica che la riga contenga uno step valido
                            if pd.isna(df.loc[step_idx, 'Tipo']):
                                continue
                            
                            # Leggi i dati dello step
                            step_type = df.loc[step_idx, 'Tipo'].lower()
                            
                            # Se è un repeat, crea un nuovo gruppo
                            if step_type == 'repeat':
                                try:
                                    iterations = int(df.loc[step_idx, 'Valore']) if pd.notna(df.loc[step_idx, 'Valore']) else 1
                                except (ValueError, TypeError):
                                    iterations = 1
                                
                                current_repeat = WorkoutStep(
                                    order=0,
                                    step_type='repeat',
                                    end_condition='iterations',
                                    end_condition_value=iterations
                                )
                                
                                # Aggiungi all'allenamento
                                workout.add_step(current_repeat)
                                
                            # Se è end_repeat, chiudi il gruppo corrente
                            elif step_type == 'end_repeat':
                                current_repeat = None
                                
                            # Altrimenti è uno step normale
                            else:
                                # Leggi i dati
                                end_condition = df.loc[step_idx, 'Condizione di fine'].lower() if pd.notna(df.loc[step_idx, 'Condizione di fine']) else 'lap.button'
                                end_value = df.loc[step_idx, 'Valore'] if pd.notna(df.loc[step_idx, 'Valore']) else None
                                description = df.loc[step_idx, 'Descrizione'] if 'Descrizione' in df.columns and pd.notna(df.loc[step_idx, 'Descrizione']) else ''
                                
                                # Target
                                target = None
                                if 'Target' in df.columns and pd.notna(df.loc[step_idx, 'Target']):
                                    target_str = str(df.loc[step_idx, 'Target'])
                                    
                                    # Analizza il target
                                    if '@' in target_str:
                                        # Formato zone @ Z1_HR o @ Z2
                                        parts = target_str.split('@')
                                        zone_name = parts[1].strip()
                                        
                                        # Otteniamo i valori dalla configurazione
                                        config = get_config()
                                        
                                        # Determina il tipo di zona
                                        if '_HR' in zone_name:
                                            # Zona di frequenza cardiaca
                                            target = Target('heart.rate.zone')
                                            target.target_zone_name = zone_name  # AGGIUNGI QUESTA RIGA
                                            
                                            # Calcola i valori dalla configurazione
                                            hr_zones = config.get('heart_rates', {})
                                            hr_zone = hr_zones.get(zone_name, '')
                                            
                                            if hr_zone and '-' in hr_zone and 'max_hr' in hr_zone:
                                                # Formato: 62-76% max_hr
                                                max_hr = hr_zones.get('max_hr', 180)
                                                parts = hr_zone.split('-')
                                                min_percent = float(parts[0])
                                                max_percent = float(parts[1].split('%')[0])
                                                
                                                target.from_value = int(min_percent * max_hr / 100)
                                                target.to_value = int(max_percent * max_hr / 100)
                                        else:
                                            # Prova con zone di passo
                                            paces = config.get(f'sports.{sport_type}.paces', {})
                                            pace_zone = paces.get(zone_name, '')
                                            
                                            if pace_zone:
                                                target = Target('pace.zone')
                                                target.target_zone_name = zone_name  # AGGIUNGI QUESTA RIGA
                                                
                                                # Converti da min/km a m/s
                                                if '-' in pace_zone:
                                                    min_pace, max_pace = pace_zone.split('-')
                                                else:
                                                    min_pace = max_pace = pace_zone
                                                
                                                # Funzione per convertire mm:ss in secondi
                                                def pace_to_seconds(pace):
                                                    parts = pace.strip().split(':')
                                                    if len(parts) == 2:
                                                        return int(parts[0]) * 60 + int(parts[1])
                                                    return 0
                                                
                                                # Converti da mm:ss/km a m/s
                                                min_pace_secs = pace_to_seconds(min_pace)
                                                max_pace_secs = pace_to_seconds(max_pace)
                                                
                                                if min_pace_secs > 0 and max_pace_secs > 0:
                                                    # Converti da secondi/km a m/s
                                                    target.from_value = 1000 / max_pace_secs  # Passo più veloce (secondi minori)
                                                    target.to_value = 1000 / min_pace_secs    # Passo più lento (secondi maggiori)
                                    elif '-' in target_str:
                                        # Intervallo (es. "4:00-4:30" per passo)
                                        parts = target_str.split('-')
                                        
                                        # Determina il tipo di target
                                        if ':' in target_str:
                                            # Passo
                                            target = Target('pace.zone')
                                            
                                            # Funzione per convertire mm:ss in secondi
                                            def pace_to_seconds(pace):
                                                parts = pace.strip().split(':')
                                                if len(parts) == 2:
                                                    return int(parts[0]) * 60 + int(parts[1])
                                                return 0
                                            
                                            # Converti da mm:ss/km a m/s
                                            min_pace = parts[0].strip()
                                            max_pace = parts[1].strip()
                                            
                                            min_pace_secs = pace_to_seconds(min_pace)
                                            max_pace_secs = pace_to_seconds(max_pace)
                                            
                                            if min_pace_secs > 0 and max_pace_secs > 0:
                                                # Converti da secondi/km a m/s
                                                target.from_value = 1000 / max_pace_secs  # Passo più veloce (secondi minori)
                                                target.to_value = 1000 / min_pace_secs    # Passo più lento (secondi maggiori)
                                        elif 'bpm' in target_str.lower():
                                            # Frequenza cardiaca
                                            target = Target('heart.rate.zone')
                                            target.from_value = int(parts[0].strip())
                                            target.to_value = int(parts[1].split('bpm')[0].strip())
                                        else:
                                            # Potenza
                                            target = Target('power.zone')
                                            target.from_value = int(parts[0].strip())
                                            target.to_value = int(parts[1].strip())
                                
                                # Crea lo step
                                step = WorkoutStep(
                                    order=0,
                                    step_type=step_type,
                                    description=description,
                                    end_condition=end_condition,
                                    end_condition_value=end_value,
                                    target=target
                                )
                                
                                # Aggiungi allo step attuale o all'allenamento
                                if current_repeat:
                                    current_repeat.add_step(step)
                                else:
                                    workout.add_step(step)
                        
                        # Aggiungi alla lista degli importati
                        imported_workouts.append((workout_name, workout))
                        
                    except Exception as e:
                        logging.error(f"Errore nell'importazione dell'allenamento alla riga {row_idx}: {str(e)}")
                        raise ValueError(f"Errore nell'importazione dell'allenamento '{df.loc[row_idx, 'Nome']}': {str(e)}")
            
            return imported_workouts
            
        except Exception as e:
            logging.error(f"Errore nell'importazione degli allenamenti da Excel: {str(e)}")
            raise
    
    @staticmethod
    def export_workouts(workouts: List[Tuple[str, Workout]], file_path: str) -> None:
        """
        Esporta allenamenti in un file Excel.
        
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
            # Raggruppa gli allenamenti per tipo di sport
            sport_workouts = {}
            
            for name, workout in workouts:
                sport_type = workout.sport_type
                
                if sport_type not in sport_workouts:
                    sport_workouts[sport_type] = []
                
                sport_workouts[sport_type].append((name, workout))
            
            # Crea un dizionario di dataframe, uno per ogni tipo di sport
            dataframes = {}
            
            # Per ogni tipo di sport
            for sport_type, sport_items in sport_workouts.items():
                # Crea il dataframe
                df = pd.DataFrame(
                    columns=['Nome', 'Sport', 'Data', 'Tipo', 'Condizione di fine', 'Valore', 'Descrizione', 'Target']
                )
                
                # Indice corrente per le righe
                row_idx = 0
                
                # Per ogni allenamento in questo sport
                for name, workout in sport_items:
                    # Trova la data dell'allenamento se presente
                    workout_date = None
                    for step in workout.workout_steps:
                        if hasattr(step, 'date') and step.date:
                            workout_date = step.date
                            break
                    
                    # Aggiungi la riga dell'allenamento
                    df.loc[row_idx] = {
                        'Nome': name,
                        'Sport': sport_type.capitalize(),
                        'Data': workout_date,
                        'Tipo': '',
                        'Condizione di fine': '',
                        'Valore': '',
                        'Descrizione': '',
                        'Target': ''
                    }
                    
                    row_idx += 1
                    
                    # Aggiungi gli step (salta lo step con la data)
                    steps_to_add = [s for s in workout.workout_steps if not (hasattr(s, 'date') and s.date)]
                    row_idx = ExcelService.add_steps_to_dataframe(df, steps_to_add, row_idx)
                    
                    # Aggiungi una riga vuota tra gli allenamenti
                    row_idx += 1
                
                # Salva il dataframe
                dataframes[sport_type] = df
            
            # Salva il file Excel
            with pd.ExcelWriter(file_path) as writer:
                for sport_type, df in dataframes.items():
                    df.to_excel(writer, sheet_name=sport_type.capitalize(), index=False)
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione degli allenamenti in Excel: {str(e)}")
            raise
    
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