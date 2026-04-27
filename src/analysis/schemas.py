"""
Analysis API — request/response schemas and route definitions.
"""

from __future__ import annotations
from enum import str, auto
from typing import Optional
from pydantic import BaseModel, Field


class VerdictStatus(str):
    SAFE = "safe"
    CAUTION = "caution"
    AVOID = "avoid"
    UNCERTAIN = "uncertain"


class IngredientVerdict(BaseModel):
    ingredient: str
    status: str
    source_text: Optional[str] = None
    resolution_path: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    chunk_id: int
    source: str
    page: int
    text_excerpt: str


class FoodAnalysisRequest(BaseModel):
    query: str = Field(
        ...,
        description="Natural language food query, e.g. 'chicken teriyaki with rice'",
        min_length=1,
        max_length=500,
    )
    diet_name: str = Field(
        default="tyramine_free",
        description="Name of the dietary restriction to evaluate against",
    )


class FoodAnalysisResponse(BaseModel):
    query: str
    diet_name: str
    overall_verdict: str
    ingredient_verdicts: list[IngredientVerdict]
    explanation: str
    citations: list[Citation]
    latency_ms: float


class RecipeAnalysisRequest(BaseModel):
    ingredients: list[str] = Field(
        ...,
        description="List of ingredients to evaluate directly",
        min_length=1,
    )
    diet_name: str = Field(default="tyramine_free")


class RecipeGenerationRequest(BaseModel):
    diet_name: str = Field(default="tyramine_free")
    meal_type: Optional[str] = Field(
        None,
        description="breakfast, lunch, dinner, snack",
    )
    cuisine: Optional[str] = Field(
        None,
        description="Optional cuisine preference, e.g. 'italian', 'japanese'",
    )
    exclusions: list[str] = Field(
        default_factory=list,
        description="Additional ingredients to exclude beyond diet rules",
    )
