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


recipes = {
    # "iron-smelting": Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1}),
    # "copper-smelting": Recipe(inputs={"copper-ore": 1}, outputs={"copper-plate": 1}),
    # "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1}),
    # "copper-wire-assembly": Recipe(inputs={"copper-plate": 1}, outputs={"copper-wire": 2}),
    # "electronic-circuits-assembly": Recipe(inputs={"iron-plate": 1, "copper-wire": 3}, outputs={"electronic-circuit": 1}),
    "advanced-oil-processing": Recipe(
        inputs={"crude-oil": 100, "water": 50},
        outputs={"heavy-oil": 25, "light-oil": 45, "petroleum-gas": 55},
    ),
    "light-oil-cracking": Recipe(
        inputs={"light-oil": 30, "water": 30}, outputs={"petroleum-gas": 20}
    ),
    "heavy-oil-cracking": Recipe(
        inputs={"heavy-oil": 40, "water": 30}, outputs={"light-oil": 30}
    ),
}


def produce_required_items(
    recipes: dict[str, Recipe],
    require: dict[str, int] = {},
    maximize: list[str] = [],
    provide: dict[str, int] = {},
    limit: dict[str, int] = {},
    optimize_for: list[str] = [],
    ignore: list[str] = [],
):
    maximize = set(maximize)
    optimize_for = set(optimize_for)
    ignore = set(ignore)

    items = set()

    # find names of items specified anywhere in input
    for item in require:
        items.add(item)

    for item in provide:
        items.add(item)

    for item in limit:
        items.add(item)

    for recipe in recipes.values():
        for input in recipe.inputs:
            items.add(input)
        for output in recipe.outputs:
            items.add(output)

    items = sorted(items)
    used_recipes = {**recipes}

    # figure out which inputs dont have a producing recipe
    # these will be inputs to the production line
    # we need to generate a 'generating' recipe for them to allow the linprog
    # to create the needed amount
    pure_inputs = set(items)

    for recipe in used_recipes.values():
        for output in recipe.outputs:
            pure_inputs.discard(output)

    for item in pure_inputs:
        # dont generate a pure input recipe for input-limited items
        if item in limit:
            continue
        input_recipe = Recipe(inputs={}, outputs={item: 1})
        used_recipes[item] = input_recipe

    # generate an output recipe for all outputs
    all_outputs = set()
    for recipe in used_recipes.values():
        for output in recipe.outputs:
            all_outputs.add(output)

    output_recipes = set()
    for output in all_outputs:
        output_recipe = Recipe(inputs={output: 1}, outputs={})
        used_recipes[f"sink-{output}"] = output_recipe
        output_recipes.add(f"sink-{output}")

    A_ub = list()
    for item in items:
        row = list()
        for recipe in used_recipes.values():
            # Aub uses -rj_ti, because linprog needs <= instead of >=
            row.append(-recipe.get_item_count(item))
        print(f"{item}: {row}")
        A_ub.append(row)

    b_ub = list()

    for item in items:
        target_item_count = (
            provide.get(item, 0) + limit.get(item, 0) - require.get(item, 0)
        )
        b_ub.append(target_item_count)

    # objective coefficients
    c = list()
    for recipe in used_recipes:
        if recipe in pure_inputs:
            # dont optimize for "pure input recipes" - take as many as is required
            c.append(0)
        elif recipe in output_recipes:
            item = list(used_recipes[recipe].inputs.keys())[0]
            if item in maximize:
                c.append(-1)
            elif item in ignore:
                c.append(0)
            else:
                c.append(1)
        else:
            c.append(0)

    print(b_ub)
    print(c)
    result = linprog(c, A_eq=A_ub, b_eq=b_ub)
    print(result)

    if result.success:
        for recipe_count, (recipe_name, recipe) in zip(result.x, used_recipes.items()):
            inputs = []
            for input_name, input_count in recipe.inputs.items():
                inputs.append(f"{input_count * recipe_count:.1f} x {input_name}")
            outputs = []
            for output_name, output_count in recipe.outputs.items():
                outputs.append(f"{output_count * recipe_count:.1f} x {output_name}")
            print(
                f"{recipe_count:.1f} x {recipe_name}: {' + '.join(inputs)} --> {' + '.join(outputs)}"
            )
    else:
        print("Failed to optimize")
        print(result)


produce_required_items(
    recipes={
        "advanced-oil-processing": Recipe(
            inputs={"crude-oil": 100, "water": 50},
            outputs={"heavy-oil": 25, "light-oil": 45, "petroleum-gas": 55},
        ),
        "light-oil-cracking": Recipe(
            inputs={"light-oil": 30, "water": 30}, outputs={"petroleum-gas": 20}
        ),
        "heavy-oil-cracking": Recipe(
            inputs={"heavy-oil": 40, "water": 30}, outputs={"light-oil": 30}
        ),
    },
    maximize=["petroleum-gas"],
    limit={"water": 1000},
)

produce_required_items(
    recipes={
        "advanced-oil-processing": Recipe(
            inputs={"crude-oil": 100, "water": 50},
            outputs={"heavy-oil": 25, "light-oil": 45, "petroleum-gas": 55},
        ),
        "light-oil-cracking": Recipe(
            inputs={"light-oil": 30, "water": 30}, outputs={"petroleum-gas": 20}
        ),
        "heavy-oil-cracking": Recipe(
            inputs={"heavy-oil": 40, "water": 30}, outputs={"light-oil": 30}
        ),
    },
    require={"petroleum-gas": 110},
    ignore=["water"],
)

produce_required_items(
    recipes={
        "copper-smelting": Recipe(
            inputs={"copper-ore": 1}, outputs={"copper-plate": 1}
        ),
        "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1}),
        "copper-wire-assembly": Recipe(
            inputs={"copper-plate": 1}, outputs={"copper-wire": 2}
        ),
        "electronic-circuits-assembly": Recipe(
            inputs={"iron-plate": 1, "copper-wire": 3},
            outputs={"electronic-circuit": 1},
        ),
    },
    provide={"iron-plate": 15, "copper-plate": 10},
    limit={"iron-plate": 0},
    maximize=["electronic-circuit"],
    require={"gear": 2},
)
