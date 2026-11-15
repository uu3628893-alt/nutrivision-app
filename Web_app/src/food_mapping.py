"""
FoodSeg103 to USDA FNDDS food mapping manager and query interface.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from src.paths import FOOD_MAPPING_CSV
from src.food_labels import get_class_name

try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    def cache_data(func):
        return func

@cache_data
def load_food_mapping() -> pd.DataFrame:
    """Load the official FoodSeg103-to-USDA ontology mapping table."""
    if not FOOD_MAPPING_CSV.exists():
        raise FileNotFoundError(f"Mapping CSV not found at: {FOOD_MAPPING_CSV}")
        
    df = pd.read_csv(FOOD_MAPPING_CSV)
    # Ensure proper data types
    df["class_id"] = df["class_id"].astype(int)
    df["approved"] = df["approved"].astype(bool)
    return df

def get_mapping_for_class(class_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve USDA mapping information for a given FoodSeg103 class ID."""
    df = load_food_mapping()
    row = df[df["class_id"] == class_id]
    if row.empty:
        return {
            "class_id": class_id,
            "foodseg_name": get_class_name(class_id),
            "usda_fdc_id": None,
            "usda_description": "Unmapped Item",
            "similarity_score": 0.0,
            "mapping_status": "Unmapped",
            "approved": False
        }
    rec = row.iloc[0].to_dict()
    if pd.isna(rec.get("usda_fdc_id")):
        rec["usda_fdc_id"] = None
    else:
        rec["usda_fdc_id"] = int(rec["usda_fdc_id"])
    return rec

def get_all_mappings() -> pd.DataFrame:
    """Return the entire mapping table as a pandas DataFrame."""
    return load_food_mapping().copy()

def update_mapping(class_id: int, usda_fdc_id: int, usda_description: str, approved: bool = True) -> bool:
    """
    Update food mapping in the CSV file for a given class ID.
    Enables manual user review and approval of ambiguous matches.
    """
    df = load_food_mapping()
    idx = df[df["class_id"] == class_id].index
    if len(idx) > 0:
        df.loc[idx, "usda_fdc_id"] = usda_fdc_id
        df.loc[idx, "usda_description"] = usda_description
        df.loc[idx, "similarity_score"] = 1.0
        df.loc[idx, "mapping_status"] = "Verified"
        df.loc[idx, "approved"] = approved
        df.to_csv(FOOD_MAPPING_CSV, index=False)
        try:
            load_food_mapping.clear()
        except Exception:
            pass
        return True
    return False

