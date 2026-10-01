"""Bugzilla API client"""

import base64
import os
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
        r = await self.client.get(
            url=f"{self.api_url}/bug/{bug_id}/attachment", params=self.params
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
        r = await self.client.get(
            url=f"{self.api_url}/bug/attachment/{attachment_id}",
            params=self.params,
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
        params = self.params.copy()
        params["id"] = ids_str

        r = await self.client.get(url=f"{self.api_url}/bug", params=params)

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
            except Exception:
                return str(bug_id), []

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

        r = await self.client.post(
            url=f"{self.api_url}/bug", params=self.params, json=payload
        )
        if r.status_code != 200:
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
        r = await self.client.put(
            url=f"{self.api_url}/bug/{bug_id}", params=self.params, json=payload
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
        params = dict(self.params)
        if new_since is not None:
            params["new_since"] = new_since

        r = await self.client.get(
            url=f"{self.api_url}/bug/{bug_id}/history", params=params
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
        params: dict[str, Any] = dict(self.params)
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

        r = await self.client.get(url=f"{self.api_url}/bug", params=params)
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
        r = await self.client.get(url=f"{self.api_url}/bug/{bug_id}", params=self.params)
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

            r = await self.client.get(
                url=f"{self.api_url}/bug/{current_id}", params=self.params
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
        params: dict[str, Any] = dict(self.params)
        if names:
            params["names"] = names
        if ids:
            params["ids"] = ids

        r = await self.client.get(url=f"{self.api_url}/user", params=params)
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
        params: dict[str, Any] = dict(self.params)
        params["match"] = match
        params["limit"] = limit

        r = await self.client.get(url=f"{self.api_url}/user", params=params)
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
        r = await self.client.get(
            url=f"{self.api_url}/product_accessible", params=self.params
        )
        if r.status_code != 200:
            raise httpx.TransportError(
                f"Failed to list products with Status code: {r.status_code}"
            )
        ids = r.json().get("ids", [])
        if not ids:
            return []

        params: dict[str, Any] = dict(self.params)
        params["ids"] = ids
        r2 = await self.client.get(url=f"{self.api_url}/product", params=params)
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
        params: dict[str, Any] = dict(self.params)
        params["names"] = product_name

        r = await self.client.get(url=f"{self.api_url}/product", params=params)
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
        file_path: str,
        summary: str,
        file_name: str | None = None,
        content_type: str | None = None,
        comment: str | None = None,
        is_patch: bool = False,
    ) -> dict[str, Any]:
        """Upload a local file as an attachment to a bug via POST /rest/bug/(id)/attachment.

        Returns:
            {"attachment_id": ..., "bug_id": ...}
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        final_name = file_name or os.path.basename(file_path)

        with open(file_path, "rb") as fh:
            raw = fh.read()

        b64_data = base64.b64encode(raw).decode("utf-8")

        # Auto-detect content_type if not provided
        if content_type is None:
            if is_patch or final_name.endswith(".patch") or final_name.endswith(".diff"):
                content_type = "text/plain"
            elif final_name.endswith(".txt"):
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

        r = await self.client.post(
            url=f"{self.api_url}/bug/{bug_id}/attachment",
            params=self.params,
            json=payload,
        )
        if r.status_code != 201:
            raise httpx.TransportError(
                f"Failed to upload attachment with Status code: {r.status_code} — {r.text}"
            )
        data = r.json()
        attachments = data.get("attachments", {})
        attachment_id = list(attachments.keys())[0] if attachments else None
        return {"attachment_id": int(attachment_id) if attachment_id else None, "bug_id": bug_id}

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

        r = await self.client.put(
            url=f"{self.api_url}/bug/comment/{comment_id}/tags",
            params=self.params,
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



