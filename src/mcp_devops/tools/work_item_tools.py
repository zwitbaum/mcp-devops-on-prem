import base64
import html
import mimetypes
import os
import re
import urllib.parse
from typing import Annotated, List, Optional

from mcp_devops.shared import (
    devops_api_delete,
    devops_api_get,
    devops_api_get_binary,
    devops_api_get_binary_stream,
    devops_api_patch,
    devops_api_post,
    devops_api_url,
    mcp,
)


def _extract_person(field_value: Optional[dict]) -> Optional[dict]:
    if not field_value:
        return None
    return {
        "displayName": field_value.get("displayName"),
        "uniqueName": field_value.get("uniqueName"),
    }


def _extract_attachments(relations: list) -> list:
    result = []
    for rel in relations:
        if rel.get("rel") == "AttachedFile":
            url = rel.get("url", "")
            m = re.search(r"attachments/([0-9a-f\-]+)", url, re.IGNORECASE)
            attrs = rel.get("attributes", {})
            result.append(
                {
                    "fileId": m.group(1) if m else None,
                    "modifiedDate": attrs.get("resourceModifiedDate"),
                    "size": attrs.get("resourceSize"),
                    "fileName": attrs.get("name"),
                    "fileType": "attachment",
                }
            )
    return result


def _extract_inline_images(description: Optional[str]) -> list:
    if not description:
        return []
    pattern = re.escape(devops_api_url) + r"/_apis/wit/attachments/([0-9a-f\-]+)\?fileName=([^\"'&\s]+)"
    result = []
    for src in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', description, re.IGNORECASE):
        m = re.search(pattern, src, re.IGNORECASE)
        if m:
            result.append(
                {
                    "fileId": m.group(1),
                    "fileName": urllib.parse.unquote(m.group(2)),
                    "fileType": "inlineImage",
                }
            )
    return result


def _extract_links(relations: list) -> list:
    result = []
    for rel in relations:
        rel_type = rel.get("rel", "")
        url = rel.get("url", "")
        attrs = rel.get("attributes", {})

        if rel_type.startswith("System.LinkTypes."):
            try:
                item_id = int(url.rstrip("/").split("/")[-1])
            except (ValueError, IndexError):
                item_id = None
            result.append(
                {
                    "type": "Work Item",
                    "name": attrs.get("name"),
                    "id": item_id,
                    "url": url,
                }
            )
        elif rel_type == "ArtifactLink":
            decoded_url = urllib.parse.unquote(url)
            if "PullRequestId" in decoded_url:
                url_parts = decoded_url.split("/")
                pr_id = url_parts[-1]
                repo_id = url_parts[-2]
                result.append(
                    {
                        "type": "Artifact",
                        "name": "Pull Request",
                        "id": pr_id,
                        "url": f"{devops_api_url}/_git/{repo_id}/pullrequest/{pr_id}",
                    }
                )
            elif "Git/Commit" in decoded_url:
                parts = decoded_url.split("/")
                commit_hash = parts[-1]
                repo_id = parts[-2]
                result.append(
                    {
                        "type": "Artifact",
                        "name": "Commit",
                        "id": commit_hash,
                        "url": f"{devops_api_url}/_git/{repo_id}/commit/{commit_hash}",
                    }
                )
    return result


_VALID_OPS = {"add", "replace", "remove"}

_COMMENTS_API_VERSION = "7.1-preview.4"

_LINK_TYPE_MAP: dict[str, str] = {
    "parent": "System.LinkTypes.Hierarchy-Reverse",
    "child": "System.LinkTypes.Hierarchy-Forward",
    "duplicate": "System.LinkTypes.Duplicate-Forward",
    "duplicate of": "System.LinkTypes.Duplicate-Reverse",
    "related": "System.LinkTypes.Related",
    "successor": "System.LinkTypes.Dependency-Forward",
    "predecessor": "System.LinkTypes.Dependency-Reverse",
    "tested by": "Microsoft.VSTS.Common.TestedBy-Forward",
    "tests": "Microsoft.VSTS.Common.TestedBy-Reverse",
    "affects": "Microsoft.VSTS.Common.Affects-Forward",
    "affected by": "Microsoft.VSTS.Common.Affects-Reverse",
}


def _get_link_rel(link_type: str) -> str:
    """Return the Azure DevOps relation type name for a human-readable link type."""
    key = link_type.strip().lower()
    rel = _LINK_TYPE_MAP.get(key)
    if rel is None:
        raise ValueError(f"Unknown link type '{link_type}'. Valid values: {', '.join(_LINK_TYPE_MAP)}.")
    return rel


def _build_artifact_vstfs_url(link_type: str, artifact_id: str) -> tuple[str, str]:
    """Build a VSTFS URL and attribute name for an artifact ArtifactLink relation.

    Returns (vstfs_url, attr_name).

    artifact_id format by link_type:
      Build / Found in build / Integrated in build  -> "{build_id}"
      Changeset                                      -> "{changeset_id}"
      Pull Request / Commit / Branch / Versioned Item -> "{project_id}/{repo_id}/{detail}"
    """
    lt = link_type.strip().lower()

    if lt in ("build", "found in build", "integrated in build"):
        return f"vstfs:///Build/Build/{urllib.parse.quote(artifact_id, safe='')}", link_type.title()

    if lt == "changeset":
        return f"vstfs:///VersionControl/Changeset/{urllib.parse.quote(artifact_id, safe='')}", "Changeset"

    # Git-based types: artifact_id = "{project_id}/{repo_id}/{detail}"
    parts = artifact_id.split("/", 2)
    if len(parts) < 3:
        raise ValueError(f"artifact_id for link_type '{link_type}' must be '{{project_id}}/{{repo_id}}/{{detail}}'.")
    project_id, repo_id, detail = parts

    if lt == "pull request":
        encoded = urllib.parse.quote(f"{project_id}/{repo_id}/{detail}", safe="")
        return f"vstfs:///Git/PullRequestId/{encoded}", "Pull Request"

    if lt == "commit":
        encoded = urllib.parse.quote(f"{project_id}/{repo_id}/{detail}", safe="")
        return f"vstfs:///Git/Commit/{encoded}", "Fixed in Commit"

    if lt == "branch":
        encoded = urllib.parse.quote(f"{project_id}/{repo_id}/GB{detail}", safe="")
        return f"vstfs:///Git/Ref/{encoded}", "Branch"

    if lt == "versioned item":
        encoded = urllib.parse.quote(f"{project_id}/{repo_id}/{detail}", safe="")
        return f"vstfs:///Git/Blob/{encoded}", "Versioned Item"

    raise ValueError(
        f"Unknown artifact link_type '{link_type}'. Valid values: "
        "'Pull Request', 'Build', 'Found in build', 'Integrated in build', "
        "'Commit', 'Branch', 'Changeset', 'Versioned Item'."
    )


def _patch_work_item(work_item_id: int, document: list, validate_only: Optional[bool] = None) -> object:
    """Send a JSON Patch document to the work item update endpoint."""
    url = f"{devops_api_url}/_apis/wit/workitems/{work_item_id}?api-version=7.1"
    if validate_only is not None:
        url += f"&validateOnly={'true' if validate_only else 'false'}"
    return devops_api_patch(
        url,
        document,
        extra_headers={"Content-Type": "application/json-patch+json"},
    )


@mcp.tool(
    name="devops_work_item_get",
    description=(
        "Retrieve a single work item by numeric ID. "
        "Returns a compact object with key fields (title, state, type, assignee, "
        "description, acceptance criteria, tags, parent), plus attachments (files "
        "and inline images) and linked items (work items, pull requests, commits)."
    ),
    annotations={"readOnlyHint": True},
)
def get_work_item(
    work_item_id: Annotated[int, "The numeric work item ID to fetch."],
) -> object:
    """Fetch a work item by ID and return a focused JSON object."""
    url = f"{devops_api_url}/_apis/wit/workitems/{work_item_id}?$expand=1"
    wit_json = devops_api_get(url)

    fields = wit_json.get("fields", {})
    relations = wit_json.get("relations") or []

    work_item_type = fields.get("System.WorkItemType")
    description = (
        fields.get("Microsoft.VSTS.TCM.ReproSteps") if work_item_type == "Bug" else fields.get("System.Description")
    )
    acceptance = fields.get("Microsoft.VSTS.Common.AcceptanceCriteria")

    result = {
        "id": wit_json.get("id"),
        "areaPath": fields.get("System.AreaPath"),
        "iterationPath": fields.get("System.IterationPath"),
        "workItemType": work_item_type,
        "state": fields.get("System.State"),
        "reason": fields.get("System.Reason"),
        "assignedTo": _extract_person(fields.get("System.AssignedTo")),
        "createdBy": _extract_person(fields.get("System.CreatedBy")),
        "changedBy": _extract_person(fields.get("System.ChangedBy")),
        "createdDate": fields.get("System.CreatedDate"),
        "changedDate": fields.get("System.ChangedDate"),
        "commentCount": fields.get("System.CommentCount"),
        "title": html.unescape(fields.get("System.Title") or ""),
        "boardColumn": fields.get("System.BoardColumn"),
        "description": html.unescape(description) if description else None,
        "acceptanceCriteria": html.unescape(acceptance) if acceptance else None,
        "tags": fields.get("System.Tags"),
        "parentId": fields.get("System.Parent"),
        "severity": fields.get("Microsoft.VSTS.Common.Severity"),
        "effort": fields.get("Microsoft.VSTS.Scheduling.Effort"),
        "systemInfo": fields.get("Microsoft.VSTS.TCM.SystemInfo"),
        "attachments": _extract_attachments(relations) + _extract_inline_images(description),
        "links": _extract_links(relations),
    }

    return result  # noqa: RET504


@mcp.tool(
    name="devops_work_item_attachment_get",
    description=(
        "Download a work item attachment by specified ID. "
        "Returns base64-encoded content, or saves to a local directory if savePath is provided."
    ),
    annotations={"readOnlyHint": True},
)
def get_work_item_attachment(
    attachment_id: Annotated[str, "The GUID of the attachment."],
    file_name: Annotated[
        str,
        (
            "The file name of the attachment. Used to determine the MIME type. "
            "If save_path is provided, the file is saved under this name."
        ),
    ],
    save_path: Annotated[
        Optional[str],
        (
            "Optional directory path to save the file to. "
            "If omitted, returns the content as a base64-encoded resource. "
            "NOTE: relative paths are resolved against the MCP server's working "
            "directory; paths starting with '..' are not allowed."
        ),
    ] = None,
) -> object:
    """Download a work item attachment by GUID."""
    if save_path is not None:
        if not os.path.isabs(save_path):
            normalized = os.path.normpath(save_path)
            if normalized.startswith(".."):
                raise ValueError("Relative save_path must not traverse outside the working directory.")

    url = f"{devops_api_url}/_apis/wit/attachments/{attachment_id}"

    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.abspath(os.path.join(save_path, file_name))
        response = devops_api_get_binary_stream(url)
        size = 0
        with open(file_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
                    size += len(chunk)
        return {"saved_path": file_path, "size_bytes": size}

    content = devops_api_get_binary(url)

    mime_type, _ = mimetypes.guess_type(file_name)
    if not mime_type:
        mime_type = "application/octet-stream"
    return {
        "fileName": file_name,
        "mimeType": mime_type,
        "content_base64": base64.b64encode(content).decode("utf-8"),
    }


@mcp.tool(
    name="devops_work_item_type_get",
    description="Get definition for the specified work item type.",
    annotations={"readOnlyHint": True},
)
def get_work_item_type(
    type: Annotated[str, "Work item type name (e.g. 'Bug', 'User Story')."],
) -> object:
    """Fetch the definition of a work item type by name."""
    url = f"{devops_api_url}/_apis/wit/workitemtypes/{urllib.parse.quote(type)}"
    return devops_api_get(url)


@mcp.tool(
    name="devops_work_item_create",
    description="Create a new work item of the specified work item type.",
    annotations={"readOnlyHint": False},
)
def create_work_item(
    type: Annotated[str, "The work item type to create, e.g. 'Task', 'Bug', 'User Story'."],
    fields: Annotated[
        List[dict],
        (
            "List of field objects to set on the new work item. "
            "Each entry must have 'name' (field reference name, e.g. 'System.Title') "
            "and 'value'. An optional 'format' key accepts 'Html' or 'Markdown' "
            "(defaults to 'Html' when omitted; use 'Markdown' only if the project supports it)."
        ),
    ],
    validate_only: Annotated[
        Optional[bool],
        "If True, validate the input against system rules without saving the work item (dry run).",
    ] = None,
) -> object:
    """Create a work item using a JSON Patch document."""
    document: list = []
    for field in fields:
        name: str = field["name"]
        value: str = field.get("value", "")
        fmt: Optional[str] = field.get("format")  # "Html", "Markdown", or None

        document.append({"op": "add", "path": f"/fields/{name}", "value": value})

        # Set Markdown rendering hint for large text fields
        if len(value) > 100 and fmt == "Markdown":
            document.append({"op": "add", "path": f"/multilineFieldsFormat/{name}", "value": "Markdown"})

    encoded_type = urllib.parse.quote(type)
    url = f"{devops_api_url}/_apis/wit/workitems/${encoded_type}?api-version=7.1"
    if validate_only is not None:
        url += f"&validateOnly={'true' if validate_only else 'false'}"

    return devops_api_post(
        url,
        document,
        extra_headers={"Content-Type": "application/json-patch+json"},
    )


@mcp.tool(
    name="devops_work_item_update",
    description="Update fields on a work item by ID.",
    annotations={"readOnlyHint": False},
)
def update_work_item(
    work_item_id: Annotated[int, "The numeric work item ID to update."],
    updates: Annotated[
        List[dict],
        (
            "List of field updates to apply. Each entry must have: "
            "'op' (one of 'add', 'replace', 'remove'; defaults to 'add'), "
            "'name' (field reference name, e.g. 'System.Title'), "
            "and 'value' (required for 'add'/'replace', omit for 'remove')."
        ),
    ],
    validate_only: Annotated[
        Optional[bool],
        "If True, validate the input against system rules without saving the work item (dry run).",
    ] = None,
) -> object:
    """Update work item fields using a JSON Patch document."""
    document: list = []
    for entry in updates:
        op: str = str(entry.get("op", "add")).lower()
        if op not in _VALID_OPS:
            raise ValueError(f"Invalid op '{op}'. Must be one of: {', '.join(sorted(_VALID_OPS))}.")
        name: str = entry["name"]
        patch_op: dict = {"op": op, "path": f"/fields/{name}"}
        if op != "remove":
            patch_op["value"] = entry.get("value", "")
        document.append(patch_op)

    return _patch_work_item(work_item_id, document, validate_only)


@mcp.tool(
    name="devops_work_item_delete",
    description=(
        "Delete a work item by ID. By default the item is sent to the Recycle Bin and can be restored. "
        "Set destroy=True to permanently destroy the item — WARNING: this is irreversible."
    ),
    annotations={"readOnlyHint": False},
)
def delete_work_item(
    work_item_id: Annotated[int, "The numeric ID of the work item to delete."],
    destroy: Annotated[
        Optional[bool],
        (
            "If True, permanently destroys the work item (requires 'Permanently delete work items' "
            "permission in Project Settings → Security; if not enabled, the server returns 404). "
            "WARNING: permanent destruction cannot be undone. Defaults to False (moves to Recycle Bin)."
        ),
    ] = None,
) -> object:
    """Delete a work item, optionally destroying it permanently."""
    url = f"{devops_api_url}/_apis/wit/workitems/{work_item_id}?api-version=7.1"
    if destroy:
        url += "&destroy=true"
    devops_api_delete(url)
    return {
        "deleted": True,
        "work_item_id": work_item_id,
        "permanent": bool(destroy),
    }


@mcp.tool(
    name="devops_work_item_undelete",
    description=(
        "Restore a work item from the Recycle Bin by ID. "
        "Only works for items deleted without the destroy flag."
    ),
    annotations={"readOnlyHint": False},
)
def undelete_work_item(
    work_item_id: Annotated[int, "The numeric ID of the deleted work item to restore."],
) -> object:
    """Restore a soft-deleted work item from the Recycle Bin."""
    url = f"{devops_api_url}/_apis/wit/recyclebin/{work_item_id}?api-version=7.1"
    return devops_api_patch(url, {"isDeleted": False})


@mcp.tool(
    name="devops_work_item_link_update",
    description=(
        "Add or remove a relation link between two work items. "
        "Use op='add' (default) to create a new link, op='remove' to delete an existing one. "
        "To change a link type, call remove then add."
    ),
    annotations={"readOnlyHint": False},
)
def update_work_item_link(
    work_item_id: Annotated[int, "The numeric ID of the work item to modify."],
    link_to_id: Annotated[int, "The numeric ID of the work item to link to or unlink from."],
    op: Annotated[
        str,
        "Operation to perform: 'add' (default) to create the link, 'remove' to delete it.",
    ] = "add",
    link_type: Annotated[
        str,
        (
            "Type of link. One of: 'parent', 'child', 'related', 'duplicate', "
            "'duplicate of', 'successor', 'predecessor', 'tested by', 'tests', "
            "'affects', 'affected by'. Defaults to 'related'."
        ),
    ] = "related",
    comment: Annotated[
        Optional[str],
        "Optional comment to attach to the link. Only used when op='add'.",
    ] = None,
    validate_only: Annotated[
        Optional[bool],
        "If True, validate without saving (dry run).",
    ] = None,
) -> object:
    """Add or remove a work item relation link using a JSON Patch document."""
    op_lower = op.strip().lower()
    if op_lower not in ("add", "remove"):
        raise ValueError(f"Invalid op '{op}'. Must be 'add' or 'remove'.")

    rel = _get_link_rel(link_type)

    if op_lower == "add":
        target_url = f"{devops_api_url}/_apis/wit/workItems/{link_to_id}"
        document = [
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": rel,
                    "url": target_url,
                    "attributes": {"comment": comment or ""},
                },
            }
        ]
        return _patch_work_item(work_item_id, document, validate_only)

    # op == "remove": locate the relation index(es) first
    wi_json = devops_api_get(f"{devops_api_url}/_apis/wit/workitems/{work_item_id}?$expand=1")
    relations: list = wi_json.get("relations") or []

    expected_url_suffix = f"/{link_to_id}"
    indexes = [
        idx
        for idx, r in enumerate(relations)
        if r.get("rel") == rel and r.get("url", "").rstrip("/").endswith(expected_url_suffix)
    ]

    if not indexes:
        raise ValueError(f"No '{link_type}' link to work item {link_to_id} found on work item {work_item_id}.")

    # Sort descending to avoid index shifting when the API applies multiple removes
    document = [{"op": "remove", "path": f"/relations/{idx}"} for idx in sorted(indexes, reverse=True)]
    return _patch_work_item(work_item_id, document, validate_only)


@mcp.tool(
    name="devops_work_item_artifact_link_update",
    description=(
        "Add or remove an artifact link (Pull Request, Build, Commit, Branch, Changeset, Versioned Item) "
        "on a work item. Use op='add' (default) to attach, op='remove' to detach. "
        "The artifact_id format depends on link_type (see parameter doc)."
    ),
    annotations={"readOnlyHint": False},
)
def update_work_item_artifact_link(
    work_item_id: Annotated[int, "The numeric ID of the work item to modify."],
    link_type: Annotated[
        str,
        (
            "Supported: 'Pull Request', 'Build', 'Found in build', "
            "'Integrated in build', 'Commit', 'Branch', 'Changeset', 'Versioned Item'."
        ),
    ],
    artifact_id: Annotated[
        str,
        (
            "Artifact identifier — format depends on link_type: "
            "Git-based (Pull Request / Commit / Branch / Versioned Item): '{project_id}/{repo_id}/{detail}', "
            "where project_id and repo_id are GUIDs (use devops_repository_get to resolve names), "
            "and detail is the PR number, commit SHA, branch name, or file path respectively. "
            "Build / Found in build / Integrated in build: '{build_id}'. "
            "Changeset: '{changeset_id}'."
        ),
    ],
    op: Annotated[
        str,
        "Operation to perform: 'add' (default) to attach the artifact link, 'remove' to detach it.",
    ] = "add",
    comment: Annotated[
        Optional[str],
        "Optional comment to attach to the link. Only used when op='add'.",
    ] = None,
    validate_only: Annotated[
        Optional[bool],
        "If True, validate without saving (dry run).",
    ] = None,
) -> object:
    """Add or remove an artifact ArtifactLink on a work item."""
    op_lower = op.strip().lower()
    if op_lower not in ("add", "remove"):
        raise ValueError(f"Invalid op '{op}'. Must be 'add' or 'remove'.")

    vstfs_url, attr_name = _build_artifact_vstfs_url(link_type, artifact_id)

    if op_lower == "add":
        document = [
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "ArtifactLink",
                    "url": vstfs_url,
                    "attributes": {"name": attr_name, "comment": comment or ""},
                },
            }
        ]
        return _patch_work_item(work_item_id, document, validate_only)

    # op == "remove": locate matching relation(s) by reconstructed URL
    wi_json = devops_api_get(f"{devops_api_url}/_apis/wit/workitems/{work_item_id}?$expand=1")
    relations: list = wi_json.get("relations") or []

    target_decoded = urllib.parse.unquote(vstfs_url).lower()
    indexes = [
        idx
        for idx, r in enumerate(relations)
        if r.get("rel") == "ArtifactLink" and urllib.parse.unquote(r.get("url", "")).lower() == target_decoded
    ]

    if not indexes:
        raise ValueError(f"No '{link_type}' artifact link for '{artifact_id}' found on work item {work_item_id}.")

    document = [{"op": "remove", "path": f"/relations/{idx}"} for idx in sorted(indexes, reverse=True)]
    return _patch_work_item(work_item_id, document, validate_only)


@mcp.tool(
    name="devops_work_item_comment_list",
    description="List comments on a work item. Returns up to `top` comments (default 50).",
    annotations={"readOnlyHint": True},
)
def list_work_item_comments(
    work_item_id: Annotated[int, "The numeric work item ID."],
    top: Annotated[Optional[int], "Maximum number of comments to return. Defaults to 50."] = 50,
    format: Annotated[
        Optional[str],
        "Response format: 'html' (default) or 'markdown'.",
    ] = "html",
) -> object:
    """List comments on a work item."""
    fmt = (format or "html").lower()
    url = (
        f"{devops_api_url}/_apis/wit/workItems/{work_item_id}/comments"
        f"?api-version={_COMMENTS_API_VERSION}&format={fmt}&$top={top or 50}"
    )
    return devops_api_get(url)


@mcp.tool(
    name="devops_work_item_comment_add",
    description="Add a comment to a work item.",
    annotations={"readOnlyHint": False},
)
def add_work_item_comment(
    work_item_id: Annotated[int, "The numeric work item ID."],
    text: Annotated[str, "The comment text (Html or Markdown depending on format)."],
    format: Annotated[
        Optional[str],
        "Format of the comment text: 'html' (default) or 'markdown'.",
    ] = "html",
) -> object:
    """Add a comment to a work item."""
    fmt = (format or "html").lower()
    url = (
        f"{devops_api_url}/_apis/wit/workItems/{work_item_id}/comments?api-version={_COMMENTS_API_VERSION}&format={fmt}"
    )
    return devops_api_post(url, {"text": text})


@mcp.tool(
    name="devops_work_item_comment_update",
    description="Update an existing comment on a work item.",
    annotations={"readOnlyHint": False},
)
def update_work_item_comment(
    work_item_id: Annotated[int, "The numeric work item ID."],
    comment_id: Annotated[int, "The numeric ID of the comment to update."],
    text: Annotated[str, "The updated comment text."],
    format: Annotated[
        Optional[str],
        "Format of the comment text: 'html' (default) or 'markdown'.",
    ] = "html",
) -> object:
    """Update a comment on a work item."""
    fmt = (format or "html").lower()
    url = (
        f"{devops_api_url}/_apis/wit/workItems/{work_item_id}/comments/{comment_id}"
        f"?api-version={_COMMENTS_API_VERSION}&format={fmt}"
    )
    return devops_api_patch(url, {"text": text})


@mcp.tool(
    name="devops_work_item_comment_delete",
    description="Delete a comment from a work item.",
    annotations={"readOnlyHint": False},
)
def delete_work_item_comment(
    work_item_id: Annotated[int, "The numeric work item ID."],
    comment_id: Annotated[int, "The numeric ID of the comment to delete."],
) -> object:
    """Delete a comment from a work item."""
    url = (
        f"{devops_api_url}/_apis/wit/workItems/{work_item_id}/comments/{comment_id}?api-version={_COMMENTS_API_VERSION}"
    )
    devops_api_delete(url)
    return {"deleted": True, "work_item_id": work_item_id, "comment_id": comment_id}
