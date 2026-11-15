import sys
from pathlib import Path
import pytest

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src import nutrition_database


def test_usda_database_loading():
    food_df = nutrition_database.get_nutrition_db()
    portions_df = nutrition_database.get_portions_db()
    assert not food_df.empty, "Food DataFrame should not be empty"
    assert not portions_df.empty, "Portions DataFrame should not be empty"
    assert 'fdc_id' in food_df.columns
    assert 'calories_kcal' in food_df.columns
    assert 'protein_g' in food_df.columns
    assert 'carbs_g' in food_df.columns
    assert 'fat_g' in food_df.columns
    assert len(food_df) > 5000, "Should have more than 5000 USDA FNDDS food items"


def test_get_food_nutrients():
    food_df = nutrition_database.get_nutrition_db()
    sample_fdc = int(food_df['fdc_id'].iloc[0])
    nutrients = nutrition_database.get_food_nutrition(sample_fdc)

    assert nutrients is not None
    assert 'calories_kcal' in nutrients
    assert 'protein_g' in nutrients
    assert nutrients['calories_kcal'] >= 0


def test_get_portions_for_food():
    food_df = nutrition_database.get_nutrition_db()
    sample_fdc = int(food_df['fdc_id'].iloc[0])
    portions = nutrition_database.get_food_portions(sample_fdc)

    assert isinstance(portions, list)
    if len(portions) > 0:
        p = portions[0]
        assert 'gram_weight' in p
        assert p['gram_weight'] > 0
