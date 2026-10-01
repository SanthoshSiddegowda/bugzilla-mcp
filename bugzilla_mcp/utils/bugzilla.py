"""Bugzilla API client"""

import asyncio
import base64
import logging
import os
from collections import Counter
from typing import Any
import httpx

logger = logging.getLogger(__name__)

API_KEY_HEADER = "X-BUGZILLA-API-KEY"

# Bugzilla base URL -> whether that instance reads the API key header.
# Keyed by URL only (no secrets). Re-probed after a process restart.
_header_auth_support: dict[str, bool] = {}

CLOSED_STATUSES = {"RESOLVED", "VERIFIED", "CLOSED"}
NOT_A_BUG_RESOLUTIONS = {"INVALID", "WONTFIX", "DUPLICATE", "WORKSFORME", "NOTABUG"}
OPEN_STATUSES = {"NEW", "ASSIGNED", "REOPENED", "UNCONFIRMED"}


def classify_bug(bug: dict[str, Any]) -> str:
    """Triage heuristic: 'invalid' (closed as not-a-bug), 'to_fix' (open) or 'review_needed'"""
    status = bug.get("status", "")
    if status in CLOSED_STATUSES and bug.get("resolution", "") in NOT_A_BUG_RESOLUTIONS:
        return "invalid"
    if status in OPEN_STATUSES:
        return "to_fix"
    return "review_needed"


def _set_if_given(payload: dict[str, Any], **fields: Any) -> None:
    """Copy only the fields the caller actually passed (not None)"""
    payload.update({k: v for k, v in fields.items() if v is not None})


class Bugzilla:
    """Bugzilla API class"""

    def __init__(self, url: str, api_key: str, allow_local_files: bool = False):
        """allow_local_files: let tools read/write the server's filesystem.
        Only the single-user local server (server_local.py) enables it; on a
        shared server it would let any caller read or overwrite server files."""
        url = url.rstrip("/")
        self.allow_local_files: bool = allow_local_files
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

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: Any = None,
        ok: tuple[int, ...] = (200,),
        what: str = "fetch API",
    ) -> Any:
        """Authenticated REST call; returns the decoded JSON or raises on an unexpected status."""
        headers, auth_params = await self.auth()
        kwargs: dict[str, Any] = {"headers": headers, "params": {**auth_params, **(params or {})}}
        if json is not None:
            kwargs["json"] = json

        r = await getattr(self.client, method)(url=f"{self.api_url}{path}", **kwargs)

        if r.status_code not in ok:
            # Bugzilla's error text explains rejected writes; reads only need the code
            detail = f" — {r.text}" if method != "get" else ""
            raise httpx.TransportError(
                f"Failed to {what} with Status code: {r.status_code}{detail}"
            )
        return r.json()

    def _require_local_files(self) -> None:
        if not self.allow_local_files:
            raise PermissionError(
                "Reading or writing files on the server is only available in the local "
                "server (server_local.py). Use get_attachment to read attachments, and "
                "pass text or data_base64 to upload_attachment."
            )

    async def bug_info(self, bug_id: int, include_fields: list[str] | None = None) -> dict[str, Any]:
        """get information about a given bug, optionally only `include_fields`"""
        params = {"include_fields": ",".join(include_fields)} if include_fields else None
        return (await self._request("get", f"/bug/{bug_id}", params=params))["bugs"][0]

    async def bug_comments(self, bug_id: int) -> dict[str, Any]:
        """Get comments of a bug"""
        data = await self._request("get", f"/bug/{bug_id}/comment")
        return data["bugs"][f"{bug_id}"]["comments"]

    async def add_comment(
        self, bug_id: int, comment: str, is_private: bool
    ) -> dict[str, int]:
        """Add a comment to bug, which can optionally be private"""
        return await self._request(
            "post",
            f"/bug/{bug_id}/comment",
            json={"comment": comment, "is_private": is_private},
            ok=(201,),
        )

    async def bug_attachments(self, bug_id: int) -> list[dict[str, Any]]:
        """List a bug's attachments (metadata only, no file data)"""
        data = await self._request(
            "get", f"/bug/{bug_id}/attachment", params={"exclude_fields": "data"}
        )
        return data.get("bugs", {}).get(str(bug_id), [])

    async def get_attachment(self, attachment_id: int) -> dict[str, Any]:
        """Fetch one attachment including its base64 `data`"""
        data = await self._request("get", f"/bug/attachment/{attachment_id}")
        att = data.get("attachments", {}).get(str(attachment_id))
        if not att:
            raise ValueError(f"Attachment {attachment_id} not found in response")
        return att

    @staticmethod
    def _save_attachment(att: dict[str, Any], dest_dir: str | None) -> str:
        """Decode an attachment into dest_dir (default: <project>/tmp) and return its path"""
        if dest_dir is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            dest_dir = os.path.join(project_root, "tmp")
        os.makedirs(dest_dir, exist_ok=True)

        try:
            content = base64.b64decode(att["data"])
        except Exception as e:
            raise ValueError(f"Failed to decode attachment {att.get('id')}: {e}")

        # basename() keeps a hostile file_name from escaping dest_dir
        dest_path = os.path.join(dest_dir, f"{att.get('id')}_{os.path.basename(att.get('file_name') or '')}")
        with open(dest_path, "wb") as f:
            f.write(content)
        return dest_path

    @staticmethod
    def _saved(att: dict[str, Any], path: str, bug_id: int | None = None) -> dict[str, Any]:
        return {
            "id": att.get("id"),
            "bug_id": bug_id if bug_id is not None else att.get("bug_id"),
            "file_name": att.get("file_name"),
            "content_type": att.get("content_type"),
            "size": att.get("size"),
            "path": path,
        }

    async def download_attachments(
        self, bug_id: int, dest_dir: str | None = None
    ) -> list[dict[str, Any]]:
        """Download all attachments of a bug to dest_dir (local server only).

        Returns:
            [{"id", "bug_id", "file_name", "content_type", "size", "path"}, ...]
        """
        self._require_local_files()
        bugs = (await self._request("get", f"/bug/{bug_id}/attachment")).get("bugs", {})
        attachments = bugs.get(str(bug_id)) or bugs.get(bug_id) or []
        return [
            self._saved(att, self._save_attachment(att, dest_dir), bug_id)
            for att in attachments
            if att.get("data")
        ]

    async def download_attachment(
        self, attachment_id: int, dest_dir: str | None = None
    ) -> dict[str, Any]:
        """Download one attachment to dest_dir (local server only).

        Returns:
            {"id", "bug_id", "file_name", "content_type", "size", "path"}
        """
        self._require_local_files()
        att = await self.get_attachment(attachment_id)
        if not att.get("data"):
            raise ValueError(f"No data field found in attachment {attachment_id}")
        return self._saved(att, self._save_attachment(att, dest_dir))

    async def bugs_info(self, bug_ids: list[int]) -> list[dict[str, Any]]:
        """get information about multiple bugs in a single request"""
        if not bug_ids:
            return []
        data = await self._request("get", "/bug", params={"id": ",".join(map(str, bug_ids))})
        return data.get("bugs", [])

    async def bugs_comments(self, bug_ids: list[int]) -> dict[str, Any]:
        """Fetch comments for multiple bugs in parallel"""

        async def fetch_one(bug_id: int):
            try:
                return str(bug_id), await self.bug_comments(bug_id)
            except Exception as e:
                return str(bug_id), {"error": f"Failed to fetch comments: {e}"}

        return dict(await asyncio.gather(*(fetch_one(b) for b in bug_ids)))

    async def bugs_analysis_context(self, bug_ids: list[int]) -> dict[str, Any]:
        """Gather bug info and comment previews in parallel to return a prompt-friendly analysis payload"""
        if not bug_ids:
            return {}

        try:
            info_list = await self.bugs_info(bug_ids)
        except Exception as e:
            raise httpx.TransportError(f"Failed to gather batch bug info: {e}")

        comments_dict = await self.bugs_comments(bug_ids)

        merged = {}
        for info in info_list:
            bid = info.get("id")
            comments = comments_dict.get(str(bid), [])
            if isinstance(comments, dict):  # fetch failed; keep the error visible
                comments_preview, count = [comments], 0
            else:
                count = len(comments)
                # First and last two comments are enough context; keep tokens down
                comments_preview = comments if count <= 4 else (
                    comments[:2]
                    + [{"text": f"... [{count - 4} comments omitted] ...", "is_private": False, "creator": "System"}]
                    + comments[-2:]
                )

            merged[str(bid)] = {
                **{k: info.get(k) for k in (
                    "id", "product", "component", "summary", "status", "resolution",
                    "assigned_to", "creator", "last_change_time", "severity", "priority",
                )},
                "comments_count": count,
                "comments_preview": comments_preview,
            }

        return merged

    async def bugs_stats_analysis(self, bug_ids: list[int]) -> dict[str, Any]:
        """Counts and percentages of triage classification, product, component and assignee,
        plus severity/priority breakdown of the bugs still to fix."""
        info_list = await self.bugs_info(bug_ids) if bug_ids else []
        total = len(info_list)

        classes = Counter({"to_fix": 0, "invalid": 0, "review_needed": 0})
        products, components, assignees = Counter(), Counter(), Counter()
        to_fix_severity, to_fix_priority = Counter(), Counter()

        for info in info_list:
            classification = classify_bug(info)
            classes[classification] += 1
            if classification == "to_fix":
                to_fix_severity[info.get("severity", "Unknown")] += 1
                to_fix_priority[info.get("priority", "Unknown")] += 1
            products[info.get("product", "Unknown")] += 1
            components[info.get("component", "Unknown")] += 1
            assignees[info.get("assigned_to", "unassigned")] += 1

        def distribution(counts: Counter) -> dict[str, dict[str, Any]]:
            return {k: {"count": v, "percentage": round(v / total * 100, 2)} for k, v in counts.items()}

        if total == 0:
            return {
                "total_bugs": 0, "classifications": {}, "products": {}, "components": {},
                "to_fix_severity": {}, "to_fix_priority": {}, "assignee_distribution": {},
            }

        return {
            "total_bugs": total,
            "classifications": distribution(classes),
            "products": distribution(products),
            "components": distribution(components),
            "to_fix_severity": dict(to_fix_severity),
            "to_fix_priority": dict(to_fix_priority),
            "assignee_distribution": distribution(assignees),
        }

    async def create_bug(
        self,
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
        """File a new bug in Bugzilla via POST /rest/bug.

        Returns:
            {"id": <new_bug_id>}
        """
        payload: dict[str, Any] = {
            "product": product,
            "component": component,
            "summary": summary,
            "version": version,
            "description": description,
        }
        _set_if_given(
            payload,
            severity=severity,
            priority=priority,
            assigned_to=assigned_to,
            keywords=keywords or None,
            target_milestone=target_milestone,
        )
        # Bugzilla answers 201 Created; accept 200 too for forks that differ
        return await self._request("post", "/bug", json=payload, ok=(200, 201), what="create bug")

    async def update_bug(
        self,
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
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Update one or more bugs via PUT /rest/bug.

        Returns:
            {"bugs": [{"id": ..., "last_change_time": ...}]}, or with dry_run
            {"dry_run": True, "changes": <payload>, "current": {bug_id: {field: value}}}
        """
        payload: dict[str, Any] = {"ids": ids}
        _set_if_given(
            payload,
            status=status,
            resolution=resolution,
            assigned_to=assigned_to,
            severity=severity,
            priority=priority,
            whiteboard=whiteboard,
            comment={"body": comment, "is_private": comment_is_private} if comment is not None else None,
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
        )
        if extra_fields is not None:
            payload.update(extra_fields)

        if dry_run:
            # Show the current value of every field the update would touch
            fields = [k for k in payload if k not in ("ids", "comment")]
            params = {"id": ",".join(map(str, ids)), "include_fields": ",".join(["id", *fields])}
            bugs = (await self._request("get", "/bug", params=params)).get("bugs", [])
            return {
                "dry_run": True,
                "changes": {k: v for k, v in payload.items() if k != "ids"},
                "current": {str(b["id"]): {k: b.get(k) for k in fields} for b in bugs},
                "not_found": sorted(set(ids) - {b["id"] for b in bugs}),
            }

        # Bugzilla REST takes one id in the URL; `ids` in the body updates them all
        return await self._request("put", f"/bug/{ids[0]}", json=payload, what="update bug")

    async def bug_history(
        self, bug_id: int, new_since: str | None = None
    ) -> list[dict[str, Any]]:
        """Get the change history for a bug via GET /rest/bug/(id)/history.

        Args:
            bug_id: The bug ID.
            new_since: Optional ISO datetime string — only return changes after this date.

        Returns:
            List of history objects with when/who/changes.
        """
        params: dict[str, Any] = {}
        _set_if_given(params, new_since=new_since)
        data = await self._request("get", f"/bug/{bug_id}/history", params=params, what="fetch bug history")
        bugs = data.get("bugs", [])
        return bugs[0].get("history", []) if bugs else []

    async def bugs_advanced_search(
        self,
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
        """Search for bugs with structured multi-criteria filters via GET /rest/bug.

        Returns:
            List of bug dicts with essential fields only to preserve token budget.
        """
        filters = {
            "product": product, "component": component, "status": status,
            "resolution": resolution, "assigned_to": assigned_to, "creator": creator,
            "severity": severity, "priority": priority, "creation_time": creation_time,
            "last_change_time": last_change_time, "keywords": keywords,
            "version": version, "target_milestone": target_milestone,
        }
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        params.update({k: v for k, v in filters.items() if v})

        data = await self._request("get", "/bug", params=params, what="search bugs")

        essential_keys = (
            "id", "summary", "status", "resolution",
            "product", "component", "assigned_to", "priority", "severity",
            "creation_time", "last_change_time",
        )
        return [{k: b.get(k) for k in essential_keys} for b in data.get("bugs", [])]

    async def bug_dependencies(self, bug_id: int) -> dict[str, Any]:
        """Fetch dependency info (blocks / depends_on) for a bug.

        Returns:
            {"id": ..., "blocks": [...], "depends_on": [...]}
        """
        bug = await self.bug_info(bug_id)
        return {
            "id": bug.get("id"),
            "summary": bug.get("summary"),
            "status": bug.get("status"),
            "blocks": bug.get("blocks", []),
            "depends_on": bug.get("depends_on", []),
        }

    async def duplicate_chain(
        self, bug_id: int, max_depth: int = 10
    ) -> list[dict[str, Any]]:
        """Follow dupe_of links from a bug to the canonical root.

        Returns:
            Ordered list from child to root: [{"id", "summary", "status", "dupe_of"}, ...]
        """
        chain: list[dict[str, Any]] = []
        visited: set[int] = set()
        current_id: int | None = bug_id

        while current_id is not None and len(chain) < max_depth and current_id not in visited:
            visited.add(current_id)
            bug = await self.bug_info(current_id)
            chain.append({k: bug.get(k) for k in ("id", "summary", "status", "dupe_of")})
            current_id = bug.get("dupe_of")

        return chain

    async def get_user(
        self, names: list[str] | None = None, ids: list[int] | None = None
    ) -> list[dict[str, Any]]:
        """Look up Bugzilla users by login name(s) or user ID(s).

        Returns:
            List of user objects with id, real_name, name, email, can_login.
        """
        params = {k: v for k, v in {"names": names, "ids": ids}.items() if v}
        data = await self._request("get", "/user", params=params, what="fetch users")
        return data.get("users", [])

    async def search_users(self, match: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for Bugzilla users by partial name or email (substring match).

        Returns:
            List of matching user objects.
        """
        data = await self._request(
            "get", "/user", params={"match": match, "limit": limit}, what="search users"
        )
        return data.get("users", [])

    async def list_products(self) -> list[dict[str, Any]]:
        """List all products that the authenticated user can access.

        Returns:
            List of product objects with id, name, description, is_active.
        """
        ids = (await self._request("get", "/product_accessible", what="list products")).get("ids", [])
        if not ids:
            return []

        data = await self._request("get", "/product", params={"ids": ids}, what="fetch product details")
        return [
            {k: p.get(k) for k in ("id", "name", "description", "is_active")}
            for p in data.get("products", [])
        ]

    async def get_product_components(
        self, product_name: str
    ) -> dict[str, Any]:
        """Fetch components for a product by name.

        Returns:
            {"name": "...", "components": [{"name", "description", "default_assignee"}, ...]}
        """
        data = await self._request("get", "/product", params={"names": product_name}, what="fetch product")
        products = data.get("products", [])
        if not products:
            raise ValueError(f"Product '{product_name}' not found")

        product = products[0]
        return {
            "name": product.get("name"),
            "components": [
                {k: c.get(k) for k in ("name", "description", "default_assignee")}
                for c in product.get("components", [])
            ],
        }

    async def upload_attachment(
        self,
        bug_id: int,
        file_path: str | None = None,
        summary: str = "",
        file_name: str | None = None,
        content_type: str | None = None,
        comment: str | None = None,
        is_patch: bool = False,
        text: str | None = None,
        data_base64: str | None = None,
    ) -> dict[str, Any]:
        """Attach content to a bug via POST /rest/bug/(id)/attachment.

        Pass exactly one of `text`, `data_base64` or (local server only) `file_path`.

        Returns:
            {"attachment_id": ..., "bug_id": ...}
        """
        if not summary:
            raise ValueError("summary is required")
        if sum(x is not None for x in (file_path, text, data_base64)) != 1:
            raise ValueError("Pass exactly one of text, data_base64 or file_path")

        if file_path is not None:
            self._require_local_files()
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            with open(file_path, "rb") as fh:
                b64_data = base64.b64encode(fh.read()).decode("utf-8")
            final_name = file_name or os.path.basename(file_path)
        elif text is not None:
            b64_data = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            final_name = file_name or "attachment.txt"
        else:
            try:
                base64.b64decode(data_base64, validate=True)
            except ValueError:
                raise ValueError("data_base64 is not valid base64")
            if not file_name:
                raise ValueError("file_name is required with data_base64")
            b64_data, final_name = data_base64, file_name

        # Auto-detect content_type if not provided
        if content_type is None:
            if is_patch or final_name.endswith((".patch", ".diff", ".txt")) or text is not None:
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"

        payload: dict[str, Any] = {
            "ids": [bug_id],
            "file_name": final_name,
            "summary": summary,
            "content_type": content_type,
            "data": b64_data,
            "is_patch": is_patch,
        }
        _set_if_given(payload, comment=comment)

        data = await self._request(
            "post", f"/bug/{bug_id}/attachment", json=payload, ok=(200, 201), what="upload attachment"
        )
        # Bugzilla returns {"ids": [<new attachment id>]}
        ids = data.get("ids") or list(data.get("attachments", {}).keys())
        return {"attachment_id": int(ids[0]) if ids else None, "bug_id": bug_id}

    async def tag_comment(
        self, comment_id: int, add: list[str] | None = None, remove: list[str] | None = None
    ) -> dict[str, Any]:
        """Add or remove tags on a bug comment via PUT /rest/bug/comment/(id)/tags.

        Returns:
            {"tags": [...]}
        """
        payload = {k: v for k, v in {"add": add, "remove": remove}.items() if v}
        tags = await self._request("put", f"/bug/comment/{comment_id}/tags", json=payload, what="tag comment")
        return {"tags": tags}

    async def close(self):
        """Close the async client"""
        await self.client.aclose()
