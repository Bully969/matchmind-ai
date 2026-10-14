# MatchMind AI — stato delle funzionalità

Aggiornato: 14 ottobre 2026.

## Presente nel progetto

- Dashboard React responsive con stile Premium Dark, desktop a colonne e menu mobile dedicato.
- Sezioni navigate: Home, Pronostici AI, Calendario, Diretta, Quote & Mercati, Report, Archivio, Performance, Simulatore e Impostazioni.
- Schede partita, filtri data/competizione, barra di ricerca, mercato selezionabile, inserimento quote manuali e navigazione Match Center.
- Componenti UI per timeline, statistiche a barre, pitch tattico, rating giocatori, sintesi editoriale, trend quote e archivio. I valori statici sono demo visive e vengono etichettati.
- PWA: manifest, icone, meta tag iOS, service worker di shell e responsive styling.
- API FastAPI con health check, elenco competizioni/partite, analisi statistica Poisson baseline, chat spiegativa configurabile e salvataggio storico minimo su database.
- Provider remoto OpenFootball CC0 per calendario, risultati pubblicati e forma recente in 8 competizioni della stagione 2026/27; non è un feed live e non fornisce quote o statistiche avanzate.
- Adapters dati per demo, OpenFootball, Football-Data.org e API-Football inclusi nello starter kit. L'uso reale dipende da configurazione, limiti e permessi del provider.

## Ancora da implementare o collegare prima di una beta reale

- Quote bookmaker in tempo reale, snapshot storici delle quote e trend: serve un provider con diritti adeguati. La tabella attuale è illustrativa.
- Feed live per eventi, statistiche, xG, formazioni, rating, immagini e notizie: non forniti dal provider OpenFootball. La UI non deve presentarli come dati verificati.
- Account privati su invito, ruoli, gestione sessioni, audit di sicurezza e isolazione utenti.
- Registro append-only con versioning completo, settlement/risultati automatici e validazione degli esiti per mercato. L'archivio corrente è minimo.
- Report schedulati con worker persistente cloud, task di refresh, retry/backoff e notifiche in-app effettive.
- Web push reale con backend di sottoscrizione e chiavi VAPID; il toggle UI è solo preferenza dimostrativa.
- Database cloud, backup giornaliero con test di restore, metriche di affidabilità e deployment protetto.
- Brier score, log loss, calibrazione, backtesting cronologico e performance finanziaria basata su storico out-of-sample; non vengono mostrati risultati inventati.
- Revisione privacy/GDPR, termini d'uso, diritti per brand/loghi e autorizzazioni di visualizzazione dei dati.

## Nota sul perimetro

Questa è una base progettuale eseguibile e un prototipo UI, non il rilascio di un servizio completo, autenticato o capace di fornire dati live senza configurazione. Non esistono credenziali/provider attivati nel progetto consegnato.
