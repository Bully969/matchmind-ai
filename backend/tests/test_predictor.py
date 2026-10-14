from app.services.predictor import analyse_matches

def sample(gf,ga):
    return [{"goals_for":gf,"goals_against":ga,"date":f"2026-0{i+1}-01"} for i in range(8)]

def test_probabilities_sum_to_one_and_markets_are_bounded():
    result=analyse_matches("A","B",sample(2,1),sample(1,2))
    probs=result["probabilities"]
    assert abs(sum(probs.values())-1.0)<1e-6
    assert all(0 <= p <= 1 for p in probs.values())
    assert 0 <= result["markets"]["over_2_5"] <= 1

def test_value_expected_value_is_calculated_when_odds_present():
    result=analyse_matches("A","B",sample(2,1),sample(1,2),{"home":2.0,"draw":None,"away":None})
    assert len(result["value_bets"]) == 1
    item=result["value_bets"][0]
    assert abs(item["expected_value"]-(item["estimated_probability"]*2.0-1))<0.001


def test_analysis_never_claims_real_money_bet_is_validated():
    result=analyse_matches("A","B",sample(2,1),sample(1,2))
    gate=result["decision_support"]
    assert gate["status"] == "ANALYSIS_ONLY"
    assert gate["can_recommend_real_money_bet"] is False
    assert gate["calibration_status"] == "NOT_VALIDATED"
    assert len(gate["reasons"]) >= 2
