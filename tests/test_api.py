"""Integration tests for the FastAPI interface layer.

These tests load the real FAISS index — run `python scripts/build_index.py` first.
Mark: pytest -m integration  (or just pytest tests/test_api.py if index is present)
"""

import pytest
from fastapi.testclient import TestClient

from interface.api import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def load_index():
    """Ensure the index is loaded before any test in this module runs."""
    import index.engine as engine
    try:
        engine.load()
    except FileNotFoundError:
        pytest.skip("FAISS index not built — run `python scripts/build_index.py` first")


@pytest.mark.integration
class TestHealth:
    def test_health_returns_200(self):
        res = client.get("/api/health")
        assert res.status_code == 200

    def test_health_fields(self):
        res = client.get("/api/health")
        data = res.json()
        assert data["status"] == "ok"
        assert data["phase"] == 8
        assert data["index_size"] == 48647
        assert data["model"] == "all-MiniLM-L6-v2"


@pytest.mark.integration
class TestQuery:
    def test_petrichor_is_rank_one(self):
        res = client.post("/api/query", json={"text": "the smell of rain on dry earth"})
        assert res.status_code == 200
        data = res.json()
        assert data["groups"][0]["results"][0]["word"] == "petrichor"

    def test_response_shape(self):
        res = client.post("/api/query", json={"text": "feeling of joy"})
        assert res.status_code == 200
        data = res.json()
        assert "mode" in data
        assert "groups" in data
        assert isinstance(data["groups"], list)
        group = data["groups"][0]
        assert "label" in group
        assert "results" in group
        result = group["results"][0]
        for field in ("word", "pos", "definition", "score", "is_interpretation"):
            assert field in result

    def test_empty_body_returns_422(self):
        res = client.post("/api/query", json={})
        assert res.status_code == 422

    def test_lucky_returns_one_result_per_group(self):
        res = client.post("/api/query", json={"text": "a feeling of sadness", "lucky": True})
        assert res.status_code == 200
        data = res.json()
        for group in data["groups"]:
            assert len(group["results"]) <= 1

    def test_pos_filter_returns_only_nouns(self):
        res = client.post("/api/query", json={
            "text": "sadness",
            "filters": {"pos": "n"},
        })
        assert res.status_code == 200
        data = res.json()
        for group in data["groups"]:
            for result in group["results"]:
                assert result["pos"] == "n"

    def test_no_results_returns_valid_structure(self):
        # Extremely restrictive filters may yield empty results — should not crash
        res = client.post("/api/query", json={
            "text": "happiness",
            "filters": {"pos": "r", "starts_with": "zz", "max_length": 2},
        })
        assert res.status_code == 200
        data = res.json()
        assert "groups" in data
