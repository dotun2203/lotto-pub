from database import db, GameCategory, GameOption, app


def print_all_categories():
    with app.app_context():
        categories = GameCategory.query.all()
        for category in categories:
            print(f"Category: {category.name}")
            for option in category.options:
                print(f"  Option: {option.option}")

if __name__ == "__main__":
    print_all_categories()
