from datetime import date, datetime, time, timedelta, timezone
from .base import DataProvider

class DemoProvider(DataProvider):
    name = "demo"
    is_demo = True
    teams = [
        ("demo-serie-a", "Serie A — DEMO", "Italia", "Inter (demo)", "Juventus (demo)"),
        ("demo-premier", "Premier League — DEMO", "Inghilterra", "Arsenal (demo)", "Liverpool (demo)"),
        ("demo-liga", "La Liga — DEMO", "Spagna", "Barcelona (demo)", "Real Madrid (demo)"),
    ]

    async def competitions(self):
        return [{"id": c[0], "name": c[1], "country": c[2], "season": "demo", "source": self.name, "is_demo": True} for c in self.teams]

    async def fixtures(self, date_from: date, date_to: date, competition_id: str | None = None):
        out = []
        today = date.today()
        for idx, comp in enumerate(self.teams):
            cid, cname, country, home, away = comp
            if competition_id and competition_id != cid:
                continue
            kickoff_date = today + timedelta(days=idx)
            if not date_from <= kickoff_date <= date_to:
                continue
            kickoff = datetime.combine(kickoff_date, time(hour=18 + (idx % 2)), tzinfo=timezone.utc)
            out.append({"id": f"demo-{idx+1}", "competition_id": cid, "competition_name": cname, "country": country, "season": "demo", "kickoff": kickoff, "status": "SCHEDULED", "home_team": home, "away_team": away, "home_team_id": f"dh{idx}", "away_team_id": f"da{idx}", "home_score": None, "away_score": None, "source": self.name, "is_demo": True})
        return out

    async def recent_team_matches(self, team_name: str, team_id: str | None, competition_id: str, season: str | None, before: date | None = None):
        # Explicitly synthetic scores: only for testing UI wiring, never represented as real results.
        home_flag = team_name.endswith("home") or "Inter" in team_name or "Arsenal" in team_name or "Barcelona" in team_name
        seed = sum(ord(ch) for ch in team_name) % 3
        scores = [(2,0),(1,1),(1,0),(2,1),(0,1),(3,1),(1,0),(2,2),(0,0),(1,2)]
        rows=[]
        for i,(gf,ga) in enumerate(scores):
            if (i+seed) % 4 == 0:
                gf,ga=ga,gf
            rows.append({"date": (date.today()-timedelta(days=i*6+2)).isoformat(), "goals_for": gf, "goals_against": ga, "venue": "unknown", "is_demo": True})
        return rows
