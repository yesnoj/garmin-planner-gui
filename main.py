#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Punto di ingresso principale per l'applicazione GarminPlannerGUI.
"""

import os
import sys
import logging
import argparse
from tkinter import Tk

# Configurazione del logging
def setup_logging(log_level=logging.INFO):
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=log_level, format=log_format)
    
    # Crea una directory logs se non esiste
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Aggiungi un FileHandler per salvare i log su file
    file_handler = logging.FileHandler('logs/garmin_planner.log')
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Aggiungi l'handler al logger root
    logging.getLogger().addHandler(file_handler)
    
    # Log di debug se viene specificato
    logging.info("Logging setup completed.")

def parse_arguments():
    """Parsa gli argomenti da linea di comando."""
    parser = argparse.ArgumentParser(description='GarminPlannerGUI - Applicazione per la gestione avanzata di allenamenti su Garmin Connect')
    
    parser.add_argument('--debug', action='store_true', help='Abilita il logging di debug')
    parser.add_argument('--config', default='config.yaml', help='Percorso del file di configurazione')
    
    return parser.parse_args()

def main():
    """Funzione principale dell'applicazione."""
    # Parsa gli argomenti
    args = parse_arguments()
    
    # Setup del logging
    if args.debug:
        setup_logging(logging.DEBUG)
    else:
        setup_logging()
    
    logging.info("Starting GarminPlannerGUI...")
    
    # Importa il modulo app solo dopo la configurazione del logging
    from gui.app import GarminPlannerApp
    
    # Crea l'applicazione Tkinter
    root = Tk()
    app = GarminPlannerApp(root, config_path=args.config)
    
    # Avvia il loop principale dell'applicazione
    root.mainloop()
    
    logging.info("GarminPlannerGUI terminated.")

if __name__ == "__main__":
    main()
