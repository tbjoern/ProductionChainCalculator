from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

Item = int


@dataclass
class ItemAmount:
    amount: int
    item: Item

    def __repr__(self):
        global item_lookup
        item_name = item_lookup.name_for(self.item)
        return f"ItemAmount(amount={self.amount}, item={item_name})"

@dataclass
class ItemLookup:
    name_to_item: Dict[str, Item]
    item_to_name: List[str]

    @classmethod
    def from_name_list(cls, name_list: List[str]) -> "ItemLookup":
        sorted_names = sorted(name_list)
        name_to_item = {name:i for i,name in enumerate(sorted_names)}
        return cls(name_to_item, sorted_names)

    def item_for(self, name):
        return self.name_to_item.get(name)

    def name_for(self, item):
        if item >= len(self.item_to_name):
            logger.warning(f"Could not find name for item {item}")
            return str(item)
        return self.item_to_name[item]

item_lookup = ItemLookup({}, [])

@dataclass
class Recipe:
    result: ItemAmount
    ingredients: List[ItemAmount]
    time: int
    factory: Item


def load_recipes(filename: Path, parser) -> Tuple[ItemLookup, Dict[Item, Recipe]]:
    item_names = []
    raw_recipes = []
    with open(filename, 'r') as fp:
        for i, line in enumerate(fp):
            tokens = line.split(';')
            if len(tokens) < 3:
                parser.error(f"Parse error in {filename}:{i} - Too few entries")
            item_token, time, factory, *ingredient_tokens = tokens

            item_token = item_token.split(',')
            if len(item_token) == 1:
                item_amount = 1
                item_name = item_token[0]
            elif len(item_token) == 2:
                item_amount, item_name = item_token
                try:
                    item_amount = int(item_amount)
                except ValueError:
                    parser.error(f"Parse error in {filename}:{i} - Item amount is not an int")
            else:
                parser.error(f"Parse error in {filename}:{i} - Item needs amount and name: {item_token}")

            item_name = item_name.strip().lower()
            if len(item_name) == 0:
                parser.error(f"Parse error in {filename}:{i} - Item name is empty")

            factory = factory.strip()
            if len(factory) == 0:
                parser.error(f"Parse error in {filename}:{i} - Factory name is empty")

            item_names.append(item_name)

            try:
                time = float(time)
            except ValueError:
                parser.error(f"Parse error in {filename}:{i} - Failed to parse time, {time} is not an int")

            ingredients = []
            for itoken in ingredient_tokens:
                itoken_split = itoken.split(',')

                if len(itoken_split) == 1:
                    amount = 1
                    ingredient_item = itoken_split[0]
                elif len(itoken_split) == 2:
                    amount, ingredient_item =  itoken_split
                    try:
                        amount = int(amount)
                    except ValueError:
                        parser.error(f"Parse error in {filename}:{i} - Failed to parse ingredient {itoken}, amount {amount} is not an int")
                else:
                    parser.error(f"Parse error in {filename}:{i} - Failed to parse ingredient {itoken}")

                ingredient_item = ingredient_item.strip().lower()
                if len(ingredient_item) == 0:
                    parser.error(f"Parse error in {filename}:{i} - Failed to parse ingredient {itoken}, item {ingredient_item} is empty")
                ingredients.append((amount, ingredient_item))

            raw_recipes.append(((item_amount, item_name), ingredients, time, factory))
    
    item_lookup = ItemLookup.from_name_list(item_names)
    
    recipes = {}
    for (item_amount, item_name), raw_ingredients, time, factory in raw_recipes:
        item = item_lookup.item_for(item_name)
        ingredients = []
        for amount, ingredient_item_name in raw_ingredients:
           ingredient_item = item_lookup.item_for(ingredient_item_name)
           ingredients.append(ItemAmount(amount, ingredient_item))
        recipes[item] = Recipe(ItemAmount(item_amount, item), ingredients, time, factory)

    return item_lookup, recipes

class Calculator:
    def __init__(self, item_lookup, recipes):
        self.item_lookup = item_lookup
        self.recipes = recipes
        self.item_tracker = [0 for _ in range(len(item_lookup.item_to_name))]

    def make_item(self, item, amount):
        self.item_tracker[item] += amount

        recipe = self.recipes[item]
        recipe_yield = recipe.result.amount
        times_recipe_needed = float(amount) / recipe_yield
        for ingredient in recipe.ingredients:
            self.make_item(ingredient.item, ingredient.amount * times_recipe_needed)

    def reset(self):
        self.item_tracker = [0 for _ in range(len(item_lookup.item_to_name))]

    def __str__(self):
        lines = []
        for item, amount in enumerate(self.item_tracker):
            if amount > 0:
                lines.append(f"{self.item_lookup.name_for(item)}: {amount}")
        return "\n".join(lines)


def main():
    global item_lookup
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--recipes', '-r', required=True, type=Path)

    args = parser.parse_args()

    if not args.recipes.is_file():
        parser.error(f"{args.recipes} is not a file")

    item_lookup, recipes = load_recipes(args.recipes, parser)

    print(item_lookup)
    print(recipes)

    calculator = Calculator(item_lookup, recipes)
    
    while True:
        try:
            item_to_produce = input("What should be produced: ")
            item_amount = input("How many: ")
        except EOFError:
            break

        item_to_produce = item_to_produce.strip().lower()

        if item_to_produce == "exit" or item_to_produce == "":
            break

        item = item_lookup.item_for(item_to_produce.strip())
        if item is None:
            print(f"Could not find {item}, choose one of")
            print("\n".join(item_lookup.item_to_name))
            continue

        try:
            item_amount = int(item_amount)
        except ValueError:
            print(f"Is not a number: {item_amount}")
            continue

        calculator.make_item(item, item_amount)
        print(str(calculator))
        calculator.reset()


if __name__ == "__main__":
    main()
