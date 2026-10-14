import httpx
from ..config import settings

SYSTEM_PROMPT = """Sei un analista calcistico prudente. Spiega sinteticamente SOLO i dati e i calcoli presenti nel contesto JSON. Non inventare assenze, formazioni, motivazioni psicologiche, statistiche, quote o notizie. Non mostrare ragionamenti interni privati: fornisci una spiegazione verificabile con fattori favorevoli, limiti e incertezze. Non promettere vincite e non dare istruzioni per recuperare perdite. Rispondi in italiano."""

def template_explanation(message: str, fixture: dict, analysis: dict | None) -> str:
    if not analysis:
        return (f"Per {fixture.get('home_team','la squadra di casa')}–{fixture.get('away_team','la squadra ospite')} posso aiutarti a verificare i dati, ma questa richiesta non contiene un'analisi statistica calcolata. "
                "Seleziona una partita e avvia prima l'analisi. Non invento assenze, quote o notizie mancanti.")
    probs=analysis.get("probabilities",{})
    markets=analysis.get("markets",{})
    quality=analysis.get("data_quality",{})
    top=max(probs,key=probs.get) if probs else "n/d"
    pct=lambda x:f"{100*x:.1f}%" if isinstance(x,(int,float)) else "n/d"
    return (f"Analisi di {fixture.get('home_team')}–{fixture.get('away_team')} basata sul modello {analysis.get('model_version','baseline')}. "
            f"La probabilità 1X2 più alta è '{top}' ({pct(probs.get(top))}); non significa che l'esito sia certo. "
            f"Over 2.5: {pct(markets.get('over_2_5'))}; Goal/BTTS: {pct(markets.get('btts_yes'))}. "
            f"Qualità dati: {quality.get('level','n/d')} con {quality.get('home_matches',0)} risultati recenti della squadra di casa e {quality.get('away_matches',0)} della squadra ospite. "
            "Il modello attuale usa gol recenti e distribuzione di Poisson; non integra ancora xG, formazioni, assenze o informazioni psicologiche verificate. "
            "Per valutare una quota serve inserirla e confrontarla con la probabilità stimata; il valore atteso è incerto e va validato con backtest.")

async def explain(message: str, fixture: dict, analysis: dict | None) -> dict:
    context={"fixture":fixture,"analysis":analysis,"user_question":message}
    provider=settings.ai_provider.lower()
    if provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp=await client.post(settings.ollama_base_url.rstrip("/")+"/api/chat",json={
                    "model":settings.ollama_model,"stream":False,
                    "messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":str(context)}]
                })
                resp.raise_for_status()
                data=resp.json()
            answer=((data.get("message") or {}).get("content") or "").strip()
            if answer:
                return {"answer":answer,"provider":"ollama","fallback":False}
        except Exception:
            pass
    elif provider == "openai_compatible" and settings.openai_compatible_base_url and settings.openai_compatible_model:
        try:
            headers={"Content-Type":"application/json"}
            if settings.openai_compatible_api_key:
                headers["Authorization"]="Bearer "+settings.openai_compatible_api_key
            async with httpx.AsyncClient(timeout=60) as client:
                resp=await client.post(settings.openai_compatible_base_url.rstrip("/")+"/chat/completions",headers=headers,json={
                    "model":settings.openai_compatible_model,
                    "messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":str(context)}],"temperature":0.2
                })
                resp.raise_for_status(); data=resp.json()
            answer=data.get("choices",[{}])[0].get("message",{}).get("content","").strip()
            if answer:
                return {"answer":answer,"provider":"openai_compatible","fallback":False}
        except Exception:
            pass
    return {"answer":template_explanation(message,fixture,analysis),"provider":"template","fallback":provider!="template"}
