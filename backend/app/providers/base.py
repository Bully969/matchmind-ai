from abc import ABC, abstractmethod
from datetime import date
from typing import Any

class DataProvider(ABC):
    name: str
    is_demo: bool = False

    @abstractmethod
    async def competitions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def fixtures(self, date_from: date, date_to: date, competition_id: str | None = None) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def recent_team_matches(self, team_name: str, team_id: str | None, competition_id: str, season: str | None, before: date | None = None) -> list[dict[str, Any]]: ...
