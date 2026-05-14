import urllib.parse
import re
from typing import Annotated
from fastmcp.exceptions import ToolError
from mcp_devops.shared import devops_api_get, devops_api_put, devops_api_patch, devops_api_delete, get_base_api_url, mcp
from requests.exceptions import HTTPError

WIKI_API_PATH = "_apis/wiki/wikis"
WIKI_INFO_CACHE = {}


@mcp.tool(
    name="devops_wiki_page_get_by_url",
    description="Retrieves metadata (incl. id, path) and/or content of a wiki page using its URL.",
)
def get_wiki_page(
    wiki_url: str,
    include_content: bool = False
) -> object:
    """Get wiki page by its url and return a JSON object."""
    ids = extract_identifiers(wiki_url)
    page = get_wiki_page_details(ids["organization"], ids["project"], ids["wikiIdentifier"], ids["page_id"], include_content)
    ids["path"] = page.get("path")
    ids["isParentPage"] = page.get("isParentPage")
    if include_content:
        ids["content"] = page.get("content")
    return ids


@mcp.tool(
    name="devops_wiki_page_create_or_update",
    description="Create or update a wiki page under the specified parent page.",
)
def create_wiki_page(
    organization: Annotated[str, "DevOps organization name."],
    project: Annotated[str, "DevOps project name."],
    wiki_id: Annotated[str, "Wiki identifier (name or ID)."],
    parent_path: Annotated[str, "Relative path of the parent wiki page, or '/' for root."],
    title: Annotated[str, "Title of the new wiki page. If a page with the same title already exists under the parent, it will be updated."],
    content: str = ""
) -> object:
    """Create or update a wiki page as a child of the given parent page and return a metadata."""
    subpage_path = f"{parent_path}/{title}"

    url = f"{get_base_api_url(organization, project, get_api_path(wiki_id))}/pages?path={subpage_path}&api-version=7.1"

    extra_headers = {}
    try:
        response = devops_api_get(url, return_response=True)
        if "application/json" not in response.headers.get("Content-Type", ""):
            raise ValueError("Unexpected response content type.")

        etag = response.headers.get("ETag")
        if etag:
            extra_headers["If-Match"] = etag
    except Exception as e:
        if isinstance(e, HTTPError) and getattr(e.response, "status_code", None) == 404:
            pass
        else:
            raise ToolError("Wiki page cannot be checked for existence. Check parameter and connection.")

    payload = {"content": content}

    wiki_info = get_wiki_info(organization, project, wiki_id)
    if wiki_info.get("type") == "codeWiki":
        branch = "test"
        version = wiki_info.get("versions", [{}])[0].get("version", branch)
        url += f"&versionDescriptor.versionType=branch&versionDescriptor.version={version}"
        payload["comment"] = f"Create/Update page: {title}"

    result = devops_api_put(url, payload, extra_headers=extra_headers)
    return {
        "path": result.get("path"),
        "order": result.get("order"),
        "id": result.get("id"),
    }


@mcp.tool(
    name="devops_wiki_page_update",
    description="Update an existing wiki page.",
)
def update_wiki_page(
    organization: Annotated[str, "DevOps organization name."],
    project: Annotated[str, "DevOps project name."],
    wiki_id: Annotated[str, "Wiki identifier (name or ID)."],
    page_id: Annotated[int, "Wiki page ID."],
    content: Annotated[str, "New content for the wiki page (optional)."] = "",
) -> object:
    """Update an existing wiki page."""
    if not isinstance(page_id, int) or page_id <= 0:
        raise ToolError("Invalid page_id. It should be a positive integer.")

    url = f"{get_base_api_url(organization, project, get_api_path(wiki_id))}/pages/{page_id}?api-version=7.1"

    extra_headers = {}
    try:
        response = devops_api_get(url, return_response=True)
        etag = response.headers.get("ETag")
        if etag:
            extra_headers["If-Match"] = etag
        else:
            raise ValueError("ETag not found in response headers.")
    except Exception as e:
        raise ToolError(f"Page version cannot be retrieved. Check parameter and connection. Details: {str(e)}")

    payload = {"content": content}
    result = devops_api_patch(url, payload, extra_headers=extra_headers)
    return {
        "path": result.get("path"),
        "order": result.get("order"),
        "id": result.get("id"),
    }


@mcp.tool(
    name="devops_wiki_page_delete",
    description="Delete an existing wiki page.",
    annotations={"readOnlyHint": False, "returnType": "void"},
)
def delete_wiki_page(
    organization: Annotated[str, "DevOps organization name."],
    project: Annotated[str, "DevOps project name."],
    wiki_id: Annotated[str, "Wiki identifier (name or ID)."],
    page_id: Annotated[int, "Wiki page ID."],
    comment: Annotated[str, "Optional comment for deleting the wiki page."] = "",
) -> None:
    """Delete an existing wiki page."""
    if not isinstance(page_id, int) or page_id <= 0:
        raise ToolError("Invalid page_id. It should be a positive integer.")

    url = f"{get_base_api_url(organization, project, get_api_path(wiki_id))}/pages/{page_id}?api-version=7.1"
    if comment:
        url += "&" + urllib.parse.urlencode({"comment": comment})

    devops_api_delete(url)


def extract_identifiers(wiki_url):
    pattern = r"https?://[^/]+/([^/]+)/([^/]+)/_?wiki/wikis/([^/]+)/([^/]+)"
    match = re.search(pattern, wiki_url)

    if not match:
        raise ToolError("Invalid wiki URL format. Expected format: https://{devops}/{organization}/{project}/_wiki/wikis/{wikiIdentifier}/{page_id}/...")

    return {
        "organization": urllib.parse.unquote(match.group(1)),
        "project": urllib.parse.unquote(match.group(2)),
        "wikiIdentifier": urllib.parse.unquote(match.group(3)),
        "page_id": match.group(4)
    }


def get_api_path(wiki_id):
    return f"{WIKI_API_PATH}/{wiki_id}"


def get_wiki_page_details(organization, project, wiki_id, page_id, include_content):
    url = f"{get_base_api_url(organization, project, get_api_path(wiki_id))}/pages/{page_id}?includeContent={str(include_content).lower()}&api-version=7.1"
    return devops_api_get(url)


def get_wiki_info(organization, project, wiki_id):
    if wiki_id not in WIKI_INFO_CACHE:
        WIKI_INFO_CACHE[wiki_id] = devops_api_get(
            f"{get_base_api_url(organization, project, get_api_path(wiki_id))}?api-version=7.1"
        )
    return WIKI_INFO_CACHE[wiki_id]
