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
    client.close = AsyncMock()
    
    # Mock the httpx client
    client.client = MagicMock()
    client.client.get = AsyncMock()
    client.client.post = AsyncMock()
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
