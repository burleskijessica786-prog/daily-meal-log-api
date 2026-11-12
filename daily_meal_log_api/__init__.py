
from flask import Flask

def create_app(config_name):
    app = Flask(__name__)

    # Select and apply the configuration
    from .config import config_by_name
    app.config.from_object(config_by_name[config_name])

    # Initialize database and migrations
    from .extensions import db, migrate
    db.init_app(app)
    migrate.init_app(app, db)

    # Register the main blueprint
    from .main import main_bp
    app.register_blueprint(main_bp)

    return app
