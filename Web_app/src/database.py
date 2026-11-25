"""
SQLite database management module for user profiles, meals, and ingredient history.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.paths import DATABASE_PATH

def get_connection() -> sqlite3.Connection:
    """Return an active connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database() -> None:
    """Initialize relational SQLite database schema if not present."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # User profile table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
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
                health_conditions TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Schema migration: ensure health_conditions column exists
        cursor.execute("PRAGMA table_info(user_profiles)")
        profile_columns = [col[1] for col in cursor.fetchall()]
        if "health_conditions" not in profile_columns:
            cursor.execute("ALTER TABLE user_profiles ADD COLUMN health_conditions TEXT DEFAULT ''")
        
        # Meal records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_name TEXT NOT NULL,
                meal_type TEXT NOT NULL,
                image_path TEXT,
                total_calories REAL NOT NULL,
                total_protein REAL NOT NULL,
                total_carbs REAL NOT NULL,
                total_fat REAL NOT NULL,
                total_fiber REAL NOT NULL,
                total_sugars REAL NOT NULL,
                total_sodium REAL NOT NULL,
                total_grams REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Meal ingredients breakdown table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meal_ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_id INTEGER NOT NULL,
                foodseg_class_id INTEGER,
                food_name TEXT NOT NULL,
                fdc_id INTEGER,
                portion_name TEXT,
                grams REAL NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                carbs REAL NOT NULL,
                fat REAL NOT NULL,
                fiber REAL NOT NULL,
                sugars REAL NOT NULL,
                sodium REAL NOT NULL,
                FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()

# User Profile CRUD Operations

def get_user_profile() -> Optional[Dict[str, Any]]:
    """Fetch the active user profile record."""
    init_database()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE id = 1")
        row = cursor.fetchone()
        if row:
            profile = dict(row)
            if "health_conditions" not in profile or profile["health_conditions"] is None:
                profile["health_conditions"] = ""
            return profile
    return None

def save_user_profile(
    age: int,
    sex: str,
    height_cm: float,
    weight_kg: float,
    activity_level: str,
    goal: str,
    allergies: str,
    preferences: str,
    target_calories: float,
    health_conditions: str = ""
) -> None:
    """Insert or update user biometric profile."""
    init_database()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_profiles (
                id, age, sex, height_cm, weight_kg, activity_level, goal, allergies, preferences, target_calories, health_conditions, updated_at
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                age = excluded.age,
                sex = excluded.sex,
                height_cm = excluded.height_cm,
                weight_kg = excluded.weight_kg,
                activity_level = excluded.activity_level,
                goal = excluded.goal,
                allergies = excluded.allergies,
                preferences = excluded.preferences,
                target_calories = excluded.target_calories,
                health_conditions = excluded.health_conditions,
                updated_at = CURRENT_TIMESTAMP
        """, (age, sex, height_cm, weight_kg, activity_level, goal, allergies, preferences, target_calories, health_conditions or ""))
        conn.commit()

def delete_user_profile() -> None:
    """Delete saved user profile information."""
    init_database()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_profiles WHERE id = 1")
        conn.commit()

# Meal CRUD Operations

def save_meal(
    meal_name: str,
    meal_type: str,
    image_path: Optional[str],
    nutrition_summary: Dict[str, Any],
    notes: str = ""
) -> int:
    """Save an analysed meal record along with its constituent ingredients."""
    init_database()
    totals = nutrition_summary.get("totals", {})
    ingredients = nutrition_summary.get("ingredient_details", [])
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO meals (
                meal_name, meal_type, image_path,
                total_calories, total_protein, total_carbs, total_fat,
                total_fiber, total_sugars, total_sodium, total_grams, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            meal_name,
            meal_type,
            image_path,
            totals.get("calories_kcal", 0.0),
            totals.get("protein_g", 0.0),
            totals.get("carbs_g", 0.0),
            totals.get("fat_g", 0.0),
            totals.get("fiber_g", 0.0),
            totals.get("sugars_g", 0.0),
            totals.get("sodium_mg", 0.0),
            totals.get("total_grams", 0.0),
            notes
        ))
        meal_id = cursor.lastrowid
        
        for item in ingredients:
            cursor.execute("""
                INSERT INTO meal_ingredients (
                    meal_id, foodseg_class_id, food_name, fdc_id, portion_name,
                    grams, calories, protein, carbs, fat, fiber, sugars, sodium
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                meal_id,
                item.get("class_id"),
                item.get("food_name", "Unknown"),
                item.get("fdc_id"),
                item.get("portion_name", "Custom grams"),
                item.get("grams", 0.0),
                item.get("calories_kcal", 0.0),
                item.get("protein_g", 0.0),
                item.get("carbs_g", 0.0),
                item.get("fat_g", 0.0),
                item.get("fiber_g", 0.0),
                item.get("sugars_g", 0.0),
                item.get("sodium_mg", 0.0)
            ))
            
        conn.commit()
        return meal_id

def get_all_meals(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve all recorded meals ordered by creation time descending."""
    init_database()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM meals ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_meal_by_id(meal_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single meal record and its ingredient breakdown."""
    init_database()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM meals WHERE id = ?", (meal_id,))
        meal_row = cursor.fetchone()
        if not meal_row:
            return None
            
        meal_dict = dict(meal_row)
        cursor.execute("SELECT * FROM meal_ingredients WHERE meal_id = ?", (meal_id,))
        ingredients = [dict(r) for r in cursor.fetchall()]
        meal_dict["ingredients"] = ingredients
        return meal_dict

def delete_meal(meal_id: int) -> bool:
    """Delete a specific meal record and its ingredients."""
    init_database()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM meal_ingredients WHERE meal_id = ?", (meal_id,))
        cursor.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
        conn.commit()
        return cursor.rowcount > 0

def get_meals_summary_stats() -> Dict[str, Any]:
    """Calculate aggregate dashboard statistics across all saved meals."""
    init_database()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_meals,
                AVG(total_calories) as avg_calories,
                AVG(total_protein) as avg_protein,
                AVG(total_carbs) as avg_carbs,
                AVG(total_fat) as avg_fat,
                AVG(total_fiber) as avg_fiber,
                SUM(total_calories) as sum_calories
            FROM meals
        """)
        row = cursor.fetchone()
        if not row or row["total_meals"] == 0:
            return {
                "total_meals": 0,
                "avg_calories": 0.0,
                "avg_protein": 0.0,
                "avg_carbs": 0.0,
                "avg_fat": 0.0,
                "avg_fiber": 0.0,
                "sum_calories": 0.0
            }
        return {
            "total_meals": int(row["total_meals"]),
            "avg_calories": round(float(row["avg_calories"] or 0.0), 1),
            "avg_protein": round(float(row["avg_protein"] or 0.0), 1),
            "avg_carbs": round(float(row["avg_carbs"] or 0.0), 1),
            "avg_fat": round(float(row["avg_fat"] or 0.0), 1),
            "avg_fiber": round(float(row["avg_fiber"] or 0.0), 1),
            "sum_calories": round(float(row["sum_calories"] or 0.0), 1)
        }

