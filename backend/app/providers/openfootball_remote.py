"""Remote, no-key provider backed by the public-domain openfootball/football.json datasets.

This source contains fixtures and final scores, not live events, bookmaker odds, xG,
lineups or injury reports. It is refreshed from the upstream repository, not from a live
sports feed. The in-process cache reduces requests and respects the source's daily cadence.
"""
import asyncio
import time as clock
from datetime import date, datetime, time
from typing import Any

import httpx

from .base import DataProvider


BASE_URL = "https://raw.githubusercontent.com/openfootball/football.json/master"
CACHE_TTL_SECONDS = 6 * 60 * 60

# Only competitions with a dataset for the current 2026/27 season appear in the live
# catalogue. The 2025/26 file is still used to seed recent-form estimates.
COMPETITIONS: dict[str, dict[str, Any]] = {
    "it.1": {"name": "Serie A", "country": "Italia", "current": "2026-27/it.1.json", "previous": "2025-26/it.1.json"},
    "en.1": {"name": "Premier League", "country": "Inghilterra", "current": "2026-27/en.1.json", "previous": "2025-26/en.1.json"},
    "en.2": {"name": "Championship", "country": "Inghilterra", "current": "2026-27/en.2.json", "previous": "2025-26/en.2.json"},
    "de.1": {"name": "Bundesliga", "country": "Germania", "current": "2026-27/de.1.json", "previous": "2025-26/de.1.json"},
    "es.1": {"name": "La Liga", "country": "Spagna", "current": "2026-27/es.1.json", "previous": "2025-26/es.1.json"},
    "fr.1": {"name": "Ligue 1", "country": "Francia", "current": "2026-27/fr.1.json", "previous": "2025-26/fr.1.json"},
    "nl.1": {"name": "Eredivisie", "country": "Paesi Bassi", "current": "2026-27/nl.1.json", "previous": "2025-26/nl.1.json"},
    "pt.1": {"name": "Primeira Liga", "country": "Portogallo", "current": "2026-27/pt.1.json", "previous": "2025-26/pt.1.json"},
}


class OpenFootballRemoteProvider(DataProvider):
    """Uses openfootball JSON files via HTTPS without an API key."""

    name = "openfootball_remote"
    is_demo = False

    def __init__(self, cache_ttl: int = CACHE_TTL_SECONDS):
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, dict[str, Any] | None]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def _dataset(self, path: str) -> dict[str, Any] | None:
        now = clock.monotonic()
        cached = self._cache.get(path)
        if cached and cached[0] > now:
            return cached[1]

        lock = self._locks.setdefault(path, asyncio.Lock())
        async with lock:
            now = clock.monotonic()
            cached = self._cache.get(path)
            if cached and cached[0] > now:
                return cached[1]

            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(f"{BASE_URL}/{path}", headers={"User-Agent": "MatchMind-AI/0.1"})
            if response.status_code == 404:
                data = None
            else:
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
                    raise RuntimeError(f"Dataset OpenFootball non valido: {path}")
            self._cache[path] = (clock.monotonic() + self.cache_ttl, data)
            return data

    async def _load_competition_seasons(self, competition_id: str) -> list[tuple[str, dict[str, Any]]]:
        config = COMPETITIONS.get(competition_id)
        if not config:
            return []
        paths = [(config["current"].split("/", 1)[0], config["current"]),
                 (config["previous"].split("/", 1)[0], config["previous"])]
        results = await asyncio.gather(*(self._dataset(path) for _, path in paths), return_exceptions=True)
        loaded: list[tuple[str, dict[str, Any]]] = []
        errors: list[Exception] = []
        for (season, _), result in zip(paths, results):
            if isinstance(result, Exception):
                errors.append(result)
            elif result:
                loaded.append((season, result))
        if not loaded and errors:
            raise RuntimeError(f"Impossibile recuperare i dataset OpenFootball: {type(errors[0]).__name__}")
        return loaded

    @staticmethod
    def _normalize_match(raw: dict[str, Any], competition_id: str, competition: dict[str, Any],
                         season: str) -> dict[str, Any] | None:
        raw_date = raw.get("date")
        home = str(raw.get("team1") or "").strip()
        away = str(raw.get("team2") or "").strip()
        if not raw_date or not home or not away:
            return None
        try:
            match_date = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            return None

        raw_time = raw.get("time")
        kickoff_time = time(12, 0)
        time_known = False
        if raw_time:
            try:
                kickoff_time = time.fromisoformat(str(raw_time)[:5])
                time_known = True
            except ValueError:
                pass
        # football.json provides local wall-clock times without a timezone. Keep the
        # datetime naive instead of falsely labelling the kickoff as UTC.
        kickoff = datetime.combine(match_date, kickoff_time)

        score = raw.get("score") or {}
        ft = score.get("ft") if isinstance(score, dict) else None
        has_final_score = (
            isinstance(ft, list) and len(ft) >= 2
            and isinstance(ft[0], int) and isinstance(ft[1], int)
        )
        if has_final_score:
            status = "FINISHED"
            home_score, away_score = ft[0], ft[1]
        else:
            status = "SCHEDULED" if match_date >= date.today() else "UNKNOWN"
            home_score = away_score = None

        fixture_id = f"openfootball:{competition_id}:{season}:{match_date.isoformat()}:{home}:{away}"
        return {
            "id": fixture_id,
            "competition_id": competition_id,
            "competition_name": competition["name"],
            "country": competition["country"],
            "season": season,
            "kickoff": kickoff,
            "kickoff_time_known": time_known,
            "status": status,
            "home_team": home,
            "away_team": away,
            "home_team_id": None,
            "away_team_id": None,
            "home_score": home_score,
            "away_score": away_score,
            "source": "openfootball_remote",
            "is_demo": False,
            "round": raw.get("round"),
        }

    async def competitions(self):
        tasks = [self._dataset(config["current"]) for config in COMPETITIONS.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items = []
        errors = []
        for (competition_id, config), result in zip(COMPETITIONS.items(), results):
            if isinstance(result, Exception):
                errors.append(result)
                continue
            if not result:
                continue
            items.append({
                "id": competition_id,
                "name": config["name"],
                "country": config["country"],
                "season": "2026-27",
                "source": self.name,
                "is_demo": False,
            })
        if not items and errors:
            raise RuntimeError(f"OpenFootball non raggiungibile: {type(errors[0]).__name__}")
        return items

    async def fixtures(self, date_from: date, date_to: date, competition_id: str | None = None):
        if competition_id and competition_id not in COMPETITIONS:
            return []
        ids = [competition_id] if competition_id else list(COMPETITIONS)
        jobs = [self._load_competition_seasons(cid) for cid in ids]
        results = await asyncio.gather(*jobs, return_exceptions=True)
        out = []
        errors = []
        loaded_datasets = 0
        for cid, result in zip(ids, results):
            if isinstance(result, Exception):
                errors.append(result)
                continue
            loaded_datasets += len(result)
            config = COMPETITIONS[cid]
            for season, dataset in result:
                for raw in dataset.get("matches", []):
                    if not isinstance(raw, dict):
                        continue
                    fixture = self._normalize_match(raw, cid, config, season)
                    if fixture and date_from <= fixture["kickoff"].date() <= date_to:
                        out.append(fixture)
        if loaded_datasets == 0 and errors:
            raise RuntimeError(f"OpenFootball non raggiungibile: {type(errors[0]).__name__}")
        return sorted(out, key=lambda item: item["kickoff"])

    async def recent_team_matches(self, team_name: str, team_id: str | None, competition_id: str,
                                  season: str | None, before: date | None = None):
        if competition_id not in COMPETITIONS or not team_name:
            return []
        loaded = await self._load_competition_seasons(competition_id)
        out = []
        needle = team_name.casefold().strip()
        config = COMPETITIONS[competition_id]
        for season_name, dataset in loaded:
            for raw in dataset.get("matches", []):
                if not isinstance(raw, dict):
                    continue
                fixture = self._normalize_match(raw, competition_id, config, season_name)
                if not fixture or fixture["status"] != "FINISHED":
                    continue
                match_date = fixture["kickoff"].date()
                if before and match_date >= before:
                    continue
                if fixture["home_team"].casefold().strip() == needle:
                    out.append({"date": match_date.isoformat(), "goals_for": fixture["home_score"],
                                "goals_against": fixture["away_score"], "venue": "home", "is_demo": False})
                elif fixture["away_team"].casefold().strip() == needle:
                    out.append({"date": match_date.isoformat(), "goals_for": fixture["away_score"],
                                "goals_against": fixture["home_score"], "venue": "away", "is_demo": False})
        # De-duplicate and sort newest-first; cap is enough for the Poisson baseline.
        by_date = {}
        for match in out:
            by_date[(match["date"], match["goals_for"], match["goals_against"])] = match
        return sorted(by_date.values(), key=lambda match: match["date"], reverse=True)[:10]
