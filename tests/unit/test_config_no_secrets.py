import re
from pathlib import Path
from typing import Any

import pytest
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
FORBIDDEN_KEY_PATTERN = re.compile(r"(password|secret|api_key|private_key|token)$", re.IGNORECASE)
FORBIDDEN_VALUE_PREFIXES = ("sk-", "ghp_", "xox", "AKIA")


def _offenders(data: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            key_path = f"{path}.{key}" if path else str(key)
            if FORBIDDEN_KEY_PATTERN.search(str(key)):
                found.append(key_path)
            found.extend(_offenders(value, key_path))
    elif isinstance(data, str) and data.startswith(FORBIDDEN_VALUE_PREFIXES):
        found.append(path)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            found.extend(_offenders(item, f"{path}[{index}]"))

    return found


@pytest.mark.unit
@pytest.mark.parametrize("yaml_path", sorted(CONFIG_DIR.glob("**/*.yaml")), ids=lambda p: p.name)
def test_no_secrets_in_yaml(yaml_path: Path) -> None:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    offenders = _offenders(data)
    assert not offenders, f"Chiavi/valori sospetti in {yaml_path.name}: {offenders}"


@pytest.mark.unit
def test_offenders_detects_secrets_inside_lists() -> None:
    assert _offenders({"tools": ["sk-abc123"]}) == ["tools[0]"]
    assert _offenders({"items": [{"password": "x"}]}) == ["items[0].password"]
