import os
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

# Derive the base server URL (scheme + host only) for wiki tools that receive
# organisation/project as explicit parameters.
_parsed = urlparse(devops_api_url)
devops_url = f"{_parsed.scheme}://{_parsed.netloc}" if _parsed.netloc else devops_api_url

DEFAULT_TIMEOUT = 30

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
    "- devops_get_work_item: retrieve a work item (PBI, bug, task) by numeric ID\n"
    "- devops_wiki_page_get_by_url: get wiki page metadata and content by its URL\n"
    "- devops_wiki_page_update: update an existing wiki page by ID\n"
    "- devops_wiki_page_delete: delete a wiki page by ID\n\n"
    "Typical PR review workflow: call devops_pull_request_get with the repo and PR ID, "
    "then use devops_repository_diffs_commits with the returned commit SHAs to see which "
    "files changed, then call devops_get_item_content_diff per file to read the actual diff."
)


def get_base_api_url(organization, project, api_path):
    # Raw strings — requests will encode any spaces/special chars in the path.
    return f"{devops_url}/{organization}/{project}/{api_path}"


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
    elif pat:
        username = os.getenv("DEVOPS_USERNAME", "")
        auth = HTTPBasicAuth(username, pat)
    else:
        auth = HttpNtlmAuth(os.getenv("DEVOPS_USERNAME"), os.getenv("DEVOPS_PASSWORD"))
    return headers, auth


def devops_api_get(url, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs()
    response = requests.get(url, headers=headers, auth=auth, timeout=DEFAULT_TIMEOUT)
    return response if return_response else response.json()


def devops_api_post(url, payload, extra_headers=None, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs({"Content-Type": "application/json"})
    if extra_headers:
        headers.update(extra_headers)
    response = requests.post(url, headers=headers, auth=auth, json=payload, timeout=DEFAULT_TIMEOUT)
    return response if return_response else response.json()


def devops_api_put(url, payload, extra_headers=None, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs({"Content-Type": "application/json"})
    if extra_headers:
        headers.update(extra_headers)
    response = requests.put(url, headers=headers, auth=auth, json=payload, timeout=DEFAULT_TIMEOUT)
    return response if return_response else response.json()


def devops_api_patch(url, payload, extra_headers=None, return_response=False):
    headers, auth = _get_auth_headers_and_kwargs({"Content-Type": "application/json"})
    if extra_headers:
        headers.update(extra_headers)
    response = requests.patch(url, headers=headers, auth=auth, json=payload, timeout=DEFAULT_TIMEOUT)
    return response if return_response else response.json()


def devops_api_delete(url):
    headers, auth = _get_auth_headers_and_kwargs()
    response = requests.delete(url, headers=headers, auth=auth, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()


def fetch_work_item(url):
    wit_json = devops_api_get(url)
    return {
        "id": wit_json.get("id"),
        "fields": wit_json.get("fields"),
    }


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
        "- devops_get_work_item: retrieve a work item (PBI, bug, task) by "
        "numeric ID\n"
        "- devops_wiki_page_get_by_url: get wiki page metadata and content by "
        "its URL\n"
        "- devops_wiki_page_update: update an existing wiki page by ID\n"
        "- devops_wiki_page_delete: delete a wiki page by ID\n\n"
        "Typical PR review workflow: call devops_pull_request_get with the repo "
        "and PR ID, then use devops_repository_diffs_commits with the returned "
        "commit SHAs to see which files changed, then call devops_get_item_content_diff "
        "per file to read the actual diff."
    ),
)
