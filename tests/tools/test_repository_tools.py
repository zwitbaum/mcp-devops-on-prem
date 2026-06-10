"""Tests for repository_tools (all public tools and private helpers).

Auth path coverage lives in test_shared.py.  These tests use the Bearer token
path only so that responses intercepts requests without NTLM negotiation.
"""

import re

import pytest
import responses as rsps_lib
from fastmcp.exceptions import ToolError

from mcp_devops.tools.repository_tools import (
    _extract_item_text_by_response,
    _make_item_url,
    _validate_commit_sha,
    compare_commits,
    get_commit_changes,
    get_item_content,
    get_item_content_diff,
    get_repositories,
    get_repository,
)
from tests.mocks.repositories import REPOSITORIES_ERROR_RESPONSE, REPOSITORIES_RESPONSE

# @mcp.tool() wraps functions as FunctionTool (Pydantic model).
# Access .fn to reach the plain Python callable.
get_repositories = get_repositories.fn
get_repository = get_repository.fn
get_commit_changes = get_commit_changes.fn
compare_commits = compare_commits.fn
get_item_content = get_item_content.fn
get_item_content_diff = get_item_content_diff.fn

BASE_URL = "https://devops.example.com/org/project"
REPOS_URL = f"{BASE_URL}/_apis/git/repositories"

# A syntactically valid 40-char hex SHA used across tests.
VALID_SHA_A = "a" * 40
VALID_SHA_B = "b" * 40


@pytest.fixture()
def token_auth(monkeypatch):
    """Set a Bearer token so requests use simple header auth."""
    monkeypatch.setenv("DEVOPS_TOKEN", "test-token")


class TestGetRepositories:
    """Integration-style tests that intercept outbound HTTP via responses."""

    @rsps_lib.activate
    def test_returns_api_response_json(self, devops_url, token_auth):
        """get_repositories() passes the JSON body straight through to the caller."""
        rsps_lib.add(rsps_lib.GET, REPOS_URL, json=REPOSITORIES_RESPONSE, status=200)

        result = get_repositories()

        assert result["count"] == 2
        assert result["value"][0]["name"] == "MyRepo"
        assert result["value"][1]["name"] == "AnotherRepo"

    @rsps_lib.activate
    def test_sends_get_to_correct_url(self, devops_url, token_auth):
        """Exactly one GET request is sent to the expected URL."""
        rsps_lib.add(rsps_lib.GET, REPOS_URL, json=REPOSITORIES_RESPONSE, status=200)

        get_repositories()

        assert len(rsps_lib.calls) == 1
        assert rsps_lib.calls[0].request.method == "GET"
        assert rsps_lib.calls[0].request.url == REPOS_URL

    @rsps_lib.activate
    def test_bearer_token_forwarded_in_header(self, devops_url, token_auth):
        """The Authorization header carries the Bearer token from DEVOPS_TOKEN."""
        rsps_lib.add(rsps_lib.GET, REPOS_URL, json=REPOSITORIES_RESPONSE, status=200)

        get_repositories()

        auth_header = rsps_lib.calls[0].request.headers.get("Authorization", "")
        assert auth_header == "Bearer test-token"

    @rsps_lib.activate
    def test_accept_json_header_is_sent(self, devops_url, token_auth):
        """The Accept: application/json header is always present."""
        rsps_lib.add(rsps_lib.GET, REPOS_URL, json=REPOSITORIES_RESPONSE, status=200)

        get_repositories()

        assert rsps_lib.calls[0].request.headers.get("Accept") == "application/json"

    @rsps_lib.activate
    def test_non_200_returns_error_json(self, devops_url, token_auth):
        """A 401 response returns the error JSON body rather than raising an exception.

        This documents current behaviour: devops_api_get calls .json() without
        raise_for_status, so callers receive the API error payload.
        """
        rsps_lib.add(rsps_lib.GET, REPOS_URL, json=REPOSITORIES_ERROR_RESPONSE, status=401)

        result = get_repositories()

        assert "message" in result
        assert "typeKey" in result

    @rsps_lib.activate
    def test_404_returns_error_json(self, devops_url, token_auth):
        """A 404 is treated the same as any other non-200: error JSON is returned."""
        rsps_lib.add(rsps_lib.GET, REPOS_URL, json={"message": "Not Found"}, status=404)

        result = get_repositories()

        assert result["message"] == "Not Found"


# ---------------------------------------------------------------------------
# _validate_commit_sha
# ---------------------------------------------------------------------------


class TestValidateCommitSha:
    def test_valid_lowercase_sha_passes(self):
        _validate_commit_sha("a" * 40)  # must not raise

    def test_valid_uppercase_sha_passes(self):
        _validate_commit_sha("A" * 40)  # must not raise

    def test_valid_mixed_sha_passes(self):
        _validate_commit_sha("aAbBcCdDeEfF" + "0123456789" + "012345678901234678")  # 40 chars

    def test_too_short_raises(self):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            _validate_commit_sha("a" * 39)

    def test_too_long_raises(self):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            _validate_commit_sha("a" * 41)

    def test_non_hex_chars_raise(self):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            _validate_commit_sha("g" * 40)

    def test_non_string_raises(self):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            _validate_commit_sha(None)  # type: ignore[arg-type]

    def test_empty_string_raises(self):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            _validate_commit_sha("")


# ---------------------------------------------------------------------------
# _make_item_url
# ---------------------------------------------------------------------------


class TestMakeItemUrl:
    def test_builds_correct_url(self, devops_url):
        url = _make_item_url("MyRepo", "src/foo.cs", VALID_SHA_A)

        assert f"{BASE_URL}/_apis/git/repositories/MyRepo/items" in url
        assert "path=src/foo.cs" in url
        assert VALID_SHA_A in url
        assert "versionDescriptor.versionType=commit" in url
        assert "includeContent=true" in url

    def test_strips_leading_slash_from_path(self, devops_url):
        url = _make_item_url("MyRepo", "/src/foo.cs", VALID_SHA_A)

        assert "path=src/foo.cs" in url
        assert "path=/src/foo.cs" not in url

    def test_invalid_sha_raises(self, devops_url):
        with pytest.raises(ToolError):
            _make_item_url("MyRepo", "src/foo.cs", "not-a-sha")


# ---------------------------------------------------------------------------
# _extract_item_text_by_response
# ---------------------------------------------------------------------------


class TestExtractItemTextByResponse:
    def test_returns_content_field_from_dict(self):
        assert _extract_item_text_by_response({"content": "hello"}) == "hello"

    def test_falls_back_to_value_field(self):
        assert _extract_item_text_by_response({"value": "world"}) == "world"

    def test_returns_empty_string_for_empty_dict(self):
        assert _extract_item_text_by_response({}) == ""

    def test_returns_string_directly(self):
        assert _extract_item_text_by_response("raw text") == "raw text"

    def test_returns_empty_string_for_other_types(self):
        assert _extract_item_text_by_response(42) == ""
        assert _extract_item_text_by_response(None) == ""
        assert _extract_item_text_by_response([]) == ""


# ---------------------------------------------------------------------------
# get_repository
# ---------------------------------------------------------------------------


class TestGetRepository:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = f"{BASE_URL}/_apis/git/repositories/MyRepo"
        rsps_lib.add(rsps_lib.GET, expected_url, json={"id": "aaaa", "name": "MyRepo"}, status=200)

        get_repository("MyRepo")

        assert rsps_lib.calls[0].request.url == expected_url

    @rsps_lib.activate
    def test_returns_response_json(self, devops_url, token_auth):
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/_apis/git/repositories/MyRepo",
            json={"id": "aaaa", "name": "MyRepo"},
            status=200,
        )

        result = get_repository("MyRepo")

        assert result["name"] == "MyRepo"


# ---------------------------------------------------------------------------
# get_commit_changes
# ---------------------------------------------------------------------------


class TestGetCommitChanges:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = f"{BASE_URL}/_apis/git/repositories/MyRepo/commits/{VALID_SHA_A}/changes"
        rsps_lib.add(rsps_lib.GET, expected_url, json={"changes": []}, status=200)

        get_commit_changes("MyRepo", VALID_SHA_A)

        assert rsps_lib.calls[0].request.url == expected_url

    @rsps_lib.activate
    def test_returns_changes_json(self, devops_url, token_auth):
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/_apis/git/repositories/MyRepo/commits/{VALID_SHA_A}/changes",
            json={"changes": [{"item": {"path": "/src/foo.cs"}, "changeType": "edit"}]},
            status=200,
        )

        result = get_commit_changes("MyRepo", VALID_SHA_A)

        assert result["changes"][0]["changeType"] == "edit"

    def test_invalid_sha_raises_before_request(self, devops_url, token_auth):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            get_commit_changes("MyRepo", "bad-sha")


# ---------------------------------------------------------------------------
# compare_commits
# ---------------------------------------------------------------------------

_DIFF_RESPONSE = {
    "changeCounts": {"Edit": 1},
    "changes": [
        {
            "item": {"path": "/src/foo.cs", "isFolder": False},
            "changeType": "edit",
        },
        {
            "item": {"path": "/src/bar/", "isFolder": True},
            "changeType": "edit",
        },
    ],
}


class TestCompareCommits:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        url = (
            f"{BASE_URL}/_apis/git/repositories/MyRepo/diffs/commits?"
            f"baseVersion={VALID_SHA_A}&baseVersionType=commit"
            f"&targetVersion={VALID_SHA_B}&targetVersionType=commit"
        )
        rsps_lib.add(rsps_lib.GET, url, json=_DIFF_RESPONSE, status=200)

        compare_commits("MyRepo", VALID_SHA_A, VALID_SHA_B)

        assert rsps_lib.calls[0].request.url == url

    @rsps_lib.activate
    def test_maps_response_to_expected_shape(self, devops_url, token_auth):
        url = (
            f"{BASE_URL}/_apis/git/repositories/MyRepo/diffs/commits?"
            f"baseVersion={VALID_SHA_A}&baseVersionType=commit"
            f"&targetVersion={VALID_SHA_B}&targetVersionType=commit"
        )
        rsps_lib.add(rsps_lib.GET, url, json=_DIFF_RESPONSE, status=200)

        result = compare_commits("MyRepo", VALID_SHA_A, VALID_SHA_B)

        assert "changeCounts" in result
        assert "changes" in result
        assert result["changes"][0]["path"] == "/src/foo.cs"
        assert result["changes"][0]["changeType"] == "edit"
        assert result["changes"][0]["isFolder"] is False
        assert result["changes"][1]["isFolder"] is True

    @rsps_lib.activate
    def test_handles_empty_changes_list(self, devops_url, token_auth):
        url = (
            f"{BASE_URL}/_apis/git/repositories/MyRepo/diffs/commits?"
            f"baseVersion={VALID_SHA_A}&baseVersionType=commit"
            f"&targetVersion={VALID_SHA_B}&targetVersionType=commit"
        )
        rsps_lib.add(rsps_lib.GET, url, json={"changeCounts": {}, "changes": []}, status=200)

        result = compare_commits("MyRepo", VALID_SHA_A, VALID_SHA_B)

        assert result["changes"] == []

    def test_invalid_base_sha_raises(self, devops_url, token_auth):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            compare_commits("MyRepo", "bad", VALID_SHA_B)

    def test_invalid_target_sha_raises(self, devops_url, token_auth):
        with pytest.raises(ToolError, match="Invalid commit SHA"):
            compare_commits("MyRepo", VALID_SHA_A, "bad")


# ---------------------------------------------------------------------------
# get_item_content
# ---------------------------------------------------------------------------


class TestGetItemContent:
    @rsps_lib.activate
    def test_returns_content_field(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "class Foo {}"}, status=200)

        result = get_item_content("MyRepo", "src/foo.cs", VALID_SHA_A)

        assert result == "class Foo {}"

    @rsps_lib.activate
    def test_returns_empty_string_when_content_missing(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={}, status=200)

        result = get_item_content("MyRepo", "src/foo.cs", VALID_SHA_A)

        assert result == ""


# ---------------------------------------------------------------------------
# get_item_content_diff  (the most complex tool)
# ---------------------------------------------------------------------------


def _make_item_url_for(repo, path, sha):
    """Build the item URL the way the tool does, for use in rsps_lib.add."""
    return (
        f"{BASE_URL}/_apis/git/repositories/{repo}/items?path={path.lstrip('/')}"
        f"&versionDescriptor.version={sha}&versionDescriptor.versionType=commit"
        f"&includeContent=true"
    )


class TestGetItemContentDiff:
    @rsps_lib.activate
    def test_unchanged_files_report_unchanged(self, devops_url, token_auth):
        content = "line1\nline2\nline3"
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": content}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": content}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "unchanged"
        assert result["changes"] == ""

    @rsps_lib.activate
    def test_edited_file_reports_edit(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "old line\ncommon"}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "new line\ncommon"}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "edit"
        assert "-old line" in result["changes"]
        assert "+new line" in result["changes"]

    @rsps_lib.activate
    def test_new_file_reports_add(self, devops_url, token_auth):
        # base fetch raises → file didn't exist in base → "add"
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), body=Exception("connection error"))
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "new content"}, status=200)

        result = get_item_content_diff("MyRepo", "src/new.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "add"
        assert result["baseAvailable"] is False
        assert result["targetAvailable"] is True

    @rsps_lib.activate
    def test_deleted_file_reports_delete(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "old content"}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), body=Exception("connection error"))

        result = get_item_content_diff("MyRepo", "src/gone.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "delete"
        assert result["baseAvailable"] is True
        assert result["targetAvailable"] is False

    @rsps_lib.activate
    def test_whitespace_only_changes_report_correct_type(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "line1\n\nline3"}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "line1\n\n\nline3"}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "white spaces only"
        assert result["changes"] == ""

    @rsps_lib.activate
    def test_result_includes_expected_fields(self, devops_url, token_auth):
        content = "same"
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": content}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": content}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["path"] == "src/foo.cs"
        assert result["baseVersion"] == VALID_SHA_A
        assert result["targetVersion"] == VALID_SHA_B
        assert "baseAvailable" in result
        assert "targetAvailable" in result
        assert "changeType" in result
        assert "changes" in result

    @rsps_lib.activate
    def test_diff_includes_context_lines_around_changes(self, devops_url, token_auth):
        base = "\n".join(["ctx1", "ctx2", "ctx3", "old line", "ctx4", "ctx5", "ctx6"])
        target = "\n".join(["ctx1", "ctx2", "ctx3", "new line", "ctx4", "ctx5", "ctx6"])
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": base}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": target}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert "ctx1" in result["changes"]
        assert "ctx6" in result["changes"]
        assert "-old line" in result["changes"]
        assert "+new line" in result["changes"]

    @rsps_lib.activate
    def test_whitespace_only_removed_blank_line_counts(self, devops_url, token_auth):
        # Removing a blank line — covers the "- " + blank content branch (line 181).
        # Patch devops_api_get directly to guarantee call order.
        from unittest.mock import patch

        responses_sequence = [
            {"content": "line1\n\nline3"},  # base has blank line
            {"content": "line1\nline3"},    # target does not
        ]
        call_iter = iter(responses_sequence)
        with patch("mcp_devops.tools.repository_tools.devops_api_get", side_effect=lambda url: next(call_iter)):
            result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "white spaces only"

    def test_ndiff_hint_lines_are_skipped(self, devops_url):
        # ndiff generates "? " hint lines for strings with only tail chars differing.
        # e.g. "abcdefghij_X" vs "abcdefghij_Y" → produces "? " lines that must be
        # skipped (line 181).  Patch devops_api_get to inject content directly.
        from unittest.mock import patch

        responses_sequence = [
            {"content": "abcdefghij_X"},
            {"content": "abcdefghij_Y"},
        ]
        call_iter = iter(responses_sequence)
        with patch("mcp_devops.tools.repository_tools.devops_api_get", side_effect=lambda url: next(call_iter)):
            result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "edit"
        assert "-abcdefghij_X" in result["changes"]
        assert "+abcdefghij_Y" in result["changes"]

    @rsps_lib.activate
    def test_whitespace_only_added_blank_line_counts(self, devops_url, token_auth):
        # Adding a blank line — covers the "+ " + blank content branch (line 189)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "line1\nline3"}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": "line1\n\nline3"}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changeType"] == "white spaces only"

    @rsps_lib.activate
    def test_ellipsis_separator_when_change_is_not_at_start(self, devops_url, token_auth):
        # A change deep in the file: context window won't include line 0 → "..." prepended
        prefix = "\n".join([f"line{i}" for i in range(10)])
        base = prefix + "\nold target\nfooter"
        target = prefix + "\nnew target\nfooter"
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": base}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": target}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changes"].startswith("...")

    @rsps_lib.activate
    def test_ellipsis_appended_when_change_is_not_at_end(self, devops_url, token_auth):
        # A change near the top, with many lines after: trailing "..." is appended
        suffix = "\n".join([f"line{i}" for i in range(10)])
        base = "header\nold target\n" + suffix
        target = "header\nnew target\n" + suffix
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": base}, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*"), json={"content": target}, status=200)

        result = get_item_content_diff("MyRepo", "src/foo.cs", VALID_SHA_A, VALID_SHA_B)

        assert result["changes"].endswith("...")


