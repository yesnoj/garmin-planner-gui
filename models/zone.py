#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modello per le zone di allenamento.
"""

import re
from typing import Dict, Any, List, Tuple, Optional, Union


class Zone:
    """Classe base per le zone di allenamento."""
    
    def __init__(self, name: str, description: Optional[str] = None):
        """
        Inizializza una zona di allenamento.
        
        Args:
            name: Nome della zona
            description: Descrizione della zona (opzionale)
        """
        self.name = name
        self.description = description
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte la zona in un dizionario.
        
        Returns:
            Dizionario con i dati della zona
        """
        return {
            'name': self.name,
            'description': self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Zone':
        """
        Crea una zona da un dizionario.
        
        Args:
            data: Dizionario con i dati della zona
            
        Returns:
            Istanza di Zone
        """
        return cls(
            name=data.get('name', ''),
            description=data.get('description')
        )


class PaceZone(Zone):
    """Zona di passo per corsa o nuoto."""
    
    def __init__(self, name: str, min_pace: str, max_pace: str, description: Optional[str] = None):
        """
        Inizializza una zona di passo.
        
        Args:
            name: Nome della zona
            min_pace: Passo minimo (formato mm:ss)
            max_pace: Passo massimo (formato mm:ss)
            description: Descrizione della zona (opzionale)
        """
        super().__init__(name, description)
        self.min_pace = min_pace
        self.max_pace = max_pace
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte la zona in un dizionario.
        
        Returns:
            Dizionario con i dati della zona
        """
        data = super().to_dict()
        data.update({
            'min_pace': self.min_pace,
            'max_pace': self.max_pace,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaceZone':
        """
        Crea una zona da un dizionario.
        
        Args:
            data: Dizionario con i dati della zona
            
        Returns:
            Istanza di PaceZone
        """
        return cls(
            name=data.get('name', ''),
            min_pace=data.get('min_pace', '0:00'),
            max_pace=data.get('max_pace', '0:00'),
            description=data.get('description')
        )
    
    @classmethod
    def from_string(cls, name: str, value: str, description: Optional[str] = None) -> 'PaceZone':
        """
        Crea una zona da una stringa (formato mm:ss-mm:ss).
        
        Args:
            name: Nome della zona
            value: Valore della zona (formato mm:ss-mm:ss o mm:ss)
            description: Descrizione della zona (opzionale)
            
        Returns:
            Istanza di PaceZone
            
        Raises:
            ValueError: Se il formato della stringa non è valido
        """
        if '-' in value:
            # Formato mm:ss-mm:ss
            parts = value.split('-')
            if len(parts) != 2:
                raise ValueError(f"Formato non valido per la zona di passo: {value}")
            
            min_pace = parts[0].strip()
            max_pace = parts[1].strip()
        else:
            # Formato mm:ss
            min_pace = value.strip()
            max_pace = value.strip()
        
        # Verifica che i valori siano nel formato mm:ss
        for pace in [min_pace, max_pace]:
            if not re.match(r'^\d{1,2}:\d{2}$', pace):
                raise ValueError(f"Formato non valido per il passo: {pace}")
        
        return cls(name, min_pace, max_pace, description)
    
    def to_string(self) -> str:
        """
        Converte la zona in una stringa.
        
        Returns:
            Stringa nel formato mm:ss-mm:ss
        """
        if self.min_pace == self.max_pace:
            return self.min_pace
        else:
            return f"{self.min_pace}-{self.max_pace}"


class HeartRateZone(Zone):
    """Zona di frequenza cardiaca."""
    
    def __init__(self, name: str, min_hr: Union[int, str], max_hr: Union[int, str], 
                description: Optional[str] = None):
        """
        Inizializza una zona di frequenza cardiaca.
        
        Args:
            name: Nome della zona
            min_hr: Frequenza cardiaca minima (bpm o percentuale)
            max_hr: Frequenza cardiaca massima (bpm o percentuale)
            description: Descrizione della zona (opzionale)
        """
        super().__init__(name, description)
        self.min_hr = min_hr
        self.max_hr = max_hr
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte la zona in un dizionario.
        
        Returns:
            Dizionario con i dati della zona
        """
        data = super().to_dict()
        data.update({
            'min_hr': self.min_hr,
            'max_hr': self.max_hr,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeartRateZone':
        """
        Crea una zona da un dizionario.
        
        Args:
            data: Dizionario con i dati della zona
            
        Returns:
            Istanza di HeartRateZone
        """
        return cls(
            name=data.get('name', ''),
            min_hr=data.get('min_hr', 0),
            max_hr=data.get('max_hr', 0),
            description=data.get('description')
        )
    
    @classmethod
    def from_string(cls, name: str, value: str, description: Optional[str] = None) -> 'HeartRateZone':
        """
        Crea una zona da una stringa (formato N-N o N% max_hr o N-N% max_hr).
        
        Args:
            name: Nome della zona
            value: Valore della zona (formato N-N o N% max_hr o N-N% max_hr)
            description: Descrizione della zona (opzionale)
            
        Returns:
            Istanza di HeartRateZone
            
        Raises:
            ValueError: Se il formato della stringa non è valido
        """
        # Verifica se è una percentuale
        is_percentage = 'max_hr' in value
        
        if '-' in value:
            # Formato N-N o N-N% max_hr
            parts = value.split('-')
            if len(parts) != 2:
                raise ValueError(f"Formato non valido per la zona di frequenza cardiaca: {value}")
            
            if is_percentage:
                # Formato N-N% max_hr
                try:
                    percent_parts = parts[1].split('%')
                    min_hr = parts[0].strip() + '% max_hr'
                    max_hr = percent_parts[0].strip() + '% max_hr'
                except:
                    raise ValueError(f"Formato non valido per la zona di frequenza cardiaca: {value}")
            else:
                # Formato N-N
                min_hr = parts[0].strip()
                max_hr = parts[1].strip()
        else:
            # Formato N o N% max_hr
            if is_percentage:
                # Formato N% max_hr
                try:
                    percent_parts = value.split('%')
                    min_hr = max_hr = percent_parts[0].strip() + '% max_hr'
                except:
                    raise ValueError(f"Formato non valido per la zona di frequenza cardiaca: {value}")
            else:
                # Formato N
                min_hr = max_hr = value.strip()
        
        return cls(name, min_hr, max_hr, description)
    
    def to_string(self) -> str:
        """
        Converte la zona in una stringa.
        
        Returns:
            Stringa nel formato N-N o N% max_hr o N-N% max_hr
        """
        if self.min_hr == self.max_hr:
            return str(self.min_hr)
        else:
            # Verifica se sono percentuali
            min_is_percent = isinstance(self.min_hr, str) and '% max_hr' in self.min_hr
            max_is_percent = isinstance(self.max_hr, str) and '% max_hr' in self.max_hr
            
            if min_is_percent and max_is_percent:
                # Formato N-N% max_hr
                min_val = self.min_hr.split('%')[0].strip()
                max_val = self.max_hr.split('%')[0].strip()
                return f"{min_val}-{max_val}% max_hr"
            else:
                # Formato N-N
                return f"{self.min_hr}-{self.max_hr}"


class PowerZone(Zone):
    """Zona di potenza per il ciclismo."""
    
    def __init__(self, name: str, min_power: Union[int, str], max_power: Union[int, str], 
                description: Optional[str] = None):
        """
        Inizializza una zona di potenza.
        
        Args:
            name: Nome della zona
            min_power: Potenza minima (watt)
            max_power: Potenza massima (watt)
            description: Descrizione della zona (opzionale)
        """
        super().__init__(name, description)
        self.min_power = min_power
        self.max_power = max_power
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte la zona in un dizionario.
        
        Returns:
            Dizionario con i dati della zona
        """
        data = super().to_dict()
        data.update({
            'min_power': self.min_power,
            'max_power': self.max_power,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PowerZone':
        """
        Crea una zona da un dizionario.
        
        Args:
            data: Dizionario con i dati della zona
            
        Returns:
            Istanza di PowerZone
        """
        return cls(
            name=data.get('name', ''),
            min_power=data.get('min_power', 0),
            max_power=data.get('max_power', 0),
            description=data.get('description')
        )
    
    @classmethod
    def from_string(cls, name: str, value: str, description: Optional[str] = None) -> 'PowerZone':
        """
        Crea una zona da una stringa (formato N-N o N o <N o N+).
        
        Args:
            name: Nome della zona
            value: Valore della zona (formato N-N o N o <N o N+)
            description: Descrizione della zona (opzionale)
            
        Returns:
            Istanza di PowerZone
            
        Raises:
            ValueError: Se il formato della stringa non è valido
        """
        if value.startswith('<'):
            # Formato <N
            try:
                power = int(value[1:].strip())
                min_power = 0
                max_power = power
            except ValueError:
                raise ValueError(f"Formato non valido per la zona di potenza: {value}")
        elif value.endswith('+'):
            # Formato N+
            try:
                power = int(value[:-1].strip())
                min_power = power
                max_power = 9999  # Valore alto per indicare "infinito"
            except ValueError:
                raise ValueError(f"Formato non valido per la zona di potenza: {value}")
        elif '-' in value:
            # Formato N-N
            parts = value.split('-')
            if len(parts) != 2:
                raise ValueError(f"Formato non valido per la zona di potenza: {value}")
            
            try:
                min_power = int(parts[0].strip())
                max_power = int(parts[1].strip())
            except ValueError:
                raise ValueError(f"Formato non valido per la zona di potenza: {value}")
        else:
            # Formato N
            try:
                power = int(value.strip())
                min_power = max_power = power
            except ValueError:
                raise ValueError(f"Formato non valido per la zona di potenza: {value}")
        
        return cls(name, min_power, max_power, description)
    
    def to_string(self) -> str:
        """
        Converte la zona in una stringa.
        
        Returns:
            Stringa nel formato N-N o N o <N o N+
        """
        if isinstance(self.min_power, int) and self.min_power == 0 and isinstance(self.max_power, int) and self.max_power > 0:
            # Formato <N
            return f"<{self.max_power}"
        elif isinstance(self.min_power, int) and self.min_power > 0 and isinstance(self.max_power, int) and self.max_power == 9999:
            # Formato N+
            return f"{self.min_power}+"
        elif self.min_power == self.max_power:
            # Formato N
            return str(self.min_power)
        else:
            # Formato N-N
            return f"{self.min_power}-{self.max_power}"


class ZoneSet:
    """Insieme di zone dello stesso tipo."""
    
    def __init__(self, name: str, sport_type: str, zone_type: str, zones: Optional[List[Zone]] = None):
        """
        Inizializza un insieme di zone.
        
        Args:
            name: Nome dell'insieme di zone
            sport_type: Tipo di sport (running, cycling, swimming)
            zone_type: Tipo di zona (pace, heart_rate, power)
            zones: Lista di zone (opzionale)
        """
        self.name = name
        self.sport_type = sport_type
        self.zone_type = zone_type
        self.zones = zones or []
    
    def add_zone(self, zone: Zone) -> None:
        """
        Aggiunge una zona all'insieme.
        
        Args:
            zone: Zona da aggiungere
        """
        self.zones.append(zone)
    
    def remove_zone(self, zone_name: str) -> None:
        """
        Rimuove una zona dall'insieme.
        
        Args:
            zone_name: Nome della zona da rimuovere
        """
        self.zones = [z for z in self.zones if z.name != zone_name]
    
    def get_zone(self, zone_name: str) -> Optional[Zone]:
        """
        Ottiene una zona dall'insieme.
        
        Args:
            zone_name: Nome della zona da ottenere
            
        Returns:
            Zona o None se non trovata
        """
        for zone in self.zones:
            if zone.name == zone_name:
                return zone
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte l'insieme di zone in un dizionario.
        
        Returns:
            Dizionario con i dati dell'insieme di zone
        """
        return {
            'name': self.name,
            'sport_type': self.sport_type,
            'zone_type': self.zone_type,
            'zones': [z.to_dict() for z in self.zones],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ZoneSet':
        """
        Crea un insieme di zone da un dizionario.
        
        Args:
            data: Dizionario con i dati dell'insieme di zone
            
        Returns:
            Istanza di ZoneSet
        """
        zone_set = cls(
            name=data.get('name', ''),
            sport_type=data.get('sport_type', ''),
            zone_type=data.get('zone_type', ''),
        )
        
        # Aggiungi le zone
        zone_type = data.get('zone_type', '')
        for zone_data in data.get('zones', []):
            if zone_type == 'pace':
                zone = PaceZone.from_dict(zone_data)
            elif zone_type == 'heart_rate':
                zone = HeartRateZone.from_dict(zone_data)
            elif zone_type == 'power':
                zone = PowerZone.from_dict(zone_data)
            else:
                zone = Zone.from_dict(zone_data)
            
            zone_set.add_zone(zone)
        
        return zone_set