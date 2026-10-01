"""Unit tests for the Bugzilla API client batch fetching features"""

import pytest
import httpx
from unittest.mock import AsyncMock
from bugzilla_mcp.utils import Bugzilla


class TestBugzillaBugsInfo:
    """Tests for bugs_info method"""

    async def test_bugs_info_success(self, httpx_mock):
        """Test successful batch bugs info retrieval"""
        bug_ids = [12345, 12346]
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug?api_key=test-key&id=12345%2C12346",
            json={
                "bugs": [
                    {"id": 12345, "summary": "Bug 1", "status": "NEW"},
                    {"id": 12346, "summary": "Bug 2", "status": "ASSIGNED"},
                ]
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_info(bug_ids)

        assert len(result) == 2
        assert result[0]["id"] == 12345
        assert result[0]["summary"] == "Bug 1"
        assert result[1]["id"] == 12346
        assert result[1]["summary"] == "Bug 2"

        await bz.close()

    async def test_bugs_info_empty(self):
        """Test batch bugs info with empty input list"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_info([])
        assert result == []
        await bz.close()

    async def test_bugs_info_failure_status_code(self, httpx_mock):
        """Test batch bugs info raises exception on non-200 status"""
        bug_ids = [12345]
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug?api_key=test-key&id=12345",
            status_code=400,
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        
        with pytest.raises(httpx.TransportError) as exc_info:
            await bz.bugs_info(bug_ids)

        assert "Status code: 400" in str(exc_info.value)
        await bz.close()


class TestBugzillaBugsComments:
    """Tests for bugs_comments method"""

    async def test_bugs_comments_success(self, httpx_mock):
        """Test successful parallel batch comments retrieval"""
        bug_ids = [12345, 12346]
        
        # Mock comments for bug 12345
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment?api_key=test-key",
            json={"bugs": {"12345": {"comments": [{"id": 1, "text": "Comment A"}]}}},
        )
        # Mock comments for bug 12346
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12346/comment?api_key=test-key",
            json={"bugs": {"12346": {"comments": [{"id": 2, "text": "Comment B"}]}}},
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_comments(bug_ids)

        assert "12345" in result
        assert "12346" in result
        assert result["12345"][0]["text"] == "Comment A"
        assert result["12346"][0]["text"] == "Comment B"

        await bz.close()

    async def test_bugs_comments_empty(self):
        """Test batch comments with empty input list"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_comments([])
        assert result == {}
        await bz.close()


class TestBugzillaBugsAnalysisContext:
    """Tests for bugs_analysis_context method"""

    async def test_bugs_analysis_context_success(self, httpx_mock):
        """Test consolidated prompt-friendly context merges info and comments properly"""
        bug_ids = [12345]

        # Mock bug info
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug?api_key=test-key&id=12345",
            json={
                "bugs": [
                    {
                        "id": 12345,
                        "summary": "Triage me",
                        "status": "NEW",
                        "product": "Firefox",
                        "component": "General",
                    }
                ]
            },
        )

        # Mock bug comments (more than 4 to trigger preview compression logic)
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment?api_key=test-key",
            json={
                "bugs": {
                    "12345": {
                        "comments": [
                            {"id": 1, "text": "C1", "is_private": False, "creator": "dev"},
                            {"id": 2, "text": "C2", "is_private": False, "creator": "dev"},
                            {"id": 3, "text": "C3", "is_private": False, "creator": "dev"},
                            {"id": 4, "text": "C4", "is_private": False, "creator": "dev"},
                            {"id": 5, "text": "C5", "is_private": False, "creator": "dev"},
                        ]
                    }
                }
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_analysis_context(bug_ids)

        assert "12345" in result
        ctx = result["12345"]
        assert ctx["id"] == 12345
        assert ctx["summary"] == "Triage me"
        assert ctx["status"] == "NEW"
        assert ctx["comments_count"] == 5
        
        # Preview should have first 2 comments, 1 compression placeholder, and last 2 comments (total 5 elements)
        assert len(ctx["comments_preview"]) == 5
        assert ctx["comments_preview"][0]["text"] == "C1"
        assert ctx["comments_preview"][1]["text"] == "C2"
        assert "omitted" in ctx["comments_preview"][2]["text"]
        assert ctx["comments_preview"][3]["text"] == "C4"
        assert ctx["comments_preview"][4]["text"] == "C5"

        await bz.close()

    async def test_bugs_analysis_context_empty(self):
        """Test bugs analysis context with empty input list"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_analysis_context([])
        assert result == {}
        await bz.close()


class TestBugzillaBugsStatsAnalysis:
    """Tests for bugs_stats_analysis method"""

    async def test_bugs_stats_analysis_success(self, httpx_mock):
        """Test successful stats computation based on classifications"""
        bug_ids = [10001, 10002, 10003]

        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug?api_key=test-key&id=10001%2C10002%2C10003",
            json={
                "bugs": [
                    {
                        "id": 10001,
                        "status": "NEW",
                        "resolution": "",
                        "product": "Firefox",
                        "component": "General",
                        "severity": "critical",
                        "priority": "P1",
                        "assigned_to": "alice@example.com",
                    },
                    {
                        "id": 10002,
                        "status": "RESOLVED",
                        "resolution": "WONTFIX",
                        "product": "Firefox",
                        "component": "Layout",
                        "severity": "normal",
                        "priority": "P2",
                        "assigned_to": "bob@example.com",
                    },
                    {
                        "id": 10003,
                        "status": "RESOLVED",
                        "resolution": "FIXED",
                        "product": "Thunderbird",
                        "component": "Mail",
                        "severity": "minor",
                        "priority": "P3",
                        "assigned_to": "alice@example.com",
                    },
                ]
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_stats_analysis(bug_ids)

        assert result["total_bugs"] == 3
        
        # Classification breakdown (1 of each -> 33.33%)
        assert result["classifications"]["to_fix"]["count"] == 1
        assert result["classifications"]["to_fix"]["percentage"] == 33.33
        assert result["classifications"]["invalid"]["count"] == 1
        assert result["classifications"]["invalid"]["percentage"] == 33.33
        assert result["classifications"]["review_needed"]["count"] == 1
        assert result["classifications"]["review_needed"]["percentage"] == 33.33

        # Products breakdown (2 Firefox -> 66.67%, 1 Thunderbird -> 33.33%)
        assert result["products"]["Firefox"]["count"] == 2
        assert result["products"]["Firefox"]["percentage"] == 66.67
        assert result["products"]["Thunderbird"]["count"] == 1
        assert result["products"]["Thunderbird"]["percentage"] == 33.33

        # Severity / Priority workload (Should only count NEW/to_fix bugs)
        assert result["to_fix_severity"] == {"critical": 1}
        assert result["to_fix_priority"] == {"P1": 1}

        # Assignees breakdown (2 alice -> 66.67%, 1 bob -> 33.33%)
        assert result["assignee_distribution"]["alice@example.com"]["count"] == 2
        assert result["assignee_distribution"]["alice@example.com"]["percentage"] == 66.67

        await bz.close()

    async def test_bugs_stats_analysis_empty(self):
        """Test bugs_stats_analysis with empty input list"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bugs_stats_analysis([])
        assert result["total_bugs"] == 0
        assert result["classifications"] == {}
        await bz.close()

