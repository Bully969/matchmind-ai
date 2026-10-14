# MatchMind AI — prototipo Full Stack

Starter full-stack per una piattaforma di analisi calcistica, probabilità, value-bet research e chat AI. È un **MVP tecnico**, non un servizio di pronostici validato e non una garanzia di rendimento.

## Obiettivi della prima versione

- UI React/Vite e API FastAPI.
- Provider intercambiabili: OpenFootball pubblico remoto (CC0; default, senza API key), dataset OpenFootball sincronizzati localmente, demo esplicita, Football-Data.org e API-Football.
- Baseline probabilistica Poisson basata sulle ultime partite disponibili, con segnali di qualità e avvisi per dati insufficienti.
- Valore atteso calcolato solo quando l'utente inserisce quote.
- AI con provider configurabile: template deterministico, Ollama in locale o endpoint compatibile OpenAI.
- Cronologia minima delle analisi su SQLite; PostgreSQL configurabile per hosting.
- Nessuna chiave API nel frontend.

## Importante: “tutti i campionati” e budget zero

L'app supporta un catalogo dinamico, ma nessuna fonte gratuita garantisce in modo affidabile tutti i campionati, le quote, gli xG, le formazioni e gli infortuni in tempo reale.

- **OpenFootball remoto (default)**: usa i dataset JSON pubblici CC0 su GitHub. Nella stagione corrente sono predisposte 8 competizioni: Serie A, Premier League, Championship, Bundesliga, La Liga, Ligue 1, Eredivisie e Primeira Liga. I risultati vengono pubblicati dai manutentori, non sono live; non include quote, eventi minuto per minuto, xG, formazioni o infortuni. Se il repository upstream non ha ancora pubblicato un aggiornamento, MatchMind non può inventarlo. Fonte: https://github.com/openfootball/football.json.
- **Football-Data.org**: piano gratuito limitato a 12 competizioni, risultati/calendari ritardati e 10 richieste/minuto; include obbligo di attribuzione in-app. Non è “tutto il calcio”.
- **API-Football**: il piano gratuito indica 100 richieste al giorno e accesso agli endpoint delle competizioni con limitazioni stagionali. L’adapter qui incluso carica solo le prime 3 pagine per risparmiare quota; aumentare il limite richiede più richieste e può consumare rapidamente il piano gratuito. Le condizioni avvertono inoltre che la pubblicazione dei dati e l'uso commerciale possono dipendere dai diritti di terze parti. Prima di esporre dati tramite un sito pubblico, verifica le autorizzazioni necessarie.
- **football-data.co.uk** non viene usato nel progetto: il sito dichiara che i dati sono per individui privati e non per prodotti commerciali o addestramento AI.

Non fare scraping aggressivo e non aggirare limiti o paywall. Conserva sempre fonte e timestamp dei dati. Nel sito pubblico non presentare come “live” dati ritardati.

## Architettura consigliata

```text
Browser (React/Vite; Cloudflare Pages per static hosting)
                |
                v
       FastAPI (Render per prototipo; oppure VPS/PC personale)
         |            |              |
         v            v              v
  Data providers   Predictor      AI adapter
  OpenFootball     Poisson        Ollama locale
  Football-Data    Value/EV       OpenAI-compatible remoto
  API-Football     History        Template fallback
         |
         v
 SQLite in locale / PostgreSQL gestito in hosting
```

### Il limite fondamentale del “hybrid AI”

Ollama installato sul tuo PC non è automaticamente raggiungibile da un backend ospitato su Render. In locale, scegli `AI_PROVIDER=ollama`. Sul sito pubblico, usa `template` come fallback oppure configura un endpoint AI remoto compatibile con OpenAI. Un endpoint remoto gratuito può avere quote/condizioni variabili e non è garantito per sempre. Non esporre direttamente la porta 11434 di Ollama a Internet.

## Requisiti Windows

- Windows 10 22H2 o Windows 11.
- Python 3.12 (64-bit), Node.js 22 LTS, Git.
- Ollama per Windows (già installato secondo la configurazione dell'utente); driver NVIDIA aggiornati.
- 16 GB RAM: comincia con un modello Ollama piccolo/quantizzato, ad es. `qwen3:4b`, se la GPU/VRAM lo consente. Se va lento, usa `AI_PROVIDER=template` durante sviluppo o prova un modello più piccolo. La RAM da sola non indica quanta parte del modello andrà in VRAM: conta la GPU esatta.

## Avvio locale passo per passo (PowerShell)

1. Estrai il progetto in una cartella semplice, ad esempio `C:\Projects\tipster-ai-starter`.
2. Copia `.env.example` in `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Crea ambiente Python e installa backend:
   ```powershell
   cd backend
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   New-Item -ItemType Directory -Force data | Out-Null
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Apri `http://127.0.0.1:8000/docs`; la modalità demo deve restituire dati marcati `is_demo=true`.
4. Apri un secondo PowerShell e avvia il frontend:
   ```powershell
   cd C:\Projects\tipster-ai-starter\frontend
   npm install
   npm run dev
   ```
   Apri `http://localhost:5173`.
5. Per AI locale, verifica Ollama e scarica il modello:
   ```powershell
   ollama --version
   ollama pull qwen3:4b
   ```
   Modifica `.env` in `AI_PROVIDER=ollama` e `OLLAMA_BASE_URL=http://127.0.0.1:11434`, poi riavvia il backend. In caso di `model not found`, verifica con `ollama list`.
6. Per arrestare i processi, usa `Ctrl+C` nelle due finestre.
7. Test del modello: in `backend`, esegui `pip install -r requirements-dev.txt` e poi `pytest -q`.

## Dati pubblici CC0 con OpenFootball

Il provider locale può leggere JSON dal progetto `openfootball/football.json`; raggruppa gli ID per campionato e può combinare i risultati di stagioni diverse dello stesso file/campionato quando i nomi squadra coincidono esattamente.

1. Dalla cartella principale esegui:
   ```powershell
   git clone --depth 1 https://github.com/openfootball/football.json.git data/openfootball
   ```
2. Nel `.env` imposta `DATA_PROVIDER=openfootball` e `OPENFOOTBALL_DATA_DIR=./data/openfootball`.
3. Riavvia il backend e controlla `/api/competitions`.
4. Per una build web con Render che usa `backend` come Root Directory, copia una selezione di JSON pertinenti in `backend/data/openfootball/` e includili intenzionalmente nel repository (la cartella dati è esclusa dal `.gitignore`; se necessario usa `git add -f` solo sui file scelti). Imposta `OPENFOOTBALL_DATA_DIR=./data/openfootball`. I file possono essere datati o incompleti; l'interfaccia mostrerà la fonte OpenFootball e non inventerà quote, infortuni o xG.

I dati OpenFootball sono CC0 secondo il repository; controlla comunque la licenza dell'eventuale dato esterno aggiunto in futuro.

## Provider ufficiali opzionali

### Football-Data.org
1. Crea una chiave personale sul sito ufficiale.
2. In `.env`: `DATA_PROVIDER=football_data_org`, `FOOTBALL_DATA_API_KEY=...`.
3. La chiave resta solo nel backend. Mostra in modo visibile l'attribuzione richiesta: `Football data provided by the Football-Data.org API`.
4. Il piano gratuito copre 12 competizioni; il motore deve rispettare rate limit e dati ritardati.

### API-Football
1. Registra una chiave personale e leggi pricing e termini aggiornati.
2. In `.env`: `DATA_PROVIDER=api_football`, `API_FOOTBALL_KEY=...`.
3. Il piano gratuito pubblicizzato è di 100 richieste/giorno; la cache riduce le chiamate, ma non rende la quota illimitata.
4. Prima di mostrarne i dati a terzi o monetizzare, verifica i diritti di visualizzazione/uso per le competizioni interessate. Non usare più account per aggirare il limite.

## Deploy web a costo zero per prototipo

> I livelli gratuiti cambiano spesso e non equivalgono a un servizio di produzione sempre disponibile. Verifica limiti e condizioni durante la registrazione. Questa procedura è per una demo/beta privata, non per un servizio di scommesse con affidabilità garantita.

### 1. Repository
- Crea un repository GitHub privato inizialmente.
- Non aggiungere `.env`, chiavi API, database o dati per i quali non possiedi diritti.
- Carica codice e una piccola selezione di dati CC0 se serve alla demo.

### 2. Database
- Crea un progetto PostgreSQL sul piano gratuito di un provider come Supabase.
- Copia la connection string PostgreSQL nel secret `DATABASE_URL` del backend. Se il provider offre un pooler, scegli la connessione raccomandata per il runtime cloud.
- Supabase Free può mettere in pausa progetti poco attivi e ha limiti di storage: esporta/backup regolari e non usarlo come unica copia dello storico.

### 3. Backend FastAPI su Render
- Crea un Web Service collegato al repository.
- Root Directory: `backend`.
- Build Command: `pip install -r requirements.txt`.
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Imposta le variabili d'ambiente dal dashboard: `DATABASE_URL`, `DATA_PROVIDER`, `AI_PROVIDER`, chiavi API se autorizzate, `CORS_ORIGINS` con l'URL esatto del frontend.
- Il servizio gratuito Render si sospende dopo 15 minuti senza traffico e non mantiene i file locali. Per questo usa PostgreSQL, non SQLite, per i dati persistenti in hosting; la prima richiesta dopo inattività può essere lenta.
- Per iniziare, usa `AI_PROVIDER=template`. Non impostare `OLLAMA_BASE_URL=localhost` sul cloud aspettandoti di raggiungere il PC di casa.

### 4. Frontend React su Cloudflare Pages
- Crea un progetto Pages collegato allo stesso repository.
- Root directory: `frontend`.
- Build command: `npm run build`.
- Build output directory: `dist`.
- Environment variable: `VITE_API_URL=https://<tuo-backend-render>.onrender.com`.
- In `CORS_ORIGINS` sul backend aggiungi l'origine Pages esatta, ad esempio `https://nome-progetto.pages.dev`.
- Ridistribuisci dopo aver cambiato variabili build-time. Il valore `VITE_API_URL` non è segreto.

### 5. Prima di renderlo accessibile al pubblico
- Aggiungi login/autenticazione, protezione degli endpoint, rate limiting persistente e limiti per utente; il rate limiting in memoria non è una protezione sufficiente contro abusi coordinati.
- Applica protezione d'accesso (ad es. Cloudflare Access per una beta privata) sia al sito sia alle API, oppure implementa un sistema di account.
- Non distribuire chiavi dati ai browser. Non pubblicare automaticamente selezioni di scommesse prima di verificare i diritti sui dati.
- Aggiungi monitoraggio di quota provider e costi (anche quando il costo previsto è zero).
- Fornisci termini d'uso, informativa privacy GDPR e una policy sull'uso responsabile. Nessuna promozione a minorenni o garanzie di vincita.

## Calcolo e limiti del modello iniziale

Il modello usa una media pesata dei gol fatti e subiti nelle ultime 10 partite disponibili e una distribuzione di Poisson per produrre 1/X/2, Over 2.5 e Goal/No Goal. È un baseline per test tecnici, non un modello avanzato calibrato. Non usa ancora xG, Elo, formazioni confermate, meteo o quote di mercato automaticamente.

Il valore atteso è calcolato come `EV = probabilità × quota - 1`, quando inserisci manualmente la quota decimale. Un EV positivo non prova l'esistenza di un vantaggio vero: servono calibrazione, backtest out-of-sample, quote timestamped e misure di incertezza.

## Roadmap raccomandata

1. Verificare fonti e permessi, importare dati storici CC0 e scrivere test.
2. Backtest cronologico senza leakage; misurare Brier score, log loss e calibrazione.
3. Persistenza quote/decisioni con timestamp e storico immutabile.
4. Addestrare e confrontare Elo, Poisson/Dixon–Coles e gradient boosting.
5. Solo in seguito aggiungere line-up/infortuni da fonti con autorizzazioni, odds snapshots e aggiornamenti controllati.
6. Prima di una monetizzazione, ottenere i diritti necessari per dati, loghi, marchi e competizioni; verificare anche i termini dei provider AI e hosting.

## Fonti da verificare prima di ogni deploy

- OpenFootball / football.json: https://github.com/openfootball/football.json (repository indica CC0).
- Football-Data.org pricing: https://www.football-data.org/pricing
- Football-Data.org terms/attribution: https://www.football-data.org/about
- API-Football pricing: https://www.api-football.com/pricing/
- API-Football terms: https://www.api-football.com/terms
- Render free limits: https://render.com/docs/free
- Cloudflare Pages limits: https://developers.cloudflare.com/pages/platform/limits/
- Supabase free-project pausing: https://supabase.com/docs/guides/platform/free-project-pausing
- Ollama Windows/NVIDIA: https://github.com/ollama/ollama/blob/main/docs/windows.mdx

## Disclaimer

Solo a scopo informativo e di ricerca. Le previsioni possono essere errate. Non promette vincite né costituisce consulenza finanziaria. Non effettuare scommesse con denaro che non puoi permetterti di perdere; rispetta le leggi locali e i requisiti di età.


## Stato della build visiva (14 ottobre 2026)

È stata realizzata una UI responsive in stile **Premium Dark + Live Center + Odds Intelligence**, con layout desktop a tre colonne e navigazione mobile dedicata. Le schermate disponibili sono:

- Home con partite, indicatori, Match Center e selezioni.
- Pronostici AI e avvio dell'analisi statistica.
- Calendario filtrabile per intervallo e competizione.
- Diretta con timeline e statistiche di esempio.
- Quote & Mercati, selettori 1X2 / Over-Under / Gol-No Gol / Doppia Chance.
- Report giornalieri, Archivio pronostici, Performance Lab e Simulatore.
- Impostazioni, stato connessione e preferenze di notifica.

**Importante:** il layout contiene esempi visivi per rendere progettazione e navigazione valutabili subito. Quote bookmaker, frecce di trend, formazioni, rating giocatori, eventi live, xG, articoli, report e alcuni indicatori sono marcati come dimostrativi e non provengono da provider reali. La build non è ancora una piattaforma di produzione: non ha autenticazione/inviti, push web effettive, scheduler cloud, settlement automatico, storico append-only garantito o feed quote/live autorizzati. Le pagine mostrano questi limiti invece di inventare dati verificati.

## UX iPhone / iOS

La UI usa layout mobile-first/responsive, viewport con `viewport-fit=cover`, area sicura inferiore, navigazione inferiore a cinque voci, tabelle quote scorrevoli, campi adatti al tocco e layout specifici per schermi stretti. La configurazione PWA include manifest, icone e service worker per la shell statica. Questo non equivale a un'app nativa né garantisce che ogni funzione iOS sia disponibile; per le notifiche push web su iPhone serve in genere una web app aggiunta alla schermata Home, consenso dell'utente e un backend push reale.

Per installarla su iPhone, prima pubblica la web app su un origin **HTTPS** accessibile dal telefono; apri l'URL in Safari, tocca **Condividi → Aggiungi alla schermata Home**. Il server Vite su `localhost` del PC non è automaticamente raggiungibile dall'iPhone. Per un test sulla stessa Wi-Fi si può usare l'IP LAN del PC, ma occorre configurare correttamente `VITE_API_URL`, CORS e rete locale; la modalità PWA/Service Worker di produzione va provata su HTTPS.

## Avvio locale Windows

Dalla cartella del progetto, apri due terminali PowerShell.

**Terminale A — API**

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
New-Item -ItemType Directory -Force data | Out-Null
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminale B — frontend**

```powershell
cd frontend
npm install
npm run dev
```

Apri `http://localhost:5173`. Per la documentazione API: `http://localhost:8000/docs`. Senza backend disponibile, l'interfaccia resta esplorabile in modalità demo locale.

### Verifiche eseguite in questa build

- Test Python backend: **2 passed**.
- Controllo sintattico JSX/React: **superato**.
- La build Vite di produzione non è stata verificata in questo ambiente perché l'installazione dei pacchetti npm non è riuscita entro il tempo disponibile/rete; esegui `npm install` e `npm run build` sul PC con accesso al registry npm.

Prima di distribuire la beta, completare auth/inviti, quote e feed autorizzati, persistenza cloud, worker/scheduler, gestione consensi, push web, monitoraggio/backup, test e privacy/GDPR.
