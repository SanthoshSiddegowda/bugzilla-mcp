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


async def download_attachments(bug_id: int, dest_dir: str | None = None) -> list[dict[str, Any]]:
    """Download all attachments for a specific bug to a temporary directory.

    If dest_dir is not provided, a local 'tmp' directory in the project root is used.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.download_attachments(bug_id, dest_dir)
    except Exception as e:
        raise ToolError(f"Failed to download attachments\nReason: {e}")


async def download_attachment(attachment_id: int, dest_dir: str | None = None) -> dict[str, Any]:
    """Download a specific attachment by its ID.

    If dest_dir is not provided, a local 'tmp' directory in the project root is used.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.download_attachment(attachment_id, dest_dir)
    except Exception as e:
        raise ToolError(f"Failed to download attachment\nReason: {e}")


async def bugs_info(ids: list[int]) -> list[dict[str, Any]]:
    """Get information about multiple bugs in a single request."""
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.bugs_info(ids)
    except Exception as e:
        raise ToolError(f"Failed to fetch batch bug info\nReason: {e}")


async def bugs_comments(ids: list[int]) -> dict[str, list[dict[str, Any]]]:
    """Fetch comments for multiple bugs in parallel."""
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.bugs_comments(ids)
    except Exception as e:
        raise ToolError(f"Failed to fetch batch comments\nReason: {e}")


async def bugs_analysis_context(ids: list[int]) -> dict[str, Any]:
    """Get consolidated prompt-friendly context (info + comments preview) for multiple bugs in parallel."""
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.bugs_analysis_context(ids)
    except Exception as e:
        raise ToolError(f"Failed to fetch bugs analysis context\nReason: {e}")


async def classify_bugs_heuristics(ids: list[int]) -> dict[str, Any]:
    """Automatically classify a list of bugs into TO_FIX, INVALID, or REVIEW_NEEDED based on server-side heuristics.

    Analyzes status, resolution, summaries, and activity in parallel to deliver instant automated triage.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        info_list = await utils.bz.bugs_info(ids)

        to_fix = []
        invalid = []
        review_needed = []

        for info in info_list:
            bid = info.get("id")
            status = info.get("status", "")
            resolution = info.get("resolution", "")
            product = info.get("product", "")
            component = info.get("component", "")

            # Heuristics classification
            is_closed_invalid = (
                status in ["RESOLVED", "VERIFIED", "CLOSED"]
                and resolution
                in [
                    "INVALID",
                    "WONTFIX",
                    "DUPLICATE",
                    "WORKSFORME",
                    "NOTABUG",
                ]
            )

            is_active_valid = status in [
                "NEW",
                "ASSIGNED",
                "REOPENED",
                "UNCONFIRMED",
            ]

            bug_summary = {
                "id": bid,
                "summary": info.get("summary"),
                "product": product,
                "component": component,
                "status": status,
                "resolution": resolution,
            }

            if is_closed_invalid:
                invalid.append(bug_summary)
            elif is_active_valid:
                to_fix.append(bug_summary)
            else:
                review_needed.append(bug_summary)

        return {
            "to_fix": to_fix,
            "invalid": invalid,
            "review_needed": review_needed,
        }
    except Exception as e:
        raise ToolError(
            f"Failed to perform heuristics classification\nReason: {e}"
        )


async def analyze_bugs_statistics(ids: list[int]) -> dict[str, Any]:
    """Perform server-side statistical analysis on a batch of bug IDs based on triage classifications.

    Returns breakdown of classifications, product distribution, component distribution,
    severity, priority workload, and assignee distribution with both counts and percentages.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.bugs_stats_analysis(ids)
    except Exception as e:
        raise ToolError(f"Failed to perform statistical analysis\nReason: {e}")


async def create_bug(
    product: str,
    component: str,
    summary: str,
    version: str,
    description: str,
    severity: str | None = None,
    priority: str | None = None,
    assigned_to: str | None = None,
    keywords: list[str] | None = None,
    target_milestone: str | None = None,
) -> dict[str, Any]:
    """File a new bug in Bugzilla.

    Returns the ID of the newly created bug.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.create_bug(
            product=product,
            component=component,
            summary=summary,
            version=version,
            description=description,
            severity=severity,
            priority=priority,
            assigned_to=assigned_to,
            keywords=keywords,
            target_milestone=target_milestone,
        )
    except Exception as e:
        raise ToolError(f"Failed to create bug\nReason: {e}")


async def update_bug(
    ids: list[int],
    status: str | None = None,
    resolution: str | None = None,
    assigned_to: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    whiteboard: str | None = None,
    comment: str | None = None,
    comment_is_private: bool = False,
    dupe_of: int | None = None,
    target_milestone: str | None = None,
    version: str | None = None,
    summary: str | None = None,
    product: str | None = None,
    component: str | None = None,
    op_sys: str | None = None,
    platform: str | None = None,
    qa_contact: str | None = None,
    url: str | None = None,
    keywords: dict[str, list[str]] | None = None,
    cc: dict[str, list[str]] | None = None,
    see_also: dict[str, list[str]] | None = None,
    blocks: dict[str, list[int]] | None = None,
    depends_on: dict[str, list[int]] | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update one or more bugs. Supports changing status, resolution, assignee, severity,
    priority, whiteboard notes, version, summary, product, component, op_sys, platform,
    qa_contact, url, keywords, cc, see_also, blocks, depends_on, custom fields and adding a
    comment in a single operation.

    To mark as duplicate set resolution='DUPLICATE' and dupe_of=<original_bug_id>.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.update_bug(
            ids=ids,
            status=status,
            resolution=resolution,
            assigned_to=assigned_to,
            severity=severity,
            priority=priority,
            whiteboard=whiteboard,
            comment=comment,
            comment_is_private=comment_is_private,
            dupe_of=dupe_of,
            target_milestone=target_milestone,
            version=version,
            summary=summary,
            product=product,
            component=component,
            op_sys=op_sys,
            platform=platform,
            qa_contact=qa_contact,
            url=url,
            keywords=keywords,
            cc=cc,
            see_also=see_also,
            blocks=blocks,
            depends_on=depends_on,
            extra_fields=extra_fields,
        )
    except Exception as e:
        raise ToolError(f"Failed to update bug\nReason: {e}")


async def bug_history(bug_id: int, new_since: str | None = None) -> list[dict[str, Any]]:
    """Get the full change history for a bug.

    Use new_since (ISO datetime, e.g. '2024-01-01T00:00:00Z') to filter
    to only changes after a specific date. Returns who changed what and when.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.bug_history(bug_id=bug_id, new_since=new_since)
    except Exception as e:
        raise ToolError(f"Failed to fetch bug history\nReason: {e}")


async def bugs_advanced_search(
    product: list[str] | None = None,
    component: list[str] | None = None,
    status: list[str] | None = None,
    resolution: list[str] | None = None,
    assigned_to: str | None = None,
    creator: str | None = None,
    severity: list[str] | None = None,
    priority: list[str] | None = None,
    creation_time: str | None = None,
    last_change_time: str | None = None,
    keywords: list[str] | None = None,
    version: list[str] | None = None,
    target_milestone: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Search bugs using structured multi-criteria filters (AND logic).

    More powerful than quicksearch — supports filtering by product, component,
    status, resolution, assignee, creator, severity, priority, date ranges,
    keywords, version, and target milestone simultaneously.

    Returns token-efficient results with essential fields only.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.bugs_advanced_search(
            product=product,
            component=component,
            status=status,
            resolution=resolution,
            assigned_to=assigned_to,
            creator=creator,
            severity=severity,
            priority=priority,
            creation_time=creation_time,
            last_change_time=last_change_time,
            keywords=keywords,
            version=version,
            target_milestone=target_milestone,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise ToolError(f"Failed to perform advanced search\nReason: {e}")


async def bug_dependencies(bug_id: int) -> dict[str, Any]:
    """Get the dependency graph for a bug — which bugs it blocks and which it depends on."""
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.bug_dependencies(bug_id=bug_id)
    except Exception as e:
        raise ToolError(f"Failed to fetch bug dependencies\nReason: {e}")


async def duplicate_chain(bug_id: int, max_depth: int = 10) -> list[dict[str, Any]]:
    """Traverse the duplicate chain of a bug to find its canonical root.

    Returns an ordered list from the given bug to the root original,
    each entry with id, summary, status, and dupe_of.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.duplicate_chain(bug_id=bug_id, max_depth=max_depth)
    except Exception as e:
        raise ToolError(f"Failed to traverse duplicate chain\nReason: {e}")


async def get_user(
    names: list[str] | None = None, ids: list[int] | None = None
) -> list[dict[str, Any]]:
    """Look up Bugzilla users by login name(s) or user ID(s).

    Provide either names (list of login emails) or ids (list of user IDs).
    Returns user details including real_name, email, and can_login.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.get_user(names=names, ids=ids)
    except Exception as e:
        raise ToolError(f"Failed to fetch user info\nReason: {e}")


async def search_users(match: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for Bugzilla users by partial name or email.

    Returns matching users for auto-suggest, assignment, and CC workflows.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.search_users(match=match, limit=limit)
    except Exception as e:
        raise ToolError(f"Failed to search users\nReason: {e}")


async def list_products() -> list[dict[str, Any]]:
    """List all Bugzilla products accessible to the current user.

    Returns product names, descriptions, and active status.
    Useful for discovering valid products before filing a bug.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.list_products()
    except Exception as e:
        raise ToolError(f"Failed to list products\nReason: {e}")


async def get_product_components(product_name: str) -> dict[str, Any]:
    """List all components for a given product name.

    Returns component names, descriptions, and default assignee for each,
    enabling accurate bug routing before filing.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.get_product_components(product_name=product_name)
    except Exception as e:
        raise ToolError(f"Failed to fetch product components\nReason: {e}")


async def upload_attachment(
    bug_id: int,
    file_path: str,
    summary: str,
    file_name: str | None = None,
    content_type: str | None = None,
    comment: str | None = None,
    is_patch: bool = False,
) -> dict[str, Any]:
    """Upload a local file as an attachment to a bug.

    Reads the file, base64-encodes it, and posts it to the Bugzilla REST API.
    Content-type is auto-detected from the file extension if not provided.
    Set is_patch=True for patch/diff files.

    Returns the attachment_id and bug_id on success.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.upload_attachment(
            bug_id=bug_id,
            file_path=file_path,
            summary=summary,
            file_name=file_name,
            content_type=content_type,
            comment=comment,
            is_patch=is_patch,
        )
    except Exception as e:
        raise ToolError(f"Failed to upload attachment\nReason: {e}")


async def tag_comment(
    comment_id: int,
    add: list[str] | None = None,
    remove: list[str] | None = None,
) -> dict[str, Any]:
    """Add or remove tags on a specific bug comment.

    Tags are useful for semantic labelling: e.g. 'fix-candidate', 'ai-generated',
    'reproduction', 'needs-review'. Returns the current list of tags on the comment.
    """
    if utils.bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    try:
        return await utils.bz.tag_comment(comment_id=comment_id, add=add, remove=remove)
    except Exception as e:
        raise ToolError(f"Failed to tag comment\nReason: {e}")



