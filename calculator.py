from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Sequence, Optional
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

    def __iter__(self):
        return iter((self.amount, self.item))

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

    def __iter__(self):
        return iter((self.results, self.ingredients, self.time, self.factory))

def parse_item_amount(item_token):
    item_token = item_token.split(',')
    if len(item_token) == 1:
        item_amount = 1
        item_name = item_token[0]
    elif len(item_token) == 2:
        item_amount, item_name = item_token
        try:
            item_amount = float(item_amount)
        except ValueError:
            raise ParseError(f"Item amount is not an number - {item_token}")
    else:
        raise ParseError(f"Item needs amount and name - {item_token}")

    item_name = item_name.strip().lower()
    if len(item_name) == 0:
        raise ParseError(f"Item name is empty - {item_token}")

    return (item_amount, item_name)

def load_recipes(filename: Path, parser) -> Tuple[ItemLookup, List[Recipe]]:
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
    
    recipes = []
    for raw_results, raw_ingredients, time, factory in raw_recipes:
        ingredients = [ItemAmount.resolve(*r) for r in raw_ingredients]
        results = [ItemAmount.resolve(*r) for r in raw_results]
        recipes.append(Recipe(results, ingredients, time, factory))

    print(f"Sucessfully loaded {filename.name}")

    return item_lookup, recipes

def build_item_recipe_map(recipes: List[Recipe]) -> Dict[Item, List[Recipe]]:
    item_recipe_map = {}
    for recipe in recipes:
        # results: List[ItemAmount]
        for amount, item in recipe.results:
            if item not in item_recipe_map:
                item_recipe_map[item] = []
            item_recipe_map[item].append(recipe)
    return item_recipe_map

class Calculator:
    def __init__(self, item_count: int):
        self.item_count = item_count
        self.recipes = {}
        self.item_tracker = None
        self.additional_items = None
        self.item_hierarchy = None
        self.reset()
    
    def set_item_recipe(self, item: Item, recipe: Recipe):
        self.recipes[item] = recipe

    def get_item_recipe(self, item: Item):
        return self.recipes[item]

    def _make_item_list(self):
        return [0 for _ in range(self.item_count)]

    def add_existing_item(self, item, amount):
        self.additional_items[item] += amount

    def make_item(self, item, amount, level=0):
        self.item_tracker[item] += amount
        self.item_hierarchy[item] = max(self.item_hierarchy[item], level)

        amount = amount - self.additional_items[item] 
        self.additional_items[item] = max(0, -amount)
        amount = max(amount, 0)

        if not item in self.recipes:
            logger.warning("Could not find a recipe for item {item}")
            return
        recipe = self.recipes[item]
        recipe_yield = recipe.get_amount(item)
        assert recipe_yield is not None

        times_recipe_needed = float(amount) / recipe_yield
        for ingredient in recipe.ingredients:
            self.make_item(ingredient.item, ingredient.amount * times_recipe_needed, level=level+1)

        for result in recipe.results:
            if item != result.item:
                self.additional_items[result.item] += times_recipe_needed * result.amount

    def reset(self):
        self.item_tracker = self._make_item_list()
        self.additional_items = self._make_item_list()
        self.item_hierarchy = self._make_item_list()

    def get_required_items(self):
        return self._iter_item_list(self.item_tracker)

    def get_additional_items(self):
        return self._iter_item_list(self.additional_items)

    def has_additional_items(self):
        return any(self.additional_items)

    def _iter_item_list(self, item_counts: List[int]) -> List[str]:
        max_item_level = max(self.item_hierarchy)
        buckets = [[] for _ in range(max_item_level+1)]
        for item, amount in enumerate(item_counts):
            if amount > 0:
                item_level = self.item_hierarchy[item]
                buckets[item_level].append(ItemAmount(amount, item))
        for level, bucket in enumerate(buckets):
            if len(bucket) > 0 and level > 0:
                yield None
            for amount, item in bucket:
                if amount > 0:
                    recipe = self.recipes[item]
                    yield item, amount, recipe

def format_calculator_result(calculator: Calculator, item_lookup: ItemLookup):
    lines = []
    lines.append("Required products:")
    for result in calculator.get_required_items():
        if result is None:
            lines.append("")
            continue
        item, amount, recipe = result
        factory = recipe.factory
        items_per_second_per_factory = recipe.get_amount(item) / recipe.time
        factories_needed = amount / items_per_second_per_factory
        lines.append(f"{item_lookup.name_for(item):<16}: {float(amount): >4g}/s - {factories_needed: >3.3g} {factory}")

    if calculator.has_additional_items():
        lines.append("Additional products:")
        for result in calculator.get_additional_items():
            if result is None:
                continue
            item, amount, recipe = result
            lines.append(f"{item_lookup.name_for(item):<16}: {float(amount): >4g}/s")

    return "\n".join(lines)

def format_item_amount(item_amount: ItemAmount, item_lookup: ItemLookup) -> str:
    amount, item = item_amount
    if amount > 1:
        return f"{amount:g} {item_lookup.name_for(item)}"
    return f"{item_lookup.name_for(item)}"

def format_recipe(recipe: Recipe, item_lookup: ItemLookup) -> str:
    tokens = []
    tokens += [" + ".join(format_item_amount(ingredient, item_lookup) for ingredient in recipe.ingredients)]
    tokens += ["->"]
    tokens += [" + ".join(format_item_amount(result, item_lookup) for result in recipe.results)]
    return " ".join(tokens)


help_msg="""Usage:
ls, list, items : Show all available items
recipes         : Show all recipes
setoptional     : Select a different recipe for an item
showoptional    : Show all items that have optional recipes, and which one is selected
?, help         : Print this help
exit, CTRL-D    : Exit the program
"""

def read_command(prompt: str) -> Optional[str]:
    try:
        command = input(prompt)
    except EOFError:
        return None

    if command == "exit" or command == "":
        return None

    return command

def main():
    global item_lookup
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--recipes', '-r', required=True, type=Path)

    args = parser.parse_args()

    if not args.recipes.is_file():
        parser.error(f"{args.recipes} is not a file")

    item_lookup, all_recipes = load_recipes(args.recipes, parser)
    item_recipe_map = build_item_recipe_map(all_recipes)

    calculator = Calculator(len(item_lookup.item_to_name))

    # set default recipes
    for item, recipes in item_recipe_map.items():
        assert len(recipes) > 0
        calculator.set_item_recipe(item, recipes[0])

    # find items with optional recipes
    optional_recipe_items = []
    for item, recipes in item_recipe_map.items():
        if len(recipes) > 1:
            optional_recipe_items.append(item)
    
    while True:
        command = read_command("Items to produce/s (amount,item + ...): ")
        if command is None:
            break

        if command == "ls" or command == "list" or command == "items":
            print("\n".join(item_lookup.item_to_name))
            print()
            continue

        if command == "?" or command == "help":
            print(help_msg)
            print()
            continue

        if command == "recipes":
            for recipe in all_recipes:
                print(format_recipe(recipe, item_lookup))
            print()
            continue

        if command == "setoptional":
            print("\n".join([item_lookup.name_for(item) for item in optional_recipe_items]))
            item = None
            item_name = read_command("Select item: ")
            if item_name is None:
                print()
                continue
            item = item_lookup.item_for(item_name)
            if item is None:
                print(f"Could not find {item_name}")
                print()
                continue

            available_recipes = item_recipe_map[item]
            print("\n".join(f"{i}: {format_recipe(recipe, item_lookup)}" for i, recipe in enumerate(available_recipes)))
            selection = read_command("Select recipe nr: ")
            if selection is None:
                print()
                continue
            try:
                selection_index = int(selection)
            except ValueError:
                print("That is not a number")
                continue
            if selection_index > len(available_recipes) - 1 or selection_index < 0:
                print("That recipe doesnt exist")
                continue

            calculator.set_item_recipe(item, available_recipes[selection_index])
            print()
            continue

        if command == "showoptional":
            for item in optional_recipe_items:
                recipe = calculator.get_item_recipe(item)
                print(f"{item_lookup.name_for(item)}: {format_recipe(recipe, item_lookup)}")
            print()
            continue
        
        item_spec = command

        def parse_spec(spec):
            tokens = spec.split('+')
            item_amounts = [ItemAmount.resolve(*parse_item_amount(token)) for token in tokens]
            for i, item_amount in enumerate(item_amounts):
                if item_amount.item is None:
                    raise ParseError(f"Item not found: {tokens[i]}")
            return item_amounts

        try:
            parts = item_spec.split(';')
            if len(parts) == 1:
                target_spec = parts[0]
                existing_spec = None
            elif len(parts) == 2:
                target_spec, existing_spec = parts
            else:
                raise ParseError("Only 1 ';' allowed")

            target_item_amounts = parse_spec(target_spec)
            if existing_spec is not None:
                existing_item_amounts = parse_spec(existing_spec)
            else:
                existing_item_amounts = []
        except ParseError as e:
            print("Invalid item specification")
            print(e)
            continue

        for amount, item in existing_item_amounts:
            calculator.add_existing_item(item, amount)
        for amount, item in target_item_amounts:
            calculator.make_item(item, amount)
        print(format_calculator_result(calculator, item_lookup))
        calculator.reset()
        print()


if __name__ == "__main__":
    main()
