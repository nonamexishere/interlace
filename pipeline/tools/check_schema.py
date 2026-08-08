#!/usr/bin/env python3
"""Validate JSON against a pipeline contract (stdlib; required + additionalProperties)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"invalid JSON {path}: {e}", file=sys.stderr)
        sys.exit(1)


def check_object(schema: dict, data, path: str = "$") -> list[str]:
    errs: list[str] = []
    t = schema.get("type")
    if t == "object":
        if not isinstance(data, dict):
            return [f"{path}: expected object"]
        req = schema.get("required", [])
        for k in req:
            if k not in data:
                errs.append(f"{path}: missing required {k}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in data:
                if k not in props:
                    errs.append(f"{path}: unexpected property {k}")
        for k, sub in props.items():
            if k in data:
                errs.extend(check_object(sub, data[k], f"{path}.{k}"))
    elif t == "array":
        if not isinstance(data, list):
            return [f"{path}: expected array"]
        if "minItems" in schema and len(data) < schema["minItems"]:
            errs.append(f"{path}: minItems {schema['minItems']}")
        item_s = schema.get("items")
        if isinstance(item_s, dict):
            for i, item in enumerate(data):
                errs.extend(check_object(item_s, item, f"{path}[{i}]"))
    elif t == "string":
        if not isinstance(data, str):
            errs.append(f"{path}: expected string")
        elif "const" in schema and data != schema["const"]:
            errs.append(f"{path}: want const {schema['const']!r}")
        elif "pattern" in schema:
            import re

            if re.fullmatch(schema["pattern"], data) is None:
                errs.append(f"{path}: pattern {schema['pattern']}")
    elif t == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            errs.append(f"{path}: expected integer")
    elif t == "boolean":
        if not isinstance(data, bool):
            errs.append(f"{path}: expected boolean")
    elif t == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errs.append(f"{path}: expected number")
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: not in enum {schema['enum']}")
    if "$ref" in schema:
        # only support local $defs one level for spike schema
        pass
    return errs


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: check_schema.py SCHEMA.json DATA.json", file=sys.stderr)
        sys.exit(2)
    schema = load(Path(sys.argv[1]))
    data = load(Path(sys.argv[2]))
    # expand $defs for spike reports
    defs = schema.get("$defs", {})
    if defs and schema.get("properties", {}).get("spikes"):
        spike = defs.get("spike", {"type": "object", "required": ["pass", "caveats"]})
        for k in ("1", "2", "3", "4"):
            schema.setdefault("properties", {}).setdefault("spikes", {}).setdefault(
                "properties", {}
            )[k] = {
                "type": "object",
                "required": spike.get("required", ["pass", "caveats"]),
                "additionalProperties": False,
                "properties": {
                    "pass": {"type": "boolean"},
                    "caveats": {"type": "array", "items": {"type": "string"}},
                },
            }
        schema["properties"]["spikes"]["type"] = "object"
        schema["properties"]["spikes"]["required"] = ["1", "2", "3", "4"]
        schema["properties"]["spikes"]["additionalProperties"] = False
        schema["properties"]["blocked"] = {"type": "boolean"}
    errs = check_object(schema, data)
    if errs:
        print("schema invalid:", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    print("schema ok")


if __name__ == "__main__":
    main()
