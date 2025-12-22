import json
from typing import Dict

from .models import GraphQLResponse


def parse_json_object(raw: str) -> Dict:
    raw = raw.strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")
    return parsed


def parse_headers(raw: str) -> Dict[str, str]:
    raw = raw.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Headers JSON must be an object.")
        return {str(k): str(v) for k, v in parsed.items()}
    except json.JSONDecodeError:
        return parse_header_lines(raw)


def parse_header_lines(raw: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"Invalid header line: {line!r}")
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def format_response(response: GraphQLResponse) -> str:
    try:
        parsed = json.loads(response.text)
        body = json.dumps(parsed, indent=2)
    except Exception:
        body = response.text
    return (
        f"Status: {response.status}\n"
        f"Time: {response.duration_ms:.1f} ms\n"
        f"Body:\n{body}"
    )
