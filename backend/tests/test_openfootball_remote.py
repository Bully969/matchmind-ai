from datetime import date, timedelta

from app.providers.openfootball_remote import COMPETITIONS, OpenFootballRemoteProvider


def test_provider_has_only_declared_current_competitions():
    provider = OpenFootballRemoteProvider()
    assert provider.is_demo is False
    assert "it.1" in COMPETITIONS
    assert "en.1" in COMPETITIONS
    assert all(config["current"].startswith("2026-27/") for config in COMPETITIONS.values())


def test_normalize_real_finished_match_has_scores_and_is_not_demo():
    provider = OpenFootballRemoteProvider()
    fixture = provider._normalize_match(
        {
            "date": "2026-10-10",
            "time": "20:45",
            "round": "Matchday 6",
            "team1": "FC Internazionale Milano",
            "team2": "Parma Calcio 1913",
            "score": {"ft": [2, 0]},
        },
        "it.1",
        COMPETITIONS["it.1"],
        "2026-27",
    )
    assert fixture is not None
    assert fixture["status"] == "FINISHED"
    assert fixture["home_score"] == 2
    assert fixture["away_score"] == 0
    assert fixture["is_demo"] is False
    assert fixture["source"] == "openfootball_remote"
    assert fixture["kickoff"].hour == 20
    assert fixture["kickoff"].minute == 45
    assert str(fixture["kickoff"].tzinfo) == "Europe/Rome"


def test_normalize_future_match_does_not_invent_a_score():
    provider = OpenFootballRemoteProvider()
    fixture = provider._normalize_match(
        {
            "date": (date.today() + timedelta(days=5)).isoformat(),
            "time": "18:00",
            "team1": "Team A",
            "team2": "Team B",
        },
        "it.1",
        COMPETITIONS["it.1"],
        "2026-27",
    )
    assert fixture is not None
    assert fixture["status"] == "SCHEDULED"
    assert fixture["home_score"] is None
    assert fixture["away_score"] is None
    assert fixture["kickoff_time_known"] is True


def test_past_match_without_result_is_unknown_not_finished_or_live():
    provider = OpenFootballRemoteProvider()
    fixture = provider._normalize_match(
        {
            "date": (date.today() - timedelta(days=2)).isoformat(),
            "team1": "Team A",
            "team2": "Team B",
        },
        "it.1",
        COMPETITIONS["it.1"],
        "2026-27",
    )
    assert fixture is not None
    assert fixture["status"] == "UNKNOWN"
    assert fixture["home_score"] is None
    assert fixture["away_score"] is None
