
import os
from datetime import date

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

# Load secret keys from the .env file
load_dotenv()

app = Flask(__name__)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meal_logs.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# JWT authentication configuration
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")

if not app.config["JWT_SECRET_KEY"]:
    raise RuntimeError("JWT_SECRET_KEY must be set")

db = SQLAlchemy(app)
jwt = JWTManager(app)



# User model
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    meal_logs = db.relationship("MealLog", back_populates="owner")


# Daily meal log model
class MealLog(db.Model):
    __tablename__ = "meal_logs"

    id = db.Column(db.Integer, primary_key=True)
    log_date = db.Column(db.Date, nullable=False, default=date.today)
    breakfast = db.Column(db.Text)
    lunch = db.Column(db.Text)
    dinner = db.Column(db.Text)
    snacks = db.Column(db.Text)
    drinks = db.Column(db.Text)
    energy_level = db.Column(db.Integer)
    feelings = db.Column(db.Text)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    owner = db.relationship("User", back_populates="meal_logs")

    # One daily log per user per date
    __table_args__ = (
        db.UniqueConstraint(
            "owner_id",
            "log_date",
            name="unique_user_log_date"
        ),
    )

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON object is required"
        }), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all(isinstance(v, str) for v in
               [username, email, password]):
        return jsonify({
            "error": "Username, email, and password are required"
        }), 400

    username = username.strip()
    email = email.strip().lower()

    if (not username or
            "@" not in email or
            "." not in email.split("@")[-1] or
            len(password) < 8):
        return jsonify({
            "error": "Enter a username, valid email, and password of at least 8 characters"
        }), 400

    existing_user = User.query.filter(
        (User.username == username) |
        (User.email == email)
    ).first()

    if existing_user:
        return jsonify({
            "error": "Username or email already registered"
        }), 400

    new_user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(
            password,
            method="pbkdf2:sha256"
        )
    )

    db.session.add(new_user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Username or email already registered"
        }), 400

    return jsonify({
        "message": "User registered successfully",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
    }), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON object is required"
        }), 400

    username = data.get("username")
    password = data.get("password")

    if (not isinstance(username, str) or
            not username.strip() or
            not isinstance(password, str) or
            not password):
        return jsonify({
            "error": "Username and password are required"
        }), 400

    user = User.query.filter_by(
        username=username.strip()
    ).first()

    if not user or not check_password_hash(
        user.password_hash, password
    ):
        return jsonify({
            "error": "Invalid username or password"
        }), 401

    access_token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }), 200


@app.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()

    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email
    }), 200


@app.route("/meal-logs", methods=["POST"])
@jwt_required()
def create_meal_log():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON object is required"
        }), 400

    log_date = data.get("log_date")

    if not isinstance(log_date, str):
        return jsonify({
            "error": "log_date is required (YYYY-MM-DD)"
        }), 400

    try:
        meal_date = date.fromisoformat(log_date)
    except ValueError:
        return jsonify({
            "error": "Invalid date format. Use YYYY-MM-DD"
        }), 400

    energy_level = data.get("energy_level")

    if (energy_level is not None and
            (type(energy_level) is not int or
             not 1 <= energy_level <= 10)):
        return jsonify({
            "error": "energy_level must be between 1 and 10"
        }), 400

    meal_fields = [
        "breakfast", "lunch", "dinner",
        "snacks", "drinks", "feelings"
    ]

    for field in meal_fields:
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            return jsonify({
                "error": f"{field} must be text"
            }), 400

    if not any(data.get(field) for field in meal_fields[:5]):
        return jsonify({
            "error": "At least one meal or drink is required"
        }), 400

    user_id = int(get_jwt_identity())

    existing_log = MealLog.query.filter_by(
        owner_id=user_id,
        log_date=meal_date
    ).first()

    if existing_log:
        return jsonify({
            "error": "A meal log already exists for this date"
        }), 400

    new_log = MealLog(
        owner_id=user_id,
        log_date=meal_date,
        breakfast=data.get("breakfast"),
        lunch=data.get("lunch"),
        dinner=data.get("dinner"),
        snacks=data.get("snacks"),
        drinks=data.get("drinks"),
        energy_level=energy_level,
        feelings=data.get("feelings")
    )

    db.session.add(new_log)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "A meal log already exists for this date"
        }), 400

    return jsonify({
        "message": "Daily meal log created successfully",
        "id": new_log.id,
        "log_date": new_log.log_date.isoformat(),
        "owner_id": new_log.owner_id
    }), 201


@app.route("/meal-logs", methods=["GET"])
@jwt_required()
def list_meal_logs():
    user_id = int(get_jwt_identity())

    logs = MealLog.query.filter_by(
        owner_id=user_id
    ).order_by(
        MealLog.log_date.desc()
    ).all()

    results = []

    for log in logs:
        results.append({
            "id": log.id,
            "log_date": log.log_date.isoformat(),
            "breakfast": log.breakfast,
            "lunch": log.lunch,
            "dinner": log.dinner,
            "snacks": log.snacks,
            "drinks": log.drinks,
            "energy_level": log.energy_level,
            "feelings": log.feelings,
            "owner_id": log.owner_id
        })

    return jsonify(results), 200


@app.route("/meal-logs/<int:log_id>", methods=["GET"])
@jwt_required()
def get_meal_log(log_id):
    user_id = int(get_jwt_identity())

    log = MealLog.query.filter_by(
        id=log_id,
        owner_id=user_id
    ).first()

    if not log:
        return jsonify({
            "error": "Meal log not found"
        }), 404

    return jsonify({
        "id": log.id,
        "log_date": log.log_date.isoformat(),
        "breakfast": log.breakfast,
        "lunch": log.lunch,
        "dinner": log.dinner,
        "snacks": log.snacks,
        "drinks": log.drinks,
        "energy_level": log.energy_level,
        "feelings": log.feelings,
        "owner_id": log.owner_id
    }), 200


@app.route("/meal-logs/<int:log_id>", methods=["PUT"])
@jwt_required()
def update_meal_log(log_id):
    user_id = int(get_jwt_identity())

    # Only find logs owned by this user
    log = MealLog.query.filter_by(
        id=log_id,
        owner_id=user_id
    ).first()

    if not log:
        return jsonify({
            "error": "Meal log not found"
        }), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON object is required"
        }), 400

    # Validate date
    log_date = data.get("log_date", log.log_date.isoformat())

    if not isinstance(log_date, str):
        return jsonify({
            "error": "log_date must be text in YYYY-MM-DD format"
        }), 400

    try:
        meal_date = date.fromisoformat(log_date)
    except ValueError:
        return jsonify({
            "error": "Invalid date format. Use YYYY-MM-DD"
        }), 400

    # Validate energy level
    energy_level = data.get("energy_level", log.energy_level)

    if (energy_level is not None and
            (type(energy_level) is not int or
             not 1 <= energy_level <= 10)):
        return jsonify({
            "error": "energy_level must be between 1 and 10"
        }), 400

    # Validate meal and feelings fields
    meal_fields = [
        "breakfast", "lunch", "dinner",
        "snacks", "drinks", "feelings"
    ]

    for field in meal_fields:
        value = data.get(field, getattr(log, field))

        if value is not None and not isinstance(value, str):
            return jsonify({
                "error": f"{field} must be text"
            }), 400

    # Prevent duplicate dates for the same user
    duplicate = MealLog.query.filter(
        MealLog.owner_id == user_id,
        MealLog.log_date == meal_date,
        MealLog.id != log_id
    ).first()

    if duplicate:
        return jsonify({
            "error": "A meal log already exists for this date"
        }), 400

    # Apply updates
    log.log_date = meal_date
    log.energy_level = energy_level

    for field in meal_fields:
        if field in data:
            setattr(log, field, data[field])

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "A meal log already exists for this date"
        }), 400

    return jsonify({
        "message": "Daily meal log updated successfully",
        "id": log.id,
        "log_date": log.log_date.isoformat(),
        "owner_id": log.owner_id,
        "breakfast": log.breakfast,
        "lunch": log.lunch,
        "dinner": log.dinner,
        "snacks": log.snacks,
        "drinks": log.drinks,
        "energy_level": log.energy_level,
        "feelings": log.feelings
    }), 200


@app.route("/meal-logs/<int:log_id>", methods=["DELETE"])
@jwt_required()
def delete_meal_log(log_id):
    user_id = int(get_jwt_identity())

    # Only locate logs belonging to the logged-in user
    log = MealLog.query.filter_by(
        id=log_id,
        owner_id=user_id
    ).first()

    if not log:
        return jsonify({
            "error": "Meal log not found"
        }), 404

    db.session.delete(log)
    db.session.commit()

    # Successful deletion returns no response body
    return "", 204

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Welcome to the Daily Meal Log API!",
        "status": "running"
    }), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, port=5003)
