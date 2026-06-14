"""Mock payloads for work item tool tests."""

BASE_URL = "https://devops.example.com/org/project"

WORK_ITEM_RESPONSE = {
    "id": 42,
    "fields": {
        "System.WorkItemType": "User Story",
        "System.State": "Active",
        "System.Reason": "Approved",
        "System.Title": "My &amp; Work Item",
        "System.AreaPath": "MyProject\\Area",
        "System.IterationPath": "MyProject\\Sprint 1",
        "System.AssignedTo": {"displayName": "Alice", "uniqueName": "alice@example.com"},
        "System.CreatedBy": {"displayName": "Bob", "uniqueName": "bob@example.com"},
        "System.ChangedBy": {"displayName": "Alice", "uniqueName": "alice@example.com"},
        "System.CreatedDate": "2024-01-10T09:00:00Z",
        "System.ChangedDate": "2024-01-15T12:00:00Z",
        "System.CommentCount": 3,
        "System.BoardColumn": "In Progress",
        "System.Description": "<p>Some &amp; description</p>",
        "Microsoft.VSTS.Common.AcceptanceCriteria": "<p>Criteria</p>",
        "System.Tags": "tag1; tag2",
        "System.Parent": 10,
        "Microsoft.VSTS.Common.Severity": "2 - High",
        "Microsoft.VSTS.Scheduling.Effort": 5,
        "Microsoft.VSTS.TCM.SystemInfo": None,
    },
    "relations": [
        {
            "rel": "AttachedFile",
            "url": f"{BASE_URL}/_apis/wit/attachments/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "attributes": {
                "name": "screenshot.png",
                "resourceSize": 12345,
                "resourceModifiedDate": "2024-01-12T10:00:00Z",
            },
        },
        {
            "rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": f"{BASE_URL}/_apis/wit/workItems/10",
            "attributes": {"name": "Parent"},
        },
        {
            "rel": "ArtifactLink",
            "url": f"vstfs:///Git/PullRequestId/proj-id%2Frepo-id%2F99",
            "attributes": {"name": "Pull Request"},
        },
    ],
}

BUG_WORK_ITEM_RESPONSE = {
    "id": 43,
    "fields": {
        "System.WorkItemType": "Bug",
        "System.State": "Active",
        "System.Reason": "New",
        "System.Title": "A Bug",
        "System.AreaPath": "MyProject",
        "System.IterationPath": "MyProject",
        "System.AssignedTo": None,
        "System.CreatedBy": None,
        "System.ChangedBy": None,
        "System.CreatedDate": None,
        "System.ChangedDate": None,
        "System.CommentCount": 0,
        "System.BoardColumn": None,
        "Microsoft.VSTS.TCM.ReproSteps": "<p>Steps to reproduce</p>",
        "Microsoft.VSTS.Common.AcceptanceCriteria": None,
        "System.Tags": None,
        "System.Parent": None,
        "Microsoft.VSTS.Common.Severity": "1 - Critical",
        "Microsoft.VSTS.Scheduling.Effort": None,
        "Microsoft.VSTS.TCM.SystemInfo": "Windows 11",
    },
    "relations": None,
}

WORK_ITEM_WITH_INLINE_IMAGE_RESPONSE = {
    "id": 44,
    "fields": {
        "System.WorkItemType": "User Story",
        "System.State": "Active",
        "System.Reason": None,
        "System.Title": "With inline image",
        "System.AreaPath": "MyProject",
        "System.IterationPath": "MyProject",
        "System.AssignedTo": None,
        "System.CreatedBy": None,
        "System.ChangedBy": None,
        "System.CreatedDate": None,
        "System.ChangedDate": None,
        "System.CommentCount": 0,
        "System.BoardColumn": None,
        "System.Description": (
            f'<img src="{BASE_URL}/_apis/wit/attachments/11111111-2222-3333-4444-555555555555?fileName=diagram.png" />'
        ),
        "Microsoft.VSTS.Common.AcceptanceCriteria": None,
        "System.Tags": None,
        "System.Parent": None,
        "Microsoft.VSTS.Common.Severity": None,
        "Microsoft.VSTS.Scheduling.Effort": None,
        "Microsoft.VSTS.TCM.SystemInfo": None,
    },
    "relations": [],
}

WORK_ITEM_WITH_COMMIT_LINK_RESPONSE = {
    "id": 45,
    "fields": {
        "System.WorkItemType": "Task",
        "System.State": "Done",
        "System.Reason": None,
        "System.Title": "Task with commit",
        "System.AreaPath": "MyProject",
        "System.IterationPath": "MyProject",
        "System.AssignedTo": None,
        "System.CreatedBy": None,
        "System.ChangedBy": None,
        "System.CreatedDate": None,
        "System.ChangedDate": None,
        "System.CommentCount": 0,
        "System.BoardColumn": None,
        "System.Description": None,
        "Microsoft.VSTS.Common.AcceptanceCriteria": None,
        "System.Tags": None,
        "System.Parent": None,
        "Microsoft.VSTS.Common.Severity": None,
        "Microsoft.VSTS.Scheduling.Effort": None,
        "Microsoft.VSTS.TCM.SystemInfo": None,
    },
    "relations": [
        {
            "rel": "ArtifactLink",
            "url": "vstfs:///Git/Commit/proj-id%2Frepo-id%2Fabcdef1234567890",
            "attributes": {"name": "Fixed in Commit"},
        }
    ],
}

WORK_ITEM_TYPE_RESPONSE = {
    "name": "Bug",
    "referenceName": "Microsoft.VSTS.WorkItemTypes.Bug",
    "description": "Describes a divergence...",
}

ATTACHMENT_BINARY = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

WIQL_RESPONSE = {
    "queryType": "flat",
    "asOf": "2024-01-15T12:00:00Z",
    "columns": [
        {"referenceName": "System.Id"},
        {"referenceName": "System.Title"},
    ],
    "workItems": [
        {"id": 1, "url": f"{BASE_URL}/_apis/wit/workItems/1"},
        {"id": 2, "url": f"{BASE_URL}/_apis/wit/workItems/2"},
    ],
}

WIQL_TREE_RESPONSE = {
    "queryType": "tree",
    "asOf": "2024-01-15T12:00:00Z",
    "workItemRelations": [{"target": {"id": 1}}],
}

WIQL_EMPTY_RESPONSE = {
    "queryType": "flat",
    "asOf": "2024-01-15T12:00:00Z",
    "columns": [{"referenceName": "System.Id"}],
    "workItems": [],
}

BATCH_RESPONSE = {
    "value": [
        {"id": 1, "fields": {"System.Id": 1, "System.Title": "Item 1"}},
        {"id": 2, "fields": {"System.Id": 2, "System.Title": "Item 2"}},
    ]
}

CREATE_WORK_ITEM_RESPONSE = {
    "id": 100,
    "fields": {"System.Title": "New Item", "System.WorkItemType": "Task"},
}

UPDATE_WORK_ITEM_RESPONSE = {
    "id": 42,
    "fields": {"System.Title": "Updated Title"},
}

PATCH_RESPONSE = {
    "id": 42,
    "fields": {"System.Title": "Patched"},
}

WORK_ITEM_WITH_RELATIONS_RESPONSE = {
    "id": 42,
    "relations": [
        {
            "rel": "System.LinkTypes.Related",
            "url": f"{BASE_URL}/_apis/wit/workItems/99",
            "attributes": {"name": "Related"},
        },
        {
            "rel": "System.LinkTypes.Related",
            "url": f"{BASE_URL}/_apis/wit/workItems/100",
            "attributes": {"name": "Related"},
        },
    ],
}

WORK_ITEM_WITH_ARTIFACT_RELATIONS_RESPONSE = {
    "id": 42,
    "relations": [
        {
            "rel": "ArtifactLink",
            "url": "vstfs:///Git/PullRequestId/proj%2Frepo%2F7",
            "attributes": {"name": "Pull Request"},
        }
    ],
}

COMMENTS_RESPONSE = {
    "comments": [
        {"id": 1, "text": "First comment"},
        {"id": 2, "text": "Second comment"},
    ],
    "count": 2,
    "totalCount": 2,
}

ADD_COMMENT_RESPONSE = {
    "id": 5,
    "text": "New comment",
    "workItemId": 42,
}

UPDATE_COMMENT_RESPONSE = {
    "id": 5,
    "text": "Updated comment",
    "workItemId": 42,
}
