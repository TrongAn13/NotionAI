"""Premium upgrade transport; resource creation is limited to files and views."""

import mimetypes
import re
from pathlib import Path

import httpx

from app.notion.client import NotionError
from app.notion.upgrades import UpgradeClient


class PremiumClient(UpgradeClient):
    def _result(self, response):
        try:
            value = response.json()
        except ValueError:
            raise NotionError("Invalid response; reconcile journal before retrying.") from None
        if not isinstance(value, dict):
            raise NotionError("Invalid response object; reconcile journal before retrying.")
        if response.status_code != 200:
            message = str(value.get("message", "Request failed"))
            token = self.http.headers.get("Authorization", "").removeprefix("Bearer ")
            if token:
                message = message.replace(token, "[redacted]")
            raise NotionError(f"Notion HTTP {response.status_code}: {message[:700]}")
        return value

    def get(self, path, **params):
        if path == "views" or path.startswith(("views/", "file_uploads/")):
            for attempt in range(6):
                self.sleep(self.interval)
                try:
                    response = self.http.get(path, params=params)
                except httpx.TransportError:
                    if attempt == 5:
                        raise NotionError("Notion read failed after retries.") from None
                    self.sleep(2**attempt)
                    continue
                if (
                    response.status_code in (429, 529) or response.status_code >= 500
                ) and attempt < 5:
                    self.sleep(float(response.headers.get("Retry-After", 2**attempt)))
                    continue
                return self._result(response)
        return super().get(path, **params)

    def mutate(self, method, path, payload):
        allowed = method == "POST" and path in ("views", "file_uploads")
        allowed |= method == "PATCH" and bool(
            re.fullmatch(r"(?:data_sources|pages|views)/[\w-]+|blocks/[\w-]+(?:/children)?", path)
        )
        if not allowed:
            raise ValueError("Premium transport only allows views, uploads and scoped updates.")
        if path.startswith("pages/") and not set(payload) <= {"properties", "icon", "cover"}:
            raise ValueError("Destructive or unsupported page update rejected.")
        if (
            path.startswith("blocks/")
            and not path.endswith("/children")
            and (
                len(payload) != 1
                or not set(payload)
                <= {
                    "paragraph",
                    "heading_1",
                    "heading_2",
                    "heading_3",
                    "to_do",
                    "callout",
                    "toggle",
                }
            )
        ):
            raise ValueError("Only owned block text updates are permitted.")
        if path.startswith("data_sources/") and (
            set(payload) != {"properties"} or any(v is None for v in payload["properties"].values())
        ):
            raise ValueError("Destructive schema update rejected.")
        for attempt in range(6):
            self.sleep(self.interval)
            try:
                response = self.http.request(method, path, json=payload)
            except httpx.TransportError:
                raise NotionError("Write outcome unknown; reconcile the saved journal.") from None
            if response.status_code == 429 and attempt < 5:
                self.sleep(float(response.headers.get("Retry-After", 2**attempt)))
                continue
            return self._result(response)
        raise NotionError("Rate-limit retry budget exhausted.")

    def upload(self, path):
        path = Path(path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        result = self.mutate(
            "POST",
            "file_uploads",
            {"mode": "single_part", "filename": path.name, "content_type": mime},
        )
        upload_id = result["id"]
        self.sleep(self.interval)
        with path.open("rb") as stream:
            try:
                response = self.http.post(
                    f"file_uploads/{upload_id}/send", files={"file": (path.name, stream, mime)}
                )
            except httpx.TransportError:
                raise NotionError("Upload interrupted; no page cover was changed.") from None
        sent = self._result(response)
        if sent.get("status") != "uploaded":
            raise NotionError("File upload is not complete; no page cover was changed.")
        return upload_id

    def list_views(self, database_id):
        cursor = None
        seen = set()
        while True:
            params = {"database_id": database_id, "page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            result = self.get("views", **params)
            yield from result["results"]
            if not result.get("has_more"):
                break
            cursor = result.get("next_cursor")
            if not cursor or cursor in seen:
                raise NotionError("Invalid view pagination.")
            seen.add(cursor)
