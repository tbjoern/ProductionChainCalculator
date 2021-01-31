from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple, Sequence, Optional, Any
import logging
import math
import readline

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

@dataclass
class Item:
    id: int
    name: str

    count = 0
    name_item_map = {}
    item_list = []

    def __str__(self):
        return self.name

    @classmethod
    def create_from(cls, name) -> Item:
        if name in cls.name_item_map:
            return cls.name_item_map[name]
        id = cls.count
        cls.count += 1
        item = Item(id, name)
        cls.name_item_map[name] = item
        cls.item_list.append(item)
        return item

    @classmethod
    def get_from(cls, name) -> Item:
        return cls.name_item_map.get(name, None)

    @classmethod
    def from_id(cls, id: int) -> Item:
        assert id < len(cls.item_list) and id >= 0
        return cls.item_list[id]

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

class ParseError(ValueError):
    pass

@dataclass
class ItemAmount:
    amount: int
    item: Item

    def __repr__(self):
        return f"ItemAmount(amount={self.amount}, item={item.name})"

    def __iter__(self):
        return iter((self.amount, self.item))

@dataclass
class Recipe:
    results: List[ItemAmount]
    ingredients: List[ItemAmount]
    time: int
    factory: Item

    def get_amount(self, item: Item) -> int:
        for result in self.results:
            if item == result.item:
                return result.amount
        return None

    def __iter__(self):
        return iter((self.results, self.ingredients, self.time, self.factory))

def parse_item_amount(item_token, allow_create=False) -> ItemAmount:
    item_token = item_token.split(',')
    if len(item_token) == 1:
        amount = 1
        item_name = item_token[0]
    elif len(item_token) == 2:
        amount, item_name = item_token
        try:
            amount = float(amount)
        except ValueError:
            raise ParseError(f"Item amount is not an number - {item_token}")
    else:
        raise ParseError(f"Item needs amount and name - {item_token}")

    item_name = item_name.strip().lower()
    if len(item_name) == 0:
        raise ParseError(f"Item name is empty - {item_token}")

    if allow_create:
        item = Item.create_from(item_name)
    else:
        item = Item.get_from(item_name)
        if item is None:
            raise ParseError(f"Item name not found in item database: {item_name}")
    return ItemAmount(amount, item)

def load_recipes(filename: Path, parser) -> List[Recipe]:
    item_names = set()
    recipes = []
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

                results = [parse_item_amount(token, allow_create=True) for token in result_tokens.split('+')]

                for amount, item_name in results:
                    item_names.add(item_name)

                try:
                    time = float(time)
                except ValueError:
                    raise ParseError(f"Failed to parse time, {time} is not an int")

                factory = factory.strip()
                if len(factory) == 0:
                    raise ParseError(f"Factory name is empty")

                ingredients = [parse_item_amount(token, allow_create=True) for token in ingredient_tokens]

                recipes.append(Recipe(results, ingredients, time, factory))
        except ParseError as e:
            parser.error("Parse error in {filename}:{i} - {e}")
    
    print(f"Sucessfully loaded {filename.name}")
    return recipes

def build_item_recipe_map(recipes: List[Recipe]) -> Dict[Item, List[Recipe]]:
    item_recipe_map = {}
    for recipe in recipes:
        # results: List[ItemAmount]
        for amount, item in recipe.results:
            if item not in item_recipe_map:
                item_recipe_map[item] = []
            item_recipe_map[item].append(recipe)
    return item_recipe_map

@dataclass
class Node:
    data: Any
    children: List[Node] = field(default_factory=list)

    def add_child(self, child: Node):
        self.children.append(child)

    def traverse(self, level=0):
        """pre-order traversal"""
        yield (self, level)
        for child in self.children:
            yield from child.traverse(level=level+1)

class Calculator:
    def __init__(self, item_count: int):
        self.item_count = item_count
        self.recipes: Dict[Item, Recipe] = {}
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
        self.additional_items[item.id] += amount

    def make_item(self, item: Item, amount: int, level=0) -> Node:
        node = Node(data=ItemAmount(amount, item))

        self.item_tracker[item.id] += amount
        self.item_hierarchy[item.id] = max(self.item_hierarchy[item.id], level)

        amount = amount - self.additional_items[item.id] 
        self.additional_items[item.id] = max(0, -amount)
        amount = max(amount, 0)

        if not item in self.recipes:
            raise RuntimeError(f"Could not find a recipe for item {item}")

        recipe = self.recipes[item]
        recipe_yield = recipe.get_amount(item)
        assert recipe_yield is not None

        times_recipe_needed = float(amount) / recipe_yield
        for ingredient in recipe.ingredients:
            childnode = self.make_item(ingredient.item, ingredient.amount * times_recipe_needed, level=level+1)
            node.add_child(childnode)

        for result in recipe.results:
            if item != result.item:
                self.additional_items[result.item.id] += times_recipe_needed * result.amount

        return node

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
        for id, amount in enumerate(item_counts):
            if amount > 0:
                item_level = self.item_hierarchy[id]
                buckets[item_level].append(ItemAmount(amount, Item.from_id(id)))
        for level, bucket in enumerate(buckets):
            if len(bucket) > 0 and level > 0:
                yield None
            for amount, item in bucket:
                if amount > 0:
                    recipe = self.recipes[item]
                    yield item, amount, recipe

def format_calculator_result(calculator: Calculator):
    lines = []
    lines.append("--- Required products ---")
    factories = {}
    for result in calculator.get_required_items():
        if result is None:
            lines.append("")
            continue
        item, amount, recipe = result
        factory = recipe.factory
        items_per_second_per_factory = recipe.get_amount(item) / recipe.time
        factories_needed = amount / items_per_second_per_factory
        if not factory in factories:
            factories[factory] = 0
        factories[factory] += factories_needed
        lines.append(f"{item.name:<16}: {float(amount): >4g}/s - {factories_needed: >3.3g} {factory}")

    lines.append("--- Needed factories ---")
    for factory, count in factories.items():
        lines.append(f"{factory:<16}: {count: >3.3g}")

    if calculator.has_additional_items():
        lines.append("--- Additional products ---")
        for result in calculator.get_additional_items():
            if result is None:
                continue
            item, amount, recipe = result
            lines.append(f"{item.name:<16}: {float(amount): >4g}/s")

    return "\n".join(lines)

def format_item_amount(item_amount: ItemAmount) -> str:
    amount, item = item_amount
    if amount > 1:
        return f"{amount:g} {item.name}"
    return f"{item.name}"

def format_recipe(recipe: Recipe) -> str:
    tokens = []
    if len(recipe.ingredients) > 0:
        tokens += [" + ".join(format_item_amount(ingredient) for ingredient in recipe.ingredients)]
        tokens += ["->"]
    tokens += [" + ".join(format_item_amount(result) for result in recipe.results)]
    tokens += [f" {recipe.factory}"]
    return " ".join(tokens)

def format_nodes(nodes: List[Node], calculator):
    lines = []
    lines.append("--- Tree View ---")
    for start in nodes:
        for node, level in start.traverse():
            amount, item = node.data
            if amount == 0:
                continue
            recipe = calculator.get_item_recipe(item)
            factory = recipe.factory
            items_per_second_per_factory = recipe.get_amount(item) / recipe.time
            factories_needed = amount / items_per_second_per_factory
            lines.append(f"{'  ' * level}{item.name} {float(amount):g}/s - {factories_needed:g} {factory}")
    return '\n'.join(lines)


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

def command_ls():
    print("\n".join(str(item) for item in Item.item_list))

def command_help():
    print(help_msg)

def command_recipes(all_recipes):
    for recipe in all_recipes:
        print(format_recipe(recipe))

def command_showoptional(optional_recipe_items, calculator):
    for item in optional_recipe_items:
        recipe = calculator.get_item_recipe(item)
        print(f"{item.name}: {format_recipe(recipe)}")

def command_setoptional(optional_recipe_items, item_recipe_map, calculator):
    print("\n".join([item.name for item in optional_recipe_items]))
    item = None
    item_name = read_command("Select item: ")
    if item_name is None:
        print()
        return
    item = Item.get_from(item_name)
    if item is None:
        print(f"Could not find {item_name}")
        print()
        return

    available_recipes = item_recipe_map[item]
    print("\n".join(f"{i}: {format_recipe(recipe)}" for i, recipe in enumerate(available_recipes)))
    selection = read_command("Select recipe nr: ")
    if selection is None:
        print()
        return
    try:
        selection_index = int(selection)
    except ValueError:
        print("That is not a number")
        return
    if selection_index > len(available_recipes) - 1 or selection_index < 0:
        print("That recipe doesnt exist")
        return

    calculator.set_item_recipe(item, available_recipes[selection_index])

def command_calculate(item_spec, calculator):
    def parse_spec(spec) -> List[ItemAmount]:
        return [parse_item_amount(token, allow_create=False) for token in spec.split('+')]

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
        return

    for amount, item in existing_item_amounts:
        calculator.add_existing_item(item, amount)
    nodes = []
    for amount, item in target_item_amounts:
        node = calculator.make_item(item, amount)
        nodes.append(node)
    print(format_calculator_result(calculator))
    print(format_nodes(nodes, calculator))
    calculator.reset()

def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--recipes', '-r', required=True, type=Path)

    args = parser.parse_args()

    if not args.recipes.is_file():
        parser.error(f"{args.recipes} is not a file")

    all_recipes = load_recipes(args.recipes, parser)
    item_recipe_map = build_item_recipe_map(all_recipes)

    calculator = Calculator(Item.count)

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

        elif command == "ls" or command == "list" or command == "items":
            command_ls()

        elif command == "?" or command == "help":
            command_help()

        elif command == "recipes":
            command_recipes(all_recipes)

        elif command == "setoptional":
            command_setoptional(optional_recipe_items, item_recipe_map, calculator)

        elif command == "showoptional":
            command_showoptional(optional_recipe_items, calculator)
        
        else:
            command_calculate(command, calculator)

        print()


if __name__ == "__main__":
    main()
