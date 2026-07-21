"""Tests for the Azure DevOps Search tools."""

import json

import responses as rsps_lib

from mcp_devops.tools import search_tools


code_search = search_tools.code_search.fn
work_item_search = search_tools.work_item_search.fn
wiki_search = search_tools.wiki_search.fn

BASE_URL = "https://devops.example.com/org/project"
TEST_ASSIGNEE = "Example User"
TEST_DOMAIN = "EXAMPLE"
TEST_ACCOUNT = "example.user"
IDENTITY_URL = (
    "https://devops.example.com/org/_apis/identities?searchFilter=General"
    f"&filterValue=Example%20User&api-version=7.1"
)
SEARCH_URL = f"{BASE_URL}/_apis/search/workitemsearchresults?api-version=7.1"


@rsps_lib.activate
def test_work_item_search_resolves_assignee_display_name(monkeypatch):
    monkeypatch.setattr(search_tools, "devops_api_url", BASE_URL)
    rsps_lib.add(
        rsps_lib.GET,
        IDENTITY_URL,
        json={
            "value": [
                {
                    "providerDisplayName": TEST_ASSIGNEE,
                    "properties": {
                        "Domain": {"$value": TEST_DOMAIN},
                        "Account": {"$value": TEST_ACCOUNT},
                    },
                }
            ]
        },
        status=200,
    )
    rsps_lib.add(rsps_lib.POST, SEARCH_URL, json={"count": 1, "results": []}, status=200)

    work_item_search("PuppeteerSharp", assigned_to=[TEST_ASSIGNEE])

    assert len(rsps_lib.calls) == 2  # noqa: S101
    search_payload = json.loads(rsps_lib.calls[1].request.body)
    assert search_payload["filters"]["System.AssignedTo"] == [  # noqa: S101
        f"{TEST_ASSIGNEE} <{TEST_DOMAIN}\\{TEST_ACCOUNT}>"
    ]  # noqa: S101
