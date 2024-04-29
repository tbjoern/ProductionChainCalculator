from flask import Flask, render_template
from calculator.recipe import parse_spec, RecipeBook, Recipe
from pathlib import Path
from dataclasses import asdict
import logging

logging.basicConfig(level=logging.DEBUG)


def load_recipes(recipe_folder: Path):
    books = {}
    for file in recipe_folder.iterdir():
        if file.is_file():
            try:
                recipes = parse_spec(file.read_text().split("\n"))
                books[file.stem] = RecipeBook(recipes)
            except:
                logging.error(f"Cannot parse recipes from {file.resolve()}")
    return books


def recipe_to_json(recipe: Recipe) -> dict:
    return asdict(recipe)


def book_to_json(book: RecipeBook) -> dict:
    return {"recipes": [recipe_to_json(r) for r in book]}


RECIPE_BOOKS_PATH = Path(__file__).parent / "recipe-collections"
books = load_recipes(RECIPE_BOOKS_PATH)

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", books=list(books.keys()))


@app.route("/<book>")
def book(book):
    if book not in books:
        return render_template("404.html")
    recipe_book = books[book]
    return render_template("book.html", book_name=book, book=recipe_book)


@app.route("/<book>.json")
def book_as_json(book):
    if book not in books:
        return render_template("404.html")
    recipes = books[book]
    return recipes, 200
