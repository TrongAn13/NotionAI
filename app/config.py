"""Configuration; secrets never appear in model representations."""

import os
from uuid import UUID

from dotenv import load_dotenv
from pydantic import BaseModel, SecretStr


class Settings(BaseModel):
    token: SecretStr
    parent_page_id: UUID
    api_version: str = "2026-03-11"

    @classmethod
    def load(cls):
        load_dotenv(dotenv_path=".env", override=False, encoding="utf-8-sig")
        token = os.environ.get("NOTION_API_TOKEN", "").strip()
        parent = os.environ.get("NOTION_PARENT_PAGE_ID", "").strip()
        if not token:
            raise ValueError("Set NOTION_API_TOKEN in your local .env or environment.")
        try:
            page_id = UUID(parent)
        except ValueError:
            raise ValueError("NOTION_PARENT_PAGE_ID must be a valid Notion page UUID.") from None
        return cls(token=SecretStr(token), parent_page_id=page_id)
