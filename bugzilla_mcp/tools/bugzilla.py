"""Bugzilla tools for MCP server"""

import base64
import json
import os
import httpx
from typing import Annotated, Any
from pydantic import Field
from fastmcp.utilities.types import Image
from mcp.types import TextContent
from fastmcp.exceptions import ToolError, PromptError
import bugzilla_mcp.utils as utils
from bugzilla_mcp.utils.bugzilla import classify_bug


def _client() -> utils.Bugzilla:
    """The current request's Bugzilla client"""
    bz = utils.current_bz.get()
    if bz is None:
        raise ToolError("Bugzilla client not initialized. Please ensure api_key and bugzilla_url headers are provided.")
    return bz


def _as_list(value):
    """Accept one value or a list: assistants often pass `status="NEW"` for a list filter"""
    if value is None or isinstance(value, list):
        return value
    return [value]


# Shared parameter types. Statuses, resolutions etc. are instance-specific, so these
# describe the format with examples instead of a fixed Literal of allowed values.
BugIds = Annotated[int | list[int], Field(description="One bug id or a list of bug ids, e.g. 12345 or [12345, 12346]")]
StrFilter = Annotated[str | list[str] | None, Field(description="One value or a list; matches any of them")]


def _compact(bug: dict[str, Any]) -> dict[str, Any]:
    """Drop empty fields (e.g. unused cf_* custom fields) to save tokens"""
    return {k: v for k, v in bug.items() if v not in (None, "", [], {})}


async def bug_info(
    id: int,
    full: bool = False,
    include_fields: Annotated[
        list[str] | None,
        Field(description='Only return these fields, e.g. ["status", "assigned_to", "cf_qatouch_id"]'),
    ] = None,
) -> dict[str, Any]:
    """Returns information about a given bugzilla bug id.

    Empty fields are left out by default; pass full=True for every field, or
    include_fields to fetch only the fields you need.
    """

    bz = _client()

    try:
        bug = await bz.bug_info(id, include_fields=include_fields)
        # update_token is a form/CSRF token: no use to an assistant
        bug.pop("update_token", None)
        return bug if full else _compact(bug)

    except Exception as e:
        raise ToolError(f"Failed to fetch bug info\nReason: {e}")


async def bug_comments(id: int, include_private_comments: bool = False):
    """Returns the comments of given bug id
    Private comments are not included by default
    but can be explicitely requested
    """

    bz = _client()

    try:
        all_comments = await bz.bug_comments(id)

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
    bz = _client()
    
    try:
        return await bz.add_comment(bug_id, comment, is_private)
    except Exception as e:
        raise ToolError(f"Failed to create a comment\n{e}")


async def bugs_quicksearch(query: str, limit: int = 50, offset: int = 0) -> list[Any]:
    """Search bugs using bugzilla's quicksearch syntax

    To reduce the token limit & response time, only returns a subset of fields for each bug

    The user can query full details of each bug using the bug_info tool
    """

    bz = _client()

    headers, tool_params = await bz.auth()
    tool_params.update({"quicksearch": query, "limit": limit, "offset": offset})

    r = await bz.client.get(f"{bz.api_url}/bug", headers=headers, params=tool_params)

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

    bz = _client()

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{bz.base_url}/page.cgi?id=quicksearch.html")

        if r.status_code != 200:
            raise PromptError(
                f"Failed to fetch bugzilla quicksearch_syntax with status code {r.status_code}"
            )

        return r.text


async def server_url() -> str:
    """bugzilla server's base url"""
    bz = _client()
    return bz.base_url


async def bug_url(bug_id: int) -> str:
    """returns the bug url"""
    bz = _client()
    return f"{bz.base_url}/show_bug.cgi?id={bug_id}"


async def download_attachments(bug_id: int, dest_dir: str | None = None) -> list[dict[str, Any]]:
    """Download all attachments for a specific bug to a temporary directory.

    If dest_dir is not provided, a local 'tmp' directory in the project root is used.
    Local server only: on the hosted server use bug_attachments / get_attachment.
    """
    bz = _client()
    try:
        return await bz.download_attachments(bug_id, dest_dir)
    except Exception as e:
        raise ToolError(f"Failed to download attachments\nReason: {e}")


async def download_attachment(attachment_id: int, dest_dir: str | None = None) -> dict[str, Any]:
    """Download a specific attachment by its ID.

    If dest_dir is not provided, a local 'tmp' directory in the project root is used.
    Local server only: on the hosted server use bug_attachments / get_attachment.
    """
    bz = _client()
    try:
        return await bz.download_attachment(attachment_id, dest_dir)
    except Exception as e:
        raise ToolError(f"Failed to download attachment\nReason: {e}")


async def bugs_info(ids: BugIds) -> list[dict[str, Any]]:
    """Get information about multiple bugs in a single request."""
    bz = _client()
    try:
        return await bz.bugs_info(_as_list(ids))
    except Exception as e:
        raise ToolError(f"Failed to fetch batch bug info\nReason: {e}")


async def bugs_comments(ids: BugIds) -> dict[str, list[dict[str, Any]]]:
    """Fetch comments for multiple bugs in parallel."""
    bz = _client()
    try:
        return await bz.bugs_comments(_as_list(ids))
    except Exception as e:
        raise ToolError(f"Failed to fetch batch comments\nReason: {e}")


async def bugs_analysis_context(ids: BugIds) -> dict[str, Any]:
    """Get consolidated prompt-friendly context (info + comments preview) for multiple bugs in parallel."""
    bz = _client()
    try:
        return await bz.bugs_analysis_context(_as_list(ids))
    except Exception as e:
        raise ToolError(f"Failed to fetch bugs analysis context\nReason: {e}")


async def classify_bugs_heuristics(ids: BugIds) -> dict[str, Any]:
    """Group bugs into to_fix, invalid and review_needed using status and resolution only.

    Rules, in order:
    - invalid: status RESOLVED/VERIFIED/CLOSED and resolution INVALID, WONTFIX,
      DUPLICATE, WORKSFORME or NOTABUG (closed as not-a-bug)
    - to_fix: status NEW, ASSIGNED, REOPENED or UNCONFIRMED (still open)
    - review_needed: everything else, e.g. RESOLVED FIXED, or a custom status
      such as CONFIRMED that the rules don't know

    It doesn't read summaries or comments; use bugs_analysis_context for that.
    """
    bz = _client()
    try:
        groups: dict[str, list[dict[str, Any]]] = {"to_fix": [], "invalid": [], "review_needed": []}
        for info in await bz.bugs_info(_as_list(ids)):
            groups[classify_bug(info)].append(
                {
                    "id": info.get("id"),
                    "summary": info.get("summary"),
                    **{k: info.get(k, "") for k in ("product", "component", "status", "resolution")},
                }
            )
        return groups
    except Exception as e:
        raise ToolError(
            f"Failed to perform heuristics classification\nReason: {e}"
        )


async def analyze_bugs_statistics(ids: BugIds) -> dict[str, Any]:
    """Perform server-side statistical analysis on a batch of bug IDs based on triage classifications.

    Returns breakdown of classifications, product distribution, component distribution,
    severity, priority workload, and assignee distribution with both counts and percentages.
    """
    bz = _client()
    try:
        return await bz.bugs_stats_analysis(_as_list(ids))
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
    keywords: Annotated[str | list[str] | None, Field(description='One keyword or a list, e.g. "regression"')] = None,
    target_milestone: str | None = None,
) -> dict[str, Any]:
    """File a new bug in Bugzilla.

    Returns the ID of the newly created bug.
    """
    bz = _client()
    try:
        return await bz.create_bug(
            product=product,
            component=component,
            summary=summary,
            version=version,
            description=description,
            severity=severity,
            priority=priority,
            assigned_to=assigned_to,
            keywords=_as_list(keywords),
            target_milestone=target_milestone,
        )
    except Exception as e:
        raise ToolError(f"Failed to create bug\nReason: {e}")


AddRemove = Annotated[
    dict[str, list[str]] | None,
    Field(description='Changes to a list field, e.g. {"add": ["a@example.com"], "remove": ["b@example.com"]}'),
]
AddRemoveIds = Annotated[
    dict[str, list[int]] | None,
    Field(description='Changes to a bug list, e.g. {"add": [123], "remove": [456]}; {"set": [...]} replaces it'),
]


async def update_bug(
    ids: BugIds,
    status: Annotated[str | None, Field(description='New status, e.g. "ASSIGNED" or "RESOLVED"; must be a status your Bugzilla defines')] = None,
    resolution: Annotated[str | None, Field(description='Required when resolving, e.g. "FIXED", "INVALID", "DUPLICATE"')] = None,
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
    keywords: AddRemove = None,
    cc: AddRemove = None,
    see_also: AddRemove = None,
    blocks: AddRemoveIds = None,
    depends_on: AddRemoveIds = None,
    extra_fields: Annotated[
        dict[str, Any] | None,
        Field(description='Custom fields, e.g. {"cf_qatouch_id": "123"}'),
    ] = None,
    dry_run: Annotated[
        bool,
        Field(description="Return the planned changes and the bugs' current values without changing anything"),
    ] = False,
) -> dict[str, Any]:
    """Update one or more bugs. Supports changing status, resolution, assignee, severity,
    priority, whiteboard notes, version, summary, product, component, op_sys, platform,
    qa_contact, url, keywords, cc, see_also, blocks, depends_on, custom fields and adding a
    comment in a single operation.

    To mark as duplicate set resolution='DUPLICATE' and dupe_of=<original_bug_id>.

    One call can change many bugs: use dry_run=True first to see what would change.
    """
    bz = _client()
    try:
        return await bz.update_bug(
            ids=_as_list(ids),
            dry_run=dry_run,
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
    bz = _client()
    try:
        return await bz.bug_history(bug_id=bug_id, new_since=new_since)
    except Exception as e:
        raise ToolError(f"Failed to fetch bug history\nReason: {e}")


async def bugs_advanced_search(
    product: StrFilter = None,
    component: StrFilter = None,
    status: Annotated[str | list[str] | None, Field(description='One status or a list, e.g. "NEW" or ["NEW", "ASSIGNED"]')] = None,
    resolution: Annotated[str | list[str] | None, Field(description='One resolution or a list, e.g. "FIXED"; use "---" for unresolved')] = None,
    assigned_to: Annotated[str | None, Field(description="Assignee login (email)")] = None,
    creator: Annotated[str | None, Field(description="Reporter login (email)")] = None,
    severity: StrFilter = None,
    priority: StrFilter = None,
    creation_time: Annotated[str | None, Field(description='Created on or after this ISO 8601 date, e.g. "2026-09-01"')] = None,
    last_change_time: Annotated[str | None, Field(description='Changed on or after this ISO 8601 date, e.g. "2026-09-01"')] = None,
    keywords: StrFilter = None,
    version: StrFilter = None,
    target_milestone: StrFilter = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Search bugs using structured multi-criteria filters (AND logic).

    More powerful than quicksearch — supports filtering by product, component,
    status, resolution, assignee, creator, severity, priority, date ranges,
    keywords, version, and target milestone simultaneously.

    Returns token-efficient results with essential fields only.
    """
    bz = _client()
    try:
        return await bz.bugs_advanced_search(
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
    bz = _client()
    try:
        return await bz.bug_dependencies(bug_id=bug_id)
    except Exception as e:
        raise ToolError(f"Failed to fetch bug dependencies\nReason: {e}")


async def duplicate_chain(bug_id: int, max_depth: int = 10) -> list[dict[str, Any]]:
    """Traverse the duplicate chain of a bug to find its canonical root.

    Returns an ordered list from the given bug to the root original,
    each entry with id, summary, status, and dupe_of.
    """
    bz = _client()
    try:
        return await bz.duplicate_chain(bug_id=bug_id, max_depth=max_depth)
    except Exception as e:
        raise ToolError(f"Failed to traverse duplicate chain\nReason: {e}")


async def get_user(
    names: Annotated[str | list[str] | None, Field(description="One login (email) or a list")] = None,
    ids: Annotated[int | list[int] | None, Field(description="One user id or a list")] = None,
) -> list[dict[str, Any]]:
    """Look up Bugzilla users by login name(s) or user ID(s).

    Provide either names (list of login emails) or ids (list of user IDs).
    Returns user details including real_name, email, and can_login.
    """
    bz = _client()
    try:
        return await bz.get_user(names=_as_list(names), ids=_as_list(ids))
    except Exception as e:
        raise ToolError(f"Failed to fetch user info\nReason: {e}")


async def search_users(match: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for Bugzilla users by partial name or email.

    Returns matching users for auto-suggest, assignment, and CC workflows.
    """
    bz = _client()
    try:
        return await bz.search_users(match=match, limit=limit)
    except Exception as e:
        raise ToolError(f"Failed to search users\nReason: {e}")


async def list_products() -> list[dict[str, Any]]:
    """List all Bugzilla products accessible to the current user.

    Returns product names, descriptions, and active status.
    Useful for discovering valid products before filing a bug.
    """
    bz = _client()
    try:
        return await bz.list_products()
    except Exception as e:
        raise ToolError(f"Failed to list products\nReason: {e}")


async def get_product_components(product_name: str) -> dict[str, Any]:
    """List all components for a given product name.

    Returns component names, descriptions, and default assignee for each,
    enabling accurate bug routing before filing.
    """
    bz = _client()
    try:
        return await bz.get_product_components(product_name=product_name)
    except Exception as e:
        raise ToolError(f"Failed to fetch product components\nReason: {e}")


async def upload_attachment(
    bug_id: int,
    summary: str,
    text: str | None = None,
    data_base64: str | None = None,
    file_name: str | None = None,
    content_type: str | None = None,
    comment: str | None = None,
    is_patch: bool = False,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Attach content to a bug.

    Pass exactly one of:
    - text: plain text such as a log or a patch (file_name defaults to attachment.txt)
    - data_base64: base64-encoded file content (file_name required)
    - file_path: path to a file on the server's machine; local server only

    Content-type is auto-detected if not provided. Set is_patch=True for patch/diff files.

    Returns the attachment_id and bug_id on success.
    """
    bz = _client()
    try:
        return await bz.upload_attachment(
            bug_id=bug_id,
            file_path=file_path,
            summary=summary,
            file_name=file_name,
            content_type=content_type,
            comment=comment,
            is_patch=is_patch,
            text=text,
            data_base64=data_base64,
        )
    except Exception as e:
        raise ToolError(f"Failed to upload attachment\nReason: {e}")


async def tag_comment(
    comment_id: int,
    add: Annotated[str | list[str] | None, Field(description='One tag or a list, e.g. "needs-review"')] = None,
    remove: Annotated[str | list[str] | None, Field(description="One tag or a list")] = None,
) -> dict[str, Any]:
    """Add or remove tags on a specific bug comment.

    Tags are useful for semantic labelling: e.g. 'fix-candidate', 'ai-generated',
    'reproduction', 'needs-review'. Returns the current list of tags on the comment.
    """
    bz = _client()
    try:
        return await bz.tag_comment(comment_id=comment_id, add=_as_list(add), remove=_as_list(remove))
    except Exception as e:
        raise ToolError(f"Failed to tag comment\nReason: {e}")


# Attachments bigger than this aren't inlined into the assistant's context
MAX_INLINE_ATTACHMENT_BYTES = 10 * 1024 * 1024

TEXT_CONTENT_TYPES = (
    "text/",
    "application/json",
    "application/xml",
    "application/x-patch",
    "application/x-diff",
)


async def bug_attachments(bug_id: int) -> list[dict[str, Any]]:
    """List a bug's attachments (id, file name, content type, size, flags) without file data.

    Use get_attachment with an id from this list to read one.
    """
    bz = _client()
    try:
        return await bz.bug_attachments(bug_id)
    except Exception as e:
        raise ToolError(f"Failed to list attachments\nReason: {e}")


async def get_attachment(attachment_id: int):
    """Read one attachment.

    Images are returned as images, text files and patches as text. Other
    binary files and files over 10 MB return metadata and a link only.
    """
    bz = _client()
    try:
        att = await bz.get_attachment(attachment_id)
        raw = base64.b64decode(att.get("data") or "")
    except Exception as e:
        raise ToolError(f"Failed to fetch attachment\nReason: {e}")

    meta = _compact({k: att.get(k) for k in (
        "id", "bug_id", "file_name", "summary", "content_type", "size",
        "creator", "creation_time", "is_patch", "is_obsolete",
    )})
    content_type = att.get("content_type") or ""
    link = f"{bz.base_url}/attachment.cgi?id={attachment_id}"

    def text(value) -> TextContent:
        return TextContent(type="text", text=value if isinstance(value, str) else json.dumps(value))

    # Explicit content blocks: fastmcp would otherwise serialize a mixed list as one JSON string
    if len(raw) > MAX_INLINE_ATTACHMENT_BYTES:
        return [text({**meta, "note": "Too large to show inline; open the link", "url": link})]
    if content_type.startswith("image/"):
        image = Image(data=raw, format=content_type.split("/", 1)[1])
        return [text(meta), image.to_image_content()]
    if att.get("is_patch") or content_type.startswith(TEXT_CONTENT_TYPES):
        return [text(meta), text(raw.decode("utf-8", errors="replace"))]
    return [text({**meta, "note": "Binary file; open the link to download it", "url": link})]


READ_ONLY_TOOLS = [
    bug_info, bug_comments, bugs_quicksearch, learn_quicksearch_syntax, server_url,
    bug_url, bug_attachments, get_attachment, bugs_info, bugs_comments,
    bugs_analysis_context, classify_bugs_heuristics, analyze_bugs_statistics,
    bug_history, bugs_advanced_search, bug_dependencies, duplicate_chain, get_user,
    search_users, list_products, get_product_components,
]
# Add to Bugzilla (or, locally, write files) without changing existing data
ADDITIVE_TOOLS = [add_comment, create_bug, upload_attachment, tag_comment]
# Write to the server's disk: only registered by the single-user local server
LOCAL_ONLY_TOOLS = [download_attachments, download_attachment]
# Change existing bugs: status, assignee, product, ...
DESTRUCTIVE_TOOLS = [update_bug]


WRITE_TOOL_NAMES = {fn.__name__ for fn in ADDITIVE_TOOLS + LOCAL_ONLY_TOOLS + DESTRUCTIVE_TOOLS}

DISABLED_TOOLS_ENV = "BUGZILLA_DISABLED_TOOLS"


def register_tools(mcp, local_files: bool = False) -> None:
    """Register tools with hints so clients can ask before writes.

    local_files: also register the tools that save to the server's disk (local server only).
    Tools named in BUGZILLA_DISABLED_TOOLS (comma-separated) are skipped.
    """
    disabled = {n.strip() for n in os.environ.get(DISABLED_TOOLS_ENV, "").split(",") if n.strip()}
    groups = [
        (READ_ONLY_TOOLS, {"readOnlyHint": True}),
        (ADDITIVE_TOOLS, {"readOnlyHint": False, "destructiveHint": False}),
        (LOCAL_ONLY_TOOLS if local_files else [], {"readOnlyHint": False, "destructiveHint": False}),
        (DESTRUCTIVE_TOOLS, {"readOnlyHint": False, "destructiveHint": True}),
    ]
    for tools, annotations in groups:
        for fn in tools:
            if fn.__name__ not in disabled:
                mcp.tool(annotations=annotations)(fn)
