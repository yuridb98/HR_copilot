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

load_dotenv()

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
        """Retrieve the value for a given field from the YAML configuration."""
        return None, field_name, False  # Placeholder for actual implementation
    
    def __call__(self) -> dict[str, Any]:
        environment = os.environ.get("ENVIRONMENT", "dev")
        config_dir = Path(__file__).resolve().parents[3] / "config"

        base_data = self._load_yaml(config_dir / "base.yaml")
        env_data = self._load_yaml(config_dir / f"{environment}.yaml")
        return self._deep_merge(base_data, env_data)

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
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
        env_file=".env",
        env_file_encoding="utf-8",
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
    return Settings()  # pyright: ignore[reportCallIssue]