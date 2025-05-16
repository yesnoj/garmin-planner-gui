import PyInstaller.__main__
import os

# Ottieni il percorso corrente
current_dir = os.path.dirname(os.path.abspath(__file__))

# Definisci i percorsi per le risorse
config_file = os.path.join(current_dir, 'config.yaml')

# Definisci i parametri per PyInstaller
PyInstaller.__main__.run([
    'main.py',                      # Script principale
    '--name=GarminPlannerGUI',      # Nome dell'eseguibile
    '--onefile',                    # Crea un singolo file eseguibile
    '--windowed',                   # Non mostrare la console quando l'app è in esecuzione
    f'--add-data={config_file};.',  # Includi il file di configurazione
    '--hidden-import=pandas',       # Importazioni nascoste
    '--hidden-import=openpyxl',
    '--hidden-import=yaml',
    '--hidden-import=garth',        # Libreria per Garmin Connect
    '--hidden-import=tkinter',
    '--hidden-import=calendar',
    '--hidden-import=re',
    '--hidden-import=logging',
    '--hidden-import=json',
])