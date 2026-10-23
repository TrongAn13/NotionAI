"""Template definitions use only additive properties and compatible formulas."""

from dataclasses import dataclass, field


@dataclass
class Formula:
    name: str
    expression: str
    requires: dict[str, str]
    percent: bool = False


@dataclass
class Template:
    title: str
    icon: str
    tagline: str
    features: list[str]
    workflow: list[str]
    manual: list[str]
    properties: dict = field(default_factory=dict)
    formulas: dict = field(default_factory=dict)
    prompts: list[str] = field(default_factory=list)


def number():
    return {"number": {"format": "number"}}


def text():
    return {"rich_text": {}}


def select(*options):
    return {"select": {"options": [{"name": name} for name in options]}}
