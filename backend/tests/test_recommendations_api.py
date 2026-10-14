from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import main


class FakeProvider:
    name = "test_public_data"
    is_demo = False

    def __init__(self):
        kickoff = datetime.now(timezone.utc) + timedelta(days=5)
        self.fixture = {
            "id": "test-fixture-1",
            "competition_id": "it.1",
            "competition_name": "Test League",
            "season": "2026-27",
            "kickoff": kickoff,
            "kickoff_time_known": True,
            "status": "SCHEDULED",
            "home_team": "Casa FC",
            "away_team": "Trasferta FC",
            "home_score": None,
            "away_score": None,
            "source": self.name,
            "is_demo": False,
        }

    async def fixtures(self, date_from, date_to, competition_id=None):
        if date_from <= self.fixture["kickoff"].date() <= date_to:
            return [self.fixture]
        return []

    async def recent_team_matches(self, team_name, team_id, competition_id, season, before=None):
        if team_name == "Casa FC":
            gf, ga = 3, 1
        else:
            gf, ga = 2, 2
        return [
            {"date": (datetime.now(timezone.utc).date() - timedelta(days=i + 1)).isoformat(),
             "goals_for": gf, "goals_against": ga, "venue": "home", "is_demo": False}
            for i in range(10)
        ]


def test_ranked_recommendations_are_watchlist_only(monkeypatch):
    monkeypatch.setattr(main, "get_provider", lambda: FakeProvider())
    fixture_date = (datetime.now(timezone.utc).date() + timedelta(days=5)).isoformat()
    with TestClient(main.app) as client:
        response = client.get(
            "/api/recommendations",
            params={"date_from": fixture_date, "date_to": fixture_date},
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["count"] == 1
    assert payload["analyzed_count"] == 1
    assert payload["can_recommend_real_money_bet"] is False
    assert payload["calibration_status"] == "NOT_VALIDATED"
    assert payload["bookmaker_odds_status"] == "NOT_CONNECTED"
    assert payload["candidate_count"] >= 1
    assert all(item["decision"] == "WATCHLIST_ONLY" for item in payload["ranked_candidates"])


def test_ranked_recommendations_reject_ranges_over_two_weeks():
    with TestClient(main.app) as client:
        response = client.get(
            "/api/recommendations",
            params={"date_from": "2026-10-01", "date_to": "2026-10-20"},
        )
    assert response.status_code == 400
