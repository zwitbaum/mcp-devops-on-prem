"""Static mock payloads that mirror real Azure DevOps REST API responses.

These are plain dicts — no logic, no dependencies — so they can be
imported by any test without side effects.
"""

REPOSITORIES_RESPONSE = {
    "value": [
        {
            "id": "aaaa-1111",
            "name": "MyRepo",
            "defaultBranch": "refs/heads/main",
            "project": {"id": "proj-1", "name": "MyProject"},
            "remoteUrl": "https://devops.example.com/org/project/_git/MyRepo",
        },
        {
            "id": "bbbb-2222",
            "name": "AnotherRepo",
            "defaultBranch": "refs/heads/develop",
            "project": {"id": "proj-1", "name": "MyProject"},
            "remoteUrl": "https://devops.example.com/org/project/_git/AnotherRepo",
        },
    ],
    "count": 2,
}

REPOSITORIES_ERROR_RESPONSE = {
    "message": "TF400813: Resource not available for anonymous access.",
    "typeKey": "UnauthorizedRequestException",
    "errorCode": 0,
    "eventId": 3000,
}
