"""Shared pytest fixtures for all test modules."""

import pytest

# A stable base URL used across all tests that need to call the DevOps API.
TEST_BASE_URL = "https://devops.example.com/org/project"

# All environment variables that the shared module reads.
_DEVOPS_ENV_VARS = (
    "DEVOPS_API_URL",
    "DEVOPS_TOKEN",
    "DEVOPS_PAT",
    "DEVOPS_USERNAME",
    "DEVOPS_PASSWORD",
)


@pytest.fixture(autouse=True)
def clean_devops_env(monkeypatch):
    """Remove every DEVOPS_* env var before each test so tests are isolated."""
    for var in _DEVOPS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def devops_url(monkeypatch):
    """
    Patch the module-level ``devops_api_url`` name in every module that
    imports it so that URL construction in tool functions uses a test value.
    """
    monkeypatch.setattr("mcp_devops.shared.devops_api_url", TEST_BASE_URL)
    monkeypatch.setattr("mcp_devops.tools.repository_tools.devops_api_url", TEST_BASE_URL)
    return TEST_BASE_URL
