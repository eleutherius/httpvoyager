import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .models import GraphQLTabSpec, HttpTabSpec, WebSocketTabSpec

APP_DIR_NAME = "http_voyager"
CONFIG_FILE_NAME = "state.json"


def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".config" / APP_DIR_NAME


def _config_path() -> Path:
    return _config_dir() / CONFIG_FILE_NAME


def load_last_state[T: (GraphQLTabSpec, HttpTabSpec, WebSocketTabSpec)](
    default_spec: T, section: str | None = None
) -> T:
    """Load last saved state for a section, merging onto defaults."""
    path = _config_path()
    if not path.exists():
        return default_spec
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_spec
    payload = _select_section(data, section)
    merged = _spec_to_dict(default_spec)
    merged.update({k: v for k, v in payload.items() if k in merged})
    return type(default_spec)(**merged)  # type: ignore[arg-type]


def save_state(spec: Any, section: str | None = None) -> None:
    """Persist last used settings to config file."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _spec_to_dict(spec)
    existing: dict[str, Any] = {}
    if section:
        if path.exists():
            try:
                existing_data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(existing_data, dict):
                    existing = existing_data
            except Exception:
                existing = {}
        existing[section] = payload
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _select_section(data: Any, section: str | None) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    if section and isinstance(data.get(section), dict):
        return data[section]
    if section == "graphql":
        return data  # Backward compatibility with pre-section format.
    return data if section is None else {}


def _spec_to_dict(spec: Any) -> dict[str, Any]:
    if is_dataclass(spec):
        return asdict(spec)
    return {k: v for k, v in spec.__dict__.items() if not k.startswith("_")}
