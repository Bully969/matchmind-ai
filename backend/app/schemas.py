from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import Any

class Competition(BaseModel):
    id: str
    name: str
    country: str | None = None
    season: str | None = None
    source: str
    is_demo: bool = False

class Fixture(BaseModel):
    id: str
    competition_id: str
    competition_name: str
    country: str | None = None
    season: str | None = None
    kickoff: datetime | None = None
    status: str = "SCHEDULED"
    home_team: str
    away_team: str
    home_team_id: str | None = None
    away_team_id: str | None = None
    home_score: int | None = None
    away_score: int | None = None
    source: str
    is_demo: bool = False

class AnalyzeRequest(BaseModel):
    fixture_id: str
    competition_id: str
    competition_name: str = ""
    season: str | None = None
    kickoff: datetime | None = None
    home_team: str
    away_team: str
    home_team_id: str | None = None
    away_team_id: str | None = None
    odds_home: float | None = Field(default=None, gt=1, le=1000)
    odds_draw: float | None = Field(default=None, gt=1, le=1000)
    odds_away: float | None = Field(default=None, gt=1, le=1000)
    is_demo: bool = False

class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1500)
    fixture: dict[str, Any]
    analysis: dict[str, Any] | None = None

class SettleRequest(BaseModel):
    outcome: str = Field(pattern="^(home|draw|away|void)$")
