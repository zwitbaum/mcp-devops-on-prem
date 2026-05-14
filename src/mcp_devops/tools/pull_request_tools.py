from typing import Annotated

from mcp_devops.shared import (
    devops_api_url,
    mcp,
    devops_api_get,
    devops_api_post,
    devops_api_patch,
    devops_api_delete,
    fetch_work_item,
)


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
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}"
        f"/pullRequests/{pull_request_id}"
    )
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
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}"
        f"/pullRequests/{pull_request_id}/threads"
    )
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
            comments.append({
                "comment_id": comment.get("id"),
                "parent_comment_id": comment.get("parentCommentId"),
                "author": (comment.get("author") or {}).get("displayName"),
                "content": comment.get("content"),
                "published": comment.get("publishedDate"),
                "last_updated": comment.get("lastUpdatedDate"),
                "last_content_updated": comment.get("lastContentUpdatedDate"),
            })
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
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}"
        f"/pullRequests/{pull_request_id}/threads/{thread_id}"
    )
    response = devops_api_get(url)

    comments = []
    for comment in response.get("comments", []):
        if comment.get("commentType") != "text" and not comment.get("isDeleted", False):
            continue
        if comment.get("isDeleted", False):
            continue
        comments.append({
            "comment_id": comment.get("id"),
            "parent_comment_id": comment.get("parentCommentId"),
            "author": (comment.get("author") or {}).get("displayName"),
            "content": comment.get("content"),
            "published": comment.get("publishedDate"),
            "last_updated": comment.get("lastUpdatedDate"),
            "last_content_updated": comment.get("lastContentUpdatedDate"),
        })

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
    file_path: Annotated[str, "Optional file path for an inline comment."] = None,
    line_number: Annotated[
        int, "Optional 1-based line number for an inline comment."
    ] = None,
) -> object:
    """Create a pull request thread (comment) on the specified PR."""
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests"
        f"/{pull_request_id}/threads?api-version=7.1"
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
        f"/{pull_request_id}/threads/{thread_id}/comments?api-version=7.1"
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
        f"/{pull_request_id}/threads/{thread_id}?api-version=7.1"
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
        f"{pull_request_id}/threads/{thread_id}/comments/{comment_id}?api-version=7.1"
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
        f"{pull_request_id}/threads/{thread_id}/comments/{comment_id}?api-version=7.1"
    )

    devops_api_delete(comment_url)
