from typing import TypeAlias
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class Recipe:
    inputs: dict[str, int]
    outputs: dict[str, int]

    def get_input_count(self, input) -> int:
        return self.inputs.get(input, 0)

    def get_output_count(self, output) -> int:
        return self.outputs.get(output, 0)

    def get_item_count(self, item) -> int:
        return self.get_output_count(item) - self.get_input_count(item)


def parse_defs(item_string) -> dict:
    items = {}

    if item_string == "":
        return items

    item_defs = item_string.split("+")
    for item_def in item_defs:
        tokens = item_def.split()
        if len(tokens) == 1:
            name = tokens[0].strip()
            count = 1
        else:
            count, name = tokens
            count = float(count.strip())
            name = name.strip()
        items[name] = count
    return items


def parse_line(line) -> tuple[str, Recipe]:
    input_string, output_string = line.split("-->")
    inputs = parse_defs(input_string.strip())
    outputs = parse_defs(output_string.strip())
    return Recipe(inputs=inputs, outputs=outputs)


def parse_spec(lines, ignore_errors=True) -> list[Recipe]:
    recipes = []

    for line in lines:
        line = line.strip()
        if len(line) == 0 or line[0] == "#":
            continue
        try:
            recipe = parse_line(line)
            recipes.append(recipe)
        except Exception as e:
            logger.error(f"Failed to parse line {line}")
            logger.exception(e)
            if not ignore_errors:
                raise e

    return recipes


class RecipeBook:
    def __init__(self, recipes: list[Recipe]):
        self.recipes = recipes

    def find_producers_of(self, item) -> list[Recipe]:
        producers = []
        for recipe in self.recipes:
            if item in recipe.outputs:
                producers.append(recipe)

        return producers

    def get_all_items(self) -> set[str]:
        items = set()
        for recipe in self.recipes:
            for item in recipe.inputs:
                items.add(item)
            for item in recipe.outputs:
                items.add(item)
        return items

    def get_pure_inputs(self) -> list[str]:
        pure_inputs = self.get_all_items()
        for recipe in self.recipes:
            for item in recipe.outputs:
                pure_inputs.discard(item)
        return pure_inputs

    def add_recipe(self, recipe: Recipe):
        self.recipes.append(recipe)
