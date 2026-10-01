"""Unit tests for Bugzilla batch and analytics MCP tools"""

import pytest
from unittest.mock import AsyncMock
from fastmcp.exceptions import ToolError
from bugzilla_mcp.tools.bugzilla import (
    bugs_info,
    bugs_comments,
    bugs_analysis_context,
    classify_bugs_heuristics,
    analyze_bugs_statistics,
)


class TestBugsInfoTool:
    """Tests for bugs_info tool"""

    async def test_bugs_info_success(self, set_bugzilla_client):
        """Test successful bugs_info call"""
        set_bugzilla_client.bugs_info.return_value = [
            {"id": 123, "summary": "Bug A"},
            {"id": 456, "summary": "Bug B"},
        ]
        result = await bugs_info([123, 456])
        assert len(result) == 2
        assert result[0]["id"] == 123
        assert result[1]["id"] == 456
        set_bugzilla_client.bugs_info.assert_called_once_with([123, 456])

    async def test_bugs_info_raises_on_missing_client(self, reset_bugzilla_client):
        """Test bugs_info raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await bugs_info([123])
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_bugs_info_raises_on_api_error(self, set_bugzilla_client):
        """Test bugs_info raises ToolError on API error"""
        set_bugzilla_client.bugs_info = AsyncMock(side_effect=Exception("API Connection Error"))
        with pytest.raises(ToolError) as exc_info:
            await bugs_info([123])
        assert "Failed to fetch batch bug info" in str(exc_info.value)
        assert "API Connection Error" in str(exc_info.value)


class TestBugsCommentsTool:
    """Tests for bugs_comments tool"""

    async def test_bugs_comments_success(self, set_bugzilla_client):
        """Test successful bugs_comments call"""
        set_bugzilla_client.bugs_comments.return_value = {
            "123": [{"id": 1, "text": "C1"}],
        }
        result = await bugs_comments([123])
        assert "123" in result
        assert result["123"][0]["text"] == "C1"
        set_bugzilla_client.bugs_comments.assert_called_once_with([123])

    async def test_bugs_comments_raises_on_missing_client(self, reset_bugzilla_client):
        """Test bugs_comments raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await bugs_comments([123])
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_bugs_comments_raises_on_api_error(self, set_bugzilla_client):
        """Test bugs_comments raises ToolError on API error"""
        set_bugzilla_client.bugs_comments = AsyncMock(side_effect=Exception("API Timeout"))
        with pytest.raises(ToolError) as exc_info:
            await bugs_comments([123])
        assert "Failed to fetch batch comments" in str(exc_info.value)
        assert "API Timeout" in str(exc_info.value)


class TestBugsAnalysisContextTool:
    """Tests for bugs_analysis_context tool"""

    async def test_bugs_analysis_context_success(self, set_bugzilla_client):
        """Test successful bugs_analysis_context call"""
        expected_context = {
            "123": {
                "id": 123,
                "summary": "Fix this",
                "comments_count": 1,
                "comments_preview": [{"id": 1, "text": "C1"}],
            }
        }
        set_bugzilla_client.bugs_analysis_context.return_value = expected_context
        result = await bugs_analysis_context([123])
        assert "123" in result
        assert result["123"]["summary"] == "Fix this"
        set_bugzilla_client.bugs_analysis_context.assert_called_once_with([123])

    async def test_bugs_analysis_context_raises_on_missing_client(self, reset_bugzilla_client):
        """Test bugs_analysis_context raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await bugs_analysis_context([123])
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_bugs_analysis_context_raises_on_api_error(self, set_bugzilla_client):
        """Test bugs_analysis_context raises ToolError on API error"""
        set_bugzilla_client.bugs_analysis_context = AsyncMock(side_effect=Exception("Data Error"))
        with pytest.raises(ToolError) as exc_info:
            await bugs_analysis_context([123])
        assert "Failed to fetch bugs analysis context" in str(exc_info.value)
        assert "Data Error" in str(exc_info.value)


class TestClassifyBugsHeuristicsTool:
    """Tests for classify_bugs_heuristics tool"""

    async def test_classify_bugs_heuristics_success(self, set_bugzilla_client):
        """Test heuristics classification maps statuses and resolutions correctly"""
        set_bugzilla_client.bugs_info.return_value = [
            {
                "id": 101,
                "summary": "Fix me",
                "status": "NEW",
                "resolution": "",
                "product": "Firefox",
                "component": "General",
            },
            {
                "id": 102,
                "summary": "Not a bug",
                "status": "RESOLVED",
                "resolution": "WONTFIX",
                "product": "Firefox",
                "component": "Layout",
            },
            {
                "id": 103,
                "summary": "Need review",
                "status": "RESOLVED",
                "resolution": "FIXED",
                "product": "Firefox",
                "component": "Build",
            },
        ]

        result = await classify_bugs_heuristics([101, 102, 103])

        # Assert correct classification structure
        assert "to_fix" in result
        assert "invalid" in result
        assert "review_needed" in result

        assert len(result["to_fix"]) == 1
        assert result["to_fix"][0]["id"] == 101
        assert result["to_fix"][0]["summary"] == "Fix me"

        assert len(result["invalid"]) == 1
        assert result["invalid"][0]["id"] == 102
        assert result["invalid"][0]["summary"] == "Not a bug"

        assert len(result["review_needed"]) == 1
        assert result["review_needed"][0]["id"] == 103
        assert result["review_needed"][0]["summary"] == "Need review"

        set_bugzilla_client.bugs_info.assert_called_once_with([101, 102, 103])

    async def test_classify_bugs_heuristics_raises_on_missing_client(self, reset_bugzilla_client):
        """Test classify_bugs_heuristics raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await classify_bugs_heuristics([101])
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_classify_bugs_heuristics_raises_on_api_error(self, set_bugzilla_client):
        """Test classify_bugs_heuristics raises ToolError on API error"""
        set_bugzilla_client.bugs_info = AsyncMock(side_effect=Exception("Parsing Error"))
        with pytest.raises(ToolError) as exc_info:
            await classify_bugs_heuristics([101])
        assert "Failed to perform heuristics classification" in str(exc_info.value)
        assert "Parsing Error" in str(exc_info.value)


class TestAnalyzeBugsStatisticsTool:
    """Tests for analyze_bugs_statistics tool"""

    async def test_analyze_bugs_statistics_success(self, set_bugzilla_client):
        """Test successful statistical analysis call"""
        set_bugzilla_client.bugs_stats_analysis.return_value = {
            "total_bugs": 2,
            "classifications": {"to_fix": {"count": 2, "percentage": 100.0}},
        }
        result = await analyze_bugs_statistics([101, 102])
        assert result["total_bugs"] == 2
        assert result["classifications"]["to_fix"]["count"] == 2
        set_bugzilla_client.bugs_stats_analysis.assert_called_once_with([101, 102])

    async def test_analyze_bugs_statistics_raises_on_missing_client(self, reset_bugzilla_client):
        """Test analyze_bugs_statistics raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await analyze_bugs_statistics([101])
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_analyze_bugs_statistics_raises_on_api_error(self, set_bugzilla_client):
        """Test analyze_bugs_statistics raises ToolError on API error"""
        set_bugzilla_client.bugs_stats_analysis = AsyncMock(side_effect=Exception("Analysis Failure"))
        with pytest.raises(ToolError) as exc_info:
            await analyze_bugs_statistics([101])
        assert "Failed to perform statistical analysis" in str(exc_info.value)
        assert "Analysis Failure" in str(exc_info.value)

