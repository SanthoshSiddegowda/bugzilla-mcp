"""Bugzilla API client"""

import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)

API_KEY_HEADER = "X-BUGZILLA-API-KEY"

# Bugzilla base URL -> whether that instance reads the API key header.
# Keyed by URL only (no secrets). Re-probed after a process restart.
_header_auth_support: dict[str, bool] = {}


class Bugzilla:
    """Bugzilla API class"""

    def __init__(self, url: str, api_key: str):
        url = url.rstrip("/")
        self.api_url: str = url + "/rest"
        self.base_url: str = url
        self.api_key: str = api_key
        self.client: httpx.AsyncClient = httpx.AsyncClient()

    async def supports_header_auth(self) -> bool:
        """Check once per Bugzilla URL whether it reads the API key header.

        Stock Bugzilla 5.0/5.2 ignore the header and only accept `?api_key=`;
        bugzilla.mozilla.org and Bugzilla master read it. The probe sends a
        deliberately invalid key in the header only: an instance that reads it
        answers error 306 (invalid API key), one that ignores it doesn't.
        """
        if self.base_url not in _header_auth_support:
            try:
                r = await self.client.get(
                    f"{self.api_url}/bug/1",
                    params={"include_fields": "id"},
                    headers={API_KEY_HEADER: "invalid-probe-key"},
                )
                supported = r.json().get("code") == 306
            except (httpx.HTTPError, ValueError):
                # Transient failure: use the query string this time, probe again next time
                return False

            _header_auth_support[self.base_url] = supported
            if not supported:
                logger.warning(
                    "Bugzilla at %s does not accept the %s header; sending the API key "
                    "in the query string instead. This fallback is deprecated: query "
                    "strings can end up in access logs. Upgrade to a Bugzilla version "
                    "that supports the header.",
                    self.base_url,
                    API_KEY_HEADER,
                )

        return _header_auth_support[self.base_url]

    async def auth(self) -> tuple[dict[str, str], dict[str, str]]:
        """Return (headers, params) that authenticate a request.

        Prefer the header so the key stays out of URLs and access logs; fall
        back to the query string (deprecated) for instances that ignore it.
        """
        if await self.supports_header_auth():
            return {API_KEY_HEADER: self.api_key}, {}
        return {}, {"api_key": self.api_key}

    async def bug_info(self, bug_id: int) -> dict[str, Any]:
        """get information about a given bug"""

        headers, params = await self.auth()
        r = await self.client.get(url=f"{self.api_url}/bug/{bug_id}", headers=headers, params=params)

        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        return r.json()["bugs"][0]

    async def bug_comments(self, bug_id: int) -> dict[str, Any]:
        """Get comments of a bug"""

        headers, params = await self.auth()
        r = await self.client.get(url=f"{self.api_url}/bug/{bug_id}/comment", headers=headers, params=params)

        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        return r.json()["bugs"][f"{bug_id}"]["comments"]

    async def add_comment(
        self, bug_id: int, comment: str, is_private: bool
    ) -> dict[str, int]:
        """Add a comment to bug, which can optionally be private"""

        c = {"comment": comment, "is_private": is_private}

        headers, params = await self.auth()
        r = await self.client.post(
            url=f"{self.api_url}/bug/{bug_id}/comment", headers=headers, params=params, json=c
        )

        if r.status_code != 201:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        return r.json()

    async def close(self):
        """Close the async client"""
        await self.client.aclose()

