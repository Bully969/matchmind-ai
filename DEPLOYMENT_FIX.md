# MatchMind AI — correzione deployment beta

Questa guida serve a collegare il frontend Vercel al backend FastAPI. Il backend presente nel repository **non viene pubblicato automaticamente solo perché il frontend è su Vercel**.

## 1. Pubblica il backend FastAPI su Render

1. Apri il dashboard Render e scegli **New → Blueprint** (oppure crea un Web Service manualmente).
2. Collega il repository `Bully969/matchmind-ai` e usa il file `render.yaml` presente nella root del repository.
3. Conferma la creazione del servizio `matchmind-ai-api`.
4. Al termine, copia l'URL HTTPS assegnato da Render. Non assumere che l'URL sia necessariamente `https://matchmind-ai-api.onrender.com`: usa quello effettivamente mostrato nel dashboard.
5. Apri `https://<URL-RENDER>/api/health`. Il risultato atteso è JSON con `"status":"ok"` e i campi `data_provider` e `ai_provider`.
6. Apri anche `https://<URL-RENDER>/api/providers` e `https://<URL-RENDER>/api/competitions`. Con la configurazione iniziale del blueprint, le partite sono **dimostrative**: servono solo a verificare la connessione.

Il blueprint usa `DATA_PROVIDER=demo` e `AI_PROVIDER=template` deliberatamente. Non crea fonti sportive reali e non abilita quote/live autentici. Il database SQLite su un servizio Render Free non è persistente: può essere perso dopo restart, sospensione o redeploy. **Non archiviarci dati importanti o previsioni di produzione.** Prima di conservare dati reali, configura `DATABASE_URL` con PostgreSQL gestito e fai una prova di backup/ripristino.

## 2. Imposta l'URL backend in Vercel

1. Apri il progetto Vercel che pubblica `matchmind-ai-beta.vercel.app`.
2. Vai a **Settings → Environment Variables**.
3. Crea o modifica la variabile:
   - **Name:** `VITE_API_URL`
   - **Value:** l'URL HTTPS di Render copiato al punto 4, senza `/api` alla fine e senza slash finale.
   - **Environment:** Production (aggiungi Preview solo se il CORS del backend autorizza anche i domini di anteprima necessari).
4. Salva e ridistribuisci il frontend. Vite incorpora le variabili `VITE_*` durante la build: salvare la variabile senza creare una nuova build non aggiorna un deployment precedente.

## 3. Verifica la connessione dal browser

Dopo che entrambi i deploy sono completati:

1. Visita `https://matchmind-ai-beta.vercel.app`.
2. In DevTools → Network verifica che le richieste di `/api/health`, `/api/competitions`, `/api/predictions` e `/api/fixtures` vadano all'URL Render, non a `localhost:8000`.
3. La richiesta API deve rispondere senza errori CORS. Il dominio Vercel di produzione è già incluso nel default CORS e nel blueprint; se usi un dominio personalizzato, aggiorna `CORS_ORIGINS` su Render con l'origine esatta e ridistribuisci il backend.
4. Con `DATA_PROVIDER=demo`, l'interfaccia deve dichiarare chiaramente la modalità demo. Non dovrebbe dichiarare quote, formazioni o statistiche reali.

## 4. Quando il backend restituisce errori

- `API non configurata`: manca `VITE_API_URL` in Vercel o il deployment non è stato ricostruito.
- `Failed to fetch` / CORS: controlla che l'API sia online, che l'URL sia HTTPS corretto e che `CORS_ORIGINS` contenga l'origine esatta del sito.
- `502` su `/api/competitions` o `/api/fixtures`: il server è raggiungibile, ma il provider selezionato ha generato un errore. Controlla Render → Logs e le variabili del provider.
- Primo caricamento lento: un web service Render Free può essere sospeso dopo un periodo di inattività e deve riavviarsi alla richiesta successiva.

## 5. Stato e limiti

Questa correzione non configura automaticamente account, login privato, push, worker pianificati, odds feed, dati live, sincronizzazione Telegram o risultati automatici. Questi elementi richiedono implementazione e, per i dati sportivi, fonti con termini d'uso adatti.

Documentazione ufficiale:
- [Variabili d'ambiente Vercel](https://vercel.com/docs/environment-variables/managing-environment-variables)
- [Vite su Vercel](https://vercel.com/docs/frameworks/frontend/vite)
- [Limiti dei servizi gratuiti Render](https://render.com/docs/free)
