import sys
from pathlib import Path
import pytest

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src import food_labels
from src import food_mapping


def test_food_labels_count():
    labels = food_labels.FOODSEG103_CLASSES
    assert len(labels) == 104, "FoodSeg103 must contain exactly 104 classes (background + 103 ingredients)"
    assert labels[0] == "background"
    assert "egg" in labels.values()
    assert "french fries" in labels.values()
    assert "rice" in labels.values()


def test_food_label_lookup():
    assert food_labels.get_class_name(0) == "background"
    assert food_labels.get_class_name(999) == "unknown"
    assert food_labels.get_class_id("egg") == 24
    assert food_labels.get_class_id("nonexistent_food_xyz") is None


def test_usda_mapping_loading():
    df = food_mapping.load_food_mapping()
    assert not df.empty, "FoodSeg-to-USDA mapping DataFrame should not be empty"
    assert 'class_id' in df.columns
    assert 'usda_fdc_id' in df.columns
    assert 'usda_description' in df.columns


def test_usda_mapping_lookup():
    # Check mapping for class_id 24 ('egg')
    res = food_mapping.get_mapping_for_class(24)
    assert res is not None
    assert 'usda_fdc_id' in res
    assert 'usda_description' in res
    assert res['class_id'] == 24
