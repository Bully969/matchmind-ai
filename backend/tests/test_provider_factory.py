from app.config import settings
from app.providers.demo import DemoProvider
from app.providers.factory import get_provider, reset_provider_for_tests
from app.providers.openfootball_remote import OpenFootballRemoteProvider


def test_demo_configuration_fails_safe_to_public_provider(monkeypatch):
    reset_provider_for_tests()
    monkeypatch.setattr(settings, "data_provider", "demo")
    monkeypatch.setattr(settings, "allow_synthetic_demo", False)
    try:
        provider = get_provider()
        assert isinstance(provider, OpenFootballRemoteProvider)
        assert provider.is_demo is False
    finally:
        reset_provider_for_tests()


def test_demo_provider_requires_explicit_opt_in(monkeypatch):
    reset_provider_for_tests()
    monkeypatch.setattr(settings, "data_provider", "demo")
    monkeypatch.setattr(settings, "allow_synthetic_demo", True)
    try:
        provider = get_provider()
        assert isinstance(provider, DemoProvider)
        assert provider.is_demo is True
    finally:
        reset_provider_for_tests()
