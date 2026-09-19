import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _config_dir() -> Path:
    """Folder with base.yaml and {ENVIRONMENT}.yaml. Override it with CONFIG_DIR."""
    override = os.environ.get("CONFIG_DIR")
    return Path(override) if override else _PROJECT_ROOT / "config"


class LLMSettings(BaseModel):
    primary_model: str
    router_model: str
    judge_model: str
    api_key: SecretStr


class RAGSettings(BaseModel):
    top_k: int
    chunk_size_tokens: int
    chunk_overlap_tokens: int


class YamlConfigSource(PydanticBaseSettingsSource):
    """Deep-merge YAML configuration source for Pydantic settings."""

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        # Required by the base class but unused: __call__ returns the whole dict at once.
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        environment = os.environ.get("ENVIRONMENT", "dev")
        config_dir = _config_dir()

        base_data = self._load_yaml(config_dir / "base.yaml")
        env_data = self._load_yaml(config_dir / f"{environment}.yaml")
        return self._deep_merge(base_data, env_data)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        # A missing file is a deployment error (typo in ENVIRONMENT, wrong path):
        # failing loudly beats silently running with the wrong configuration.
        if not path.is_file():
            raise FileNotFoundError(f"Missing config file: {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = YamlConfigSource._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: str = "dev"
    llm: LLMSettings
    rag: RAGSettings

    @model_validator(mode="before")
    @classmethod
    def _inject_openai_api_key(cls, data: Any) -> Any:
        """OPENAI_API_KEY is required for LLMSettings. If not provided, attempt to load it from the environment."""
        if not isinstance(data, dict):
            return data
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return data
        llm_data = dict(data.get("llm", {}))
        llm_data.setdefault("api_key", api_key)
        return {**data, "llm": llm_data}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSource(settings_cls),
        )


@lru_cache
def get_settings() -> Settings:
    # Loaded here, not at import time: importing this module must have no side effects.
    # override=False (default): variables already in the process win over .env.
    load_dotenv(_PROJECT_ROOT / ".env")
    return Settings()  # pyright: ignore[reportCallIssue]
