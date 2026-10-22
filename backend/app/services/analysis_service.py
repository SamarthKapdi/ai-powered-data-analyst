"""Analysis service – the brain of the application.

Parses natural-language questions, executes deterministic data operations,
generates charts/code, and optionally enriches answers via LLM.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Any

import numpy as np
import pandas as pd

from app.models.schemas import AnalysisResponse
from app.services.anomaly_service import AnomalyService
from app.services.code_generator import CodeGenerator
from app.services.data_service import DataService
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AnalysisService:
    """Orchestrates question parsing → data computation → response formatting."""

    def __init__(self) -> None:
        self.data_service = DataService()
        self.anomaly_service = AnomalyService()
        self.code_generator = CodeGenerator()
        self.llm_service = LLMService()

    # ==================================================================
    # Public entry point
    # ==================================================================
    def analyze(
        self,
        question: str,
        datasets: dict[str, dict],
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> AnalysisResponse:
        """Full analysis pipeline."""
        if not datasets:
            return AnalysisResponse(answer="No datasets are loaded. Please upload a CSV file first.", error="no_datasets")

        # Merge all referenced datasets into one working copy
        df, table_name, schema_info = self._prepare_data(datasets)

        # 1. Parse the question
        parsed = self._parse_question(question, df)

        # 1b. Enrich from conversation history for follow-up questions
        if conversation_history:
            parsed = self._enrich_from_context(parsed, question, conversation_history, df)

        intent = parsed["intent"]

        try:
            # 2. Execute analysis
            result_df, result_scalar, result_summary = self._execute(intent, parsed, df)

            # 3. Build chart config
            chart_config = self._build_chart(intent, parsed, result_df, result_scalar)

            # 4. Generate code
            operation = self._build_operation_dict(parsed)
            sql_code = self.code_generator.generate_sql(operation, table_name)
            pandas_code = self.code_generator.generate_pandas(operation)

            # 5. Detect anomalies if relevant
            anomalies_list: list[dict] | None = None
            if intent == "anomaly":
                target_cols = parsed.get("target_columns") or None
                anomalies_list = self.anomaly_service.detect_anomalies(df, columns=target_cols)

            # 6. Generate explanation
            answer = self._generate_answer(question, result_summary, schema_info, conversation_history)

            # 7. Prepare data payload
            data_payload = self._result_to_payload(result_df, result_scalar)

            return AnalysisResponse(
                answer=answer,
                data=data_payload,
                chart_config=chart_config,
                sql_code=sql_code,
                pandas_code=pandas_code,
                anomalies=anomalies_list,
            )

        except Exception as exc:
            logger.exception("Analysis execution error")
            return AnalysisResponse(
                answer=f"I encountered an error while analysing your data: {exc}",
                error=str(exc),
            )

    # ==================================================================
    # Data preparation
    # ==================================================================
    def _prepare_data(self, datasets: dict[str, dict]) -> tuple[pd.DataFrame, str, str]:
        """Combine datasets intelligently via merge on shared keys or source-tagged concatenation."""
        entries = list(datasets.values())
        if len(entries) == 1:
            df = entries[0]["df"].copy()
            table_name = entries[0].get("filename", "dataset").rsplit(".", 1)[0]
        else:
            dfs = [e["df"] for e in entries]
            # Find common columns across all datasets
            common_cols = set(dfs[0].columns)
            for d in dfs[1:]:
                common_cols &= set(d.columns)

            # If schemas are nearly identical (e.g. monthly or yearly splits)
            if len(common_cols) >= len(dfs[0].columns) * 0.8:
                tagged_dfs = []
                for e in entries:
                    tdf = e["df"].copy()
                    fname = e.get("filename", "file").rsplit(".", 1)[0]
                    tdf["source_file"] = fname
                    tagged_dfs.append(tdf)
                df = pd.concat(tagged_dfs, ignore_index=True)
                table_name = "combined_dataset"
            else:
                # Intelligent join on shared key (e.g. 'region', 'product', 'category')
                candidate_keys = [
                    c for c in common_cols
                    if not (c.lower().endswith("_id") or c.lower() == "id") and dfs[0][c].dtype == "object"
                ]
                if candidate_keys:
                    join_key = candidate_keys[0]
                    df1 = dfs[0].copy()
                    df2 = dfs[1].copy()
                    num1 = [c for c in df1.select_dtypes(include=[np.number]).columns if not c.lower().endswith("_id")]

                    # Aggregate df1 if needed before joining
                    if df1[join_key].duplicated().any() and num1:
                        df1 = df1.groupby(join_key, as_index=False)[num1].sum()

                    df = pd.merge(df1, df2, on=join_key, how="inner")
                    table_name = "merged_dataset"
                else:
                    df = pd.concat(dfs, ignore_index=True)
                    table_name = "combined_dataset"

        schema_lines = [f"Table: {table_name}"]
        for col in df.columns:
            dtype = str(df[col].dtype)
            nunique = df[col].nunique()
            schema_lines.append(f"  - {col} ({dtype}, {nunique} unique values)")
        schema_info = "\n".join(schema_lines)

        return df, table_name, schema_info

    # ==================================================================
    # Question parser
    # ==================================================================
    def _parse_question(self, question: str, df: pd.DataFrame) -> dict[str, Any]:
        """Keyword / regex-based intent and entity extraction."""
        q = question.lower().strip()
        columns = list(df.columns)

        parsed: dict[str, Any] = {
            "intent": "general_info",
            "target_columns": [],
            "group_by": [],
            "agg_func": "sum",
            "filters": [],
            "sort_direction": "desc",
            "limit": None,
            "raw_question": question,
        }

        # ----- Intent detection -----
        has_group_hint = bool(re.search(r"\b(which|by|per|each|across|every|distribution|breakdown)\s+\w+", q))

        if re.search(r"\b(trend\w*|over\s+time|monthly|quarterly|yearly|weekly|time\s*series)\b", q):
            parsed["intent"] = "trend"

        elif re.search(r"\b(anomal\w*|outlier\w*|unusual|abnormal|spike\w*|drop\w*)\b", q):
            parsed["intent"] = "anomaly"

        elif re.search(r"\b(correlat\w*|relationship\w*|association\w*)\b", q):
            parsed["intent"] = "correlation"

        elif re.search(r"\b(compar\w*|versus|vs\.?|difference\w*|between)\b", q):
            parsed["intent"] = "comparison"

        elif re.search(r"\b(sql|pandas|code|query|script)\b", q):
            parsed["intent"] = "code_generation"

        elif re.search(r"\b(underperform\w*|under-perform\w*|least\s+performing|worst\s+performing)\b", q):
            parsed["intent"] = "ranking"
            parsed["sort_direction"] = "asc"
            parsed["limit"] = 5

        elif has_group_hint and re.search(r"\b(highest|lowest|most|least|best|worst|largest|smallest)\b", q):
            parsed["intent"] = "aggregation"
            if re.search(r"\b(lowest|least|worst|smallest)\b", q):
                parsed["sort_direction"] = "asc"

        elif re.search(r"\b(top|bottom)\s+\d+\b", q) or re.search(r"\b(rank\w*)\b", q):
            parsed["intent"] = "ranking"
            m = re.search(r"\b(top|bottom)\s+(\d+)", q)
            if m:
                parsed["limit"] = int(m.group(2))
                if m.group(1) == "bottom":
                    parsed["sort_direction"] = "asc"
            else:
                parsed["limit"] = 10
            if re.search(r"\b(lowest|bottom|worst|smallest|underperform\w*)\b", q):
                parsed["sort_direction"] = "asc"

        elif re.search(r"\b(highest|lowest|best|worst|largest|smallest)\b", q):
            parsed["intent"] = "ranking"
            parsed["limit"] = 10
            if re.search(r"\b(lowest|worst|smallest)\b", q):
                parsed["sort_direction"] = "asc"

        elif re.search(r"\b(by\s+\w+)\b", q) or re.search(r"\b(total|sum|average|mean|count|how\s+many|median|max|min)\b", q):
            parsed["intent"] = "aggregation"
        else:
            parsed["intent"] = "general_info"

        # ----- Aggregation function -----
        if re.search(r"\b(average|mean|avg)\b", q):
            parsed["agg_func"] = "mean"
        elif re.search(r"\b(total|sum)\b", q):
            parsed["agg_func"] = "sum"
        elif re.search(r"\b(count|how\s+many|number\s+of)\b", q):
            parsed["agg_func"] = "count"
        elif re.search(r"\b(median)\b", q):
            parsed["agg_func"] = "median"
        elif re.search(r"\b(std|deviation|volatility)\b", q):
            parsed["agg_func"] = "std"
        elif parsed["intent"] == "aggregation" and re.search(r"\b(highest|most|best|largest|biggest)\b", q):
            # "Which X has the highest Y" → sum by group then rank
            parsed["agg_func"] = "sum"
        elif re.search(r"\b(max|maximum)\b", q):
            parsed["agg_func"] = "max"
        elif re.search(r"\b(min|minimum)\b", q):
            parsed["agg_func"] = "min"
        else:
            # Default: sum for aggregations, sum for rankings
            parsed["agg_func"] = "sum"

        # ----- Column matching -----
        matched_cols = self._match_columns(q, columns, df)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = [c for c in columns if c not in numeric_cols]

        # Separate matched columns into target (numeric) and group-by (categorical)
        for col in matched_cols:
            if col in numeric_cols:
                if col not in parsed["target_columns"]:
                    parsed["target_columns"].append(col)
            else:
                if col not in parsed["group_by"]:
                    parsed["group_by"].append(col)

        # ----- Detect "by <column>" pattern -----
        by_match = re.findall(r"\bby\s+(\w[\w\s]*?)(?:\s+and\s+|\s*,\s*|\s*$)", q)
        for by_phrase in by_match:
            by_col = self._fuzzy_match_column(by_phrase.strip(), columns)
            if by_col and by_col not in parsed["group_by"]:
                parsed["group_by"].append(by_col)

        # ----- Defaults: pick the best metric candidates (excluding IDs) -----
        metric_candidates = [
            c for c in numeric_cols if not (c.lower().endswith("_id") or c.lower() == "id")
        ]
        if not metric_candidates:
            metric_candidates = numeric_cols

        # Preferred metric columns in order: revenue/sales first, then others
        priority_metrics = []
        for pref in ["revenue", "sales", "total_revenue", "total_sales", "amount", "profit"]:
            found = [c for c in metric_candidates if pref == c.lower() or pref in c.lower()]
            if found:
                priority_metrics.extend(found)
                break
        if not priority_metrics:
            for pref in ["quantity", "total", "value", "price", "cost"]:
                found = [c for c in metric_candidates if pref in c.lower()]
                if found:
                    priority_metrics.extend(found)
                    break

        default_metric = priority_metrics[0] if priority_metrics else (metric_candidates[0] if metric_candidates else None)

        # For ranking / aggregation / trend: default target column to priority metric
        if not parsed["target_columns"] and default_metric and parsed["intent"] not in ("anomaly", "general_info", "code_generation"):
            parsed["target_columns"] = [default_metric]

        if parsed["intent"] == "aggregation" and not parsed["group_by"] and categorical_cols:
            parsed["group_by"] = [categorical_cols[0]]

        # ----- Filter detection  e.g. "in North", "for Electronics" -----
        parsed["filters"] = self._detect_filters(q, df)

        return parsed

    def _enrich_from_context(
        self,
        parsed: dict[str, Any],
        question: str,
        history: list[dict[str, Any]],
        df: pd.DataFrame,
    ) -> dict[str, Any]:
        """Inherit metrics, dimensions, and filters from recent conversation turns for follow-ups."""
        if not history:
            return parsed

        last_user_turn = None
        for msg in reversed(history):
            if msg.get("role") == "user" and msg.get("content"):
                last_user_turn = msg["content"]
                break

        if not last_user_turn:
            return parsed

        prev_parsed = self._parse_question(last_user_turn, df)
        q_lower = question.lower()

        # Follow-up patterns like "which one performed worst", "which one was best", "what about the worst"
        if re.search(r"\b(which\s+one|what\s+about|who|which)\b", q_lower) and re.search(r"\b(worst|best|lowest|highest|least|most)\b", q_lower):
            if prev_parsed.get("group_by"):
                parsed["group_by"] = prev_parsed["group_by"]
            if prev_parsed.get("target_columns"):
                parsed["target_columns"] = prev_parsed["target_columns"]
            parsed["intent"] = "ranking"
            parsed["limit"] = 1
            if re.search(r"\b(worst|lowest|least|bottom)\b", q_lower):
                parsed["sort_direction"] = "asc"
            else:
                parsed["sort_direction"] = "desc"

        # Pattern: "Show that by <dimension>" or "Now by <dimension>"
        elif re.search(r"\b(that|it|same|now)\s+(by|per|across)\b|\bshow\s+that\b", q_lower):
            if prev_parsed.get("target_columns"):
                parsed["target_columns"] = prev_parsed["target_columns"]
                parsed["agg_func"] = prev_parsed.get("agg_func", parsed["agg_func"])
            if not parsed.get("intent") or parsed["intent"] == "general_info":
                parsed["intent"] = "aggregation"

        # Pattern: "What about <category_value>?" (e.g. "What about South?", "What about Electronics?")
        elif re.search(r"\bwhat\s+about\b", q_lower):
            if prev_parsed.get("target_columns"):
                parsed["target_columns"] = prev_parsed["target_columns"]
            if prev_parsed.get("group_by"):
                parsed["group_by"] = prev_parsed["group_by"]
            parsed["intent"] = prev_parsed.get("intent", "aggregation")

        return parsed

    def _match_columns(self, question: str, columns: list[str], df: pd.DataFrame) -> list[str]:
        """Match words in the question to DataFrame column names using fuzzy matching."""
        matched: list[str] = []
        q = question.lower()

        # Synonyms / aliases for common column names
        aliases: dict[str, list[str]] = {
            "revenue": ["revenue", "total_revenue", "sales", "amount", "income", "turnover"],
            "sales": ["sales", "revenue", "total_sales", "amount"],
            "profit": ["profit", "net_profit", "gross_profit", "margin", "earnings"],
            "quantity": ["quantity", "qty", "units", "units_sold", "count"],
            "price": ["price", "unit_price", "cost", "rate", "amount"],
            "date": ["date", "order_date", "created_at", "timestamp", "time", "period"],
            "region": ["region", "area", "territory", "zone", "location", "state", "country"],
            "category": ["category", "product_category", "type", "segment", "group", "department"],
            "product": ["product", "product_name", "item", "sku"],
            "customer": ["customer", "customer_name", "client", "buyer"],
            "name": ["name", "full_name", "title"],
        }

        col_lower = {c.lower().replace("_", " "): c for c in columns}
        col_lower_underscore = {c.lower(): c for c in columns}

        # Direct substring matching
        for cl, original in col_lower.items():
            if cl in q and original not in matched:
                matched.append(original)

        for cl, original in col_lower_underscore.items():
            if cl in q and original not in matched:
                matched.append(original)

        # Alias matching
        for alias_key, alias_list in aliases.items():
            if alias_key in q:
                for alias in alias_list:
                    for cl, original in col_lower_underscore.items():
                        if alias in cl and original not in matched:
                            matched.append(original)

        # Fuzzy fallback – check each word of the question against column names
        words = re.findall(r"\b\w{3,}\b", q)
        for word in words:
            best = self._fuzzy_match_column(word, columns, threshold=0.7)
            if best and best not in matched:
                matched.append(best)

        return matched

    @staticmethod
    def _fuzzy_match_column(
        text: str,
        columns: list[str],
        threshold: float = 0.6,
    ) -> str | None:
        """Return the best-matching column name if similarity >= threshold."""
        text_lower = text.lower().replace("_", " ")
        best_score = 0.0
        best_col: str | None = None
        for col in columns:
            col_lower = col.lower().replace("_", " ")
            score = SequenceMatcher(None, text_lower, col_lower).ratio()
            if score > best_score:
                best_score = score
                best_col = col
        return best_col if best_score >= threshold else None

    def _detect_filters(self, question: str, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Detect filter expressions like 'in North', 'for Electronics'."""
        filters: list[dict[str, Any]] = []
        q = question.lower()

        # Patterns: "in <value>", "for <value>", "where <col> is <value>"
        preposition_patterns = [
            r"\b(?:in|for|of|from)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)",
        ]
        for pattern in preposition_patterns:
            for match in re.finditer(pattern, question):
                value = match.group(1).strip()
                # Find which categorical column contains this value
                for col in df.select_dtypes(include=["object"]).columns:
                    unique_lower = {str(v).lower(): str(v) for v in df[col].dropna().unique()}
                    if value.lower() in unique_lower:
                        filters.append(
                            {"column": col, "operator": "==", "value": unique_lower[value.lower()]}
                        )
                        break

        # Pattern: "where <col> = <value>" or "<col> equals <value>"
        where_patterns = re.findall(
            r"where\s+(\w+)\s*(?:=|is|equals?)\s*['\"]?(\w+)['\"]?", q
        )
        for col_text, val in where_patterns:
            matched_col = self._fuzzy_match_column(col_text, list(df.columns))
            if matched_col:
                filters.append({"column": matched_col, "operator": "==", "value": val})

        return filters

    # ==================================================================
    # Execution engine
    # ==================================================================
    def _execute(
        self,
        intent: str,
        parsed: dict[str, Any],
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame | None, Any, str]:
        """Run the identified operation and return (result_df, scalar, summary)."""

        # Apply any filters first
        if parsed["filters"]:
            df = self.data_service.filter_data(df, parsed["filters"])

        target_cols = parsed["target_columns"]
        group_by = parsed["group_by"]
        agg_func = parsed["agg_func"]
        limit = parsed.get("limit") or 10
        ascending = parsed["sort_direction"] == "asc"

        if intent == "ranking":
            target_col = target_cols[0] if target_cols else (default_metric if "default_metric" in locals() and default_metric else df.select_dtypes(include=[np.number]).columns[0])
            direction = "bottom" if ascending else "top"
            if group_by:
                result_df = self.data_service.compute_aggregation(df, group_by, target_col, agg_func)
                val_col = result_df.columns[-1]
                result_df = result_df.sort_values(val_col, ascending=ascending).head(limit)
                summary = f"{direction.title()} {limit} {', '.join(group_by)} by {agg_func} of {target_col}:\n{result_df.to_string(index=False)}"
                return result_df, None, summary
            else:
                result_df = self.data_service.compute_ranking(df, target_col, n=limit, ascending=ascending)
                summary = f"{direction.title()} {limit} rows by {target_col}:\n{result_df.to_string(index=False)}"
                return result_df, None, summary

        elif intent == "aggregation" or intent == "comparison":
            target_col = target_cols[0] if target_cols else df.select_dtypes(include=[np.number]).columns[0]
            if group_by:
                result_df = self.data_service.compute_aggregation(df, group_by, target_col, agg_func)
                result_df = result_df.sort_values(result_df.columns[-1], ascending=ascending)
                summary = f"{agg_func.upper()} of {target_col} grouped by {', '.join(group_by)}:\n{result_df.to_string(index=False)}"
                return result_df, None, summary
            else:
                agg_map = {"sum": "sum", "mean": "mean", "count": "count",
                           "max": "max", "min": "min", "median": "median", "std": "std"}
                func_name = agg_map.get(agg_func, "sum")
                scalar = getattr(df[target_col], func_name)()
                summary = f"The {agg_func} of {target_col} is {scalar:,.2f}" if isinstance(scalar, float) else f"The {agg_func} of {target_col} is {scalar}"
                return None, scalar, summary

        elif intent == "trend":
            date_cols = self.data_service.detect_date_columns(df)
            if not date_cols:
                return None, None, "No date columns detected in the dataset for trend analysis."
            date_col = date_cols[0]
            target_col = target_cols[0] if target_cols else df.select_dtypes(include=[np.number]).columns[0]
            result_df = self.data_service.compute_time_series(df, date_col, target_col)
            result_df[date_col] = result_df[date_col].astype(str)
            summary = f"Trend of {target_col} over {date_col}:\n{result_df.to_string(index=False)}"
            return result_df, None, summary

        elif intent == "anomaly":
            target = target_cols if target_cols else None
            anomalies = self.anomaly_service.detect_anomalies(df, columns=target)
            if anomalies:
                summary_lines = [f"Found {len(anomalies)} anomalies:"]
                for a in anomalies[:10]:
                    summary_lines.append(self.anomaly_service.explain_anomaly(a))
                summary = "\n".join(summary_lines)
                row_indices = list(set(a["row_index"] for a in anomalies))
                result_df = df.loc[row_indices]
            else:
                summary = "No significant anomalies detected in the data."
                result_df = None
            return result_df, None, summary

        elif intent == "correlation":
            corr_df = self.data_service.compute_correlation(df)
            if corr_df.empty:
                return None, None, "Not enough numeric columns to compute correlations."
            summary = f"Correlation matrix:\n{corr_df.to_string()}"
            return corr_df, None, summary

        elif intent == "code_generation":
            # Just generate code – the code is already generated in analyze()
            summary = "Code has been generated for your query."
            return None, None, summary

        else:  # general_info
            info_lines = [
                f"Dataset has {len(df)} rows and {len(df.columns)} columns.",
                f"Columns: {', '.join(df.columns)}",
            ]
            numeric = df.select_dtypes(include=[np.number])
            if not numeric.empty:
                desc = numeric.describe().round(2)
                info_lines.append(f"\nNumeric summary:\n{desc.to_string()}")
            summary = "\n".join(info_lines)
            return None, None, summary

    # ==================================================================
    # Chart configuration
    # ==================================================================
    def _build_chart(
        self,
        intent: str,
        parsed: dict[str, Any],
        result_df: pd.DataFrame | None,
        result_scalar: Any,
    ) -> dict[str, Any] | None:
        """Generate a chart_config dict based on the result type."""
        if result_df is None or result_df.empty:
            return None

        columns = list(result_df.columns)

        # --- Recharts-compatible format: list of {xKey: ..., yKey: ...} dicts ---

        label_cols = [c for c in columns if not pd.api.types.is_numeric_dtype(result_df[c])]
        value_cols = [c for c in columns if pd.api.types.is_numeric_dtype(result_df[c])]

        if intent == "trend":
            label_col = columns[0]
            value_col = columns[1] if len(columns) > 1 else columns[0]
            chart_data = []
            for _, row in result_df.iterrows():
                chart_data.append({label_col: str(row[label_col]), value_col: row[value_col]})
            return {
                "type": "line",
                "data": chart_data,
                "options": {"title": f"Trend of {value_col}", "xKey": label_col, "yKey": value_col, "xLabel": label_col, "yLabel": value_col},
            }

        elif intent == "ranking":
            label_col = label_cols[0] if label_cols else columns[0]
            value_col = value_cols[0] if value_cols else columns[-1]
            chart_data = []
            for _, row in result_df.iterrows():
                chart_data.append({label_col: str(row[label_col]), value_col: row[value_col]})
            return {
                "type": "bar",
                "data": chart_data,
                "options": {"title": f"Ranking by {value_col}", "xKey": label_col, "yKey": value_col, "xLabel": label_col, "yLabel": value_col},
            }

        elif intent in ("aggregation", "comparison"):
            label_col = columns[0]
            value_col = columns[-1]
            chart_data = []
            for _, row in result_df.iterrows():
                chart_data.append({label_col: str(row[label_col]), value_col: row[value_col]})

            chart_type = "pie" if len(result_df) <= 6 else "bar"
            return {
                "type": chart_type,
                "data": chart_data,
                "options": {"title": f"{value_col} by {label_col}", "xKey": label_col, "yKey": value_col,
                            "nameKey": label_col, "valueKey": value_col, "xLabel": label_col, "yLabel": value_col},
            }

        elif intent == "correlation":
            chart_data = []
            for _, row in result_df.iterrows():
                entry = {c: row[c] for c in columns}
                chart_data.append(entry)
            return {
                "type": "table",
                "data": chart_data,
                "options": {"title": "Correlation Matrix"},
            }

        elif intent == "anomaly":
            if result_df is not None and not result_df.empty:
                label_cols = [c for c in columns if not pd.api.types.is_numeric_dtype(result_df[c])]
                val_cols = [c for c in columns if pd.api.types.is_numeric_dtype(result_df[c]) and not c.lower().endswith("_id")]
                label_col = label_cols[0] if label_cols else columns[0]
                val_col = val_cols[0] if val_cols else columns[-1]
                chart_data = []
                for _, row in result_df.head(10).iterrows():
                    chart_data.append({label_col: str(row[label_col]), val_col: row[val_col]})
                return {
                    "type": "bar",
                    "data": chart_data,
                    "options": {"title": f"Anomalous Records ({val_col})", "xKey": label_col, "yKey": val_col, "xLabel": label_col, "yLabel": val_col},
                }

        return None

    # ==================================================================
    # Operation dict (for code generation)
    # ==================================================================
    @staticmethod
    def _build_operation_dict(parsed: dict[str, Any]) -> dict[str, Any]:
        """Translate parsed question into the operation dict expected by CodeGenerator."""
        op: dict[str, Any] = {
            "select": parsed.get("target_columns") or ["*"],
            "agg_func": parsed.get("agg_func"),
            "agg_column": parsed["target_columns"][0] if parsed.get("target_columns") else None,
            "group_by": parsed.get("group_by") or None,
            "filters": parsed.get("filters") or None,
            "order_by": None,
            "order_dir": "ASC" if parsed.get("sort_direction") == "asc" else "DESC",
            "limit": parsed.get("limit"),
        }
        # Set order_by to the aggregated column alias when there's a group
        if op["agg_func"] and op["agg_column"] and op["group_by"]:
            op["order_by"] = f"{op['agg_func']}_{op['agg_column']}"
        elif op["agg_column"]:
            op["order_by"] = op["agg_column"]
        return op

    # ==================================================================
    # Answer generation
    # ==================================================================
    def _generate_answer(
        self,
        question: str,
        results_summary: str,
        schema_info: str,
        conversation_history: list[dict[str, Any]] | None,
    ) -> str:
        """Produce a natural-language answer (LLM or template-based)."""
        if self.llm_service.is_available():
            return self.llm_service.generate_explanation(
                question, results_summary, schema_info, conversation_history
            )
        return self.llm_service._fallback_explanation(question, results_summary)

    # ==================================================================
    # Payload conversion
    # ==================================================================
    @staticmethod
    def _result_to_payload(
        result_df: pd.DataFrame | None,
        result_scalar: Any,
    ) -> dict[str, Any] | list[Any] | None:
        """Convert analysis results into a JSON-safe payload."""
        if result_df is not None and not result_df.empty:
            # Convert to list of dicts for the frontend data table
            records = result_df.head(500).replace({np.nan: None}).to_dict(orient="records")
            return records
        if result_scalar is not None:
            if isinstance(result_scalar, (np.integer,)):
                return {"value": int(result_scalar)}
            if isinstance(result_scalar, (np.floating, float)):
                return {"value": round(float(result_scalar), 4)}
            return {"value": result_scalar}
        return None
