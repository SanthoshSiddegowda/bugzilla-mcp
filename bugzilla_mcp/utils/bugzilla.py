"""Bugzilla API client"""

from typing import Any
import httpx


class Bugzilla:
    """Bugzilla API class"""

    def __init__(self, url: str, api_key: str):
        self.api_url: str = url + "/rest"
        self.base_url: str = url
        self.api_key: str = api_key
        # request params sent for each request
        self.params: dict[str, Any] = {"api_key": self.api_key}
        # Create a shared async client
        self.client: httpx.AsyncClient = httpx.AsyncClient()

    async def bug_info(self, bug_id: int) -> dict[str, Any]:
        """get information about a given bug"""

        r = await self.client.get(url=f"{self.api_url}/bug/{bug_id}", params=self.params)

        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        return r.json()["bugs"][0]

    async def bug_comments(self, bug_id: int) -> dict[str, Any]:
        """Get comments of a bug"""

        r = await self.client.get(url=f"{self.api_url}/bug/{bug_id}/comment", params=self.params)

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

        r = await self.client.post(
            url=f"{self.api_url}/bug/{bug_id}/comment", params=self.params, json=c
        )

        if r.status_code != 201:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        return r.json()

    async def close(self):
        """Close the async client"""
        await self.client.aclose()

