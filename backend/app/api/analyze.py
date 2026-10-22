"""Analysis router – natural-language question → structured analysis."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()
analysis_service = AnalysisService()


@router.post("/", response_model=AnalysisResponse)
async def analyze(request: Request, body: AnalysisRequest) -> AnalysisResponse:
    """Answer an analytical question about uploaded datasets."""
    store: dict[str, dict[str, Any]] = request.app.state.datasets  # type: ignore[attr-defined]

    if not store:
        raise HTTPException(status_code=400, detail="No datasets uploaded yet. Please upload a CSV file first.")

    # Resolve which datasets to use
    if body.dataset_ids:
        datasets = {}
        for did in body.dataset_ids:
            if did not in store:
                raise HTTPException(status_code=404, detail=f"Dataset '{did}' not found.")
            datasets[did] = store[did]
    else:
        # Use all uploaded datasets
        datasets = dict(store)

    result = analysis_service.analyze(
        question=body.question,
        datasets=datasets,
        conversation_history=body.conversation_history,
    )

    return result
