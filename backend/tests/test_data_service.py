"""Unit tests for DataService."""

from __future__ import annotations

import io
import pandas as pd
import pytest

from app.services.data_service import DataService


@pytest.fixture
def data_service():
    return DataService()


def test_validate_csv_valid(data_service, sample_csv_bytes):
    df, warnings = data_service.validate_csv(sample_csv_bytes, "test.csv")
    assert len(df) == 50
    assert len(df.columns) == 10
    assert "revenue" in df.columns
    assert isinstance(warnings, list)


def test_validate_csv_empty(data_service):
    with pytest.raises(ValueError, match="empty"):
        data_service.validate_csv(b"", "empty.csv")


def test_validate_csv_malformed(data_service):
    malformed = b"col1,col2\nval1\nval1,val2,extra,extra2\n"
    # Parser should handle or raise gracefully
    try:
        df, _ = data_service.validate_csv(malformed, "bad.csv")
        assert len(df) > 0
    except ValueError:
        pass  # Also valid behavior for malformed CSV


def test_column_analysis(data_service, sample_df):
    analysis = data_service.get_column_analysis(sample_df)
    assert "revenue" in analysis
    assert analysis["revenue"]["type"] in ("numeric", "float")
    assert "region" in analysis
    assert analysis["region"]["type"] in ("categorical", "text")
    assert "missing" in analysis["revenue"]


def test_compute_aggregation(data_service, sample_df):
    # Total revenue by region
    agg = data_service.compute_aggregation(sample_df, "region", "revenue", "sum")
    assert "region" in agg.columns
    assert "sum_revenue" in agg.columns
    assert len(agg) == 4  # North, South, East, West

    north_rev = agg[agg["region"] == "North"]["sum_revenue"].values[0]
    assert north_rev == 7925.0


def test_compute_ranking(data_service, sample_df):
    top3 = data_service.compute_ranking(sample_df, "revenue", n=3, ascending=False)
    assert len(top3) == 3
    # Top record in sample dataset is order 1049 with 3000.0 revenue
    assert top3.iloc[0]["revenue"] == 3000.0


def test_filter_data(data_service, sample_df):
    filtered = data_service.filter_data(
        sample_df, [{"column": "region", "operator": "==", "value": "North"}]
    )
    assert all(filtered["region"] == "North")
    assert len(filtered) < len(sample_df)


def test_detect_date_columns(data_service, sample_df):
    date_cols = data_service.detect_date_columns(sample_df)
    assert "order_date" in date_cols


def test_compute_time_series(data_service, sample_df):
    ts = data_service.compute_time_series(sample_df, "order_date", "revenue")
    assert len(ts) == 12  # 12 months in 2024
    assert "order_date" in ts.columns
    # Jan 2024 total is 250 + 225 + 240 + 375 = 1090.0
    jan_val = ts[ts["order_date"] == "2024-01"].iloc[0]["total_revenue"]
    assert jan_val == 1090.0


def test_compute_correlation(data_service, sample_df):
    corr = data_service.compute_correlation(sample_df)
    assert not corr.empty
    assert "revenue" in corr.columns
    assert "quantity" in corr.columns
    # Revenue should positively correlate with quantity
    assert corr.loc["revenue", "quantity"] > 0
