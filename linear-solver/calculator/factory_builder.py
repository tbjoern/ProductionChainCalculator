from .recipe import Recipe, RecipeBook
from .linearv2 import produce_required_items, OptimizerResult
from typing import Callable


class AlreadyProduced(Exception):
    pass


class NoProducers(Exception):
    pass


class FactoryBuilder:
    def __init__(self, recipes: list[Recipe]):
        self.all_recipes = RecipeBook(recipes)
        self.used_recipes = RecipeBook([])
        self.required = {}

    def set_required_item(self, item: str, count: float):
        self.required[item] = count

    def remove_required_item(self, item: str):
        if item in self.required:
            del self.required[item]

    def get_required_items(self) -> dict[str, int]:
        return self.required

    def add_recipe(self, recipe: Recipe):
        self.used_recipes.add_recipe(recipe)

    def find_producers_of(self, item: str) -> list[Recipe]:
        producers = []
        for recipe in self.all_recipes:
            if item in recipe.outputs:
                producers.append(recipe)

        return producers

    def produce_item(
        self,
        item: str,
        resolve_multiple_producers: Callable[
            [str, list[Recipe]], Recipe
        ] = lambda item, producers: producers[0],
    ) -> Recipe:
        if item in self.get_factory_outputs():
            raise AlreadyProduced()

        producers = self.find_producers_of(item)
        if len(producers) > 1:
            producer = resolve_multiple_producers(item, producers)
        elif len(producers) == 1:
            producer = producers[0]
        else:
            raise NoProducers()

        self.add_recipe(producer)
        return producer

    def produce_item_chain(
        self,
        item: str,
        resolve_multiple_producers: Callable[
            [str, list[Recipe]], Recipe
        ] = lambda item, producers: producers[0],
    ) -> set[Recipe]:
        new_recipes = set()

        try:
            recipe = self.produce_item(item, resolve_multiple_producers)
            new_recipes.add(recipe)
        except:
            return set()

        inputs = self.get_factory_inputs()
        for input in inputs:
            new_recipes.update(self.produce_item_chain(input))
        return new_recipes

    def get_factory_inputs(self) -> list[str]:
        return self.used_recipes.get_pure_inputs()

    def get_factory_outputs(self) -> list[str]:
        return self.used_recipes.get_outputs()

    def optimize(self) -> OptimizerResult:
        return produce_required_items(self.used_recipes.all(), require=self.required)
