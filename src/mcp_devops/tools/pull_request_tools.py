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
        "'devops_compare_commits' tool."
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
    name="devops_pull_request_create_comment",
    description=("Create a new pull request thread comment."),
    annotations={"readOnlyHint": False},
)
def create_pull_request_comment(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    comment_content: Annotated[str, "The text content or markdown of the comment."],
    file_path: Annotated[str, "File path for an inline comment."],
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
    name="devops_pull_request_update_comment",
    description=("Update a pull request thread comment."),
    annotations={"readOnlyHint": False},
)
def update_pull_request_comment(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    thread_id: Annotated[int, "Thread ID to update."],
    comment_content: Annotated[str, "New comment text content."],
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
    description=("Delete a pull request thread comment."),
    annotations={"readOnlyHint": False},
)
def delete_pull_request_comment(
    repository_id: Annotated[str, "Repository name or ID."],
    pull_request_id: Annotated[int, "Pull request ID."],
    thread_id: Annotated[int, "Thread ID."],
    comment_id: Annotated[int, "Comment ID to delete."],
) -> object:
    """Delete a specific comment from a pull request thread."""
    comment_url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/pullRequests/"
        f"{pull_request_id}/threads/{thread_id}/comments/{comment_id}?api-version=7.1"
    )

    devops_api_delete(comment_url)
