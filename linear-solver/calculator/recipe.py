from typing import TypeAlias, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class Recipe:
    inputs: dict[str, int]
    outputs: dict[str, int]
    extras: dict[str, Any] = field(default_factory=dict)
    serialized: str = field(init=False)

    def __post_init__(self):
        tokens = []
        for item, count in self.inputs.items():
            tokens.append(f"{count} {item}")
        inputs = " + ".join(tokens)

        tokens = []
        for item, count in self.outputs.items():
            tokens.append(f"{count} {item}")
        outputs = " + ".join(tokens)

        tokens = []
        for extra, value in self.extras.items():
            tokens.append(f"{extra}: {value}")
        extras = ", ".join(tokens)

        tokens = [inputs, "-->", outputs]
        if extras != "":
            tokens.extend([";", extras])
        self.serialized = " ".join(tokens)

    def __hash__(self):
        return hash(self.serialized)

    def __str__(self):
        return self.serialized

    def get_input_count(self, input) -> int:
        return self.inputs.get(input, 0)

    def get_output_count(self, output) -> int:
        return self.outputs.get(output, 0)

    def get_item_count(self, item) -> int:
        return self.get_output_count(item) - self.get_input_count(item)


def parse_def(item_def):
    tokens = item_def.split()
    if len(tokens) == 1:
        name = tokens[0].strip()
        count = 1
    else:
        count, name = tokens
        count = float(count.strip())
        name = name.strip()
    return name, count


def parse_defs(item_string) -> dict:
    items = {}

    if item_string == "":
        return items

    item_defs = item_string.split("+")
    for item_def in item_defs:
        name, count = parse_def(item_def)
        items[name] = count
    return items


def parse_extras(extras_spec) -> dict[str, Any]:
    extras = {}
    extras_defs = extras_spec.split(",")
    for extra_def in extras_defs:
        name, value = extra_def.split(":")
        name = name.strip()
        value = value.strip()
        try:
            value = float(value)
        except:
            pass
        extras[name] = value
    return extras


def parse_line(line) -> tuple[str, Recipe]:
    recipe_spec, *extra_spec = line.split(";", maxsplit=1)
    if len(extra_spec) > 0:
        extras = parse_extras(extra_spec[0])
    else:
        extras = {}

    input_string, output_string = recipe_spec.split("-->")
    inputs = parse_defs(input_string.strip())
    outputs = parse_defs(output_string.strip())
    return Recipe(inputs=inputs, outputs=outputs, extras=extras)


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

    def __len__(self):
        return len(self.recipes)

    def __iter__(self):
        return iter(self.recipes)

    def all(self) -> list[Recipe]:
        return self.recipes

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

    def get_outputs(self) -> list[str]:
        outputs = set()
        for recipe in self.recipes:
            for item in recipe.outputs:
                outputs.add(item)
        return outputs
