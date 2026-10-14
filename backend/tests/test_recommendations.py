from app.services.recommendations import rank_market_candidates


def sample_analysis(level="moderate", home_n=10, away_n=9):
    return {
        "home_team": "Casa FC",
        "away_team": "Ospiti FC",
        "probabilities": {"home": 0.48, "draw": 0.25, "away": 0.27},
        "markets": {
            "over_2_5": 0.64,
            "under_2_5": 0.36,
            "btts_yes": 0.61,
            "btts_no": 0.39,
        },
        "data_quality": {
            "level": level,
            "home_matches": home_n,
            "away_matches": away_n,
        },
    }


def test_ranker_returns_watchlist_candidates_but_never_approves_real_money_bet():
    result = rank_market_candidates(sample_analysis())
    assert result["decision"] == "WATCHLIST_ONLY"
    assert result["can_recommend_real_money_bet"] is False
    assert result["calibration_status"] == "NOT_VALIDATED"
    assert result["bookmaker_odds_status"] == "NOT_CONNECTED"
    assert [x["market"] for x in result["candidates"]] == ["over_2_5", "btts_yes"]
    assert all(x["status"] == "WATCHLIST_ONLY" for x in result["candidates"])
    assert all(x["blocking_reasons"] for x in result["candidates"])


def test_ranker_does_not_create_candidates_with_insufficient_history():
    result = rank_market_candidates(sample_analysis(level="low", home_n=4, away_n=9))
    assert result["decision"] == "NO_SELECTION"
    assert result["candidates"] == []
    assert result["can_recommend_real_money_bet"] is False
    assert "servono almeno" in result["reason"]


def test_ranker_does_not_publish_candidates_for_demo_data():
    result = rank_market_candidates(sample_analysis(), is_demo=True)
    assert result["decision"] == "NO_SELECTION"
    assert result["candidates"] == []
    assert "dimostrativa" in result["reason"]


def test_ranker_does_not_force_a_pick_when_no_market_clears_threshold():
    a = sample_analysis()
    a["markets"] = {"over_2_5": 0.51, "under_2_5": 0.49, "btts_yes": 0.50, "btts_no": 0.50}
    result = rank_market_candidates(a)
    assert result["decision"] == "NO_SELECTION"
    assert result["candidates"] == []
    assert "non forzare" in result["reason"]
