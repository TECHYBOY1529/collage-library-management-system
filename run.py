from app import create_app
from app.extensions import db
from app.models import Book
from seed import seed_demo_data

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Automatically seed demo data on first launch if database is empty
        if Book.query.count() == 0:
            seed_demo_data(reset_existing_demo=False)
    app.run(host="127.0.0.1", port=5000, debug=True)
