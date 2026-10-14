"""Ranked statistical candidates with strict, explicit no-bet gates.

This is a decision-support layer, not a source of guaranteed betting advice.
Without licensed real-time odds and a validated/calibrated model, candidates are
watchlist-only and must never be described as value bets or safe bets.
"""
from typing import Any

MIN_CANDIDATE_PROBABILITY = 0.60
MIN_MATCHES_PER_TEAM = 7

def rank_market_candidates(analysis: dict[str, Any], is_demo: bool = False) -> dict[str, Any]:
    quality = analysis.get("data_quality") or {}
    probabilities = analysis.get("probabilities") or {}
    markets = analysis.get("markets") or {}
    home = analysis.get("home_team", "Casa")
    away = analysis.get("away_team", "Trasferta")

    sample_home = int(quality.get("home_matches") or 0)
    sample_away = int(quality.get("away_matches") or 0)
    enough_history = min(sample_home, sample_away) >= MIN_MATCHES_PER_TEAM
    candidates = [
        {"market": "1", "label": f"Vittoria {home}", "probability": probabilities.get("home")},
        {"market": "X", "label": "Pareggio", "probability": probabilities.get("draw")},
        {"market": "2", "label": f"Vittoria {away}", "probability": probabilities.get("away")},
        {"market": "over_2_5", "label": "Over 2.5 gol", "probability": markets.get("over_2_5")},
        {"market": "under_2_5", "label": "Under 2.5 gol", "probability": markets.get("under_2_5")},
        {"market": "btts_yes", "label": "Entrambe segnano — Sì", "probability": markets.get("btts_yes")},
        {"market": "btts_no", "label": "Entrambe segnano — No", "probability": markets.get("btts_no")},
    ]
    eligible = []
    if not is_demo and enough_history and quality.get("level") == "moderate":
        for item in candidates:
            p = item.get("probability")
            if isinstance(p, (int, float)) and MIN_CANDIDATE_PROBABILITY <= p <= 1:
                eligible.append({
                    **item,
                    "probability": round(float(p), 4),
                    "status": "WATCHLIST_ONLY",
                    "decision": "WAIT_FOR_ODDS_AND_VALIDATION",
                    "blocking_reasons": [
                        "Nessun feed bookmaker con quota e timestamp collegato.",
                        "Modello baseline non ancora calibrato e verificato out-of-sample.",
                    ],
                })
    eligible.sort(key=lambda item: item["probability"], reverse=True)

    if is_demo:
        reason = "La fonte è dimostrativa: nessun candidato pubblicabile."
    elif not enough_history:
        reason = (
            f"Storico insufficiente: servono almeno {MIN_MATCHES_PER_TEAM} risultati "
            f"validi per ciascuna squadra (casa {sample_home}, trasferta {sample_away})."
        )
    elif not eligible:
        reason = (
            f"Nessun mercato supera la soglia esplorativa del "
            f"{MIN_CANDIDATE_PROBABILITY:.0%}; non forzare una selezione."
        )
    else:
        reason = (
            "Candidati statistici in watchlist, non giocate consigliate: mancano "
            "quote bookmaker aggiornate e validazione/calibrazione del modello."
        )

    return {
        "candidates": eligible,
        "decision": "WATCHLIST_ONLY" if eligible else "NO_SELECTION",
        "can_recommend_real_money_bet": False,
        "minimum_probability_threshold": MIN_CANDIDATE_PROBABILITY,
        "calibration_status": "NOT_VALIDATED",
        "bookmaker_odds_status": "NOT_CONNECTED",
        "reason": reason,
    }
