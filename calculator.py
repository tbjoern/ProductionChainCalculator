from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Sequence
import logging
import math

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

Item = int

class ParseError(ValueError):
    pass

@dataclass
class ItemAmount:
    amount: int
    item: Item

    def __repr__(self):
        global item_lookup
        item_name = item_lookup.name_for(self.item)
        return f"ItemAmount(amount={self.amount}, item={item_name})"

    @classmethod
    def resolve(cls, amount, name):
        item = item_lookup.item_for(name)
        return cls(amount, item)

@dataclass
class ItemLookup:
    name_to_item: Dict[str, Item]
    item_to_name: List[str]

    @classmethod
    def from_name_list(cls, name_list: Sequence[str]) -> "ItemLookup":
        sorted_names = sorted(list(name_list))
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
    results: List[ItemAmount]
    ingredients: List[ItemAmount]
    time: int
    factory: Item

    def get_amount(self, item) -> int:
        for result in self.results:
            if item == result.item:
                return result.amount
        return None

def parse_item_amount(item_token):
    item_token = item_token.split(',')
    if len(item_token) == 1:
        item_amount = 1
        item_name = item_token[0]
    elif len(item_token) == 2:
        item_amount, item_name = item_token
        try:
            item_amount = int(item_amount)
        except ValueError:
            raise ParseError(f"Item amount is not an int - {item_token}")
    else:
        raise ParseError(f"Item needs amount and name - {item_token}")

    item_name = item_name.strip().lower()
    if len(item_name) == 0:
        raise ParseError(f"Item name is empty - {item_token}")

    return (item_amount, item_name)

def load_recipes(filename: Path, parser) -> Tuple[ItemLookup, Dict[Item, Recipe]]:
    global item_lookup
    item_names = set()
    raw_recipes = []
    with open(filename, 'r') as fp:
        try:
            for i, line in enumerate(fp):
                line = line.strip()
                if len(line) == 0:
                    continue
                if line[0] == '#':
                    continue
                tokens = line.split(';')
                if len(tokens) < 3:
                    raise ParseError("Too few entries in line - {line}")
                result_tokens, time, factory, *ingredient_tokens = tokens

                results = [parse_item_amount(token) for token in result_tokens.split('+')]

                for amount, item_name in results:
                    item_names.add(item_name)

                try:
                    time = float(time)
                except ValueError:
                    raise ParseError(f"Failed to parse time, {time} is not an int")

                factory = factory.strip()
                if len(factory) == 0:
                    raise ParseError(f"Factory name is empty")

                ingredients = [parse_item_amount(token) for token in ingredient_tokens]

                raw_recipes.append((results, ingredients, time, factory))
        except ParseError as e:
            parser.error("Parse error in {filename}:{i} - {e}")
    
    item_lookup = ItemLookup.from_name_list(item_names)
    
    recipes = {}
    for raw_results, raw_ingredients, time, factory in raw_recipes:
        ingredients = [ItemAmount.resolve(*r) for r in raw_ingredients]
        results = [ItemAmount.resolve(*r) for r in raw_results]
        for result in results:
            recipes[result.item] = Recipe(results, ingredients, time, factory)

    print(f"Sucessfully loaded {filename.name}")

    return item_lookup, recipes

class Calculator:
    def __init__(self, item_lookup, recipes):
        self.item_lookup = item_lookup
        self.recipes = recipes
        self.item_tracker = None
        self.additional_items = None
        self.reset()

    def _make_item_list(self):
        return [0 for _ in range(len(self.item_lookup.item_to_name))]

    def make_item(self, item, amount):
        self.item_tracker[item] += amount
        amount = amount - self.additional_items[item] 
        self.additional_items[item] = max(0, -amount)

        if amount < 0:
            return

        recipe = self.recipes[item]
        recipe_yield = recipe.get_amount(item)
        assert recipe_yield is not None

        times_recipe_needed = float(amount) / recipe_yield
        for ingredient in recipe.ingredients:
            self.make_item(ingredient.item, ingredient.amount * times_recipe_needed)

        for result in recipe.results:
            if item != result.item:
                self.additional_items[result.item] += times_recipe_needed * result.amount

    def reset(self):
        self.item_tracker = self._make_item_list()
        self.additional_items = self._make_item_list()

    def _format_item_list(self, item_list) -> List[str]:
        lines = []
        for item, amount in enumerate(item_list):
            if amount > 0:
                recipe = self.recipes[item]
                factory = recipe.factory
                items_per_second_per_factory = recipe.get_amount(item) / recipe.time
                factories_needed = math.ceil(amount / items_per_second_per_factory)
                lines.append(f"{self.item_lookup.name_for(item):<16}: {float(amount): >4g}/s - {factories_needed: >3} {factory}")
        return lines

    def __str__(self):
        lines = []
        lines.append("Required products:")
        lines += self._format_item_list(self.item_tracker)
        if any(self.additional_items):
            lines.append("Additional products:")
            lines += self._format_item_list(self.additional_items)
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

    calculator = Calculator(item_lookup, recipes)
    
    while True:
        try:
            item_spec = input("Items to produce/s (amount,item + ...): ")
        except EOFError:
            break

        if item_spec == "exit" or item_spec == "":
            break

        try:
            item_amounts = [ItemAmount.resolve(*parse_item_amount(token)) for token in item_spec.split('+')]
        except ParseError as e:
            print("Invalid item format")
            print(e)
            continue

        for item_amount in item_amounts:
            calculator.make_item(item_amount.item, item_amount.amount)
        print(str(calculator))
        calculator.reset()
        print()


if __name__ == "__main__":
    main()
