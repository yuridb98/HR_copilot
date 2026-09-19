import pytest
from pydantic import ValidationError
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
    """Hermetic environment: fake key, no ENVIRONMENT, and never read a developer's real .env."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("CONFIG_DIR", raising=False)
    monkeypatch.setattr("hr_copilot.core.config.load_dotenv", lambda *args, **kwargs: False)


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
    assert settings.environment == "prod"
    assert settings.rag.top_k == 10  # overridden by prod.yaml
    assert settings.rag.chunk_size_tokens == 400  # inherited from base.yaml: deep-merge


def test_openai_api_key_becomes_secret_str():
    settings = get_settings()
    assert settings.llm.api_key.get_secret_value() == "sk-test-key"
    assert "sk-test-key" not in repr(settings.llm.api_key)
    assert "sk-test-key" not in str(settings.llm.api_key)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        get_settings()


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_unknown_environment_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "porod")
    with pytest.raises(FileNotFoundError, match=r"porod\.yaml"):
        get_settings()


def test_missing_base_yaml_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match=r"base\.yaml"):
        get_settings()


def test_config_dir_can_be_overridden(monkeypatch, tmp_path):
    (tmp_path / "base.yaml").write_text(
        "llm:\n  primary_model: a\n  router_model: b\n  judge_model: c\n"
        "rag:\n  top_k: 1\n  chunk_size_tokens: 2\n  chunk_overlap_tokens: 0\n",
        encoding="utf-8",
    )
    (tmp_path / "dev.yaml").write_text("", encoding="utf-8")
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    settings = get_settings()
    assert settings.llm.primary_model == "a"
    assert settings.rag.top_k == 1
