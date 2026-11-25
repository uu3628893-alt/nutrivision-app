"""
LLM-based dietary recommendation module.
Interacts with OpenAI-compatible APIs to provide personalized dietary guidance.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from src import config
from src import recommendation_engine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a clinical nutrition analysis assistant for an academic research prototype.
Analyze the provided structured meal nutrition data and user profile.
Generate personalized, evidence-based, cautious dietary recommendations.

Follow these strict clinical constraints:
1. Do not invent nutrients, ingredients, medical diagnoses, medication recommendations, or treatment plans.
2. Ground all commentary in the supplied nutritional values, ingredient list, and user goals.
3. If an ingredient portion is marked as assumed or estimated, acknowledge the uncertainty.
4. If health conditions are provided, offer cautious dietary context only. State clearly that this is general guidance, not medical advice.
5. If allergens are flagged, emphasize them prominently. Do not contradict allergen warnings.
6. Provide actionable, practical adjustments (e.g. food swaps, portion modifications).
7. Respond strictly in valid JSON format matching this schema:
{
  "meal_assessment": "Concise evaluation of the meal estimated nutritional composition and caloric balance.",
  "personalized_suggestions": ["Actionable adjustment 1", "Actionable adjustment 2"],
  "health_considerations": ["Cautious dietary observation reflecting health conditions or preferences"],
  "important_notices": ["Portion assumptions, missing nutrient data, or safety limitations"]
}
"""

def build_user_prompt(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch",
    rule_results: Optional[Dict[str, Any]] = None
) -> str:
    totals = meal_nutrition.get("totals", {})
    percentages = meal_nutrition.get("macronutrient_percentages", {})
    ingredients = meal_nutrition.get("ingredient_details", [])
    
    # Anonymized user details only (no personal names, emails, or identifiers)
    user_info = {
        "age": user_profile.get("age", "Unknown"),
        "biological_sex": user_profile.get("sex", "Unknown"),
        "activity_level": user_profile.get("activity_level", "Unknown"),
        "dietary_goal": user_profile.get("goal", "maintain"),
        "daily_calorie_target": user_profile.get("target_calories", 2000),
        "declared_allergies": user_profile.get("allergies", "None"),
        "food_preferences": user_profile.get("preferences", "None"),
        "health_conditions": user_profile.get("health_conditions", "None disclosed")
    }
    
    ingredient_summary = []
    for item in ingredients:
        ingredient_summary.append({
            "food_name": item.get("food_name", "Unknown"),
            "grams": round(float(item.get("grams", 0.0)), 1),
            "portion_description": item.get("portion_name", "standard reference"),
            "calories_kcal": round(float(item.get("calories_kcal", 0.0)), 1)
        })
        
    meal_summary = {
        "meal_type": meal_type,
        "ingredients": ingredient_summary,
        "nutritional_totals": {
            "calories_kcal": totals.get("calories_kcal", 0.0),
            "protein_g": totals.get("protein_g", 0.0),
            "carbohydrates_g": totals.get("carbs_g", 0.0),
            "fat_g": totals.get("fat_g", 0.0),
            "fiber_g": totals.get("fiber_g", 0.0),
            "sodium_mg": totals.get("sodium_mg", 0.0),
            "sugars_g": totals.get("sugars_g", 0.0)
        },
        "macronutrient_distribution": {
            "protein_pct": percentages.get("protein_pct", 0.0),
            "carbs_pct": percentages.get("carbs_pct", 0.0),
            "fat_pct": percentages.get("fat_pct", 0.0)
        }
    }
    
    rule_alerts = rule_results.get("alerts", []) if rule_results else []
    
    payload = {
        "user_profile": user_info,
        "meal_data": meal_summary,
        "rule_based_alerts": rule_alerts
    }
    
    return json.dumps(payload, indent=2)

def generate_fallback_recommendation(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch",
    reason: str = ""
) -> Dict[str, Any]:
    rule_results = recommendation_engine.generate_dietary_recommendations(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type=meal_type
    )
    
    totals = meal_nutrition.get("totals", {})
    cal = round(float(totals.get("calories_kcal") or 0.0))
    p = round(float(totals.get("protein_g") or 0.0), 1)
    c = round(float(totals.get("carbs_g") or 0.0), 1)
    f = round(float(totals.get("fat_g") or 0.0), 1)
    
    meal_assessment = (
        f"This {meal_type} provides an estimated {cal} kcal (Protein: {p}g, "
        f"Carbohydrates: {c}g, Fat: {f}g). Evaluated using deterministic clinical guidelines."
    )
    
    suggestions = list(rule_results.get("recommendations", []))
    if not suggestions and rule_results.get("positive_feedback"):
        suggestions = list(rule_results.get("positive_feedback", []))
        
    health_conds = list(rule_results.get("health_notices", []))
    if not health_conds:
        health_conds.append("No specific health considerations identified for this nutritional profile.")
        
    important_notices = list(rule_results.get("alerts", []))
    important_notices.extend(rule_results.get("assumed_portions", []))
    if reason:
        important_notices.append(f"Notice: {reason}")
    important_notices.append(rule_results.get("disclaimer", "Recommendations provide general nutritional guidance."))
    
    return {
        "success": True,
        "source": "rule_based_fallback",
        "meal_assessment": meal_assessment,
        "personalized_suggestions": suggestions if suggestions else ["Maintain balanced portion sizes consistent with your caloric goal."],
        "health_considerations": health_conds,
        "important_notices": important_notices,
        "safety_alerts": rule_results.get("alerts", []),
        "raw_text": "",
        "model_used": "rule_based_engine"
    }

def parse_llm_response(raw_text: str) -> Optional[Dict[str, Any]]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None

def generate_llm_recommendation(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch",
    client: Optional[Any] = None
) -> Dict[str, Any]:
    # Compute deterministic rule-based checks first for safety baseline
    rule_results = recommendation_engine.generate_dietary_recommendations(
        meal_nutrition=meal_nutrition,
        user_profile=user_profile,
        meal_type=meal_type
    )
    safety_alerts = rule_results.get("alerts", [])
    assumed_portions = rule_results.get("assumed_portions", [])
    
    llm_conf = config.get_llm_config()
    api_key = llm_conf.get("api_key")
    
    if not api_key and client is None:
        fallback = generate_fallback_recommendation(
            meal_nutrition, user_profile, meal_type,
            reason=""
        )
        return fallback
        
    user_prompt = build_user_prompt(meal_nutrition, user_profile, meal_type, rule_results)
    
    try:
        if client is None:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                timeout=llm_conf.get("timeout", 15)
            )
            
        model_name = llm_conf.get("model", "gpt-4o-mini")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=llm_conf.get("temperature", 0.2),
            max_tokens=llm_conf.get("max_tokens", 700),
            timeout=llm_conf.get("timeout", 15)
        )
        
        raw_content = response.choices[0].message.content or ""
        parsed = parse_llm_response(raw_content)
        
        if not parsed:
            # Fallback if parsing fails
            fallback = generate_fallback_recommendation(
                meal_nutrition, user_profile, meal_type,
                reason="LLM response format could not be parsed into structured format. Displaying rule-based baseline."
            )
            fallback["raw_text"] = raw_content
            return fallback
            
        # Ensure independent safety warnings are never suppressed
        important_notices = parsed.get("important_notices", [])
        if isinstance(important_notices, str):
            important_notices = [important_notices]
            
        for alert in safety_alerts:
            if not any(alert in item for item in important_notices):
                important_notices.insert(0, alert)
                
        for port_note in assumed_portions:
            if not any(port_note in item for item in important_notices):
                important_notices.append(port_note)
                
        important_notices.append("General Guidance: Recommendations do not replace professional medical advice.")
        
        suggestions = parsed.get("personalized_suggestions", [])
        if isinstance(suggestions, str):
            suggestions = [suggestions]
            
        health_cons = parsed.get("health_considerations", [])
        if isinstance(health_cons, str):
            health_cons = [health_cons]
            
        return {
            "success": True,
            "source": "llm",
            "meal_assessment": parsed.get("meal_assessment", "Nutritional evaluation completed."),
            "personalized_suggestions": suggestions,
            "health_considerations": health_cons,
            "important_notices": important_notices,
            "safety_alerts": safety_alerts,
            "raw_text": raw_content,
            "model_used": model_name
        }
        
    except Exception as exc:
        err_msg = str(exc)
        logger.warning("LLM recommendation call encountered an error: %s", err_msg)
        fallback = generate_fallback_recommendation(
            meal_nutrition, user_profile, meal_type,
            reason=f"LLM service unavailable ({type(exc).__name__}). Showing rule-based clinical recommendation."
        )
        fallback["error_message"] = err_msg
        return fallback
