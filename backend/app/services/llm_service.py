"""LLM service wrapping Google Gemini for natural-language explanations and code."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class LLMService:
    """Optional Google Gemini integration for richer explanations."""

    def __init__(self) -> None:
        self.available = False
        self.client = None
        api_key = os.getenv("GEMINI_API_KEY", "")

        if not api_key or api_key == "your_gemini_api_key_here":
            logger.info("GEMINI_API_KEY not set – LLM features disabled.")
            return

        try:
            from google import genai

            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.0-flash"
            self.available = True
            logger.info("Gemini LLM service initialized successfully.")
        except Exception as exc:
            logger.warning("Failed to initialize Gemini client: %s", exc)
            self.available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        return self.available

    def generate_explanation(
        self,
        question: str,
        results_summary: str,
        schema_info: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Ask Gemini to explain the analysis results in plain English."""
        if not self.available:
            return self._fallback_explanation(question, results_summary)

        prompt = self._build_explanation_prompt(
            question, results_summary, schema_info, conversation_history
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            text = response.text
            return text.strip() if text else self._fallback_explanation(question, results_summary)
        except Exception as exc:
            logger.error("Gemini explanation call failed: %s", exc)
            return self._fallback_explanation(question, results_summary)

    def generate_code(
        self,
        question: str,
        schema_info: str,
        operation_type: str,
    ) -> tuple[str, str]:
        """Generate SQL and Pandas code via Gemini. Returns (sql, pandas)."""
        if not self.available:
            return "", ""

        prompt = (
            "You are a data analyst assistant. Generate ONLY the code, no explanations.\n\n"
            f"Dataset schema:\n{schema_info}\n\n"
            f"Question: {question}\n"
            f"Operation type: {operation_type}\n\n"
            "Respond in this exact JSON format:\n"
            '{"sql": "<SQL query>", "pandas": "<Pandas code>"}'
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            text = (response.text or "").strip()
            # Try to parse JSON from the response
            text = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(text)
            return parsed.get("sql", ""), parsed.get("pandas", "")
        except Exception as exc:
            logger.error("Gemini code generation failed: %s", exc)
            return "", ""

    def plan_analysis(
        self,
        question: str,
        schema_info: str,
    ) -> dict[str, Any]:
        """Ask Gemini to plan the analysis steps (intent, columns, etc.)."""
        if not self.available:
            return {}

        prompt = (
            "You are a data analyst. Given the dataset schema and question, "
            "identify the analysis plan.\n\n"
            f"Schema:\n{schema_info}\n\n"
            f"Question: {question}\n\n"
            "Respond in this exact JSON format (no markdown, no explanation):\n"
            "{\n"
            '  "intent": "aggregation|comparison|ranking|trend|anomaly|code_generation|general_info|correlation",\n'
            '  "target_columns": ["col1", "col2"],\n'
            '  "group_by": ["col"] or null,\n'
            '  "agg_func": "sum|mean|count|max|min" or null,\n'
            '  "filters": [{"column": "col", "operator": "==", "value": "val"}] or [],\n'
            '  "sort_direction": "asc|desc" or null,\n'
            '  "limit": 10 or null\n'
            "}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            text = (response.text or "").strip()
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as exc:
            logger.error("Gemini analysis planning failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _build_explanation_prompt(
        self,
        question: str,
        results_summary: str,
        schema_info: str,
        conversation_history: list[dict[str, Any]] | None,
    ) -> str:
        parts: list[str] = [
            "You are an expert data analyst providing clear, actionable insights. ",
            "Be concise and use bullet points when helpful.\n\n",
        ]

        if conversation_history:
            parts.append("Conversation so far:\n")
            for msg in conversation_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                parts.append(f"  {role}: {content}\n")
            parts.append("\n")

        parts.extend(
            [
                f"Dataset schema:\n{schema_info}\n\n",
                f"User question: {question}\n\n",
                f"Calculated results:\n{results_summary}\n\n",
                "Provide a clear, insightful explanation of these results. "
                "Mention key takeaways, notable patterns, and potential actions.",
            ]
        )
        return "".join(parts)

    @staticmethod
    def _fallback_explanation(question: str, results_summary: str) -> str:
        """Template-based explanation when LLM is unavailable."""
        return (
            f"**Analysis Results**\n\n"
            f"Based on your question: *\"{question}\"*\n\n"
            f"{results_summary}\n\n"
            f"*For richer natural-language insights, configure a Gemini API key.*"
        )
