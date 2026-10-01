# LLM Agent Guide: Solving Bugs with Bugzilla MCP

This guide is the operating manual for any autonomous LLM agent using the **Bugzilla MCP Server** to discover, analyze, triage, fix, and close single or multiple bugs.

> **26 tools available.** All tools are async. All write operations require a valid `api_key` and `bugzilla_url`.

---

## 🧭 Workflow Overview

```
┌──────────────────────────────────────────────────────────────┐
│  1. DISCOVER    →  2. TRIAGE    →  3. CONTEXT   →  4. ACT   │
│  Search &          Classify &       Deep-dive        Fix,    │
│  explore           prioritize       & inspect       update,  │
│  bugs              bugs             attachments      close   │
└──────────────────────────────────────────────────────────────┘
```

**Tool categories by workflow phase:**

| Phase | Tools |
|---|---|
| Discovery & Search | `bugs_quicksearch`, `bugs_advanced_search`, `learn_quicksearch_syntax` |
| Triage & Analytics | `classify_bugs_heuristics`, `analyze_bugs_statistics`, `bugs_analysis_context` |
| Detail Retrieval | `bug_info`, `bug_comments`, `bug_history`, `bug_dependencies`, `duplicate_chain` |
| Attachments | `download_attachments`, `download_attachment`, `upload_attachment` |
| Write & Update | `create_bug`, `update_bug`, `add_comment`, `tag_comment` |
| Discovery Tools | `list_products`, `get_product_components`, `get_user`, `search_users` |
| Info | `server_url`, `bug_url` |

---

## 🧰 Tools Reference

### 🔍 Discovery & Search

**`bugs_quicksearch(query)`**
Run Google-like quicksearch queries (free-text, product, component, status).
- Returns token-optimized subset: `id`, `summary`, `status`, `resolution`, `assigned_to`, `last_change_time`.
- Use `learn_quicksearch_syntax` for advanced query syntax.

**`bugs_advanced_search(...)`** *(new)*
Structured multi-criteria search using AND logic. More reliable than quicksearch for automation.
- Filter by `product`, `component`, `status`, `resolution`, `assigned_to`, `creator`, `severity`, `priority`, `creation_time`, `last_change_time`, `keywords`, `version`, `target_milestone`.
- Supports `limit` (default: 50) and `offset` for pagination.
- Returns token-optimized essential fields only.

**`learn_quicksearch_syntax()`**
Returns the full quicksearch documentation for constructing complex queries.

---

### 📊 Triage & Analytics

**`classify_bugs_heuristics(ids)`**
Classifies a list of bug IDs into three categories based on status/resolution:
- `to_fix` — Active bugs requiring attention (`NEW`, `ASSIGNED`, `REOPENED`).
- `invalid` — Closed/resolved bugs that need no action (`RESOLVED WONTFIX`, `DUPLICATE`, etc.).
- `review_needed` — Edge cases, ambiguous states.

**`analyze_bugs_statistics(ids)`**
Server-side aggregation on a batch of bug IDs. Returns:
- Triage classification counts & percentages.
- Product/component distribution.
- Severity & priority distribution for `to_fix` bugs.
- Per-assignee workload metrics.

**`bugs_analysis_context(ids)`**
Fetches compressed bug detail + comments for multiple bug IDs in a single parallelized call.
- Comment threads > 4 entries are auto-compressed to first 2 + last 2 with omission marker.
- Use this **before** `bug_comments` to preserve context window.

**`bugs_info(ids)` / `bugs_comments(ids)`**
Batch-fetch raw metadata or comments for a list of bug IDs (minimal processing).

---

### 📖 Detail Retrieval

**`bug_info(id)`**
Full uncompressed metadata for a single bug (all fields).

**`bug_comments(id, include_private_comments=False)`**
Full comment thread for a single bug. Set `include_private_comments=True` to include private comments.

**`bug_history(bug_id, new_since=None)`** *(new)*
Returns the complete change audit trail for a bug.
- Each entry shows: `when`, `who`, `changes: [{field_name, removed, added}]`.
- Use `new_since="YYYY-MM-DDTHH:MM:SSZ"` to filter to recent changes only.
- Useful for detecting staleness (no activity in 30 days), ownership changes, priority escalations.

**`bug_dependencies(bug_id)`** *(new)*
Returns `blocks` and `depends_on` ID lists for a bug.
- Use to map the dependency graph and find release blockers.

**`duplicate_chain(bug_id, max_depth=10)`** *(new)*
Traverses the `dupe_of` chain from a bug to its canonical root.
- Returns ordered list: `[{id, summary, status, dupe_of}, ...]` from child to root.
- Stops at root (where `dupe_of=null`) or at `max_depth`.

---

### 📎 Attachments

**`download_attachments(bug_id)`**
Downloads and decodes all attachments for a bug. Saves to `tmp/`. Returns local file paths.

**`download_attachment(attachment_id)`**
Downloads and decodes a single attachment by its ID.

**`upload_attachment(bug_id, file_path, summary, ...)`** *(new)*
Uploads a local file to a bug as an attachment.
- Reads the file, base64-encodes it, and POSTs to `/rest/bug/(id)/attachment`.
- `content_type` is auto-detected from file extension if not provided.
- Set `is_patch=True` for patch/diff files.
- Optional `comment` to append a comment alongside the upload.
- Returns `{attachment_id, bug_id}`.

---

### ✏️ Write & Update

**`create_bug(product, component, summary, version, description, ...)`** *(new)*
Files a new bug in Bugzilla.
- Required: `product`, `component`, `summary`, `version`, `description`.
- Optional: `severity`, `priority`, `assigned_to`, `keywords`, `target_milestone`.
- Returns `{"id": <new_bug_id>}`.

**`update_bug(ids, ...)`** *(new)*
Updates one or more bugs in a single API call. Supports:
- `status` — Move to `NEW`, `ASSIGNED`, `RESOLVED`, etc.
- `resolution` — `FIXED`, `INVALID`, `WONTFIX`, `DUPLICATE`, etc.
- `assigned_to` — Reassign to a user's login email.
- `severity`, `priority` — Escalate or de-escalate.
- `whiteboard` — Set free-text triage notes.
- `comment` + `comment_is_private` — Append a comment atomically.
- `dupe_of` — Set when `resolution=DUPLICATE`.
- `target_milestone` — Associate with a release.

**`add_comment(bug_id, comment, is_private=False)`**
Posts a comment to a specific bug. Set `is_private=True` for internal notes.

**`tag_comment(comment_id, add=[], remove=[])`** *(new)*
Add or remove tags on a specific bug comment for semantic labelling.
- Suggested tags: `fix-candidate`, `ai-generated`, `reproduction`, `needs-review`, `verified`.
- Returns the current tag list on the comment.

---

### 👥 User Management

**`get_user(names=[], ids=[])`** *(new)*
Look up Bugzilla user profiles by login email(s) or user ID(s).
- Returns: `id`, `real_name`, `name`, `email`, `can_login`.
- Use to validate an assignee before calling `update_bug`.

**`search_users(match, limit=10)`** *(new)*
Search for users by partial name or email (substring match).
- Returns matching user objects.
- Use for auto-suggest and CC-list population.

---

### 🗂 Product & Component Discovery

**`list_products()`** *(new)*
Lists all Bugzilla products accessible to the current user.
- Returns `id`, `name`, `description`, `is_active` for each product.
- Use before `create_bug` to validate product names.

**`get_product_components(product_name)`** *(new)*
Lists all components for a given product name.
- Returns `{name, description, default_assignee}` per component.
- Use to pick the right component before filing a bug.

---

### ℹ️ Server Info

**`server_url()`** — Returns the configured Bugzilla instance URL.
**`bug_url(bug_id)`** — Returns the direct web browser URL for a bug.

---

## 🚀 Playbooks

### Playbook A: Triaging & Resolving a Single Bug

```
1. bug_info(id)                          # Understand status, product, component
2. bug_comments(id)                      # Read full discussion history
3. bug_history(id)                       # Check what changed and who touched it
4. bug_dependencies(id)                  # Check if it blocks other bugs
5. download_attachments(id)              # Get crash logs, patches, screenshots
   → Analyse files in tmp/
6. [Fix the code locally]
7. upload_attachment(id, "fix.patch",    # Upload your patch to the bug
       summary="Agent-generated fix",
       is_patch=True)
8. update_bug(ids=[id],                  # Close the bug in one call
       status="RESOLVED",
       resolution="FIXED",
       comment="Fixed by adjusting config.py L42. Patch attached.")
9. tag_comment(comment_id,              # Tag the closing comment
       add=["ai-generated", "fix-candidate"])
```

---

### Playbook B: Bulk Triage of Multiple Bugs

```
1. analyze_bugs_statistics(ids=[...])    # High-level breakdown: severity, product, assignee
2. classify_bugs_heuristics(ids=[...])  # Split into to_fix / invalid / review_needed
3. bugs_analysis_context(ids=[to_fix])  # Token-safe context for active bugs
4. For each to_fix bug → run Playbook A
```

---

### Playbook C: Filing a New Bug from Agent Analysis

```
1. list_products()                               # Discover available products
2. get_product_components("Firefox")             # Verify component names
3. search_users("alice")                         # Find the right owner
4. create_bug(
       product="Firefox",
       component="Networking",
       summary="HTTP/3 drops on slow network",
       version="121.0",
       description="Steps:\n1. ...",
       severity="critical",
       priority="P1",
       assigned_to="alice@example.com"
   )
→ Returns {"id": <new_bug_id>}
```

---

### Playbook D: Deduplication Audit

```
1. bugs_advanced_search(                          # Find potential duplicates
       product=["Firefox"],
       status=["RESOLVED"],
       resolution=["DUPLICATE"],
       limit=100
   )
2. For each DUPLICATE bug:
       duplicate_chain(bug_id)                    # Trace to canonical root
3. Report: how many bugs cluster around each root
```

---

### Playbook E: Staleness & Inactivity Audit

```
1. bugs_advanced_search(                          # Find stale open bugs
       status=["NEW", "ASSIGNED"],
       last_change_time="<30-days-ago ISO date>"
   )
2. For each stale bug:
       bug_history(bug_id)                        # Confirm no hidden activity
3. update_bug(
       ids=[stale_id],
       whiteboard="[AI-Audit] No activity for 30+ days. Needs triage.",
       comment="Flagged by automated staleness audit."
   )
```

---

## ⚠️ Agent Best Practices

| Rule | Why |
|---|---|
| Always call `bugs_advanced_search` or `bugs_quicksearch` first | Never guess bug IDs |
| Use `bugs_analysis_context` for batch > 3 bugs | Prevents context window overflow |
| Validate users with `get_user` before `update_bug(assigned_to=...)` | Avoids failed assignment |
| Validate product/component with `list_products` + `get_product_components` before `create_bug` | Prevents 400 errors |
| Set `comment` inside `update_bug` instead of calling `add_comment` separately | Saves one API round-trip |
| Tag AI-generated comments with `tag_comment(add=["ai-generated"])` | Makes them reviewable by humans |
| Always check `bug_dependencies` before closing a blocker | Prevents blocking other teams |
| Use `duplicate_chain` before resolving as DUPLICATE | Ensures you point to the actual root |
