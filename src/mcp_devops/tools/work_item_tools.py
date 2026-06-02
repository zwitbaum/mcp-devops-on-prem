import base64
import html
import mimetypes
import os
import re
import urllib.parse
from typing import Annotated, Optional

from mcp_devops.shared import (
    devops_api_get,
    devops_api_get_binary,
    devops_api_get_binary_stream,
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


@mcp.tool(
    name="devops_work_item_get",
    description=(
        "Retrieve a single work item by numeric ID. "
        "Returns a compact object with key fields (title, state, type, assignee, "
        "description, acceptance criteria, tags, parent), plus attachments (files "
        "and inline images) and linked items (work items, pull requests, commits)."
    ),
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
