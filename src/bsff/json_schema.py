# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Derive JSON Schema (draft 2020-12) from the BSFF dataclass contracts.

ClaimSpec and VerdictJSON are frozen dataclasses, not Pydantic models, so there
is no built-in schema export. Downstream reviewers, regulators, and a JOSS
submission need a machine-readable contract that cannot silently drift from the
code. This module generates the schema *from the dataclass fields and their
type hints* — Literal types become enums, ``X | None`` becomes nullable, fields
without defaults become ``required`` — so the schema is always in lock-step with
the dataclass rather than hand-maintained alongside it.
"""

from __future__ import annotations

import dataclasses
import types
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from .schemas import ClaimSpec, VerdictJSON

JSONSchema = dict[str, Any]
_PRIMITIVE: dict[type, str] = {str: "string", bool: "boolean", int: "integer", float: "number"}
_BASE = "https://neuron7xlab.github.io/bsff/schemas"


def _schema_for_type(tp: Any) -> JSONSchema:
    origin = get_origin(tp)
    if origin is Literal:
        values = list(get_args(tp))
        node: JSONSchema = {"enum": values}
        if {type(v) for v in values} <= {str}:
            node["type"] = "string"
        return node
    if origin is Union or origin is types.UnionType:
        args = get_args(tp)
        nullable = type(None) in args
        non_null = [a for a in args if a is not type(None)]
        sub = (
            _schema_for_type(non_null[0])
            if len(non_null) == 1
            else {"anyOf": [_schema_for_type(a) for a in non_null]}
        )
        if nullable and isinstance(sub.get("type"), str):
            sub = {**sub, "type": [sub["type"], "null"]}
        elif nullable:
            sub = {"anyOf": [sub, {"type": "null"}]}
        return sub
    if origin in (dict,):
        return {"type": "object"}
    if origin in (list, tuple):
        return {"type": "array"}
    if tp in _PRIMITIVE:
        return {"type": _PRIMITIVE[tp]}
    return {}  # Any / object: unconstrained


def dataclass_json_schema(cls: type, *, title: str, schema_id: str | None = None) -> JSONSchema:
    """Generate a JSON Schema object for a (frozen) dataclass."""
    hints = get_type_hints(cls)
    properties: JSONSchema = {}
    required: list[str] = []
    for f in dataclasses.fields(cls):
        properties[f.name] = _schema_for_type(hints[f.name])
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING:
            required.append(f.name)
    schema: JSONSchema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
    if schema_id is not None:
        schema["$id"] = schema_id
    return schema


def claim_spec_schema() -> JSONSchema:
    return dataclass_json_schema(
        ClaimSpec, title="BSFF ClaimSpec", schema_id=f"{_BASE}/claim_spec.schema.json"
    )


def verdict_json_schema() -> JSONSchema:
    return dataclass_json_schema(
        VerdictJSON, title="BSFF VerdictJSON", schema_id=f"{_BASE}/verdict.schema.json"
    )
