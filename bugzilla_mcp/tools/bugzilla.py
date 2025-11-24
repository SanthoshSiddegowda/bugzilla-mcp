"""Bugzilla tools for MCP server"""

import httpx
from typing import Any
from fastmcp.exceptions import ToolError, PromptError
import bugzilla_mcp.utils as utils


async def bug_info(id: int) -> dict[str, Any]:
    """Returns the entire information about a given bugzilla bug id"""

    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")

    try:
        return await utils.bz.bug_info(id)

    except Exception as e:
        raise ToolError(f"Failed to fetch bug info\nReason: {e}")


async def bug_comments(id: int, include_private_comments: bool = False):
    """Returns the comments of given bug id
    Private comments are not included by default
    but can be explicitely requested
    """

    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")

    try:
        all_comments = await utils.bz.bug_comments(id)

        if include_private_comments:
            return all_comments

        public_comments = []

        for comment in all_comments:
            if not comment["is_private"]:
                public_comments.append(comment)

        return public_comments

    except Exception as e:
        raise ToolError(f"Failed to fetch bug comments\nReason: {e}")


async def add_comment(bug_id: int, comment: str, is_private: bool = False) -> dict[str, int]:
    """Add a comment to a bug. It can optionally be private. If success, returns the created comment id."""
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    
    try:
        return await utils.bz.add_comment(bug_id, comment, is_private)
    except Exception as e:
        raise ToolError(f"Failed to create a comment\n{e}")


async def bugs_quicksearch(query: str, limit: int = 50, offset: int = 0) -> list[Any]:
    """Search bugs using bugzilla's quicksearch syntax

    To reduce the token limit & response time, only returns a subset of fields for each bug

    The user can query full details of each bug using the bug_info tool
    """

    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")

    tool_params = utils.bz.params.copy()
    tool_params["quicksearch"] = query
    tool_params["limit"] = limit
    tool_params["offset"] = offset

    r = await utils.bz.client.get(f"{utils.bz.api_url}/bug", params=tool_params)

    if r.status_code != 200:
        raise ToolError(f"Search failed with status code {r.status_code}")

    all_bugs = r.json()["bugs"]

    bugs_with_essential_fields = []

    for bug in all_bugs:
        b = {
            "bug_id": bug["id"],
            "product": bug["product"],
            "component": bug["component"],
            "assigned_to": bug["assigned_to"],
            "status": bug["status"],
            "resolution": bug["resolution"],
            "summary": bug["summary"],
            "last_updated": bug["last_change_time"],
        }

        bugs_with_essential_fields.append(b)

    return bugs_with_essential_fields


async def learn_quicksearch_syntax() -> str:
    """Access the documentation of the bugzilla quicksearch syntax.
    LLM can learn using this tool. Response is in HTML"""

    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{utils.bz.base_url}/page.cgi?id=quicksearch.html")

        if r.status_code != 200:
            raise PromptError(
                f"Failed to fetch bugzilla quicksearch_syntax with status code {r.status_code}"
            )

        return r.text


async def server_url() -> str:
    """bugzilla server's base url"""
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    return utils.bz.base_url


async def bug_url(bug_id: int) -> str:
    """returns the bug url"""
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    return f"{utils.bz.base_url}/show_bug.cgi?id={bug_id}"

