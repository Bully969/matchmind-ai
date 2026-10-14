import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from .base import DataProvider

class OpenFootballProvider(DataProvider):
    """Reads user-synced openfootball/football.json files (repository is CC0)."""
    name = "openfootball"
    is_demo = False

    def __init__(self, data_dir: str):
        candidate = Path(data_dir)
        if not candidate.is_absolute():
            # Prefer a path relative to the project root, with cwd as a fallback.
            project_root = Path(__file__).resolve().parents[3]
            rooted = project_root / candidate
            cwd_path = Path.cwd() / candidate
            candidate = rooted if rooted.exists() or not cwd_path.exists() else cwd_path
        self.data_dir = candidate.resolve()

    def _files(self):
        if not self.data_dir.exists():
            return []
        return list(self.data_dir.rglob("*.json"))

    def _load(self, path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict) and isinstance(obj.get("matches"), list):
                return obj
        except (OSError, json.JSONDecodeError):
            return None
        return None

    def _comp_id(self, path: Path) -> str:
        # Use a season-independent competition ID so recent results can span seasons.
        parts=list(path.relative_to(self.data_dir).with_suffix("").parts)
        parts=[part for part in parts if not re.fullmatch(r"\d{4}(?:-\d{2,4})?", part)]
        return "/".join(parts).replace("\\", "/")

    async def competitions(self):
        by_id={}
        for path in self._files():
            data=self._load(path)
            if not data:
                continue
            comp_id=self._comp_id(path)
            season=path.parent.name
            item={"id": comp_id, "name": data.get("name") or path.stem, "country": None, "season": season, "source": self.name, "is_demo": False}
            # Prefer the most recent season for the catalogue label.
            if comp_id not in by_id or str(season)>str(by_id[comp_id].get("season") or ""):
                by_id[comp_id]=item
        return sorted(by_id.values(), key=lambda c: c["name"].lower())

    def _normalize_match(self, item: dict[str, Any], comp_id: str, comp_name: str, path: Path):
        raw_date=item.get("date")
        if not raw_date:
            return None
        try:
            # OpenFootball usually publishes ISO dates; tolerate full ISO datetime strings.
            kickoff=datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            if kickoff.tzinfo is None:
                kickoff=kickoff.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        score=item.get("score") or {}
        ft=score.get("ft") if isinstance(score,dict) else None
        hs=ft[0] if isinstance(ft,list) and len(ft)>1 and all(isinstance(v,int) for v in ft[:2]) else None
        aws=ft[1] if isinstance(ft,list) and len(ft)>1 and all(isinstance(v,int) for v in ft[:2]) else None
        home=str(item.get("team1") or item.get("home") or "Unknown")
        away=str(item.get("team2") or item.get("away") or "Unknown")
        identifier=f"openfootball:{comp_id}:{kickoff.date().isoformat()}:{home}:{away}"
        return {"id":identifier,"competition_id":comp_id,"competition_name":comp_name,"country":None,"season":path.parent.name,"kickoff":kickoff,"status":"FINISHED" if hs is not None and aws is not None else "SCHEDULED","home_team":home,"away_team":away,"home_team_id":None,"away_team_id":None,"home_score":hs,"away_score":aws,"source":self.name,"is_demo":False,"round":item.get("round")}

    async def fixtures(self, date_from: date, date_to: date, competition_id: str | None = None):
        out=[]
        for path in self._files():
            cid=self._comp_id(path)
            if competition_id and competition_id != cid:
                continue
            data=self._load(path)
            if not data:
                continue
            cname=str(data.get("name") or path.stem)
            for item in data["matches"]:
                if not isinstance(item,dict):
                    continue
                match=self._normalize_match(item,cid,cname,path)
                if match and date_from <= match["kickoff"].date() <= date_to:
                    out.append(match)
        return sorted(out,key=lambda f:f["kickoff"])

    async def recent_team_matches(self, team_name: str, team_id: str | None, competition_id: str, season: str | None, before: date | None = None):
        # Exact name matching is deliberate: no fuzzy inference that could merge different teams.
        out=[]
        for path in self._files():
            cid=self._comp_id(path)
            if competition_id and cid != competition_id:
                continue
            data=self._load(path)
            if not data:
                continue
            cname=str(data.get("name") or path.stem)
            for item in data["matches"]:
                if not isinstance(item,dict):
                    continue
                match=self._normalize_match(item,cid,cname,path)
                if not match or match["status"] != "FINISHED":
                    continue
                if before and match["kickoff"].date() >= before:
                    continue
                if match["home_team"].casefold() == team_name.casefold():
                    out.append({"date":match["kickoff"].date().isoformat(),"goals_for":match["home_score"],"goals_against":match["away_score"],"venue":"home","is_demo":False})
                elif match["away_team"].casefold() == team_name.casefold():
                    out.append({"date":match["kickoff"].date().isoformat(),"goals_for":match["away_score"],"goals_against":match["home_score"],"venue":"away","is_demo":False})
        return sorted(out,key=lambda m:m["date"],reverse=True)[:10]
