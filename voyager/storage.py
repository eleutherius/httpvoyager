import json
import os
from pathlib import Path
from typing import Any

from .models import GraphQLTabSpec

APP_DIR_NAME = "http_voyager"
CONFIG_FILE_NAME = "state.json"


def _config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / ".config" / APP_DIR_NAME


def _config_path() -> Path:
    return _config_dir() / CONFIG_FILE_NAME


def load_last_state(default_spec: GraphQLTabSpec) -> GraphQLTabSpec:
    """Load last saved state, merging onto defaults."""
    path = _config_path()
    if not path.exists():
        return default_spec
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default_spec
    merged: dict[str, Any] = {
        "id": default_spec.id,
        "title": default_spec.title,
        "endpoint": default_spec.endpoint,
        "query": default_spec.query,
        "variables": default_spec.variables,
        "headers": default_spec.headers,
        "verify_tls": default_spec.verify_tls,
    }
    merged.update({k: v for k, v in data.items() if k in merged})
    return GraphQLTabSpec(**merged)  # type: ignore[arg-type]


def save_state(spec: GraphQLTabSpec) -> None:
    """Persist last used query/settings to config file."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": spec.id,
        "title": spec.title,
        "endpoint": spec.endpoint,
        "query": spec.query,
        "variables": spec.variables,
        "headers": spec.headers,
        "verify_tls": spec.verify_tls,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
