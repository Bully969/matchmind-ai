from contextlib import asynccontextmanager
import asyncio
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
from .services.llm import explain, provider_status
from .services.match_context import verified_match_context
from .services.recommendations import rank_market_candidates

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
            "provider_error":provider_error,"ai_provider":provider_status()["effective"],
            "ai_status":provider_status(),"model_version":MODEL_VERSION,
            "note":"Health check confirms application response, not data freshness or predictive accuracy."}

@app.get("/api/providers")
async def providers():
    try:
        active_data_provider = get_provider().name
    except Exception:
        active_data_provider = "unavailable"
    return {"data_provider":active_data_provider,"configured_data_provider":settings.data_provider,
            "ai_provider":provider_status()["effective"],"ai_status":provider_status(),"providers":[
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
        return {"items":data,"count":len(data),"source":provider.name,"is_demo":provider.is_demo,"retrieved_at":datetime.now(timezone.utc).isoformat(),
                "data_status":provider.data_status() if hasattr(provider, "data_status") else {"source_updated_at":None,"coverage":"UNVERIFIED"}}
    except Exception as exc:
        raise HTTPException(status_code=502,detail="Fonte dati temporaneamente non disponibile. Riprova tra poco.")

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
        return {"items":items,"count":len(items),"source":provider.name,"is_demo":provider.is_demo,"retrieved_at":datetime.now(timezone.utc).isoformat(),"date_from":start,"date_to":end,
                "data_status":provider.data_status(competition_id) if hasattr(provider, "data_status") else {"source_updated_at":None,"coverage":"UNVERIFIED"}}
    except Exception as exc:
        raise HTTPException(status_code=502,detail="Fonte dati temporaneamente non disponibile. Riprova tra poco.")

@app.get("/api/recommendations")
@limiter.limit("8/minute")
async def recommendations(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    competition_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=40),
):
    """Return statistically ranked watchlist candidates, never 'safe bets'.

    This endpoint deliberately does not persist predictions: it is a transient
    scan. The existing /api/analyze route persists only user-requested analyses.
    """
    start = date_from or date.today()
    end = date_to or (start + timedelta(days=7))
    if end < start:
        raise HTTPException(status_code=400, detail="date_to non può precedere date_from")
    if (end - start).days > 14:
        raise HTTPException(status_code=400, detail="Per il ranking usa un intervallo massimo di 14 giorni")

    try:
        provider = get_provider()
        fixtures = await provider.fixtures(start, end, competition_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Impossibile caricare le partite: {type(exc).__name__}: {str(exc)[:200]}")

    # Only include confirmed pre-match fixtures. For matches today, kickoff must be known and in the future.
    def is_upcoming(fixture: dict[str, Any]) -> bool:
        kickoff = fixture.get("kickoff")
        if fixture.get("status") != "SCHEDULED" or kickoff is None or fixture.get("is_demo", False):
            return False
        now = datetime.now(kickoff.tzinfo) if kickoff.tzinfo else datetime.now()
        if kickoff.date() > now.date():
            return True
        if kickoff.date() < now.date():
            return False
        return bool(fixture.get("kickoff_time_known", False)) and kickoff > now

    upcoming = [fixture for fixture in fixtures if is_upcoming(fixture)]
    upcoming = sorted(upcoming, key=lambda f: f["kickoff"])[:limit]
    semaphore = asyncio.Semaphore(5)

    async def inspect_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            try:
                before = fixture["kickoff"].date()
                home_recent, away_recent = await asyncio.gather(
                    provider.recent_team_matches(
                        fixture["home_team"], fixture.get("home_team_id"),
                        fixture["competition_id"], fixture.get("season"), before,
                    ),
                    provider.recent_team_matches(
                        fixture["away_team"], fixture.get("away_team_id"),
                        fixture["competition_id"], fixture.get("season"), before,
                    ),
                )
                analysis = analyse_matches(
                    fixture["home_team"], fixture["away_team"],
                    home_recent, away_recent, odds=None, is_demo=False,
                )
                ranking = rank_market_candidates(analysis, is_demo=provider.is_demo)
                return {
                    "fixture": fixture,
                    "analysis_available": True,
                    "analysis": analysis,
                    "recommendation": ranking,
                }
            except ValueError as exc:
                return {
                    "fixture": fixture,
                    "analysis_available": False,
                    "analysis": None,
                    "recommendation": {
                        "candidates": [],
                        "decision": "NO_SELECTION",
                        "can_recommend_real_money_bet": False,
                        "calibration_status": "NOT_VALIDATED",
                        "bookmaker_odds_status": "NOT_CONNECTED",
                        "reason": str(exc),
                    },
                }
            except Exception as exc:
                return {
                    "fixture": fixture,
                    "analysis_available": False,
                    "analysis": None,
                    "recommendation": {
                        "candidates": [],
                        "decision": "NO_SELECTION",
                        "can_recommend_real_money_bet": False,
                        "calibration_status": "NOT_VALIDATED",
                        "bookmaker_odds_status": "NOT_CONNECTED",
                        "reason": f"Dato non disponibile: {type(exc).__name__}",
                    },
                }

    items = await asyncio.gather(*(inspect_fixture(f) for f in upcoming))
    ranked = []
    for item in items:
        for candidate in item["recommendation"].get("candidates", []):
            ranked.append({
                "fixture": item["fixture"],
                **candidate,
                "decision": "WATCHLIST_ONLY",
                "can_recommend_real_money_bet": False,
            })
    ranked.sort(key=lambda x: x["probability"], reverse=True)
    return {
        "items": items,
        "ranked_candidates": ranked[:40],
        "count": len(items),
        "analyzed_count": sum(1 for item in items if item["analysis_available"]),
        "candidate_count": len(ranked),
        "source": provider.name,
        "is_demo": provider.is_demo,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calibration_status": "NOT_VALIDATED",
        "bookmaker_odds_status": "NOT_CONNECTED",
        "can_recommend_real_money_bet": False,
        "message": "Ranking statistico sperimentale: nessuna giocata è considerata sicura. Quote aggiornate e validazione out-of-sample sono obbligatorie prima di parlare di value bet.",
    }


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
    try:
        provider = get_provider()
    except Exception:
        raise HTTPException(status_code=503, detail="Fonte dati non configurata correttamente.")
    fixture = await verified_match_context(provider, body)
    # Client-supplied analysis, scores and team names are intentionally ignored.
    result = await explain(body.message, fixture, None)
    result["context"] = {"fixture_id": fixture["id"], "source": fixture["source"], "verified_at": fixture["verified_at"]}
    return result

@app.get("/api/predictions")
@limiter.limit("30/minute")
async def predictions(request: Request, limit: int=Query(default=25,ge=1,le=100), db: Session=Depends(get_db)):
    rows=db.query(Prediction).order_by(Prediction.created_at.desc()).limit(limit).all()
    return {"items":[{"id":r.id,"fixture_id":r.fixture_id,"home_team":r.home_team,"away_team":r.away_team,"model_version":r.model_version,"source":r.source,"data_retrieved_at":r.data_retrieved_at.isoformat() if r.data_retrieved_at else None,"probabilities":{"home":r.p_home,"draw":r.p_draw,"away":r.p_away},"odds":{"home":r.odds_home,"draw":r.odds_draw,"away":r.odds_away},"created_at":r.created_at.isoformat() if r.created_at else None} for r in rows]}

@app.get("/")
async def root():
    return {"name":settings.app_name,"api_docs":"/docs","health":"/api/health"}
