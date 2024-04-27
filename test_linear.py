import pytest
from linearv2 import produce_required_items, Recipe


def test_basic():
    result = produce_required_items(
        recipes={
            "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1})
        },
        require={"gear": 2},
    )

    assert result.solvable
    assert result.recipe_count["gear-assembly"] == 2
    assert result.consumed == {"iron-plate": 4}
    assert result.produced == {"gear": 2}


def test_chain():
    result = produce_required_items(
        recipes={
            "iron-smelting": Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1}),
            "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1}),
        },
        require={"gear": 2},
    )

    assert result.solvable
    assert result.recipe_count["iron-smelting"] == 4
    assert result.recipe_count["gear-assembly"] == 2
    assert result.consumed == {"iron-ore": 4, "iron-plate": 4}
    assert result.produced == {"iron-plate": 4, "gear": 2}


def test_chain_with_provide():
    result = produce_required_items(
        recipes={
            "iron-smelting": Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1}),
            "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1}),
        },
        require={"gear": 2},
        provide={"iron-plate": 2},
    )

    assert result.solvable
    assert result.recipe_count["iron-smelting"] == 2
    assert result.recipe_count["gear-assembly"] == 2
    assert result.consumed == {"iron-ore": 2, "iron-plate": 4}
    assert result.produced == {"iron-plate": 2, "gear": 2}


def test_chain_with_provide_overflow():
    result = produce_required_items(
        recipes={
            "iron-smelting": Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1}),
            "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1}),
        },
        require={"gear": 2},
        provide={"iron-plate": 10},
    )

    assert result.solvable
    assert result.recipe_count["iron-smelting"] == 0
    assert result.recipe_count["gear-assembly"] == 2
    assert result.consumed["iron-plate"] == 4
    assert result.produced["gear"] == 2


def test_side_products():
    result = produce_required_items(
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
    )

    assert result.solvable
    assert result.recipe_count["advanced-oil-processing"] > 0
    assert result.recipe_count["light-oil-cracking"] > 0
    assert result.recipe_count["heavy-oil-cracking"] > 0
    assert result.produced["petroleum-gas"] == 110
    assert result.consumed["petroleum-gas"] == 0
    for intermediate in ["light-oil", "heavy-oil"]:
        assert result.produced[intermediate] - result.consumed[intermediate] == 0
    for input in ["water", "crude-oil"]:
        assert result.produced[input] == 0
        assert result.consumed[input] > 0


def test_maximize():
    result = produce_required_items(
        recipes={
            "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1}),
        },
        limit={"iron-plate": 8},
        maximize=["gear"],
    )

    assert result.solvable
    assert result.consumed["iron-plate"] == 8
    assert result.produced["gear"] == 4


def test_maximize_and_require():
    result = produce_required_items(
        recipes={
            "iron-smelting": Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1}),
            "gear-assembly": Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1}),
        },
        limit={"iron-ore": 8},
        require={"iron-plate": 2},
        maximize=["gear"],
    )

    assert result.solvable
    assert result.consumed["iron-plate"] == 6
    assert result.produced["gear"] == 3
    assert result.produced["iron-plate"] == 8
