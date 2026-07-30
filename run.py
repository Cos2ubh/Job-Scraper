from app import create_app
from app.database import db
from app.migrations import run_migrations

app = create_app()

with app.app_context():
    db.create_all()
    run_migrations()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
