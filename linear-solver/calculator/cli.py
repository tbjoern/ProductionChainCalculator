from pathlib import Path
from .recipe import parse_spec, parse_def, Recipe
from .factory_builder import FactoryBuilder, AlreadyProduced, NoProducers
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def resolve_multiple_producers(item, producers):
    print(f"Item {item} has multiple producers, choose one:")
    return select_recipe(producers)


def select_recipe(recipes: list[Recipe]) -> Recipe:
    for i, recipe in enumerate(recipes):
        print(f"{i}: {str(recipe)}")
    while True:
        choice = input("> ")
        try:
            return recipes[int(choice)]
        except:
            print("Invalid number, try again")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument("--recipes", "-r", required=True, type=Path)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    spec = args.recipes.read_text().split("\n")
    recipes = parse_spec(spec)

    builder = FactoryBuilder(recipes)

    while True:
        try:
            command = input("> ").strip()
            if command is None or command == "" or command == "exit":
                break

            opcode, *rest = command.split(maxsplit=1)
            opcode = opcode.strip()
            if len(rest) > 0:
                rest = rest[0].strip()
            else:
                rest = ""

            if opcode == "require":
                item, count = parse_def(rest)
                builder.set_required_item(item, count)
            elif opcode == "remove":
                item = rest.strip()
                builder.remove_required_item(item)
            elif opcode == "add-limit":
                item, count = parse_def(rest)
                builder.set_limit(item, count)
            elif opcode == "remove-limit":
                item = rest.strip()
                builder.remove_limit(item)
            elif opcode == "set-input":
                item = rest.strip()
                builder.set_explicit_input(item)
            elif opcode == "remove-input":
                item = rest.strip()
                builder.remove_explicit_input(item)
            elif opcode == "set-ignored":
                item = rest.strip()
                builder.set_ignored(item)
            elif opcode == "remove-ignored":
                item = rest.strip()
                builder.remove_ignored(item)
            elif opcode == "produce":
                item = rest.strip()
                try:
                    new_recipe = builder.produce_item(
                        item, resolve_multiple_producers=resolve_multiple_producers
                    )
                    print(f"Added recipe {new_recipe}")
                except AlreadyProduced:
                    print(f"Item {item} is already beeing produced")
                except NoProducers:
                    print(f"There are no recipes that produce {item}")
            elif opcode == "add-recipe-for":
                item = rest.strip()
                recipes = list(
                    filter(
                        lambda recipe: not builder.is_using_recipe(recipe),
                        builder.find_producers_of(item),
                    )
                )
                if len(recipes) == 0:
                    print("All available recipes in use")
                else:
                    print("Available recipes:")
                    recipe = select_recipe(recipes)
                    builder.add_recipe(recipe)
                    print(f"Added recipe {recipe}")
            elif opcode == "produce-chain":
                item = rest.strip()
                new_recipes = builder.produce_item_chain(
                    item, resolve_multiple_producers=resolve_multiple_producers
                )
                print("Added recipes:")
                for recipe in new_recipes:
                    print(f"\t{recipe}")
            elif opcode in {"ls", "show"}:
                print("Required Products:")
                for item, count in builder.get_required_items().items():
                    print(f"\t{item}: {count}")
                print("Used recipes:")
                for recipe in builder.used_recipes.all():
                    print(f"\t{recipe}")
                inputs = builder.get_factory_inputs()
                print("Inputs:")
                for item in inputs:
                    print(f"\t{item}")
                outputs = builder.get_factory_outputs()
                print("Outputs:")
                for item in outputs:
                    print(f"\t{item}")
            elif opcode == "recipes":
                print("All available recipes:")
                for recipe in builder.all_recipes:
                    print(f"\t{recipe}")
            elif opcode == "remove-recipe":
                print("Select recipe to remove:")
                recipe = select_recipe(builder.used_recipes.all())
                builder.remove_recipe(recipe)
                print(f"Removed recipe {recipe}")
            elif opcode == "optimize":
                timespan = None
                try:
                    timespan = float(rest)
                except:
                    pass
                result = builder.optimize()
                if result.solvable:
                    print("Inputs:")
                    for item in result.consumed:
                        count = result.consumed[item] - result.produced[item]
                        if count > 0:
                            print(f"\t{item}: {count}")
                    print("Outputs:")
                    for item in result.produced:
                        count = result.produced[item] - result.consumed[item]
                        if count > 0:
                            print(f"\t{item}: {count}")
                    print("Recipes:")
                    for recipe, count in result.recipe_count.items():
                        time = recipe.extras.get("time")
                        if (
                            timespan is not None
                            and time is not None
                            and type(time) in {int, float}
                        ):
                            machine_count = count * time / timespan
                            machine_label = (
                                recipe.extras.get("factory")
                                or recipe.extras.get("machine")
                                or "machine"
                            )

                            print(f"\t{machine_count} x {machine_label}, {recipe}")
                        else:
                            print(f"\t{count} x {recipe}")
                else:
                    print("No solution :(")
                    print(result)
            elif opcode == "used-in":
                item = rest.strip()
                consumers = builder.find_consumers_of(item)
                for recipe in consumers:
                    print(recipe)

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.exception(e)
            print("Could not parse that - try again")
