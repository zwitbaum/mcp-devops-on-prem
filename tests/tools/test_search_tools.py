"""Tests for the Azure DevOps Search tools."""

import json

import pytest
import responses as rsps_lib
from fastmcp.exceptions import ToolError

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
CODE_SEARCH_URL = f"{BASE_URL}/_apis/search/codesearchresults?api-version=7.1"
WIKI_SEARCH_URL = f"{BASE_URL}/_apis/search/wikisearchresults?api-version=7.1"


@pytest.fixture()
def configured_search_module(monkeypatch):
    monkeypatch.setattr(search_tools, "devops_api_url", BASE_URL)
    monkeypatch.setattr(search_tools, "_project_name", "project")


@rsps_lib.activate
def test_work_item_search_resolves_assignee_display_name(configured_search_module):
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


@rsps_lib.activate
def test_code_search_sends_all_optional_filters(configured_search_module):
    rsps_lib.add(rsps_lib.POST, CODE_SEARCH_URL, json={"count": 1, "results": []}, status=200)

    result = code_search(
        "Repository",
        repository=["ZEUS-Code"],
        path=["/src"],
        branch=["main"],
        include_facets=True,
        skip=5,
        top=10,
    )

    payload = json.loads(rsps_lib.calls[0].request.body)
    assert result == {"count": 1, "results": []}  # noqa: S101
    assert payload == {  # noqa: S101
        "searchText": "Repository",
        "includeFacets": True,
        "$skip": 5,
        "$top": 10,
        "filters": {
            "Project": ["project"],
            "Repository": ["ZEUS-Code"],
            "Path": ["/src"],
            "Branch": ["main"],
        },
    }


@rsps_lib.activate
def test_code_search_raises_tool_error_for_failed_response(configured_search_module):
    rsps_lib.add(rsps_lib.POST, CODE_SEARCH_URL, body="bad request", status=400)

    with pytest.raises(ToolError, match="Search API request failed with status 400"):
        code_search("Repository")


@rsps_lib.activate
def test_work_item_search_sends_all_optional_filters(configured_search_module):
    rsps_lib.add(rsps_lib.POST, SEARCH_URL, json={"count": 2, "results": []}, status=200)

    result = work_item_search(
        "Systemtest",
        area_path=["project\\Area"],
        work_item_type=["Bug"],
        state=["Active"],
        include_facets=True,
        skip=1,
        top=2,
    )

    payload = json.loads(rsps_lib.calls[0].request.body)
    assert result == {"count": 2, "results": []}  # noqa: S101
    assert payload["filters"] == {  # noqa: S101
        "System.TeamProject": ["project"],
        "System.AreaPath": ["project\\Area"],
        "System.WorkItemType": ["Bug"],
        "System.State": ["Active"],
    }
    assert payload["includeFacets"] is True  # noqa: S101
    assert payload["$skip"] == 1  # noqa: S101
    assert payload["$top"] == 2  # noqa: S101


@rsps_lib.activate
def test_work_item_search_preserves_canonical_assignee(configured_search_module):
    canonical = "Example User <EXAMPLE\\example.user>"
    rsps_lib.add(rsps_lib.POST, SEARCH_URL, json={"count": 1, "results": []}, status=200)

    work_item_search("PuppeteerSharp", assigned_to=[canonical])

    payload = json.loads(rsps_lib.calls[0].request.body)
    assert len(rsps_lib.calls) == 1  # noqa: S101
    assert payload["filters"]["System.AssignedTo"] == [canonical]  # noqa: S101


@rsps_lib.activate
def test_work_item_search_uses_display_name_when_identity_is_not_found(configured_search_module):
    rsps_lib.add(rsps_lib.GET, IDENTITY_URL, json={"value": []}, status=200)
    rsps_lib.add(rsps_lib.POST, SEARCH_URL, json={"count": 0, "results": []}, status=200)

    work_item_search("PuppeteerSharp", assigned_to=[TEST_ASSIGNEE])

    payload = json.loads(rsps_lib.calls[1].request.body)
    assert payload["filters"]["System.AssignedTo"] == [TEST_ASSIGNEE]  # noqa: S101


@rsps_lib.activate
def test_wiki_search_sends_optional_wiki_filter(configured_search_module):
    rsps_lib.add(rsps_lib.POST, WIKI_SEARCH_URL, json={"count": 1, "results": []}, status=200)

    result = wiki_search("release", wiki=["Project Wiki"], include_facets=True, skip=2, top=3)

    payload = json.loads(rsps_lib.calls[0].request.body)
    assert result == {"count": 1, "results": []}  # noqa: S101
    assert payload == {  # noqa: S101
        "searchText": "release",
        "includeFacets": True,
        "$skip": 2,
        "$top": 3,
        "filters": {"Project": ["project"], "Wiki": ["Project Wiki"]},
    }
