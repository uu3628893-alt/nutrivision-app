import sys
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src import llm_recommendation
from src import recommendation_engine
from src import config

def create_mock_client(response_text: str):
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = response_text
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client

def test_scenario_1_normal_meal_valid_profile():
    meal_nutrition = {
        "totals": {
            "calories_kcal": 650.0,
            "protein_g": 35.0,
            "carbs_g": 70.0,
            "fat_g": 20.0,
            "fiber_g": 9.0,
            "sodium_mg": 520.0,
            "sugars_g": 8.0,
            "total_grams": 450.0
        },
        "macronutrient_percentages": {
            "protein_pct": 22.0,
            "carbs_pct": 48.0,
            "fat_pct": 30.0
        },
        "ingredient_details": [
            {"food_name": "grilled chicken breast", "grams": 150.0, "portion_name": "1 piece (150g)", "calories_kcal": 240.0},
            {"food_name": "brown rice cooked", "grams": 200.0, "portion_name": "1 cup (200g)", "calories_kcal": 220.0},
            {"food_name": "steamed broccoli", "grams": 100.0, "portion_name": "1 cup (100g)", "calories_kcal": 55.0}
        ]
    }
    user_profile = {
        "age": 28,
        "sex": "Male",
        "height_cm": 178.0,
        "weight_kg": 75.0,
        "activity_level": "Moderately Active",
        "goal": "maintain",
        "allergies": "",
        "preferences": "",
        "target_calories": 2200.0,
        "health_conditions": ""
    }

    mock_llm_json = json.dumps({
        "meal_assessment": "This balanced lunch provides 650 kcal with good protein and fiber distribution.",
        "personalized_suggestions": [
            "Maintain current portion proportions to align with daily energy targets.",
            "Incorporate healthy fats such as olive oil or avocado if additional satiety is desired."
        ],
        "health_considerations": [
            "No chronic health conditions disclosed; macronutrient proportions are within recommended ranges."
        ],
        "important_notices": [
            "Portion weights based on typical prepared servings."
        ]
    })
    mock_client = create_mock_client(mock_llm_json)

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="lunch",
        client=mock_client
    )

    assert result["success"] is True
    assert result["source"] == "llm"
    assert "650 kcal" in result["meal_assessment"]
    assert len(result["personalized_suggestions"]) == 2
    assert len(result["important_notices"]) >= 1

def test_scenario_2_weight_management_goal():
    meal_nutrition = {
        "totals": {
            "calories_kcal": 920.0,
            "protein_g": 20.0,
            "carbs_g": 130.0,
            "fat_g": 35.0,
            "fiber_g": 4.0,
            "sodium_mg": 950.0,
            "sugars_g": 32.0,
            "total_grams": 550.0
        },
        "macronutrient_percentages": {
            "protein_pct": 9.0,
            "carbs_pct": 56.0,
            "fat_pct": 35.0
        },
        "ingredient_details": [
            {"food_name": "pasta in cream sauce", "grams": 400.0, "portion_name": "large bowl", "calories_kcal": 750.0},
            {"food_name": "garlic bread", "grams": 150.0, "portion_name": "2 slices", "calories_kcal": 170.0}
        ]
    }
    user_profile = {
        "age": 35,
        "sex": "Female",
        "height_cm": 162.0,
        "weight_kg": 80.0,
        "activity_level": "Sedentary",
        "goal": "weight_loss",
        "allergies": "",
        "preferences": "",
        "target_calories": 1500.0,
        "health_conditions": ""
    }

    mock_llm_json = json.dumps({
        "meal_assessment": "This meal provides 920 kcal, which constitutes over 60% of your daily caloric budget for weight reduction.",
        "personalized_suggestions": [
            "Reduce pasta portion to 200g and add a lean protein source such as chicken breast to increase protein above 25%.",
            "Swap creamy sauce for a tomato-based vegetable marinara to reduce dietary fat density."
        ],
        "health_considerations": [
            "Low fiber (4g) may reduce satiety between meals during a caloric deficit."
        ],
        "important_notices": [
            "Estimated portion sizes; weigh starches to assist accurate caloric tracking."
        ]
    })
    mock_client = create_mock_client(mock_llm_json)

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="dinner",
        client=mock_client
    )

    assert result["success"] is True
    assert "920 kcal" in result["meal_assessment"]
    assert any("reduce" in s.lower() or "protein" in s.lower() for s in result["personalized_suggestions"])

def test_scenario_3_declared_allergen_and_synonyms():
    meal_nutrition = {
        "totals": {
            "calories_kcal": 400.0,
            "protein_g": 12.0,
            "carbs_g": 30.0,
            "fat_g": 25.0,
            "fiber_g": 5.0,
            "sodium_mg": 280.0,
            "sugars_g": 10.0,
            "total_grams": 200.0
        },
        "macronutrient_percentages": {"protein_pct": 12.0, "carbs_pct": 32.0, "fat_pct": 56.0},
        "ingredient_details": [
            {"food_name": "peanut butter spread", "grams": 40.0, "portion_name": "2 tbsp", "calories_kcal": 240.0},
            {"food_name": "whole wheat toast", "grams": 60.0, "portion_name": "2 slices", "calories_kcal": 160.0}
        ]
    }
    user_profile = {
        "age": 24,
        "sex": "Male",
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "activity_level": "Moderately Active",
        "goal": "maintain",
        "allergies": "peanut, shellfish",
        "preferences": "",
        "target_calories": 2100.0,
        "health_conditions": ""
    }

    mock_llm_json = json.dumps({
        "meal_assessment": "Energy-dense meal containing toast and peanut butter.",
        "personalized_suggestions": [
            "Replace peanut butter with sunflower seed butter due to declared allergen."
        ],
        "health_considerations": ["Allergy hazard present."],
        "important_notices": ["Immediate allergen check required."]
    })
    mock_client = create_mock_client(mock_llm_json)

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="breakfast",
        client=mock_client
    )

    # Independent rule-based allergen alert must be preserved in safety alerts and important notices
    assert len(result["safety_alerts"]) >= 1
    assert any("peanut" in a.lower() for a in result["safety_alerts"])
    assert any("ALLERGEN WARNING" in n for n in result["important_notices"])

def test_scenario_4_optional_health_conditions():
    meal_nutrition = {
        "totals": {
            "calories_kcal": 750.0,
            "protein_g": 30.0,
            "carbs_g": 85.0,
            "fat_g": 25.0,
            "fiber_g": 7.0,
            "sodium_mg": 1250.0,
            "sugars_g": 28.0,
            "total_grams": 450.0
        },
        "macronutrient_percentages": {"protein_pct": 17.0, "carbs_pct": 50.0, "fat_pct": 33.0},
        "ingredient_details": [
            {"food_name": "teriyaki chicken bowl", "grams": 450.0, "portion_name": "1 bowl", "calories_kcal": 750.0}
        ]
    }
    user_profile = {
        "age": 52,
        "sex": "Female",
        "height_cm": 160.0,
        "weight_kg": 68.0,
        "activity_level": "Lightly Active",
        "goal": "maintain",
        "allergies": "",
        "preferences": "",
        "target_calories": 1750.0,
        "health_conditions": "Diabetes, High blood pressure"
    }

    mock_llm_json = json.dumps({
        "meal_assessment": "The meal provides 750 kcal with notable sodium and simple carbohydrate content.",
        "personalized_suggestions": [
            "Request sauce on the side to moderate sodium and sugar intake."
        ],
        "health_considerations": [
            "Sodium level (1250 mg) is elevated relative to DASH diet targets for blood pressure management.",
            "Higher sugar content from teriyaki glaze may prompt a sharper postprandial glucose curve."
        ],
        "important_notices": [
            "Guidance is educational and does not supersede your clinical care plan."
        ]
    })
    mock_client = create_mock_client(mock_llm_json)

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="lunch",
        client=mock_client
    )

    assert result["success"] is True
    assert len(result["health_considerations"]) >= 1
    assert any("blood pressure" in h.lower() or "sodium" in h.lower() for h in result["health_considerations"])

def test_scenario_5_missing_nutritional_values():
    meal_nutrition = {
        "totals": {
            "calories_kcal": 350.0,
            "protein_g": 10.0,
            "carbs_g": None,
            "fat_g": 8.0,
            "fiber_g": None,
            "sodium_mg": None,
            "sugars_g": 5.0,
            "total_grams": 200.0
        },
        "macronutrient_percentages": {"protein_pct": 15.0, "carbs_pct": 0.0, "fat_pct": 20.0},
        "ingredient_details": [
            {"food_name": "unclassified specialty soup", "grams": 200.0, "portion_name": "1 bowl", "calories_kcal": 350.0}
        ]
    }
    user_profile = {
        "age": 30,
        "sex": "Male",
        "height_cm": 175.0,
        "weight_kg": 72.0,
        "activity_level": "Sedentary",
        "goal": "maintain",
        "allergies": "",
        "preferences": "",
        "target_calories": 2000.0,
        "health_conditions": ""
    }

    # Rule-based check must flag missing nutrients
    rule_results = recommendation_engine.generate_dietary_recommendations(meal_nutrition, user_profile)
    assert any("missing" in a.lower() or "unrecorded" in a.lower() for a in rule_results["alerts"])

def test_scenario_6_uncertain_assumed_portions():
    meal_nutrition = {
        "totals": {
            "calories_kcal": 500.0,
            "protein_g": 20.0,
            "carbs_g": 60.0,
            "fat_g": 15.0,
            "fiber_g": 5.0,
            "sodium_mg": 400.0,
            "sugars_g": 6.0,
            "total_grams": 300.0
        },
        "macronutrient_percentages": {"protein_pct": 18.0, "carbs_pct": 52.0, "fat_pct": 30.0},
        "ingredient_details": [
            {"food_name": "curry stew", "grams": 200.0, "portion_name": "100 g reference", "calories_kcal": 320.0},
            {"food_name": "naan", "grams": 100.0, "portion_name": "100 g custom", "calories_kcal": 180.0}
        ]
    }
    user_profile = {
        "age": 28,
        "sex": "Male",
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "activity_level": "Moderately Active",
        "goal": "maintain",
        "allergies": "",
        "preferences": "",
        "target_calories": 2100.0,
        "health_conditions": ""
    }

    mock_llm_json = json.dumps({
        "meal_assessment": "Estimated 500 kcal meal based on reference amounts.",
        "personalized_suggestions": ["Ensure portion accuracy if tracking closely."],
        "health_considerations": ["Balanced macronutrients."],
        "important_notices": ["Portions were assumed based on standard references."]
    })
    mock_client = create_mock_client(mock_llm_json)

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="dinner",
        client=mock_client
    )

    # Assumed portions must be noted in important notices
    assert any("assumed portion" in n.lower() or "reference" in n.lower() for n in result["important_notices"])

def test_scenario_7_empty_user_profile():
    meal_nutrition = {
        "totals": {"calories_kcal": 450.0, "protein_g": 25.0, "carbs_g": 40.0, "fat_g": 18.0, "fiber_g": 6.0, "sodium_mg": 500.0, "sugars_g": 4.0, "total_grams": 300.0},
        "macronutrient_percentages": {"protein_pct": 24.0, "carbs_pct": 39.0, "fat_pct": 37.0},
        "ingredient_details": []
    }
    empty_profile = {}

    fallback = llm_recommendation.generate_fallback_recommendation(meal_nutrition, empty_profile, meal_type="lunch")
    assert fallback["success"] is True
    assert "450 kcal" in fallback["meal_assessment"]
    assert len(fallback["personalized_suggestions"]) >= 1

def test_scenario_8_invalid_llm_response():
    meal_nutrition = {
        "totals": {"calories_kcal": 550.0, "protein_g": 30.0, "carbs_g": 60.0, "fat_g": 18.0, "fiber_g": 8.0, "sodium_mg": 450.0, "sugars_g": 5.0, "total_grams": 350.0},
        "macronutrient_percentages": {"protein_pct": 23.0, "carbs_pct": 47.0, "fat_pct": 30.0},
        "ingredient_details": [{"food_name": "salmon fillet", "grams": 150.0, "portion_name": "1 fillet", "calories_kcal": 300.0}]
    }
    user_profile = {"age": 30, "sex": "Male", "height_cm": 175.0, "weight_kg": 72.0, "activity_level": "Moderately Active", "goal": "maintain", "target_calories": 2100.0}

    # Malformed non-JSON response from LLM
    mock_client = create_mock_client("I cannot generate a structured JSON recommendation right now.")

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="lunch",
        client=mock_client
    )

    # Must fall back gracefully to rule-based without crashing
    assert result["success"] is True
    assert result["source"] == "rule_based_fallback"
    assert "550 kcal" in result["meal_assessment"]

def test_scenario_9_llm_timeout_or_api_failure():
    meal_nutrition = {
        "totals": {"calories_kcal": 600.0, "protein_g": 25.0, "carbs_g": 70.0, "fat_g": 20.0, "fiber_g": 6.0, "sodium_mg": 600.0, "sugars_g": 10.0, "total_grams": 400.0},
        "macronutrient_percentages": {"protein_pct": 18.0, "carbs_pct": 51.0, "fat_pct": 31.0},
        "ingredient_details": []
    }
    user_profile = {"age": 30, "sex": "Female", "height_cm": 165.0, "weight_kg": 60.0, "activity_level": "Moderately Active", "goal": "maintain", "target_calories": 1900.0}

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = TimeoutError("Request timed out after 15 seconds")

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="lunch",
        client=mock_client
    )

    assert result["success"] is True
    assert result["source"] == "rule_based_fallback"
    assert "error_message" in result
    assert "TimeoutError" in result["error_message"] or "timed out" in result["error_message"]

def test_scenario_10_missing_api_key(monkeypatch):
    meal_nutrition = {
        "totals": {"calories_kcal": 500.0, "protein_g": 25.0, "carbs_g": 55.0, "fat_g": 15.0, "fiber_g": 7.0, "sodium_mg": 400.0, "sugars_g": 6.0, "total_grams": 350.0},
        "macronutrient_percentages": {"protein_pct": 21.0, "carbs_pct": 47.0, "fat_pct": 32.0},
        "ingredient_details": []
    }
    user_profile = {"age": 28, "sex": "Male", "height_cm": 175.0, "weight_kg": 70.0, "activity_level": "Moderately Active", "goal": "maintain", "target_calories": 2000.0}

    # Ensure no API key in environment or secrets
    monkeypatch.setattr(config, "get_llm_api_key", lambda: None)

    result = llm_recommendation.generate_llm_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type="lunch",
        client=None
    )

    assert result["success"] is True
    assert result["source"] == "rule_based_fallback"
    assert len(result["personalized_suggestions"]) >= 1
    assert "500 kcal" in result["meal_assessment"]

def test_pediatric_age_warning():
    meal_nutrition = {
        "totals": {"calories_kcal": 500.0, "protein_g": 20.0, "carbs_g": 65.0, "fat_g": 15.0, "fiber_g": 5.0, "sodium_mg": 450.0, "sugars_g": 10.0, "total_grams": 300.0},
        "macronutrient_percentages": {"protein_pct": 17.0, "carbs_pct": 55.0, "fat_pct": 28.0},
        "ingredient_details": []
    }
    user_profile = {"age": 16, "sex": "Male", "height_cm": 170.0, "weight_kg": 60.0, "activity_level": "Moderately Active", "goal": "maintain", "target_calories": 2200.0}

    rule_results = recommendation_engine.generate_dietary_recommendations(meal_nutrition, user_profile)
    assert any("under 18" in a.lower() or "pediatric" in a.lower() for a in rule_results["alerts"])
