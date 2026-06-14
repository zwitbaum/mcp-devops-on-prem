"""Tests for work_item_tools — all public tools and private helpers.

Auth coverage lives in test_shared.py. All tests use Bearer token auth.
"""

import json
import re
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest
import responses as rsps_lib
from fastmcp.exceptions import ToolError

from mcp_devops.tools.work_item_tools import (
    _build_artifact_vstfs_url,
    _extract_attachments,
    _extract_inline_images,
    _extract_links,
    _extract_person,
    _get_link_rel,
    _patch_work_item,
    add_work_item_comment,
    create_work_item,
    delete_work_item,
    delete_work_item_comment,
    get_work_item,
    get_work_item_attachment,
    get_work_item_type,
    list_work_item_comments,
    undelete_work_item,
    update_work_item,
    update_work_item_artifact_link,
    update_work_item_comment,
    update_work_item_link,
)
from tests.mocks.work_items import (
    ADD_COMMENT_RESPONSE,
    ATTACHMENT_BINARY,
    BATCH_RESPONSE,
    BUG_WORK_ITEM_RESPONSE,
    COMMENTS_RESPONSE,
    CREATE_WORK_ITEM_RESPONSE,
    PATCH_RESPONSE,
    UPDATE_COMMENT_RESPONSE,
    UPDATE_WORK_ITEM_RESPONSE,
    WIQL_EMPTY_RESPONSE,
    WIQL_RESPONSE,
    WIQL_TREE_RESPONSE,
    WORK_ITEM_RESPONSE,
    WORK_ITEM_TYPE_RESPONSE,
    WORK_ITEM_WITH_ARTIFACT_RELATIONS_RESPONSE,
    WORK_ITEM_WITH_COMMIT_LINK_RESPONSE,
    WORK_ITEM_WITH_INLINE_IMAGE_RESPONSE,
    WORK_ITEM_WITH_RELATIONS_RESPONSE,
)

# Unwrap @mcp.tool() FunctionTool wrappers
get_work_item = get_work_item.fn
get_work_item_attachment = get_work_item_attachment.fn
get_work_item_type = get_work_item_type.fn
create_work_item = create_work_item.fn
update_work_item = update_work_item.fn
delete_work_item = delete_work_item.fn
undelete_work_item = undelete_work_item.fn
update_work_item_link = update_work_item_link.fn
update_work_item_artifact_link = update_work_item_artifact_link.fn
list_work_item_comments = list_work_item_comments.fn
add_work_item_comment = add_work_item_comment.fn
update_work_item_comment = update_work_item_comment.fn
delete_work_item_comment = delete_work_item_comment.fn

BASE_URL = "https://devops.example.com/org/project"
WIT_BASE = f"{BASE_URL}/_apis/wit"


@pytest.fixture()
def token_auth(monkeypatch):
    monkeypatch.setenv("DEVOPS_TOKEN", "test-token")


# ---------------------------------------------------------------------------
# _extract_person
# ---------------------------------------------------------------------------


class TestExtractPerson:
    def test_returns_display_and_unique_name(self):
        result = _extract_person({"displayName": "Alice", "uniqueName": "alice@x.com"})
        assert result == {"displayName": "Alice", "uniqueName": "alice@x.com"}

    def test_returns_none_for_none_input(self):
        assert _extract_person(None) is None

    def test_returns_none_for_empty_dict(self):
        assert _extract_person({}) is None

    def test_handles_missing_fields(self):
        result = _extract_person({"displayName": "Alice"})
        assert result["displayName"] == "Alice"
        assert result["uniqueName"] is None


# ---------------------------------------------------------------------------
# _extract_attachments
# ---------------------------------------------------------------------------


class TestExtractAttachments:
    def test_extracts_attached_file_guid(self):
        relations = [
            {
                "rel": "AttachedFile",
                "url": f"{BASE_URL}/_apis/wit/attachments/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "attributes": {
                    "name": "file.txt",
                    "resourceSize": 100,
                    "resourceModifiedDate": "2024-01-01",
                },
            }
        ]
        result = _extract_attachments(relations)
        assert len(result) == 1
        assert result[0]["fileId"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert result[0]["fileName"] == "file.txt"
        assert result[0]["fileType"] == "attachment"

    def test_ignores_non_attached_file_relations(self):
        relations = [{"rel": "System.LinkTypes.Related", "url": "...", "attributes": {}}]
        assert _extract_attachments(relations) == []

    def test_handles_empty_relations_list(self):
        assert _extract_attachments([]) == []

    def test_file_id_is_none_when_url_has_no_guid(self):
        relations = [
            {"rel": "AttachedFile", "url": "https://example.com/no-guid-here", "attributes": {}}
        ]
        result = _extract_attachments(relations)
        assert result[0]["fileId"] is None


# ---------------------------------------------------------------------------
# _extract_inline_images
# ---------------------------------------------------------------------------


class TestExtractInlineImages:
    def test_extracts_image_from_description(self, devops_url):
        description = (
            f'<img src="{BASE_URL}/_apis/wit/attachments/'
            f'11111111-2222-3333-4444-555555555555?fileName=diagram.png" />'
        )
        result = _extract_inline_images(description)
        assert len(result) == 1
        assert result[0]["fileId"] == "11111111-2222-3333-4444-555555555555"
        assert result[0]["fileName"] == "diagram.png"
        assert result[0]["fileType"] == "inlineImage"

    def test_returns_empty_list_for_none(self, devops_url):
        assert _extract_inline_images(None) == []

    def test_returns_empty_list_for_empty_string(self, devops_url):
        assert _extract_inline_images("") == []

    def test_returns_empty_for_non_devops_image(self, devops_url):
        description = '<img src="https://other.com/image.png" />'
        assert _extract_inline_images(description) == []

    def test_decodes_url_encoded_filename(self, devops_url):
        description = (
            f'<img src="{BASE_URL}/_apis/wit/attachments/'
            f'aaaaaaaa-0000-0000-0000-bbbbbbbbbbbb?fileName=my%20file.png" />'
        )
        result = _extract_inline_images(description)
        assert result[0]["fileName"] == "my file.png"


# ---------------------------------------------------------------------------
# _extract_links
# ---------------------------------------------------------------------------


class TestExtractLinks:
    def test_extracts_work_item_link(self):
        relations = [
            {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"{BASE_URL}/_apis/wit/workItems/10",
                "attributes": {"name": "Parent"},
            }
        ]
        result = _extract_links(relations)
        assert len(result) == 1
        assert result[0]["type"] == "Work Item"
        assert result[0]["id"] == 10
        assert result[0]["name"] == "Parent"

    def test_handles_invalid_work_item_url(self):
        relations = [
            {
                "rel": "System.LinkTypes.Related",
                "url": "https://example.com/not-a-number",
                "attributes": {"name": "Related"},
            }
        ]
        result = _extract_links(relations)
        assert result[0]["id"] is None

    def test_extracts_pull_request_artifact_link(self):
        relations = [
            {
                "rel": "ArtifactLink",
                "url": f"vstfs:///Git/PullRequestId/proj-id%2Frepo-id%2F99",
                "attributes": {"name": "Pull Request"},
            }
        ]
        result = _extract_links(relations)
        assert len(result) == 1
        assert result[0]["type"] == "Artifact"
        assert result[0]["name"] == "Pull Request"
        assert result[0]["id"] == "99"

    def test_extracts_commit_artifact_link(self):
        relations = [
            {
                "rel": "ArtifactLink",
                "url": "vstfs:///Git/Commit/proj%2Frepo%2Fabcdef12",
                "attributes": {"name": "Commit"},
            }
        ]
        result = _extract_links(relations)
        assert result[0]["name"] == "Commit"
        assert result[0]["id"] == "abcdef12"

    def test_ignores_unrecognised_artifact_links(self):
        relations = [
            {
                "rel": "ArtifactLink",
                "url": "vstfs:///Build/Build/123",
                "attributes": {"name": "Build"},
            }
        ]
        # No PullRequestId or Git/Commit in URL → not added to result
        result = _extract_links(relations)
        assert result == []

    def test_ignores_attached_file_relations(self):
        relations = [{"rel": "AttachedFile", "url": "...", "attributes": {}}]
        assert _extract_links(relations) == []

    def test_empty_relations_returns_empty(self):
        assert _extract_links([]) == []


# ---------------------------------------------------------------------------
# _get_link_rel
# ---------------------------------------------------------------------------


class TestGetLinkRel:
    def test_maps_parent(self):
        assert _get_link_rel("parent") == "System.LinkTypes.Hierarchy-Reverse"

    def test_maps_child(self):
        assert _get_link_rel("child") == "System.LinkTypes.Hierarchy-Forward"

    def test_case_insensitive(self):
        assert _get_link_rel("RELATED") == "System.LinkTypes.Related"

    def test_strips_whitespace(self):
        assert _get_link_rel("  related  ") == "System.LinkTypes.Related"

    def test_raises_for_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown link type"):
            _get_link_rel("unknown-link")


# ---------------------------------------------------------------------------
# _build_artifact_vstfs_url
# ---------------------------------------------------------------------------


class TestBuildArtifactVstfsUrl:
    def test_build_url_returns_tuple(self):
        url, name = _build_artifact_vstfs_url("Pull Request", "proj/repo/42")
        assert url.startswith("vstfs:///Git/PullRequestId/")
        assert name == "Pull Request"

    def test_commit_type(self):
        url, name = _build_artifact_vstfs_url("commit", "proj/repo/abcdef")
        assert "Commit" in url
        assert name == "Fixed in Commit"

    def test_branch_type_prepends_gb(self):
        url, name = _build_artifact_vstfs_url("branch", "proj/repo/main")
        assert "GBmain" in urllib.parse.unquote(url)
        assert name == "Branch"

    def test_versioned_item_type(self):
        url, name = _build_artifact_vstfs_url("versioned item", "proj/repo/src/foo.cs")
        assert "Blob" in url

    def test_build_type(self):
        url, name = _build_artifact_vstfs_url("build", "12345")
        assert "vstfs:///Build/Build/12345" == url

    def test_found_in_build(self):
        url, name = _build_artifact_vstfs_url("Found in build", "99")
        assert "Build/Build/99" in url

    def test_changeset_type(self):
        url, name = _build_artifact_vstfs_url("changeset", "42")
        assert "VersionControl/Changeset/42" in url
        assert name == "Changeset"

    def test_git_type_with_too_few_parts_raises(self):
        with pytest.raises(ValueError, match="artifact_id for link_type"):
            _build_artifact_vstfs_url("pull request", "proj/repo")

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown artifact link_type"):
            _build_artifact_vstfs_url("unknown type", "proj/repo/detail")


# ---------------------------------------------------------------------------
# _patch_work_item
# ---------------------------------------------------------------------------


class TestPatchWorkItem:
    @rsps_lib.activate
    def test_sends_patch_to_correct_url(self, devops_url, token_auth):
        expected = f"{WIT_BASE}/workitems/42?api-version=7.1"
        rsps_lib.add(rsps_lib.PATCH, expected, json=PATCH_RESPONSE, status=200)

        _patch_work_item(42, [{"op": "add", "path": "/fields/System.Title", "value": "X"}])

        assert rsps_lib.calls[0].request.url == expected

    @rsps_lib.activate
    def test_appends_validate_only_param(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        _patch_work_item(42, [], validate_only=True)

        assert "validateOnly=true" in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_appends_validate_only_false(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        _patch_work_item(42, [], validate_only=False)

        assert "validateOnly=false" in rsps_lib.calls[0].request.url


# ---------------------------------------------------------------------------
# get_work_item
# ---------------------------------------------------------------------------


class TestGetWorkItem:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        url = f"{WIT_BASE}/workitems/42?$expand=1"
        rsps_lib.add(rsps_lib.GET, url, json=WORK_ITEM_RESPONSE, status=200)

        get_work_item(42)

        assert rsps_lib.calls[0].request.url == url

    @rsps_lib.activate
    def test_returns_mapped_fields(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems/42.*"), json=WORK_ITEM_RESPONSE, status=200)

        result = get_work_item(42)

        assert result["id"] == 42
        assert result["title"] == "My & Work Item"  # HTML-unescaped
        assert result["state"] == "Active"
        assert result["workItemType"] == "User Story"

    @rsps_lib.activate
    def test_html_unescapes_title_and_description(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems/42.*"), json=WORK_ITEM_RESPONSE, status=200)

        result = get_work_item(42)

        assert "&amp;" not in result["title"]
        assert "&amp;" not in result["description"]

    @rsps_lib.activate
    def test_extracts_attachment(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems/42.*"), json=WORK_ITEM_RESPONSE, status=200)

        result = get_work_item(42)

        assert len(result["attachments"]) == 1
        assert result["attachments"][0]["fileName"] == "screenshot.png"

    @rsps_lib.activate
    def test_extracts_work_item_link(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems/42.*"), json=WORK_ITEM_RESPONSE, status=200)

        result = get_work_item(42)

        wi_links = [l for l in result["links"] if l["type"] == "Work Item"]
        assert len(wi_links) == 1
        assert wi_links[0]["id"] == 10

    @rsps_lib.activate
    def test_bug_uses_repro_steps_as_description(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems/43.*"), json=BUG_WORK_ITEM_RESPONSE, status=200)

        result = get_work_item(43)

        assert result["description"] == "<p>Steps to reproduce</p>"

    @rsps_lib.activate
    def test_extracts_inline_image(self, devops_url, token_auth):
        rsps_lib.add(
            rsps_lib.GET, re.compile(r".*workitems/44.*"), json=WORK_ITEM_WITH_INLINE_IMAGE_RESPONSE, status=200
        )

        result = get_work_item(44)

        inline = [a for a in result["attachments"] if a["fileType"] == "inlineImage"]
        assert len(inline) == 1
        assert inline[0]["fileName"] == "diagram.png"

    @rsps_lib.activate
    def test_none_relations_handled(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitems/43.*"), json=BUG_WORK_ITEM_RESPONSE, status=200)

        result = get_work_item(43)

        assert result["attachments"] == []
        assert result["links"] == []

    @rsps_lib.activate
    def test_commit_artifact_link_extracted(self, devops_url, token_auth):
        rsps_lib.add(
            rsps_lib.GET, re.compile(r".*workitems/45.*"), json=WORK_ITEM_WITH_COMMIT_LINK_RESPONSE, status=200
        )

        result = get_work_item(45)

        commit_links = [l for l in result["links"] if l["name"] == "Commit"]
        assert len(commit_links) == 1


# ---------------------------------------------------------------------------
# get_work_item_attachment
# ---------------------------------------------------------------------------


class TestGetWorkItemAttachment:
    @rsps_lib.activate
    def test_returns_base64_content(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*attachments.*"), body=ATTACHMENT_BINARY, status=200)

        result = get_work_item_attachment("aaaa-bbbb", "image.png")

        import base64
        assert result["fileName"] == "image.png"
        assert result["mimeType"] == "image/png"
        assert base64.b64decode(result["content_base64"]) == ATTACHMENT_BINARY

    @rsps_lib.activate
    def test_unknown_mime_type_defaults_to_octet_stream(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*attachments.*"), body=b"\x00\x01\x02", status=200)

        result = get_work_item_attachment("aaaa", "file.unknownextxyz")

        assert result["mimeType"] == "application/octet-stream"

    @rsps_lib.activate
    def test_saves_to_disk_when_save_path_provided(self, devops_url, token_auth, tmp_path):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*attachments.*"), body=ATTACHMENT_BINARY, status=200)

        result = get_work_item_attachment("aaaa-bbbb", "image.png", save_path=str(tmp_path))

        saved = tmp_path / "image.png"
        assert saved.exists()
        assert saved.read_bytes() == ATTACHMENT_BINARY
        assert result["size_bytes"] == len(ATTACHMENT_BINARY)

    def test_raises_for_path_traversal(self, devops_url, token_auth):
        with pytest.raises(ValueError, match="must not traverse"):
            get_work_item_attachment("aaaa", "file.txt", save_path="../outside")


# ---------------------------------------------------------------------------
# get_work_item_type
# ---------------------------------------------------------------------------


class TestGetWorkItemType:
    @rsps_lib.activate
    def test_builds_correct_url_with_encoded_type(self, devops_url, token_auth):
        url = f"{WIT_BASE}/workitemtypes/Bug"
        rsps_lib.add(rsps_lib.GET, url, json=WORK_ITEM_TYPE_RESPONSE, status=200)

        result = get_work_item_type("Bug")

        assert rsps_lib.calls[0].request.url == url
        assert result["name"] == "Bug"

    @rsps_lib.activate
    def test_url_encodes_type_with_spaces(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workitemtypes.*"), json=WORK_ITEM_TYPE_RESPONSE, status=200)

        get_work_item_type("User Story")

        assert "User%20Story" in rsps_lib.calls[0].request.url


# ---------------------------------------------------------------------------
# query_work_items_by_wiql (via mcp tool wrapper)
# ---------------------------------------------------------------------------


from mcp_devops.tools.work_item_tools import query_work_items_by_wiql
query_work_items_by_wiql = query_work_items_by_wiql.fn


class TestQueryWorkItemsByWiql:
    @rsps_lib.activate
    def test_posts_wiql_and_batches_results(self, devops_url, token_auth):
        wiql_url = f"{WIT_BASE}/wiql?api-version=7.1"
        batch_url = f"{WIT_BASE}/workitemsbatch?api-version=7.1"
        rsps_lib.add(rsps_lib.POST, wiql_url, json=WIQL_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.POST, batch_url, json=BATCH_RESPONSE, status=200)

        result = query_work_items_by_wiql("SELECT [System.Id] FROM WorkItems")

        assert result["count"] == 2
        assert result["queryType"] == "flat"
        assert len(result["workItems"]) == 2

    @rsps_lib.activate
    def test_tree_result_returned_as_is(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*wiql.*"), json=WIQL_TREE_RESPONSE, status=200)

        result = query_work_items_by_wiql("SELECT ... FROM WorkItemLinks")

        assert result["queryType"] == "tree"
        assert "workItemRelations" in result

    @rsps_lib.activate
    def test_empty_result_returned_as_is(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*wiql.*"), json=WIQL_EMPTY_RESPONSE, status=200)

        result = query_work_items_by_wiql("SELECT [System.Id] FROM WorkItems WHERE 1=0")

        # empty workItems → returned as-is (no batch call)
        assert result["workItems"] == []
        assert len(rsps_lib.calls) == 1

    @rsps_lib.activate
    def test_appends_top_param(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*wiql.*"), json=WIQL_EMPTY_RESPONSE, status=200)

        query_work_items_by_wiql("SELECT [System.Id] FROM WorkItems", top=10)

        assert "$top=10" in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_appends_time_precision_param(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*wiql.*"), json=WIQL_EMPTY_RESPONSE, status=200)

        query_work_items_by_wiql("SELECT [System.Id] FROM WorkItems", time_precision=True)

        assert "timePrecision=true" in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_truncated_flag_set_when_over_200(self, devops_url, token_auth):
        many_items = [{"id": i, "url": f"{BASE_URL}/_apis/wit/workItems/{i}"} for i in range(1, 205)]
        wiql_many = {**WIQL_RESPONSE, "workItems": many_items}
        rsps_lib.add(rsps_lib.POST, re.compile(r".*wiql.*"), json=wiql_many, status=200)
        rsps_lib.add(rsps_lib.POST, re.compile(r".*workitemsbatch.*"), json=BATCH_RESPONSE, status=200)

        result = query_work_items_by_wiql("SELECT [System.Id] FROM WorkItems")

        assert result["truncated"] is True
        assert result["totalMatched"] == 204

    @rsps_lib.activate
    def test_uses_default_fields_when_columns_empty(self, devops_url, token_auth):
        wiql_no_cols = {**WIQL_RESPONSE, "columns": []}
        rsps_lib.add(rsps_lib.POST, re.compile(r".*wiql.*"), json=wiql_no_cols, status=200)
        rsps_lib.add(rsps_lib.POST, re.compile(r".*workitemsbatch.*"), json=BATCH_RESPONSE, status=200)

        query_work_items_by_wiql("SELECT [System.Id] FROM WorkItems")

        batch_body = json.loads(rsps_lib.calls[1].request.body)
        assert "System.Id" in batch_body["fields"]
        assert "System.Title" in batch_body["fields"]


# ---------------------------------------------------------------------------
# create_work_item
# ---------------------------------------------------------------------------


class TestCreateWorkItem:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        url = f"{WIT_BASE}/workitems/$Task?api-version=7.1"
        rsps_lib.add(rsps_lib.POST, url, json=CREATE_WORK_ITEM_RESPONSE, status=200)

        create_work_item("Task", [{"name": "System.Title", "value": "My Task"}])

        assert rsps_lib.calls[0].request.url == url

    @rsps_lib.activate
    def test_url_encodes_type_with_spaces(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*workitems.*"), json=CREATE_WORK_ITEM_RESPONSE, status=200)

        create_work_item("User Story", [{"name": "System.Title", "value": "Story"}])

        assert "User%20Story" in rsps_lib.calls[0].request.url

    @rsps_lib.activate
    def test_sends_json_patch_document(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*workitems.*"), json=CREATE_WORK_ITEM_RESPONSE, status=200)

        create_work_item("Task", [{"name": "System.Title", "value": "My Task"}])

        body = json.loads(rsps_lib.calls[0].request.body)
        assert isinstance(body, list)
        assert body[0]["op"] == "add"
        assert body[0]["path"] == "/fields/System.Title"
        assert body[0]["value"] == "My Task"

    @rsps_lib.activate
    def test_markdown_format_hint_added_for_long_value(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*workitems.*"), json=CREATE_WORK_ITEM_RESPONSE, status=200)

        long_value = "x" * 200
        create_work_item(
            "Task",
            [{"name": "System.Description", "value": long_value, "format": "Markdown"}],
        )

        body = json.loads(rsps_lib.calls[0].request.body)
        paths = [op["path"] for op in body]
        assert "/multilineFieldsFormat/System.Description" in paths

    @rsps_lib.activate
    def test_no_markdown_hint_for_short_value(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*workitems.*"), json=CREATE_WORK_ITEM_RESPONSE, status=200)

        create_work_item(
            "Task",
            [{"name": "System.Description", "value": "Short", "format": "Markdown"}],
        )

        body = json.loads(rsps_lib.calls[0].request.body)
        paths = [op["path"] for op in body]
        assert "/multilineFieldsFormat/System.Description" not in paths

    @rsps_lib.activate
    def test_appends_validate_only_param(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*workitems.*"), json=CREATE_WORK_ITEM_RESPONSE, status=200)

        create_work_item("Task", [{"name": "System.Title", "value": "X"}], validate_only=True)

        assert "validateOnly=true" in rsps_lib.calls[0].request.url


# ---------------------------------------------------------------------------
# update_work_item
# ---------------------------------------------------------------------------


class TestUpdateWorkItem:
    @rsps_lib.activate
    def test_sends_patch_with_correct_fields(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=UPDATE_WORK_ITEM_RESPONSE, status=200)

        update_work_item(42, [{"name": "System.Title", "value": "New Title"}])

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body[0]["path"] == "/fields/System.Title"
        assert body[0]["value"] == "New Title"

    @rsps_lib.activate
    def test_remove_op_omits_value(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=UPDATE_WORK_ITEM_RESPONSE, status=200)

        update_work_item(42, [{"op": "remove", "name": "System.Tags"}])

        body = json.loads(rsps_lib.calls[0].request.body)
        assert "value" not in body[0]

    def test_raises_for_invalid_op(self, devops_url, token_auth):
        with pytest.raises(ValueError, match="Invalid op"):
            update_work_item(42, [{"op": "invalid", "name": "System.Title", "value": "X"}])

    @rsps_lib.activate
    def test_defaults_op_to_add(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=UPDATE_WORK_ITEM_RESPONSE, status=200)

        update_work_item(42, [{"name": "System.Title", "value": "X"}])

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body[0]["op"] == "add"


# ---------------------------------------------------------------------------
# delete_work_item
# ---------------------------------------------------------------------------


class TestDeleteWorkItem:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        url = f"{WIT_BASE}/workitems/42?api-version=7.1"
        rsps_lib.add(rsps_lib.DELETE, url, status=204)

        result = delete_work_item(42)

        assert rsps_lib.calls[0].request.url == url
        assert result == {"deleted": True, "work_item_id": 42, "permanent": False}

    @rsps_lib.activate
    def test_appends_destroy_param(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.DELETE, re.compile(r".*workitems/42.*"), status=204)

        result = delete_work_item(42, destroy=True)

        assert "destroy=true" in rsps_lib.calls[0].request.url
        assert result["permanent"] is True


# ---------------------------------------------------------------------------
# undelete_work_item
# ---------------------------------------------------------------------------


class TestUndeleteWorkItem:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        url = f"{WIT_BASE}/recyclebin/42?api-version=7.1"
        rsps_lib.add(rsps_lib.PATCH, url, json={"id": 42, "isDeleted": False}, status=200)

        undelete_work_item(42)

        assert rsps_lib.calls[0].request.url == url

    @rsps_lib.activate
    def test_sends_is_deleted_false(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*recyclebin.*"), json={"id": 42}, status=200)

        undelete_work_item(42)

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body == {"isDeleted": False}


# ---------------------------------------------------------------------------
# update_work_item_link
# ---------------------------------------------------------------------------


class TestUpdateWorkItemLink:
    @rsps_lib.activate
    def test_add_link_sends_patch(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        update_work_item_link(42, 99, op="add", link_type="related")

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body[0]["op"] == "add"
        assert body[0]["value"]["rel"] == "System.LinkTypes.Related"

    @rsps_lib.activate
    def test_add_includes_comment(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        update_work_item_link(42, 99, comment="My comment")

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body[0]["value"]["attributes"]["comment"] == "My comment"

    @rsps_lib.activate
    def test_remove_link_fetches_then_patches(self, devops_url, token_auth):
        get_url = f"{WIT_BASE}/workitems/42?$expand=1"
        rsps_lib.add(rsps_lib.GET, get_url, json=WORK_ITEM_WITH_RELATIONS_RESPONSE, status=200)
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        update_work_item_link(42, 99, op="remove", link_type="related")

        assert rsps_lib.calls[0].request.method == "GET"
        body = json.loads(rsps_lib.calls[1].request.body)
        assert body[0]["op"] == "remove"

    @rsps_lib.activate
    def test_remove_raises_when_link_not_found(self, devops_url, token_auth):
        rsps_lib.add(
            rsps_lib.GET,
            re.compile(r".*workitems/42.*"),
            json={"id": 42, "relations": []},
            status=200,
        )

        with pytest.raises(ValueError, match="No 'related' link"):
            update_work_item_link(42, 99, op="remove", link_type="related")

    def test_raises_for_invalid_op(self, devops_url, token_auth):
        with pytest.raises(ValueError, match="Invalid op"):
            update_work_item_link(42, 99, op="upsert")

    def test_raises_for_unknown_link_type(self, devops_url, token_auth):
        with pytest.raises(ValueError, match="Unknown link type"):
            update_work_item_link(42, 99, link_type="unknown-type")

    @rsps_lib.activate
    def test_remove_sorts_indexes_descending(self, devops_url, token_auth):
        """Multiple matching relations → removed in descending index order."""
        rsps_lib.add(
            rsps_lib.GET,
            re.compile(r".*workitems/42.*"),
            json=WORK_ITEM_WITH_RELATIONS_RESPONSE,
            status=200,
        )
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        update_work_item_link(42, 99, op="remove", link_type="related")

        body = json.loads(rsps_lib.calls[1].request.body)
        indexes = [int(op["path"].split("/")[-1]) for op in body]
        assert indexes == sorted(indexes, reverse=True)


# ---------------------------------------------------------------------------
# update_work_item_artifact_link
# ---------------------------------------------------------------------------


class TestUpdateWorkItemArtifactLink:
    @rsps_lib.activate
    def test_add_artifact_link(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        update_work_item_artifact_link(42, "Pull Request", "proj/repo/7", op="add")

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body[0]["value"]["rel"] == "ArtifactLink"
        assert "PullRequestId" in body[0]["value"]["url"]

    @rsps_lib.activate
    def test_remove_artifact_link(self, devops_url, token_auth):
        rsps_lib.add(
            rsps_lib.GET,
            re.compile(r".*workitems/42.*"),
            json=WORK_ITEM_WITH_ARTIFACT_RELATIONS_RESPONSE,
            status=200,
        )
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        update_work_item_artifact_link(42, "Pull Request", "proj/repo/7", op="remove")

        body = json.loads(rsps_lib.calls[1].request.body)
        assert body[0]["op"] == "remove"

    @rsps_lib.activate
    def test_remove_raises_when_not_found(self, devops_url, token_auth):
        rsps_lib.add(
            rsps_lib.GET,
            re.compile(r".*workitems/42.*"),
            json={"id": 42, "relations": []},
            status=200,
        )

        with pytest.raises(ValueError, match="No 'Pull Request' artifact link"):
            update_work_item_artifact_link(42, "Pull Request", "proj/repo/7", op="remove")

    def test_raises_for_invalid_op(self, devops_url, token_auth):
        with pytest.raises(ValueError, match="Invalid op"):
            update_work_item_artifact_link(42, "Pull Request", "proj/repo/7", op="upsert")

    @rsps_lib.activate
    def test_add_sends_comment(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*workitems/42.*"), json=PATCH_RESPONSE, status=200)

        update_work_item_artifact_link(42, "Pull Request", "proj/repo/7", comment="Link to PR")

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body[0]["value"]["attributes"]["comment"] == "Link to PR"


# ---------------------------------------------------------------------------
# list_work_item_comments
# ---------------------------------------------------------------------------


class TestListWorkItemComments:
    @rsps_lib.activate
    def test_builds_correct_url(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*workItems/42/comments.*"), json=COMMENTS_RESPONSE, status=200)

        list_work_item_comments(42)

        url = rsps_lib.calls[0].request.url
        assert "workItems/42/comments" in url
        assert "format=html" in url
        assert "$top=50" in url

    @rsps_lib.activate
    def test_custom_top_and_format(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*comments.*"), json=COMMENTS_RESPONSE, status=200)

        list_work_item_comments(42, top=10, format="markdown")

        url = rsps_lib.calls[0].request.url
        assert "format=markdown" in url
        assert "$top=10" in url

    @rsps_lib.activate
    def test_returns_api_response(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.GET, re.compile(r".*comments.*"), json=COMMENTS_RESPONSE, status=200)

        result = list_work_item_comments(42)

        assert result["count"] == 2


# ---------------------------------------------------------------------------
# add_work_item_comment
# ---------------------------------------------------------------------------


class TestAddWorkItemComment:
    @rsps_lib.activate
    def test_posts_to_correct_url(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*comments.*"), json=ADD_COMMENT_RESPONSE, status=200)

        add_work_item_comment(42, "Hello")

        url = rsps_lib.calls[0].request.url
        assert "workItems/42/comments" in url
        assert "format=html" in url

    @rsps_lib.activate
    def test_sends_text_in_payload(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*comments.*"), json=ADD_COMMENT_RESPONSE, status=200)

        add_work_item_comment(42, "My comment")

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["text"] == "My comment"

    @rsps_lib.activate
    def test_markdown_format_used(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.POST, re.compile(r".*comments.*"), json=ADD_COMMENT_RESPONSE, status=200)

        add_work_item_comment(42, "# Heading", format="markdown")

        assert "format=markdown" in rsps_lib.calls[0].request.url


# ---------------------------------------------------------------------------
# update_work_item_comment
# ---------------------------------------------------------------------------


class TestUpdateWorkItemComment:
    @rsps_lib.activate
    def test_patches_correct_url(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*comments/5.*"), json=UPDATE_COMMENT_RESPONSE, status=200)

        update_work_item_comment(42, 5, "Updated text")

        url = rsps_lib.calls[0].request.url
        assert "workItems/42/comments/5" in url

    @rsps_lib.activate
    def test_sends_text_in_payload(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.PATCH, re.compile(r".*comments.*"), json=UPDATE_COMMENT_RESPONSE, status=200)

        update_work_item_comment(42, 5, "New text")

        body = json.loads(rsps_lib.calls[0].request.body)
        assert body["text"] == "New text"


# ---------------------------------------------------------------------------
# delete_work_item_comment
# ---------------------------------------------------------------------------


class TestDeleteWorkItemComment:
    @rsps_lib.activate
    def test_deletes_correct_url(self, devops_url, token_auth):
        rsps_lib.add(rsps_lib.DELETE, re.compile(r".*comments/5.*"), status=204)

        result = delete_work_item_comment(42, 5)

        url = rsps_lib.calls[0].request.url
        assert "workItems/42/comments/5" in url
        assert result == {"deleted": True, "work_item_id": 42, "comment_id": 5}
