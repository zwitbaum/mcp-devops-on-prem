"""Tests for pull_request_tools — all public tools and the private helper.

Auth path coverage lives in test_shared.py. These tests use the Bearer token
path only so responses intercepts requests without NTLM negotiation.
"""

import re

import pytest
import responses as rsps_lib

from mcp_devops.tools.pull_request_tools import (
    _ensure_rel_file_path,
    create_pull_request_comment,
    delete_pull_request_comment,
    get_pull_request,
    list_pull_request_thread_comments,
    list_pull_request_threads,
    reply_pull_request_comment,
    update_pull_request_comment,
    update_pull_request_thread,
)
from tests.mocks.pull_requests import (
    CREATE_THREAD_RESPONSE,
    PULL_REQUEST_NO_WORKITEMS_RESPONSE,
    PULL_REQUEST_RESPONSE,
    REPLY_COMMENT_RESPONSE,
    SINGLE_THREAD_RESPONSE,
    THREADS_RESPONSE,
    UPDATE_COMMENT_RESPONSE,
    UPDATE_THREAD_RESPONSE,
    WORK_ITEM_RESPONSE,
    WORK_ITEMS_LIST_RESPONSE,
)

# @mcp.tool() wraps functions as FunctionTool. Use .fn to reach the callable.
get_pull_request = get_pull_request.fn
list_pull_request_threads = list_pull_request_threads.fn
list_pull_request_thread_comments = list_pull_request_thread_comments.fn
create_pull_request_comment = create_pull_request_comment.fn
reply_pull_request_comment = reply_pull_request_comment.fn
update_pull_request_thread = update_pull_request_thread.fn
update_pull_request_comment = update_pull_request_comment.fn
delete_pull_request_comment = delete_pull_request_comment.fn

BASE_URL = "https://devops.example.com/org/project"
REPO = "MyRepo"
PR_ID = 42
THREAD_ID = 10
COMMENT_ID = 1

PR_URL = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}"
THREADS_URL = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}/threads"
THREAD_URL = f"{THREADS_URL}/{THREAD_ID}"


@pytest.fixture()
def token_auth(monkeypatch):
    monkeypatch.setenv("DEVOPS_TOKEN", "test-token")


# ---------------------------------------------------------------------------
# _ensure_rel_file_path
# ---------------------------------------------------------------------------


class TestEnsureRelFilePath:
    def test_adds_leading_slash_when_missing(self):
        assert _ensure_rel_file_path("src/foo.cs") == "/src/foo.cs"

    def test_does_not_double_slash(self):
        assert _ensure_rel_file_path("/src/foo.cs") == "/src/foo.cs"

    def test_returns_none_for_none(self):
        assert _ensure_rel_file_path(None) is None

    def test_returns_empty_string_unchanged(self):
        # Empty string is falsy → the condition `file_path and ...` is False, returns as-is.
        assert _ensure_rel_file_path("") == ""


# ---------------------------------------------------------------------------
# get_pull_request
# ---------------------------------------------------------------------------


class TestGetPullRequest:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, PR_URL, json=PULL_REQUEST_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems.*"), json=WORK_ITEMS_LIST_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*wit/workItems.*"), json=WORK_ITEM_RESPONSE, status=200)

        get_pull_request(REPO, PR_ID)

        assert rsps_lib.calls[0].request.url == PR_URL

    @rsps_lib.activate
    def test_maps_response_to_simplified_shape(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, PR_URL, json=PULL_REQUEST_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems.*"), json=WORK_ITEMS_LIST_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*wit/workItems.*"), json=WORK_ITEM_RESPONSE, status=200)

        result = get_pull_request(REPO, PR_ID)

        assert result["prId"] == 42
        assert result["title"] == "Add new feature"
        assert result["status"] == "active"
        assert result["isDraft"] is False
        assert result["lastMergeSourceCommit"] == "a" * 40
        assert result["lastMergeTargetCommit"] == "b" * 40
        assert result["sourceRefName"] == "refs/heads/feature/my-feature"

    @rsps_lib.activate
    def test_fetches_and_embeds_work_items(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, PR_URL, json=PULL_REQUEST_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems.*"), json=WORK_ITEMS_LIST_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.GET, re.compile(r".*wit/workItems.*"), json=WORK_ITEM_RESPONSE, status=200)

        result = get_pull_request(REPO, PR_ID)

        assert len(result["workItems"]) == 1
        assert result["workItems"][0]["id"] == 101

    @rsps_lib.activate
    def test_returns_empty_work_items_when_no_link(self, devops_url, token_auth):
        no_wi_url = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/99"
        rsps_lib.add(rsps_lib.GET, no_wi_url, json=PULL_REQUEST_NO_WORKITEMS_RESPONSE, status=200)

        result = get_pull_request(REPO, 99)

        assert result["workItems"] == []
        assert len(rsps_lib.calls) == 1  # No additional fetches


# ---------------------------------------------------------------------------
# list_pull_request_threads
# ---------------------------------------------------------------------------


class TestListPullRequestThreads:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=THREADS_RESPONSE, status=200)

        list_pull_request_threads(REPO, PR_ID)

        assert rsps_lib.calls[0].request.url == THREADS_URL

    @rsps_lib.activate
    def test_returns_only_text_comment_threads(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=THREADS_RESPONSE, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        # Thread 10 has text comment → included; thread 11 system only → excluded;
        # thread 12 deleted → excluded
        assert len(result) == 1
        assert result[0]["thread_id"] == 10

    @rsps_lib.activate
    def test_thread_includes_file_path_and_line(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=THREADS_RESPONSE, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        assert result[0]["file_path"] == "/src/foo.cs"
        assert result[0]["line"] == 42

    @rsps_lib.activate
    def test_thread_includes_status(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=THREADS_RESPONSE, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        assert result[0]["status"] == "active"

    @rsps_lib.activate
    def test_comment_fields_are_mapped(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=THREADS_RESPONSE, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        comment = result[0]["comments"][0]
        assert comment["comment_id"] == 1
        assert comment["author"] == "Alice"
        assert comment["content"] == "Please fix this."

    @rsps_lib.activate
    def test_thread_without_context_fields_omitted(self, devops_url, token_auth):
        # Thread with no threadContext
        payload = {
            "value": [
                {
                    "id": 20,
                    "publishedDate": "2024-01-17T10:00:00Z",
                    "lastUpdatedDate": "2024-01-17T10:00:00Z",
                    "isDeleted": False,
                    "pullRequestThreadContext": None,
                    "comments": [
                        {
                            "id": 1,
                            "commentType": "text",
                            "isDeleted": False,
                            "author": {"displayName": "Bob"},
                            "content": "General comment",
                            "parentCommentId": 0,
                        }
                    ],
                }
            ]
        }
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=payload, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        assert "file_path" not in result[0]
        assert "line" not in result[0]

    @rsps_lib.activate
    def test_author_none_handled_gracefully(self, devops_url, token_auth):
        payload = {
            "value": [
                {
                    "id": 30,
                    "publishedDate": "2024-01-17T10:00:00Z",
                    "lastUpdatedDate": "2024-01-17T10:00:00Z",
                    "isDeleted": False,
                    "pullRequestThreadContext": None,
                    "comments": [
                        {
                            "id": 1,
                            "commentType": "text",
                            "isDeleted": False,
                            "author": None,
                            "content": "Anonymous comment",
                            "parentCommentId": 0,
                        }
                    ],
                }
            ]
        }
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=payload, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        assert result[0]["comments"][0]["author"] is None

    @rsps_lib.activate
    def test_deleted_text_comment_excluded(self, devops_url, token_auth):
        """Thread whose only comment is a text+deleted comment → thread omitted."""
        payload = {
            "value": [
                {
                    "id": 40,
                    "publishedDate": "2024-01-17T10:00:00Z",
                    "lastUpdatedDate": "2024-01-17T10:00:00Z",
                    "isDeleted": False,
                    "pullRequestThreadContext": None,
                    "comments": [
                        {
                            "id": 1,
                            "commentType": "text",
                            "isDeleted": True,
                            "author": {"displayName": "Alice"},
                            "content": "Was here",
                            "parentCommentId": 0,
                        }
                    ],
                }
            ]
        }
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json=payload, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        # The comment is deleted, so the comments list is empty → thread skipped
        assert result == []

    @rsps_lib.activate
    def test_empty_threads_returns_empty_list(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREADS_URL, json={"value": []}, status=200)

        result = list_pull_request_threads(REPO, PR_ID)

        assert result == []


# ---------------------------------------------------------------------------
# list_pull_request_thread_comments
# ---------------------------------------------------------------------------


class TestListPullRequestThreadComments:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREAD_URL, json=SINGLE_THREAD_RESPONSE, status=200)

        list_pull_request_thread_comments(REPO, PR_ID, THREAD_ID)

        assert rsps_lib.calls[0].request.url == THREAD_URL

    @rsps_lib.activate
    def test_returns_thread_metadata(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREAD_URL, json=SINGLE_THREAD_RESPONSE, status=200)

        result = list_pull_request_thread_comments(REPO, PR_ID, THREAD_ID)

        assert result["thread_id"] == 10
        assert result["status"] == "active"

    @rsps_lib.activate
    def test_excludes_deleted_comments(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, THREAD_URL, json=SINGLE_THREAD_RESPONSE, status=200)

        result = list_pull_request_thread_comments(REPO, PR_ID, THREAD_ID)

        # SINGLE_THREAD_RESPONSE has 1 text + 1 deleted → only 1 returned
        assert len(result["comments"]) == 1
        assert result["comments"][0]["comment_id"] == 1

    @rsps_lib.activate
    def test_excludes_deleted_text_comments(self, devops_url, token_auth):
        payload = {
            "id": 10,
            "publishedDate": "2024-01-16T10:00:00Z",
            "lastUpdatedDate": "2024-01-16T11:00:00Z",
            "status": "active",
            "comments": [
                {
                    "id": 1,
                    "parentCommentId": 0,
                    "commentType": "text",
                    "isDeleted": True,
                    "author": {"displayName": "Alice"},
                    "content": "Deleted text comment",
                }
            ],
        }
        rsps_lib.add(rsps_lib.GET, THREAD_URL, json=payload, status=200)

        result = list_pull_request_thread_comments(REPO, PR_ID, THREAD_ID)

        assert result["comments"] == []

    @rsps_lib.activate
    def test_excludes_non_text_non_deleted_comments(self, devops_url, token_auth):
        payload = {
            "id": 10,
            "publishedDate": "2024-01-16T10:00:00Z",
            "lastUpdatedDate": "2024-01-16T11:00:00Z",
            "status": "active",
            "comments": [
                {
                    "id": 5,
                    "parentCommentId": 0,
                    "commentType": "system",
                    "isDeleted": False,
                    "author": {"displayName": "System"},
                    "content": "Auto comment",
                }
            ],
        }
        rsps_lib.add(rsps_lib.GET, THREAD_URL, json=payload, status=200)

        result = list_pull_request_thread_comments(REPO, PR_ID, THREAD_ID)

        assert result["comments"] == []


# ---------------------------------------------------------------------------
# create_pull_request_comment
# ---------------------------------------------------------------------------


class TestCreatePullRequestComment:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = f"{THREADS_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.POST, expected_url, json=CREATE_THREAD_RESPONSE, status=200)

        create_pull_request_comment(REPO, PR_ID, "Looks good!")

        assert rsps_lib.calls[0].request.url == expected_url

    @rsps_lib.activate
    def test_returns_thread_and_comment_ids(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*threads.*"), json=CREATE_THREAD_RESPONSE, status=200)

        result = create_pull_request_comment(REPO, PR_ID, "Looks good!")

        assert result["threadId"] == 20
        assert result["commentId"] == 1
        assert result["parentCommentId"] == 0

    @rsps_lib.activate
    def test_sends_comment_content_in_payload(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*threads.*"), json=CREATE_THREAD_RESPONSE, status=200)

        create_pull_request_comment(REPO, PR_ID, "My comment text")

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["comments"][0]["content"] == "My comment text"
        assert body["comments"][0]["commentType"] == 1

    @rsps_lib.activate
    def test_inline_comment_includes_thread_context(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*threads.*"), json=CREATE_THREAD_RESPONSE, status=200)

        create_pull_request_comment(REPO, PR_ID, "Inline!", file_path="src/foo.cs", line_number=10)

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert "threadContext" in body
        assert body["threadContext"]["filePath"] == "/src/foo.cs"
        assert body["threadContext"]["rightFileStart"]["line"] == 10

    @rsps_lib.activate
    def test_inline_comment_normalises_file_path(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*threads.*"), json=CREATE_THREAD_RESPONSE, status=200)

        create_pull_request_comment(REPO, PR_ID, "Inline!", file_path="/src/foo.cs", line_number=5)

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["threadContext"]["filePath"] == "/src/foo.cs"

    @rsps_lib.activate
    def test_no_thread_context_when_line_is_zero(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*threads.*"), json=CREATE_THREAD_RESPONSE, status=200)

        create_pull_request_comment(REPO, PR_ID, "No line", file_path="src/foo.cs", line_number=0)

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert "threadContext" not in body

    @rsps_lib.activate
    def test_no_thread_context_when_no_file_path(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*threads.*"), json=CREATE_THREAD_RESPONSE, status=200)

        create_pull_request_comment(REPO, PR_ID, "General comment")

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert "threadContext" not in body

    @rsps_lib.activate
    def test_returns_none_comment_id_when_no_comments_in_response(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*threads.*"), json={"id": 99, "comments": []}, status=200)

        result = create_pull_request_comment(REPO, PR_ID, "test")

        assert result["threadId"] == 99
        assert result["commentId"] is None
        assert result["parentCommentId"] is None


# ---------------------------------------------------------------------------
# reply_pull_request_comment
# ---------------------------------------------------------------------------


class TestReplyPullRequestComment:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = f"{THREAD_URL}/comments?api-version=7.1"
        rsps_lib.add(rsps_lib.POST, expected_url, json=REPLY_COMMENT_RESPONSE, status=200)

        reply_pull_request_comment(REPO, PR_ID, THREAD_ID, "My reply")

        assert rsps_lib.calls[0].request.url == expected_url

    @rsps_lib.activate
    def test_returns_correct_ids(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*comments.*"), json=REPLY_COMMENT_RESPONSE, status=200)

        result = reply_pull_request_comment(REPO, PR_ID, THREAD_ID, "My reply")

        assert result["threadId"] == THREAD_ID
        assert result["commentId"] == 3
        assert result["parentCommentId"] == 1

    @rsps_lib.activate
    def test_sends_correct_payload(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*comments.*"), json=REPLY_COMMENT_RESPONSE, status=200)

        reply_pull_request_comment(REPO, PR_ID, THREAD_ID, "Reply text")

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["content"] == "Reply text"
        assert body["commentType"] == 1


# ---------------------------------------------------------------------------
# update_pull_request_thread
# ---------------------------------------------------------------------------


class TestUpdatePullRequestThread:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = f"{THREAD_URL}?api-version=7.1"
        rsps_lib.add(rsps_lib.PATCH, expected_url, json=UPDATE_THREAD_RESPONSE, status=200)

        update_pull_request_thread(REPO, PR_ID, THREAD_ID, status=2)

        assert rsps_lib.calls[0].request.url == expected_url

    @rsps_lib.activate
    def test_sends_status_in_payload(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*threads.*"), json=UPDATE_THREAD_RESPONSE, status=200)

        update_pull_request_thread(REPO, PR_ID, THREAD_ID, status=2)

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["status"] == 2

    @rsps_lib.activate
    def test_returns_thread_id_and_status(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*threads.*"), json=UPDATE_THREAD_RESPONSE, status=200)

        result = update_pull_request_thread(REPO, PR_ID, THREAD_ID, status=2)

        assert result["threadId"] == 10
        assert result["status"] == "fixed"


# ---------------------------------------------------------------------------
# update_pull_request_comment
# ---------------------------------------------------------------------------


class TestUpdatePullRequestComment:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = (
            f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/"
            f"{PR_ID}/threads/{THREAD_ID}/comments/{COMMENT_ID}?api-version=7.1"
        )
        rsps_lib.add(rsps_lib.PATCH, expected_url, json=UPDATE_COMMENT_RESPONSE, status=200)

        update_pull_request_comment(REPO, PR_ID, THREAD_ID, "Updated text", COMMENT_ID, 0)

        assert rsps_lib.calls[0].request.url == expected_url

    @rsps_lib.activate
    def test_sends_correct_payload(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*comments.*"), json=UPDATE_COMMENT_RESPONSE, status=200)

        update_pull_request_comment(REPO, PR_ID, THREAD_ID, "Updated text", COMMENT_ID, 0)

        import json
        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["content"] == "Updated text"
        assert body["parentCommentId"] == 0
        assert body["commentType"] == 1

    @rsps_lib.activate
    def test_returns_correct_ids(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*comments.*"), json=UPDATE_COMMENT_RESPONSE, status=200)

        result = update_pull_request_comment(REPO, PR_ID, THREAD_ID, "Updated", COMMENT_ID, 0)

        assert result["threadId"] == THREAD_ID
        assert result["commentId"] == 1
        assert result["parentCommentId"] == 0


# ---------------------------------------------------------------------------
# delete_pull_request_comment
# ---------------------------------------------------------------------------


class TestDeletePullRequestComment:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        expected_url = (
            f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/"
            f"{PR_ID}/threads/{THREAD_ID}/comments/{COMMENT_ID}?api-version=7.1"
        )
        rsps_lib.add(rsps_lib.DELETE, expected_url, status=204)

        delete_pull_request_comment(REPO, PR_ID, THREAD_ID, COMMENT_ID)

        assert rsps_lib.calls[0].request.url == expected_url
        assert rsps_lib.calls[0].request.method == "DELETE"

    @rsps_lib.activate
    def test_returns_none(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.DELETE, re.compile(r".*comments.*"), status=204)

        result = delete_pull_request_comment(REPO, PR_ID, THREAD_ID, COMMENT_ID)

        assert result is None
