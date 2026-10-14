from datetime import date, datetime, timezone
import httpx
from .base import DataProvider

class FootballDataOrgProvider(DataProvider):
    name = "football_data_org"
    is_demo = False
    base_url = "https://api.football-data.org/v4"

    def __init__(self, api_key: str):
        self.api_key=api_key
        self._cache={}

    async def _get(self, path, params=None, ttl=1800):
        import time
        key=(path,tuple(sorted((params or {}).items())))
        now=time.time()
        if key in self._cache and self._cache[key][0] > now:
            return self._cache[key][1]
        async with httpx.AsyncClient(timeout=20) as client:
            response=await client.get(self.base_url+path,headers={"X-Auth-Token":self.api_key},params=params or {})
            response.raise_for_status()
            data=response.json()
        self._cache[key]=(now+ttl,data)
        return data

    async def competitions(self):
        data=await self._get("/competitions",ttl=21600)
        out=[]
        for c in data.get("competitions",[]):
            area=c.get("area") or {}
            season=c.get("currentSeason") or {}
            out.append({"id":str(c.get("id")),"name":c.get("name") or "Unknown","country":area.get("name"),"season":str(season.get("startDate", ""))[:4] or None,"source":self.name,"is_demo":False})
        return out

    def _normalize(self,m):
        comp=m.get("competition") or {}; area=comp.get("area") or {}; home=m.get("homeTeam") or {}; away=m.get("awayTeam") or {}; score=m.get("score") or {}; ft=score.get("fullTime") or {}
        kickoff=None
        try:
            kickoff=datetime.fromisoformat(str(m.get("utcDate")).replace("Z","+00:00"))
        except (ValueError,TypeError):
            pass
        return {"id":str(m.get("id")),"competition_id":str(comp.get("id")),"competition_name":comp.get("name") or "Unknown","country":area.get("name"),"season":str((m.get("season") or {}).get("startDate", ""))[:4] or None,"kickoff":kickoff,"status":m.get("status","SCHEDULED"),"home_team":home.get("name") or "Unknown","away_team":away.get("name") or "Unknown","home_team_id":str(home.get("id")) if home.get("id") else None,"away_team_id":str(away.get("id")) if away.get("id") else None,"home_score":ft.get("home"),"away_score":ft.get("away"),"source":self.name,"is_demo":False}

    async def fixtures(self, date_from: date, date_to: date, competition_id: str|None=None):
        params={"dateFrom":date_from.isoformat(),"dateTo":date_to.isoformat()}
        if competition_id:
            params["competitions"]=competition_id
        data=await self._get("/matches",params,ttl=900)
        return [self._normalize(m) for m in data.get("matches",[])]

    async def recent_team_matches(self, team_name: str, team_id: str|None, competition_id: str, season: str|None, before: date|None=None):
        if not team_id:
            return []
        params={"status":"FINISHED","limit":10}
        if season:
            params["season"]=season
        data=await self._get(f"/teams/{team_id}/matches",params,ttl=21600)
        matches=[]
        for raw in data.get("matches",[]):
            m=self._normalize(raw)
            if m.get("status") != "FINISHED" or m.get("home_score") is None or m.get("away_score") is None:
                continue
            if before and m.get("kickoff") and m["kickoff"].date() >= before:
                continue
            if str(m.get("competition_id")) != str(competition_id):
                continue
            if str(m.get("home_team_id")) == str(team_id):
                gf,ga=m["home_score"],m["away_score"]; venue="home"
            elif str(m.get("away_team_id")) == str(team_id):
                gf,ga=m["away_score"],m["home_score"]; venue="away"
            else:
                continue
            matches.append({"date":m["kickoff"].date().isoformat() if m.get("kickoff") else "", "goals_for":gf,"goals_against":ga,"venue":venue,"is_demo":False})
        return matches[:10]
