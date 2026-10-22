"""Insights router – automated KPI / trend / anomaly generation."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import InsightsRequest, InsightsResponse
from app.services.anomaly_service import AnomalyService
from app.services.data_service import DataService

logger = logging.getLogger(__name__)

router = APIRouter()
data_service = DataService()
anomaly_service = AnomalyService()


@router.post("/", response_model=InsightsResponse)
async def generate_insights(request: Request, body: InsightsRequest) -> InsightsResponse:
    """Generate automated insights for a single dataset matching frontend expectations."""
    store: dict[str, dict[str, Any]] = request.app.state.datasets  # type: ignore[attr-defined]

    entry = store.get(body.dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    df: pd.DataFrame = entry["df"]

    # Filter out ID columns from numeric analysis
    all_numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in all_numeric if not (c.lower().endswith("_id") or c.lower() == "id")]
    if not numeric_cols:
        numeric_cols = all_numeric

    # ---- 1. KPIs (formatted as {name, value, description}) ----
    kpis: list[dict[str, Any]] = []

    # Total rows KPI
    kpis.append({
        "name": "Total Records",
        "value": len(df),
        "description": "Total rows analyzed in this dataset",
    })

    # Numeric metrics KPIs
    for col in numeric_cols[:4]:
        series = df[col].dropna()
        if series.empty:
            continue
        total_val = round(float(series.sum()), 2)
        mean_val = round(float(series.mean()), 2)
        clean_name = col.replace("_", " ").title()

        kpis.append({
            "name": f"Total {clean_name}",
            "value": total_val,
            "description": f"Sum across all records (avg: {mean_val})",
        })

    # ---- 2. Top Performers (formatted as {name, value, category}) ----
    top_performers: list[dict[str, Any]] = []
    date_cols = data_service.detect_date_columns(df)
    all_cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    # Filter out date columns from category grouping
    categorical_cols = [c for c in all_cat_cols if c not in date_cols]
    if not categorical_cols:
        categorical_cols = all_cat_cols

    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        # Choose revenue or primary metric
        primary_metric = numeric_cols[0]
        for col in numeric_cols:
            if any(k in col.lower() for k in ["revenue", "sales", "amount", "total"]):
                primary_metric = col
                break

        try:
            grouped = (
                df.groupby(cat_col, dropna=True)[primary_metric]
                .sum()
                .sort_values(ascending=False)
                .head(5)
            )
            for k, v in grouped.items():
                top_performers.append({
                    "name": str(k),
                    "value": round(float(v), 2),
                    "category": f"By {cat_col.replace('_', ' ').title()}",
                })
        except Exception as exc:
            logger.warning("Error calculating top performers: %s", exc)

    # ---- 3. Trends (formatted as {period, value, change}) ----
    trends: list[dict[str, Any]] = []
    date_cols = data_service.detect_date_columns(df)
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        primary_metric = numeric_cols[0]
        for col in numeric_cols:
            if any(k in col.lower() for k in ["revenue", "sales", "amount"]):
                primary_metric = col
                break

        try:
            ts = data_service.compute_time_series(df, date_col, primary_metric)
            val_col = ts.columns[-1]
            prev_val = None
            for _, row in ts.iterrows():
                curr_val = round(float(row[val_col]), 2)
                change = None
                if prev_val is not None and prev_val > 0:
                    change = round(((curr_val - prev_val) / prev_val) * 100, 1)
                trends.append({
                    "period": str(row[date_col]),
                    "value": curr_val,
                    "change": change,
                })
                prev_val = curr_val
        except Exception as exc:
            logger.warning("Error calculating trends: %s", exc)

    # ---- 4. Anomalies ----
    anomalies_raw = anomaly_service.detect_anomalies(df, columns=numeric_cols)
    anomalies_out = anomalies_raw[:10]

    # ---- 5. Suggested Questions ----
    suggestions: list[str] = []
    if numeric_cols:
        m = numeric_cols[0].replace("_", " ")
        suggestions.append(f"What is the total {m} across all records?")
    if categorical_cols and numeric_cols:
        c = categorical_cols[0].replace("_", " ")
        m = numeric_cols[0].replace("_", " ")
        suggestions.append(f"Which {c} generated the highest {m}?")
        if len(categorical_cols) > 1:
            c2 = categorical_cols[1].replace("_", " ")
            suggestions.append(f"Show {m} distribution by {c2}")
    if date_cols and numeric_cols:
        m = numeric_cols[0].replace("_", " ")
        suggestions.append(f"Show monthly trends for {m}")
    suggestions.append("Detect anomalies and outliers in the data")
    if numeric_cols:
        suggestions.append(f"Generate SQL to rank top 5 by {numeric_cols[0]}")

    return InsightsResponse(
        kpis=kpis,
        top_performers=top_performers,
        trends=trends,
        anomalies=anomalies_out,
        suggestions=suggestions,
    )
