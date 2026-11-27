"""
Deterministic nutritional safety and allergy screening module.
Performs deterministic safety validation, allergen conflict detection, and portion checks.
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

def validate_meal_safety(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch"
) -> Dict[str, Any]:
    # Evaluates deterministic clinical exclusions, allergen conflicts, and data integrity
    alerts = []
    assumed_portions = []
    
    totals = meal_nutrition.get("totals", {})
    ingredients = meal_nutrition.get("ingredient_details", [])
    
    # 1. Missing data validation
    missing_nutrients = []
    for k in ["calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sodium_mg", "sugars_g"]:
        if totals.get(k) is None:
            missing_nutrients.append(k)
    if missing_nutrients:
        alerts.append("Notice: Some nutrient measurements are unrecorded or missing in the database and should not be assumed to be zero.")

    user_allergies = [a.lower().strip() for a in user_profile.get("allergies", "").split(",") if a.strip()]
    user_prefs = [p.lower().strip() for p in user_profile.get("preferences", "").split(",") if p.strip()]
    user_goal = str(user_profile.get("goal", "maintain")).lower()
    user_age = int(user_profile.get("age") or 25)
    
    # 2. Allergen Screening with synonym expansion
    detected_names = [item.get("food_name", "").lower() for item in ingredients]
    for allergen in user_allergies:
        for fname in detected_names:
            if check_allergen_match(allergen, fname):
                alerts.append(f"ALLERGEN WARNING: Detected '{fname}' matches your declared exclusion for '{allergen}'.")
                
    # 3. Dietary Philosophy Screening
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

    # 4. Portion estimation check
    for item in ingredients:
        p_name = item.get("portion_name", "").lower()
        if "reference" in p_name or "custom" in p_name:
            assumed_portions.append(f"Assumed portion: '{item.get('food_name', '')}' evaluated at {item.get('grams', 0):.0f}g ({item.get('portion_name', 'standard portion')}).")

    # 5. Biometric and age safety validation
    if user_age < 18:
        alerts.append("Age Notice: Adult BMI classifications and standardized adult energy calculations require cautious interpretation for individuals under 18 years.")
        
    user_weight = float(user_profile.get("weight_kg") or 0.0)
    user_height = float(user_profile.get("height_cm") or 0.0)
    if user_weight > 0 and user_height > 0:
        h_m = user_height / 100.0
        bmi_val = user_weight / (h_m ** 2)
        if bmi_val < 18.5 and user_goal in ["weight_loss", "fat loss", "cut"]:
            alerts.append("Safety Warning: Profile indicates underweight status. Calorie-restricted weight loss regimens are not recommended without professional supervision.")

    return {
        "alerts": alerts,
        "assumed_portions": assumed_portions,
        "recommendations": [],
        "disclaimer": "These safety checks provide general nutritional screening and do not replace professional medical advice."
    }

def generate_dietary_recommendations(
    meal_nutrition: Dict[str, Any],
    user_profile: Dict[str, Any],
    meal_type: str = "lunch"
) -> Dict[str, Any]:
    # Compatibility wrapper returning safety validation
    return validate_meal_safety(meal_nutrition, user_profile, meal_type)
