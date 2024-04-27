from calculator.factory_builder import FactoryBuilder
from calculator.recipe import Recipe


class TestFactoryBuilder:
    def test_simple_usage(self):
        plate_recipe = Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1})
        gear_recipe = Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1})
        recipes = [plate_recipe, gear_recipe]
        builder = FactoryBuilder(recipes=recipes)

        builder.set_required_item("gear", 2)
        gear_producers = builder.find_producers_of("gear")
        assert gear_producers == [gear_recipe]
        builder.add_recipe(gear_producers[0])

        pure_inputs = builder.get_factory_inputs()
        assert pure_inputs == {"iron-plate"}

        plate_producers = builder.find_producers_of("iron-plate")
        assert plate_producers == [plate_recipe]
        builder.add_recipe(plate_producers[0])

        pure_inputs = builder.get_factory_inputs()
        assert pure_inputs == {"iron-ore"}

        ore_producers = builder.find_producers_of("iron-ore")
        assert ore_producers == []

        result = builder.optimize()

        assert result.solvable
        assert result.recipe_count[gear_recipe] == 2
        assert result.recipe_count[plate_recipe] == 4
        assert result.produced["gear"] == 2
        assert result.consumed["gear"] == 0
        assert result.produced["iron-plate"] == 4
        assert result.consumed["iron-plate"] == 4
        assert result.produced["iron-ore"] == 0
        assert result.consumed["iron-ore"] == 4

    def test_produce_helper(self):
        plate_recipe = Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1})
        gear_recipe = Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1})
        recipes = [plate_recipe, gear_recipe]
        builder = FactoryBuilder(recipes=recipes)

        builder.set_required_item("gear", 2)
        builder.produce_item("gear")
        builder.produce_item("iron-plate")

        assert set(builder.used_recipes.all()) == {plate_recipe, gear_recipe}

    def test_produce_helper_with_multiple_producers(self):
        plate_recipe = Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1})
        scrap_recipe = Recipe(inputs={"iron-scrap": 1}, outputs={"iron-plate": 1})
        recipes = [plate_recipe, scrap_recipe]
        builder = FactoryBuilder(recipes=recipes)

        def resolve(item, producers):
            assert item == "iron-plate"
            assert producers == recipes
            return producers[1]

        builder.set_required_item("gear", 2)
        builder.produce_item("iron-plate", resolve_multiple_producers=resolve)

        assert set(builder.used_recipes.all()) == {scrap_recipe}

    def test_produce_chain_helper(self):
        plate_recipe = Recipe(inputs={"iron-ore": 1}, outputs={"iron-plate": 1})
        scrap_recipe = Recipe(inputs={"iron-scrap": 1}, outputs={"iron-plate": 1})
        gear_recipe = Recipe(inputs={"iron-plate": 2}, outputs={"gear": 1})
        recipes = [plate_recipe, gear_recipe, scrap_recipe]
        builder = FactoryBuilder(recipes=recipes)

        builder.set_required_item("gear", 2)
        builder.produce_item_chain("gear")

        assert set(builder.used_recipes.all()) == {plate_recipe, gear_recipe}
