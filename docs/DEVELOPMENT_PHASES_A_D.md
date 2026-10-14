# MatchMind AI — incremento verificabile A–D

Data: 14 ottobre 2026. Base verificata prima dello sviluppo e prima della pubblicazione:
`2fff9ae2cce21004eff4b1a3f1b0ce7419fbfb59` (`main`).
Branch: `fix/navigation-data-integrity`. Stack e hosting conservati.

## A — navigazione e stato dell'interfaccia

File: `frontend/src/App.jsx`, `frontend/src/test/navigation.test.jsx`,
`frontend/src/test/setup.js`, `frontend/vite.config.js`, `frontend/package.json`,
`frontend/package-lock.json`.

- Passaggio esplicito di `health` e `setPage` a PageView; titolo Impostazioni corretto.
- Caricamento distinguibile dal calendario vuoto, errori accessibili con role alert.
- Risposte obsolete ignorate; calendario precedente rimosso quando il nuovo caricamento fallisce.
- Risposte chat/analisi in ritardo non associate a una nuova selezione.
- Navigazione desktop e mobile con nomi accessibili.
- Rimossi la scorciatoia da tastiera non implementata e l'indicatore di notifiche fittizio.
- Esportazione non implementata disabilitata; notifiche indicate come non configurate.
- Intervallo iniziale coerente con il pulsante Oggi.

Operativo nei test: tutte le destinazioni del menu, Impostazioni, Diretta → Calendario,
menu mobile, schede informative del Match Center, errore e riconnessione.
Nessuna nuova credenziale richiesta. Non è una verifica visuale Safari/iPhone.

## B — controlli automatici

File: `.github/workflows/tests.yml`, test frontend e backend.

- Vitest, Testing Library e jsdom per rendering e interazioni reali nel DOM simulato.
- Pipeline frontend con Node 22, npm ci, test e build, in aggiunta ai test backend.
- API testate con TestClient e provider controllati, senza chiamare servizi a pagamento.
- 16 test frontend superati; 25 test backend superati.
- Build Vite riuscita; `git diff --check` senza errori.
- Un warning di deprecazione proviene da Starlette/AnyIO: non causa fallimenti.

Comandi riproducibili, nelle rispettive directory:

```sh
# frontend
npm ci
npm test
npm run build
# backend (ambiente virtuale isolato)
pip install -r requirements-dev.txt
python -m pytest -q
```

Il test locale backend è stato eseguito con DATABASE_URL su un database SQLite temporaneo,
non sul database di produzione. Non sono state eseguite migrazioni o cancellazioni.
Limite: nessun browser di collaudo previsto dal workflow Sites è disponibile in questo
ambiente gestito. I test DOM non attestano layout, assenza di overflow, service worker,
Safari o comportamento end-to-end sui deployment.

## C — dati, orari, provider

File: `frontend/src/dates.js`, `frontend/src/api.js`, `frontend/src/App.jsx`,
`backend/app/providers/openfootball_remote.py`, `backend/app/main.py`,
`backend/app/services/llm.py`, `frontend/src/test/dates.test.js`,
`frontend/src/test/api.test.js`, `backend/tests/test_data_integrity.py`.

- `kickoff_time_known=false` visualizza la data sorgente e “orario da confermare”.
- Gli orari confermati sono mostrati in Europe/Rome, con test ora legale/solare.
- Aggiunto `kickoff_date`; il timestamp convenzionale interno viene mantenuto per compatibilità,
  ma non è mostrato come orario ufficiale nelle viste partita.
- `retrieved_at` resta compatibile e indica la risposta API.
- `data_status.datasets[].fetched_at` indica il download, conservato durante il riuso della cache.
- `source_updated_at` resta null: non viene inventato un aggiornamento editoriale.
- Il calendario segnala copertura parziale dei dataset. COMPLETE si riferisce solo alla
  disponibilità dei file della stagione corrente, non a completezza delle statistiche o accuratezza.
- Gli errori di calendario/competizioni non espongono dettagli interni del provider.
- Timeout frontend di 30 secondi (45 per la chat), messaggi leggibili per rete, JSON e validazione.
- `ai_status` distingue configurazione, provider effettivo e stato non verificato.
  `gemini` non è supportato da questo adapter: viene esplicitamente dichiarato template.

Nessuna chiave necessaria per OpenFootball e template. Ollama o endpoint OpenAI-compatible
richiedono le variabili server già previste; configurazione non significa connessione verificata.
Non è stato collegato né testato un modello remoto. Nessun nuovo feed live o quote.

## D — contesto verificato della chat (parte descrittiva)

File: `backend/app/services/match_context.py`, `backend/app/schemas.py`,
`backend/app/main.py`, `backend/app/services/llm.py`, `backend/tests/test_verified_chat.py`,
`frontend/src/api.js`, `frontend/src/App.jsx`.

- Il frontend invia identificativo, competizione e data.
- Il backend rilegge la partita dal provider e usa una lista esplicita di campi consentiti.
- Nomi, punteggi e analisi inviati dal browser non sono considerati prove.
- Compatibilità con il vecchio payload: vengono usati soltanto i selettori.
- Partita mancante → 404; selettori insufficienti → 422; fonte non raggiungibile → 502.
- Nessuna chiamata al modello quando il contesto non viene verificato.
- Template descrittivo dei fatti disponibili, esplicitamente non generativo.
- Timeout del modello e fallback identificati; contesto serializzato come JSON.
- Test contro fatti alterati dal browser, partita inesistente e timeout del modello.

Limiti: il contesto della chat copre metadati e risultati della partita, non dati avanzati.
Un modello generativo resta soggetto a errori; il prompt non è una garanzia di accuratezza.
Questa modifica non aggiunge né ottimizza selezioni di scommesse, valore delle puntate,
mercati predittivi o raccomandazioni. Non costituisce il completamento del motore statistico.

## E–H — non completate da questo incremento

Autenticazione/sessioni/ruoli, database cloud persistente, snapshot versionati, migrazioni,
backup con restore, report persistenti, worker e notifiche restano da implementare/verificare.
Nessun modello viene dichiarato calibrato o affidabile. Nessun nuovo abbonamento o costo introdotto.
Il rifacimento visivo completo e il collaudo iPhone restano aperti.

## Deployment e rollback

La modifica è destinata a una pull request di revisione. Non viene unita automaticamente a main.
Non si dichiara riuscito alcun deployment Vercel/Render di questo incremento.
La disponibilità HTTP della versione precedente non verifica il nuovo codice.

Prima della produzione: CI verde, revisione della PR, verifica preview e configurazione
backend. Non affidare dati importanti al sistema prima di autenticazione e persistenza.
Le nuove proprietà API sono additive; la chat accetta i selettori del vecchio payload.
Nessuno schema database è stato modificato. Rollback: revert del commit della PR o ripristino
del precedente deployment; non richiede ripristini o cancellazioni del database.
