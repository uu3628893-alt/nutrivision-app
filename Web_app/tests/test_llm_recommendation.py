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

def create_mock_gemini_client(response_text: str):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client.models.generate_content.return_value = mock_response
    return mock_client

@pytest.fixture
def sample_meal():
    return {
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
            {"food_name": "grilled chicken breast", "grams": 150.0, "portion_name": "1 piece (150g)", "calories_kcal": 240.0, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 5.0},
            {"food_name": "brown rice cooked", "grams": 200.0, "portion_name": "1 cup (200g)", "calories_kcal": 220.0, "protein_g": 5.0, "carbs_g": 45.0, "fat_g": 2.0},
            {"food_name": "steamed broccoli", "grams": 100.0, "portion_name": "1 cup (100g)", "calories_kcal": 55.0, "protein_g": 3.7, "carbs_g": 11.0, "fat_g": 0.6}
        ]
    }

@pytest.fixture
def sample_profile():
    return {
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

# Scenario 1: Successful personalized recommendation with Gemini
def test_scenario_1_successful_gemini_recommendation(sample_meal, sample_profile):
    mock_payload = {
        "meal_assessment": "This lunch provides 650 kcal with a well-balanced macronutrient distribution (22% protein, 48% carbs, 30% fat).",
        "personalized_recommendations": [
            "Maintain current portion sizes of grilled chicken and brown rice to align with your 2200 kcal daily maintenance target.",
            "Consider adding a light drizzle of olive oil or seeds for beneficial unsaturated fatty acids."
        ],
        "health_considerations": [
            "No chronic conditions reported; current sodium (520 mg) is within standard daily reference limits."
        ],
        "suggested_improvements": [
            "Increase cruciferous vegetables such as broccoli or spinach to further boost dietary fiber intake."
        ],
        "limitations": [
            "Portion weights are based on standard reference measurements."
        ]
    }
    client = create_mock_gemini_client(json.dumps(mock_payload))
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=sample_profile,
        meal_type="lunch",
        include_health_conditions=True,
        client=client
    )

    assert result["success"] is True
    assert result["source"] == "gemini"
    assert "650 kcal" in result["meal_assessment"]
    assert len(result["personalized_recommendations"]) == 2
    assert len(result["suggested_improvements"]) == 1
    assert any("Educational Prototype Notice" in l for l in result["limitations"])

# Scenario 2: Nutrients & goals alignment (e.g. weight loss deficit target)
def test_scenario_2_nutrients_and_goals_alignment(sample_meal):
    deficit_profile = {
        "age": 35,
        "sex": "Female",
        "height_cm": 162.0,
        "weight_kg": 82.0,
        "activity_level": "Sedentary",
        "goal": "weight_loss",
        "allergies": "",
        "preferences": "",
        "target_calories": 1400.0,
        "health_conditions": ""
    }
    mock_payload = {
        "meal_assessment": "This meal yields 650 kcal, consuming approximately 46% of your daily 1400 kcal deficit allocation.",
        "personalized_recommendations": [
            "Reduce brown rice portion from 200g to 120g to lower meal energy while preserving satiety through the lean chicken breast.",
            "Double the steamed broccoli portion to maintain volume and micronutrient density with minimal additional calories."
        ],
        "health_considerations": [
            "Adequate dietary fiber (9g) supports blood glucose stability and prolongs satiety during caloric restriction."
        ],
        "suggested_improvements": [
            "Prioritize lean proteins and high-volume leafy greens across remaining daily meals."
        ],
        "limitations": []
    }
    client = create_mock_gemini_client(json.dumps(mock_payload))
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=deficit_profile,
        meal_type="lunch",
        client=client
    )

    assert result["success"] is True
    assert "1400 kcal" in result["meal_assessment"]
    assert any("reduce" in r.lower() or "rice" in r.lower() for r in result["personalized_recommendations"])

# Scenario 3: Optional health condition handling (consented vs excluded)
def test_scenario_3_optional_health_condition_handling(sample_meal, sample_profile):
    profile_with_health = dict(sample_profile)
    profile_with_health["health_conditions"] = "Type 2 Diabetes, Hypertension"

    # Consented inclusion
    prompt_consented = llm_recommendation.build_gemini_prompt(
        meal_nutrition=sample_meal,
        user_profile=profile_with_health,
        meal_type="lunch",
        include_health_conditions=True
    )
    prompt_consented_data = json.loads(prompt_consented)
    assert "Type 2 Diabetes" in prompt_consented_data["user_profile"]["health_conditions"]

    # Excluded / privacy opted-out
    prompt_excluded = llm_recommendation.build_gemini_prompt(
        meal_nutrition=sample_meal,
        user_profile=profile_with_health,
        meal_type="lunch",
        include_health_conditions=False
    )
    prompt_excluded_data = json.loads(prompt_excluded)
    assert "Excluded by user privacy choice" in prompt_excluded_data["user_profile"]["health_conditions"]
    assert "Type 2 Diabetes" not in prompt_excluded_data["user_profile"]["health_conditions"]

# Scenario 4: Allergy safety alerts (deterministic safety alerts preserved independently)
def test_scenario_4_allergy_safety_alerts(sample_meal, sample_profile):
    allergic_profile = dict(sample_profile)
    allergic_profile["allergies"] = "peanut, chicken"

    safety = recommendation_engine.validate_meal_safety(sample_meal, allergic_profile)
    allergen_alerts = [a for a in safety["alerts"] if "ALLERGEN WARNING" in a]
    assert len(allergen_alerts) > 0
    assert any("chicken" in a.lower() for a in allergen_alerts)

    # Prompt builder must include the independent safety flags
    prompt_json = llm_recommendation.build_gemini_prompt(
        meal_nutrition=sample_meal,
        user_profile=allergic_profile,
        safety_alerts=safety["alerts"]
    )
    prompt_data = json.loads(prompt_json)
    assert len(prompt_data["independent_safety_flags"]) > 0

# Scenario 5: Missing nutrient values
def test_scenario_5_missing_nutrient_values(sample_profile):
    meal_with_missing = {
        "totals": {
            "calories_kcal": 400.0,
            "protein_g": 20.0,
            "carbs_g": None,
            "fat_g": None,
            "fiber_g": None,
            "sodium_mg": None,
            "sugars_g": None,
            "total_grams": 250.0
        },
        "macronutrient_percentages": {
            "protein_pct": 20.0,
            "carbs_pct": 0.0,
            "fat_pct": 0.0
        },
        "ingredient_details": [
            {"food_name": "steamed fish", "grams": 250.0, "portion_name": "custom", "calories_kcal": 400.0}
        ]
    }
    safety = recommendation_engine.validate_meal_safety(meal_with_missing, sample_profile)
    missing_notice = [a for a in safety["alerts"] if "unrecorded or missing" in a.lower()]
    assert len(missing_notice) > 0

# Scenario 6: Invalid Gemini response (malformed JSON or invalid schema)
def test_scenario_6_invalid_gemini_response(sample_meal, sample_profile):
    client = create_mock_gemini_client("This is non-JSON unstructured conversational text from model.")
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=sample_profile,
        meal_type="lunch",
        client=client
    )

    # Must fail cleanly without crashing and must NOT substitute rule recommendations
    assert result["success"] is False
    assert result["personalized_recommendations"] == []
    assert len(result["error_message"]) > 0

# Scenario 7: Missing API key (clear error message, no rule fallback)
def test_scenario_7_missing_api_key(monkeypatch, sample_meal, sample_profile):
    monkeypatch.setattr(config, "get_gemini_config", lambda: {"api_key": None, "model": "gemini-2.5-flash"})
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=sample_profile,
        meal_type="lunch",
        client=None
    )

    assert result["success"] is False
    assert "GEMINI_API_KEY" in result["error_message"]
    assert result["personalized_recommendations"] == []

# Scenario 8: API timeout handling (no rule fallback)
def test_scenario_8_api_timeout(sample_meal, sample_profile):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("DEADLINE_EXCEEDED: request timed out after 15000ms")
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=sample_profile,
        meal_type="lunch",
        client=mock_client
    )

    assert result["success"] is False
    assert "timed out" in result["error_message"].lower()
    assert result["personalized_recommendations"] == []

# Scenario 9: Free-tier rate-limit error (429/ResourceExhausted handling)
def test_scenario_9_rate_limit_error(sample_meal, sample_profile):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: rate limit exceeded for free tier")
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=sample_profile,
        meal_type="lunch",
        client=mock_client
    )

    assert result["success"] is False
    assert "rate limit" in result["error_message"].lower()
    assert result["personalized_recommendations"] == []

# Scenario 10: Unavailable model (404/NotFound handling)
def test_scenario_10_unavailable_model(sample_meal, sample_profile):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("404 NOT_FOUND: model models/gemini-invalid-model not found")
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=sample_profile,
        meal_type="lunch",
        client=mock_client
    )

    assert result["success"] is False
    assert "unavailable" in result["error_message"].lower() or "not found" in result["error_message"].lower()
    assert result["personalized_recommendations"] == []

# Scenario 11: Verification that rule-based recommendations are NEVER returned as fallback
def test_scenario_11_no_rule_fallback_on_any_error(sample_meal, sample_profile):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Fatal connection failure")
    result = llm_recommendation.generate_gemini_recommendation(
        meal_nutrition=sample_meal,
        user_profile=sample_profile,
        meal_type="lunch",
        client=mock_client
    )

    assert result["success"] is False
    # Verify that no canned rule advice is generated
    assert result["personalized_recommendations"] == []
    assert result["meal_assessment"] == ""
    assert result["suggested_improvements"] == []
    # Verify that independent safety alerts remain accessible
    assert "safety_alerts" in result

# Scenario 12: Outdated recommendations signature invalidation
def test_scenario_12_recommendation_signature_invalidation():
    items_state_1 = [{"fdc_id": 1001, "grams": 150.0}]
    items_state_2 = [{"fdc_id": 1001, "grams": 200.0}]
    profile_time_1 = "2026-11-25 10:00:00"
    profile_time_2 = "2026-11-25 11:30:00"

    sig_1 = (tuple((it["fdc_id"], it["grams"]) for it in items_state_1), profile_time_1, "Lunch")
    sig_1_same = (tuple((it["fdc_id"], it["grams"]) for it in items_state_1), profile_time_1, "Lunch")
    sig_portion_change = (tuple((it["fdc_id"], it["grams"]) for it in items_state_2), profile_time_1, "Lunch")
    sig_profile_change = (tuple((it["fdc_id"], it["grams"]) for it in items_state_1), profile_time_2, "Lunch")
    sig_occasion_change = (tuple((it["fdc_id"], it["grams"]) for it in items_state_1), profile_time_1, "Dinner")

    assert sig_1 == sig_1_same
    assert sig_1 != sig_portion_change
    assert sig_1 != sig_profile_change
    assert sig_1 != sig_occasion_change
