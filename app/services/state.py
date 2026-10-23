"""Durable local state and ownership verification."""

import hashlib
import json
import os
from pathlib import Path


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def load_manifest(path=Path("state/manifest.json")):
    if not path.exists():
        return {"version": 1, "dashboards": {}, "operations": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != 1 or not isinstance(value.get("dashboards"), dict):
        raise ValueError("Unsupported or invalid manifest; preserve it and resolve manually.")
    return value


def text_signature(rich_text):
    return [
        {
            "content": part.get("text", {}).get("content", part.get("plain_text", "")),
            "link": (part.get("text", {}).get("link") or {}).get("url"),
            "annotations": {
                k: v for k, v in part.get("annotations", {}).items() if v not in (False, "default")
            },
        }
        for part in rich_text
    ]


def signature(block):
    kind = block["type"]
    body = block.get(kind, {})
    result = {"type": kind}
    if "rich_text" in body:
        result["rich_text"] = text_signature(body["rich_text"])
    if kind == "callout":
        result["icon"] = body.get("icon")
    if body.get("color", "default") != "default":
        result["color"] = body["color"]
    if "children" in body:
        result["children"] = [signature(child) for child in body["children"]]
    return result


def read_tree(client, block):
    value = dict(block)
    kind = block["type"]
    value[kind] = dict(block.get(kind, {}))
    if block.get("has_children"):
        value[kind]["children"] = [
            read_tree(client, child) for child in client.children(block["id"])
        ]
    return value
