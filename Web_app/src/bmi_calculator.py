"""
Body Mass Index (BMI) and physiological energy requirement calculator.
Implements the Mifflin-St Jeor equation and WHO adult BMI categorization.
"""

from typing import Dict, Tuple, Any

def calculate_bmi(weight_kg: float, height_cm: float) -> Tuple[float, str, str]:
    """
    Calculate adult Body Mass Index (BMI) and assign WHO classification.
    Returns (bmi_value, category_name, description).
    """
    if height_cm <= 0 or weight_kg <= 0:
        return 0.0, "Invalid biometrics", "Height and weight must be greater than zero."
        
    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m ** 2), 2)
    
    if bmi < 18.5:
        category = "Underweight"
        desc = "Below standard physiological weight range. May indicate undernutrition or elevated health risks."
    elif bmi < 25.0:
        category = "Normal weight"
        desc = "Within optimal adult weight range associated with lowest statistical morbidity risk."
    elif bmi < 30.0:
        category = "Overweight"
        desc = "Modestly elevated weight relative to height. Dietary and physical activity optimization advised."
    elif bmi < 35.0:
        category = "Obesity Class I"
        desc = "Class I obesity. Increased cardiometabolic and cardiovascular risk profile."
    elif bmi < 40.0:
        category = "Obesity Class II"
        desc = "Class II severe obesity. Structured lifestyle or clinical intervention indicated."
    else:
        category = "Obesity Class III"
        desc = "Class III severe/morbid obesity. High cardiometabolic risk requiring clinical supervision."
        
    return bmi, category, desc

def calculate_ree_mifflin_st_jeor(weight_kg: float, height_cm: float, age_years: int, sex: str) -> float:
    """
    Estimate Resting Energy Expenditure (REE / BMR) using the clinically validated Mifflin-St Jeor equation.
    Men:   REE = 10 * weight (kg) + 6.25 * height (cm) - 5 * age (y) + 5
    Women: REE = 10 * weight (kg) + 6.25 * height (cm) - 5 * age (y) - 161
    """
    if weight_kg <= 0 or height_cm <= 0 or age_years <= 0:
        return 0.0
        
    base = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age_years
    if sex.lower().startswith("m"):
        ree = base + 5.0
    else:
        ree = base - 161.0
    return round(max(ree, 500.0), 1)

def calculate_tdee(ree: float, activity_multiplier: float) -> float:
    """Calculate Total Daily Energy Expenditure (TDEE)."""
    return round(ree * activity_multiplier, 1)

def calculate_nutritional_targets(tdee: float, goal: str = "maintain") -> Dict[str, Any]:
    """
    Compute daily calorie and macronutrient targets based on physiological goal.
    Conforms to Acceptable Macronutrient Distribution Ranges (AMDR).
    """
    g = goal.lower()
    if g in ["weight_loss", "fat loss", "cut"]:
        target_calories = max(tdee - 500.0, 1200.0)
        p_pct, c_pct, f_pct = 30.0, 40.0, 30.0
    elif g in ["muscle_gain", "hypertrophy", "bulk"]:
        target_calories = tdee + 350.0
        p_pct, c_pct, f_pct = 25.0, 50.0, 25.0
    else: # maintenance
        target_calories = tdee
        p_pct, c_pct, f_pct = 20.0, 50.0, 30.0
        
    # Convert calories to grams: Protein = 4 kcal/g, Carbs = 4 kcal/g, Fat = 9 kcal/g
    protein_g = round((target_calories * (p_pct / 100.0)) / 4.0, 1)
    carbs_g = round((target_calories * (c_pct / 100.0)) / 4.0, 1)
    fat_g = round((target_calories * (f_pct / 100.0)) / 9.0, 1)
    
    return {
        "target_calories": round(target_calories, 1),
        "target_macros": {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "fiber_g": 28.0,
            "sodium_max_mg": 2300.0
        },
        "target_percentages": {
            "protein_pct": p_pct,
            "carbs_pct": c_pct,
            "fat_pct": f_pct
        }
    }

