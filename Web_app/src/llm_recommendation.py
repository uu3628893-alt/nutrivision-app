"""
Google Gemini-powered personalized dietary recommendation module.
Sole generator of personalized, context-aware dietary recommendations in NutriVision.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src import config
from src import recommendation_engine

logger = logging.getLogger(__name__)

class DietaryRecommendationSchema(BaseModel):
    meal_assessment: str = Field(
        description="A concise explanation of the meal's estimated nutritional composition and energy balance."
    )
    personalized_recommendations: List[str] = Field(
        description="Practical dietary recommendations and adjustments aligned with the user's goals and preferences."
    )
    health_considerations: List[str] = Field(
        description="Appropriate general nutritional considerations based on voluntarily shared health conditions."
    )
    suggested_improvements: List[str] = Field(
        description="Specific ingredient substitutions, portion modifications, or meal-balance enhancements."
    )
    limitations: List[str] = Field(
        description="Transparent limitations regarding missing nutrient data, ambiguous items, or assumed portions."
    )

GEMINI_SYSTEM_INSTRUCTION = """You are an evidence-based clinical nutrition analysis assistant for an academic research prototype.
Analyze the supplied meal nutrition data, ingredient details, and anonymized user profile.
Generate personalized, context-aware, cautious dietary recommendations.

Follow these strict constraints:
1. You are the sole generator of personalized dietary recommendations.
2. Ground all advice strictly in the provided nutrient values, ingredients, and stated user goals.
3. Do not invent nutrients, unlisted ingredients, medical diagnoses, medication recommendations, or clinical treatment plans.
4. If an ingredient portion is flagged as estimated or assumed, explicitly acknowledge that limitation.
5. If health conditions are disclosed with consent, offer cautious general dietary context only. Never claim clinical approval.
6. If allergen warnings are present, ensure your suggestions strictly respect those exclusions.
7. Provide actionable, practical adjustments (e.g. food swaps, portion adjustments).
8. Return strictly structured JSON matching the provided schema.
"""

def build_gemini_prompt(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch",
    include_health_conditions: bool = True,
    safety_alerts: Optional[List[str]] = None
) -> str:
    totals = meal_nutrition.get("totals", {})
    percentages = meal_nutrition.get("macronutrient_percentages", {})
    ingredients = meal_nutrition.get("ingredient_details", [])
    
    # Anonymized user details only (no personal names, emails, or identifiers)
    user_payload = {
        "age": user_profile.get("age", "Unknown"),
        "biological_sex": user_profile.get("sex", "Unknown"),
        "activity_level": user_profile.get("activity_level", "Unknown"),
        "dietary_goal": user_profile.get("goal", "maintain"),
        "daily_calorie_target": user_profile.get("target_calories", 2000),
        "declared_allergies": user_profile.get("allergies", "None"),
        "dietary_preferences": user_profile.get("preferences", "None"),
        "health_conditions": user_profile.get("health_conditions", "None disclosed") if include_health_conditions else "Excluded by user privacy choice"
    }
    
    ingredient_summary = []
    for item in ingredients:
        ingredient_summary.append({
            "food_name": item.get("food_name", "Unknown"),
            "grams": round(float(item.get("grams", 0.0)), 1),
            "portion_description": item.get("portion_name", "standard reference"),
            "calories_kcal": round(float(item.get("calories_kcal", 0.0)), 1),
            "protein_g": round(float(item.get("protein_g", 0.0)), 1),
            "carbs_g": round(float(item.get("carbs_g", 0.0)), 1),
            "fat_g": round(float(item.get("fat_g", 0.0)), 1)
        })
        
    meal_summary = {
        "meal_type": meal_type,
        "ingredients": ingredient_summary,
        "nutritional_totals": {
            "calories_kcal": totals.get("calories_kcal"),
            "protein_g": totals.get("protein_g"),
            "carbohydrates_g": totals.get("carbs_g"),
            "fat_g": totals.get("fat_g"),
            "fiber_g": totals.get("fiber_g"),
            "sodium_mg": totals.get("sodium_mg"),
            "sugars_g": totals.get("sugars_g")
        },
        "macronutrient_percentages": {
            "protein_pct": percentages.get("protein_pct", 0.0),
            "carbs_pct": percentages.get("carbs_pct", percentages.get("carb_pct", 0.0)),
            "fat_pct": percentages.get("fat_pct", 0.0)
        }
    }
    
    request_data = {
        "user_profile": user_payload,
        "meal_analysis": meal_summary,
        "independent_safety_flags": safety_alerts or []
    }
    
    return json.dumps(request_data, indent=2)

def generate_gemini_recommendation(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch",
    include_health_conditions: bool = True,
    client: Optional[Any] = None
) -> Dict[str, Any]:
    # Run deterministic safety validation
    safety_results = recommendation_engine.validate_meal_safety(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type=meal_type
    )
    safety_alerts = safety_results.get("alerts", [])
    assumed_portions = safety_results.get("assumed_portions", [])
    
    gemini_conf = config.get_gemini_config()
    api_key = gemini_conf.get("api_key")
    model_name = gemini_conf.get("model", config.GEMINI_DEFAULT_MODEL)
    
    # Strictly purely LLM-based: fail clearly if API key is not configured
    if not api_key and client is None:
        return {
            "success": False,
            "source": "gemini",
            "error_message": "Google Gemini API key not configured. Please set the GEMINI_API_KEY environment variable or Streamlit secret to generate personalised recommendations.",
            "meal_assessment": "",
            "personalized_recommendations": [],
            "health_considerations": [],
            "suggested_improvements": [],
            "limitations": [],
            "safety_alerts": safety_alerts,
            "assumed_portions": assumed_portions,
            "model_used": model_name
        }

    prompt = build_gemini_prompt(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type=meal_type,
        include_health_conditions=include_health_conditions,
        safety_alerts=safety_alerts
    )

    try:
        if client is None:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
        else:
            from google.genai import types

        req_config = types.GenerateContentConfig(
            system_instruction=GEMINI_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=DietaryRecommendationSchema,
            temperature=gemini_conf.get("temperature", 0.2),
            max_output_tokens=gemini_conf.get("max_output_tokens", 1200)
        )

        models_to_try = [model_name]
        if client is None and model_name != "gemini-3.5-flash-lite":
            models_to_try.append("gemini-3.5-flash-lite")

        response = None
        used_model = model_name
        for m in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=req_config
                )
                used_model = m
                break
            except Exception as e:
                err_text = str(e)
                if ("NOT_FOUND" in err_text or "404" in err_text or "no longer available" in err_text.lower()) and len(models_to_try) > 1 and m != models_to_try[-1]:
                    logger.warning("Configured model %s unavailable for user key, trying %s", m, models_to_try[-1])
                    continue
                raise e

        raw_text = getattr(response, "text", "") or ""
        
        # Parse and validate response against Pydantic schema
        try:
            parsed = DietaryRecommendationSchema.model_validate_json(raw_text)
        except Exception:
            # Fallback direct json parse
            data = json.loads(raw_text)
            parsed = DietaryRecommendationSchema.model_validate(data)

        # Append portion assumptions to limitations if not present
        limitations = list(parsed.limitations)
        for ap in assumed_portions:
            if not any(ap in l for l in limitations):
                limitations.append(ap)
                
        limitations.append("Educational Prototype Notice: Recommendations provide general dietary guidance and do not replace professional healthcare advice.")

        return {
            "success": True,
            "source": "gemini",
            "meal_assessment": parsed.meal_assessment,
            "personalized_recommendations": parsed.personalized_recommendations,
            "health_considerations": parsed.health_considerations,
            "suggested_improvements": parsed.suggested_improvements,
            "limitations": limitations,
            "safety_alerts": safety_alerts,
            "assumed_portions": assumed_portions,
            "raw_text": raw_text,
            "model_used": used_model
        }

    except Exception as exc:
        err_type = type(exc).__name__
        err_str = str(exc)
        logger.error("Gemini recommendation request failed: %s", err_type)
        
        # User-friendly error message mapping without leaking sensitive credentials
        if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "Quota" in err_str:
            user_msg = "Google Gemini rate limit reached (Free Tier quota). Please wait a moment and try again."
        elif "NOT_FOUND" in err_str or "404" in err_str or "model" in err_str.lower():
            user_msg = f"Configured Gemini model '{model_name}' is unavailable. Please check the GEMINI_MODEL setting."
        elif "DEADLINE_EXCEEDED" in err_str or "timeout" in err_str.lower():
            user_msg = "The request to Google Gemini timed out. Please verify network connectivity and try again."
        elif "API_KEY_INVALID" in err_str or "unauthenticated" in err_str.lower():
            user_msg = "Invalid Google Gemini API key. Please check your GEMINI_API_KEY credential."
        else:
            user_msg = f"Google Gemini is temporarily unavailable ({err_type}). Please try again."

        return {
            "success": False,
            "source": "gemini",
            "error_message": user_msg,
            "meal_assessment": "",
            "personalized_recommendations": [],
            "health_considerations": [],
            "suggested_improvements": [],
            "limitations": [],
            "safety_alerts": safety_alerts,
            "assumed_portions": assumed_portions,
            "model_used": model_name
        }

# Retain backward compatible alias
def generate_llm_recommendation(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch",
    client: Optional[Any] = None
) -> Dict[str, Any]:
    return generate_gemini_recommendation(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type=meal_type,
        include_health_conditions=True,
        client=client
    )
