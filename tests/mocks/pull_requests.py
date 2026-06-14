"""Static mock payloads mirroring real Azure DevOps pull request API responses."""

PULL_REQUEST_RESPONSE = {
    "pullRequestId": 42,
    "status": "active",
    "creationDate": "2024-01-15T10:00:00Z",
    "title": "Add new feature",
    "description": "This PR adds a new feature.",
    "sourceRefName": "refs/heads/feature/my-feature",
    "targetRefName": "refs/heads/main",
    "isDraft": False,
    "lastMergeSourceCommit": {"commitId": "a" * 40},
    "lastMergeTargetCommit": {"commitId": "b" * 40},
    "_links": {
        "workItems": {
            "href": "https://devops.example.com/org/project/_apis/git/repositories/MyRepo/pullRequests/42/workitems"
        }
    },
}

PULL_REQUEST_NO_WORKITEMS_RESPONSE = {
    "pullRequestId": 99,
    "status": "completed",
    "creationDate": "2024-02-01T09:00:00Z",
    "title": "Fix bug",
    "description": None,
    "sourceRefName": "refs/heads/bugfix/fix-crash",
    "targetRefName": "refs/heads/main",
    "isDraft": False,
    "lastMergeSourceCommit": {"commitId": "c" * 40},
    "lastMergeTargetCommit": {"commitId": "d" * 40},
    "_links": {},
}

WORK_ITEMS_LIST_RESPONSE = {
    "value": [
        {"url": "https://devops.example.com/org/project/_apis/wit/workItems/101"}
    ]
}

WORK_ITEM_RESPONSE = {
    "id": 101,
    "fields": {"System.Title": "My Work Item", "System.WorkItemType": "Task"},
}

THREADS_RESPONSE = {
    "value": [
        {
            "id": 10,
            "publishedDate": "2024-01-16T10:00:00Z",
            "lastUpdatedDate": "2024-01-16T11:00:00Z",
            "isDeleted": False,
            "pullRequestThreadContext": None,
            "status": "active",
            "threadContext": {
                "filePath": "/src/foo.cs",
                "rightFileStart": {"line": 42, "offset": 1},
                "rightFileEnd": {"line": 42, "offset": 1},
            },
            "comments": [
                {
                    "id": 1,
                    "parentCommentId": 0,
                    "commentType": "text",
                    "isDeleted": False,
                    "author": {"displayName": "Alice"},
                    "content": "Please fix this.",
                    "publishedDate": "2024-01-16T10:00:00Z",
                    "lastUpdatedDate": "2024-01-16T10:00:00Z",
                    "lastContentUpdatedDate": "2024-01-16T10:00:00Z",
                }
            ],
        },
        # Thread with no text comments — should be excluded
        {
            "id": 11,
            "publishedDate": "2024-01-16T12:00:00Z",
            "lastUpdatedDate": "2024-01-16T12:00:00Z",
            "isDeleted": False,
            "pullRequestThreadContext": None,
            "comments": [
                {
                    "id": 2,
                    "commentType": "system",
                    "isDeleted": False,
                    "author": {"displayName": "System"},
                    "content": "PR created",
                }
            ],
        },
        # Deleted thread — should be excluded
        {
            "id": 12,
            "publishedDate": "2024-01-16T13:00:00Z",
            "lastUpdatedDate": "2024-01-16T13:00:00Z",
            "isDeleted": True,
            "pullRequestThreadContext": None,
            "comments": [],
        },
    ]
}

SINGLE_THREAD_RESPONSE = {
    "id": 10,
    "publishedDate": "2024-01-16T10:00:00Z",
    "lastUpdatedDate": "2024-01-16T11:00:00Z",
    "status": "active",
    "comments": [
        {
            "id": 1,
            "parentCommentId": 0,
            "commentType": "text",
            "isDeleted": False,
            "author": {"displayName": "Alice"},
            "content": "Please fix this.",
            "publishedDate": "2024-01-16T10:00:00Z",
            "lastUpdatedDate": "2024-01-16T10:00:00Z",
            "lastContentUpdatedDate": "2024-01-16T10:00:00Z",
        },
        # Deleted comment — should be excluded
        {
            "id": 2,
            "parentCommentId": 1,
            "commentType": "text",
            "isDeleted": True,
            "author": {"displayName": "Bob"},
            "content": "Deleted reply",
        },
    ],
}

CREATE_THREAD_RESPONSE = {
    "id": 20,
    "comments": [
        {"id": 1, "parentCommentId": 0}
    ],
}

REPLY_COMMENT_RESPONSE = {
    "id": 3,
    "parentCommentId": 1,
}

UPDATE_THREAD_RESPONSE = {
    "id": 10,
    "status": "fixed",
}

UPDATE_COMMENT_RESPONSE = {
    "id": 1,
    "parentCommentId": 0,
}
