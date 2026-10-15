# PR #7 — matrice prima delle correzioni

Rilevazione: 2026-10-14. Produzione Vercel verificata: `2fff9ae2cce21004eff4b1a3f1b0ce7419fbfb59`.
PR #7 aperta, non unita. Preview verificata: `78eab898420aa48472d9bf660e115931c0528c40`.
Backend: https://matchmind-ai-j87n.onrender.com, API 0.1.0. SHA non esposto dall'health check;
accesso ai deployment Render sospeso in attesa della selezione esplicita del workspace.

| Funzione | Produzione precedente | Preview PR7 | Prova / causa | Correzione minima | Verifica richiesta |
|---|---|---|---|---|---|
| Caricamento dati | Browser: 75 partite, 8 competizioni | Browser: API non collegata, calendario e archivio vuoti | OPTIONS da origine produzione 200; origine preview 400 Disallowed CORS origin. Frontend chiama Render direttamente | Rewrite API sulla stessa origine Vercel, senza allargare CORS su Render | Browser preview + richieste attraverso rewrite |
| Chat | OpenAPI distribuito richiede message e fixture | api.js invia solo identificatori nuovi | Contratto nuovo frontend / vecchio backend incompatibile | Payload compatibile con entrambi, senza modificare motore; esplicitare contesto legacy | Test contratto contro schema precedente e chiamata descrittiva |
| Intervallo iniziale | Oggi → oggi+7 | Solo oggi | App.jsx cambia useState(plusDays(7)) in todayISO | Ripristinare intervallo e indicazione visibile coerente | Test intervallo iniziale + browser |
| Aggiornamento selezione | Mantiene partita se ancora nell'elenco | setSelected(null) prima della richiesta: seleziona sempre la prima | App.jsx loadData; da riprodurre con test controllato | Preservare selezione fino al nuovo elenco; scartare solo se assente | Seleziona seconda partita, aggiorna, controlla identità |
| Impostazioni | Browser: pagina bianca, ReferenceError health is not defined | Browser: pagina renderizzata | Vecchio bug corretto nella PR7 | Mantenere fix | Browser e regressione DOM |
| Diretta → Calendario | Vecchio callback setPage mancante | Callback passato dalla PR7 | Fix precedente da preservare | Nessun rollback del fix | Navigazione browser |
| Preview protetta | Produzione accessibile | Redirect login Vercel prima di aprire app | Protezione Vercel, distinta dal guasto API | Accesso temporaneo autorizzato per collaudo, senza disabilitare protezione | Browser autorizzato |
| Risposte obsolete | Nessuna protezione | Contatore richieste presente | Protezione utile, ma reset indiscriminato del contesto | Conservare il contatore separando refresh e cambio partita | Due richieste risolte fuori ordine |
| Mobile/Safari | Non verificato in questo confronto | Non verificato in questo confronto | Il browser disponibile non espone emulazione/resize viewport | Non dichiarare verifica iPhone | Collaudo dispositivo/viewport ancora richiesto |

Questa matrice è stata scritta prima delle modifiche applicative. Nessun errore di estensioni
Chrome o login Google/Vercel è attribuito al codice MatchMind. Non sono stati modificati
produzione, database, CORS Render, autenticazione o motore statistico.
