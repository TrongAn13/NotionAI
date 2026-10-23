from uuid import UUID

import httpx
import pytest

from app.config import Settings
from app.notion.client import NotionError
from app.notion.upgrades import UpgradeClient


def make_client(handler, sleeps=None):
    return UpgradeClient(
        Settings(token="test-only", parent_page_id=UUID("401de7f296f680c99145c4077252d990")),
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append if sleeps is not None else lambda _: None,
    )


def test_query_pagination_and_retry_after():
    calls = []
    sleeps = []

    def handler(req):
        import json

        calls.append(req)
        if len(calls) == 1:
            return httpx.Response(429, json={}, headers={"Retry-After": "4"})
        payload = json.loads(req.content)
        if "start_cursor" not in payload:
            return httpx.Response(
                200, json={"results": [{"id": "one"}], "has_more": True, "next_cursor": "cursor"}
            )
        assert payload["start_cursor"] == "cursor"
        return httpx.Response(200, json={"results": [{"id": "two"}], "has_more": False})

    c = make_client(handler, sleeps)
    assert [r["id"] for r in c.query("source")] == ["one", "two"]
    assert 4 in sleeps
    assert all(req.method == "POST" and req.url.path.endswith("/query") for req in calls)
    c.close()


def test_ambiguous_append_never_retried():
    calls = []

    def handler(req):
        calls.append(req)
        raise httpx.ReadTimeout("private response detail", request=req)

    c = make_client(handler)
    with pytest.raises(NotionError, match="unknown"):
        c.send("PATCH", "blocks/page/children", {"children": []})
    assert len(calls) == 1
    c.close()


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("POST", "pages", {}),
        ("DELETE", "blocks/id", {}),
        ("PATCH", "data_sources/id", {"properties": {"Existing": None}}),
        ("PATCH", "pages/id", {"properties": {}}),
    ],
)
def test_unsupported_or_destructive_endpoints_rejected(method, path, payload):
    c = make_client(lambda _: pytest.fail("Must reject before any HTTP request"))
    with pytest.raises(NotionError):
        c.send(method, path, payload)
    c.close()
