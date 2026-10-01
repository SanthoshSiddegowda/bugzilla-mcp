"""Bugzilla API client"""

import base64
import logging
import os
from typing import Any
import httpx

logger = logging.getLogger(__name__)

API_KEY_HEADER = "X-BUGZILLA-API-KEY"

# Bugzilla base URL -> whether that instance reads the API key header.
# Keyed by URL only (no secrets). Re-probed after a process restart.
_header_auth_support: dict[str, bool] = {}


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

    def _require_local_files(self) -> None:
        if not self.allow_local_files:
            raise PermissionError(
                "Reading or writing files on the server is only available in the local "
                "server (server_local.py). Use get_attachment to read attachments, and "
                "pass text or data_base64 to upload_attachment."
            )

    async def bug_attachments(self, bug_id: int) -> list[dict[str, Any]]:
        """List a bug's attachments (metadata only, no file data)"""
        headers, params = await self.auth()
        params["exclude_fields"] = "data"
        r = await self.client.get(
            url=f"{self.api_url}/bug/{bug_id}/attachment", headers=headers, params=params
        )
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )
        return r.json().get("bugs", {}).get(str(bug_id), [])

    async def get_attachment(self, attachment_id: int) -> dict[str, Any]:
        """Fetch one attachment including its base64 `data`"""
        headers, params = await self.auth()
        r = await self.client.get(
            url=f"{self.api_url}/bug/attachment/{attachment_id}", headers=headers, params=params
        )
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )
        att = r.json().get("attachments", {}).get(str(attachment_id))
        if not att:
            raise ValueError(f"Attachment {attachment_id} not found")
        return att

    async def download_attachments(
        self, bug_id: int, dest_dir: str | None = None
    ) -> list[dict[str, Any]]:
        """Download all attachments for a specific bug to a temporary directory.

        Args:
            bug_id: The ID of the bug.
            dest_dir: Optional destination directory. If not specified, a 'tmp'
                      directory in the project root will be used.

        Returns:
            A list of dicts containing attachment metadata and the local path:
            [{"id": 123, "file_name": "...", "path": "...", "size": 1024}]
        """
        self._require_local_files()
        headers, params = await self.auth()
        r = await self.client.get(
            url=f"{self.api_url}/bug/{bug_id}/attachment", headers=headers, params=params
        )

        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        data = r.json()
        bugs_data = data.get("bugs", {})
        attachments = (
            bugs_data.get(str(bug_id)) or bugs_data.get(bug_id) or []
        )

        if dest_dir is None:
            # Create a tmp directory in the project root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            dest_dir = os.path.join(project_root, "tmp")

        os.makedirs(dest_dir, exist_ok=True)

        downloaded = []
        for att in attachments:
            att_id = att.get("id")
            file_name = att.get("file_name")
            b64_data = att.get("data")

            if not b64_data:
                continue

            try:
                file_content = base64.b64decode(b64_data)
            except Exception as e:
                raise ValueError(f"Failed to decode attachment {att_id}: {e}")

            # Construct safe filename
            safe_file_name = os.path.basename(file_name)
            safe_file_name = f"{att_id}_{safe_file_name}"
            dest_path = os.path.join(dest_dir, safe_file_name)

            with open(dest_path, "wb") as f:
                f.write(file_content)

            downloaded.append(
                {
                    "id": att_id,
                    "bug_id": bug_id,
                    "file_name": file_name,
                    "content_type": att.get("content_type"),
                    "size": att.get("size"),
                    "path": dest_path,
                }
            )

        return downloaded

    async def download_attachment(
        self, attachment_id: int, dest_dir: str | None = None
    ) -> dict[str, Any]:
        """Download a specific attachment by its ID.

        Args:
            attachment_id: The ID of the attachment.
            dest_dir: Optional destination directory. If not specified, a 'tmp'
                      directory in the project root will be used.

        Returns:
            A dict containing attachment metadata and the local path:
            {"id": 123, "file_name": "...", "path": "...", "size": 1024}
        """
        self._require_local_files()
        headers, params = await self.auth()
        r = await self.client.get(
            url=f"{self.api_url}/bug/attachment/{attachment_id}",
            headers=headers, params=params,
        )

        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        data = r.json()
        attachments_data = data.get("attachments", {})
        att = attachments_data.get(str(attachment_id)) or attachments_data.get(
            attachment_id
        )

        if not att:
            raise ValueError(f"Attachment {attachment_id} not found in response")

        b64_data = att.get("data")
        if not b64_data:
            raise ValueError(f"No data field found in attachment {attachment_id}")

        if dest_dir is None:
            # Create a tmp directory in the project root
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            dest_dir = os.path.join(project_root, "tmp")

        os.makedirs(dest_dir, exist_ok=True)

        try:
            file_content = base64.b64decode(b64_data)
        except Exception as e:
            raise ValueError(f"Failed to decode attachment {attachment_id}: {e}")

        file_name = att.get("file_name")
        safe_file_name = os.path.basename(file_name)
        safe_file_name = f"{attachment_id}_{safe_file_name}"
        dest_path = os.path.join(dest_dir, safe_file_name)

        with open(dest_path, "wb") as f:
            f.write(file_content)

        return {
            "id": attachment_id,
            "bug_id": att.get("bug_id"),
            "file_name": file_name,
            "content_type": att.get("content_type"),
            "size": att.get("size"),
            "path": dest_path,
        }

    async def bugs_info(self, bug_ids: list[int]) -> list[dict[str, Any]]:
        """get information about multiple bugs in a single request"""
        if not bug_ids:
            return []

        # Join ids with commas
        ids_str = ",".join(map(str, bug_ids))
        headers, params = await self.auth()
        params["id"] = ids_str

        r = await self.client.get(url=f"{self.api_url}/bug", headers=headers, params=params)

        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch API with Status code: {r.status_code}"
            )

        return r.json().get("bugs", [])

    async def bugs_comments(self, bug_ids: list[int]) -> dict[str, list[dict[str, Any]]]:
        """fetch comments for multiple bugs in parallel using asyncio.gather"""
        if not bug_ids:
            return {}

        import asyncio

        async def fetch_one(bug_id: int):
            try:
                comments = await self.bug_comments(bug_id)
                return str(bug_id), comments
            except Exception as e:
                return str(bug_id), {"error": f"Failed to fetch comments: {e}"}

        tasks = [fetch_one(bid) for bid in bug_ids]
        results = await asyncio.gather(*tasks)
        return dict(results)

    async def bugs_analysis_context(self, bug_ids: list[int]) -> dict[str, Any]:
        """Gather bug info and comment previews in parallel to return a prompt-friendly analysis payload"""
        if not bug_ids:
            return {}

        # Fetch all bug details in a single request
        try:
            info_list = await self.bugs_info(bug_ids)
        except Exception as e:
            raise httpx.TransportError(f"Failed to gather batch bug info: {e}")

        # Fetch comments in parallel
        comments_dict = await self.bugs_comments(bug_ids)

        # Merge them into a structured dict mapping bug_id -> merged details
        merged = {}
        for info in info_list:
            bid = info.get("id")
            bid_str = str(bid)
            comments = comments_dict.get(bid_str, [])

            # Limit comments to most relevant to avoid token explosion
            comments_preview = []
            if len(comments) <= 4:
                comments_preview = comments
            else:
                comments_preview = (
                    comments[:2]
                    + [
                        {
                            "text": f"... [{len(comments)-4} comments omitted] ...",
                            "is_private": False,
                            "creator": "System",
                        }
                    ]
                    + comments[-2:]
                )

            merged[bid_str] = {
                "id": bid,
                "product": info.get("product"),
                "component": info.get("component"),
                "summary": info.get("summary"),
                "status": info.get("status"),
                "resolution": info.get("resolution"),
                "assigned_to": info.get("assigned_to"),
                "creator": info.get("creator"),
                "last_change_time": info.get("last_change_time"),
                "severity": info.get("severity"),
                "priority": info.get("priority"),
                "comments_count": len(comments),
                "comments_preview": comments_preview,
            }

        return merged

    async def bugs_stats_analysis(self, bug_ids: list[int]) -> dict[str, Any]:
        """Fetch bug info and perform high-level statistical analysis based on classifications and properties.

        Args:
            bug_ids: The list of bug IDs to analyze.

        Returns:
            A structured dict of counts and percentages of classifications, products, components,
            severity, priority, and assignees.
        """
        if not bug_ids:
            return {
                "total_bugs": 0,
                "classifications": {},
                "products": {},
                "components": {},
                "to_fix_severity": {},
                "to_fix_priority": {},
                "assignee_distribution": {},
            }

        info_list = await self.bugs_info(bug_ids)
        total = len(info_list)

        if total == 0:
            return {
                "total_bugs": 0,
                "classifications": {},
                "products": {},
                "components": {},
                "to_fix_severity": {},
                "to_fix_priority": {},
                "assignee_distribution": {},
            }

        # Initialize counts
        class_counts = {"to_fix": 0, "invalid": 0, "review_needed": 0}
        product_counts = {}
        component_counts = {}
        to_fix_severity = {}
        to_fix_priority = {}
        assignee_counts = {}

        for info in info_list:
            status = info.get("status", "")
            resolution = info.get("resolution", "")
            product = info.get("product", "Unknown")
            component = info.get("component", "Unknown")
            severity = info.get("severity", "Unknown")
            priority = info.get("priority", "Unknown")
            assigned_to = info.get("assigned_to", "unassigned")

            # Classification heuristics
            is_closed_invalid = (
                status in ["RESOLVED", "VERIFIED", "CLOSED"]
                and resolution in ["INVALID", "WONTFIX", "DUPLICATE", "WORKSFORME", "NOTABUG"]
            )
            is_active_valid = status in ["NEW", "ASSIGNED", "REOPENED", "UNCONFIRMED"]

            classification = "review_needed"
            if is_closed_invalid:
                classification = "invalid"
            elif is_active_valid:
                classification = "to_fix"
                # Severity and Priority breakdown specifically for "to_fix" bugs
                to_fix_severity[severity] = to_fix_severity.get(severity, 0) + 1
                to_fix_priority[priority] = to_fix_priority.get(priority, 0) + 1

            class_counts[classification] += 1
            product_counts[product] = product_counts.get(product, 0) + 1
            component_counts[component] = component_counts.get(component, 0) + 1
            assignee_counts[assigned_to] = assignee_counts.get(assigned_to, 0) + 1

        # Helper to compute counts and percentages
        def make_distribution(counts_dict: dict[str, int]) -> dict[str, dict[str, Any]]:
            dist = {}
            for key, val in counts_dict.items():
                pct = round((val / total) * 100, 2)
                dist[key] = {"count": val, "percentage": pct}
            return dist

        return {
            "total_bugs": total,
            "classifications": make_distribution(class_counts),
            "products": make_distribution(product_counts),
            "components": make_distribution(component_counts),
            "to_fix_severity": to_fix_severity,
            "to_fix_priority": to_fix_priority,
            "assignee_distribution": make_distribution(assignee_counts),
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
        if severity is not None:
            payload["severity"] = severity
        if priority is not None:
            payload["priority"] = priority
        if assigned_to is not None:
            payload["assigned_to"] = assigned_to
        if keywords:
            payload["keywords"] = keywords
        if target_milestone is not None:
            payload["target_milestone"] = target_milestone

        headers, params = await self.auth()
        r = await self.client.post(
            url=f"{self.api_url}/bug", headers=headers, params=params, json=payload
        )
        # Bugzilla answers 201 Created; accept 200 too for forks that differ
        if r.status_code not in (200, 201):
            raise httpx.TransportError(
                f"Failed to create bug with Status code: {r.status_code} — {r.text}"
            )
        return r.json()

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
    ) -> dict[str, Any]:
        """Update one or more bugs via PUT /rest/bug.

        Returns:
            {"bugs": [{"id": ..., "last_change_time": ...}]}
        """
        payload: dict[str, Any] = {"ids": ids}
        if status is not None:
            payload["status"] = status
        if resolution is not None:
            payload["resolution"] = resolution
        if assigned_to is not None:
            payload["assigned_to"] = assigned_to
        if severity is not None:
            payload["severity"] = severity
        if priority is not None:
            payload["priority"] = priority
        if whiteboard is not None:
            payload["whiteboard"] = whiteboard
        if comment is not None:
            payload["comment"] = {"body": comment, "is_private": comment_is_private}
        if dupe_of is not None:
            payload["dupe_of"] = dupe_of
        if target_milestone is not None:
            payload["target_milestone"] = target_milestone
        if version is not None:
            payload["version"] = version
        if summary is not None:
            payload["summary"] = summary
        if product is not None:
            payload["product"] = product
        if component is not None:
            payload["component"] = component
        if op_sys is not None:
            payload["op_sys"] = op_sys
        if platform is not None:
            payload["platform"] = platform
        if qa_contact is not None:
            payload["qa_contact"] = qa_contact
        if url is not None:
            payload["url"] = url
        if keywords is not None:
            payload["keywords"] = keywords
        if cc is not None:
            payload["cc"] = cc
        if see_also is not None:
            payload["see_also"] = see_also
        if blocks is not None:
            payload["blocks"] = blocks
        if depends_on is not None:
            payload["depends_on"] = depends_on
        if extra_fields is not None:
            payload.update(extra_fields)

        # Bugzilla REST update accepts the first id in the URL
        bug_id = ids[0]
        headers, params = await self.auth()
        r = await self.client.put(
            url=f"{self.api_url}/bug/{bug_id}", headers=headers, params=params, json=payload
        )
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to update bug with Status code: {r.status_code} — {r.text}"
            )
        return r.json()

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
        headers, params = await self.auth()
        if new_since is not None:
            params["new_since"] = new_since

        r = await self.client.get(
            url=f"{self.api_url}/bug/{bug_id}/history", headers=headers, params=params
        )
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch bug history with Status code: {r.status_code}"
            )
        bugs = r.json().get("bugs", [])
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
        headers, params = await self.auth()
        params["limit"] = limit
        params["offset"] = offset

        if product:
            params["product"] = product
        if component:
            params["component"] = component
        if status:
            params["status"] = status
        if resolution:
            params["resolution"] = resolution
        if assigned_to:
            params["assigned_to"] = assigned_to
        if creator:
            params["creator"] = creator
        if severity:
            params["severity"] = severity
        if priority:
            params["priority"] = priority
        if creation_time:
            params["creation_time"] = creation_time
        if last_change_time:
            params["last_change_time"] = last_change_time
        if keywords:
            params["keywords"] = keywords
        if version:
            params["version"] = version
        if target_milestone:
            params["target_milestone"] = target_milestone

        r = await self.client.get(url=f"{self.api_url}/bug", headers=headers, params=params)
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to search bugs with Status code: {r.status_code}"
            )

        bugs = r.json().get("bugs", [])
        # Return only essential fields for token efficiency
        essential_keys = {
            "id", "summary", "status", "resolution",
            "product", "component", "assigned_to", "priority", "severity",
            "creation_time", "last_change_time",
        }
        return [{k: b.get(k) for k in essential_keys} for b in bugs]

    async def bug_dependencies(self, bug_id: int) -> dict[str, Any]:
        """Fetch dependency info (blocks / depends_on) for a bug.

        Returns:
            {"id": ..., "blocks": [...], "depends_on": [...]}
        """
        headers, params = await self.auth()
        r = await self.client.get(url=f"{self.api_url}/bug/{bug_id}", headers=headers, params=params)
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch bug with Status code: {r.status_code}"
            )
        bug = r.json()["bugs"][0]
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
        """Traverse the chain of duplicate bugs until reaching the canonical root.

        Args:
            bug_id: Starting bug ID.
            max_depth: Maximum recursion depth to prevent infinite loops.

        Returns:
            Ordered list from child to root: [{"id", "summary", "dupe_of"}, ...]
        """
        chain: list[dict[str, Any]] = []
        visited: set[int] = set()
        current_id: int = bug_id
        depth: int = 0

        while current_id is not None and depth < max_depth:
            if current_id in visited:
                break
            visited.add(current_id)

            headers, params = await self.auth()
            r = await self.client.get(
                url=f"{self.api_url}/bug/{current_id}", headers=headers, params=params
            )
            if r.status_code != 200:
                raise httpx.TransportError(
                    f"Failed to fetch bug {current_id} with Status code: {r.status_code}"
                )
            bug = r.json()["bugs"][0]
            chain.append(
                {
                    "id": bug.get("id"),
                    "summary": bug.get("summary"),
                    "status": bug.get("status"),
                    "dupe_of": bug.get("dupe_of"),
                }
            )
            current_id = bug.get("dupe_of")
            depth += 1

        return chain

    async def get_user(
        self, names: list[str] | None = None, ids: list[int] | None = None
    ) -> list[dict[str, Any]]:
        """Look up Bugzilla users by login name(s) or user ID(s).

        Returns:
            List of user objects with id, real_name, name, email, can_login.
        """
        headers, params = await self.auth()
        if names:
            params["names"] = names
        if ids:
            params["ids"] = ids

        r = await self.client.get(url=f"{self.api_url}/user", headers=headers, params=params)
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch users with Status code: {r.status_code}"
            )
        return r.json().get("users", [])

    async def search_users(self, match: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for Bugzilla users by partial name or email (substring match).

        Returns:
            List of matching user objects.
        """
        headers, params = await self.auth()
        params["match"] = match
        params["limit"] = limit

        r = await self.client.get(url=f"{self.api_url}/user", headers=headers, params=params)
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to search users with Status code: {r.status_code}"
            )
        return r.json().get("users", [])

    async def list_products(self) -> list[dict[str, Any]]:
        """List all products that the authenticated user can access.

        Returns:
            List of product objects with id, name, description, is_active.
        """
        # First get accessible product IDs, then fetch their details
        headers, params = await self.auth()
        r = await self.client.get(
            url=f"{self.api_url}/product_accessible", headers=headers, params=params
        )
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to list products with Status code: {r.status_code}"
            )
        ids = r.json().get("ids", [])
        if not ids:
            return []

        headers, params = await self.auth()
        params["ids"] = ids
        r2 = await self.client.get(url=f"{self.api_url}/product", headers=headers, params=params)
        if r2.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch product details with Status code: {r2.status_code}"
            )
        products = r2.json().get("products", [])
        return [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "description": p.get("description"),
                "is_active": p.get("is_active"),
            }
            for p in products
        ]

    async def get_product_components(
        self, product_name: str
    ) -> dict[str, Any]:
        """Fetch components for a product by name.

        Returns:
            {"name": "...", "components": [{"name", "description", "default_assignee"}, ...]}
        """
        headers, params = await self.auth()
        params["names"] = product_name

        r = await self.client.get(url=f"{self.api_url}/product", headers=headers, params=params)
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to fetch product with Status code: {r.status_code}"
            )
        products = r.json().get("products", [])
        if not products:
            raise ValueError(f"Product '{product_name}' not found")

        product = products[0]
        components = [
            {
                "name": c.get("name"),
                "description": c.get("description"),
                "default_assignee": c.get("default_assignee"),
            }
            for c in product.get("components", [])
        ]
        return {"name": product.get("name"), "components": components}

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
            b64_data = data_base64
            if not file_name:
                raise ValueError("file_name is required with data_base64")
            final_name = file_name

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
        if comment is not None:
            payload["comment"] = comment

        headers, params = await self.auth()
        r = await self.client.post(
            url=f"{self.api_url}/bug/{bug_id}/attachment",
            headers=headers,
            params=params,
            json=payload,
        )

        if r.status_code not in (200, 201):
            raise httpx.TransportError(
                f"Failed to upload attachment with Status code: {r.status_code} — {r.text}"
            )

        # Bugzilla returns {"ids": [<new attachment id>]}
        data = r.json()
        ids = data.get("ids") or list(data.get("attachments", {}).keys())
        return {"attachment_id": int(ids[0]) if ids else None, "bug_id": bug_id}

    async def tag_comment(
        self, comment_id: int, add: list[str] | None = None, remove: list[str] | None = None
    ) -> dict[str, Any]:
        """Add or remove tags on a bug comment via PUT /rest/bug/comment/(id)/tags.

        Returns:
            {"tags": [...]}
        """
        payload: dict[str, Any] = {}
        if add:
            payload["add"] = add
        if remove:
            payload["remove"] = remove

        headers, params = await self.auth()
        r = await self.client.put(
            url=f"{self.api_url}/bug/comment/{comment_id}/tags",
            headers=headers, params=params,
            json=payload,
        )
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to tag comment with Status code: {r.status_code} — {r.text}"
            )
        return {"tags": r.json()}

    async def close(self):
        """Close the async client"""
        await self.client.aclose()



