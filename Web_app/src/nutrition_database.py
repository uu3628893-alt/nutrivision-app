"""
USDA FNDDS 2021-2023 relational database integration and query module.
Consolidates foods, chemical nutrient amounts per 100g, and empirical portion options.
"""

from typing import Dict, List, Any, Optional, Tuple
import os
import pandas as pd
from src.paths import USDA_DIR

try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    def cache_data(func):
        return func

# Standard USDA nutrient numbers used in FNDDS
TARGET_NUTRIENTS = {
    208.0: "calories_kcal",
    203.0: "protein_g",
    204.0: "fat_g",
    205.0: "carbs_g",
    291.0: "fiber_g",
    269.3: "sugars_g",
    307.0: "sodium_mg"
}

@cache_data
def load_consolidated_usda_database() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load and consolidate USDA FNDDS survey tables into optimized DataFrames.
    Returns (nutrition_db, portions_db).
    """
    if not USDA_DIR.exists():
        raise FileNotFoundError(f"USDA directory not found at: {USDA_DIR}")
        
    food_csv = USDA_DIR / "food.csv"
    survey_csv = USDA_DIR / "survey_fndds_food.csv"
    fn_csv = USDA_DIR / "food_nutrient.csv"
    portion_csv = USDA_DIR / "food_portion.csv"
    
    # 1. Load Food core records
    food_df = pd.read_csv(food_csv, usecols=["fdc_id", "description"])
    survey_df = pd.read_csv(survey_csv, usecols=["fdc_id", "food_code", "wweia_category_number"])
    
    merged_food = food_df.merge(survey_df, on="fdc_id", how="inner")
    
    # 2. Load food nutrient records and filter to target nutrients
    # In FNDDS 2021-2023, nutrient_id in food_nutrient.csv matches nutrient_nbr in nutrient.csv
    fn_df = pd.read_csv(fn_csv, usecols=["fdc_id", "nutrient_id", "amount"])
    
    # Check if nutrient_id is matching target IDs
    filtered_fn = fn_df[fn_df["nutrient_id"].isin(TARGET_NUTRIENTS.keys())].copy()
    
    # Pivot to wide format: 1 row per fdc_id
    pivoted = filtered_fn.pivot_table(
        index="fdc_id",
        columns="nutrient_id",
        values="amount",
        aggfunc="first"
    ).reset_index()
    
    pivoted.rename(columns=TARGET_NUTRIENTS, inplace=True)
    
    nutrition_db = merged_food.merge(pivoted, on="fdc_id", how="left")
    
    # Fill missing nutrient amounts with 0.0
    for col in TARGET_NUTRIENTS.values():
        if col not in nutrition_db.columns:
            nutrition_db[col] = 0.0
        else:
            nutrition_db[col] = nutrition_db[col].fillna(0.0)
            
    # 3. Load empirical portions
    portion_df = pd.read_csv(portion_csv, usecols=["fdc_id", "portion_description", "modifier", "gram_weight"])
    portion_df = portion_df[portion_df["gram_weight"] > 0].copy()
    
    portion_df["serving_name"] = portion_df["portion_description"].fillna("")
    mask_mod = (portion_df["serving_name"] == "") & portion_df["modifier"].notna()
    portion_df.loc[mask_mod, "serving_name"] = portion_df.loc[mask_mod, "modifier"].astype(str)
    portion_df.loc[portion_df["serving_name"] == "", "serving_name"] = "Standard portion"
    
    return nutrition_db, portion_df

# Convenience wrapper
def get_nutrition_db() -> pd.DataFrame:
    nutr_df, _ = load_consolidated_usda_database()
    return nutr_df

def get_portions_db() -> pd.DataFrame:
    _, portion_df = load_consolidated_usda_database()
    return portion_df

def get_food_nutrition(fdc_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve nutritional profile per 100g for a USDA FDC ID."""
    nutr_df = get_nutrition_db()
    row = nutr_df[nutr_df["fdc_id"] == fdc_id]
    if row.empty:
        return None
    res = row.iloc[0].to_dict()
    return res

def get_food_portions(fdc_id: int) -> List[Dict[str, Any]]:
    """Retrieve available standard empirical portion servings for a USDA food item."""
    portions_df = get_portions_db()
    sub = portions_df[portions_df["fdc_id"] == fdc_id]
    if sub.empty:
        return [{"serving_name": "Standard serving (100g)", "gram_weight": 100.0}]
    return sub[["serving_name", "gram_weight"]].to_dict("records")

def search_usda_foods(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search USDA survey foods by description keyword."""
    nutr_df = get_nutrition_db()
    q = query.lower().strip()
    if not q:
        return nutr_df[["fdc_id", "description"]].head(limit).to_dict("records")
        
    mask = nutr_df["description"].str.lower().str.contains(q, na=False)
    matches = nutr_df[mask][["fdc_id", "description", "calories_kcal", "protein_g", "fat_g", "carbs_g"]].head(limit)
    return matches.to_dict("records")

def get_database_summary() -> Dict[str, Any]:
    """Return summary statistics of the USDA FNDDS database."""
    nutr_df = get_nutrition_db()
    port_df = get_portions_db()
    return {
        "total_foods": len(nutr_df),
        "total_portions": len(port_df),
        "mean_calories_per_100g": round(float(nutr_df["calories_kcal"].mean()), 1),
        "mean_protein_per_100g": round(float(nutr_df["protein_g"].mean()), 1),
        "mean_fat_per_100g": round(float(nutr_df["fat_g"].mean()), 1),
        "mean_carbs_per_100g": round(float(nutr_df["carbs_g"].mean()), 1)
    }
