import sys
from pathlib import Path
import pytest

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src import nutrition_calculator
from src import nutrition_database
from src import bmi_calculator
from src import recommendation_engine


def test_ingredient_calculation():
    food_df = nutrition_database.get_nutrition_db()
    sample_fdc = int(food_df['fdc_id'].iloc[0])
    nutr_100g = nutrition_database.get_food_nutrition(sample_fdc)

    # Calculate for 200g
    calc_200 = nutrition_calculator.calculate_ingredient_nutrition(sample_fdc, 200.0)
    assert round(calc_200['calories_kcal']) == round(nutr_100g['calories_kcal'] * 2.0)
    assert round(calc_200['protein_g']) == round(nutr_100g['protein_g'] * 2.0)


def test_meal_aggregation():
    food_df = nutrition_database.get_nutrition_db()
    fdc1 = int(food_df['fdc_id'].iloc[0])
    fdc2 = int(food_df['fdc_id'].iloc[1])

    items = [
        {'fdc_id': fdc1, 'grams': 100.0, 'food_name': 'Item 1'},
        {'fdc_id': fdc2, 'grams': 150.0, 'food_name': 'Item 2'}
    ]
    meal = nutrition_calculator.calculate_meal_nutrition(items)
    assert 'totals' in meal
    assert 'macronutrient_percentages' in meal
    assert meal['totals']['total_grams'] == 250.0
    assert meal['totals']['calories_kcal'] >= 0


def test_bmi_and_classification():
    # 70 kg, 175 cm
    bmi, cat, desc = bmi_calculator.calculate_bmi(70.0, 175.0)
    assert round(bmi, 2) == 22.86
    assert cat == "Normal weight"

    # Underweight
    bmi_under, cat_under, _ = bmi_calculator.calculate_bmi(45.0, 175.0)
    assert cat_under == "Underweight"

    # Overweight
    bmi_over, cat_over, _ = bmi_calculator.calculate_bmi(85.0, 175.0)
    assert cat_over == "Overweight"


def test_mifflin_st_jeor_ree():
    # Male: 80 kg, 180 cm, 30 years -> 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
    ree_male = bmi_calculator.calculate_ree_mifflin_st_jeor(80.0, 180.0, 30, "Male")
    assert ree_male == 1780.0

    # Female: 60 kg, 165 cm, 25 years -> 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
    ree_female = bmi_calculator.calculate_ree_mifflin_st_jeor(60.0, 165.0, 25, "Female")
    assert ree_female == 1345.2


def test_nutritional_targets():
    targets = bmi_calculator.calculate_nutritional_targets(2000.0, "maintain")
    assert targets['target_calories'] == 2000.0
    assert 'protein_g' in targets['target_macros']
    assert 'carbs_g' in targets['target_macros']
    assert 'fat_g' in targets['target_macros']


def test_recommendation_engine():
    profile = {
        'target_calories': 2000.0,
        'allergies': 'peanut, egg',
        'preferences': 'vegetarian',
        'goal': 'maintain'
    }
    meal = {
        'totals': {
            'calories_kcal': 950.0,
            'protein_g': 25.0,
            'carbs_g': 120.0,
            'fat_g': 40.0,
            'fiber_g': 3.0,
            'sugars_g': 45.0,
            'sodium_mg': 1500.0
        },
        'macronutrient_percentages': {
            'protein_pct': 10.5,
            'carbs_pct': 50.5,
            'fat_pct': 39.0
        },
        'ingredient_details': [
            {'food_name': 'peanut butter spread', 'grams': 30.0},
            {'food_name': 'chicken breast roasted', 'grams': 120.0}
        ]
    }
    recs = recommendation_engine.generate_dietary_recommendations(meal, profile, meal_type='lunch')
    assert 'alerts' in recs
    assert 'recommendations' in recs
    # Allergen alert for peanut should trigger
    allergen_alerts = [a for a in recs['alerts'] if 'ALLERGEN' in a]
    assert len(allergen_alerts) > 0
    # Vegetarian alert for chicken should trigger
    veg_alerts = [a for a in recs['alerts'] if 'PREFERENCE' in a]
    assert len(veg_alerts) > 0
