"""Shared pytest fixtures for Bugzilla MCP tests"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import bugzilla_mcp.utils as utils
from bugzilla_mcp.utils import Bugzilla


# Sample bug data
SAMPLE_BUG = {
    "id": 12345,
    "product": "Firefox",
    "component": "General",
    "summary": "Test bug summary",
    "status": "NEW",
    "resolution": "",
    "assigned_to": "developer@example.com",
    "creator": "reporter@example.com",
    "creation_time": "2023-01-15T10:30:00Z",
    "last_change_time": "2023-01-20T15:45:00Z",
    "priority": "P2",
    "severity": "normal",
    "version": "120.0",
}

# Sample bug API response
SAMPLE_BUG_RESPONSE = {
    "bugs": [SAMPLE_BUG]
}

# Sample comments
SAMPLE_COMMENTS = [
    {
        "id": 1001,
        "bug_id": 12345,
        "creator": "reporter@example.com",
        "creation_time": "2023-01-15T10:30:00Z",
        "text": "This is the first public comment",
        "is_private": False,
    },
    {
        "id": 1002,
        "bug_id": 12345,
        "creator": "developer@example.com",
        "creation_time": "2023-01-16T14:20:00Z",
        "text": "This is a private comment",
        "is_private": True,
    },
    {
        "id": 1003,
        "bug_id": 12345,
        "creator": "qa@example.com",
        "creation_time": "2023-01-17T09:15:00Z",
        "text": "This is another public comment",
        "is_private": False,
    },
]

# Sample comments API response
SAMPLE_COMMENTS_RESPONSE = {
    "bugs": {
        "12345": {
            "comments": SAMPLE_COMMENTS
        }
    }
}

# Sample search results
SAMPLE_SEARCH_RESULTS = {
    "bugs": [
        {
            "id": 12345,
            "product": "Firefox",
            "component": "General",
            "assigned_to": "developer@example.com",
            "status": "NEW",
            "resolution": "",
            "summary": "Test bug 1",
            "last_change_time": "2023-01-20T15:45:00Z",
        },
        {
            "id": 12346,
            "product": "Firefox",
            "component": "CSS",
            "assigned_to": "css-dev@example.com",
            "status": "RESOLVED",
            "resolution": "FIXED",
            "summary": "Test bug 2",
            "last_change_time": "2023-01-19T10:00:00Z",
        },
    ]
}

# Sample add comment response
SAMPLE_ADD_COMMENT_RESPONSE = {
    "id": 2001
}

# Sample attachments responses
SAMPLE_ATTACHMENTS_RESPONSE = {
    "bugs": {
        "12345": [
            {
                "id": 9001,
                "bug_id": 12345,
                "file_name": "test_attachment.txt",
                "summary": "Sample test attachment",
                "content_type": "text/plain",
                "size": 13,
                "creation_time": "2023-01-18T11:00:00Z",
                "last_change_time": "2023-01-18T11:00:00Z",
                "is_private": False,
                "data": "SGVsbG8sIFdvcmxkIQ=="  # Base64 encoded "Hello, World!"
            }
        ]
    }
}

SAMPLE_SINGLE_ATTACHMENT_RESPONSE = {
    "attachments": {
        "9001": {
            "id": 9001,
            "bug_id": 12345,
            "file_name": "test_attachment.txt",
            "summary": "Sample test attachment",
            "content_type": "text/plain",
            "size": 13,
            "creation_time": "2023-01-18T11:00:00Z",
            "last_change_time": "2023-01-18T11:00:00Z",
            "is_private": False,
            "data": "SGVsbG8sIFdvcmxkIQ=="  # Base64 encoded "Hello, World!"
        }
    }
}


@pytest.fixture
def mock_bugzilla_client():
    """Create a mock Bugzilla client instance"""
    client = MagicMock(spec=Bugzilla)
    client.base_url = "https://bugzilla.mozilla.org"
    client.api_url = "https://bugzilla.mozilla.org/rest"
    client.api_key = "test-api-key"
    client.params = {"api_key": "test-api-key"}
    
    # Setup async mock methods
    client.bug_info = AsyncMock(return_value=SAMPLE_BUG)
    client.bug_comments = AsyncMock(return_value=SAMPLE_COMMENTS)
    client.add_comment = AsyncMock(return_value=SAMPLE_ADD_COMMENT_RESPONSE)
    client.download_attachments = AsyncMock(return_value=[
        {
            "id": 9001,
            "bug_id": 12345,
            "file_name": "test_attachment.txt",
            "content_type": "text/plain",
            "size": 13,
            "path": "/mock/path/tmp/9001_test_attachment.txt"
        }
    ])
    client.download_attachment = AsyncMock(return_value={
        "id": 9001,
        "bug_id": 12345,
        "file_name": "test_attachment.txt",
        "content_type": "text/plain",
        "size": 13,
        "path": "/mock/path/tmp/9001_test_attachment.txt"
    })
    client.bugs_info = AsyncMock(return_value=[SAMPLE_BUG])
    client.bugs_comments = AsyncMock(return_value={"12345": SAMPLE_COMMENTS})
    client.bugs_analysis_context = AsyncMock(return_value={
        "12345": {
            "id": 12345,
            "summary": "Test bug summary",
            "product": "Firefox",
            "component": "General",
            "status": "NEW",
            "resolution": "",
            "comments_count": len(SAMPLE_COMMENTS),
            "comments_preview": SAMPLE_COMMENTS
        }
    })
    client.bugs_stats_analysis = AsyncMock(return_value={
        "total_bugs": 1,
        "classifications": {"to_fix": {"count": 1, "percentage": 100.0}},
        "products": {"Firefox": {"count": 1, "percentage": 100.0}},
        "components": {"General": {"count": 1, "percentage": 100.0}},
        "to_fix_severity": {"normal": 1},
        "to_fix_priority": {"P2": 1},
        "assignee_distribution": {"developer@example.com": {"count": 1, "percentage": 100.0}},
    })
    client.close = AsyncMock()

    # New tools mocks
    client.create_bug = AsyncMock(return_value={"id": 99999})
    client.update_bug = AsyncMock(return_value={
        "bugs": [{"id": 12345, "last_change_time": "2024-01-20T10:00:00Z", "changes": []}]
    })
    client.bug_history = AsyncMock(return_value=[
        {
            "when": "2024-01-20T10:00:00Z",
            "who": "dev@example.com",
            "changes": [
                {"field_name": "priority", "removed": "P3", "added": "P1"},
            ],
        }
    ])
    client.bugs_advanced_search = AsyncMock(return_value=[
        {
            "id": 12345,
            "summary": "Test bug summary",
            "status": "NEW",
            "resolution": "",
            "product": "Firefox",
            "component": "General",
            "assigned_to": "developer@example.com",
            "priority": "P2",
            "severity": "normal",
            "creation_time": "2023-01-15T10:30:00Z",
            "last_change_time": "2023-01-20T15:45:00Z",
        }
    ])
    client.bug_dependencies = AsyncMock(return_value={
        "id": 12345,
        "summary": "Test bug summary",
        "status": "NEW",
        "blocks": [12346, 12347],
        "depends_on": [12300],
    })
    client.duplicate_chain = AsyncMock(return_value=[
        {"id": 99999, "summary": "Dup bug", "status": "RESOLVED", "dupe_of": 12345},
        {"id": 12345, "summary": "Root bug", "status": "RESOLVED", "dupe_of": None},
    ])
    client.get_user = AsyncMock(return_value=[
        {"id": 42, "real_name": "Alice Dev", "name": "alice@example.com",
         "email": "alice@example.com", "can_login": True}
    ])
    client.search_users = AsyncMock(return_value=[
        {"id": 42, "real_name": "Alice Dev", "name": "alice@example.com",
         "email": "alice@example.com", "can_login": True}
    ])
    client.list_products = AsyncMock(return_value=[
        {"id": 1, "name": "Firefox", "description": "Firefox Browser", "is_active": True},
        {"id": 2, "name": "Thunderbird", "description": "Thunderbird Email", "is_active": True},
    ])
    client.get_product_components = AsyncMock(return_value={
        "name": "Firefox",
        "components": [
            {"name": "General", "description": "General Firefox issues",
             "default_assignee": "nobody@example.com"},
            {"name": "Networking", "description": "Network issues",
             "default_assignee": "net-dev@example.com"},
        ],
    })
    client.upload_attachment = AsyncMock(return_value={"attachment_id": 8001, "bug_id": 12345})
    client.tag_comment = AsyncMock(return_value={"tags": ["fix-candidate", "ai-generated"]})

    # Mock the httpx client
    client.client = MagicMock()
    client.client.get = AsyncMock()
    client.client.post = AsyncMock()
    client.client.put = AsyncMock()
    client.client.aclose = AsyncMock()

    return client



@pytest.fixture
def set_bugzilla_client(mock_bugzilla_client):
    """Set the global bugzilla client"""
    original_bz = utils.bz
    utils.bz = mock_bugzilla_client
    yield mock_bugzilla_client
    utils.bz = original_bz


@pytest.fixture
def reset_bugzilla_client():
    """Reset the global bugzilla client to None"""
    original_bz = utils.bz
    utils.bz = None
    yield
    utils.bz = original_bz
