from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import ChecklistItem, RecipePreflightResponse, RecipeSummary, SystemState
from .safety import ALLOWED_AI_STEPS, FORBIDDEN_AI_STEPS


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    description: str
    locked: bool
    requires_homing: bool
    steps: list[dict[str, Any]]


class RecipeEngine:
    def __init__(self, recipes_dir: Path):
        self.recipes_dir = recipes_dir

    def list_recipes(self) -> list[RecipeSummary]:
        return [
            RecipeSummary(id=recipe.id, name=recipe.name, description=recipe.description, locked=recipe.locked)
            for recipe in self._load_all()
        ]

    def get(self, recipe_id: str) -> Recipe:
        for recipe in self._load_all():
            if recipe.id == recipe_id:
                return recipe
        raise ValueError("unknown_recipe")

    def preflight(self, recipe_id: str, state: SystemState) -> RecipePreflightResponse:
        try:
            recipe = self.get(recipe_id)
        except ValueError:
            return RecipePreflightResponse(
                recipe_id=recipe_id,
                ok=False,
                reasons=["unknown_recipe"],
                checks=[
                    ChecklistItem(
                        id="recipe_exists",
                        label="Recipe exists",
                        ok=False,
                        detail="unknown_recipe",
                    )
                ],
            )
        reasons: list[str] = []
        checks: list[ChecklistItem] = []
        if recipe.locked:
            reasons.append("recipe_locked")
        checks.append(
            ChecklistItem(
                id="recipe_unlocked",
                label="Recipe is unlocked",
                ok=not recipe.locked,
                detail="locked" if recipe.locked else "ok",
            )
        )
        if state.estop:
            reasons.append("estop_active")
        checks.append(
            ChecklistItem(
                id="estop_clear",
                label="ESTOP is clear",
                ok=not state.estop,
                detail="active" if state.estop else "clear",
            )
        )
        if recipe.requires_homing and not state.homed:
            reasons.append("not_homed")
        checks.append(
            ChecklistItem(
                id="homed",
                label="CookBot is homed",
                ok=(not recipe.requires_homing) or state.homed,
                detail="required" if recipe.requires_homing and not state.homed else "ok",
            )
        )
        forbidden_steps: list[str] = []
        for step in recipe.steps:
            step_type = str(step.get("type"))
            if step_type in FORBIDDEN_AI_STEPS or step_type not in ALLOWED_AI_STEPS:
                reasons.append(f"forbidden_recipe_step:{step_type}")
                forbidden_steps.append(step_type)
        checks.append(
            ChecklistItem(
                id="steps_allowed",
                label="Recipe steps are allow-listed",
                ok=not forbidden_steps,
                detail=",".join(forbidden_steps) if forbidden_steps else "ok",
            )
        )
        checks.append(
            ChecklistItem(
                id="no_heat_steps",
                label="Recipe has no heating or hazardous steps",
                ok=not forbidden_steps,
                detail="ok" if not forbidden_steps else "forbidden_steps_present",
            )
        )
        return RecipePreflightResponse(recipe_id=recipe_id, ok=not reasons, reasons=reasons, checks=checks)

    def _load_all(self) -> list[Recipe]:
        recipes: list[Recipe] = []
        if not self.recipes_dir.exists():
            return recipes
        for path in sorted(self.recipes_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            recipes.append(
                Recipe(
                    id=str(data["id"]),
                    name=str(data.get("name", data["id"])),
                    description=str(data.get("description", "")),
                    locked=bool(data.get("locked", False)),
                    requires_homing=bool(data.get("requires_homing", True)),
                    steps=list(data.get("steps", [])),
                )
            )
        return recipes
