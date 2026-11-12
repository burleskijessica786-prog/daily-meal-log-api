
from dotenv import load_dotenv

# Load environment variables before importing the factory
load_dotenv()

from daily_meal_log_api import create_app

app = create_app("dev")

# Temporary checks (never print the actual secret)
print("DB URI:", app.config["SQLALCHEMY_DATABASE_URI"])
print("JWT secret set:", bool(app.config.get("JWT_SECRET")))
