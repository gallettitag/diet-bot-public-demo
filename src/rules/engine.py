"""
Diet rule engine — deterministic safety evaluation.

Evaluates each ingredient against the diet rule database using a
four-strategy resolution order. Returns a RuleVerdict for every
ingredient, aggregated into a single meal-level verdict.

Resolution order:
  1. Direct name match
  2. Alias resolution via food ontology
  3. Ancestor traversal up the ontology tree
  4. No match → UNCERTAIN (never SAFE)

Full implementation is maintained privately.
"""

from __future__ import annotations

from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession


class VerdictStatus(IntEnum):
    """
    Verdict priority. Higher value = more restrictive.
    Meal verdict is always max(ingredient verdicts).
    """
    SAFE = 0
    UNCERTAIN = 1
    CAUTION = 2
    AVOID = 3


@dataclass
class RuleVerdict:
    ingredient: str
    status: VerdictStatus
    rule_id: Optional[int] = None
    source_text: Optional[str] = None
    resolution_path: list[str] = field(default_factory=list)
    """
    resolution_path records how the verdict was reached, e.g.:
      ["direct_match"]
      ["alias_resolution", "aged_cheese"]
      ["ancestor_traversal", "cheddar", "hard_cheese", "aged_cheese"]
      ["no_match"]
    Used in the audit trail and for debugging resolution failures.
    """


@dataclass
class MealVerdict:
    overall_status: VerdictStatus
    ingredient_verdicts: list[RuleVerdict]
    flagged_ingredients: list[RuleVerdict]

    @classmethod
    def aggregate(cls, verdicts: list[RuleVerdict]) -> "MealVerdict":
        """
        Aggregate ingredient verdicts into a single meal verdict.
        The meal verdict is always the most restrictive ingredient verdict.
        A meal with one AVOID ingredient is an AVOID meal.
        """
        # Implementation maintained privately
        raise NotImplementedError


class RuleEngine:
    """
    Deterministic rule evaluator. Stateless — all state lives in the database.

    Deliberately does not use LLM reasoning for safety verdicts.
    LLMs are used only upstream (ingredient extraction) and downstream
    (explanation generation). The verdict itself must be deterministic
    and auditable.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(
        self,
        ingredient: str,
        diet_name: str,
    ) -> RuleVerdict:
        """
        Evaluate a single ingredient against the named diet's rules.
        Tries resolution strategies in order, returns on first match.
        Unknown ingredients always return UNCERTAIN — never SAFE.
        """
        # Strategy 1: direct name match
        verdict = await self._direct_match(ingredient, diet_name)
        if verdict:
            return verdict

        # Strategy 2: alias resolution via food ontology
        verdict = await self._alias_resolution(ingredient, diet_name)
        if verdict:
            return verdict

        # Strategy 3: ancestor traversal up the ontology tree
        verdict = await self._ancestor_traversal(ingredient, diet_name)
        if verdict:
            return verdict

        # Strategy 4: no match — return UNCERTAIN, never SAFE
        return RuleVerdict(
            ingredient=ingredient,
            status=VerdictStatus.UNCERTAIN,
            resolution_path=["no_match"],
        )

    async def evaluate_meal(
        self,
        ingredients: list[str],
        diet_name: str,
    ) -> MealVerdict:
        """
        Evaluate all ingredients in a meal and aggregate into a meal verdict.
        Runs ingredient evaluations concurrently where possible.
        """
        # Implementation maintained privately
        raise NotImplementedError

    async def _direct_match(
        self,
        ingredient: str,
        diet_name: str,
    ) -> Optional[RuleVerdict]:
        """Exact case-insensitive lookup in diet_rules table."""
        raise NotImplementedError

    async def _alias_resolution(
        self,
        ingredient: str,
        diet_name: str,
    ) -> Optional[RuleVerdict]:
        """
        Resolve ingredient to canonical food_item via alias table,
        then look up rule by food_item_id.
        """
        raise NotImplementedError

    async def _ancestor_traversal(
        self,
        ingredient: str,
        diet_name: str,
    ) -> Optional[RuleVerdict]:
        """
        Walk up the food ontology tree from the ingredient's food_item,
        checking for a rule at each ancestor level.
        Stops at first match (most specific ancestor wins).
        """
        raise NotImplementedError
