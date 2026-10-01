# Bugzilla MCP — Proposed Tools from Official Documentation

This document identifies **new MCP tools** that can be added to the Bugzilla MCP server, derived from the official [Bugzilla 5.2 WebService API Reference](https://bugzilla.readthedocs.io/en/5.2/api/index.html).

For each tool, you will find the **API endpoint**, **use case for automation**, and the **input/output contract** that the tool will expose to agents.

---

## 1. Bug Lifecycle Management

### 1.1 `create_bug`
**API**: `POST /rest/bug`

**Automation Use Case**: Automatically file a new bug from an agent's analysis without human intervention.

- An agent analyzing logs detects a regression and files it directly.
- A CI/CD pipeline creates a bug when a test suite fails repeatedly.

**Agent Prompt Example**:
> "Create a P1 bug in the Firefox product under the Networking component. Summary: 'HTTP/3 connection drops on slow networks'. Version: 120.0."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `product` | ✅ | Product to file under |
| `component` | ✅ | Component to file under |
| `summary` | ✅ | Short summary of the bug |
| `version` | ✅ | Version the bug was reported against |
| `description` | ✅ | Initial comment / steps to reproduce |
| `severity` | ❌ | `blocker`, `critical`, `major`, `normal`, `minor`, `trivial`, `enhancement` |
| `priority` | ❌ | `P1` – `P5` |
| `assigned_to` | ❌ | Login email of initial assignee |

**Returns**: `{ "id": <new_bug_id> }`

---

### 1.2 `update_bug`
**API**: `PUT /rest/bug/(id)`

**Automation Use Case**: Modify bug fields based on agent analysis or external events.

- Auto-reassign bugs based on product/component ownership lookup.
- Change status to `ASSIGNED` when an agent starts working on a bug.
- Set `whiteboard` field with AI-generated triage notes.
- Auto-escalate a severity when similar bugs are opened in rapid succession.
- Mark a bug as `RESOLVED DUPLICATE` when a duplicate is detected.

**Agent Prompt Example**:
> "Update bug 12345: change status to ASSIGNED, set assigned_to=alice@example.com, and add a whiteboard note '[AI-Triage] Confirmed by log analysis'."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `ids` | ✅ | List of bug IDs to update |
| `status` | ❌ | New status value |
| `resolution` | ❌ | e.g. `FIXED`, `DUPLICATE`, `INVALID` |
| `assigned_to` | ❌ | New assignee email |
| `severity` | ❌ | New severity |
| `priority` | ❌ | New priority |
| `whiteboard` | ❌ | Freeform notes field |
| `comment` | ❌ | Comment to append during update |
| `dupe_of` | ❌ | ID of the original bug (for DUPLICATE) |
| `target_milestone` | ❌ | Milestone to associate |

**Returns**: `{ "bugs": [{ "id": 12345, "last_change_time": "..." }] }`

---

### 1.3 `bug_history`
**API**: `GET /rest/bug/(id)/history`

**Automation Use Case**: Understand what changed and when — critical for change attribution and audit reports.

- Detect if a bug was recently re-opened after being marked RESOLVED.
- Find who last changed severity or priority.
- Surface bugs that have been in `NEW` status with no activity for > 30 days.
- Detect patterns like repeated reassignment (indicating unclear ownership).

**Agent Prompt Example**:
> "Get the full change history for bug 12345. Tell me who changed the priority and when."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `bug_id` | ✅ | The bug ID |
| `new_since` | ❌ | Only return changes since this datetime |

**Returns**: List of `{ "when", "who", "changes": [{ "field_name", "removed", "added" }] }`

---

## 2. Dependency & Relationship Analysis

### 2.1 `bug_dependencies`
**API**: Included in `GET /rest/bug/(id)` via `blocks` and `depends_on` fields.

**Automation Use Case**: Map bug dependency graphs to understand blast radius and prioritize fixes.

- Identify which bugs are **blockers** for a release milestone.
- Find bugs that become unblocked once a specific bug is fixed.
- Detect circular dependencies.

**Agent Prompt Example**:
> "Fetch bug 12345 and show me which bugs it blocks and which bugs it depends on."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `bug_id` | ✅ | The bug ID to inspect |

**Returns**: `{ "id": 12345, "blocks": [...], "depends_on": [...] }`

---

### 2.2 `duplicate_chain`
**API**: Uses `dupe_of` field from `GET /rest/bug/(id)`

**Automation Use Case**: Traverse the chain of duplicate bugs to find the original canonical bug.

- Follow duplicates until reaching the master bug.
- Consolidate comment summaries from all duplicates.
- Identify which product/version clusters report the same root issue.

**Agent Prompt Example**:
> "Bug 99999 is a duplicate. Traverse all its duplicates recursively and return the canonical root bug."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `bug_id` | ✅ | Starting bug ID |
| `max_depth` | ❌ | Maximum recursion depth (default: 10) |

**Returns**: Full chain of duplicate IDs from child to root.

---

## 3. Search & Advanced Queries

### 3.1 `bugs_advanced_search`
**API**: `GET /rest/bug` with structured filters

**Automation Use Case**: Run structured searches that go beyond quicksearch syntax.

- Find all `P1` bugs with severity `critical` that have not been updated in 7 days.
- Find all bugs in a specific product assigned to a specific user.
- Search by date ranges, versions, OS, platform, keywords.
- Combine multiple criteria (AND logic) for targeted queries.

**Agent Prompt Example**:
> "Find all unresolved bugs in Firefox's Networking component, severity=critical, assigned to nobody@mozilla.org, created after 2024-01-01."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `product` | ❌ | Product name(s) |
| `component` | ❌ | Component name(s) |
| `status` | ❌ | Bug status(es) |
| `resolution` | ❌ | Bug resolution(s) |
| `assigned_to` | ❌ | Assignee login |
| `creator` | ❌ | Reporter login |
| `severity` | ❌ | Severity level(s) |
| `priority` | ❌ | Priority level(s) |
| `creation_time` | ❌ | Created after/before datetime |
| `last_change_time` | ❌ | Changed after/before datetime |
| `keywords` | ❌ | Keyword(s) on the bug |
| `version` | ❌ | Version filed against |
| `target_milestone` | ❌ | Target milestone |
| `limit` | ❌ | Max results (default: 50) |
| `offset` | ❌ | Pagination offset |

**Returns**: List of matching bugs (with essential fields only to save tokens).

---

## 4. User Information

### 4.1 `get_user`
**API**: `GET /rest/user?names=user@email.com` or `GET /rest/user/(id)`

**Automation Use Case**: Look up user identities, real names, and group memberships for assignments and routing.

- Validate an email address before assigning a bug to a user.
- Look up a user's real name from their Bugzilla login for readability in reports.
- Determine if a user has admin privileges by checking groups.

**Agent Prompt Example**:
> "Who is developer@example.com? What is their real name and are they in any admin groups?"

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `names` | ❌ | List of login names (emails) to look up |
| `ids` | ❌ | List of user IDs to look up |

**Returns**: `[{ "id", "real_name", "name", "email", "can_login", "groups" }]`

---

### 4.2 `search_users`
**API**: `GET /rest/user?match=partial_name`

**Automation Use Case**: Find matching users by partial name or email for auto-suggest and assignment workflows.

- An agent looking for an owner for a Networking component bug can search for "network" to find relevant developers.
- Auto-populate CC list from team membership.

**Agent Prompt Example**:
> "Search for Bugzilla users matching 'alice'."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `match` | ✅ | Partial name or email to search |
| `limit` | ❌ | Max results |

**Returns**: List of matching user objects.

---

## 5. Products & Components Discovery

### 5.1 `list_products`
**API**: `GET /rest/product_accessible` or `GET /rest/product_enterable`

**Automation Use Case**: Discover what products and components are available before filing or routing bugs.

- A new bug's product can be auto-suggested from a list of accessible products.
- Validate that a product/component pair exists before creating a bug.

**Agent Prompt Example**:
> "List all products I can file bugs in."

**Inputs**: None (uses authenticated session)

**Returns**: `[{ "id", "name", "description", "is_active" }]`

---

### 5.2 `get_product_components`
**API**: `GET /rest/product/(id)` (includes components)

**Automation Use Case**: List available components for a given product to enable accurate bug routing.

- Auto-classify a bug to the right component using component descriptions + LLM reasoning.
- Validate component names before bug creation.

**Agent Prompt Example**:
> "List all components for the Firefox product."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `product_name` | ✅ | Product name or ID |

**Returns**: `{ "name": "Firefox", "components": [{ "name", "description", "default_assignee" }] }`

---

## 6. Attachment Upload

### 6.1 `upload_attachment`
**API**: `POST /rest/bug/(id)/attachment`

**Automation Use Case**: Upload files, patches, or log outputs to bugs directly from an agent workflow.

- An agent that auto-generates a patch can upload it to the bug immediately.
- A CI runner can upload test failure logs or screenshots as attachments.
- Upload repro cases in script format.

**Agent Prompt Example**:
> "Upload the file /tmp/crash_log.txt as an attachment to bug 12345 with the description 'Crash log from reproduced run'."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `bug_id` | ✅ | Bug to attach to |
| `file_path` | ✅ | Local file path to upload |
| `file_name` | ❌ | Override filename (defaults to basename) |
| `summary` | ✅ | Short description of the attachment |
| `content_type` | ❌ | MIME type (auto-detected if omitted) |
| `comment` | ❌ | Comment to add when uploading |
| `is_patch` | ❌ | Whether this is a patch file |

**Returns**: `{ "attachment_id": <id>, "bug_id": <bug_id> }`

---

## 7. Comment Tagging & Organization

### 7.1 `tag_comment`
**API**: `PUT /rest/bug/comment/(comment_id)/tags`

**Automation Use Case**: Tag comments with metadata for filtering, reporting, or workflow tracking.

- Tag comments that contain a fix with `"fix-candidate"`.
- Tag comments with repro steps as `"reproduction"`.
- Mark AI-generated comments with `"ai-generated"` for human review.

**Agent Prompt Example**:
> "Tag comment 5001 on bug 12345 with the tag 'fix-candidate'."

**Inputs**:
| Field | Required | Description |
|---|---|---|
| `comment_id` | ✅ | ID of the comment to tag |
| `add` | ❌ | List of tags to add |
| `remove` | ❌ | List of tags to remove |

**Returns**: `{ "tags": [...] }`

---

## Summary: Recommended Priority Order

| Priority | Tool | Reason |
|---|---|---|
| 🔴 P1 | `update_bug` | Core action for full automation — close, assign, escalate |
| 🔴 P1 | `create_bug` | File bugs programmatically from CI/agents |
| 🟠 P2 | `bug_history` | Audit, activity detection, staleness detection |
| 🟠 P2 | `bugs_advanced_search` | Structured queries replacing quicksearch for precision |
| 🟡 P3 | `get_product_components` | Enable smart routing before bug creation |
| 🟡 P3 | `upload_attachment` | Close the loop: agent uploads generated patches/logs |
| 🟢 P4 | `get_user` / `search_users` | Validate and suggest assignees |
| 🟢 P4 | `bug_dependencies` | Dependency graph analysis for sprint planning |
| 🟢 P4 | `duplicate_chain` | Deduplication and canonical bug tracing |
| 🔵 P5 | `list_products` | Discovery tool for onboarding/validation |
| 🔵 P5 | `tag_comment` | Semantic tagging for workflow organization |
