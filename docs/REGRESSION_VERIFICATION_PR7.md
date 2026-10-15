# Correzione incrementale PR #7 — verifica del 15 ottobre 2026

## Identità delle versioni

- Produzione Vercel ricontrollata: `2fff9ae2cce21004eff4b1a3f1b0ce7419fbfb59`, deployment `dpl_6quSnzRX24gGV5VrjUTd5BptuE2K`.
- PR #7: `78eab898420aa48472d9bf660e115931c0528c40`. Non unita.
- Correzione applicativa: `60f3431d62793d526eca78280ab771deef8c0319`, branch `fix/pr7-regressions`.
- Preview effettivamente collaudata: https://matchmind-394ectspr-bully3.vercel.app/ — deployment `dpl_DxCCzyLwDgRagBngB8sD6UvibBCv`. Vercel conferma lo SHA sopra. Accesso con protezione Vercel mantenuta.
- Backend usato dalla preview: https://matchmind-ai-j87n.onrender.com, API `0.1.0`, modello dichiarato `poisson-baseline-v1`, fonte `openfootball_remote`. Il commit backend **non è verificato**: health non lo espone e il connettore Render richiede selezione esplicita del workspace da parte dell'utente.

## Cause e modifiche

La matrice precedente alle modifiche è in `REGRESSION_MATRIX_PR7.md`.

1. Il frontend della preview chiamava direttamente Render, che rifiutava la sua origine CORS (OPTIONS 400); la produzione era autorizzata (200). `frontend/vercel.json` inoltra ora `/api/*` a Render sulla stessa origine e imposta `Cache-Control: no-store`. `frontend/src/api.js` usa percorsi relativi nelle build distribuite. Non sono stati ampliati i permessi CORS del backend.
2. Il payload chat della PR non rispettava lo schema ancora distribuito, che richiede `fixture`. `frontend/src/api.js` include il campo legacy e gli identificatori nuovi. Ripristina la compatibilità HTTP, **non** la ricostruzione verificata server-side sul backend vecchio. Nessuna probabilità del browser viene inviata alla chat.
3. `frontend/src/App.jsx` aveva ridotto la finestra iniziale da sette giorni al solo giorno corrente. Ripristinata e indicata esplicitamente nell'intestazione dell'elenco.
4. Lo stesso file azzerava selezione e contesto prima di ogni refresh. Ora mantiene la partita se presente nei nuovi risultati e invalida il contesto solo se cambia l'identità; i contatori contro risposte obsolete restano attivi.
5. Conservate le correzioni di PR7 per `health` e `setPage`; nessun rollback indiscriminato. Nessuna modifica al motore statistico o al database.

File applicativi/test modificati: `frontend/src/App.jsx`, `frontend/src/api.js`, `frontend/vercel.json`, `frontend/src/test/api.test.js`, `frontend/src/test/navigation.test.jsx`. Aggiunta questa documentazione e la matrice.

## Test automatici eseguiti

- Due nuovi test prima della correzione: **falliti**, rispettivamente intervallo iniziale di zero invece di sette giorni e perdita della seconda partita al refresh. Dopo la correzione: passati.
- `cd frontend && npm test`: **19/19**, tre file. Comprendono navigazione, Impostazioni, Diretta, menu mobile DOM, schede, risposta obsoleta, errore calendario/riprova, timeout, contratto chat e URL same-origin.
- `cd frontend && npm run build`: **passata**. Bundle `index-BV-_lAJC.js`, CSS `index-CyWNfccG.css`.
- `cd backend && DATABASE_URL=sqlite:////tmp/matchmind-regression-tests.db python -m pytest -q`: **25/25** (eseguito con database locale isolato equivalente e venv Python 3.12). Una deprecazione Starlette/AnyIO, nessun errore.
- GitHub Actions sul commit applicativo: run `38664703561`, conclusione **success**.
- `git diff --check`: passato.

## Verifiche reali browser Chrome sulla nuova preview

Questi controlli sono stati eseguiti con browser remoto reale, non con jsdom. I fixture e i conteggi sono osservazioni della fonte al momento del controllo, non fixture di test inventati.

| Passi riproducibili | Esito osservato |
|---|---|
| Apri preview; se il backend non risponde usa Aggiorna connessione | Primo caricamento terminato con errore gestito; riprova riuscita: API connessa, 71 partite, 8 competizioni. Causa del ritardo iniziale non attestata dai log Render. |
| Seleziona Eintracht Frankfurt–1. FC Köln (seconda partita), Aggiorna dati | Match Center mantiene la stessa partita durante e dopo il refresh. |
| Apri Impostazioni | Nessuna pagina bianca; stato fonte e modello visibili. |
| Diretta → Vai al calendario → Diretta | Navigazione riuscita; disclaimer assenza feed live presente. |
| Calendario → Campionato Serie A → Applica filtri | 10 partite Serie A visualizzate. |
| Home → Oggi (15 ottobre) | Zero partite, stato vuoto, nessuna partita selezionata, chat disabilitata. |
| Apri tutte le destinazioni della barra laterale | Home, Pronostici, Calendario, Diretta, Quote, Report, Archivio, Performance, Simulatore, Impostazioni renderizzati. Verifica di navigazione, non certificazione delle funzionalità avanzate. |
| Match Center: Sintesi, Statistiche, Formazioni, Stats giocatore, Quote, ritorno Home/Riassunto | Stati disponibili/non disponibili renderizzati. Quote naviga alla pagina Quote & Mercati, comportamento esistente. |
| Ricarica pagina | Nuovo caricamento riuscito, 71 partite e 8 competizioni. |
| Chat: domanda descrittiva su squadre e fonte, senza pronostici | Risposta ricevuta per SC Heerenveen–SBV Excelsior, etichetta `template · risposta di riserva`; nessun errore schema 422. La risposta legacy invita ad avviare l'analisi e non fornisce la spiegazione completa richiesta. |
| Esamina console dopo navigazione e reload | Nessun errore applicativo nei log raccolti; presenti errori dell'estensione Chrome, esclusi esplicitamente. |
| Ispezione screenshot desktop | Layout Dark renderizzato; non equivalente a verifica mobile. |

Verifica HTTP indipendente: GET della preview `/api/health` tramite accesso Vercel autorizzato restituisce **200**, JSON backend, `Cache-Control: no-store`, `x-render-origin-server: uvicorn`. Il proxy è stato verificato in funzione, non dedotto dalla sola build READY.

## Gate ancora aperti: NON pronto per produzione

- Nessun collaudo iPhone, Safari, viewport mobile o rete offline forzata: il browser disponibile non espone emulazione/resize/offline. Il test menu mobile è DOM e non lo sostituisce.
- Nessuna suite browser E2E autonoma in CI: sono presenti regressioni automatiche DOM/API e i flussi browser sopra, da non confondere tra loro.
- Identificazione SHA Render e diagnosi del ritardo iniziale ancora da completare.
- Il backend distribuito restituisce `ai_provider: gemini` senza stato verificato; la chat usa effettivamente il template. La nuova implementazione server della PR7 non è distribuita. Impostazioni mostra anche `Stato modello: Non verificato`, ma il campo provider legacy rimane ambiguo.
- La compatibilità chat non risolve il limite di fiducia del vecchio server verso il payload browser. Non dichiarare la chat verificata server-side in produzione.
- Non eseguite nuove analisi persistenti o calcoli di mercato sulla produzione durante questo collaudo; nessun risultato predittivo o archivio è stato alterato.
- Autenticazione privata, persistenza e backup non sono stati certificati da questo intervento.
- Nessun redesign: intenzionalmente rinviato fino alla chiusura delle regressioni e dei gate di rilascio.

## Rollback verificabile e rilascio

Non effettuati merge, promozioni Vercel, deploy Render o migrazioni. La produzione rimane al deployment/SHA riportato sopra.

La correzione è isolata in un commit applicativo con padre `78eab898420aa48472d9bf660e115931c0528c40`. Un revert del commit `60f3431d62793d526eca78280ab771deef8c0319` su un branch di prova ripristina esattamente l'albero della PR7 (salvo documentazione successiva). È un percorso di rollback del codice, non un ripristino operativo che consigliamo: la preview PR7 ha i guasti descritti.

Per un eventuale rilascio futuro conservare come rollback di produzione il deployment `dpl_6quSnzRX24gGV5VrjUTd5BptuE2K`, senza ricostruire dipendenze. Verificare prima la possibilità di ripromuoverlo nel progetto Vercel. **Nessuna promozione/rollback reale è stata eseguita o certificata**. Prima del merge chiudere i gate sopra, collaudare la coppia frontend/backend destinata alla produzione e registrare entrambi gli SHA.
