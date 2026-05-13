from typing import Annotated

from mcp_devops.shared import devops_api_url, mcp, fetch_work_item


@mcp.tool(
    name="devops_get_work_item",
    description="Retrieve a single work item (PBI) by its numeric ID.",
)
def get_work_item(
    work_item_id: Annotated[int, "The numeric work item ID to fetch."],
) -> object:
    """Fetch a single work item by ID and return a simplified JSON object."""
    url = f"{devops_api_url}/_apis/wit/workitems/{work_item_id}"
    return fetch_work_item(url)
