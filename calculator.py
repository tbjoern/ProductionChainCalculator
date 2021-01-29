from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

Item = int

@dataclass
class Ingredient:
    amount: int
    item: Item

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
        return self.name_to_item[name]

    def name_for(self, item):
        return self.item_to_name[item]

@dataclass
class Recipe:
    item: Item
    ingredients: List[Ingredient]
    time: int
    factory: Item


def load_recipes(filename: Path, parser) -> Tuple[ItemLookup, List[Recipe]]:
    item_names = []
    raw_recipes = []
    with open(filename, 'r') as fp:
        for i, line in enumerate(fp):
            tokens = line.split(';')
            if len(tokens) < 3:
                parser.error(f"Parse error in {filename}:{i} - Too few entries")
            item_name, time, factory, *ingredient_tokens = tokens
            item_name = item_name.strip()
            factory = factory.strip()
            if len(item_name) == 0:
                parser.error(f"Parse error in {filename}:{i} - Item name is empty")
            if len(factory) == 0:
                parser.error(f"Parse error in {filename}:{i} - Factory name is empty")

            item_names.append(item_name)

            try:
                time = int(time)
            except ValueError:
                parser.error(f"Parse error in {filename}:{i} - Failed to parse time, {time} is not an int")

            ingredients = []
            for itoken in ingredient_tokens:
                itoken_split = itoken.split(',')
                if len(itoken_split) != 2:
                    parser.error(f"Parse error in {filename}:{i} - Failed to parse ingredient {itoken}")
                amount, ingredient_item =  itoken_split
                ingredient_item = ingredient_item.strip()
                try:
                    amount = int(amount)
                except ValueError:
                    parser.error(f"Parse error in {filename}:{i} - Failed to parse ingredient {itoken}, amount {amount} is not an int")
                if len(ingredient_item) == 0:
                    parser.error(f"Parse error in {filename}:{i} - Failed to parse ingredient {itoken}, item {ingredient_item} is empty")
                ingredients.append((amount, ingredient_item))

            raw_recipes.append((item_name, ingredients, time, factory))
    
    item_lookup = ItemLookup.from_name_list(item_names)
    
    recipes = []
    for item_name, raw_ingredients, time, factory in raw_recipes:
        item = item_lookup.item_for(item_name)
        ingredients = []
        for amount, ingredient_item_name in raw_ingredients:
           ingredient_item = item_lookup.item_for(ingredient_item_name)
           ingredients.append(Ingredient(amount, ingredient_item))
        recipes.append(Recipe(item, ingredients, time, factory))

    return item_lookup, recipes


def main():
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--recipes', '-r', required=True, type=Path)

    args = parser.parse_args()

    if not args.recipes.is_file():
        parser.error(f"{args.recipes} is not a file")

    print(load_recipes(args.recipes, parser))


if __name__ == "__main__":
    main()
