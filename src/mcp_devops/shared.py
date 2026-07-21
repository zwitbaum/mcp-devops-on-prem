import json
import os
import sys
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from requests.auth import HTTPBasicAuth
from requests_ntlm import HttpNtlmAuth

# Load .env from repo root (no-op if file doesn't exist)
load_dotenv()

# Single connection URL: https://<server>/<organization>/<project>
# Keep the raw value (spaces allowed) — requests percent-encodes paths internally.
devops_api_url = os.getenv("DEVOPS_API_URL", "")

DEFAULT_TIMEOUT = 30

# Azure DevOps REST API version used across all tool modules.
DEVOPS_API_VERSION = "7.1"

# Updated docstring to comply with line length limits
__doc__ = (
    "\n"
    "Available tools:\n"
    "- devops_pull_request_get: fetch a PR by ID, returns title, description, "
    "source/target branch, linked work items, and commit SHAs for diffing\n"
    "- devops_pull_request_create_comment: post a general or inline code comment on a PR\n"
    "- devops_pull_request_update_comment: update an existing PR comment\n"
    "- devops_pull_request_delete_comment: delete a PR comment\n"
    "- devops_repository_get: get repository details by name or ID\n"
    "- devops_repository_commit_changes: list files changed in a specific commit\n"
    "- devops_repository_diffs_commits: diff two commits (returns changed file paths)\n"
    "- devops_repository_item_content: get the raw content of a file at a specific commit\n"
    "- devops_get_item_content_diff: get a line-level text diff of a file between two commits\n"
    "- devops_code_search: search source code with repository, path, and branch filters\n"
    "- devops_work_item_search: search work items with area, type, state, and assigned-to filters\n"
    "- devops_wiki_search: search wiki pages with an optional wiki filter\n"
    "- devops_work_item_get: retrieve a work item (PBI, bug, task, etc.) by ID\n"
    "- devops_work_item_attachment_get: download a work item attachment by ID\n"
    "- devops_work_item_type_get: get work item type definition by name\n"
    "- devops_work_item_query_by_wiql: execute a WIQL query and return matching work items\n"
    "- devops_work_item_create: create a new work item with fields\n"
    "- devops_work_item_update: update fields on an existing work item\n"
    "- devops_work_item_delete: delete a work item (Recycle Bin or permanent)\n"
    "- devops_work_item_undelete: restore a work item from Recycle Bin (opt-in)\n"
    "- devops_work_item_link_update: add or remove a relation link between work items\n"
    "- devops_work_item_artifact_link_update: add or remove an artifact link on a work item\n"
    "- devops_work_item_comment_list: list comments on a work item\n"
    "- devops_work_item_comment_add: add a comment to a work item\n"
    "- devops_work_item_comment_update: update an existing comment on a work item\n"
    "- devops_work_item_comment_delete: delete a comment from a work item\n"
    "- devops_wiki_page_get: get wiki page metadata and content by wiki ID and page ID\n"
    "- devops_wiki_page_update: update an existing wiki page by ID\n"
    "- devops_wiki_page_delete: delete a wiki page by ID\n\n"
    "Typical PR review workflow: call devops_pull_request_get with the repo and PR ID, "
    "then use devops_repository_diffs_commits with the returned commit SHAs to see which "
    "files changed, then call devops_get_item_content_diff per file to read the actual diff."
)


def validate_configuration() -> None:
    """Validate required environment configuration for supported auth modes."""
    api_url = os.getenv("DEVOPS_API_URL", "").strip()
    username = os.getenv("DEVOPS_USERNAME", "")
    password = os.getenv("DEVOPS_PASSWORD", "")
    pat = os.getenv("DEVOPS_PAT", "")
    token = os.getenv("DEVOPS_TOKEN", "")

    if not api_url:
        raise ValueError("DEVOPS_API_URL is required.")

    parsed = urlparse(api_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("DEVOPS_API_URL must be a valid absolute http(s) URL like https://server/org/project.")

    has_username = bool(username)
    has_password = bool(password)
    has_pat = bool(pat)
    has_token = bool(token)
    has_ntlm = has_username or has_password

    if has_username ^ has_password:
        raise ValueError("NTLM configuration is incomplete: set both DEVOPS_USERNAME and DEVOPS_PASSWORD.")

    configured_modes = sum((has_token, has_pat, has_ntlm))
    if configured_modes == 0:
        raise ValueError(
            "Configure exactly one auth mode: DEVOPS_TOKEN, DEVOPS_PAT, or DEVOPS_USERNAME with DEVOPS_PASSWORD."
        )
    if configured_modes > 1:
        raise ValueError(
            "Conflicting auth configuration: set only one of DEVOPS_TOKEN, "
            "DEVOPS_PAT, or DEVOPS_USERNAME with DEVOPS_PASSWORD."
        )


def _is_auth_debug_enabled() -> bool:
    return os.getenv("DEVOPS_AUTH_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug_auth_selection(method: str, username: str | None = None) -> None:
    if not _is_auth_debug_enabled():
        return
    password_present = bool(os.getenv("DEVOPS_PASSWORD"))
    pat_present = bool(os.getenv("DEVOPS_PAT"))
    token_present = bool(os.getenv("DEVOPS_TOKEN"))
    api_url = os.getenv("DEVOPS_API_URL", "")
    print(
        "[DEVOPS AUTH DEBUG] "
        f"method={method}; "
        f"username={username or '<empty>'}; "
        f"password_present={password_present}; "
        f"pat_present={pat_present}; "
        f"token_present={token_present}; "
        f"api_url={api_url}",
        file=sys.stderr,
        flush=True,
    )


def _get_auth_headers_and_kwargs(extra_headers=None):
    """Return (headers, auth_or_none) for the configured auth strategy."""
    token = os.getenv("DEVOPS_TOKEN")
    pat = os.getenv("DEVOPS_PAT")
    headers = {"Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    auth = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
        _debug_auth_selection("bearer-token")
    elif pat:
        username = os.getenv("DEVOPS_USERNAME", "")
        auth = HTTPBasicAuth(username, pat)
        _debug_auth_selection("pat", username=username)
    else:
        username = os.getenv("DEVOPS_USERNAME")
        auth = HttpNtlmAuth(username, os.getenv("DEVOPS_PASSWORD"))
        _debug_auth_selection("ntlm", username=username)
    return headers, auth


def _decode_json_response(response):
    """Decode JSON responses, including Azure DevOps responses with a UTF-8 BOM."""
    return json.loads(response.content.decode("utf-8-sig"))


def devops_api_get(url, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs()
    response = requests.get(url, headers=headers, auth=auth, timeout=DEFAULT_TIMEOUT)
    return response if return_response else _decode_json_response(response)


def devops_api_post(url, payload, extra_headers=None, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs({"Content-Type": "application/json"})
    if extra_headers:
        headers.update(extra_headers)
    response = requests.post(url, headers=headers, auth=auth, json=payload, timeout=DEFAULT_TIMEOUT)
    return response if return_response else _decode_json_response(response)


def devops_api_put(url, payload, extra_headers=None, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs({"Content-Type": "application/json"})
    if extra_headers:
        headers.update(extra_headers)
    response = requests.put(url, headers=headers, auth=auth, json=payload, timeout=DEFAULT_TIMEOUT)
    return response if return_response else _decode_json_response(response)


def devops_api_patch(url, payload, extra_headers=None, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs({"Content-Type": "application/json"})
    if extra_headers:
        headers.update(extra_headers)
    response = requests.patch(url, headers=headers, auth=auth, json=payload, timeout=DEFAULT_TIMEOUT)
    return response if return_response else _decode_json_response(response)


def devops_api_delete(url):
    headers, auth = _get_auth_headers_and_kwargs()
    response = requests.delete(url, headers=headers, auth=auth, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()


_EXPAND_MAP = {"none": 0, "relations": 1, "fields": 2, "links": 3, "all": 4}


def fetch_work_item(url):
    wit_json = devops_api_get(url)
    result = {
        "id": wit_json.get("id"),
        "fields": wit_json.get("fields"),
    }
    if wit_json.get("relations") is not None:
        result["relations"] = wit_json.get("relations")
    if wit_json.get("_links") is not None:
        result["_links"] = wit_json.get("_links")
    return result


def devops_api_get_binary_stream(url):
    """Return a streaming response for raw binary content from a DevOps endpoint."""
    headers, auth = _get_auth_headers_and_kwargs({"Accept": "*/*"})
    response = requests.get(url, headers=headers, auth=auth, timeout=DEFAULT_TIMEOUT, stream=True)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type or "application/json" in content_type:
        # Drain and surface the error body instead of silently writing it as a file
        body = response.content.decode("utf-8", errors="replace")[:500]
        raise ValueError(
            f"Server returned unexpected Content-Type '{content_type}' — likely an error page. Body preview: {body}"
        )
    return response


def devops_api_get_binary(url):
    """Fetch raw binary content from a DevOps endpoint."""
    response = devops_api_get_binary_stream(url)
    chunks = []
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            chunks.append(chunk)
    return b"".join(chunks)


# Shared FastMCP instance for the application
mcp = FastMCP(
    name="DevOpsOnPremise",
    instructions=(
        "MCP server for on-premises Azure DevOps. "
        "Use this server whenever the user wants to work with DevOps pull "
        "requests, repositories, work items (PBIs/bugs), or wiki pages.\n\n"
        "Available tools:\n"
        "- devops_pull_request_get: fetch a PR by ID, returns title, description, "
        "source/target branch, linked work items, and commit SHAs for diffing\n"
        "- devops_pull_request_create_comment: post a general or inline code "
        "comment on a PR\n"
        "- devops_pull_request_update_comment: update an existing PR comment\n"
        "- devops_pull_request_delete_comment: delete a PR comment\n"
        "- devops_repository_get: get repository details by name or ID\n"
        "- devops_repository_commit_changes: list files changed in a specific "
        "commit\n"
        "- devops_repository_diffs_commits: diff two commits (returns changed "
        "file paths)\n"
        "- devops_repository_item_content: get the raw content of a file at a "
        "specific commit\n"
        "- devops_get_item_content_diff: get a line-level text diff of a file "
        "between two commits\n"
        "- devops_code_search: search source code with repository, path, and branch filters\n"
        "- devops_work_item_search: search work items with area, type, state, and assigned-to filters\n"
        "- devops_wiki_search: search wiki pages with an optional wiki filter\n"
        "- devops_work_item_get: retrieve a work item (PBI, bug, task) by "
        "numeric ID; returns key fields, attachments, and linked items\n"
        "- devops_work_item_attachment_get: download a work item attachment by "
        "GUID, returns base64 content or saves to a local path\n"
        "- devops_wiki_page_get: get wiki page metadata and content by wiki ID "
        "and page ID\n"
        "- devops_wiki_page_update: update an existing wiki page by ID\n"
        "- devops_wiki_page_delete: delete a wiki page by ID\n\n"
        "Typical PR review workflow: call devops_pull_request_get with the repo "
        "and PR ID, then use devops_repository_diffs_commits with the returned "
        "commit SHAs to see which files changed, then call devops_get_item_content_diff "
        "per file to read the actual diff."
    ),
)
