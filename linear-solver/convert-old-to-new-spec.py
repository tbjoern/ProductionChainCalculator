import json
from calculator.recipe import Recipe
from typing import Optional


class ParseError(Exception):
    pass


def parse_item_amount(item_token) -> Optional[tuple[str, float]]:
    item_token = item_token.split(",")
    if len(item_token) == 1:
        amount = 1
        item_name = item_token[0].strip().lower()
    elif len(item_token) == 2:
        amount, item_name = item_token
        try:
            amount = int(amount)
        except ValueError:
            raise ParseError()
    else:
        raise ParseError()
    return item_name, amount


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()

    parser.add_argument("--recipes", "-r", type=Path, required=True)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--ignore-extras", nargs="*", default=[])

    args = parser.parse_args()

    input = args.recipes.read_text().split("\n")
    output = open(args.output, "w")
    ignore_extras = set(args.ignore_extras)

    for line in input:
        line = line.strip()
        if len(line) == 0:
            output.write(line + "\n")
            continue
        if line[0] == "#":
            output.write(line + "\n")
            continue
        tokens = line.split(";")
        if len(tokens) < 3:
            print("Too few entries in line - {line} - Skip!")
            continue

        result_tokens, time, factory, *ingredient_tokens = tokens

        time = time.strip()
        factory = factory.strip()

        extras = {}

        try:
            time = float(time)
        except:
            pass

        if "time" not in ignore_extras:
            extras["time"] = time
        if "factory" not in ignore_extras:
            extras["factory"] = factory

        try:
            outputs = dict(
                [parse_item_amount(token) for token in result_tokens.split("+")]
            )

            inputs = dict([parse_item_amount(token) for token in ingredient_tokens])
        except ParseError:
            continue

        recipe = Recipe(inputs, outputs, extras)
        output.write(f"{recipe.serialized}\n")
