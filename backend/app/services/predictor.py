from math import exp, factorial
from statistics import mean
from typing import Any

MODEL_VERSION = "poisson-baseline-v1"

def _poisson_pmf(k: int, lam: float) -> float:
    return exp(-lam) * (lam ** k) / factorial(k)

def _team_averages(matches: list[dict[str, Any]]) -> tuple[float, float]:
    good=[m for m in matches if isinstance(m.get("goals_for"),int) and isinstance(m.get("goals_against"),int)]
    if len(good)<5:
        raise ValueError(f"Servono almeno 5 risultati recenti validi; disponibili {len(good)}")
    # Recency weighting: latest result counts more, but no recent score is treated as certainty.
    weights=[1.0/(1.0+0.12*i) for i in range(len(good))]
    total=sum(weights)
    gf=sum(m["goals_for"]*w for m,w in zip(good,weights))/total
    ga=sum(m["goals_against"]*w for m,w in zip(good,weights))/total
    return gf,ga

def analyse_matches(home_team: str, away_team: str, home_recent: list[dict[str, Any]], away_recent: list[dict[str, Any]], odds: dict[str, float|None] | None=None, is_demo: bool=False) -> dict[str, Any]:
    hgf,hga=_team_averages(home_recent)
    agf,aga=_team_averages(away_recent)
    # Intentionally simple baseline: future versions should add home/away splits, league prior, xG and calibration.
    lam_h=min(4.0,max(0.15,0.55*hgf+0.45*aga))
    lam_a=min(4.0,max(0.15,0.55*agf+0.45*hga))
    max_goals=10
    grid={(h,a):_poisson_pmf(h,lam_h)*_poisson_pmf(a,lam_a) for h in range(max_goals+1) for a in range(max_goals+1)}
    # Renormalize truncated grid so markets add to 100% within numerical truncation.
    total=sum(grid.values())
    grid={key:value/total for key,value in grid.items()}
    p_home=sum(p for (h,a),p in grid.items() if h>a)
    p_draw=sum(p for (h,a),p in grid.items() if h==a)
    p_away=sum(p for (h,a),p in grid.items() if h<a)
    p_over25=sum(p for (h,a),p in grid.items() if h+a>=3)
    p_btts=sum(p for (h,a),p in grid.items() if h>0 and a>0)
    sample=min(len(home_recent),len(away_recent))
    quality="low" if sample<7 else "moderate"
    probability_map={"home":p_home,"draw":p_draw,"away":p_away}
    value_bets=[]
    for key,label in [("home",f"Vittoria {home_team}"),("draw","Pareggio"),("away",f"Vittoria {away_team}")]:
        odd=(odds or {}).get(key)
        if odd and odd>1:
            ev=probability_map[key]*odd-1
            value_bets.append({"market":key,"label":label,"odds":odd,"estimated_probability":round(probability_map[key],4),"implied_probability":round(1/odd,4),"expected_value":round(ev,4),"edge_vs_raw_implied":round(probability_map[key]-1/odd,4),"warning":"Stima esplorativa; non corregge il margine bookmaker e non dimostra un vantaggio reale."})
    max_outcome=max(probability_map,key=probability_map.get)
    return {
        "model_version":MODEL_VERSION,
        "home_team":home_team,"away_team":away_team,
        "expected_goals":{"home":round(lam_h,3),"away":round(lam_a,3)},
        "probabilities":{"home":round(p_home,4),"draw":round(p_draw,4),"away":round(p_away,4)},
        "markets":{"over_2_5":round(p_over25,4),"under_2_5":round(1-p_over25,4),"btts_yes":round(p_btts,4),"btts_no":round(1-p_btts,4)},
        "most_likely_1x2":max_outcome,
        "data_quality":{"level":quality,"home_matches":len(home_recent),"away_matches":len(away_recent),"note":"Baseline su risultati recenti; non usa xG, assenze, quote di mercato o formazione confermata."},
        "value_bets":value_bets,
        "is_demo":is_demo,
        "disclaimer":"Le probabilità sono stime sperimentali, non garanzie. Una probabilità più alta non implica profitto; la qualità dipende dalla fonte e dalla calibrazione fuori campione."
    }
