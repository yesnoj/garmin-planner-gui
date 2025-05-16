import PyInstaller.__main__
import os

# Ottieni il percorso corrente
current_dir = os.path.dirname(os.path.abspath(__file__))

# Definisci i percorsi per le risorse
config_file = os.path.join(current_dir, 'config.yaml')
icon_file = os.path.join(current_dir, 'assets', 'garmin_planner_icon.ico')

# Verifica che il file dell'icona esista
if not os.path.exists(icon_file):
    print(f"ATTENZIONE: File icona non trovato in: {icon_file}")
    print("L'eseguibile verrà creato senza icona personalizzata.")
    icon_param = []
else:
    print(f"Icona trovata: {icon_file}")
    icon_param = [f'--icon={icon_file}']

# Definisci i parametri per PyInstaller
params = [
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
]

# Aggiungi il parametro dell'icona se disponibile
params.extend(icon_param)

# Crea anche la cartella assets nella directory di distribuzione
assets_dir = os.path.join(current_dir, 'assets')
if os.path.exists(assets_dir):
    params.append(f'--add-data={assets_dir};assets')
    print(f"Aggiunta cartella assets: {assets_dir}")

# Esegui PyInstaller
print("Avvio della compilazione con PyInstaller...")
PyInstaller.__main__.run(params)
print("Compilazione completata.")