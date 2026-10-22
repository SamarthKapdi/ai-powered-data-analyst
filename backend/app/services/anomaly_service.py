"""Anomaly detection service – IQR, Z-score, and time-series methods."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

logger = logging.getLogger(__name__)


class AnomalyService:
    """Detects statistical anomalies in tabular data."""

    # ------------------------------------------------------------------
    # General anomaly detection
    # ------------------------------------------------------------------
    @staticmethod
    def detect_anomalies(
        df: pd.DataFrame,
        columns: list[str] | None = None,
        method: str = "auto",
    ) -> list[dict[str, Any]]:
        """Detect anomalies in numeric columns.

        Parameters
        ----------
        df : DataFrame
        columns : subset of columns to check (None = all numeric)
        method : "iqr", "zscore", or "auto" (choose per-column)

        Returns
        -------
        List of anomaly dicts.
        """
        anomalies: list[dict[str, Any]] = []

        if columns is None:
            # Exclude identifier columns (e.g. order_id, customer_id) from anomaly detection
            columns = [
                c for c in df.select_dtypes(include=[np.number]).columns
                if not (c.lower().endswith("_id") or c.lower() == "id")
            ]
            if not columns:
                columns = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in columns:
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue

            series = df[col].dropna()
            if len(series) < 5:
                continue

            # Decide method
            chosen = method
            if chosen == "auto":
                skewness = float(series.skew())
                chosen = "iqr" if abs(skewness) > 1.0 else "zscore"

            if chosen == "iqr":
                q1 = float(series.quantile(0.25))
                q3 = float(series.quantile(0.75))
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr

                mask = (df[col] < lower) | (df[col] > upper)
                for idx in df.index[mask]:
                    val = float(df.at[idx, col])
                    severity = "high" if (val < q1 - 3 * iqr or val > q3 + 3 * iqr) else "medium"
                    anomalies.append(
                        {
                            "row_index": int(idx),
                            "column": col,
                            "value": val,
                            "expected_range": f"[{round(lower, 2)}, {round(upper, 2)}]",
                            "method": "IQR",
                            "reason": f"Value {val} is outside expected IQR range [{round(lower, 2)}, {round(upper, 2)}]",
                            "severity": severity,
                        }
                    )

            elif chosen == "zscore":
                mean = float(series.mean())
                std = float(series.std())
                if std == 0:
                    continue

                z_scores = (df[col] - mean) / std
                mask = z_scores.abs() > 3
                for idx in df.index[mask]:
                    val = float(df.at[idx, col])
                    z = float(z_scores.at[idx])
                    severity = "high" if abs(z) > 4 else "medium"
                    exp_lower = round(mean - 3 * std, 2)
                    exp_upper = round(mean + 3 * std, 2)
                    anomalies.append(
                        {
                            "row_index": int(idx),
                            "column": col,
                            "value": val,
                            "expected_range": f"[{exp_lower}, {exp_upper}]",
                            "method": "Z-Score",
                            "reason": f"Z-score of {round(z, 2)} exceeds ±3 threshold (expected [{exp_lower}, {exp_upper}])",
                            "severity": severity,
                        }
                    )

        return anomalies

    # ------------------------------------------------------------------
    # Time-series anomaly detection
    # ------------------------------------------------------------------
    @staticmethod
    def detect_time_series_anomalies(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        window: int = 7,
    ) -> list[dict[str, Any]]:
        """Flag data points beyond 2 std from a rolling mean."""
        anomalies: list[dict[str, Any]] = []

        tmp = df[[date_col, value_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp.dropna(subset=[date_col, value_col])
        tmp = tmp.sort_values(date_col).reset_index(drop=True)

        if len(tmp) < window + 1:
            return anomalies

        rolling_mean = tmp[value_col].rolling(window=window, center=False).mean()
        rolling_std = tmp[value_col].rolling(window=window, center=False).std()

        for i in range(window, len(tmp)):
            val = float(tmp.at[i, value_col])
            rm = float(rolling_mean.iloc[i])
            rs = float(rolling_std.iloc[i])

            if rs == 0:
                continue

            deviation = abs(val - rm) / rs
            if deviation > 2:
                severity = "high" if deviation > 3 else "medium"
                anomalies.append(
                    {
                        "row_index": int(i),
                        "date": str(tmp.at[i, date_col]),
                        "column": value_col,
                        "value": val,
                        "rolling_mean": round(rm, 4),
                        "rolling_std": round(rs, 4),
                        "deviation": round(deviation, 2),
                        "method": "Rolling Z-Score",
                        "reason": (
                            f"Value {val} deviates {round(deviation, 1)}σ from the "
                            f"{window}-period rolling mean ({round(rm, 2)})"
                        ),
                        "severity": severity,
                    }
                )

        return anomalies

    # ------------------------------------------------------------------
    # Human-readable explanation
    # ------------------------------------------------------------------
    @staticmethod
    def explain_anomaly(anomaly: dict[str, Any]) -> str:
        """Generate a human-readable explanation for a single anomaly dict."""
        col = anomaly.get("column", "unknown")
        val = anomaly.get("value", "?")
        method = anomaly.get("method", "unknown")
        severity = anomaly.get("severity", "unknown")
        reason = anomaly.get("reason", "")

        expected = anomaly.get("expected_range", "")
        if isinstance(expected, dict):
            range_str = f"[{expected.get('lower', '?')}, {expected.get('upper', '?')}]"
        else:
            range_str = str(expected)

        date_str = anomaly.get("date", "")
        date_part = f" on {date_str}" if date_str else f" at row {anomaly.get('row_index', '?')}"

        return (
            f"⚠️ {severity.upper()} severity anomaly detected in '{col}'{date_part}: "
            f"the value {val} is outside the expected range {range_str}. "
            f"Detection method: {method}. {reason}."
        )
