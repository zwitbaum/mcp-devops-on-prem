from typing import Annotated, List, Optional
from urllib.parse import quote, unquote, urlparse

from fastmcp.exceptions import ToolError
from mcp_devops.shared import (
    DEVOPS_API_VERSION,
    devops_api_get,
    devops_api_post,
    devops_api_url,
    mcp,
)

# Extract the fixed project from DEVOPS_API_URL = https://server/org/project.
_parsed_url = urlparse(devops_api_url)
_path_parts = [unquote(p) for p in _parsed_url.path.strip("/").split("/") if p]
_project_name = _path_parts[-1] if len(_path_parts) >= 2 else ""

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_search_url(endpoint: str) -> str:
    """Return the project-scoped search API URL for the given endpoint."""
    return f"{devops_api_url}/_apis/search/{endpoint}?api-version={DEVOPS_API_VERSION}"


def _build_identity_search_url(display_name: str) -> str:
    """Return the collection-scoped identity lookup URL for a display name."""
    parsed_url = urlparse(devops_api_url)
    project_path = parsed_url.path.rstrip("/")
    collection_path = project_path.rsplit("/", 1)[0]
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{collection_path}"
    return (
        f"{base_url}/_apis/identities?searchFilter=General"
        f"&filterValue={quote(display_name)}&api-version={DEVOPS_API_VERSION}"
    )


def _resolve_assigned_to(assigned_to: List[str]) -> List[str]:
    """Resolve display names to the canonical identity values used by Search."""
    resolved: List[str] = []
    for value in assigned_to:
        if "<" in value and value.rstrip().endswith(">"):
            resolved.append(value)
            continue

        response = devops_api_get(_build_identity_search_url(value), return_response=True)
        _raise_for_error(response)
        identities = response.json().get("value", [])
        identity = next(
            (
                item
                for item in identities
                if item.get("displayName") == value
                or item.get("providerDisplayName") == value
                or item.get("providerDisplayName", "").startswith(f"{value} <")
            ),
            None,
        )
        if identity is None:
            resolved.append(value)
            continue

        canonical = identity.get("providerDisplayName")
        if not canonical or "<" not in canonical:
            unique_name = identity.get("uniqueName") or identity.get("mail")
            properties = identity.get("properties") or {}
            domain = properties.get("Domain", {}).get("$value")
            account = properties.get("Account", {}).get("$value")
            if not unique_name and domain and account:
                unique_name = f"{domain}\\{account}"
            canonical = f"{value} <{unique_name}>" if unique_name else value
        resolved.append(canonical)

    return resolved


def _raise_for_error(response) -> None:
    """Raise a ToolError if the HTTP response indicates a failure."""
    if response.status_code >= 400:
        raise ToolError(f"Search API request failed with status {response.status_code}: {response.text[:500]}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="devops_code_search",
    description=(
        "Search source code in the configured Azure DevOps project. "
        "Returns matching file locations with snippet context. "
        "Optionally filter by repository, path, and branch."
    ),
)
def code_search(
    search_text: Annotated[str, "Keywords or code fragment to search for."],
    repository: Annotated[
        Optional[List[str]],
        "Filter results to one or more repository names.",
    ] = None,
    path: Annotated[
        Optional[List[str]],
        "Filter results to one or more file paths (prefix match).",
    ] = None,
    branch: Annotated[
        Optional[List[str]],
        "Filter results to one or more branch names.",
    ] = None,
    include_facets: Annotated[
        bool,
        "When true, include facet counts (projects, repositories, etc.) in the response.",
    ] = False,
    skip: Annotated[int, "Number of results to skip for pagination."] = 0,
    top: Annotated[int, "Maximum number of results to return (1–1000)."] = 25,
) -> object:
    """Search code in Azure DevOps repositories and return matching file locations."""
    url = _build_search_url("codesearchresults")

    payload: dict = {
        "searchText": search_text,
        "includeFacets": include_facets,
        "$skip": skip,
        "$top": top,
    }

    filters: dict = {"Project": [_project_name]}
    if repository:
        filters["Repository"] = repository
    if path:
        filters["Path"] = path
    if branch:
        filters["Branch"] = branch
    payload["filters"] = filters

    response = devops_api_post(url, payload, return_response=True)
    _raise_for_error(response)
    return response.json()


@mcp.tool(
    name="devops_work_item_search",
    description=(
        "Search work items (PBIs, bugs, tasks, etc.) in the configured Azure DevOps project using full-text search. "
        "Optionally filter by area path, work item type, state, or assigned-to user."
    ),
)
def work_item_search(
    search_text: Annotated[str, "Keywords to search for in work item fields."],
    area_path: Annotated[
        Optional[List[str]],
        "Filter results to one or more area paths.",
    ] = None,
    work_item_type: Annotated[
        Optional[List[str]],
        "Filter results to one or more work item types (e.g. 'Bug', 'Task').",
    ] = None,
    state: Annotated[
        Optional[List[str]],
        "Filter results to one or more work item states (e.g. 'Active', 'Closed').",
    ] = None,
    assigned_to: Annotated[
        Optional[List[str]],
        "Filter results to one or more assigned-to display names or canonical identity values.",
    ] = None,
    include_facets: Annotated[
        bool,
        "When true, include facet counts in the response.",
    ] = False,
    skip: Annotated[int, "Number of results to skip for pagination."] = 0,
    top: Annotated[int, "Maximum number of results to return (1–200)."] = 25,
) -> object:
    """Search work items across Azure DevOps projects using full-text search."""
    url = _build_search_url("workitemsearchresults")

    payload: dict = {
        "searchText": search_text,
        "includeFacets": include_facets,
        "$skip": skip,
        "$top": top,
    }

    filters: dict = {"System.TeamProject": [_project_name]}
    if area_path:
        filters["System.AreaPath"] = area_path
    if work_item_type:
        filters["System.WorkItemType"] = work_item_type
    if state:
        filters["System.State"] = state
    if assigned_to:
        filters["System.AssignedTo"] = _resolve_assigned_to(assigned_to)
    payload["filters"] = filters

    response = devops_api_post(url, payload, return_response=True)
    _raise_for_error(response)
    return response.json()


@mcp.tool(
    name="devops_wiki_search",
    description=(
        "Search wiki pages in the configured Azure DevOps project. "
        "Returns matching pages with snippet context. "
        "Optionally filter by wiki name."
    ),
)
def wiki_search(
    search_text: Annotated[str, "Keywords to search for in wiki page content and titles."],
    wiki: Annotated[
        Optional[List[str]],
        "Filter results to one or more wiki names.",
    ] = None,
    include_facets: Annotated[
        bool,
        "When true, include facet counts in the response.",
    ] = False,
    skip: Annotated[int, "Number of results to skip for pagination."] = 0,
    top: Annotated[int, "Maximum number of results to return (1–1000)."] = 25,
) -> object:
    """Search wiki pages across Azure DevOps projects using full-text search."""
    url = _build_search_url("wikisearchresults")

    payload: dict = {
        "searchText": search_text,
        "includeFacets": include_facets,
        "$skip": skip,
        "$top": top,
    }

    filters: dict = {"Project": [_project_name]}
    if wiki:
        filters["Wiki"] = wiki
    payload["filters"] = filters

    response = devops_api_post(url, payload, return_response=True)
    _raise_for_error(response)
    return response.json()
