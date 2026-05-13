from typing import Annotated

from fastmcp.exceptions import ToolError

from mcp_devops.shared import devops_api_url, mcp, devops_api_get


@mcp.tool(
    name="devops_repository_list",
    description="Get the list of repositories.",
    annotations={"readOnlyHint": True},
)
def get_repositories() -> object:
    """Retrieve DevOps repositories for the configured organization/project."""
    url = f"{devops_api_url}/_apis/git/repositories"
    return devops_api_get(url)


@mcp.tool(
    name="devops_repository_get",
    description="Retrieve repository details by repository name or ID.",
    annotations={"readOnlyHint": True},
)
def get_repository(
    repository_id: Annotated[str, "Repository name or ID."],
) -> object:
    """Fetch repository data by repository name or ID."""
    url = f"{devops_api_url}/_apis/git/repositories/{repository_id}"
    return devops_api_get(url)


@mcp.tool(
    name="devops_repository_commit_changes",
    description="Retrieve a list of files changed in the specified commit, including "
    "the type of change for each file (e.g., add, edit, remove).",
    annotations={"readOnlyHint": True},
)
def get_commit_changes(
    repository_id: Annotated[str, "Repository name or ID."],
    commit_id: Annotated[str, "Full 40-character commit SHA (hex string)."],
) -> object:
    """Return the list of changes in this commit."""
    _validate_commit_sha(commit_id)
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/commits"
        f"/{commit_id}/changes"
    )
    return devops_api_get(url)


@mcp.tool(
    name="devops_repository_diffs_commits",
    description="Get the difference between the base and target commits.",
    annotations={"readOnlyHint": True},
)
def compare_commits(
    repository_id: Annotated[str, "Repository name or ID."],
    base_commit: Annotated[str, "Base commit SHA — full 40-character hex (e.g. lastMergeTargetCommit)."],
    target_commit: Annotated[str, "Target commit SHA — full 40-character hex (e.g. lastMergeSourceCommit)."],
) -> object:
    """Compute a diff between two commit SHAs and return the API response."""
    _validate_commit_sha(base_commit)
    _validate_commit_sha(target_commit)
    url = (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/diffs/commits?"
        f"baseVersion={base_commit}&baseVersionType=commit&targetVersion={target_commit}"
        f"&targetVersionType=commit"
    )
    data = devops_api_get(url)
    return {
        "changeCounts": data['changeCounts'],
        "changes": [
            {
                "path": item["item"].get("path", ""),
                "isFolder": item["item"].get("isFolder", False),
                "changeType": item.get("changeType", "")
            }
            for item in data.get("changes", [])
        ]
    }


@mcp.tool(
    name="devops_repository_item_content",
    description=("Get raw file content for a repository path at a specific version."),
    annotations={"readOnlyHint": True},
)
def get_item_content(
    repository_id: Annotated[str, "Repository name or ID."],
    path: Annotated[str, "Path of the item, e.g. src/foo.cs"],
    version: Annotated[str, "Commit ID to fetch the file from."],
) -> str:
    """Fetch raw file content for a repository path at a specific commit SHA.

    The version must be a commit SHA (40-char hex). Use `repo_compare_commits`
    or `repo_get_pull_request_by_id` to determine commit SHAs when needed.
    """
    data = _request_item_content(repository_id, path, version)
    return data.get('content', '')


@mcp.tool(
    name="devops_get_item_content_diff",
    description=(
        "Get textual diff between two versions of a file (changed hunks only). "
        "Lines are numbered; added lines are prefixed with '+', and removed with '-'. "
        "For full content of specific file, use item content tool with target version ."
    ),
    annotations={"readOnlyHint": True},
)
def get_item_content_diff(  # noqa: C901 - readability prioritized for difflib logic
    repository_id: Annotated[str, "Repository name or ID."],
    path: Annotated[str, "Path of the file to diff, e.g. src/foo.cs"],
    base_version: Annotated[str, "Base commit ID, e.g. lastMergeTargetCommit."],
    target_version: Annotated[str, "Target commit ID, e.g. lastMergeSourceCommit."],
) -> object:
    """Return a simple line-diff between two versions of a single file.

    Lines removed from the base are prefixed with '-', added lines with '+',
    and unchanged lines are returned without a prefix.
    """
    base_available = True
    target_available = True
    try:
        base_text = _extract_item_text(repository_id, path, base_version)
    except Exception:
        base_text = ""
        base_available = False

    try:
        target_text = _extract_item_text(repository_id, path, target_version)
    except Exception:
        target_text = ""
        target_available = False

    base_lines = base_text.splitlines()
    target_lines = target_text.splitlines()

    import difflib

    raw = list(difflib.ndiff(base_lines, target_lines))

    all_processed = []
    substantive_indices = set()
    empty_line_changes = 0
    target_line_num = 0
    for line in raw:
        if line.startswith("? "):
            continue
        prefix = line[:2]
        content = line[2:]
        formatted = None
        is_substantive = False

        if prefix == "- ":
            if content.strip() == "":
                empty_line_changes += 1
            else:
                formatted = f" :-{content}"
                is_substantive = True
        elif prefix == "+ ":
            target_line_num += 1
            if content.strip() == "":
                empty_line_changes += 1
            else:
                formatted = f"{target_line_num}:+{content}"
                is_substantive = True
        elif prefix == "  ":
            target_line_num += 1
            formatted = f"{target_line_num}: {content}"

        if formatted is not None:
            if is_substantive:
                substantive_indices.add(len(all_processed))
            all_processed.append(formatted)

    meaningful_changes = []
    if substantive_indices:
        included_indices = set()
        for idx in substantive_indices:
            for i in range(max(0, idx - 3), min(len(all_processed), idx + 4)):
                included_indices.add(i)

        for i in range(len(all_processed)):
            if i in included_indices:
                if i > 0 and (i - 1) not in included_indices:
                    meaningful_changes.append("...")
                meaningful_changes.append(all_processed[i])

        if all_processed and (len(all_processed) - 1) not in included_indices:
            meaningful_changes.append("...")

    if not base_available and target_available:
        change_type = "add"
    elif base_available and not target_available:
        change_type = "delete"
    else:
        if meaningful_changes:
            change_type = "edit"
        elif empty_line_changes > 0:
            change_type = "white spaces only"
        else:
            change_type = "unchanged"

    changes_text = (
        "" if change_type == "white spaces only" else "\n".join(meaningful_changes)
    )

    return {
        "path": path,
        "baseVersion": base_version,
        "targetVersion": target_version,
        "baseAvailable": base_available,
        "targetAvailable": target_available,
        "changeType": change_type,
        "changes": changes_text,
    }


def _validate_commit_sha(sha: str) -> None:
    """Raise ToolError early if sha is not a valid 40-char hex commit SHA."""
    if not (
        isinstance(sha, str)
        and len(sha) == 40
        and all(c in "0123456789abcdefABCDEF" for c in sha)
    ):
        raise ToolError(
            f"Invalid commit SHA: '{sha}'. Expected a 40-character hexadecimal string. "
            "Use devops_pull_request_get to obtain lastMergeSourceCommit / lastMergeTargetCommit."
        )


def _make_item_url(repository_id: str, path: str, version: str) -> str:
    _validate_commit_sha(version)
    return (
        f"{devops_api_url}/_apis/git/repositories/{repository_id}/items?path={path.lstrip('/')}"
        + f"&versionDescriptor.version={version}&versionDescriptor.versionType=commit"
        + "&includeContent=true"
    )


def _extract_item_text_by_response(resp) -> str:
    if isinstance(resp, dict):
        return resp.get("content") or resp.get("value") or ""
    if isinstance(resp, str):
        return resp
    return ""


def _request_item_content(repository_id: str, path: str, version: str):
    url = _make_item_url(repository_id, path, version)
    return devops_api_get(url)


def _extract_item_text(repository_id: str, path: str, version: str) -> str:
    resp = _request_item_content(repository_id, path, version)
    return _extract_item_text_by_response(resp) or ""
