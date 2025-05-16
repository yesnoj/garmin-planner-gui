# Manuale utente di GarminPlannerGUI

**Versione 1.0.0**

## Indice
1. [Introduzione](#introduzione)
2. [Installazione](#installazione)
3. [Primo avvio](#primo-avvio)
4. [Login a Garmin Connect](#login-a-garmin-connect)
5. [Editor di allenamenti](#editor-di-allenamenti)
   - [Creazione di un nuovo allenamento](#creazione-di-un-nuovo-allenamento)
   - [Modifica di un allenamento esistente](#modifica-di-un-allenamento-esistente)
   - [Aggiunta di step](#aggiunta-di-step)
   - [Creazione di ripetute](#creazione-di-ripetute)
   - [Aggiunta di target (zone)](#aggiunta-di-target-zone)
   - [Salvataggio degli allenamenti](#salvataggio-degli-allenamenti)
6. [Calendario](#calendario)
   - [Visualizzazione calendario](#visualizzazione-calendario)
   - [Pianificazione allenamenti](#pianificazione-allenamenti)
   - [Sincronizzazione con Garmin Connect](#sincronizzazione-con-garmin-connect)
7. [Gestione zone](#gestione-zone)
   - [Configurazione zone di passo](#configurazione-zone-di-passo)
   - [Configurazione zone di frequenza cardiaca](#configurazione-zone-di-frequenza-cardiaca)
   - [Configurazione zone di potenza](#configurazione-zone-di-potenza)
8. [Importazione ed esportazione](#importazione-ed-esportazione)
   - [Importazione da YAML](#importazione-da-yaml)
   - [Importazione da Excel](#importazione-da-excel)
   - [Importazione da Garmin Connect](#importazione-da-garmin-connect)
   - [Esportazione in YAML](#esportazione-in-yaml)
   - [Esportazione in Excel](#esportazione-in-excel)
   - [Esportazione in Garmin Connect](#esportazione-in-garmin-connect)
9. [Pianificazione avanzata](#pianificazione-avanzata)
   - [Creazione di un piano di allenamento](#creazione-di-un-piano-di-allenamento)
   - [Configurazione dei giorni di allenamento](#configurazione-dei-giorni-di-allenamento)
   - [Modificare la data della gara](#modificare-la-data-della-gara)
10. [Esempi pratici](#esempi-pratici)
    - [Esempio 1: Creazione di un allenamento intervallato](#esempio-1-creazione-di-un-allenamento-intervallato)
    - [Esempio 2: Importazione di un piano di allenamento](#esempio-2-importazione-di-un-piano-di-allenamento)
    - [Esempio 3: Pianificazione e sincronizzazione](#esempio-3-pianificazione-e-sincronizzazione)
11. [Risoluzione dei problemi](#risoluzione-dei-problemi)
12. [FAQ](#faq)

## Introduzione

GarminPlannerGUI è un'applicazione per la gestione avanzata degli allenamenti su Garmin Connect. Permette di creare, modificare e pianificare allenamenti, gestire le zone di intensità, importare ed esportare piani di allenamento e sincronizzarli con Garmin Connect. È uno strumento pensato per atleti e allenatori che vogliono avere un controllo più dettagliato sulla creazione e pianificazione degli allenamenti rispetto a quanto offerto dall'interfaccia web di Garmin Connect.

### Caratteristiche principali:
- Creazione e modifica dettagliata di allenamenti con supporto per corsa, ciclismo e nuoto
- Gestione personalizzata delle zone di intensità (passo, frequenza cardiaca, potenza)
- Calendario integrato per la pianificazione degli allenamenti
- Importazione ed esportazione di piani di allenamento in formato YAML ed Excel
- Sincronizzazione bidirezionale con Garmin Connect

## Installazione

### Requisiti di sistema
- Windows 10/11, macOS o Linux
- Python 3.7 o superiore (se installato dalla sorgente)
- Connessione internet per sincronizzare con Garmin Connect

### Metodo 1: Installazione dell'eseguibile (Windows)
1. Scarica l'ultimo eseguibile (`GarminPlannerGUI.exe`) dalla pagina di rilascio
2. Posiziona il file in una cartella di tua scelta
3. Esegui il file facendo doppio clic su di esso

### Metodo 2: Installazione dalla sorgente (tutti i sistemi operativi)
1. Clona il repository o scarica il codice sorgente
2. Assicurati di avere Python 3.7 o superiore installato
3. Installa le dipendenze richieste:
   ```bash
   pip install -r requirements.txt
   ```
4. Esegui l'applicazione:
   ```bash
   python main.py
   ```

## Primo avvio

Al primo avvio dell'applicazione, verranno create automaticamente alcune cartelle:
- `logs`: per i file di log dell'applicazione
- `training_plans`: per i file dei piani di allenamento

Inoltre, verrà creato (se non esiste) il file `config.yaml` contenente le impostazioni predefinite dell'applicazione. Al primo avvio, l'applicazione mostrerà la schermata di login a Garmin Connect.

## Login a Garmin Connect

Per utilizzare tutte le funzionalità dell'applicazione, è necessario effettuare l'accesso al tuo account Garmin Connect.

### Procedura di login:
1. Nella scheda **Login**, inserisci l'email e la password del tuo account Garmin Connect
2. Seleziona l'opzione "Ricorda le credenziali" se desideri che l'applicazione memorizzi i tuoi dati di accesso
3. Clicca sul pulsante **Login**
4. Attendi che l'applicazione si connetta a Garmin Connect

Se l'accesso è stato effettuato con successo, vedrai il messaggio "Login effettuato con successo" nella barra di stato in basso e l'applicazione passerà automaticamente alla scheda successiva.

> **Nota**: Le credenziali vengono salvate localmente nel file `~/.garmin_planner/credentials.txt` se si seleziona l'opzione "Ricorda le credenziali". Se hai già effettuato l'accesso in precedenza, puoi utilizzare il pulsante **Riprendi sessione** per riprendere una sessione esistente senza reinserire le credenziali.

## Editor di allenamenti

L'editor di allenamenti è il cuore dell'applicazione e permette di creare e modificare allenamenti in modo dettagliato.

### Creazione di un nuovo allenamento

Per creare un nuovo allenamento:
1. Nella scheda **Editor Allenamenti**, clicca sul pulsante **Nuovo allenamento**
2. Nella finestra che appare, inserisci:
   - **Nome**: Il nome dell'allenamento (es. "W1D2 - Corsa lunga")
   - **Sport**: Seleziona il tipo di sport (running, cycling, swimming)
   - **Descrizione**: Una descrizione opzionale dell'allenamento
3. Clicca su **OK** per creare l'allenamento

> **Suggerimento per la nomenclatura**: Usa il formato "WnDm - Descrizione" dove n è il numero della settimana e m è il giorno della settimana. Ad esempio, "W1D2 - Corsa lunga" indica un allenamento nella settimana 1, giorno 2. Questo facilita la pianificazione automatica.

### Modifica di un allenamento esistente

Se hai già creato allenamenti o ne hai importati, puoi modificarli:
1. Nella lista degli allenamenti, seleziona quello che vuoi modificare
2. Le informazioni dell'allenamento verranno mostrate nei campi a destra
3. Modifica i campi desiderati (nome, sport, descrizione)
4. Gli step dell'allenamento sono visualizzati nell'area inferiore
5. Le modifiche vengono salvate automaticamente

### Aggiunta di step

Un allenamento è composto da una serie di step. Per aggiungere uno step:
1. Seleziona l'allenamento a cui vuoi aggiungere lo step
2. Clicca sul pulsante **Aggiungi step**
3. Nella finestra che appare, configura lo step:
   - **Tipo di step**: Seleziona tra riscaldamento, defaticamento, intervallo, recupero, riposo o altro
   - **Descrizione**: Inserisci una descrizione opzionale per lo step
   - **Condizione di fine**: Seleziona quando lo step termina (pulsante lap, tempo, distanza)
   - **Valore**: Inserisci il valore della condizione di fine (es. 10:00 per 10 minuti o 1000 per 1000 metri)
   - **Target**: Seleziona un target opzionale (zona di passo, frequenza cardiaca o potenza)
4. Clicca su **OK** per aggiungere lo step all'allenamento

Esempi di condizioni di fine:
- **Tempo**: Inserisci il valore nel formato `mm:ss` (es. 5:30 per 5 minuti e 30 secondi)
- **Distanza**: Inserisci il valore in metri o seguito da 'm' (es. 1000 o 1000m) o in chilometri seguito da 'km' (es. 5km)
- **Pulsante lap**: Lo step termina quando premi il pulsante lap sul dispositivo

### Creazione di ripetute

Per creare un gruppo di ripetizioni:
1. Clicca sul pulsante **Aggiungi repeat**
2. Nella finestra che appare, inserisci il numero di ripetizioni
3. Clicca su **Aggiungi step** per aggiungere gli step che saranno ripetuti
4. Ogni step aggiunto sarà parte della ripetizione
5. Puoi riordinare gli step usando i pulsanti **Sposta su** e **Sposta giù**
6. Clicca su **OK** per aggiungere il gruppo di ripetizioni all'allenamento

Esempio di repeat: un allenamento a intervalli potrebbe avere un gruppo di 5 ripetizioni contenente:
- Interval: 400m @ Z4 (un intervallo di 400 metri in Zona 4)
- Recovery: 200m @ Z1 (un recupero di 200 metri in Zona 1)

### Aggiunta di target (zone)

I target definiscono l'intensità dello step. Per aggiungere un target:
1. Nella finestra di creazione/modifica dello step, seleziona il tipo di target:
   - **Zona di passo**: Per definire un range di passo (min/km)
   - **Zona di frequenza cardiaca**: Per definire un range di frequenza cardiaca (bpm)
   - **Zona di potenza**: Per definire un range di potenza (watt) - solo per ciclismo
2. Seleziona una zona predefinita dalla lista a discesa (es. Z1, Z2, threshold)
3. I valori minimo e massimo verranno compilati automaticamente in base alla zona selezionata
4. Puoi anche inserire manualmente i valori minimo e massimo

> **Nota**: Le zone disponibili dipendono dalla configurazione nella scheda **Zone**. È consigliabile configurare le zone prima di creare allenamenti con target.

### Salvataggio degli allenamenti

Gli allenamenti vengono salvati automaticamente quando vengono modificati. Se desideri esportarli, puoi farlo dalla scheda **Importa/Esporta**.

## Calendario

La scheda **Calendario** permette di visualizzare, pianificare e sincronizzare gli allenamenti con Garmin Connect.

### Visualizzazione calendario

Il calendario mostra gli allenamenti pianificati per il mese corrente:
1. Utilizza i pulsanti **<** e **>** per navigare tra i mesi
2. Il pulsante **Oggi** riporta al mese corrente
3. Gli allenamenti sono visualizzati nelle date corrispondenti con icone che indicano il tipo di sport
4. Clicca su un giorno per vedere i dettagli degli allenamenti pianificati
5. Clicca su **Aggiorna** per sincronizzare il calendario con Garmin Connect

### Pianificazione allenamenti

Per pianificare un allenamento:
1. Seleziona un giorno nel calendario
2. Nei dettagli del giorno, clicca su **Pianifica allenamento**
3. Nella finestra che appare, seleziona l'allenamento da pianificare
4. Clicca su **Pianifica** per aggiungere l'allenamento al giorno selezionato

Puoi anche usare la funzione di pianificazione automatica dalla scheda **Editor Allenamenti**:
1. Clicca su **Pianifica allenamenti**
2. Nella finestra che appare, configura la pianificazione:
   - **Data della gara**: Inserisci la data della gara (es. una maratona)
   - **Giorni preferiti**: Seleziona i giorni in cui preferisci allenarti
3. Seleziona una settimana dal menu a discesa
4. Clicca su **Pianifica settimana** per pianificare automaticamente gli allenamenti della settimana
5. Oppure clicca su **Pianifica tutto** per pianificare tutte le settimane disponibili

### Sincronizzazione con Garmin Connect

Per sincronizzare gli allenamenti con Garmin Connect:
1. Dopo aver pianificato gli allenamenti, clicca su **Sincronizza con Garmin Connect** nella scheda **Editor Allenamenti** o usa il pulsante **Aggiorna** nella scheda **Calendario**
2. Gli allenamenti pianificati verranno sincronizzati con il tuo account Garmin Connect
3. Vedrai una barra di progresso durante la sincronizzazione
4. Al termine, un messaggio confermerà il completamento della sincronizzazione

> **Nota**: Gli allenamenti sincronizzati appariranno nel calendario di Garmin Connect e saranno disponibili sui dispositivi Garmin compatibili.

## Gestione zone

La scheda **Zone** permette di configurare le zone di intensità per i diversi sport.

### Configurazione zone di passo

Per configurare le zone di passo per la corsa o il nuoto:
1. Nella scheda **Zone**, seleziona il tipo di sport (running o swimming)
2. Seleziona il tipo di zona (pace)
3. Clicca su **Aggiungi zona** per creare una nuova zona o seleziona una zona esistente e clicca su **Modifica zona**
4. Nella finestra che appare, configura la zona:
   - **Nome**: Inserisci un nome per la zona (es. Z1, recovery, threshold)
   - **Min**: Inserisci il valore minimo nel formato mm:ss (es. 5:30 per 5:30 min/km)
   - **Max**: Inserisci il valore massimo nel formato mm:ss (es. 6:00 per 6:00 min/km)
   - **Descrizione**: Inserisci una descrizione opzionale
5. Clicca su **Salva** per salvare la zona

### Configurazione zone di frequenza cardiaca

Per configurare le zone di frequenza cardiaca:
1. Nella scheda **Zone**, seleziona qualsiasi tipo di sport
2. Seleziona il tipo di zona (heart_rate)
3. Clicca su **Aggiungi zona** o **Modifica zona**
4. Configura la zona con i valori di frequenza cardiaca in battiti al minuto (bpm)
5. Clicca su **Salva** per salvare la zona

> **Suggerimento**: Puoi definire zone basate su percentuale della frequenza cardiaca massima. Per esempio, Z1_HR potrebbe essere 60-70% della tua frequenza cardiaca massima.

### Configurazione zone di potenza

Per configurare le zone di potenza per il ciclismo:
1. Nella scheda **Zone**, seleziona il tipo di sport (cycling)
2. Seleziona il tipo di zona (power)
3. Clicca su **Aggiungi zona** o **Modifica zona**
4. Configura la zona con i valori di potenza in watt
5. Clicca su **Salva** per salvare la zona

> **Nota**: Puoi utilizzare notazioni speciali per le zone di potenza:
> - `125-175`: Un range da 125 a 175 watt
> - `<125`: Potenza inferiore a 125 watt
> - `375+`: Potenza superiore a 375 watt

## Importazione ed esportazione

La scheda **Importa/Esporta** permette di importare ed esportare allenamenti in diversi formati.

### Importazione da YAML

Per importare allenamenti da un file YAML:
1. Nella scheda **Importa/Esporta**, clicca su **Importa da YAML**
2. Seleziona il file YAML da importare
3. Gli allenamenti importati verranno aggiunti alla lista degli allenamenti disponibili

Esempio di struttura YAML:
```yaml
config:
  athlete_name: "Mario Rossi"
  name_prefix: "Maratona Milano"
  race_day: "2025-05-12"
  preferred_days: [1, 3, 5]

paces:
  Z1: "6:30-6:00"
  Z2: "6:00-5:30"
  Z3: "5:30-5:00"
  Z4: "5:00-4:30"
  Z5: "4:30-4:00"
  recovery: "7:00-6:30"
  threshold: "5:10-4:50"

heart_rates:
  max_hr: "180"
  Z1_HR: "62-76% max_hr"
  Z2_HR: "76-85% max_hr"
  Z3_HR: "85-91% max_hr"
  Z4_HR: "91-95% max_hr"
  Z5_HR: "95-100% max_hr"
  rest_hr: "60"

"W1D1 - Corsa facile":
  - sport_type: running
  - date: "2025-04-25"
  - warmup: 10min @ Z2
  - interval: 30min @ Z2
  - cooldown: 5min @ Z1

"W1D3 - Intervalli":
  - sport_type: running
  - date: "2025-04-27"
  - warmup: 10min @ Z2
  - repeat 5:
      steps:
        - interval: 400m @ Z4
        - recovery: 200m @ Z1
  - cooldown: 5min @ Z1
```

### Importazione da Excel

Per importare allenamenti da un file Excel:
1. Nella scheda **Importa/Esporta**, clicca su **Importa da Excel**
2. Seleziona il file Excel da importare
3. Gli allenamenti importati verranno aggiunti alla lista degli allenamenti disponibili

Un file Excel valido dovrebbe contenere i seguenti fogli:
- **Config**: Configurazione generale (athlete_name, race_day, ecc.)
- **Paces**: Zone di passo per i diversi sport
- **HeartRates**: Zone di frequenza cardiaca
- **Workouts**: Definizione degli allenamenti

> **Suggerimento**: Per creare un file Excel iniziale, usa la funzione **Crea Esempio Excel** che genererà un file con la struttura corretta e alcuni esempi di allenamenti.

### Importazione da Garmin Connect

Per importare allenamenti da Garmin Connect:
1. Assicurati di aver effettuato l'accesso a Garmin Connect
2. Nella scheda **Importa/Esporta**, clicca su **Importa da Garmin Connect**
3. Nella finestra di conferma, clicca su **Sì** per importare tutti gli allenamenti
4. Gli allenamenti importati verranno aggiunti alla lista degli allenamenti disponibili

### Esportazione in YAML

Per esportare allenamenti in un file YAML:
1. Nella scheda **Importa/Esporta**, seleziona gli allenamenti che vuoi esportare
2. Se non selezioni nessun allenamento, verranno esportati tutti gli allenamenti
3. Clicca su **Esporta in YAML**
4. Seleziona la posizione dove salvare il file YAML
5. Il file YAML conterrà gli allenamenti selezionati e la configurazione corrente

### Esportazione in Excel

Per esportare allenamenti in un file Excel:
1. Nella scheda **Importa/Esporta**, seleziona gli allenamenti che vuoi esportare
2. Clicca su **Esporta in Excel**
3. Seleziona la posizione dove salvare il file Excel
4. Il file Excel conterrà i fogli Config, Paces, HeartRates e Workouts

### Esportazione in Garmin Connect

Per esportare allenamenti in Garmin Connect:
1. Assicurati di aver effettuato l'accesso a Garmin Connect
2. Nella scheda **Importa/Esporta**, seleziona gli allenamenti che vuoi esportare
3. Clicca su **Esporta in Garmin Connect**
4. Nella finestra di conferma, clicca su **Sì** per esportare gli allenamenti selezionati
5. Gli allenamenti verranno aggiunti al tuo account Garmin Connect

## Pianificazione avanzata

### Creazione di un piano di allenamento

Un piano di allenamento è composto da una serie di allenamenti organizzati in settimane. Per creare un piano di allenamento completo:

1. **Definisci la struttura del piano**:
   - Determina il numero di settimane e il numero di allenamenti per settimana
   - Scegli una convenzione di denominazione (es. "W1D1 - Tipo di allenamento")

2. **Crea gli allenamenti**:
   - Per ogni settimana e giorno, crea un allenamento usando l'Editor di allenamenti
   - Usa la convenzione di denominazione scelta per facilitare la pianificazione automatica

3. **Configura le zone**:
   - Nella scheda Zone, definisci le zone di intensità per i diversi sport
   - Assicurati che le zone utilizzate negli allenamenti siano definite

4. **Pianifica gli allenamenti**:
   - Usando il dialog di pianificazione, specifica la data della gara
   - Seleziona i giorni preferiti per gli allenamenti
   - Pianifica automaticamente le settimane

5. **Sincronizza con Garmin Connect**:
   - Esporta gli allenamenti pianificati in Garmin Connect
   - Gli allenamenti saranno disponibili sul tuo dispositivo Garmin

### Configurazione dei giorni di allenamento

Per configurare i giorni preferiti per gli allenamenti:
1. Nella finestra di pianificazione, seleziona i giorni della settimana in cui preferisci allenarti
2. L'applicazione cercherà di pianificare gli allenamenti in questi giorni
3. Se un giorno preferito è già occupato, l'applicazione utilizzerà il giorno successivo disponibile

> **Suggerimento**: Se segui un piano di allenamento specifico, cerca di mantenere coerenza nei giorni di allenamento. Ad esempio, se un piano prevede gli allenamenti lunghi la domenica, seleziona sempre la domenica tra i giorni preferiti.

### Modificare la data della gara

La data della gara è il punto di riferimento per la pianificazione degli allenamenti:
1. Nella finestra di pianificazione, inserisci la data della gara nel formato GG/MM/AAAA
2. Puoi anche utilizzare il pulsante **Seleziona...** per scegliere la data da un calendario
3. La settimana 0 è quella della gara, le settimane precedenti sono numerate a ritroso

> **Nota**: Se cambi la data della gara dopo aver già pianificato degli allenamenti, dovrai ripianificarli per adattarli alla nuova data.

## Esempi pratici

### Esempio 1: Creazione di un allenamento intervallato

In questo esempio, creeremo un allenamento a intervalli per la corsa.

1. **Creazione dell'allenamento base**:
   - Vai alla scheda **Editor Allenamenti**
   - Clicca su **Nuovo allenamento**
   - Inserisci i seguenti dati:
     - Nome: "W1D3 - Intervalli 400m"
     - Sport: running
     - Descrizione: "Allenamento a intervalli di 400m"
   - Clicca su **OK**

2. **Aggiunta del riscaldamento**:
   - Clicca su **Aggiungi step**
   - Configura lo step:
     - Tipo di step: warmup
     - Descrizione: "Riscaldamento progressivo"
     - Condizione di fine: time
     - Valore: 10:00
     - Target: Zona di passo
     - Zona predefinita: Z2
   - Clicca su **OK**

3. **Creazione delle ripetizioni**:
   - Clicca su **Aggiungi repeat**
   - Inserisci 5 ripetizioni
   - Clicca su **Aggiungi step**
   - Configura lo step intervallo:
     - Tipo di step: interval
     - Descrizione: "Intervallo veloce"
     - Condizione di fine: distance
     - Valore: 400m
     - Target: Zona di passo
     - Zona predefinita: Z4
   - Clicca su **OK**
   - Clicca su **Aggiungi step**
   - Configura lo step recupero:
     - Tipo di step: recovery
     - Descrizione: "Recupero attivo"
     - Condizione di fine: distance
     - Valore: 200m
     - Target: Zona di passo
     - Zona predefinita: Z1
   - Clicca su **OK**
   - Clicca su **OK** per chiudere la finestra delle ripetizioni

4. **Aggiunta del defaticamento**:
   - Clicca su **Aggiungi step**
   - Configura lo step:
     - Tipo di step: cooldown
     - Descrizione: "Defaticamento lento"
     - Condizione di fine: time
     - Valore: 5:00
     - Target: Zona di passo
     - Zona predefinita: Z1
   - Clicca su **OK**

L'allenamento è ora completo e verrà salvato automaticamente.

### Esempio 2: Importazione di un piano di allenamento

In questo esempio, importeremo un piano di allenamento da un file Excel.

1. **Creazione del file Excel**:
   - Vai alla scheda **Importa/Esporta**
   - Clicca su **Crea Esempio Excel**
   - Salva il file nella cartella `training_plans`
   - Apri il file con Excel o un programma simile

2. **Modifica del file Excel**:
   - Nel foglio **Config**, modifica i valori per adattarli alle tue esigenze
   - Nel foglio **Paces**, modifica le zone di passo in base alle tue capacità
   - Nel foglio **HeartRates**, modifica le zone di frequenza cardiaca
   - Nel foglio **Workouts**, modifica gli allenamenti esistenti o aggiungine di nuovi

3. **Importazione del file Excel**:
   - Salva il file Excel modificato
   - Nella scheda **Importa/Esporta**, clicca su **Importa da Excel**
   - Seleziona il file Excel modificato
   - Gli allenamenti verranno importati e saranno visibili nella lista

### Esempio 3: Pianificazione e sincronizzazione

In questo esempio, pianificheremo gli allenamenti e li sincronizzeremo con Garmin Connect.

1. **Pianificazione degli allenamenti**:
   - Vai alla scheda **Editor Allenamenti**
   - Clicca su **Pianifica allenamenti**
   - Nella finestra di pianificazione:
     - Inserisci la data della gara (es. 06/06/2025)
     - Seleziona i giorni preferiti (es. Lunedì, Mercoledì, Venerdì, Domenica)
     - Seleziona la settimana da pianificare (es. Week 01)
     - Clicca su **Pianifica settimana**
   - Ripeti l'operazione per le altre settimane o usa **Pianifica tutto**

2. **Visualizzazione nel calendario**:
   - Vai alla scheda **Calendario**
   - Naviga tra i mesi per vedere gli allenamenti pianificati
   - Clicca su un giorno per vedere i dettagli degli allenamenti pianificati

3. **Sincronizzazione con Garmin Connect**:
   - Assicurati di aver effettuato l'accesso a Garmin Connect
   - Nella scheda **Editor Allenamenti**, clicca su **Sincronizza con Garmin Connect**
   - Attendi il completamento della sincronizzazione
   - Gli allenamenti pianificati saranno ora disponibili su Garmin Connect e sui tuoi dispositivi Garmin

## Risoluzione dei problemi

### Problemi di connessione a Garmin Connect

Se riscontri problemi di connessione a Garmin Connect:
1. Verifica che la tua connessione internet funzioni correttamente
2. Assicurati di aver inserito le credenziali corrette
3. Prova a cliccare su **Riprendi sessione** se avevi già effettuato l'accesso in precedenza
4. Se il problema persiste, prova a riavviare l'applicazione
5. In alcuni casi, Garmin Connect può limitare temporaneamente l'accesso API. Attendi qualche minuto e riprova

### Problemi con l'importazione/esportazione

Se riscontri problemi con l'importazione o l'esportazione di file:
1. Verifica che il file sia nel formato corretto (YAML o Excel)
2. Per i file Excel, assicurati che contenga i fogli richiesti (Config, Paces, HeartRates, Workouts)
3. Per i file YAML, verifica che la sintassi sia corretta
4. Controlla la cartella `logs` per eventuali messaggi di errore dettagliati

### L'applicazione si blocca o si chiude inaspettatamente

Se l'applicazione si blocca o si chiude inaspettatamente:
1. Controlla la cartella `logs` per eventuali messaggi di errore
2. Assicurati di avere l'ultima versione dell'applicazione
3. Verifica che il tuo sistema soddisfi i requisiti minimi
4. Prova a riavviare l'applicazione con l'opzione `--debug` per ottenere più informazioni di debug:
   ```bash
   python main.py --debug
   ```

## FAQ

### Come posso modificare le zone di passo/frequenza cardiaca/potenza?

Le zone possono essere modificate nella scheda **Zone**. Seleziona il tipo di sport e il tipo di zona, quindi usa i pulsanti **Aggiungi zona** o **Modifica zona** per configurare le zone.

### Posso importare allenamenti esistenti da Garmin Connect?

Sì, puoi importare allenamenti esistenti da Garmin Connect. Vai alla scheda **Importa/Esporta** e clicca su **Importa da Garmin Connect**. Gli allenamenti verranno importati e potrai modificarli nell'applicazione.

### Come posso pianificare gli allenamenti in base alla data della gara?

Nella finestra di pianificazione, inserisci la data della gara e seleziona i giorni preferiti per gli allenamenti. Poi usa il pulsante **Pianifica settimana** o **Pianifica tutto** per pianificare automaticamente gli allenamenti.

### Le modifiche agli allenamenti vengono salvate automaticamente?

Sì, le modifiche agli allenamenti vengono salvate automaticamente quando passi a un altro allenamento o quando chiudi l'applicazione. Se vuoi esportare gli allenamenti, puoi farlo dalla scheda **Importa/Esporta**.

### Posso utilizzare l'applicazione senza un account Garmin Connect?

Sì, puoi utilizzare l'applicazione senza un account Garmin Connect per creare e modificare allenamenti, ma non potrai sincronizzarli con i dispositivi Garmin. Puoi comunque esportare gli allenamenti in file YAML o Excel e condividerli con altri utenti.

### Come posso aggiornare l'applicazione?

Per aggiornare l'applicazione, scarica l'ultima versione dalla pagina di rilascio e sostituisci il file eseguibile. Se hai installato l'applicazione dalla sorgente, aggiorna il codice sorgente e reinstalla le dipendenze se necessario.
