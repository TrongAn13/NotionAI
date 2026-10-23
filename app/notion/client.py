"""GET-only transport: mutations are intentionally unavailable in Phase 2."""

import random
import time

import httpx


class NotionError(RuntimeError):
    pass


class NotionClient:
    def __init__(self, settings, *, transport=None, sleep=time.sleep, interval=0.36):
        self.sleep = sleep
        self.interval = interval
        self.http = httpx.Client(
            base_url="https://api.notion.com/v1/",
            timeout=30,
            headers={
                "Authorization": "Bearer " + settings.token.get_secret_value(),
                "Notion-Version": settings.api_version,
            },
            transport=transport,
            follow_redirects=False,
        )

    def close(self):
        self.http.close()

    def get(self, path, **params):
        # Only known relative read endpoints may be requested; never follow redirects.
        if not path.startswith(("pages/", "blocks/", "databases/", "data_sources/")):
            raise NotionError("Unsupported read endpoint")
        for attempt in range(6):
            self.sleep(self.interval)
            try:
                response = self.http.get(path, params=params)
            except httpx.TransportError:
                if attempt == 5:
                    raise NotionError("Notion connection failed after retries.") from None
                self.sleep(2**attempt + random.random())
                continue
            if (response.status_code in (429, 529) or response.status_code >= 500) and attempt < 5:
                try:
                    delay = max(0, float(response.headers["Retry-After"]))
                except (KeyError, ValueError):
                    delay = 2**attempt + random.random()
                self.sleep(delay)
                continue
            if response.status_code != 200:
                # Do not expose server body, request headers or potentially sensitive content.
                raise NotionError(
                    f"Notion HTTP {response.status_code}; check access and resource ID."
                )
            try:
                data = response.json()
            except ValueError:
                raise NotionError("Notion returned invalid JSON.") from None
            if not isinstance(data, dict):
                raise NotionError("Notion returned an invalid object.")
            return data
        raise NotionError("Notion retry budget exhausted.")

    def children(self, block_id):
        cursor = None
        seen = set()
        while True:
            params = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = self.get(f"blocks/{block_id}/children", **params)
            results = data.get("results")
            if not isinstance(results, list):
                raise NotionError("Invalid block list response.")
            yield from results
            if not data.get("has_more"):
                return
            cursor = data.get("next_cursor")
            if not cursor or cursor in seen:
                raise NotionError("Invalid or repeated pagination cursor.")
            seen.add(cursor)
