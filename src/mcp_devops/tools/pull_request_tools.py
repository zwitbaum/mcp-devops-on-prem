from typing import Annotated

from mcp_devops.shared import (
    devops_api_url,
    mcp,
    devops_api_get,
    devops_api_post,
    devops_api_put,
    devops_api_patch,
    devops_api_delete,
    fetch_work_item,
    DEVOPS_API_VERSION,
)


def _ensure_rel_file_path(file_path: str | None) -> str | None:
    """Ensure file path starts with a slash, as required by the Azure DevOps API."""
    return f"/{file_path}" if file_path and not file_path.startswith("/") else file_path


_PULL_REQUEST_STATUS_BY_NAME = {
    "Active": 1,
    "Abandoned": 2,
}

_PULL_REQUEST_VOTE_BY_NAME = {
    "Approved": 10,
    "ApprovedWithSuggestions": 5,
    "NoVote": 0,
    "WaitingForAuthor": -5,
    "Rejected": -10,
}

_MERGE_STRATEGY_BY_NAME = {
    "NoFastForward": 1,
    "Squash": 2,
    "Rebase": 3,
    "RebaseMerge": 4,
}


def _split_work_item_ids(work_items: str | None) -> list[dict[str, str]]:
    if not work_items:
        return []
    return [{"id": item.strip()} for item in work_items.split() if item.strip()]


def _trim_pull_request_response(data: dict, include_description: bool = True) -> dict:
    result = {
        "prId": data.get("pullRequestId"),
        "codeReviewId": data.get("codeReviewId"),
        "repository": (data.get("repository") or {}).get("name"),
        "status": data.get("status"),
        "createdBy": {
            "displayName": ((data.get("createdBy") or {}).get("displayName")),
            "uniqueName": ((data.get("createdBy") or {}).get("uniqueName")),
        },
        "creationDate": data.get("creationDate"),
        "closedDate": data.get("closedDate"),
        "title": data.get("title"),
        "isDraft": data.get("isDraft"),
        "sourceRefName": data.get("sourceRefName"),
        "targetRefName": data.get("targetRefName"),
        "project": ((data.get("repository") or {}).get("project") or {}).get("name"),
    }
    if include_description:
        result["description"] = data.get("description") or ""
    return result


def _get_current_user_id() -> str | None:
    url = f"{devops_api_url}/_apis/connectionData?api-version={DEVOPS_API_VERSION}"
    data = devops_api_get(url)
    return (data.get("authenticatedUser") or {}).get("id")


def _labels_url(repository_id: str, pull_request_id: int) -> str:
    return (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
        f"/{pull_request_id}/labels?api-version={DEVOPS_API_VERSION}"
    )


def _label_url(repository_id: str, pull_request_id: int, label_id: str) -> str:
    return (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
        f"/{pull_request_id}/labels/{label_id}?api-version={DEVOPS_API_VERSION}"
    )


def _reviewer_url(repository_id: str, pull_request_id: int, reviewer_id: str) -> str:
    return (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
        f"/{pull_request_id}/reviewers/{reviewer_id}?api-version={DEVOPS_API_VERSION}"
    )


def _pull_request_url(repository_id: str, pull_request_id: int | None = None) -> str:
    url = f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
    if pull_request_id is not None:
        url = f"{url}/{pull_request_id}"
    return f"{url}?api-version={DEVOPS_API_VERSION}"


def _replace_pull_request_labels(repository_id: str, pull_request_id: int, labels: list[str]) -> None:
    current_labels = devops_api_get(_labels_url(repository_id, pull_request_id)).get("value", [])
    for label in current_labels:
        label_id = label.get("id") or label.get("name")
        if label_id:
            devops_api_delete(_label_url(repository_id, pull_request_id, label_id))
    for label in labels:
        devops_api_post(_labels_url(repository_id, pull_request_id), {"name": label})


def _require(value, message: str) -> str | None:
    return None if value else message


@mcp.tool(
    name="devops_pull_request_write",
    description=(
        "Write operations for pull requests. Use the action parameter to create or update pull requests, "
        "add or remove reviewers, or cast the authenticated user's vote."
    ),
    annotations={"readOnlyHint": False},
)
def write_pull_request(
    action: Annotated[
        str,
        "Action to perform: create, update, update_reviewers, or vote.",
    ],
    repository_id: Annotated[str | None, "Repository name or ID. Required for all actions."] = None,
    pull_request_id: Annotated[
        int | None,
        "Pull request ID. Required for update, update_reviewers, and vote.",
    ] = None,
    source_ref_name: Annotated[
        str | None,
        "Source branch ref for create, for example refs/heads/feature-branch.",
    ] = None,
    target_ref_name: Annotated[
        str | None,
        "Target branch ref for create or update, for example refs/heads/main.",
    ] = None,
    title: Annotated[str | None, "Pull request title. Required for create; optional for update."] = None,
    description: Annotated[
        str | None,
        "Pull request description. Used for create and update.",
    ] = None,
    is_draft: Annotated[bool | None, "Whether the pull request is a draft. Used for create and update."] = None,
    work_items: Annotated[
        str | None,
        "Space-separated work item IDs to associate. Used for create.",
    ] = None,
    fork_source_repository_id: Annotated[
        str | None,
        "Fork source repository ID. Used for create.",
    ] = None,
    labels: Annotated[list[str] | None, "Label names. Used for create and update."] = None,
    status: Annotated[str | None, "New status for update: Active or Abandoned."] = None,
    auto_complete: Annotated[bool | None, "Set or clear autocomplete. Used for update."] = None,
    merge_strategy: Annotated[str | None, "Merge strategy for autocomplete. Used for update."] = None,
    merge_commit_message: Annotated[str | None, "Commit message for autocomplete. Used for update."] = None,
    delete_source_branch: Annotated[bool, "Delete source branch on autocomplete. Used for update."] = False,
    transition_work_items: Annotated[bool, "Transition work items on autocomplete. Used for update."] = True,
    bypass_policy: Annotated[bool, "Bypass branch policies on autocomplete. Requires bypass_reason."] = False,
    bypass_reason: Annotated[str | None, "Reason for bypassing branch policies."] = None,
    reviewer_ids: Annotated[list[str] | None, "Reviewer IDs. Required for update_reviewers."] = None,
    reviewer_action: Annotated[str | None, "Reviewer action: add or remove. Required for update_reviewers."] = None,
    vote: Annotated[
        str | None,
        "Vote to cast: Approved, ApprovedWithSuggestions, NoVote, WaitingForAuthor, or Rejected.",
    ] = None,
) -> object:
    """Create or update pull requests, reviewers, and authenticated-user votes."""
    if action == "create":
        if error := _require(repository_id, "repository_id is required for create"):
            return {"error": error}
        if error := _require(source_ref_name, "source_ref_name is required for create"):
            return {"error": error}
        if error := _require(target_ref_name, "target_ref_name is required for create"):
            return {"error": error}
        if error := _require(title, "title is required for create"):
            return {"error": error}

        payload = {
            "sourceRefName": source_ref_name,
            "targetRefName": target_ref_name,
            "title": title,
            "description": description,
            "isDraft": bool(is_draft),
            "workItemRefs": _split_work_item_ids(work_items),
            "supportsIterations": True,
        }
        if fork_source_repository_id:
            payload["forkSource"] = {"repository": {"id": fork_source_repository_id}}
        if labels:
            payload["labels"] = [{"name": label} for label in labels]

        response = devops_api_post(_pull_request_url(repository_id), payload)
        return _trim_pull_request_response(response)

    if action == "update":
        if error := _require(repository_id, "repository_id is required for update"):
            return {"error": error}
        if error := _require(pull_request_id, "pull_request_id is required for update"):
            return {"error": error}

        payload = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if is_draft is not None:
            payload["isDraft"] = is_draft
        if target_ref_name is not None:
            payload["targetRefName"] = target_ref_name
        if status is not None:
            if status not in _PULL_REQUEST_STATUS_BY_NAME:
                return {"error": "status must be Active or Abandoned"}
            payload["status"] = _PULL_REQUEST_STATUS_BY_NAME[status]

        if auto_complete is not None:
            if auto_complete:
                if bypass_policy and not bypass_reason:
                    return {"error": "bypass_reason is required when bypass_policy is true"}
                user_id = _get_current_user_id()
                if not user_id:
                    return {"error": "Could not determine authenticated user ID."}
                payload["autoCompleteSetBy"] = {"id": user_id}
                completion_options = {
                    "deleteSourceBranch": delete_source_branch,
                    "transitionWorkItems": transition_work_items,
                    "bypassPolicy": bypass_policy,
                }
                if merge_strategy:
                    if merge_strategy not in _MERGE_STRATEGY_BY_NAME:
                        return {"error": "merge_strategy must be NoFastForward, Squash, Rebase, or RebaseMerge"}
                    completion_options["mergeStrategy"] = _MERGE_STRATEGY_BY_NAME[merge_strategy]
                if merge_commit_message:
                    completion_options["mergeCommitMessage"] = merge_commit_message
                if bypass_reason:
                    completion_options["bypassReason"] = bypass_reason
                payload["completionOptions"] = completion_options
            else:
                payload["autoCompleteSetBy"] = None
                payload["completionOptions"] = None

        if not payload and labels is None:
            return {
                "error": (
                    "At least one field (title, description, is_draft, target_ref_name, status, "
                    "auto_complete options, or labels) must be provided for update."
                )
            }

        if labels is not None:
            _replace_pull_request_labels(repository_id, pull_request_id, labels)

        response = (
            devops_api_patch(_pull_request_url(repository_id, pull_request_id), payload)
            if payload
            else devops_api_get(_pull_request_url(repository_id, pull_request_id))
        )
        return _trim_pull_request_response(response)

    if action == "update_reviewers":
        if error := _require(repository_id, "repository_id is required for update_reviewers"):
            return {"error": error}
        if error := _require(pull_request_id, "pull_request_id is required for update_reviewers"):
            return {"error": error}
        if not reviewer_ids:
            return {"error": "reviewer_ids is required for update_reviewers"}
        if reviewer_action not in {"add", "remove"}:
            return {"error": "reviewer_action must be add or remove"}

        if reviewer_action == "add":
            reviewers = []
            for reviewer_id in reviewer_ids:
                reviewer = devops_api_put(
                    _reviewer_url(repository_id, pull_request_id, reviewer_id),
                    {"id": reviewer_id},
                )
                reviewers.append(
                    {
                        "displayName": reviewer.get("displayName"),
                        "id": reviewer.get("id"),
                        "uniqueName": reviewer.get("uniqueName"),
                        "vote": reviewer.get("vote"),
                        "hasDeclined": reviewer.get("hasDeclined"),
                        "isFlagged": reviewer.get("isFlagged"),
                    }
                )
            return reviewers

        for reviewer_id in reviewer_ids:
            devops_api_delete(_reviewer_url(repository_id, pull_request_id, reviewer_id))
        return {"message": f"Reviewers with IDs {', '.join(reviewer_ids)} removed from pull request {pull_request_id}."}

    if action == "vote":
        if error := _require(repository_id, "repository_id is required for vote"):
            return {"error": error}
        if error := _require(pull_request_id, "pull_request_id is required for vote"):
            return {"error": error}
        if vote not in _PULL_REQUEST_VOTE_BY_NAME:
            return {"error": "vote must be Approved, ApprovedWithSuggestions, NoVote, WaitingForAuthor, or Rejected"}

        user_id = _get_current_user_id()
        if not user_id:
            return {"error": "Could not determine authenticated user ID."}
        payload = {"id": user_id, "vote": _PULL_REQUEST_VOTE_BY_NAME[vote]}
        devops_api_put(_reviewer_url(repository_id, pull_request_id, user_id), payload)
        return {"message": f"Successfully cast vote '{vote}' on PR #{pull_request_id}."}

    return {"error": f"Unknown action: {action}"}


@mcp.tool(
    name="devops_pull_request_get",
    description=(
        "Retrieve a pull request by ID. Use the 'lastMergeTargetCommit' and "
        "'lastMergeSourceCommit' from the result to obtain changes with "
        "'devops_repository_diffs_commits' tool."
    ),
    annotations={"readOnlyHint": True},
)
def get_pull_request(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "The ID of the pull request to retrieve."],
) -> object:
    """Fetch a single pull request by its integer ID."""
    url = f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests/{pull_request_id}"
    data = devops_api_get(url)

    # create a simplified result object
    result = {
        "prId": data.get("pullRequestId"),
        "status": data.get("status"),
        "creationDate": data.get("creationDate"),
        "title": data.get("title"),
        "description": data.get("description"),
        "sourceRefName": data.get("sourceRefName"),
        "targetRefName": data.get("targetRefName"),
        "isDraft": data.get("isDraft"),
        "lastMergeSourceCommit": data.get("lastMergeSourceCommit", {}).get("commitId"),
        "lastMergeTargetCommit": data.get("lastMergeTargetCommit", {}).get("commitId"),
        "workItems": data.get("_links", {}).get("workItems", {}).get("href", {}),
    }

    # Fetch work item details if any
    work_items = []
    if result.get("workItems"):
        work_item_json = devops_api_get(result["workItems"])
        for i in work_item_json.get("value", []):
            work_items.append(fetch_work_item(i.get("url")))
    result["workItems"] = work_items
    return result


@mcp.tool(
    name="devops_pull_request_list_threads",
    description=(
        "Retrieve a hierarchical list of non-deleted comment threads and their text comments for a pull request."
    ),
    annotations={"readOnlyHint": True},
)
def list_pull_request_threads(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "The ID of the pull request."],
) -> object:
    """List all comment threads for a given pull request."""
    url = f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests/{pull_request_id}/threads"
    response = devops_api_get(url)

    threads = []
    for thread in response.get("value", []):
        if thread.get("pullRequestThreadContext") is None and thread.get("isDeleted", False):
            continue

        thread_entry = {
            "thread_id": thread.get("id"),
            "published": thread.get("publishedDate"),
            "last_updated": thread.get("lastUpdatedDate"),
        }

        if thread.get("status") is not None:
            thread_entry["status"] = thread.get("status")

        thread_context = thread.get("threadContext")
        if thread_context:
            if thread_context.get("filePath") is not None:
                thread_entry["file_path"] = thread_context.get("filePath")
            right_file_start = thread_context.get("rightFileStart")
            if right_file_start and right_file_start.get("line") is not None:
                thread_entry["line"] = right_file_start.get("line")

        comments = []
        for comment in thread.get("comments", []):
            if comment.get("commentType") != "text" and not comment.get("isDeleted", False):
                continue
            if comment.get("isDeleted", False):
                continue
            comments.append(
                {
                    "comment_id": comment.get("id"),
                    "parent_comment_id": comment.get("parentCommentId"),
                    "author": (comment.get("author") or {}).get("displayName"),
                    "content": comment.get("content"),
                    "published": comment.get("publishedDate"),
                    "last_updated": comment.get("lastUpdatedDate"),
                    "last_content_updated": comment.get("lastContentUpdatedDate"),
                }
            )
        if not comments:
            continue
        thread_entry["comments"] = comments
        threads.append(thread_entry)

    return threads


@mcp.tool(
    name="devops_pull_request_list_thread_comments",
    description=("Retrieves a list of non-deleted text comments in a specific thread."),
    annotations={"readOnlyHint": True},
)
def list_pull_request_thread_comments(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "The ID of the pull request."],
    thread_id: Annotated[int, "The ID of the thread to retrieve."],
) -> object:
    """Get details of a specific pull request thread."""
    url = f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests/{pull_request_id}/threads/{thread_id}"
    response = devops_api_get(url)

    comments = []
    for comment in response.get("comments", []):
        if comment.get("commentType") != "text" and not comment.get("isDeleted", False):
            continue
        if comment.get("isDeleted", False):
            continue
        comments.append(
            {
                "comment_id": comment.get("id"),
                "parent_comment_id": comment.get("parentCommentId"),
                "author": (comment.get("author") or {}).get("displayName"),
                "content": comment.get("content"),
                "published": comment.get("publishedDate"),
                "last_updated": comment.get("lastUpdatedDate"),
                "last_content_updated": comment.get("lastContentUpdatedDate"),
            }
        )

    return {
        "thread_id": response.get("id"),
        "published": response.get("publishedDate"),
        "last_updated": response.get("lastUpdatedDate"),
        "status": response.get("status"),
        "comments": comments,
    }


@mcp.tool(
    name="devops_pull_request_create_comment",
    description=("Create a new thread with initial comment in the specified pull request."),
    annotations={"readOnlyHint": False},
)
def create_pull_request_comment(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    comment_content: Annotated[str, "The text content or markdown of the comment."],
    file_path: Annotated[str, "File path relative to the root of the repository."] = None,
    line_number: Annotated[int, "Optional 1-based line number for an inline comment."] = None,
) -> object:
    """Create a pull request thread (comment) on the specified PR."""
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
        f"/{pull_request_id}/threads?api-version={DEVOPS_API_VERSION}"
    )

    payload = {
        "comments": [
            {
                "parentCommentId": 0,
                "content": comment_content,
                "commentType": 1,
            }
        ],
        "status": 1,
    }

    if file_path and line_number is not None and line_number > 0:
        file_path = _ensure_rel_file_path(file_path)
        payload["threadContext"] = {
            "filePath": file_path,
            "rightFileStart": {"line": line_number, "offset": 1},
            "rightFileEnd": {"line": line_number, "offset": 1},
        }

    response = devops_api_post(url, payload)

    thread_id = response.get("id")
    comment_id = None
    parent_comment_id = None
    comments = response.get("comments") or []
    if comments:
        first = comments[0]
        comment_id = first.get("id")
        parent_comment_id = first.get("parentCommentId")

    return {
        "threadId": thread_id,
        "commentId": comment_id,
        "parentCommentId": parent_comment_id,
    }


@mcp.tool(
    name="devops_pull_request_reply_comment",
    description=("Replies to a specific comment on a pull request."),
    annotations={"readOnlyHint": False},
)
def reply_pull_request_comment(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    thread_id: Annotated[int, "Thread ID to reply to."],
    comment_content: Annotated[str, "The text content or markdown of the reply comment."],
) -> object:
    """Reply to an existing pull request thread (comment) on the specified PR."""
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
        f"/{pull_request_id}/threads/{thread_id}/comments?api-version={DEVOPS_API_VERSION}"
    )

    payload = {
        "parentCommentId": 0,
        "content": comment_content,
        "commentType": 1,
    }

    response = devops_api_post(url, payload)

    comment_id = response.get("id")
    parent_comment_id = response.get("parentCommentId")

    return {
        "threadId": thread_id,
        "commentId": comment_id,
        "parentCommentId": parent_comment_id,
    }


@mcp.tool(
    name="devops_pull_request_update_thread",
    description=("Update the status of a comment thread."),
    annotations={"readOnlyHint": False},
)
def update_pull_request_thread(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    thread_id: Annotated[int, "Thread ID to update."],
    status: Annotated[int, "New thread status (1=Active, 2=Fixed or Resolved, 3=WontFix, 4=Closed, 6=Pending)."],
) -> object:
    """Update the status of an existing pull request thread."""
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
        f"/{pull_request_id}/threads/{thread_id}?api-version={DEVOPS_API_VERSION}"
    )

    payload = {"status": status}

    response = devops_api_patch(url, payload)

    return {
        "threadId": response.get("id"),
        "status": response.get("status"),
    }


@mcp.tool(
    name="devops_pull_request_update_comment",
    description=("Update an existing comment in the specified pull request."),
    annotations={"readOnlyHint": False},
)
def update_pull_request_comment(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    thread_id: Annotated[int, "Thread ID to update."],
    comment_content: Annotated[str, "Updated text content."],
    comment_id: Annotated[int, "ID of the comment to update."],
    parent_comment_id: Annotated[int, "Parent comment id for replies."],
) -> object:
    """Update a text comment inside an existing pull request thread."""
    comment_url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests/"
        f"{pull_request_id}/threads/{thread_id}/comments/{comment_id}?api-version={DEVOPS_API_VERSION}"
    )

    payload = {
        "content": comment_content,
        "parentCommentId": parent_comment_id,
        "commentType": 1,
    }

    response = devops_api_patch(comment_url, payload)
    comment_id = response.get("id")
    parent_comment_id = response.get("parentCommentId")

    return {
        "threadId": thread_id,
        "commentId": comment_id,
        "parentCommentId": parent_comment_id,
    }


@mcp.tool(
    name="devops_pull_request_delete_comment",
    description=("Delete a comment from the specified pull request."),
    annotations={"readOnlyHint": False, "returnType": "void"},
)
def delete_pull_request_comment(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    thread_id: Annotated[int, "Thread ID."],
    comment_id: Annotated[int, "Comment ID to delete."],
) -> None:
    """Delete a specific comment from a pull request thread."""
    comment_url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests/"
        f"{pull_request_id}/threads/{thread_id}/comments/{comment_id}?api-version={DEVOPS_API_VERSION}"
    )

    devops_api_delete(comment_url)
