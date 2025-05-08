#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servizio per la gestione dei file Excel.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from garmin_planner_gui.models.workout import Workout, WorkoutStep, Target


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
                        
                        # Righe degli step
                        next_workout_row = workout_rows[i + 1] if i + 1 < len(workout_rows) else len(df)
                        step_rows = range(row_idx + 1, next_workout_row)
                        
                        # Crea l'allenamento
                        workout = Workout(sport_type, workout_name)
                        
                        # Per ogni step
                        current_repeat = None
                        
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
                                    if '-' in target_str:
                                        # Intervallo (es. "4:00-4:30" per passo)
                                        parts = target_str.split('-')
                                        
                                        # Determina il tipo di target
                                        if ':' in target_str:
                                            # Passo
                                            target = Target('pace.zone')
                                        elif 'bpm' in target_str.lower():
                                            # Frequenza cardiaca
                                            target = Target('heart.rate.zone')
                                        else:
                                            # Potenza
                                            target = Target('power.zone')
                                
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
                    columns=['Nome', 'Sport', 'Tipo', 'Condizione di fine', 'Valore', 'Descrizione', 'Target']
                )
                
                # Indice corrente per le righe
                row_idx = 0
                
                # Per ogni allenamento in questo sport
                for name, workout in sport_items:
                    # Aggiungi la riga dell'allenamento
                    df.loc[row_idx] = {
                        'Nome': name,
                        'Sport': sport_type.capitalize(),
                        'Tipo': '',
                        'Condizione di fine': '',
                        'Valore': '',
                        'Descrizione': '',
                        'Target': ''
                    }
                    
                    row_idx += 1
                    
                    # Aggiungi gli step
                    row_idx = ExcelService.add_steps_to_dataframe(df, workout.workout_steps, row_idx)
                    
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
        
        # Per ogni step
        for step in steps:
            # Caso speciale: repeat
            if step.step_type == 'repeat':
                # Aggiungi la riga repeat
                df.loc[row_idx] = {
                    'Nome': '',
                    'Sport': '',
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
                    if step.target.target == 'pace.zone' and step.target.from_value and step.target.to_value:
                        # Converti da m/s a min/km
                        min_pace_secs = int(1000 / step.target.from_value)
                        max_pace_secs = int(1000 / step.target.to_value)
                        
                        min_pace = f"{min_pace_secs // 60}:{min_pace_secs % 60:02d}"
                        max_pace = f"{max_pace_secs // 60}:{max_pace_secs % 60:02d}"
                        
                        if min_pace == max_pace:
                            target_str = min_pace
                        else:
                            target_str = f"{min_pace}-{max_pace}"
                    elif step.target.target == 'heart.rate.zone' and step.target.from_value and step.target.to_value:
                        target_str = f"{step.target.from_value}-{step.target.to_value} bpm"
                    elif step.target.target == 'power.zone' and step.target.from_value and step.target.to_value:
                        target_str = f"{step.target.from_value}-{step.target.to_value} W"
                
                # Aggiungi lo step al dataframe
                df.loc[row_idx] = {
                    'Nome': '',
                    'Sport': '',
                    'Tipo': f"{indent}{step.step_type}",
                    'Condizione di fine': step.end_condition,
                    'Valore': end_value,
                    'Descrizione': step.description,
                    'Target': target_str
                }
                
                row_idx += 1
        
        return row_idx