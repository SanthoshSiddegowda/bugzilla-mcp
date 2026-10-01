"""Unit tests for the Bugzilla API client attachment downloading features"""

import base64
import os
import tempfile
import pytest
import httpx
from bugzilla_mcp.utils import Bugzilla


class TestBugzillaDownloadAttachments:
    """Tests for download_attachments method"""

    async def test_download_attachments_success(self, httpx_mock):
        """Test successful download of all bug attachments"""
        bug_id = 12345
        att_id = 9001
        file_name = "test_file.txt"
        file_content = b"Hello, World!"
        b64_data = base64.b64encode(file_content).decode("utf-8")

        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/{bug_id}/attachment?api_key=test-key",
            json={
                "bugs": {
                    str(bug_id): [
                        {
                            "id": att_id,
                            "bug_id": bug_id,
                            "file_name": file_name,
                            "content_type": "text/plain",
                            "size": len(file_content),
                            "data": b64_data,
                        }
                    ]
                }
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = await bz.download_attachments(bug_id, dest_dir=tmp_dir)

            assert len(result) == 1
            att = result[0]
            assert att["id"] == att_id
            assert att["bug_id"] == bug_id
            assert att["file_name"] == file_name
            assert att["content_type"] == "text/plain"
            assert att["size"] == len(file_content)

            # Check that file was actually written to disk
            expected_path = os.path.join(tmp_dir, f"{att_id}_{file_name}")
            assert att["path"] == expected_path
            assert os.path.exists(expected_path)
            with open(expected_path, "rb") as f:
                assert f.read() == file_content

        await bz.close()

    async def test_download_attachments_empty(self, httpx_mock):
        """Test download when there are no attachments"""
        bug_id = 12345
        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/{bug_id}/attachment?api_key=test-key",
            json={"bugs": {str(bug_id): []}},
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = await bz.download_attachments(bug_id, dest_dir=tmp_dir)
            assert result == []

        await bz.close()

    async def test_download_attachments_failure_status_code(self, httpx_mock):
        """Test download raises exception on non-200 status"""
        bug_id = 99999
        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/{bug_id}/attachment?api_key=test-key",
            status_code=500,
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with pytest.raises(httpx.TransportError) as exc_info:
            await bz.download_attachments(bug_id)

        assert "Status code: 500" in str(exc_info.value)
        await bz.close()

    async def test_download_attachments_invalid_base64(self, httpx_mock):
        """Test download raises exception on invalid base64 data"""
        bug_id = 12345
        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/{bug_id}/attachment?api_key=test-key",
            json={
                "bugs": {
                    str(bug_id): [
                        {
                            "id": 9001,
                            "file_name": "bad.txt",
                            "data": "!!!InvalidBase64!!!",
                        }
                    ]
                }
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(ValueError) as exc_info:
                await bz.download_attachments(bug_id, dest_dir=tmp_dir)
            assert "Failed to decode attachment" in str(exc_info.value)

        await bz.close()


class TestBugzillaDownloadAttachment:
    """Tests for download_attachment method"""

    async def test_download_attachment_success(self, httpx_mock):
        """Test successful download of a specific attachment by ID"""
        att_id = 9001
        bug_id = 12345
        file_name = "single_file.txt"
        file_content = b"Single attachment content"
        b64_data = base64.b64encode(file_content).decode("utf-8")

        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/attachment/{att_id}?api_key=test-key",
            json={
                "attachments": {
                    str(att_id): {
                        "id": att_id,
                        "bug_id": bug_id,
                        "file_name": file_name,
                        "content_type": "text/plain",
                        "size": len(file_content),
                        "data": b64_data,
                    }
                }
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with tempfile.TemporaryDirectory() as tmp_dir:
            att = await bz.download_attachment(att_id, dest_dir=tmp_dir)

            assert att["id"] == att_id
            assert att["bug_id"] == bug_id
            assert att["file_name"] == file_name
            assert att["content_type"] == "text/plain"
            assert att["size"] == len(file_content)

            # Check that file was actually written to disk
            expected_path = os.path.join(tmp_dir, f"{att_id}_{file_name}")
            assert att["path"] == expected_path
            assert os.path.exists(expected_path)
            with open(expected_path, "rb") as f:
                assert f.read() == file_content

        await bz.close()

    async def test_download_attachment_failure_status_code(self, httpx_mock):
        """Test download raises exception on non-200 status"""
        att_id = 99999
        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/attachment/{att_id}?api_key=test-key",
            status_code=404,
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with pytest.raises(httpx.TransportError) as exc_info:
            await bz.download_attachment(att_id)

        assert "Status code: 404" in str(exc_info.value)
        await bz.close()

    async def test_download_attachment_not_found(self, httpx_mock):
        """Test download raises ValueError when attachment not found in response"""
        att_id = 9001
        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/attachment/{att_id}?api_key=test-key",
            json={"attachments": {}},
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with pytest.raises(ValueError) as exc_info:
            await bz.download_attachment(att_id)

        assert f"Attachment {att_id} not found" in str(exc_info.value)
        await bz.close()

    async def test_download_attachment_no_data(self, httpx_mock):
        """Test download raises ValueError when no data field present"""
        att_id = 9001
        httpx_mock.add_response(
            url=f"https://bugzilla.mozilla.org/rest/bug/attachment/{att_id}?api_key=test-key",
            json={
                "attachments": {
                    str(att_id): {
                        "id": att_id,
                        "file_name": "no_data.txt",
                    }
                }
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")

        with pytest.raises(ValueError) as exc_info:
            await bz.download_attachment(att_id)

        assert "No data field found" in str(exc_info.value)
        await bz.close()
