"""
Nutritional calculation engine for portion scaling and multi-ingredient meal aggregation.
"""

from typing import Dict, List, Any
from src.nutrition_database import get_food_nutrition

def calculate_ingredient_nutrition(fdc_id: int, grams: float) -> Dict[str, float]:
    """
    Calculate nutrient amounts for an ingredient based on selected gram weight.
    Formula: Nutrient Amount = (Nutrient per 100g * Grams) / 100
    """
    nutr = get_food_nutrition(fdc_id)
    if not nutr or grams <= 0:
        return {
            "calories_kcal": 0.0,
            "protein_g": 0.0,
            "fat_g": 0.0,
            "carbs_g": 0.0,
            "fiber_g": 0.0,
            "sugars_g": 0.0,
            "sodium_mg": 0.0
        }
        
    factor = grams / 100.0
    return {
        "calories_kcal": round(float(nutr.get("calories_kcal", 0.0)) * factor, 1),
        "protein_g": round(float(nutr.get("protein_g", 0.0)) * factor, 2),
        "fat_g": round(float(nutr.get("fat_g", 0.0)) * factor, 2),
        "carbs_g": round(float(nutr.get("carbs_g", 0.0)) * factor, 2),
        "fiber_g": round(float(nutr.get("fiber_g", 0.0)) * factor, 2),
        "sugars_g": round(float(nutr.get("sugars_g", 0.0)) * factor, 2),
        "sodium_mg": round(float(nutr.get("sodium_mg", 0.0)) * factor, 1)
    }

def calculate_meal_nutrition(ingredients: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate aggregate nutrition across multiple meal ingredients.
    Calculates macronutrient calorie distributions and percentage shares.
    """
    totals = {
        "total_grams": 0.0,
        "calories_kcal": 0.0,
        "protein_g": 0.0,
        "fat_g": 0.0,
        "carbs_g": 0.0,
        "fiber_g": 0.0,
        "sugars_g": 0.0,
        "sodium_mg": 0.0
    }
    
    ingredient_details = []
    
    for item in ingredients:
        fdc_id = item.get("fdc_id")
        grams = float(item.get("grams", 0.0))
        name = item.get("food_name", "Unknown Food")
        portion_name = item.get("portion_name", f"{grams}g")
        class_id = item.get("class_id")
        
        item_nutr = calculate_ingredient_nutrition(fdc_id, grams)
        
        detail = {
            "class_id": class_id,
            "food_name": name,
            "fdc_id": fdc_id,
            "portion_name": portion_name,
            "grams": grams,
            **item_nutr
        }
        ingredient_details.append(detail)
        
        totals["total_grams"] += grams
        totals["calories_kcal"] += item_nutr["calories_kcal"]
        totals["protein_g"] += item_nutr["protein_g"]
        totals["fat_g"] += item_nutr["fat_g"]
        totals["carbs_g"] += item_nutr["carbs_g"]
        totals["fiber_g"] += item_nutr["fiber_g"]
        totals["sugars_g"] += item_nutr["sugars_g"]
        totals["sodium_mg"] += item_nutr["sodium_mg"]
        
    for k in totals:
        totals[k] = round(totals[k], 1)
        
    # Macronutrient energy contribution (Atwater general factors)
    prot_cal = totals["protein_g"] * 4.0
    carb_cal = totals["carbs_g"] * 4.0
    fat_cal = totals["fat_g"] * 9.0
    total_macro_cal = max(prot_cal + carb_cal + fat_cal, 1.0)
    
    macro_pct = {
        "protein_pct": round((prot_cal / total_macro_cal) * 100.0, 1),
        "carbs_pct": round((carb_cal / total_macro_cal) * 100.0, 1),
        "fat_pct": round((fat_cal / total_macro_cal) * 100.0, 1)
    }
    
    return {
        "totals": totals,
        "macronutrient_percentages": macro_pct,
        "macronutrient_calories": {
            "protein_kcal": round(prot_cal, 1),
            "carbs_kcal": round(carb_cal, 1),
            "fat_kcal": round(fat_cal, 1)
        },
        "ingredient_details": ingredient_details
    }

