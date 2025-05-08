#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestione della configurazione per l'applicazione GarminPlannerGUI.
"""

import os
import yaml
import logging
import json
from typing import Dict, Any, Optional

# Configurazione predefinita
DEFAULT_CONFIG = {
    # Informazioni utente
    'athlete_name': '',
    'oauth_folder': '~/.garth',
    
    # Configurazione sport
    'sports': {
        'running': {
            'paces': {
                'Z1': '6:30-6:00',
                'Z2': '6:00-5:30',
                'Z3': '5:30-5:00',
                'Z4': '5:00-4:30',
                'Z5': '4:30-4:00',
                'recovery': '7:00-6:30',
                'threshold': '5:10-4:50',
                'marathon': '5:20-5:10',
                'race_pace': '5:10-4:50',
            },
            'margins': {
                'faster': '0:05',
                'slower': '0:05',
            }
        },
        'cycling': {
            'power_values': {
                'ftp': '250',
                'Z1': '125-175',
                'Z2': '175-215',
                'Z3': '215-250',
                'Z4': '250-300',
                'Z5': '300-375',
                'Z6': '375+',
                'recovery': '<125',
                'threshold': '235-265',
                'sweet_spot': '220-235',
            },
            'margins': {
                'power_up': 10,
                'power_down': 10,
            }
        },
        'swimming': {
            'paces': {
                'Z1': '2:30-2:15',
                'Z2': '2:15-2:00',
                'Z3': '2:00-1:45',
                'Z4': '1:45-1:30',
                'Z5': '1:30-1:15',
                'recovery': '2:45-2:30',
                'threshold': '1:55-1:40',
                'sprint': '1:25-1:15',
            },
            'margins': {
                'faster': '0:05',
                'slower': '0:05',
            }
        }
    },
    
    # Configurazione frequenza cardiaca (comune a tutti gli sport)
    'heart_rates': {
        'max_hr': 180,
        'rest_hr': 60,
        'Z1_HR': '62-76% max_hr',
        'Z2_HR': '76-85% max_hr',
        'Z3_HR': '85-91% max_hr',
        'Z4_HR': '91-95% max_hr',
        'Z5_HR': '95-100% max_hr',
    },
    'hr_margins': {
        'hr_up': 5,
        'hr_down': 5,
    },
    
    # Configurazione pianificazione
    'planning': {
        'name_prefix': '',
        'race_day': '',
        'preferred_days': [1, 3, 5],  # 0=Monday, 6=Sunday
    },
    
    # Preferenze UI
    'ui': {
        'theme': 'light',
        'font_size': 'medium',
        'calendar_first_day': 1,  # 0=Monday, 6=Sunday
        'language': 'it',
    },
    
    # Percorsi dei file
    'paths': {
        'last_import_dir': '',
        'last_export_dir': '',
    }
}

class Config:
    """Classe per gestire la configurazione dell'applicazione."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Inizializza la configurazione.
        
        Args:
            config_path: Percorso del file di configurazione.
        """
        self.config_path = os.path.expanduser(config_path)
        self.config = DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> bool:
        """
        Carica la configurazione dal file.
        
        Returns:
            True se il caricamento è riuscito, False altrimenti.
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f)
                
                if loaded_config:
                    # Aggiorna la configurazione mantenendo i valori predefiniti per le chiavi mancanti
                    self._recursive_update(self.config, loaded_config)
                
                logging.info(f"Configuration loaded from {self.config_path}")
                return True
            else:
                logging.info(f"Configuration file {self.config_path} not found, using defaults")
                return False
                
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
            return False
    
    def save(self) -> bool:
        """
        Salva la configurazione nel file.
        
        Returns:
            True se il salvataggio è riuscito, False altrimenti.
        """
        try:
            # Assicurati che la directory esista
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            
            logging.info(f"Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Ottiene un valore dalla configurazione.
        
        Args:
            key: Chiave del valore da ottenere (può essere nidificata con punto, es. 'sports.running.paces.Z1')
            default: Valore predefinito se la chiave non esiste
            
        Returns:
            Il valore della configurazione o il valore predefinito
        """
        parts = key.split('.')
        value = self.config
        
        try:
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Imposta un valore nella configurazione.
        
        Args:
            key: Chiave del valore da impostare (può essere nidificata con punto)
            value: Valore da impostare
        """
        parts = key.split('.')
        config = self.config
        
        # Naviga fino all'ultimo elemento
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        
        # Imposta il valore
        config[parts[-1]] = value
    
    def _recursive_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """
        Aggiorna ricorsivamente un dizionario mantenendo la struttura originale.
        
        Args:
            base_dict: Dizionario di base da aggiornare
            update_dict: Dizionario con i nuovi valori
        """
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._recursive_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def to_json(self) -> str:
        """
        Converte la configurazione in una stringa JSON.
        
        Returns:
            Stringa JSON della configurazione
        """
        return json.dumps(self.config, indent=2)
    
    def from_json(self, json_str: str) -> bool:
        """
        Carica la configurazione da una stringa JSON.
        
        Args:
            json_str: Stringa JSON da caricare
            
        Returns:
            True se il caricamento è riuscito, False altrimenti
        """
        try:
            loaded_config = json.loads(json_str)
            self._recursive_update(self.config, loaded_config)
            return True
        except Exception as e:
            logging.error(f"Error loading configuration from JSON: {e}")
            return False
    
    def get_sport_paces(self, sport: str) -> Dict:
        """
        Ottiene le zone di passo per uno sport specifico.
        
        Args:
            sport: Nome dello sport (running, cycling, swimming)
            
        Returns:
            Dizionario con le zone di passo
        """
        return self.get(f'sports.{sport}.paces', {})
    
    def get_heart_rates(self) -> Dict:
        """
        Ottiene le zone di frequenza cardiaca.
        
        Returns:
            Dizionario con le zone di frequenza cardiaca
        """
        return self.get('heart_rates', {})
    
    def get_power_values(self) -> Dict:
        """
        Ottiene i valori di potenza per il ciclismo.
        
        Returns:
            Dizionario con i valori di potenza
        """
        return self.get('sports.cycling.power_values', {})

# Istanza singleton della configurazione
_config_instance: Optional[Config] = None

def get_config(config_path: str = 'config.yaml') -> Config:
    """
    Ottiene l'istanza singleton della configurazione.
    
    Args:
        config_path: Percorso del file di configurazione
        
    Returns:
        Istanza della configurazione
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance

def reset_config() -> None:
    """Reimposta l'istanza della configurazione."""
    global _config_instance
    _config_instance = None
