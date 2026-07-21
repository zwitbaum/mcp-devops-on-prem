"""Tests for wiki_tools — all public tools and helper functions.

Auth path coverage lives in test_shared.py. These tests use Bearer token auth.

URL construction in wiki tools uses the module-level ``devops_api_url`` (full
project URL). The ``devops_url`` fixture in conftest.py patches that variable.
"""

import re

from tests.conftest import TEST_BASE_URL

import pytest
import responses as rsps_lib
from fastmcp.exceptions import ToolError

from mcp_devops.tools.wiki_tools import (
    WIKI_API_PATH,
    _get_api_path,
    _get_wiki_info,
    _get_wiki_page_details,
    create_wiki_page,
    delete_wiki_page,
    get_wiki_page,
    update_wiki_page,
)
from tests.mocks.wiki import (
    WIKI_INFO_CODE_RESPONSE,
    WIKI_INFO_PROJECT_RESPONSE,
    WIKI_PAGE_RESPONSE,
    WIKI_PAGE_WITH_CONTENT_RESPONSE,
    WIKI_PATCH_RESPONSE,
    WIKI_PUT_RESPONSE,
)

# @mcp.tool() wraps functions as FunctionTool — use .fn to call them directly.
get_wiki_page = get_wiki_page.fn
create_wiki_page = create_wiki_page.fn
update_wiki_page = update_wiki_page.fn
delete_wiki_page = delete_wiki_page.fn

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

WIKI_ID = "MyWiki.wiki"
PAGE_ID = 12

WIKI_BASE = f"{TEST_BASE_URL}/_apis/wiki/wikis/{WIKI_ID}"
PAGES_BASE = f"{WIKI_BASE}/pages"
PAGE_URL = f"{PAGES_BASE}/{PAGE_ID}"
WIKI_INFO_URL = f"{WIKI_BASE}?api-version=7.1"


@pytest.fixture(autouse=True)
def clear_wiki_cache(monkeypatch):
    """Reset the module-level WIKI_INFO_CACHE before every test."""
    monkeypatch.setattr("mcp_devops.tools.wiki_tools.WIKI_INFO_CACHE", {})


@pytest.fixture()
def token_auth(monkeypatch):
    monkeypatch.setenv("DEVOPS_TOKEN", "test-token")


# ---------------------------------------------------------------------------
# _get_api_path
# ---------------------------------------------------------------------------


class TestGetApiPath:
    def test_returns_correct_path(self):
        assert _get_api_path("MyWiki") == f"{WIKI_API_PATH}/MyWiki"

    def test_includes_dot_in_wiki_id(self):
        assert _get_api_path("MyWiki.wiki") == f"{WIKI_API_PATH}/MyWiki.wiki"


# ---------------------------------------------------------------------------
# _get_wiki_page_details
# ---------------------------------------------------------------------------


class TestGetWikiPageDetails:
    @rsps_lib.activate
    def test_builds_correct_url_without_content(self, devops_url, token_auth):
        expected = f"{PAGE_URL}?includeContent=false&api-version=7.1"
        rsps_lib.add(rsps_lib.GET, expected, json=WIKI_PAGE_RESPONSE, status=200)

        _get_wiki_page_details(WIKI_ID, PAGE_ID, include_content=False)

        assert rsps_lib.calls[0].request.url == expected

    @rsps_lib.activate
    def test_builds_correct_url_with_content(self, devops_url, token_auth):
        expected = f"{PAGE_URL}?includeContent=true&api-version=7.1"
        rsps_lib.add(rsps_lib.GET, expected, json=WIKI_PAGE_WITH_CONTENT_RESPONSE, status=200)

        result = _get_wiki_page_details(WIKI_ID, PAGE_ID, include_content=True)

        assert rsps_lib.calls[0].request.url == expected
        assert result["content"] == "# My Page\n\nHello World"

    @rsps_lib.activate
    def test_returns_parsed_json(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages.*"), json=WIKI_PAGE_RESPONSE, status=200)

        result = _get_wiki_page_details(WIKI_ID, PAGE_ID, include_content=False)

        assert result["id"] == 12
        assert result["path"] == "/MyPage"


# ---------------------------------------------------------------------------
# _get_wiki_info (including cache behaviour)
# ---------------------------------------------------------------------------


class TestGetWikiInfo:
    @rsps_lib.activate
    def test_fetches_wiki_info_from_api(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=WIKI_INFO_PROJECT_RESPONSE, status=200)

        result = _get_wiki_info(WIKI_ID)

        assert result["type"] == "projectWiki"
        assert len(rsps_lib.calls) == 1

    @rsps_lib.activate
    def test_caches_result_on_second_call(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=WIKI_INFO_PROJECT_RESPONSE, status=200)

        _get_wiki_info(WIKI_ID)
        _get_wiki_info(WIKI_ID)  # second call — should hit cache

        assert len(rsps_lib.calls) == 1  # only one HTTP request made


# ---------------------------------------------------------------------------
# get_wiki_page (MCP tool)
# ---------------------------------------------------------------------------


class TestGetWikiPage:
    @rsps_lib.activate
    def test_returns_page_metadata(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages.*"), json=WIKI_PAGE_RESPONSE, status=200)

        result = get_wiki_page(WIKI_ID, PAGE_ID, include_content=False)

        assert result["path"] == "/MyPage"
        assert result["isParentPage"] is False

    @rsps_lib.activate
    def test_does_not_include_content_by_default(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages.*"), json=WIKI_PAGE_RESPONSE, status=200)

        result = get_wiki_page(WIKI_ID, PAGE_ID)

        assert "content" not in result

    @rsps_lib.activate
    def test_includes_content_when_requested(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages.*"), json=WIKI_PAGE_WITH_CONTENT_RESPONSE, status=200)

        result = get_wiki_page(WIKI_ID, PAGE_ID, include_content=True)

        assert result["content"] == "# My Page\n\nHello World"


# ---------------------------------------------------------------------------
# create_wiki_page (MCP tool)
# ---------------------------------------------------------------------------


class TestCreateWikiPage:
    @rsps_lib.activate
    def test_creates_new_page_when_404(self, devops_url, token_auth):
        """When the existence check returns a 404, PUT proceeds without If-Match."""
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages\?.*"), json={}, status=404)
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=WIKI_INFO_PROJECT_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PUT, re.compile(r".*"), json=WIKI_PUT_RESPONSE, status=200)

        result = create_wiki_page(WIKI_ID, "/Root", "NewPage", content="Hello")

        assert result["id"] == 20
        assert result["path"] == "/Root/NewPage"
        put_request = rsps_lib.calls[-1].request
        assert "If-Match" not in put_request.headers

    @rsps_lib.activate
    def test_updates_existing_page_with_etag(self, devops_url, token_auth):
        """When the existence check returns 200 with ETag, PUT sends If-Match."""
        rsps_lib.add(
            rsps_lib.GET,
            re.compile(r".*pages\?.*"),
            json=WIKI_PAGE_RESPONSE,
            status=200,
            headers={"ETag": '"v1"', "Content-Type": "application/json"},
        )
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=WIKI_INFO_PROJECT_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PUT, re.compile(r".*"), json=WIKI_PUT_RESPONSE, status=200)

        result = create_wiki_page(WIKI_ID, "/Root", "NewPage", content="Updated")

        assert result["id"] == 20
        put_request = rsps_lib.calls[-1].request
        assert put_request.headers.get("If-Match") == '"v1"'

    @rsps_lib.activate
    def test_code_wiki_appends_version_descriptor(self, devops_url, token_auth):
        """codeWiki type → PUT URL includes versionDescriptor params."""
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages\?.*"), json={}, status=404)
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=WIKI_INFO_CODE_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PUT, re.compile(r".*"), json=WIKI_PUT_RESPONSE, status=200)

        create_wiki_page(WIKI_ID, "/Root", "NewPage")

        put_url = rsps_lib.calls[-1].request.url
        assert "versionDescriptor.versionType=branch" in put_url
        assert "versionDescriptor.version=main" in put_url

    @rsps_lib.activate
    def test_code_wiki_adds_comment_to_payload(self, devops_url, token_auth):
        """codeWiki type → PUT payload includes a commit comment."""
        import json

        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages\?.*"), json={}, status=404)
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=WIKI_INFO_CODE_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PUT, re.compile(r".*"), json=WIKI_PUT_RESPONSE, status=200)

        create_wiki_page(WIKI_ID, "/Root", "NewPage")

        body = json.loads(rsps_lib.calls[-1].request.body)
        assert "comment" in body

    @rsps_lib.activate
    def test_raises_tool_error_when_existence_check_fails(self, devops_url, token_auth):
        """Non-JSON response from the existence GET raises ToolError."""
        rsps_lib.add(
            rsps_lib.GET,
            re.compile(r".*pages\?.*"),
            body="<html>Server Error</html>",
            status=500,
            content_type="text/html",
        )

        with pytest.raises(ToolError):
            create_wiki_page(WIKI_ID, "/Root", "NewPage")

    def test_silently_continues_on_http_error_404(self, devops_url, token_auth):
        """HTTPError with 404 on the existence check is swallowed; PUT proceeds."""
        from requests.exceptions import HTTPError
        from unittest.mock import MagicMock, patch as mock_patch

        mock_response = MagicMock()
        mock_response.status_code = 404
        http_404 = HTTPError(response=mock_response)

        with mock_patch("mcp_devops.tools.wiki_tools.devops_api_get", side_effect=http_404):
            with mock_patch("mcp_devops.tools.wiki_tools._get_wiki_info", return_value=WIKI_INFO_PROJECT_RESPONSE):
                with mock_patch("mcp_devops.tools.wiki_tools.devops_api_put", return_value=WIKI_PUT_RESPONSE):
                    result = create_wiki_page(WIKI_ID, "/Root", "NewPage")

        assert result["id"] == 20

    @rsps_lib.activate
    def test_returns_path_order_id(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages\?.*"), json={}, status=404)
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=WIKI_INFO_PROJECT_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PUT, re.compile(r".*"), json=WIKI_PUT_RESPONSE, status=200)

        result = create_wiki_page(WIKI_ID, "/Root", "NewPage")

        assert set(result.keys()) == {"path", "order", "id"}

    @rsps_lib.activate
    def test_code_wiki_no_versions_uses_fallback(self, devops_url, token_auth):
        """codeWiki with empty versions list → falls back to 'test' version."""
        code_wiki_no_version = {**WIKI_INFO_CODE_RESPONSE, "versions": [{}]}
        rsps_lib.add(rsps_lib.GET, re.compile(r".*pages\?.*"), json={}, status=404)
        rsps_lib.add(rsps_lib.GET, WIKI_INFO_URL, json=code_wiki_no_version, status=200)
        rsps_lib.add(rsps_lib.PUT, re.compile(r".*"), json=WIKI_PUT_RESPONSE, status=200)

        create_wiki_page(WIKI_ID, "/Root", "NewPage")

        put_url = rsps_lib.calls[-1].request.url
        assert "versionDescriptor.version=test" in put_url


# ---------------------------------------------------------------------------
# update_wiki_page (MCP tool)
# ---------------------------------------------------------------------------


class TestUpdateWikiPage:
    @rsps_lib.activate
    def test_builds_correct_get_and_patch_url(self, devops_url, token_auth):
        expected_url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(
            rsps_lib.GET,
            expected_url,
            json=WIKI_PAGE_RESPONSE,
            status=200,
            headers={"ETag": '"v2"', "Content-Type": "application/json"},
        )
        rsps_lib.add(rsps_lib.PATCH, expected_url, json=WIKI_PATCH_RESPONSE, status=200)

        update_wiki_page(WIKI_ID, PAGE_ID, content="New content")

        assert rsps_lib.calls[0].request.url == expected_url
        assert rsps_lib.calls[1].request.url == expected_url

    @rsps_lib.activate
    def test_sends_etag_as_if_match_header(self, devops_url, token_auth):
        url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(
            rsps_lib.GET, url, json=WIKI_PAGE_RESPONSE, status=200, headers={"ETag": '"etag-xyz"'}
        )
        rsps_lib.add(rsps_lib.PATCH, url, json=WIKI_PATCH_RESPONSE, status=200)

        update_wiki_page(WIKI_ID, PAGE_ID, content="Updated")

        patch_request = rsps_lib.calls[1].request
        assert patch_request.headers.get("If-Match") == '"etag-xyz"'

    @rsps_lib.activate
    def test_sends_content_in_payload(self, devops_url, token_auth):
        import json

        url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.GET, url, json=WIKI_PAGE_RESPONSE, status=200, headers={"ETag": '"v1"'})
        rsps_lib.add(rsps_lib.PATCH, url, json=WIKI_PATCH_RESPONSE, status=200)

        update_wiki_page(WIKI_ID, PAGE_ID, content="## Heading")

        body = json.loads(rsps_lib.calls[1].request.body)
        assert body["content"] == "## Heading"

    @rsps_lib.activate
    def test_returns_path_order_id(self, devops_url, token_auth):
        url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.GET, url, json=WIKI_PAGE_RESPONSE, status=200, headers={"ETag": '"v1"'})
        rsps_lib.add(rsps_lib.PATCH, url, json=WIKI_PATCH_RESPONSE, status=200)

        result = update_wiki_page(WIKI_ID, PAGE_ID)

        assert set(result.keys()) == {"path", "order", "id"}
        assert result["path"] == "/MyPage"

    def test_raises_tool_error_for_zero_page_id(self, devops_url, token_auth):
        with pytest.raises(ToolError, match="Invalid page_id"):
            update_wiki_page(WIKI_ID, 0)

    def test_raises_tool_error_for_negative_page_id(self, devops_url, token_auth):
        with pytest.raises(ToolError, match="Invalid page_id"):
            update_wiki_page(WIKI_ID, -5)

    @rsps_lib.activate
    def test_raises_tool_error_when_no_etag(self, devops_url, token_auth):
        """If the GET response has no ETag, a ToolError should be raised."""
        url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.GET, url, json=WIKI_PAGE_RESPONSE, status=200)  # no ETag header

        with pytest.raises(ToolError, match="Page version cannot be retrieved"):
            update_wiki_page(WIKI_ID, PAGE_ID)

    @rsps_lib.activate
    def test_raises_tool_error_on_get_failure(self, devops_url, token_auth):
        """Any exception from the GET call is wrapped in a ToolError."""
        url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.GET, url, body=Exception("Connection refused"))

        with pytest.raises(ToolError, match="Page version cannot be retrieved"):
            update_wiki_page(WIKI_ID, PAGE_ID)


# ---------------------------------------------------------------------------
# delete_wiki_page (MCP tool)
# ---------------------------------------------------------------------------


class TestDeleteWikiPage:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.DELETE, expected_url, status=204)

        delete_wiki_page(WIKI_ID, PAGE_ID)

        assert rsps_lib.calls[0].request.url == expected_url
        assert rsps_lib.calls[0].request.method == "DELETE"

    @rsps_lib.activate
    def test_appends_comment_when_provided(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.DELETE, re.compile(r".*pages.*"), status=204)

        delete_wiki_page(WIKI_ID, PAGE_ID, comment="Removing outdated page")

        delete_url = rsps_lib.calls[0].request.url
        assert "comment=Removing+outdated+page" in delete_url or "comment=Removing%20outdated%20page" in delete_url

    @rsps_lib.activate
    def test_no_comment_param_when_omitted(self, devops_url, token_auth):
        expected_url = f"{PAGE_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.DELETE, expected_url, status=204)

        delete_wiki_page(WIKI_ID, PAGE_ID)

        assert "comment" not in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_returns_none(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.DELETE, re.compile(r".*pages.*"), status=204)

        result = delete_wiki_page(WIKI_ID, PAGE_ID)

        assert result is None

    def test_raises_tool_error_for_zero_page_id(self, devops_url, token_auth):
        with pytest.raises(ToolError, match="Invalid page_id"):
            delete_wiki_page(WIKI_ID, 0)

    def test_raises_tool_error_for_negative_page_id(self, devops_url, token_auth):
        with pytest.raises(ToolError, match="Invalid page_id"):
            delete_wiki_page(WIKI_ID, -1)
