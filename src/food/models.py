"""
Food ontology — hierarchical food taxonomy.

Enables rule inheritance: a rule on "aged cheese" automatically applies
to cheddar, parmesan, brie, and any other food whose ancestor chain
includes "aged cheese".

The tree is self-referential: each FoodItem has an optional parent_id
pointing to a more general category. Aliases allow the same food_item
to be reached by many common names ("soy sauce", "shoyu", "tamari"
all resolve to the same item).

Full implementation is maintained privately.
"""

from __future__ import annotations
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class FoodItem(Base):
    """
    Self-referential tree node representing a food category or specific food.

    Example hierarchy:
      dairy
      └── cheese
          └── aged cheese
              ├── cheddar
              ├── parmesan
              └── brie

    A rule on "aged cheese" is inherited by all descendants.
    A rule on "cheddar" overrides the ancestor rule for cheddar specifically.
    """
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("food_items.id"), nullable=True
    )

    parent: Mapped[Optional["FoodItem"]] = relationship(
        "FoodItem", remote_side="FoodItem.id", back_populates="children"
    )
    children: Mapped[list["FoodItem"]] = relationship(
        "FoodItem", back_populates="parent"
    )
    aliases: Mapped[list["FoodAlias"]] = relationship(
        "FoodAlias", back_populates="food_item"
    )


class FoodAlias(Base):
    """
    Alternative names for a food item.
    Enables resolution of colloquial names to canonical food items.

    Example: "shoyu", "tamari", "soy sauce" → soy_sauce (food_item_id=42)
    """
    __tablename__ = "food_aliases"
    __table_args__ = (UniqueConstraint("alias", name="uq_food_alias"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    food_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("food_items.id"), nullable=False
    )

    food_item: Mapped[FoodItem] = relationship("FoodItem", back_populates="aliases")
