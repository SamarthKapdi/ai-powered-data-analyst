"""Datasets router – list, inspect, and paginate uploaded datasets."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

from app.models.schemas import DatasetInfo

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_store(request: Request) -> dict[str, dict[str, Any]]:
    return request.app.state.datasets  # type: ignore[return-value]


# ------------------------------------------------------------------
# GET /api/datasets – list all datasets
# ------------------------------------------------------------------
@router.get("/", response_model=list[DatasetInfo])
async def list_datasets(request: Request) -> list[DatasetInfo]:
    store = _get_store(request)
    return [entry["info"] for entry in store.values()]


# ------------------------------------------------------------------
# GET /api/datasets/{dataset_id} – single dataset info
# ------------------------------------------------------------------
@router.get("/{dataset_id}", response_model=DatasetInfo)
async def get_dataset(request: Request, dataset_id: str) -> DatasetInfo:
    store = _get_store(request)
    entry = store.get(dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return entry["info"]


# ------------------------------------------------------------------
# GET /api/datasets/{dataset_id}/data – paginated data
# ------------------------------------------------------------------
@router.get("/{dataset_id}/data")
async def get_dataset_data(
    request: Request,
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    store = _get_store(request)
    entry = store.get(dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    df: pd.DataFrame = entry["df"]
    total_rows = len(df)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)

    start = (page - 1) * page_size
    end = start + page_size

    page_df = df.iloc[start:end]
    rows = page_df.replace({np.nan: None}).to_dict(orient="records")

    return {
        "data": rows,
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": total_pages,
    }
