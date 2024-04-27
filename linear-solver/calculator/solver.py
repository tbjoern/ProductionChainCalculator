"""
Production Chain LinProg

given things t1 .. tn
and recipes r1 ... rm

each recipe consumes some things and produces some things
the amount of ti produced or consumed by rj is defined as rj_ti, with rj_ti > 0 when rj produces ti and rj_ti < 0 when rj consumes ti

let c_ri define how often recipe ri is used, c_ri >= 0

lets also P_ti define how much of ti is available
let R_ti define how much of ti is required

for all i, we can assert that

P_ti - R_ti + (for all j in i..m): rj_ti * c_rj >= 0

P_ti and R_ti are constants, therefore

(for all j in i..m): rj_ti * c_rj >= R_ti - P_ti

reformulating this as a matrix:

A_ij = -rj_ti
cv_i = c_ri
b_i = P_ti - R_ti


A * cv <= b
0 <= cv

minimizing sum(cv_i)

Caveats:
Every thing needs a recipe rj that produces it.
For inputs that means we need a placeholder recipe which 'produces' only that input and has an optimization weight of 0.
Each run will use a subset of the recipes for optimization. We need to figure out which items are pure inputs, which are all things that are inputs and not simultaneously outputs.
This also allows the user to specify that some items are pure inputs, even when a factory produces them (e.g. as a side product)


TODO: update this text with the output recipes. Generate an output recipe and use equality instead of <=. Then optimizer is forced to balance overproduction with output recipe, allowing us to
- mimize overproduction by using 1 as optimization weight
- ignore overproduction by using 0
- encourage overproduction (maximize given the inputs) by using -1
"""

from scipy.optimize import linprog
from dataclasses import dataclass
from collections import defaultdict
import logging
from .recipe import Recipe

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


@dataclass
class OptimizerResult:
    solvable: bool
    recipe_count: dict[str, int]
    produced: dict[str, int]
    consumed: dict[str, int]


def produce_required_items(
    recipes: list[Recipe],
    require: dict[str, int] = {},
    maximize: list[str] = [],
    provide: dict[str, int] = {},
    limit: dict[str, int] = {},
    ignore: list[str] = [],
    conserve: list[str] = [],
) -> OptimizerResult:
    maximize = set(maximize)
    ignore = set(ignore)
    conserve = set(conserve)

    items = set()

    # find names of items specified anywhere in input
    for item in require:
        items.add(item)

    for item in provide:
        items.add(item)

    for item in limit:
        items.add(item)

    for recipe in recipes:
        for input in recipe.inputs:
            items.add(input)
        for output in recipe.outputs:
            items.add(output)

    items = sorted(items)
    used_recipes = [*recipes]

    # figure out which inputs dont have a producing recipe
    # these will be inputs to the production line
    # we need to generate a 'generating' recipe for them to allow the linprog
    # to create the needed amount
    pure_inputs = set(items)

    for recipe in used_recipes:
        for output in recipe.outputs:
            pure_inputs.discard(output)

    input_recipes = set()
    for item in pure_inputs:
        # dont generate a pure input recipe for input-limited items
        if item in limit:
            continue
        input_recipe = Recipe(inputs={}, outputs={item: 1})
        used_recipes.append(input_recipe)
        input_recipes.add(input_recipe)

    # generate an output recipe for all outputs
    # output recipes control optimization of byproducts
    # see recipe_weights
    all_outputs = set()
    for recipe in used_recipes:
        for output in recipe.outputs:
            all_outputs.add(output)

    output_recipes = set()
    for output in all_outputs:
        output_recipe = Recipe(inputs={output: 1}, outputs={})
        used_recipes.append(output_recipe)
        output_recipes.add(output_recipe)

    # sums up the inputs + outputs of all recipes, by item
    # cell i,j contains how many of item i recipe j consumes (negative) or produces (positive)
    recipe_item_sums = list()
    for item in items:
        row = list()
        for recipe in used_recipes:
            row.append(recipe.get_item_count(item))
        logger.debug(f"{item}: {row}")
        recipe_item_sums.append(row)

    # positive: factory produces as intended output
    # negative: factory can consume as input
    # byproducts will be 'consumed' by an overflow output recipe
    target_item_counts = list()
    for item in items:
        target_item_count = (
            require.get(item, 0) - provide.get(item, 0) - limit.get(item, 0)
        )
        target_item_counts.append(target_item_count)

    # objective coefficients
    recipe_weights = list()
    for recipe in used_recipes:
        if recipe in input_recipes:
            item = list(recipe.outputs.keys())[0]
            if item in conserve:
                # try to minimize input
                recipe_weights.append(1)
            else:
                # dont optimize - take as many as is required
                recipe_weights.append(0)
        elif recipe in output_recipes:
            item = list(recipe.inputs.keys())[0]
            if item in maximize:
                # enourage producing as much of this output as possible
                recipe_weights.append(-1)
            elif item in ignore or item in provide or item in limit:
                # allow/ignore any overflow
                recipe_weights.append(0)
            else:
                # try to mimize byproduct
                recipe_weights.append(1)
        else:
            recipe_weights.append(0)

    logger.debug(recipe_item_sums)
    logger.debug(target_item_counts)
    logger.debug(recipe_weights)
    result = linprog(recipe_weights, A_eq=recipe_item_sums, b_eq=target_item_counts)

    recipe_counts = {}
    total_inputs = defaultdict(lambda: 0)
    total_outputs = defaultdict(lambda: 0)
    if result.success:
        for recipe_count, recipe in zip(result.x, used_recipes):
            if recipe not in output_recipes and recipe not in input_recipes:
                recipe_counts[recipe] = recipe_count

            if recipe not in output_recipes:
                for item, count in recipe.inputs.items():
                    total_inputs[item] += count * recipe_count

            if recipe not in input_recipes:
                for item, count in recipe.outputs.items():
                    total_outputs[item] += count * recipe_count

            inputs = []
            for input_name, input_count in recipe.inputs.items():
                inputs.append(f"{input_count * recipe_count:.1f} x {input_name}")
            outputs = []
            for output_name, output_count in recipe.outputs.items():
                outputs.append(f"{output_count * recipe_count:.1f} x {output_name}")
            logger.debug(
                f"{recipe_count:.1f} x {recipe.serialized}: {' + '.join(inputs)} --> {' + '.join(outputs)}"
            )

    else:
        logger.debug("Failed to optimize")
        logger.debug(result)
    return OptimizerResult(
        solvable=result.success,
        recipe_count=recipe_counts,
        consumed=total_inputs,
        produced=total_outputs,
    )
