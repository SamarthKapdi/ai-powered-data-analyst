"""Unit tests for AnomalyService."""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.anomaly_service import AnomalyService


@pytest.fixture
def anomaly_service():
    return AnomalyService()


def test_detect_anomalies_sample_data(anomaly_service, sample_df):
    anomalies = anomaly_service.detect_anomalies(sample_df)
    assert len(anomalies) > 0

    # Ensure required structure
    for a in anomalies:
        assert "row_index" in a
        assert "column" in a
        assert "value" in a
        assert "expected_range" in a
        assert "method" in a
        assert "reason" in a
        assert "severity" in a

    # Row 48 has quantity=200 and revenue=3000 (extreme outliers)
    flagged_rows = [a["row_index"] for a in anomalies]
    assert 48 in flagged_rows


def test_detect_anomalies_specific_column(anomaly_service, sample_df):
    anomalies = anomaly_service.detect_anomalies(sample_df, columns=["quantity"])
    assert len(anomalies) > 0
    assert all(a["column"] == "quantity" for a in anomalies)


def test_explain_anomaly(anomaly_service):
    anomaly = {
        "row_index": 48,
        "column": "revenue",
        "value": 3000.0,
        "expected_range": "[-210.0, 900.0]",
        "method": "IQR",
        "reason": "Value 3000.0 is outside expected IQR range",
        "severity": "high",
    }
    explanation = anomaly_service.explain_anomaly(anomaly)
    assert "revenue" in explanation
    assert "3000.0" in explanation
    assert "IQR" in explanation


def test_anomaly_no_data(anomaly_service):
    empty_df = pd.DataFrame({"a": []})
    assert anomaly_service.detect_anomalies(empty_df) == []
