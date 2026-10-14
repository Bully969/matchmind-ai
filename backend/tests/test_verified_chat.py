from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app import main
from app.config import settings


class Source:
    name = 'verified-test-source'
    is_demo = False
    async def fixtures(self, start, end, competition_id=None):
        return [{'id':'verified-id','competition_id':'test','competition_name':'Test League',
                 'home_team':'Verified Home','away_team':'Verified Away','status':'SCHEDULED',
                 'kickoff':datetime(2026,10,17,12,tzinfo=timezone.utc),'kickoff_time_known':False}]


def test_chat_ignores_forged_browser_facts(monkeypatch):
    monkeypatch.setattr(main, 'get_provider', lambda: Source())
    monkeypatch.setattr(settings, 'ai_provider', 'template')
    with TestClient(main.app) as client:
        response = client.post('/api/chat', json={'message':'Qual è il contesto?',
          'fixture':{'id':'verified-id','competition_id':'test','kickoff':'2026-10-17','home_team':'FORGED TEAM','home_score':99},
          'analysis':{'probabilities':{'home':1},'note':'FORGED ANALYSIS'}})
    assert response.status_code == 200
    data = response.json()
    assert 'Verified Home' in data['answer']
    assert 'FORGED' not in data['answer']
    assert '99' not in data['answer']
    assert 'Orario da confermare' in data['answer']
    assert data['context']['source'] == 'verified-test-source'


def test_unresolvable_match_does_not_call_model(monkeypatch):
    monkeypatch.setattr(main, 'get_provider', lambda: Source())
    async def forbidden(*args):
        raise AssertionError('model must not be called')
    monkeypatch.setattr(main, 'explain', forbidden)
    with TestClient(main.app) as client:
        response = client.post('/api/chat', json={'message':'Contesto?', 'fixture_id':'fake', 'competition_id':'test','fixture_date':'2026-10-17'})
        assert response.status_code == 404
        response = client.post('/api/chat', json={'message':'Contesto?'})
        assert response.status_code == 422


def test_gemini_configuration_returns_explicit_template_fallback(monkeypatch):
    monkeypatch.setattr(main, 'get_provider', lambda: Source())
    monkeypatch.setattr(settings, 'ai_provider', 'gemini')
    with TestClient(main.app) as client:
        result = client.post('/api/chat', json={'message':'Contesto?', 'fixture_id':'verified-id','competition_id':'test','fixture_date':'2026-10-17'}).json()
    assert result['provider'] == 'template'
    assert result['fallback'] is True
    assert result['fallback_reason'] == 'UNSUPPORTED_PROVIDER'


def test_model_timeout_returns_identified_fallback(monkeypatch):
    import asyncio
    import httpx
    from app.services.llm import explain
    class TimedOutClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(settings, 'ai_provider', 'ollama')
    monkeypatch.setattr(httpx, 'AsyncClient', TimedOutClient)
    result = asyncio.run(explain('Contesto?', {'home_team':'A','away_team':'B','source':'test'}, None))
    assert result['provider'] == 'template'
    assert result['fallback_reason'] == 'TIMEOUT'
    assert result['fallback'] is True
