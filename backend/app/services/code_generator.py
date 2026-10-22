"""Deterministic SQL & Pandas code generator – no LLM required."""

from __future__ import annotations

from typing import Any


class CodeGenerator:
    """Generates SQL and Pandas code strings from an operation description."""

    # ------------------------------------------------------------------
    # SQL generation
    # ------------------------------------------------------------------
    @staticmethod
    def generate_sql(operation: dict[str, Any], table_name: str = "dataset") -> str:
        """Build a SQL statement from an operation dict.

        Expected keys in *operation*:
            select     – list[str] of columns (or ["*"])
            agg_func   – str | None  (SUM, AVG, COUNT, MAX, MIN)
            agg_column – str | None
            group_by   – list[str] | None
            filters    – list[dict] with {column, operator, value}
            order_by   – str | None
            order_dir  – "ASC" | "DESC"
            limit      – int | None
            join       – dict | None  {table, on, how}
        """
        select_cols = operation.get("select", ["*"])
        agg_func = operation.get("agg_func")
        agg_column = operation.get("agg_column")
        group_by = operation.get("group_by") or []
        filters = operation.get("filters") or []
        order_by = operation.get("order_by")
        order_dir = operation.get("order_dir", "DESC")
        limit = operation.get("limit")
        join = operation.get("join")

        # ---- SELECT clause ----
        if agg_func and agg_column:
            agg_expr = f"{agg_func.upper()}({agg_column})"
            if group_by:
                select_part = ", ".join(group_by) + f", {agg_expr} AS {agg_func.lower()}_{agg_column}"
            else:
                select_part = agg_expr
        else:
            select_part = ", ".join(select_cols)

        sql = f"SELECT {select_part}\nFROM {table_name}"

        # ---- JOIN ----
        if join:
            join_type = (join.get("how", "INNER")).upper()
            join_table = join.get("table", "other_table")
            join_on = join.get("on", "id")
            sql += f"\n{join_type} JOIN {join_table} ON {table_name}.{join_on} = {join_table}.{join_on}"

        # ---- WHERE clause ----
        if filters:
            conditions: list[str] = []
            for f in filters:
                col = f["column"]
                op = f.get("operator", "=")
                val = f["value"]

                sql_op_map = {
                    "==": "=", "eq": "=", "equals": "=",
                    "!=": "!=", "ne": "!=", "not_equals": "!=",
                    ">": ">", "gt": ">",
                    "<": "<", "lt": "<",
                    ">=": ">=", "gte": ">=",
                    "<=": "<=", "lte": "<=",
                    "contains": "LIKE", "like": "LIKE",
                    "in": "IN",
                }
                sql_op = sql_op_map.get(op, "=")

                if sql_op == "LIKE":
                    conditions.append(f"{col} LIKE '%{val}%'")
                elif sql_op == "IN":
                    if isinstance(val, list):
                        vals_str = ", ".join(f"'{v}'" for v in val)
                    else:
                        vals_str = ", ".join(f"'{v.strip()}'" for v in str(val).split(","))
                    conditions.append(f"{col} IN ({vals_str})")
                elif isinstance(val, (int, float)):
                    conditions.append(f"{col} {sql_op} {val}")
                else:
                    conditions.append(f"{col} {sql_op} '{val}'")

            sql += "\nWHERE " + " AND ".join(conditions)

        # ---- GROUP BY ----
        if group_by:
            sql += "\nGROUP BY " + ", ".join(group_by)

        # ---- ORDER BY ----
        if order_by:
            sql += f"\nORDER BY {order_by} {order_dir}"
        elif agg_func and agg_column:
            sql += f"\nORDER BY {agg_func.lower()}_{agg_column} {order_dir}"

        # ---- LIMIT ----
        if limit:
            sql += f"\nLIMIT {limit}"

        return sql + ";"

    # ------------------------------------------------------------------
    # Pandas code generation
    # ------------------------------------------------------------------
    @staticmethod
    def generate_pandas(operation: dict[str, Any], df_name: str = "df") -> str:
        """Build a Pandas code string from an operation dict."""
        lines: list[str] = [f"import pandas as pd\n"]
        result_var = "result"

        filters = operation.get("filters") or []
        group_by = operation.get("group_by") or []
        agg_func = operation.get("agg_func")
        agg_column = operation.get("agg_column")
        order_by = operation.get("order_by")
        order_dir = operation.get("order_dir", "DESC")
        limit = operation.get("limit")
        select_cols = operation.get("select", [])
        join = operation.get("join")

        current = df_name

        # ---- JOIN ----
        if join:
            join_table = join.get("table", "df2")
            join_on = join.get("on", "id")
            join_how = join.get("how", "inner")
            lines.append(f'{current} = pd.merge({current}, {join_table}, on="{join_on}", how="{join_how}")')

        # ---- Filters ----
        if filters:
            for f in filters:
                col = f["column"]
                op = f.get("operator", "==")
                val = f["value"]

                if op in ("contains", "like"):
                    lines.append(f'{current} = {current}[{current}["{col}"].str.contains("{val}", case=False, na=False)]')
                elif op in ("in",):
                    if isinstance(val, list):
                        lines.append(f'{current} = {current}[{current}["{col}"].isin({val})]')
                    else:
                        val_list = [v.strip() for v in str(val).split(",")]
                        lines.append(f'{current} = {current}[{current}["{col}"].isin({val_list})]')
                else:
                    pd_op = {"==": "==", "eq": "==", "equals": "==", "!=": "!=", "ne": "!=",
                             ">": ">", "gt": ">", "<": "<", "lt": "<",
                             ">=": ">=", "gte": ">=", "<=": "<=", "lte": "<="}.get(op, "==")
                    if isinstance(val, (int, float)):
                        lines.append(f'{current} = {current}[{current}["{col}"] {pd_op} {val}]')
                    else:
                        lines.append(f'{current} = {current}[{current}["{col}"] {pd_op} "{val}"]')

        # ---- Select columns ----
        if select_cols and select_cols != ["*"]:
            lines.append(f'{current} = {current}[{select_cols}]')

        # ---- Aggregation ----
        pd_agg_map = {"sum": "sum", "mean": "mean", "average": "mean", "avg": "mean",
                       "count": "count", "max": "max", "min": "min",
                       "median": "median", "std": "std"}

        if agg_func and agg_column and group_by:
            pd_func = pd_agg_map.get(agg_func.lower(), "sum")
            gb = group_by if len(group_by) > 1 else f'"{group_by[0]}"'
            if isinstance(gb, list):
                gb = str(gb)
            lines.append(
                f'{result_var} = {current}.groupby({gb})["{agg_column}"].{pd_func}()'
                f'.reset_index(name="{agg_func.lower()}_{agg_column}")'
            )
            current = result_var
        elif agg_func and agg_column:
            pd_func = pd_agg_map.get(agg_func.lower(), "sum")
            lines.append(f'{result_var} = {current}["{agg_column}"].{pd_func}()')
            current = result_var

        # ---- Sorting ----
        if order_by:
            ascending = order_dir.upper() == "ASC"
            lines.append(f'{current} = {current}.sort_values("{order_by}", ascending={ascending})')

        # ---- Limit ----
        if limit:
            lines.append(f'{current} = {current}.head({limit})')

        lines.append(f'print({current})')
        return "\n".join(lines)
