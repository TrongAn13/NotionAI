"""Conservative migration: only unique exact matches and empty new fields."""

import re
from collections import defaultdict
from datetime import date


def text_value(prop):
    kind = prop.get("type")
    if kind in ("title", "rich_text"):
        return "".join(
            t.get("plain_text", t.get("text", {}).get("content", "")) for t in prop.get(kind, [])
        )
    if kind in ("select", "status"):
        return (prop.get(kind) or {}).get("name", "")
    return ""


def name_of(page):
    return next(
        (text_value(p) for p in page.get("properties", {}).values() if p.get("type") == "title"), ""
    )


def normalized(text):
    return " ".join(text.casefold().split())


def unique_index(records):
    index = defaultdict(list)
    for record in records:
        index[normalized(name_of(record))].append(record["id"])
    return index


def matching_id(index, label):
    values = index.get(normalized(label), [])
    return values[0] if len(values) == 1 and label.strip() else None


def relation_updates(records, targets, relation_name, legacy_name):
    index = unique_index(targets)
    result = {}
    skipped = 0
    for record in records:
        label = text_value(record.get("properties", {}).get(legacy_name, {}))
        target_id = matching_id(index, label)
        if target_id:
            result[record["id"]] = {relation_name: {"relation": [{"id": target_id}]}}
        elif label:
            skipped += 1
    return result, skipped


def budget_updates(transactions, budgets):
    index = defaultdict(list)
    for budget in budgets:
        props = budget.get("properties", {})
        month = name_of(budget).strip()
        if re.fullmatch(r"\d{4}-\d{2}", month):
            category = text_value(props.get("Category", {}))
            index[(month, normalized(category))].append(budget["id"])
    updates = {}
    for record in transactions:
        props = record.get("properties", {})
        start = (props.get("Date", {}).get("date") or {}).get("start", "")
        category = text_value(props.get("Category", {}))
        targets = index.get((start[:7], normalized(category)), [])
        if len(targets) == 1:
            updates[record["id"]] = {"Budget Link": {"relation": [{"id": targets[0]}]}}
    for record in budgets:
        month = name_of(record).strip()
        if re.fullmatch(r"\d{4}-\d{2}", month):
            try:
                start = date.fromisoformat(month + "-01").isoformat()
            except ValueError:
                continue
            updates[record["id"]] = {"Month Start": {"date": {"start": start}}}
    return updates


def only_empty(current, desired):
    result = {}
    for name, value in desired.items():
        old = current.get("properties", {}).get(name)
        if old is None:
            raise ValueError(f"Target field has not been created: {name}")
        kind = next(iter(value))
        if old.get("type") != kind:
            raise ValueError(f"Cannot migrate incompatible field: {name}")
        present = old.get(kind)
        if present in (None, [], ""):
            result[name] = value
        elif present != value[kind]:
            # A customer may already have linked the correct resource differently. Preserve it.
            continue
    return result
