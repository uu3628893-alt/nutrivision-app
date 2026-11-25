"""
Rule-based dietary recommendation engine.
Evaluates meal nutritional composition against user profile, biometric targets, and dietary guidelines.
"""

from typing import Dict, List, Any

ALLERGEN_SYNONYMS = {
    "peanut": ["peanut", "peanuts", "groundnut", "arachis"],
    "tree nuts": ["tree nuts", "nut", "walnut", "almond", "cashew", "pistachio", "pecan", "hazelnut", "macadamia", "brazil nut"],
    "milk": ["milk", "dairy", "cheese", "butter", "cream", "yogurt", "whey", "casein", "custard"],
    "egg": ["egg", "eggs", "albumin", "mayonnaise"],
    "wheat": ["wheat", "gluten", "flour", "bread", "pasta", "noodle"],
    "soy": ["soy", "soya", "soybean", "tofu", "edamame", "tempeh"],
    "fish": ["fish", "salmon", "tuna", "cod", "trout", "halibut", "sardine", "tilapia", "bass", "anchovy"],
    "shellfish": ["shellfish", "crustacean", "shrimp", "prawn", "crab", "lobster", "clam", "mussel", "oyster", "scallop"]
}

def check_allergen_match(allergen: str, food_name: str) -> bool:
    allergen_clean = allergen.lower().strip()
    food_clean = food_name.lower().strip()
    synonyms = ALLERGEN_SYNONYMS.get(allergen_clean, [allergen_clean])
    for syn in synonyms:
        if syn in food_clean:
            return True
    return False

def generate_dietary_recommendations(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch"
) -> Dict[str, Any]:
    alerts = []
    recommendations = []
    positive_feedback = []
    health_notices = []
    assumed_portions = []
    
    totals = meal_nutrition.get("totals", {})
    percentages = meal_nutrition.get("macronutrient_percentages", {})
    ingredients = meal_nutrition.get("ingredient_details", [])
    
    # Check for missing nutrition data
    missing_nutrients = []
    for k in ["calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sodium_mg", "sugars_g"]:
        if totals.get(k) is None:
            missing_nutrients.append(k)
    if missing_nutrients:
        alerts.append("Notice: Some nutrient measurements are unrecorded or missing and should not be assumed to be zero.")

    meal_cal = float(totals.get("calories_kcal") or 0.0)
    meal_p = float(totals.get("protein_g") or 0.0)
    meal_c = float(totals.get("carbs_g") or 0.0)
    meal_f = float(totals.get("fat_g") or 0.0)
    meal_fiber = float(totals.get("fiber_g") or 0.0)
    meal_sodium = float(totals.get("sodium_mg") or 0.0)
    meal_sugar = float(totals.get("sugars_g") or 0.0)
    
    user_allergies = [a.lower().strip() for a in user_profile.get("allergies", "").split(",") if a.strip()]
    user_prefs = [p.lower().strip() for p in user_profile.get("preferences", "").split(",") if p.strip()]
    user_goal = str(user_profile.get("goal", "maintain")).lower()
    daily_cal_target = float(user_profile.get("target_calories") or 2000.0)
    user_age = int(user_profile.get("age") or 25)
    health_conds_str = str(user_profile.get("health_conditions") or "").lower()
    
    # 1. Allergen Screening with synonym expansion
    detected_names = [item.get("food_name", "").lower() for item in ingredients]
    for allergen in user_allergies:
        for fname in detected_names:
            if check_allergen_match(allergen, fname):
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

    # 3. Check for estimated / assumed portion sizes
    for item in ingredients:
        p_name = item.get("portion_name", "").lower()
        if "reference" in p_name or "custom" in p_name:
            assumed_portions.append(f"Assumed portion: '{item.get('food_name', '')}' evaluated at {item.get('grams', 0):.0f}g ({item.get('portion_name', 'standard portion')}).")

    # 4. Pediatric and Biometric Validation
    if user_age < 18:
        alerts.append("Age Notice: Adult BMI classifications and standardized adult energy calculations require cautious interpretation for individuals under 18 years.")
        
    user_weight = float(user_profile.get("weight_kg") or 0.0)
    user_height = float(user_profile.get("height_cm") or 0.0)
    if user_weight > 0 and user_height > 0:
        h_m = user_height / 100.0
        bmi_val = user_weight / (h_m ** 2)
        if bmi_val < 18.5 and user_goal in ["weight_loss", "fat loss", "cut"]:
            alerts.append("Safety Warning: Profile indicates underweight status. Calorie-restricted weight loss regimens are not recommended without professional supervision.")

    # 5. Meal Caloric Budget Allocation
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
        
    # 6. Macronutrient Distribution
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
        
    # 7. Dietary Fiber Sufficiency (consistent threshold and guidance)
    if meal_fiber < 8.0:
        recommendations.append(
            f"Dietary Fiber: This meal supplies {meal_fiber:.1f}g fiber (recommended: >= 8.0g per major meal). "
            f"Adding dark leafy vegetables, legumes, or whole grains will enhance glycemic control and digestive health."
        )
    else:
        positive_feedback.append(f"Excellent Fiber: Delivers {meal_fiber:.1f}g fiber, promoting cardiovascular and gastrointestinal wellness.")
        
    # 8. Sodium and Sugar Monitoring
    if meal_sodium > 800.0:
        recommendations.append(
            f"Sodium Moderation: Meal sodium ({meal_sodium:.0f} mg) exceeds 35% of the daily 2,300 mg limit. "
            f"Rinse canned ingredients or reduce added sodium to support healthy blood pressure."
        )
        
    if meal_sugar > 20.0:
        recommendations.append(
            f"Sugar Intake: Contains {meal_sugar:.1f}g sugars. Moderating high-sugar sauces or condiments supports steady insulin response."
        )

    # 9. Optional Health Considerations
    if "diabetes" in health_conds_str:
        if meal_c > 60.0 or meal_sugar > 15.0:
            health_notices.append("Glycemic Awareness: Carbohydrate and sugar content noted. Pairing carbohydrates with dietary fiber and lean protein helps modulate glycemic response.")
        else:
            health_notices.append("Glycemic Balance: Moderate carbohydrate density observed, supporting stable postprandial glucose levels.")
            
    if "high blood pressure" in health_conds_str or "hypertension" in health_conds_str:
        if meal_sodium > 600.0:
            health_notices.append(f"Sodium Awareness: High blood pressure consideration noted. This meal supplies {meal_sodium:.0f} mg sodium; limiting sodium to under 600 mg per meal supports cardiovascular wellness.")
        else:
            health_notices.append("Sodium Prudence: Meal sodium is within moderate limits, consistent with blood pressure management principles.")
            
    if "kidney" in health_conds_str or "renal" in health_conds_str:
        health_notices.append("Renal Consideration: Kidney health consideration noted. Individual electrolyte (potassium, sodium) and protein targets should be coordinated with your renal specialist.")

    return {
        "alerts": alerts,
        "recommendations": recommendations,
        "positive_feedback": positive_feedback,
        "health_notices": health_notices,
        "assumed_portions": assumed_portions,
        "meal_calorie_budget": round(meal_cal_budget, 1),
        "disclaimer": "These recommendations provide general nutritional guidance for informational purposes and do not replace professional medical advice, diagnosis, or treatment."
    }
