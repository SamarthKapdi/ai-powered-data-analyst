"""Upload router – file upload, deletion, and preview endpoints."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from app.core.config import settings
from app.models.schemas import DataPreviewResponse, DatasetInfo
from app.services.data_service import DataService

logger = logging.getLogger(__name__)

router = APIRouter()
data_service = DataService()


def _get_store(request: Request) -> dict[str, dict[str, Any]]:
    """Retrieve the in-memory dataset store from app state."""
    return request.app.state.datasets  # type: ignore[return-value]


def _dtype_friendly(dtype: Any) -> str:
    """Convert numpy/pandas dtype to a human-friendly string."""
    s = str(dtype)
    if "int" in s:
        return "integer"
    if "float" in s:
        return "float"
    if "datetime" in s:
        return "datetime"
    if "bool" in s:
        return "boolean"
    return "string"


# ------------------------------------------------------------------
# POST /api/upload  – upload one or more CSV files
# ------------------------------------------------------------------
@router.post("/", response_model=list[DatasetInfo])
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
) -> list[DatasetInfo]:
    """Accept one or more CSV uploads and register them in memory."""
    store = _get_store(request)
    results: list[DatasetInfo] = []

    for upload in files:
        filename = upload.filename or "unknown.csv"
        ext = os.path.splitext(filename)[1].lower()

        # Validate extension
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' has unsupported extension '{ext}'. Allowed: {settings.ALLOWED_EXTENSIONS}",
            )

        # Read bytes
        content = await upload.read()

        # Validate size
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' exceeds the {settings.MAX_FILE_SIZE_MB} MB limit.",
            )

        # Parse CSV
        try:
            df, warnings = data_service.validate_csv(content, filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        # Enforce row limit
        if len(df) > settings.MAX_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}' has {len(df)} rows, exceeding the {settings.MAX_ROWS:,} row limit.",
            )

        # Generate ID and build metadata
        dataset_id = uuid.uuid4().hex[:12]
        column_types = {col: _dtype_friendly(df[col].dtype) for col in df.columns}
        missing_values = {col: int(df[col].isna().sum()) for col in df.columns}
        duplicate_rows = int(df.duplicated().sum())

        info = DatasetInfo(
            id=dataset_id,
            filename=filename,
            rows=len(df),
            columns=len(df.columns),
            column_names=list(df.columns),
            column_types=column_types,
            missing_values=missing_values,
            duplicate_rows=duplicate_rows,
            file_size=len(content),
            uploaded_at=datetime.now(timezone.utc),
        )

        store[dataset_id] = {"df": df, "filename": filename, "info": info}
        results.append(info)
        logger.info("Uploaded '%s' → dataset_id=%s  (%d rows, %d cols)", filename, dataset_id, len(df), len(df.columns))

    return results


# ------------------------------------------------------------------
# DELETE /api/upload/{dataset_id}
# ------------------------------------------------------------------
@router.delete("/{dataset_id}")
async def delete_dataset(request: Request, dataset_id: str) -> dict[str, str]:
    store = _get_store(request)
    if dataset_id not in store:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    del store[dataset_id]
    return {"status": "deleted", "dataset_id": dataset_id}


# ------------------------------------------------------------------
# GET /api/upload/{dataset_id}/preview
# ------------------------------------------------------------------
@router.get("/{dataset_id}/preview", response_model=DataPreviewResponse)
async def preview_dataset(request: Request, dataset_id: str) -> DataPreviewResponse:
    store = _get_store(request)
    entry = store.get(dataset_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    df: pd.DataFrame = entry["df"]
    preview = df.head(100).replace({np.nan: None}).to_dict(orient="records")

    return DataPreviewResponse(
        columns=list(df.columns),
        dtypes={col: _dtype_friendly(df[col].dtype) for col in df.columns},
        preview_data=preview,
        total_rows=len(df),
        missing_summary={col: int(df[col].isna().sum()) for col in df.columns},
        duplicate_count=int(df.duplicated().sum()),
    )
