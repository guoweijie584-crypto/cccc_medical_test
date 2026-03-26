import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.memory.palace_client import MemoryPalaceClientSync


def test_normalize_legacy_medical_uri_maps_to_core_with_prefix():
    client = MemoryPalaceClientSync()
    domain, path = client._normalize_uri("medical://patient/PAT001/profile")
    assert domain == "core"
    assert path == "medical/patient_profiles/PAT001"


def test_normalize_legacy_medical_memory_uri_flattens_to_stable_leaf():
    client = MemoryPalaceClientSync()
    domain, path = client._normalize_uri("medical://patient/PAT001/glucose/20260325120000")
    assert domain == "core"
    assert path == "medical/patient_memories/PAT001__glucose__20260325120000"


def test_build_search_filters_strips_patient_token_and_adds_path_prefix():
    client = MemoryPalaceClientSync()
    query, filters = client._build_search_filters(
        "glucose trend patient:PAT001",
        "medical",
    )
    assert query == "glucose trend PAT001"
    assert filters["domain"] == "core"
    assert filters["path_prefix"] == "medical/patient_memories"


def test_create_ensures_parent_chain_before_leaf(monkeypatch):
    client = MemoryPalaceClientSync()
    calls = []
    existing_paths = set()

    async def fake_request(method, path, json_data=None, params=None):
        calls.append((method, path, json_data, params))
        if method == "GET" and path == "/browse/node":
            wanted = str((params or {}).get("path") or "")
            if wanted in existing_paths:
                return {"node": {"path": wanted, "domain": "core", "content": ""}}
            return {"error": "not found"}
        if method == "POST" and path == "/browse/node":
            parent = str((json_data or {}).get("parent_path") or "")
            title = str((json_data or {}).get("title") or "")
            current = f"{parent}/{title}" if parent else title
            existing_paths.add(current)
            return {"success": True, "created": True}
        raise AssertionError(f"unexpected call: {method} {path}")

    monkeypatch.setattr(client, "_request", fake_request)
    result = client.create(
        content='{"patient_id":"PAT001"}',
        uri="medical://patient/PAT001/profile",
    )

    assert result["uri"] == "core://medical/patient_profiles/PAT001"
    post_bodies = [item[2] for item in calls if item[0] == "POST"]
    assert post_bodies == [
        {"parent_path": "", "title": "medical", "content": client._namespace_marker("medical"), "domain": "core"},
        {
            "parent_path": "medical",
            "title": "patient_profiles",
            "content": client._namespace_marker("medical/patient_profiles"),
            "domain": "core",
        },
        {
            "parent_path": "medical/patient_profiles",
            "title": "PAT001",
            "content": '{"patient_id":"PAT001"}',
            "domain": "core",
        },
    ]


def test_search_normalizes_snippet_to_content(monkeypatch):
    client = MemoryPalaceClientSync()

    async def fake_request(method, path, json_data=None, params=None):
        assert method == "POST"
        assert path == "/maintenance/observability/search"
        return {
            "results": [
                {
                    "uri": "core://medical/patient_memories/PAT001__glucose__1",
                    "snippet": '{"patient_id":"PAT001","category":"glucose"}',
                    "scores": {"final": 0.9},
                }
            ]
        }

    monkeypatch.setattr(client, "_request", fake_request)
    monkeypatch.setattr(client, "read", lambda uri: None)

    results = client.search("PAT001", domain="medical", max_results=5, mode="keyword")
    assert results[0]["content"] == '{"patient_id":"PAT001","category":"glucose"}'
    assert results[0]["score"] == 0.9
