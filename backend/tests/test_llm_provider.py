import asyncio
import json
import httpx
import pytest
from app.config import settings
from app.services.llm import explain


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(settings, 'ai_provider', 'openai_compatible')
    monkeypatch.setattr(settings, 'openai_compatible_base_url', 'https://api.openai.com/v1')
    monkeypatch.setattr(settings, 'openai_compatible_model', 'gpt-6-luna')
    monkeypatch.setattr(settings, 'openai_compatible_api_key', 'test-secret')


def ask():
    return asyncio.run(explain('Qual è la fonte?', {'home_team':'A','away_team':'B','source':'verified'}, None))


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))


def test_success_uses_verified_context_and_supported_payload(provider, monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        assert body['model'] == 'gpt-6-luna'
        assert body['reasoning_effort'] == 'none'
        assert body['max_completion_tokens'] == 1200
        assert 'temperature' not in body
        assert json.loads(body['messages'][1]['content'])['fixture']['source'] == 'verified'
        return httpx.Response(200, json={'choices':[{'message':{'content':'Fonte: verified.'}}]})
    transport(monkeypatch, handler)
    assert ask() == {'answer':'Fonte: verified.','provider':'openai_compatible','fallback':False}


@pytest.mark.parametrize('code,reason', [(400,'INVALID_REQUEST'),(401,'AUTHENTICATION_FAILED'),(403,'ACCESS_DENIED'),(404,'MODEL_NOT_FOUND'),(429,'RATE_LIMITED'),(503,'MODEL_UNAVAILABLE')])
def test_provider_errors_are_safe_and_distinguishable(provider, monkeypatch, code, reason):
    transport(monkeypatch, lambda request: httpx.Response(code, text='test-secret private account details'))
    result = ask()
    assert result['fallback_reason'] == reason
    assert result['fallback'] is True
    assert 'test-secret' not in json.dumps(result)
    assert 'private account' not in json.dumps(result)


@pytest.mark.parametrize('body', [{'choices':[]},{'choices':[{'message':{'content':None}}]},{'choices':[{'message':{'content':'  '}}]}])
def test_empty_completion_is_identified(provider, monkeypatch, body):
    transport(monkeypatch, lambda request: httpx.Response(200, json=body))
    assert ask()['fallback_reason'] == 'EMPTY_RESPONSE'


@pytest.mark.parametrize('base,key,reason', [('https://generativelanguage.googleapis.com/v1beta/openai/','test-secret','MODEL_PROVIDER_MISMATCH'),('https://api.openai.com/v1','','MISSING_CONFIGURATION')])
def test_invalid_configuration_does_not_call_provider(provider, monkeypatch, base, key, reason):
    monkeypatch.setattr(settings, 'openai_compatible_base_url', base)
    monkeypatch.setattr(settings, 'openai_compatible_api_key', key)
    def forbidden(request):
        pytest.fail('Invalid configuration must not call the provider')
    transport(monkeypatch, forbidden)
    assert ask()['fallback_reason'] == reason


@pytest.mark.parametrize('error,reason', [
    ({'code':'credit_balance_exhausted','type':'insufficient_quota'}, 'CREDIT_EXHAUSTED'),
    ({'code':'insufficient_quota'}, 'QUOTA_EXHAUSTED'),
    ({'type':'insufficient_quota'}, 'QUOTA_EXHAUSTED'),
    ({'code':'rate_limit_exceeded'}, 'RATE_LIMITED'),
    ({'code': ['unexpected']}, 'RATE_LIMITED'),
    ('malformed', 'RATE_LIMITED'),
])
def test_quota_diagnostics_without_sensitive_provider_message(provider, monkeypatch, error, reason):
    if isinstance(error, dict):
        error['message'] = 'test-secret private billing details'
    transport(monkeypatch, lambda request: httpx.Response(429, json={'error': error}))
    result = ask()
    assert result['fallback_reason'] == reason
    assert 'test-secret' not in json.dumps(result)
    assert 'private billing' not in json.dumps(result)
