import pytest

from hr_copilot.core.config import get_settings

pytestmark = pytest.mark.unit

@pytest.fixture(autouse=True)
def _isolated_settings_cache():
    """Clear the settings cache before each test to ensure isolation."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    
@pytest.fixture(autouse=True)
def _base_env(monkeypatch):
    """Set a default environment variable for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    
    
def test_default_from_base_yaml(monkeypatch):
    """Test that the default settings are loaded from base.yaml when no ENVIRONMENT is set."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    settings = get_settings()
    assert settings.llm.primary_model == "gpt-5.6-luna"
    assert settings.rag.top_k == 5
    
    
def test_env_var_overrides_yaml(monkeypatch):
    monkeypatch.setenv("RAG__TOP_K", "3")
    settings = get_settings()
    assert settings.rag.top_k == 3


def test_environment_selects_prod_yaml(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    settings = get_settings()
    assert settings.rag.top_k == 10
    assert settings.llm.primary_model == "gpt-5.6-luna"


def test_openai_api_key_becomes_secret_str():
    settings = get_settings()
    assert settings.llm.api_key.get_secret_value() == "sk-test-key"
    assert "sk-test-key" not in repr(settings.llm.api_key)
    assert "sk-test-key" not in str(settings.llm.api_key)


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
    
    