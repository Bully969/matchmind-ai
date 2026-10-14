from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from .config import settings
from .db import Base, engine, get_db
from .models import Prediction
from .schemas import AnalyzeRequest, ChatRequest
from .providers.factory import get_provider
from .services.predictor import analyse_matches, MODEL_VERSION
from .services.llm import explain

limiter=Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app=FastAPI(title=settings.app_name,version="0.1.0",description="MVP sperimentale di analisi calcistica; non è un servizio di scommesse validato.",lifespan=lifespan)
app.state.limiter=limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=False,allow_methods=["GET","POST","OPTIONS"],allow_headers=["Content-Type","Authorization"])

@app.get("/api/health")
async def health():
    try:
        active_provider = get_provider()
        data_provider = active_provider.name
        is_demo = active_provider.is_demo
        provider_error = None
    except Exception as exc:
        data_provider = "unavailable"
        is_demo = False
        provider_error = type(exc).__name__
    return {"status":"ok","app":settings.app_name,"version":"0.1.0","data_provider":data_provider,
            "configured_data_provider":settings.data_provider,"is_demo":is_demo,
            "provider_error":provider_error,"ai_provider":settings.ai_provider,"model_version":MODEL_VERSION,
            "note":"Health check confirms application response, not data freshness or predictive accuracy."}

@app.get("/api/providers")
async def providers():
    try:
        active_data_provider = get_provider().name
    except Exception:
        active_data_provider = "unavailable"
    return {"data_provider":active_data_provider,"configured_data_provider":settings.data_provider,
            "ai_provider":settings.ai_provider,"providers":[
        {"id":"openfootball_remote","label":"OpenFootball pubblico CC0","limits":"8 competizioni della stagione 2026/27; calendari e risultati pubblicati; non live; nessuna quota, xG, formazione o infortunio"},
        {"id":"openfootball","label":"OpenFootball locale","limits":"Dataset sincronizzati manualmente in backend/data; copertura dipendente dai file presenti"},
        {"id":"football_data_org","label":"Football-Data.org","limits":"Richiede API key; piano gratuito limitato a 12 competizioni e dati ritardati"},
        {"id":"api_football","label":"API-Football","limits":"Richiede API key; controllare quota e diritti di pubblicazione"},
        {"id":"demo","label":"Demo sintetica","limits":"Solo test UI, dati fittizi marcati demo"}
    ]}

@app.get("/api/competitions")
@limiter.limit("30/minute")
async def competitions(request: Request):
    try:
        provider=get_provider()
        data=await provider.competitions()
        return {"items":data,"count":len(data),"source":provider.name,"is_demo":provider.is_demo,"retrieved_at":datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=502,detail=f"Errore fonte dati: {type(exc).__name__}: {str(exc)[:300]}")

@app.get("/api/fixtures")
@limiter.limit("30/minute")
async def fixtures(request: Request, date_from: date|None=None, date_to: date|None=None, competition_id: str|None=None):
    start=date_from or date.today()
    end=date_to or (start+timedelta(days=7))
    if end < start: raise HTTPException(status_code=400,detail="date_to non può precedere date_from")
    if (end-start).days>31: raise HTTPException(status_code=400,detail="Intervallo massimo: 31 giorni per richiesta")
    try:
        provider=get_provider()
        items=await provider.fixtures(start,end,competition_id)
        return {"items":items,"count":len(items),"source":provider.name,"is_demo":provider.is_demo,"retrieved_at":datetime.now(timezone.utc).isoformat(),"date_from":start,"date_to":end}
    except Exception as exc:
        raise HTTPException(status_code=502,detail=f"Errore fonte dati: {type(exc).__name__}: {str(exc)[:300]}")

@app.post("/api/analyze")
@limiter.limit("10/minute")
async def analyze(request: Request, body: AnalyzeRequest, db: Session=Depends(get_db)):
    try:
        provider=get_provider()
        before=body.kickoff.date() if body.kickoff else None
        home_recent=await provider.recent_team_matches(body.home_team,body.home_team_id,body.competition_id,body.season,before)
        away_recent=await provider.recent_team_matches(body.away_team,body.away_team_id,body.competition_id,body.season,before)
        result=analyse_matches(body.home_team,body.away_team,home_recent,away_recent,{"home":body.odds_home,"draw":body.odds_draw,"away":body.odds_away},is_demo=provider.is_demo or body.is_demo)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502,detail=f"Analisi non disponibile: {type(exc).__name__}: {str(exc)[:300]}")
    prediction=Prediction(fixture_id=body.fixture_id,home_team=body.home_team,away_team=body.away_team,model_version=result["model_version"],source=provider.name,data_retrieved_at=datetime.now(timezone.utc),p_home=result["probabilities"]["home"],p_draw=result["probabilities"]["draw"],p_away=result["probabilities"]["away"],odds_home=body.odds_home,odds_draw=body.odds_draw,odds_away=body.odds_away)
    db.add(prediction); db.commit(); db.refresh(prediction)
    result["prediction_id"]=prediction.id
    result["source"]=provider.name
    return result

@app.post("/api/chat")
@limiter.limit("15/minute")
async def chat(request: Request, body: ChatRequest):
    result=await explain(body.message,body.fixture,body.analysis)
    return result

@app.get("/api/predictions")
@limiter.limit("30/minute")
async def predictions(request: Request, limit: int=Query(default=25,ge=1,le=100), db: Session=Depends(get_db)):
    rows=db.query(Prediction).order_by(Prediction.created_at.desc()).limit(limit).all()
    return {"items":[{"id":r.id,"fixture_id":r.fixture_id,"home_team":r.home_team,"away_team":r.away_team,"model_version":r.model_version,"source":r.source,"data_retrieved_at":r.data_retrieved_at.isoformat() if r.data_retrieved_at else None,"probabilities":{"home":r.p_home,"draw":r.p_draw,"away":r.p_away},"odds":{"home":r.odds_home,"draw":r.odds_draw,"away":r.odds_away},"created_at":r.created_at.isoformat() if r.created_at else None} for r in rows]}

@app.get("/")
async def root():
    return {"name":settings.app_name,"api_docs":"/docs","health":"/api/health"}
