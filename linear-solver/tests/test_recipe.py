from calculator.recipe import parse_spec, parse_line, RecipeBook, Recipe


class TestParser:
    def test_parse(self):
        recipe = parse_line("3 iron-ore + 1 coal --> 3 iron-plate + 1 slag")

        assert recipe.inputs == {"iron-ore": 3, "coal": 1}
        assert recipe.outputs == {"iron-plate": 3, "slag": 1}

    def test_parse_single(self):
        recipe = parse_line(" 1 iron-ore --> 1 iron-plate ")

        assert recipe.inputs == {"iron-ore": 1}
        assert recipe.outputs == {"iron-plate": 1}

    def test_parse_omitted_count(self):
        recipe = parse_line(" iron-ore --> iron-plate ")

        assert recipe.inputs == {"iron-ore": 1}
        assert recipe.outputs == {"iron-plate": 1}

    def test_parse_catalyst(self):
        recipe = parse_line(" 2 dirt --> 1 gem + 1 dirt ")

        assert recipe.inputs == {"dirt": 2}
        assert recipe.outputs == {"gem": 1, "dirt": 1}

    def test_parse_no_input(self):
        # e.g. a water pump, an ore mine
        recipe = parse_line(" --> 1 water ")

        assert recipe.inputs == {}
        assert recipe.outputs == {"water": 1}

    def test_parse_no_output(self):
        # e.g. an outflow pipe
        recipe = parse_line("1 water --> ")

        assert recipe.inputs == {"water": 1}
        assert recipe.outputs == {}

    def test_parse_additional_data(self):
        recipe = parse_line("1 ore --> 1 plate ; time: 60, machine: smelter")

        assert recipe.inputs == {"ore": 1}
        assert recipe.outputs == {"plate": 1}
        assert recipe.extras["time"] == 60
        assert recipe.extras["machine"] == "smelter"

    def test_parse_spec(self):
        spec = [
            "3 iron-ore + coal --> 3 iron-plate + slag",
            "# im a comment",
            "    ",
            "2 iron-plate --> gear",
            "1 steel-plate --> gear",
        ]

        recipes = parse_spec(spec, ignore_errors=False)
        assert len(recipes) == 3
        assert recipes[0].inputs == {
            "iron-ore": 3,
            "coal": 1,
        }
        assert recipes[0].outputs == {
            "iron-plate": 3,
            "slag": 1,
        }
        assert recipes[1].inputs == {"iron-plate": 2}
        assert recipes[1].outputs == {"gear": 1}
        assert recipes[2].inputs == {"steel-plate": 1}
        assert recipes[2].outputs == {"gear": 1}


class TestRecipeBook:
    def test_find_producer(self):
        recipes = [Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1})]
        recipe_book = RecipeBook(recipes)

        assert recipe_book.find_producers_of("iron-plate") == recipes
        assert recipe_book.find_producers_of("iron-ore") == []
        assert recipe_book.find_producers_of("foo") == []
