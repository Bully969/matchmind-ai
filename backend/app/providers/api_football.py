from datetime import date, datetime, timezone
import httpx
from .base import DataProvider

class ApiFootballProvider(DataProvider):
    name="api_football"
    is_demo=False
    base_url="https://v3.football.api-sports.io"

    def __init__(self, api_key: str):
        self.api_key=api_key
        self._cache={}

    async def _get(self,path,params=None,ttl=1800):
        import time
        key=(path,tuple(sorted((params or {}).items())))
        now=time.time()
        if key in self._cache and self._cache[key][0]>now:
            return self._cache[key][1]
        async with httpx.AsyncClient(timeout=25) as client:
            response=await client.get(self.base_url+path,headers={"x-apisports-key":self.api_key},params=params or {})
            response.raise_for_status()
            data=response.json()
        if data.get("errors"):
            raise RuntimeError(f"API-Football ha restituito errori: {data['errors']}")
        self._cache[key]=(now+ttl,data)
        return data

    async def competitions(self):
        # API-Football is paginated; cap pages to conserve the advertised free quota.
        out=[]
        for page in range(1,4):
            data=await self._get("/leagues",{"current":"true","page":page},ttl=21600)
            for row in data.get("response",[]):
                league=row.get("league") or {}; country=row.get("country") or {}; seasons=row.get("seasons") or []
                active=next((s for s in seasons if s.get("current")), seasons[-1] if seasons else {})
                out.append({"id":str(league.get("id")),"name":league.get("name") or "Unknown","country":country.get("name"),"season":str(active.get("year")) if active.get("year") else None,"source":self.name,"is_demo":False})
            paging=data.get("paging") or {}
            if int(paging.get("current",page)) >= int(paging.get("total",page)):
                break
        return out

    def _normalize(self,row):
        league=row.get("league") or {}; country=league.get("country"); fixture=row.get("fixture") or {}; teams=row.get("teams") or {}; home=teams.get("home") or {}; away=teams.get("away") or {}; goals=row.get("goals") or {}
        kickoff=None
        try:
            kickoff=datetime.fromisoformat(str(fixture.get("date")).replace("Z","+00:00"))
        except (ValueError,TypeError):
            pass
        return {"id":str(fixture.get("id")),"competition_id":str(league.get("id")),"competition_name":league.get("name") or "Unknown","country":country,"season":str(league.get("season")) if league.get("season") else None,"kickoff":kickoff,"status":(fixture.get("status") or {}).get("long","Scheduled"),"home_team":home.get("name") or "Unknown","away_team":away.get("name") or "Unknown","home_team_id":str(home.get("id")) if home.get("id") else None,"away_team_id":str(away.get("id")) if away.get("id") else None,"home_score":goals.get("home"),"away_score":goals.get("away"),"source":self.name,"is_demo":False}

    async def fixtures(self,date_from:date,date_to:date,competition_id:str|None=None):
        params={"from":date_from.isoformat(),"to":date_to.isoformat(),"timezone":"Europe/Rome"}
        if competition_id:
            params["league"]=competition_id
        data=await self._get("/fixtures",params,ttl=900)
        return [self._normalize(row) for row in data.get("response",[])]

    async def recent_team_matches(self,team_name:str,team_id:str|None,competition_id:str,season:str|None,before:date|None=None):
        if not team_id:
            return []
        params={"team":team_id,"last":10,"league":competition_id}
        if season:
            try: params["season"]=int(season)
            except ValueError: pass
        data=await self._get("/fixtures",params,ttl=21600)
        matches=[]
        for row in data.get("response",[]):
            m=self._normalize(row)
            if m.get("home_score") is None or m.get("away_score") is None or not m.get("kickoff"):
                continue
            if before and m["kickoff"].date() >= before:
                continue
            if str(m.get("competition_id")) != str(competition_id):
                continue
            if str(m.get("home_team_id")) == str(team_id):
                gf,ga,venue=m["home_score"],m["away_score"],"home"
            elif str(m.get("away_team_id")) == str(team_id):
                gf,ga,venue=m["away_score"],m["home_score"],"away"
            else:
                continue
            matches.append({"date":m["kickoff"].date().isoformat(),"goals_for":gf,"goals_against":ga,"venue":venue,"is_demo":False})
        return matches[:10]
