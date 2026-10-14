from .demo import DemoProvider
from .openfootball import OpenFootballProvider
from .openfootball_remote import OpenFootballRemoteProvider
from .football_data_org import FootballDataOrgProvider
from .api_football import ApiFootballProvider
from ..config import settings

_provider=None

def get_provider():
    global _provider
    if _provider is not None:
        return _provider
    kind=settings.data_provider.strip().lower()
    if kind == "demo":
        _provider=DemoProvider()
    elif kind == "openfootball":
        _provider=OpenFootballProvider(settings.openfootball_data_dir)
    elif kind == "openfootball_remote":
        _provider=OpenFootballRemoteProvider()
    elif kind == "football_data_org":
        if not settings.football_data_api_key:
            raise RuntimeError("DATA_PROVIDER=football_data_org ma FOOTBALL_DATA_API_KEY è vuota")
        _provider=FootballDataOrgProvider(settings.football_data_api_key)
    elif kind == "api_football":
        if not settings.api_football_key:
            raise RuntimeError("DATA_PROVIDER=api_football ma API_FOOTBALL_KEY è vuota")
        _provider=ApiFootballProvider(settings.api_football_key)
    else:
        raise RuntimeError(f"Provider dati non riconosciuto: {kind}")
    return _provider

def reset_provider_for_tests():
    global _provider
    _provider=None
