"""Data processing service – CSV parsing, column analysis, aggregation, filtering."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataService:
    """Stateless helper for dataframe operations."""

    # ------------------------------------------------------------------
    # CSV validation / parsing
    # ------------------------------------------------------------------
    @staticmethod
    def validate_csv(file_content: bytes, filename: str) -> tuple[pd.DataFrame, list[str]]:
        """Parse raw bytes into a DataFrame. Returns (df, warnings)."""
        warnings: list[str] = []
        from io import BytesIO

        encodings = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]
        df: pd.DataFrame | None = None

        for enc in encodings:
            try:
                df = pd.read_csv(BytesIO(file_content), encoding=enc)
                if enc != "utf-8":
                    warnings.append(f"File decoded using {enc} encoding (not UTF-8).")
                break
            except UnicodeDecodeError:
                continue
            except pd.errors.EmptyDataError:
                raise ValueError(f"The file '{filename}' is empty or contains no parseable data.")
            except pd.errors.ParserError as exc:
                raise ValueError(f"CSV parse error in '{filename}': {exc}")

        if df is None:
            raise ValueError(
                f"Unable to decode '{filename}' with any supported encoding."
            )

        if df.empty:
            warnings.append("The parsed CSV has zero rows.")

        # Strip whitespace from column names
        df.columns = [str(c).strip() for c in df.columns]

        return df, warnings

    # ------------------------------------------------------------------
    # Column analysis
    # ------------------------------------------------------------------
    @staticmethod
    def get_column_analysis(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        """For each column return inferred type and basic stats."""
        analysis: dict[str, dict[str, Any]] = {}

        for col in df.columns:
            info: dict[str, Any] = {}
            series = df[col]

            # Infer semantic type
            if pd.api.types.is_numeric_dtype(series):
                info["type"] = "numeric"
                info["mean"] = float(series.mean()) if not series.empty else None
                info["median"] = float(series.median()) if not series.empty else None
                info["std"] = float(series.std()) if not series.empty else None
                info["min"] = float(series.min()) if not series.empty else None
                info["max"] = float(series.max()) if not series.empty else None
            elif pd.api.types.is_datetime64_any_dtype(series):
                info["type"] = "datetime"
                info["min"] = str(series.min())
                info["max"] = str(series.max())
            else:
                # Try to parse as date
                sample = series.dropna().head(50)
                if len(sample) > 0:
                    try:
                        pd.to_datetime(sample, infer_datetime_format=True)
                        info["type"] = "datetime"
                        info["min"] = str(sample.min())
                        info["max"] = str(sample.max())
                    except (ValueError, TypeError):
                        nunique = series.nunique()
                        if nunique <= max(20, int(len(df) * 0.05)):
                            info["type"] = "categorical"
                            info["unique"] = int(nunique)
                            info["top_values"] = (
                                series.value_counts().head(10).to_dict()
                            )
                        else:
                            info["type"] = "text"
                            info["unique"] = int(nunique)
                else:
                    info["type"] = "text"

            info["missing"] = int(series.isna().sum())
            info["non_null"] = int(series.notna().sum())
            analysis[col] = info

        return analysis

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def compute_aggregation(
        df: pd.DataFrame,
        group_by: str | list[str],
        agg_column: str,
        agg_func: str,
    ) -> pd.DataFrame:
        """Group by one or more columns and aggregate."""
        if isinstance(group_by, str):
            group_by = [group_by]

        agg_map = {
            "sum": "sum",
            "mean": "mean",
            "average": "mean",
            "avg": "mean",
            "count": "count",
            "max": "max",
            "min": "min",
            "median": "median",
            "std": "std",
        }
        func = agg_map.get(agg_func.lower(), "sum")

        result = df.groupby(group_by, dropna=False)[agg_column].agg(func).reset_index()
        result.columns = [*group_by, f"{agg_func}_{agg_column}"]
        return result

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    @staticmethod
    def filter_data(df: pd.DataFrame, filters: list[dict[str, Any]]) -> pd.DataFrame:
        """Apply a list of filter dicts: {column, operator, value}."""
        filtered = df.copy()

        for f in filters:
            col = f.get("column", "")
            op = f.get("operator", "==")
            val = f.get("value")

            if col not in filtered.columns:
                continue

            series = filtered[col]

            if op in ("==", "eq", "equals"):
                if pd.api.types.is_numeric_dtype(series):
                    filtered = filtered[series == float(val)]
                else:
                    filtered = filtered[series.astype(str).str.lower() == str(val).lower()]
            elif op in ("!=", "ne", "not_equals"):
                if pd.api.types.is_numeric_dtype(series):
                    filtered = filtered[series != float(val)]
                else:
                    filtered = filtered[series.astype(str).str.lower() != str(val).lower()]
            elif op in (">", "gt"):
                filtered = filtered[series > float(val)]
            elif op in ("<", "lt"):
                filtered = filtered[series < float(val)]
            elif op in (">=", "gte"):
                filtered = filtered[series >= float(val)]
            elif op in ("<=", "lte"):
                filtered = filtered[series <= float(val)]
            elif op in ("contains", "like"):
                filtered = filtered[series.astype(str).str.contains(str(val), case=False, na=False)]
            elif op in ("in",):
                if isinstance(val, list):
                    filtered = filtered[series.isin(val)]
                else:
                    filtered = filtered[series.astype(str).str.lower().isin([str(v).lower() for v in str(val).split(",")])]

        return filtered

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------
    @staticmethod
    def compute_ranking(
        df: pd.DataFrame,
        column: str,
        n: int = 10,
        ascending: bool = False,
    ) -> pd.DataFrame:
        """Return top/bottom N rows sorted by *column*."""
        return df.nlargest(n, column) if not ascending else df.nsmallest(n, column)

    # ------------------------------------------------------------------
    # Time-series helpers
    # ------------------------------------------------------------------
    @staticmethod
    def compute_time_series(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        freq: str = "ME",
    ) -> pd.DataFrame:
        """Resample a time series by month-end frequency and format nicely."""
        tmp = df[[date_col, value_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp = tmp.dropna(subset=[date_col])
        tmp = tmp.set_index(date_col)
        # Use ME for Pandas 3.0+ compatibility
        try:
            resampled = tmp.resample(freq).sum().reset_index()
        except Exception:
            try:
                resampled = tmp.resample("ME").sum().reset_index()
            except Exception:
                resampled = tmp.resample("M").sum().reset_index()

        # Format date as readable YYYY-MM
        resampled[date_col] = resampled[date_col].dt.strftime("%Y-%m")
        resampled.columns = [date_col, f"total_{value_col}"]
        return resampled

    # ------------------------------------------------------------------
    # Date column detection
    # ------------------------------------------------------------------
    @staticmethod
    def detect_date_columns(df: pd.DataFrame) -> list[str]:
        """Attempt to parse object columns as datetime; return those that succeed."""
        date_cols: list[str] = []

        # Include actual datetime columns first
        for col in df.select_dtypes(include=["datetime", "datetimetz"]).columns:
            date_cols.append(col)

        # Check object columns
        for col in df.select_dtypes(include=["object"]).columns:
            if col in date_cols:
                continue
            sample = df[col].dropna().head(50)
            if len(sample) == 0:
                continue
            try:
                # Standard pandas pd.to_datetime without removed keyword
                parsed = pd.to_datetime(sample, errors="raise")
                if parsed.notna().sum() > len(sample) * 0.8:
                    date_cols.append(col)
            except Exception:
                continue

        return date_cols

    # ------------------------------------------------------------------
    # Merge / join
    # ------------------------------------------------------------------
    @staticmethod
    def merge_datasets(
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        on: str | list[str],
        how: str = "inner",
    ) -> pd.DataFrame:
        """Merge two dataframes."""
        return pd.merge(df1, df2, on=on, how=how)

    # ------------------------------------------------------------------
    # Correlation
    # ------------------------------------------------------------------
    @staticmethod
    def compute_correlation(df: pd.DataFrame) -> pd.DataFrame:
        """Return correlation matrix for numeric columns."""
        numeric = df.select_dtypes(include=[np.number])
        if numeric.shape[1] < 2:
            return pd.DataFrame()
        return numeric.corr()

    # ------------------------------------------------------------------
    # Percentages
    # ------------------------------------------------------------------
    @staticmethod
    def compute_percentages(series: pd.Series) -> pd.Series:
        """Convert a numeric series to percentages of total."""
        total = series.sum()
        if total == 0:
            return series
        return (series / total * 100).round(2)
