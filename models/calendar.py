#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modello per il calendario di allenamenti.
"""

import datetime
import calendar
from typing import Dict, Any, List, Tuple, Optional, Union


class CalendarItem:
    """Item del calendario (allenamento o attività)."""
    
    def __init__(self, item_id: str, item_type: str, date: str, title: str, 
               sport_type: str, description: Optional[str] = None, 
               source: str = 'garmin', source_id: Optional[str] = None):
        """
        Inizializza un item del calendario.
        
        Args:
            item_id: ID dell'item
            item_type: Tipo dell'item (workout, activity)
            date: Data dell'item (formato YYYY-MM-DD)
            title: Titolo dell'item
            sport_type: Tipo di sport
            description: Descrizione dell'item (opzionale)
            source: Origine dell'item (garmin, local)
            source_id: ID dell'item nella fonte di origine (opzionale)
        """
        self.item_id = item_id
        self.item_type = item_type
        self.date = date
        self.title = title
        self.sport_type = sport_type
        self.description = description
        self.source = source
        self.source_id = source_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte l'item in un dizionario.
        
        Returns:
            Dizionario con i dati dell'item
        """
        return {
            'item_id': self.item_id,
            'item_type': self.item_type,
            'date': self.date,
            'title': self.title,
            'sport_type': self.sport_type,
            'description': self.description,
            'source': self.source,
            'source_id': self.source_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalendarItem':
        """
        Crea un item da un dizionario.
        
        Args:
            data: Dizionario con i dati dell'item
            
        Returns:
            Istanza di CalendarItem
        """
        return cls(
            item_id=data.get('item_id', ''),
            item_type=data.get('item_type', ''),
            date=data.get('date', ''),
            title=data.get('title', ''),
            sport_type=data.get('sport_type', ''),
            description=data.get('description'),
            source=data.get('source', 'garmin'),
            source_id=data.get('source_id')
        )
    
    @classmethod
    def from_garmin_workout(cls, workout: Dict[str, Any]) -> 'CalendarItem':
        """
        Crea un item da un workout di Garmin Connect.
        
        Args:
            workout: Dizionario con i dati del workout
            
        Returns:
            Istanza di CalendarItem
        """
        # Estrai i dati necessari
        item_id = str(workout.get('id', ''))
        date = workout.get('date', '')
        title = workout.get('title', '')
        
        # Estrai il tipo di sport
        sport_type = 'running'  # Default
        if 'sportTypeKey' in workout:
            sport_type = workout['sportTypeKey']
        
        # ID del workout
        workout_id = str(workout.get('workoutId', ''))
        
        return cls(
            item_id=item_id,
            item_type='workout',
            date=date,
            title=title,
            sport_type=sport_type,
            source='garmin',
            source_id=workout_id
        )
    
    @classmethod
    def from_garmin_activity(cls, activity: Dict[str, Any]) -> 'CalendarItem':
        """
        Crea un item da un'attività di Garmin Connect.
        
        Args:
            activity: Dizionario con i dati dell'attività
            
        Returns:
            Istanza di CalendarItem
        """
        # Estrai i dati necessari
        item_id = str(activity.get('activityId', ''))
        
        # Estrai la data
        date = ''
        if 'startTimeLocal' in activity:
            # Potrebbe essere nel formato "2025-04-29T20:05:43" o "2025-04-29 20:05:43"
            start_time = activity['startTimeLocal']
            if 'T' in start_time:
                date = start_time.split('T')[0]
            else:
                date = start_time.split(' ')[0]
        
        # Estrai il titolo
        title = activity.get('activityName', '')
        
        # Estrai il tipo di sport
        sport_type = 'running'  # Default
        if 'activityType' in activity and 'typeKey' in activity['activityType']:
            sport_type = activity['activityType']['typeKey']
        
        return cls(
            item_id=item_id,
            item_type='activity',
            date=date,
            title=title,
            sport_type=sport_type,
            source='garmin',
            source_id=item_id
        )


class CalendarDay:
    """Giorno del calendario con gli item associati."""
    
    def __init__(self, date: str):
        """
        Inizializza un giorno del calendario.
        
        Args:
            date: Data del giorno (formato YYYY-MM-DD)
        """
        self.date = date
        self.items = []
    
    def add_item(self, item: CalendarItem) -> None:
        """
        Aggiunge un item al giorno.
        
        Args:
            item: Item da aggiungere
        """
        self.items.append(item)
    
    def remove_item(self, item_id: str) -> None:
        """
        Rimuove un item dal giorno.
        
        Args:
            item_id: ID dell'item da rimuovere
        """
        self.items = [i for i in self.items if i.item_id != item_id]
    
    def get_item(self, item_id: str) -> Optional[CalendarItem]:
        """
        Ottiene un item dal giorno.
        
        Args:
            item_id: ID dell'item da ottenere
            
        Returns:
            Item o None se non trovato
        """
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il giorno in un dizionario.
        
        Returns:
            Dizionario con i dati del giorno
        """
        return {
            'date': self.date,
            'items': [i.to_dict() for i in self.items],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalendarDay':
        """
        Crea un giorno da un dizionario.
        
        Args:
            data: Dizionario con i dati del giorno
            
        Returns:
            Istanza di CalendarDay
        """
        day = cls(data.get('date', ''))
        
        # Aggiungi gli item
        for item_data in data.get('items', []):
            item = CalendarItem.from_dict(item_data)
            day.add_item(item)
        
        return day


class CalendarMonth:
    """Mese del calendario con i giorni associati."""
    
    def __init__(self, year: int, month: int):
        """
        Inizializza un mese del calendario.
        
        Args:
            year: Anno del mese
            month: Mese (1-12)
        """
        self.year = year
        self.month = month
        self.days = {}
    
    def add_day(self, day: CalendarDay) -> None:
        """
        Aggiunge un giorno al mese.
        
        Args:
            day: Giorno da aggiungere
        """
        self.days[day.date] = day
    
    def get_day(self, date: str) -> Optional[CalendarDay]:
        """
        Ottiene un giorno dal mese.
        
        Args:
            date: Data del giorno (formato YYYY-MM-DD)
            
        Returns:
            Giorno o None se non trovato
        """
        return self.days.get(date)
    
    def get_or_create_day(self, date: str) -> CalendarDay:
        """
        Ottiene un giorno dal mese o lo crea se non esiste.
        
        Args:
            date: Data del giorno (formato YYYY-MM-DD)
            
        Returns:
            Giorno
        """
        if date not in self.days:
            self.days[date] = CalendarDay(date)
        return self.days[date]
    
    def add_item(self, item: CalendarItem) -> None:
        """
        Aggiunge un item al mese.
        
        Args:
            item: Item da aggiungere
        """
        # Verifica che la data dell'item sia in questo mese
        date_obj = datetime.datetime.strptime(item.date, '%Y-%m-%d')
        if date_obj.year != self.year or date_obj.month != self.month:
            return
        
        # Ottieni o crea il giorno
        day = self.get_or_create_day(item.date)
        
        # Aggiungi l'item
        day.add_item(item)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il mese in un dizionario.
        
        Returns:
            Dizionario con i dati del mese
        """
        return {
            'year': self.year,
            'month': self.month,
            'days': {date: day.to_dict() for date, day in self.days.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalendarMonth':
        """
        Crea un mese da un dizionario.
        
        Args:
            data: Dizionario con i dati del mese
            
        Returns:
            Istanza di CalendarMonth
        """
        month = cls(
            year=data.get('year', 0),
            month=data.get('month', 0)
        )
        
        # Aggiungi i giorni
        for date, day_data in data.get('days', {}).items():
            day = CalendarDay.from_dict(day_data)
            month.add_day(day)
        
        return month
    
    @classmethod
    def from_garmin_data(cls, year: int, month: int, data: Dict[str, Any]) -> 'CalendarMonth':
        """
        Crea un mese da dati di Garmin Connect.
        
        Args:
            year: Anno del mese
            month: Mese (1-12)
            data: Dizionario con i dati del mese da Garmin Connect
            
        Returns:
            Istanza di CalendarMonth
        """
        month_obj = cls(year, month)
        
        # Aggiungi gli item dal calendario
        if 'calendarItems' in data:
            for item in data['calendarItems']:
                if item.get('itemType') == 'workout':
                    calendar_item = CalendarItem.from_garmin_workout(item)
                    month_obj.add_item(calendar_item)
        
        return month_obj


class Calendar:
    """Calendario di allenamenti."""
    
    def __init__(self):
        """Inizializza un calendario."""
        self.months = {}
    
    def add_month(self, month: CalendarMonth) -> None:
        """
        Aggiunge un mese al calendario.
        
        Args:
            month: Mese da aggiungere
        """
        key = f"{month.year}-{month.month:02d}"
        self.months[key] = month
    
    def get_month(self, year: int, month: int) -> Optional[CalendarMonth]:
        """
        Ottiene un mese dal calendario.
        
        Args:
            year: Anno del mese
            month: Mese (1-12)
            
        Returns:
            Mese o None se non trovato
        """
        key = f"{year}-{month:02d}"
        return self.months.get(key)
    
    def get_or_create_month(self, year: int, month: int) -> CalendarMonth:
        """
        Ottiene un mese dal calendario o lo crea se non esiste.
        
        Args:
            year: Anno del mese
            month: Mese (1-12)
            
        Returns:
            Mese
        """
        key = f"{year}-{month:02d}"
        if key not in self.months:
            self.months[key] = CalendarMonth(year, month)
        return self.months[key]
    
    def add_item(self, item: CalendarItem) -> None:
        """
        Aggiunge un item al calendario.
        
        Args:
            item: Item da aggiungere
        """
        # Estrai anno e mese dalla data dell'item
        date_obj = datetime.datetime.strptime(item.date, '%Y-%m-%d')
        year = date_obj.year
        month = date_obj.month
        
        # Ottieni o crea il mese
        month_obj = self.get_or_create_month(year, month)
        
        # Aggiungi l'item
        month_obj.add_item(item)
    
    def get_items_by_date_range(self, start_date: str, end_date: str) -> List[CalendarItem]:
        """
        Ottiene gli item in un intervallo di date.
        
        Args:
            start_date: Data di inizio (formato YYYY-MM-DD)
            end_date: Data di fine (formato YYYY-MM-DD)
            
        Returns:
            Lista di item
        """
        # Converti le date in oggetti datetime
        start_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        # Raccogli gli item
        items = []
        
        # Per ogni mese nell'intervallo
        current = start_obj
        while current <= end_obj:
            # Ottieni il mese
            month_obj = self.get_month(current.year, current.month)
            
            if month_obj:
                # Per ogni giorno nel mese
                for date, day in month_obj.days.items():
                    # Verifica che la data sia nell'intervallo
                    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                    if start_obj <= date_obj <= end_obj:
                        items.extend(day.items)
            
            # Passa al mese successivo
            if current.month == 12:
                current = datetime.datetime(current.year + 1, 1, 1)
            else:
                current = datetime.datetime(current.year, current.month + 1, 1)
        
        return items
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il calendario in un dizionario.
        
        Returns:
            Dizionario con i dati del calendario
        """
        return {
            'months': {key: month.to_dict() for key, month in self.months.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Calendar':
        """
        Crea un calendario da un dizionario.
        
        Args:
            data: Dizionario con i dati del calendario
            
        Returns:
            Istanza di Calendar
        """
        calendar_obj = cls()
        
        # Aggiungi i mesi
        for key, month_data in data.get('months', {}).items():
            month = CalendarMonth.from_dict(month_data)
            calendar_obj.add_month(month)
        
        return calendar_obj