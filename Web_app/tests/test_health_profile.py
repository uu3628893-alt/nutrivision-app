import sys
import sqlite3
import tempfile
from pathlib import Path
import pytest

CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src import database

def test_database_schema_migration(tmp_path, monkeypatch):
    test_db = tmp_path / "test_migration.db"
    
    # Create legacy schema without health_conditions
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE user_profiles (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            height_cm REAL NOT NULL,
            weight_kg REAL NOT NULL,
            activity_level TEXT NOT NULL,
            goal TEXT NOT NULL,
            allergies TEXT,
            preferences TEXT,
            target_calories REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT INTO user_profiles (
            id, age, sex, height_cm, weight_kg, activity_level, goal, allergies, preferences, target_calories
        ) VALUES (1, 29, 'Female', 168.0, 62.0, 'Moderately Active', 'maintain', 'peanut', 'vegetarian', 1950.0)
    """)
    conn.commit()
    conn.close()

    monkeypatch.setattr(database, "DATABASE_PATH", test_db)

    # Running init_database should migrate column safely
    database.init_database()

    # Verify column exists and existing record is preserved
    profile = database.get_user_profile()
    assert profile is not None
    assert profile["age"] == 29
    assert profile["sex"] == "Female"
    assert "health_conditions" in profile
    assert profile["health_conditions"] in ("", None)

def test_save_and_retrieve_health_conditions(tmp_path, monkeypatch):
    test_db = tmp_path / "test_health.db"
    monkeypatch.setattr(database, "DATABASE_PATH", test_db)
    database.init_database()

    database.save_user_profile(
        age=45,
        sex="Male",
        height_cm=180.0,
        weight_kg=88.0,
        activity_level="Sedentary",
        goal="weight_loss",
        allergies="shellfish",
        preferences="low sodium",
        target_calories=1800.0,
        health_conditions="Diabetes, High blood pressure"
    )

    saved = database.get_user_profile()
    assert saved is not None
    assert saved["health_conditions"] == "Diabetes, High blood pressure"
    assert saved["goal"] == "weight_loss"

    # Update and clear health conditions
    database.save_user_profile(
        age=45,
        sex="Male",
        height_cm=180.0,
        weight_kg=88.0,
        activity_level="Sedentary",
        goal="weight_loss",
        allergies="shellfish",
        preferences="low sodium",
        target_calories=1800.0,
        health_conditions=""
    )

    cleared = database.get_user_profile()
    assert cleared is not None
    assert cleared["health_conditions"] == ""

def test_undisclosed_health_conditions(tmp_path, monkeypatch):
    test_db = tmp_path / "test_undisclosed.db"
    monkeypatch.setattr(database, "DATABASE_PATH", test_db)
    database.init_database()

    database.save_user_profile(
        age=32,
        sex="Female",
        height_cm=165.0,
        weight_kg=58.0,
        activity_level="Lightly Active",
        goal="maintain",
        allergies="",
        preferences="",
        target_calories=1900.0,
        health_conditions="Prefer not to disclose"
    )

    prof = database.get_user_profile()
    assert prof is not None
    assert prof["health_conditions"] == "Prefer not to disclose"
