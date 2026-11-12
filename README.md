# Daily Meal Log API

A Flask backend API that allows users to record their daily meals, track their energy levels, and manage their personal meal logs.

**Project status:** Early in development; endpoints and responses may change.

## Technologies
- Python 3.15.2
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-JWT-Extended
- SQLite

## Local Setup

1. Clone the repository:

   git clone https://github.com/burleskijessica786-prog/daily-meal-log-api.git

2. Enter the project folder:

   cd daily-meal-log-api

3. Create and activate a virtual environment:

   python3 -m venv venv
   source venv/bin/activate

4. Install dependencies:

   python -m pip install -r requirements.txt

5. Create a private .env file using .env.example as a guide.

   Set DATABASE_URL and JWT_SECRET to appropriate values.
   Never commit your real .env file.

6. Run the application factory:

   python -m flask --app wsgi:app run --port 5003

## Project Structure

- app.py: Existing meal-log API implementation
- wsgi.py: Application factory entry point
- daily_meal_log_api/: Flask application package
- requirements.txt: Pinned Python dependencies
- .env.example: Environment variable template

## Development Note

The factory-based application is currently being developed separately from the existing meal-log API. Its blueprint is registered, but its existing authentication and meal-log endpoints have not yet been migrated.
