"""Tests for pull_request_tools — all public tools and the private helper.

Auth path coverage lives in test_shared.py. These tests use the Bearer token
path only so responses intercepts requests without NTLM negotiation.
"""

import json
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
    write_pull_request,
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
write_pull_request = write_pull_request.fn

BASE_URL = "https://devops.example.com/org/project"
REPO = "MyRepo"
PR_ID = 42
THREAD_ID = 10
COMMENT_ID = 1

PR_URL = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}"
THREADS_URL = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}/threads"
THREAD_URL = f"{THREADS_URL}/{THREAD_ID}"
WRITE_PR_URL = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests?api-version=7.1"
WRITE_PR_ID_URL = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}?api-version=7.1"
CONNECTION_DATA_URL = f"{BASE_URL}/_apis/connectionData?api-version=7.1"

WRITE_PR_RESPONSE = {
    **PULL_REQUEST_RESPONSE,
    "codeReviewId": 500,
    "repository": {"name": REPO, "project": {"name": "Project"}},
    "createdBy": {"displayName": "Alice", "uniqueName": "alice@example.com"},
}

CONNECTION_DATA_RESPONSE = {"authenticatedUser": {"id": "user-1"}}


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
# write_pull_request
# ---------------------------------------------------------------------------


class TestWritePullRequest:
    @rsps_lib.activate
    def test_create_builds_payload_and_returns_trimmed_response(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, WRITE_PR_URL, json=WRITE_PR_RESPONSE, status=200)

        result = write_pull_request(
            "create",
            repository_id=REPO,
            source_ref_name="refs/heads/feature/new-tool",
            target_ref_name="refs/heads/main",
            title="Add PR write tool",
            description="Create a write tool",
            is_draft=True,
            work_items="101 102",
            labels=["ready", "mcp"],
        )

        body = json.loads(rsps_lib.calls[0].request.body)
        assert rsps_lib.calls[0].request.url == WRITE_PR_URL
        assert body["sourceRefName"] == "refs/heads/feature/new-tool"
        assert body["targetRefName"] == "refs/heads/main"
        assert body["title"] == "Add PR write tool"
        assert body["isDraft"] is True
        assert body["supportsIterations"] is True
        assert body["workItemRefs"] == [{"id": "101"}, {"id": "102"}]
        assert body["labels"] == [{"name": "ready"}, {"name": "mcp"}]
        assert result["prId"] == 42
        assert result["repository"] == REPO
        assert result["createdBy"]["displayName"] == "Alice"

    @rsps_lib.activate
    def test_create_validates_required_fields_before_calling_api(self, devops_url, token_auth):
        result = write_pull_request("create", repository_id=REPO, source_ref_name="refs/heads/topic")

        assert result == {"error": "target_ref_name is required for create"}
        assert len(rsps_lib.calls) == 0

    @pytest.mark.parametrize(
        ("kwargs", "expected_error"),
        [
            ({}, "repository_id is required for create"),
            ({"repository_id": REPO}, "source_ref_name is required for create"),
            (
                {"repository_id": REPO, "source_ref_name": "refs/heads/topic", "target_ref_name": "refs/heads/main"},
                "title is required for create",
            ),
        ],
    )
    @rsps_lib.activate
    def test_create_validates_each_required_field_before_calling_api(self, devops_url, token_auth, kwargs, expected_error):
        result = write_pull_request("create", **kwargs)

        assert result == {"error": expected_error}
        assert len(rsps_lib.calls) == 0

    @rsps_lib.activate
    def test_create_without_optional_work_items_sends_empty_work_item_refs(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, WRITE_PR_URL, json=WRITE_PR_RESPONSE, status=200)

        write_pull_request(
            "create",
            repository_id=REPO,
            source_ref_name="refs/heads/feature/no-work-items",
            target_ref_name="refs/heads/main",
            title="No work items",
        )

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["workItemRefs"] == []

    @rsps_lib.activate
    def test_create_includes_fork_source_repository(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, WRITE_PR_URL, json=WRITE_PR_RESPONSE, status=200)

        write_pull_request(
            "create",
            repository_id=REPO,
            source_ref_name="refs/heads/feature/forked",
            target_ref_name="refs/heads/main",
            title="From fork",
            fork_source_repository_id="fork-repo-id",
        )

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["forkSource"] == {"repository": {"id": "fork-repo-id"}}

    @rsps_lib.activate
    def test_update_sets_auto_complete_options(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, CONNECTION_DATA_URL, json=CONNECTION_DATA_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PATCH, WRITE_PR_ID_URL, json=WRITE_PR_RESPONSE, status=200)

        result = write_pull_request(
            "update",
            repository_id=REPO,
            pull_request_id=PR_ID,
            title="Updated title",
            auto_complete=True,
            merge_strategy="Squash",
            merge_commit_message="Merge by squash",
            delete_source_branch=True,
        )

        body = json.loads(rsps_lib.calls[1].request.body)
        assert rsps_lib.calls[0].request.url == CONNECTION_DATA_URL
        assert rsps_lib.calls[1].request.url == WRITE_PR_ID_URL
        assert body["title"] == "Updated title"
        assert body["autoCompleteSetBy"] == {"id": "user-1"}
        assert body["completionOptions"] == {
            "deleteSourceBranch": True,
            "transitionWorkItems": True,
            "bypassPolicy": False,
            "mergeStrategy": 2,
            "mergeCommitMessage": "Merge by squash",
        }
        assert result["title"] == "Add new feature"

    @rsps_lib.activate
    def test_update_requires_bypass_reason_when_bypassing_policy(self, devops_url, token_auth):
        result = write_pull_request(
            "update",
            repository_id=REPO,
            pull_request_id=PR_ID,
            auto_complete=True,
            bypass_policy=True,
        )

        assert result == {"error": "bypass_reason is required when bypass_policy is true"}
        assert len(rsps_lib.calls) == 0

    @pytest.mark.parametrize(
        ("kwargs", "expected_error"),
        [
            ({}, "repository_id is required for update"),
            ({"repository_id": REPO}, "pull_request_id is required for update"),
            ({"repository_id": REPO, "pull_request_id": PR_ID, "status": "Completed"}, "status must be Active or Abandoned"),
            (
                {"repository_id": REPO, "pull_request_id": PR_ID, "auto_complete": True, "merge_strategy": "Bad"},
                "merge_strategy must be NoFastForward, Squash, Rebase, or RebaseMerge",
            ),
        ],
    )
    @rsps_lib.activate
    def test_update_validates_inputs_before_patch(self, devops_url, token_auth, kwargs, expected_error):
        if kwargs.get("auto_complete"):
            rsps_lib.add(rsps_lib.GET, CONNECTION_DATA_URL, json=CONNECTION_DATA_RESPONSE, status=200)

        result = write_pull_request("update", **kwargs)

        assert result == {"error": expected_error}
        assert not any(call.request.method == "PATCH" for call in rsps_lib.calls)

    @rsps_lib.activate
    def test_update_returns_error_when_auto_complete_user_is_missing(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, CONNECTION_DATA_URL, json={"authenticatedUser": {}}, status=200)

        result = write_pull_request("update", repository_id=REPO, pull_request_id=PR_ID, auto_complete=True)

        assert result == {"error": "Could not determine authenticated user ID."}
        assert len(rsps_lib.calls) == 1

    @rsps_lib.activate
    def test_update_clears_auto_complete(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, WRITE_PR_ID_URL, json=WRITE_PR_RESPONSE, status=200)

        write_pull_request("update", repository_id=REPO, pull_request_id=PR_ID, auto_complete=False)

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["autoCompleteSetBy"] is None
        assert body["completionOptions"] is None

    @rsps_lib.activate
    def test_update_sends_optional_scalar_fields_and_status(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, WRITE_PR_ID_URL, json=WRITE_PR_RESPONSE, status=200)

        write_pull_request(
            "update",
            repository_id=REPO,
            pull_request_id=PR_ID,
            description="Updated description",
            is_draft=True,
            target_ref_name="refs/heads/release/v5.16.0",
            status="Abandoned",
        )

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body == {
            "description": "Updated description",
            "isDraft": True,
            "targetRefName": "refs/heads/release/v5.16.0",
            "status": 2,
        }

    @rsps_lib.activate
    def test_update_includes_bypass_reason_when_bypassing_policy(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, CONNECTION_DATA_URL, json=CONNECTION_DATA_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PATCH, WRITE_PR_ID_URL, json=WRITE_PR_RESPONSE, status=200)

        write_pull_request(
            "update",
            repository_id=REPO,
            pull_request_id=PR_ID,
            auto_complete=True,
            bypass_policy=True,
            bypass_reason="Emergency hotfix",
        )

        body = json.loads(rsps_lib.calls[1].request.body)
        assert body["completionOptions"]["bypassPolicy"] is True
        assert body["completionOptions"]["bypassReason"] == "Emergency hotfix"

    @rsps_lib.activate
    def test_update_requires_at_least_one_update_field(self, devops_url, token_auth):
        result = write_pull_request("update", repository_id=REPO, pull_request_id=PR_ID)

        assert result == {
            "error": (
                "At least one field (title, description, is_draft, target_ref_name, status, "
                "auto_complete options, or labels) must be provided for update."
            )
        }
        assert len(rsps_lib.calls) == 0

    @rsps_lib.activate
    def test_update_replaces_labels_without_other_patch_fields(self, devops_url, token_auth):
        labels_url = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}/labels?api-version=7.1"
        label_url = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}/labels/old-label?api-version=7.1"
        rsps_lib.add(rsps_lib.GET, labels_url, json={"value": [{"id": "old-label", "name": "old"}]}, status=200)
        rsps_lib.add(rsps_lib.DELETE, label_url, status=204)
        rsps_lib.add(rsps_lib.POST, labels_url, json={"id": "new-label", "name": "new"}, status=200)
        rsps_lib.add(rsps_lib.GET, WRITE_PR_ID_URL, json=WRITE_PR_RESPONSE, status=200)

        result = write_pull_request("update", repository_id=REPO, pull_request_id=PR_ID, labels=["new"])

        assert [call.request.method for call in rsps_lib.calls] == ["GET", "DELETE", "POST", "GET"]
        assert json.loads(rsps_lib.calls[2].request.body) == {"name": "new"}
        assert result["prId"] == PR_ID

    @rsps_lib.activate
    def test_update_reviewers_adds_each_reviewer(self, devops_url, token_auth):
        reviewer_url = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}/reviewers/user-1?api-version=7.1"
        rsps_lib.add(
            rsps_lib.PUT,
            reviewer_url,
            json={"displayName": "Bob", "id": "user-1", "uniqueName": "bob@example.com", "vote": 0},
            status=200,
        )

        result = write_pull_request(
            "update_reviewers",
            repository_id=REPO,
            pull_request_id=PR_ID,
            reviewer_ids=["user-1"],
            reviewer_action="add",
        )

        assert json.loads(rsps_lib.calls[0].request.body) == {"id": "user-1"}
        assert result == [
            {
                "displayName": "Bob",
                "id": "user-1",
                "uniqueName": "bob@example.com",
                "vote": 0,
                "hasDeclined": None,
                "isFlagged": None,
            }
        ]

    @rsps_lib.activate
    def test_update_reviewers_removes_each_reviewer(self, devops_url, token_auth):
        reviewer_url = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}/reviewers/user-1?api-version=7.1"
        rsps_lib.add(rsps_lib.DELETE, reviewer_url, status=204)

        result = write_pull_request(
            "update_reviewers",
            repository_id=REPO,
            pull_request_id=PR_ID,
            reviewer_ids=["user-1"],
            reviewer_action="remove",
        )

        assert rsps_lib.calls[0].request.method == "DELETE"
        assert result == {"message": "Reviewers with IDs user-1 removed from pull request 42."}

    @pytest.mark.parametrize(
        ("kwargs", "expected_error"),
        [
            ({}, "repository_id is required for update_reviewers"),
            ({"repository_id": REPO}, "pull_request_id is required for update_reviewers"),
            ({"repository_id": REPO, "pull_request_id": PR_ID}, "reviewer_ids is required for update_reviewers"),
            (
                {"repository_id": REPO, "pull_request_id": PR_ID, "reviewer_ids": ["user-1"]},
                "reviewer_action must be add or remove",
            ),
        ],
    )
    @rsps_lib.activate
    def test_update_reviewers_validates_inputs(self, devops_url, token_auth, kwargs, expected_error):
        result = write_pull_request("update_reviewers", **kwargs)

        assert result == {"error": expected_error}
        assert len(rsps_lib.calls) == 0

    @rsps_lib.activate
    def test_vote_casts_authenticated_user_vote(self, devops_url, token_auth):
        reviewer_url = f"{BASE_URL}/_apis/git/repositories/{REPO}/pullRequests/{PR_ID}/reviewers/user-1?api-version=7.1"
        rsps_lib.add(rsps_lib.GET, CONNECTION_DATA_URL, json=CONNECTION_DATA_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PUT, reviewer_url, json={"id": "user-1", "vote": -10}, status=200)

        result = write_pull_request("vote", repository_id=REPO, pull_request_id=PR_ID, vote="Rejected")

        body = json.loads(rsps_lib.calls[1].request.body)
        assert body == {"id": "user-1", "vote": -10}
        assert result == {"message": "Successfully cast vote 'Rejected' on PR #42."}

    @pytest.mark.parametrize(
        ("kwargs", "expected_error"),
        [
            ({}, "repository_id is required for vote"),
            ({"repository_id": REPO}, "pull_request_id is required for vote"),
            ({"repository_id": REPO, "pull_request_id": PR_ID}, "vote must be Approved, ApprovedWithSuggestions, NoVote, WaitingForAuthor, or Rejected"),
        ],
    )
    @rsps_lib.activate
    def test_vote_validates_inputs(self, devops_url, token_auth, kwargs, expected_error):
        result = write_pull_request("vote", **kwargs)

        assert result == {"error": expected_error}
        assert len(rsps_lib.calls) == 0

    @rsps_lib.activate
    def test_vote_returns_error_when_authenticated_user_is_missing(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, CONNECTION_DATA_URL, json={"authenticatedUser": {}}, status=200)

        result = write_pull_request("vote", repository_id=REPO, pull_request_id=PR_ID, vote="Approved")

        assert result == {"error": "Could not determine authenticated user ID."}
        assert len(rsps_lib.calls) == 1

    @rsps_lib.activate
    def test_unknown_write_action_returns_error(self, devops_url, token_auth):
        result = write_pull_request("unknown")

        assert result == {"error": "Unknown action: unknown"}
        assert len(rsps_lib.calls) == 0


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
