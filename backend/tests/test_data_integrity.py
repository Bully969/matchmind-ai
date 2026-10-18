import asyncio
from datetime import date
import httpx
from fastapi.testclient import TestClient
from app import main
from app.config import settings
from app.providers.openfootball_remote import OpenFootballRemoteProvider, COMPETITIONS
from app.services.llm import provider_status


def test_unsupported_ai_is_not_reported_active(monkeypatch):
    monkeypatch.setattr(settings, 'ai_provider', 'gemini')
    with TestClient(main.app) as client:
        result = client.get('/api/health').json()
    assert result['ai_provider'] == 'template'
    assert result['ai_status']['configured'] == 'gemini'
    assert result['ai_status']['status'] == 'UNSUPPORTED_PROVIDER'
    assert result['ai_status']['model_verified'] is False


def test_configured_model_is_not_claimed_verified(monkeypatch):
    monkeypatch.setattr(settings, 'ai_provider', 'ollama')
    assert provider_status()['status'] == 'NOT_VERIFIED'
    assert provider_status()['model_verified'] is False


def test_cache_keeps_download_timestamp(monkeypatch):
    requests = []
    async def get(self, url, **kwargs):
        requests.append(url)
        return httpx.Response(200, json={'matches': []}, request=httpx.Request('GET', url))
    client_class = httpx.AsyncClient
    monkeypatch.setattr(client_class, 'get', get)
    # Network is fully mocked; do not inherit machine-specific proxy settings.
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: client_class(trust_env=False, **kwargs))
    provider = OpenFootballRemoteProvider()
    async def check():
        await provider._dataset(COMPETITIONS['it.1']['current'])
        before = provider.data_status('it.1')
        await provider._dataset(COMPETITIONS['it.1']['current'])
        assert provider.data_status('it.1') == before
        assert before['datasets'][0]['fetched_at'] is not None
        assert before['source_updated_at'] is None
        assert before['is_live'] is False
    asyncio.run(check())
    assert len(requests) == 1


def test_partial_dataset_failure_is_visible(monkeypatch):
    async def get(self, url, **kwargs):
        if 'en.1' in url:
            raise httpx.ConnectError('private upstream detail')
        return httpx.Response(200, json={'matches': []}, request=httpx.Request('GET', url))
    client_class = httpx.AsyncClient
    monkeypatch.setattr(client_class, 'get', get)
    # Network is fully mocked; do not inherit machine-specific proxy settings.
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: client_class(trust_env=False, **kwargs))
    provider = OpenFootballRemoteProvider()
    asyncio.run(provider.competitions())
    assert provider.data_status()['coverage'] == 'PARTIAL'
    assert any(x['status'] == 'UNAVAILABLE' for x in provider.data_status()['datasets'])


def test_calendar_validation_and_upstream_error_do_not_expose_details(monkeypatch):
    class BrokenProvider:
        async def fixtures(self, *args):
            raise RuntimeError('secret-provider-detail')
    monkeypatch.setattr(main, 'get_provider', lambda: BrokenProvider())
    with TestClient(main.app) as client:
        assert client.get('/api/fixtures?date_from=2026-10-21&date_to=2026-10-14').status_code == 400
        response = client.get('/api/fixtures?date_from=2026-10-14&date_to=2026-10-15')
        assert response.status_code == 502
        assert 'secret-provider-detail' not in response.text


def test_unknown_time_has_explicit_date_and_flag():
    item = OpenFootballRemoteProvider._normalize_match({'date':'2026-10-17','team1':'A','team2':'B'}, 'it.1', COMPETITIONS['it.1'], '2026-27')
    assert item['kickoff_time_known'] is False
    assert item['kickoff_date'] == '2026-10-17'
