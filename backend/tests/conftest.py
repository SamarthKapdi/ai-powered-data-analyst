"""Pytest test fixtures and configuration."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAMPLE_CSV_PATH = DATA_DIR / "sample_sales.csv"


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Load the realistic sample dataset."""
    return pd.read_csv(SAMPLE_CSV_PATH)


@pytest.fixture
def sample_csv_bytes() -> bytes:
    """Raw bytes of sample_sales.csv."""
    with open(SAMPLE_CSV_PATH, "rb") as f:
        return f.read()


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient with fresh state."""
    with TestClient(app) as test_client:
        yield test_client
