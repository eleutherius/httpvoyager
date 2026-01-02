# ruff: noqa: S101
import json

from voyager.introspection import add_types_to_tree, build_introspection_result
from voyager.models import GraphQLResponse


class _Node:
    def __init__(self, label: str) -> None:
        self.label = label
        self.children: list[_Node] = []
        self.data = None

    def add(self, label: str, data=None):
        child = _Node(label)
        child.data = data
        self.children.append(child)
        return child

    def expand(self):
        return None


class _Tree:
    def __init__(self) -> None:
        self.root = _Node("root")


def test_build_introspection_result_success():
    payload = {
        "data": {
            "__schema": {
                "types": [
                    {
                        "name": "Query",
                        "kind": "OBJECT",
                        "description": "Root",
                        "fields": [
                            {
                                "name": "hello",
                                "description": "says hi",
                                "type": {"name": "String", "kind": "SCALAR"},
                                "args": [{"name": "name", "type": {"name": "String", "kind": "SCALAR"}}],
                            }
                        ],
                    }
                ]
            }
        }
    }
    resp = GraphQLResponse(status=200, text=json.dumps(payload), duration_ms=1.0)
    result = build_introspection_result(resp)
    assert result.success is True
    assert result.types[0].name == "Query"
    assert result.types[0].fields[0].args_str == "name: String"
    assert "Schema loaded: 1 types." in result.details


def test_build_introspection_result_errors_field():
    payload = {"errors": [{"message": "boom"}]}
    resp = GraphQLResponse(status=200, text=json.dumps(payload), duration_ms=1.0)
    result = build_introspection_result(resp)
    assert result.success is False
    assert "GraphQL errors" in result.status


def test_build_introspection_result_missing_types():
    payload = {"data": {"__schema": {"types": []}}}
    resp = GraphQLResponse(status=200, text=json.dumps(payload), duration_ms=1.0)
    result = build_introspection_result(resp)
    assert result.success is False
    assert "No types returned" in result.status or "Schema loaded but no object" in result.status


def test_build_introspection_result_bad_json():
    resp = GraphQLResponse(status=200, text="{not json", duration_ms=1.0)
    result = build_introspection_result(resp)
    assert result.success is False
    assert "Could not parse JSON" in result.status


def test_build_introspection_result_http_error():
    resp = GraphQLResponse(status=500, text="fail", duration_ms=1.0)
    result = build_introspection_result(resp)
    assert result.success is False
    assert "HTTP 500" in result.status


def test_add_types_to_tree():
    payload = {
        "data": {
            "__schema": {
                "types": [
                    {"name": "Query", "kind": "OBJECT", "fields": [{"name": "hello", "type": {"name": "String"}}]},
                    {"name": "Ignored", "kind": "SCALAR"},
                ]
            }
        }
    }
    resp = GraphQLResponse(status=200, text=json.dumps(payload), duration_ms=1.0)
    result = build_introspection_result(resp)
    tree = _Tree()
    added = add_types_to_tree(tree, result.types)
    assert added == 1
    assert tree.root.children[0].label.startswith("Query")
    assert tree.root.children[0].children[0].data["type"] == "String"
