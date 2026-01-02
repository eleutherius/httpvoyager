# ruff: noqa: S101
import pytest

from voyager.models import GraphQLResponse
from voyager.parsing import format_response, parse_headers, parse_json_object


def test_parse_json_object_valid():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_non_object():
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_json_object('["a", "b"]')


def test_parse_headers_json_object():
    result = parse_headers('{"Authorization": "token", "X": 1}')
    assert result == {"Authorization": "token", "X": "1"}


def test_parse_headers_key_value_lines():
    result = parse_headers("A: 1\nB: two")
    assert result == {"A": "1", "B": "two"}


def test_parse_headers_invalid_line():
    with pytest.raises(ValueError, match="Invalid header line"):
        parse_headers("NoColonHere")


def test_format_response_json_body():
    resp = GraphQLResponse(status=200, text='{"ok":true}', duration_ms=12.3)
    formatted = format_response(resp)
    assert "Status: 200" in formatted
    assert '"ok": true' in formatted


def test_format_response_plain_text():
    resp = GraphQLResponse(status=500, text="boom", duration_ms=1.0)
    formatted = format_response(resp)
    assert "boom" in formatted
