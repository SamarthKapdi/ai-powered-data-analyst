"""Integration tests for FastAPI endpoints."""

from __future__ import annotations

import io
import pytest


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}


def test_upload_csv(client, sample_csv_bytes):
    response = client.post(
        "/api/upload",
        files={"files": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["filename"] == "sales.csv"
    assert data[0]["rows"] == 50
    assert data[0]["columns"] == 10


def test_dataset_list_and_preview(client, sample_csv_bytes):
    # Upload first
    up_resp = client.post(
        "/api/upload",
        files={"files": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = up_resp.json()[0]["id"]

    # List datasets
    list_resp = client.get("/api/datasets")
    assert list_resp.status_code == 200
    assert any(d["id"] == dataset_id for d in list_resp.json())

    # Data preview
    prev_resp = client.get(f"/api/upload/{dataset_id}/preview")
    assert prev_resp.status_code == 200
    preview = prev_resp.json()
    assert len(preview["preview_data"]) == 50
    assert "revenue" in preview["columns"]


def test_analyze_endpoint(client, sample_csv_bytes):
    up_resp = client.post(
        "/api/upload",
        files={"files": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = up_resp.json()[0]["id"]

    analyze_resp = client.post(
        "/api/analyze",
        json={
            "question": "Which region generated the highest revenue?",
            "dataset_ids": [dataset_id],
            "conversation_history": [],
        },
    )
    assert analyze_resp.status_code == 200
    result = analyze_resp.json()
    assert "answer" in result
    assert result["chart_config"] is not None
    assert result["chart_config"]["type"] in ("pie", "bar")


def test_insights_endpoint(client, sample_csv_bytes):
    up_resp = client.post(
        "/api/upload",
        files={"files": ("sales.csv", sample_csv_bytes, "text/csv")},
    )
    dataset_id = up_resp.json()[0]["id"]

    insights_resp = client.post(
        "/api/insights",
        json={"dataset_id": dataset_id},
    )
    assert insights_resp.status_code == 200
    data = insights_resp.json()
    assert len(data["kpis"]) > 0
    assert len(data["suggestions"]) > 0
