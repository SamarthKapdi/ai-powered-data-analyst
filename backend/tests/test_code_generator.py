"""Unit tests for CodeGenerator."""

from __future__ import annotations

import pytest
from app.services.code_generator import CodeGenerator


@pytest.fixture
def generator():
    return CodeGenerator()


def test_generate_sql_simple(generator):
    op = {
        "select": ["region"],
        "agg_func": "SUM",
        "agg_column": "revenue",
        "group_by": ["region"],
        "order_by": "sum_revenue",
        "order_dir": "DESC",
        "limit": 5,
    }
    sql = generator.generate_sql(op, table_name="sales")
    assert "SELECT region, SUM(revenue) AS sum_revenue" in sql
    assert "FROM sales" in sql
    assert "GROUP BY region" in sql
    assert "ORDER BY sum_revenue DESC" in sql
    assert "LIMIT 5" in sql


def test_generate_sql_with_filter(generator):
    op = {
        "select": ["*"],
        "filters": [{"column": "region", "operator": "==", "value": "North"}],
    }
    sql = generator.generate_sql(op, table_name="sales")
    assert "WHERE region = 'North'" in sql


def test_generate_pandas(generator):
    op = {
        "agg_func": "sum",
        "agg_column": "revenue",
        "group_by": ["region"],
        "order_by": "sum_revenue",
        "order_dir": "DESC",
        "limit": 5,
    }
    code = generator.generate_pandas(op)
    assert "groupby" in code
    assert "revenue" in code
    assert "sort_values" in code
    assert "head(5)" in code
