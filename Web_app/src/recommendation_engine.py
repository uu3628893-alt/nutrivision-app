"""
Rule-based clinical dietary recommendation engine.
Evaluates meal nutritional composition against user profile, biometric targets, and clinical guidelines.
"""

from typing import Dict, List, Any

def generate_dietary_recommendations(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch"
) -> Dict[str, Any]:
    """
    Generate actionable, evidence-based recommendations and allergen warnings.
    """
    alerts = []
    recommendations = []
    positive_feedback = []
    
    totals = meal_nutrition.get("totals", {})
    percentages = meal_nutrition.get("macronutrient_percentages", {})
    ingredients = meal_nutrition.get("ingredient_details", [])
    
    meal_cal = totals.get("calories_kcal", 0.0)
    meal_p = totals.get("protein_g", 0.0)
    meal_c = totals.get("carbs_g", 0.0)
    meal_f = totals.get("fat_g", 0.0)
    meal_fiber = totals.get("fiber_g", 0.0)
    meal_sodium = totals.get("sodium_mg", 0.0)
    meal_sugar = totals.get("sugars_g", 0.0)
    
    user_allergies = [a.lower().strip() for a in user_profile.get("allergies", "").split(",") if a.strip()]
    user_prefs = [p.lower().strip() for p in user_profile.get("preferences", "").split(",") if p.strip()]
    user_goal = user_profile.get("goal", "maintain").lower()
    daily_cal_target = float(user_profile.get("target_calories", 2000.0))
    
    # 1. Allergen Screening (Safety Critical)
    detected_names = [item.get("food_name", "").lower() for item in ingredients]
    for allergen in user_allergies:
        for fname in detected_names:
            if allergen in fname:
                alerts.append(f"ALLERGEN WARNING: Detected '{fname}' matches your declared exclusion for '{allergen}'.")
                
    # 2. Preference Screening
    if "vegetarian" in user_prefs or "vegan" in user_prefs:
        animal_terms = ["chicken", "beef", "steak", "pork", "fish", "shrimp", "duck", "lamb", "crab", "shellfish"]
        for fname in detected_names:
            if any(term in fname for term in animal_terms):
                alerts.append(f"DIETARY PREFERENCE ALERT: '{fname}' contains animal meat inconsistent with a vegetarian/vegan diet.")
    if "vegan" in user_prefs:
        dairy_terms = ["milk", "cheese", "butter", "egg", "cream", "yogurt"]
        for fname in detected_names:
            if any(term in fname for term in dairy_terms):
                alerts.append(f"DIETARY PREFERENCE ALERT: '{fname}' contains dairy or egg products.")

    # 3. Meal Caloric Budget Allocation
    budget_fractions = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.35, "snack": 0.15}
    frac = budget_fractions.get(meal_type.lower(), 0.35)
    meal_cal_budget = daily_cal_target * frac
    cal_diff = meal_cal - meal_cal_budget
    
    if cal_diff > 150:
        recommendations.append(
            f"Caloric Surplus: This meal ({meal_cal:.0f} kcal) exceeds your allocated {meal_type} target "
            f"({meal_cal_budget:.0f} kcal) by {cal_diff:.0f} kcal. Consider moderating portion sizes of energy-dense sides."
        )
    elif cal_diff < -200 and meal_cal > 0:
        recommendations.append(
            f"Caloric Deficit: This meal provides only {meal_cal:.0f} kcal versus your allocated target of {meal_cal_budget:.0f} kcal. "
            f"Ensure adequate nutritional volume to avoid hunger and subsequent compensatory overconsumption."
        )
    else:
        positive_feedback.append(
            f"Optimal Energy: Meal energy ({meal_cal:.0f} kcal) aligns with your target {meal_type} budget ({meal_cal_budget:.0f} kcal)."
        )
        
    # 4. Macronutrient Distribution
    p_pct = percentages.get("protein_pct", 0.0)
    c_pct = percentages.get("carbs_pct", 0.0)
    f_pct = percentages.get("fat_pct", 0.0)
    
    if user_goal in ["weight_loss", "fat loss"] and p_pct < 25.0:
        recommendations.append(
            f"Protein Optimization: Protein represents {p_pct:.1f}% of energy. Increasing protein to at least 25% "
            f"(e.g., adding skinless poultry, egg whites, or tofu) enhances satiety and lean mass preservation during fat loss."
        )
    elif user_goal in ["muscle_gain", "hypertrophy"] and p_pct < 20.0:
        recommendations.append(
            f"Hypertrophy Target: Protein is {p_pct:.1f}%. Aim for 20-30% of meal calories from protein to stimulate muscle protein synthesis."
        )
    elif p_pct >= 20.0:
        positive_feedback.append(f"Substantial Protein: Protein accounts for {p_pct:.1f}% of calories, supporting muscle repair and satiety.")
        
    if f_pct > 35.0:
        recommendations.append(
            f"Fat Density: Dietary fat represents {f_pct:.1f}% of energy (AMDR range: 20-35%). "
            f"Consider trimming visible fats or reducing added cooking oils."
        )
        
    # 5. Dietary Fiber Sufficiency
    if meal_fiber < 6.0:
        recommendations.append(
            f"Dietary Fiber: This meal supplies {meal_fiber:.1f}g fiber (recommended: >= 8g per major meal). "
            f"Adding dark leafy vegetables, legumes, or whole grains will enhance glycemic control and digestive health."
        )
    else:
        positive_feedback.append(f"Excellent Fiber: Delivers {meal_fiber:.1f}g fiber, promoting cardiovascular and gastrointestinal wellness.")
        
    # 6. Sodium and Sugar Monitoring
    if meal_sodium > 800.0:
        recommendations.append(
            f"Sodium Moderation: Meal sodium ({meal_sodium:.0f} mg) exceeds 35% of the daily 2,300 mg limit. "
            f"Rinse canned ingredients or reduce added sodium to support healthy blood pressure."
        )
        
    if meal_sugar > 20.0:
        recommendations.append(
            f"Sugar Intake: Contains {meal_sugar:.1f}g sugars. Moderating high-sugar sauces or condiments supports steady insulin response."
        )

    return {
        "alerts": alerts,
        "recommendations": recommendations,
        "positive_feedback": positive_feedback,
        "meal_calorie_budget": round(meal_cal_budget, 1)
    }

