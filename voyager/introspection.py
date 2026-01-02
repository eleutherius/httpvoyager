from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from .models import GraphQLResponse


@dataclass
class FieldInfo:
    name: str
    type_repr: str
    description: str = ""
    args_str: str = ""


@dataclass
class TypeInfo:
    name: str
    kind: str
    description: str = ""
    fields: list[FieldInfo] = field(default_factory=list)


@dataclass
class IntrospectionResult:
    success: bool
    status: str
    details: str
    types: list[TypeInfo] = field(default_factory=list)


def build_introspection_result(response: GraphQLResponse) -> IntrospectionResult:
    """Parse introspection HTTP response into a structured result."""
    try:
        data = json.loads(response.text)
    except Exception as exc:
        return IntrospectionResult(False, f"Could not parse JSON: {exc}", response.text, [])

    if response.status != 200:
        return IntrospectionResult(False, f"HTTP {response.status}", response.text, [])

    errors = data.get("errors")
    if errors:
        return IntrospectionResult(False, "GraphQL errors", json.dumps(errors, indent=2), [])

    types_raw = data.get("data", {}).get("__schema", {}).get("types")
    if not types_raw:
        return IntrospectionResult(False, "No types returned from schema.", response.text, [])

    types = _collect_types(types_raw)
    if not types:
        return IntrospectionResult(False, "Schema loaded but no object/interface/input types.", response.text, [])

    type_names = [t.name for t in types]
    summary = f"Schema loaded: {len(types)} types."
    details = summary + "\n\n" + "\n".join(type_names[:50])
    return IntrospectionResult(True, summary, details, types)


def add_types_to_tree(tree: Any, types: Iterable[TypeInfo]) -> int:
    """Populate a textual-like Tree with introspection types."""
    added = 0
    root = getattr(tree, "root", None)
    if root is None:
        return 0

    for type_info in types:
        type_node = root.add(f"{type_info.name} ({type_info.kind.lower()})", data={"description": type_info.description})
        for field in type_info.fields:
            field_data = {"description": field.description, "type": field.type_repr, "args_str": field.args_str}
            type_node.add(f"{field.name}: {field.type_repr}", data=field_data)
        added += 1
    return added


def _collect_types(types_raw: Iterable[dict[str, Any]]) -> list[TypeInfo]:
    types: list[TypeInfo] = []
    for t in types_raw:
        name = t.get("name")
        kind = t.get("kind")
        if not name or name.startswith("__"):
            continue
        if kind not in {"OBJECT", "INTERFACE", "INPUT_OBJECT"}:
            continue
        fields_raw = t.get("fields") or []
        fields = _collect_fields(fields_raw)
        types.append(TypeInfo(name=name, kind=kind, description=t.get("description") or "", fields=fields))
    return types


def _collect_fields(fields_raw: Iterable[dict[str, Any]]) -> list[FieldInfo]:
    fields: list[FieldInfo] = []
    for field in fields_raw:
        name = field.get("name")
        if not name:
            continue
        type_repr = _type_repr(field.get("type"))
        description = field.get("description") or ""
        args_raw = field.get("args") or []
        args_str = ", ".join(_format_arg(arg) for arg in args_raw if arg.get("name"))
        fields.append(FieldInfo(name=name, type_repr=type_repr, description=description, args_str=args_str))
    return fields


def _format_arg(arg: dict[str, Any]) -> str:
    return f"{arg.get('name')}: {_type_repr(arg.get('type'))}"


def _type_repr(node: dict[str, Any] | None) -> str:
    if not node:
        return "Unknown"
    name = node.get("name")
    kind = node.get("kind")
    of_type = node.get("ofType")
    if of_type:
        inner = _type_repr(of_type)
        if kind == "NON_NULL":
            return f"{inner}!"
        if kind == "LIST":
            return f"[{inner}]"
        return inner
    return name or kind or "Unknown"

