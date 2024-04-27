from pathlib import Path
from .recipe import parse_spec, parse_def
from .factory_builder import FactoryBuilder, AlreadyProduced, NoProducers
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def resolve_multiple_producers(item, producers):
    print(f"Item {item} has multiple producers, choose one:")
    for i, producer in enumerate(producers):
        print(f"{i}: {str(producer)}")
    while True:
        choice = input("> ")
        try:
            producer = producers[int(choice)]
            break
        except:
            print("Invalid number, try again")

    return producer


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
            elif opcode == "optimize":
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
                        print(f"\t{count} x {recipe}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.exception(e)
            print("Could not parse that - try again")
