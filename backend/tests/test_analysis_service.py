"""Unit tests for AnalysisService verifying accuracy against ground truth."""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from app.services.analysis_service import AnalysisService

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def service():
    return AnalysisService()


@pytest.fixture
def datasets_dict(sample_df):
    return {"dataset_1": {"df": sample_df, "filename": "sample_sales.csv"}}


def test_question_highest_revenue_region(service, datasets_dict):
    resp = service.analyze("Which region generated the highest revenue?", datasets_dict)
    assert resp.error is None
    assert resp.chart_config is not None
    # Ground truth: North has highest revenue (7,925.0)
    data = resp.chart_config.get("data", [])
    assert len(data) == 4
    top_entry = data[0]
    assert top_entry["region"] == "North"
    assert top_entry["sum_revenue"] == 7925.0


def test_question_monthly_trend(service, datasets_dict):
    resp = service.analyze("Show monthly sales trends", datasets_dict)
    assert resp.error is None
    assert resp.chart_config is not None
    assert resp.chart_config["type"] == "line"
    data = resp.chart_config.get("data", [])
    assert len(data) == 12  # All 12 months present


def test_question_top_products(service, datasets_dict):
    resp = service.analyze("What are the top 5 products by revenue?", datasets_dict)
    assert resp.error is None
    data = resp.chart_config.get("data", [])
    assert len(data) == 5
    # Top product is Widget A
    assert data[0]["product"] == "Widget A"
    assert data[0]["sum_revenue"] == 6875.0


def test_question_anomalies(service, datasets_dict):
    resp = service.analyze("Detect anomalies in the dataset", datasets_dict)
    assert resp.error is None
    assert resp.anomalies is not None
    assert len(resp.anomalies) > 0


def test_question_underperforming(service, datasets_dict):
    resp = service.analyze("Which products are underperforming?", datasets_dict)
    assert resp.error is None
    assert resp.chart_config is not None
    data = resp.chart_config.get("data", [])
    assert len(data) > 0
    # Underperforming product sorted ascending: Gadget Z has lowest revenue (1040.0)
    assert data[0]["product"] == "Gadget Z"
    assert data[0]["sum_revenue"] == 1040.0


def test_multi_file_analysis(service, sample_df):
    targets_df = pd.read_csv(DATA_DIR / "sample_targets.csv")
    multi_dict = {
        "1": {"df": sample_df, "filename": "sample_sales.csv"},
        "2": {"df": targets_df, "filename": "sample_targets.csv"},
    }
    resp = service.analyze("Compare revenue with target revenue by region", multi_dict)
    assert resp.error is None
    assert resp.chart_config is not None
    data = resp.chart_config.get("data", [])
    assert len(data) >= 4


def test_generated_sql_included(service, datasets_dict):
    resp = service.analyze("What are the top 5 products by revenue?", datasets_dict)
    assert resp.sql_code is not None
    assert "SELECT" in resp.sql_code
    assert resp.pandas_code is not None
    assert "df" in resp.pandas_code
def test_conversation_context_followup(service, datasets_dict):
    history = [{"role": "user", "content": "What are the top 5 products by revenue?"}]
    resp = service.analyze("Which one performed worst?", datasets_dict, conversation_history=history)
    assert resp.error is None
    assert resp.chart_config is not None
    data = resp.chart_config.get("data", [])
    assert len(data) == 1
    assert data[0]["product"] == "Gadget Z"
    assert data[0]["sum_revenue"] == 1040.0
