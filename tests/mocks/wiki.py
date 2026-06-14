"""Mock payloads for wiki tool tests."""

WIKI_PAGE_RESPONSE = {
    "id": 12,
    "path": "/MyPage",
    "order": 1,
    "isParentPage": False,
    "url": "https://devops.example.com/MyOrg/MyProject/_apis/wiki/wikis/MyWiki.wiki/pages/12",
    "remoteUrl": "https://devops.example.com/MyOrg/MyProject/_wiki/wikis/MyWiki.wiki/12/MyPage",
}

WIKI_PAGE_WITH_CONTENT_RESPONSE = {
    **WIKI_PAGE_RESPONSE,
    "content": "# My Page\n\nHello World",
}

WIKI_PUT_RESPONSE = {
    "id": 20,
    "path": "/Root/NewPage",
    "order": 0,
}

WIKI_PATCH_RESPONSE = {
    "id": 12,
    "path": "/MyPage",
    "order": 1,
}

WIKI_INFO_PROJECT_RESPONSE = {
    "id": "wiki-id-123",
    "type": "projectWiki",
    "name": "MyWiki.wiki",
    "versions": [{"version": "main"}],
}

WIKI_INFO_CODE_RESPONSE = {
    "id": "wiki-id-456",
    "type": "codeWiki",
    "name": "MyWiki.wiki",
    "versions": [{"version": "main"}],
}
