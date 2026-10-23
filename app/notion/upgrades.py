"""Explicit endpoint allowlist for queries and non-destructive upgrades."""

import random
import re

import httpx

from app.notion.client import NotionClient, NotionError


class UpgradeClient(NotionClient):
    def send(self, method, path, payload):
        allowed = (
            method == "POST"
            and re.fullmatch(r"data_sources/[\w-]+/query", path)
            or method == "PATCH"
            and re.fullmatch(r"data_sources/[\w-]+", path)
            or method == "PATCH"
            and re.fullmatch(r"blocks/[\w-]+/children", path)
        )
        if not allowed:
            raise NotionError("Endpoint is not allowed by the upgrade client.")
        if (
            method == "PATCH"
            and path.startswith("data_sources/")
            and (
                set(payload) != {"properties"}
                or any(value is None for value in payload["properties"].values())
            )
        ):
            raise NotionError("Only additive schema payloads are allowed.")
        for attempt in range(6):
            self.sleep(self.interval)
            try:
                response = self.http.request(method, path, json=payload)
            except httpx.TransportError:
                if method == "POST" and attempt < 5:
                    self.sleep(2**attempt + random.random())
                    continue
                raise NotionError(
                    "Request interrupted; outcome unknown. Rerun discovery to reconcile before retrying."
                ) from None
            # A rejected 429 is safe to retry. Ambiguous writes and server errors are not.
            retryable = response.status_code == 429 or (
                method == "POST" and response.status_code >= 500
            )
            if retryable and attempt < 5:
                try:
                    delay = max(0, float(response.headers["Retry-After"]))
                except (KeyError, ValueError):
                    delay = 2**attempt + random.random()
                self.sleep(delay)
                continue
            break
        if response.status_code != 200:
            raise NotionError(
                f"Notion HTTP {response.status_code}; operation stopped. "
                "No automatic write retry; rerun to reconcile."
            )
        try:
            value = response.json()
        except ValueError:
            raise NotionError(
                "Invalid write response; outcome unknown. Reconcile before retrying."
            ) from None
        if not isinstance(value, dict):
            raise NotionError("Invalid response object; reconcile before retrying.")
        return value

    def query(self, source_id):
        cursor = None
        seen = set()
        while True:
            payload = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            # Queries are read-only, although Notion specifies POST.
            result = self.send("POST", f"data_sources/{source_id}/query", payload)
            if not isinstance(result.get("results"), list):
                raise NotionError("Invalid data-source query response.")
            yield from result["results"]
            if not result.get("has_more"):
                return
            cursor = result.get("next_cursor")
            if not cursor or cursor in seen:
                raise NotionError("Invalid data-source pagination cursor.")
            seen.add(cursor)
