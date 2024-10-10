from database import db, GameCategory, GameOption, app

def add_initial_categories_and_options():
    with app.app_context():
        # Clear existing data (optional)
        db.drop_all()
        db.create_all()

        # Create categories
        animal_category = GameCategory(name="name of name: animal")
        country_category = GameCategory(name="name of name: country")

        # Create options for animal category
        animal_options = [
            GameOption(option="Lion", category=animal_category),
            GameOption(option="Tiger", category=animal_category),
            GameOption(option="Elephant", category=animal_category),
            GameOption(option="Dog", category=animal_category),
            GameOption(option="Cat", category=animal_category)
        ]

        # Create options for country category
        country_options = [
            GameOption(option="USA", category=country_category),
            GameOption(option="Canada", category=country_category),
            GameOption(option="Mexico", category=country_category),
            GameOption(option="Brazil", category=country_category),
            GameOption(option="UK", category=country_category)
        ]

        # Add categories and options to session
        db.session.add(animal_category)
        db.session.add(country_category)

        # Add options to session
        db.session.add_all(animal_options)
        db.session.add_all(country_options)

        # Commit the session to the database
        db.session.commit()

        print("Categories and options added successfully!")

if __name__ == "__main__":
    add_initial_categories_and_options()
