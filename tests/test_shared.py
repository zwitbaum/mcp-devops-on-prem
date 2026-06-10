"""Tests for the shared helper functions in mcp_devops.shared.

Covers:
- _get_auth_headers_and_kwargs() — all three auth paths
- get_base_api_url() — pure URL builder
- devops_api_get/post/put/patch/delete — HTTP method wrappers (return_response variants)
- fetch_work_item() — conditional field extraction
- devops_api_get_binary_stream/binary — binary download helpers
"""

import pytest
import responses as rsps_lib
from requests.auth import HTTPBasicAuth
from requests_ntlm import HttpNtlmAuth

from mcp_devops.shared import (
    _get_auth_headers_and_kwargs,
    devops_api_delete,
    devops_api_get,
    devops_api_get_binary,
    devops_api_get_binary_stream,
    devops_api_patch,
    devops_api_post,
    devops_api_put,
    fetch_work_item,
    get_base_api_url,
)

_TEST_URL = "https://devops.example.com/org/project/_apis/test"


class TestGetAuthHeadersAndKwargs:
    """Unit tests for all three supported authentication paths."""

    def test_bearer_token_sets_authorization_header(self, monkeypatch):
        """When DEVOPS_TOKEN is set, a Bearer header is added and auth is None."""
        monkeypatch.setenv("DEVOPS_TOKEN", "my-bearer-token")

        headers, auth = _get_auth_headers_and_kwargs()

        assert headers["Authorization"] == "Bearer my-bearer-token"
        assert auth is None

    def test_bearer_token_takes_precedence_over_pat(self, monkeypatch):
        """DEVOPS_TOKEN wins when both DEVOPS_TOKEN and DEVOPS_PAT are set."""
        monkeypatch.setenv("DEVOPS_TOKEN", "token-wins")
        monkeypatch.setenv("DEVOPS_PAT", "pat-loses")

        headers, auth = _get_auth_headers_and_kwargs()

        assert "Bearer token-wins" in headers["Authorization"]
        assert auth is None

    def test_pat_uses_http_basic_auth(self, monkeypatch):
        """When only DEVOPS_PAT is set, HTTPBasicAuth is returned."""
        monkeypatch.setenv("DEVOPS_PAT", "my-pat")
        monkeypatch.setenv("DEVOPS_USERNAME", "alice")

        headers, auth = _get_auth_headers_and_kwargs()

        assert "Authorization" not in headers
        assert isinstance(auth, HTTPBasicAuth)
        assert auth.username == "alice"
        assert auth.password == "my-pat"

    def test_pat_without_username_uses_empty_string(self, monkeypatch):
        """DEVOPS_USERNAME defaults to empty string when not set alongside PAT."""
        monkeypatch.setenv("DEVOPS_PAT", "my-pat")
        # DEVOPS_USERNAME intentionally absent (cleared by autouse fixture)

        headers, auth = _get_auth_headers_and_kwargs()

        assert isinstance(auth, HTTPBasicAuth)
        assert auth.username == ""

    def test_ntlm_fallback_when_no_token_or_pat(self, monkeypatch):
        """When neither token nor PAT is set, NTLM auth is used."""
        monkeypatch.setenv("DEVOPS_USERNAME", "DOMAIN\\alice")
        monkeypatch.setenv("DEVOPS_PASSWORD", "secret")

        headers, auth = _get_auth_headers_and_kwargs()

        assert "Authorization" not in headers
        assert isinstance(auth, HttpNtlmAuth)
        assert auth.username == "DOMAIN\\alice"
        assert auth.password == "secret"

    def test_accept_header_always_present(self, monkeypatch):
        """The Accept: application/json header is always included."""
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")

        headers, _ = _get_auth_headers_and_kwargs()

        assert headers.get("Accept") == "application/json"

    def test_extra_headers_are_merged(self, monkeypatch):
        """Extra headers passed in are merged into the result."""
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")

        headers, _ = _get_auth_headers_and_kwargs(
            extra_headers={"Content-Type": "application/json", "X-Custom": "value"}
        )

        assert headers["Content-Type"] == "application/json"
        assert headers["X-Custom"] == "value"


class TestGetBaseApiUrl:
    """Tests for the pure URL builder."""

    def test_builds_correct_url(self, monkeypatch):
        monkeypatch.setattr("mcp_devops.shared.devops_url", "https://devops.example.com")

        url = get_base_api_url("MyOrg", "MyProject", "_apis/git/repositories")

        assert url == "https://devops.example.com/MyOrg/MyProject/_apis/git/repositories"


class TestDevopsApiGet:
    """Tests for devops_api_get HTTP wrapper."""

    @rsps_lib.activate
    def test_returns_json_by_default(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.GET, _TEST_URL, json={"ok": True}, status=200)

        result = devops_api_get(_TEST_URL)

        assert result == {"ok": True}

    @rsps_lib.activate
    def test_returns_response_object_when_flagged(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.GET, _TEST_URL, json={"ok": True}, status=200)

        result = devops_api_get(_TEST_URL, return_response=True)

        assert hasattr(result, "status_code")
        assert result.status_code == 200


class TestDevopsApiPost:
    """Tests for devops_api_post HTTP wrapper."""

    @rsps_lib.activate
    def test_returns_json_by_default(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.POST, _TEST_URL, json={"created": True}, status=201)

        result = devops_api_post(_TEST_URL, payload={"name": "test"})

        assert result == {"created": True}

    @rsps_lib.activate
    def test_returns_response_object_when_flagged(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.POST, _TEST_URL, json={"created": True}, status=201)

        result = devops_api_post(_TEST_URL, payload={}, return_response=True)

        assert result.status_code == 201

    @rsps_lib.activate
    def test_merges_extra_headers(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.POST, _TEST_URL, json={}, status=200)

        devops_api_post(_TEST_URL, payload={}, extra_headers={"X-Extra": "yes"})

        assert rsps_lib.calls[0].request.headers.get("X-Extra") == "yes"


class TestDevopsApiPut:
    """Tests for devops_api_put HTTP wrapper."""

    @rsps_lib.activate
    def test_returns_json_by_default(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.PUT, _TEST_URL, json={"updated": True}, status=200)

        result = devops_api_put(_TEST_URL, payload={"x": 1})

        assert result == {"updated": True}

    @rsps_lib.activate
    def test_returns_response_object_when_flagged(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.PUT, _TEST_URL, json={}, status=200)

        result = devops_api_put(_TEST_URL, payload={}, return_response=True)

        assert result.status_code == 200

    @rsps_lib.activate
    def test_merges_extra_headers(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.PUT, _TEST_URL, json={}, status=200)

        devops_api_put(_TEST_URL, payload={}, extra_headers={"X-Put": "yes"})

        assert rsps_lib.calls[0].request.headers.get("X-Put") == "yes"


class TestDevopsApiPatch:
    """Tests for devops_api_patch HTTP wrapper."""

    @rsps_lib.activate
    def test_returns_json_by_default(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.PATCH, _TEST_URL, json={"patched": True}, status=200)

        result = devops_api_patch(_TEST_URL, payload=[{"op": "add", "path": "/fields/x", "value": "y"}])

        assert result == {"patched": True}

    @rsps_lib.activate
    def test_returns_response_object_when_flagged(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.PATCH, _TEST_URL, json={}, status=200)

        result = devops_api_patch(_TEST_URL, payload={}, return_response=True)

        assert result.status_code == 200

    @rsps_lib.activate
    def test_merges_extra_headers(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.PATCH, _TEST_URL, json={}, status=200)

        devops_api_patch(_TEST_URL, payload={}, extra_headers={"X-Patch": "yes"})

        assert rsps_lib.calls[0].request.headers.get("X-Patch") == "yes"


class TestDevopsApiDelete:
    """Tests for devops_api_delete HTTP wrapper."""

    @rsps_lib.activate
    def test_succeeds_on_204(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.DELETE, _TEST_URL, status=204)

        devops_api_delete(_TEST_URL)  # must not raise

        assert rsps_lib.calls[0].request.method == "DELETE"

    @rsps_lib.activate
    def test_raises_on_error_status(self, monkeypatch):
        import requests as req_lib

        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(rsps_lib.DELETE, _TEST_URL, status=404)

        with pytest.raises(req_lib.HTTPError):
            devops_api_delete(_TEST_URL)


class TestFetchWorkItem:
    """Tests for fetch_work_item() conditional field extraction."""

    @rsps_lib.activate
    def test_returns_id_and_fields_only_when_no_extras(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(
            rsps_lib.GET,
            _TEST_URL,
            json={"id": 42, "fields": {"System.Title": "Bug"}, "rev": 3},
            status=200,
        )

        result = fetch_work_item(_TEST_URL)

        assert result["id"] == 42
        assert result["fields"] == {"System.Title": "Bug"}
        assert "relations" not in result
        assert "_links" not in result

    @rsps_lib.activate
    def test_includes_relations_when_present(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(
            rsps_lib.GET,
            _TEST_URL,
            json={"id": 1, "fields": {}, "relations": [{"rel": "System.LinkTypes.Hierarchy-Forward"}]},
            status=200,
        )

        result = fetch_work_item(_TEST_URL)

        assert "relations" in result
        assert result["relations"][0]["rel"] == "System.LinkTypes.Hierarchy-Forward"

    @rsps_lib.activate
    def test_includes_links_when_present(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(
            rsps_lib.GET,
            _TEST_URL,
            json={"id": 1, "fields": {}, "_links": {"self": {"href": "https://example.com"}}},
            status=200,
        )

        result = fetch_work_item(_TEST_URL)

        assert "_links" in result


class TestDevopsApiGetBinaryStream:
    """Tests for devops_api_get_binary_stream()."""

    @rsps_lib.activate
    def test_returns_response_for_binary_content(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(
            rsps_lib.GET,
            _TEST_URL,
            body=b"\x89PNG\r\n",
            status=200,
            headers={"Content-Type": "image/png"},
            stream=True,
        )

        response = devops_api_get_binary_stream(_TEST_URL)

        assert response.status_code == 200

    @rsps_lib.activate
    def test_raises_for_html_content_type(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(
            rsps_lib.GET,
            _TEST_URL,
            body=b"<html>Unauthorized</html>",
            status=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

        with pytest.raises(ValueError, match="unexpected Content-Type"):
            devops_api_get_binary_stream(_TEST_URL)

    @rsps_lib.activate
    def test_raises_for_json_content_type(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(
            rsps_lib.GET,
            _TEST_URL,
            json={"message": "Unauthorized"},
            status=200,
            headers={"Content-Type": "application/json"},
        )

        with pytest.raises(ValueError, match="unexpected Content-Type"):
            devops_api_get_binary_stream(_TEST_URL)


class TestDevopsApiGetBinary:
    """Tests for devops_api_get_binary()."""

    @rsps_lib.activate
    def test_returns_bytes(self, monkeypatch):
        monkeypatch.setenv("DEVOPS_TOKEN", "tok")
        rsps_lib.add(
            rsps_lib.GET,
            _TEST_URL,
            body=b"binarydata",
            status=200,
            headers={"Content-Type": "application/octet-stream"},
        )

        result = devops_api_get_binary(_TEST_URL)

        assert isinstance(result, bytes)
        assert result == b"binarydata"
