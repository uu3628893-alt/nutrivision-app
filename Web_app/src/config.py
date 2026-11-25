"""
Configuration constants and global application parameters for NutriVision.
"""

import os
from typing import Optional, Dict, Any
import numpy as np

# Application Identity
APP_NAME = "NutriVision"
APP_TITLE = "NutriVision - AI-Powered Nutritional Analysis and Personalised Dietary Recommendation System"
APP_ICON = "N"
APP_VERSION = "1.1.0"

# LLM Configuration
LLM_PROVIDER = "openai"
LLM_DEFAULT_MODEL = "gpt-4o-mini"
LLM_REQUEST_TIMEOUT = 15
LLM_MAX_TOKENS = 700
LLM_TEMPERATURE = 0.2

def get_llm_api_key() -> Optional[str]:
    # Check session state first (from UI input), then secrets, then environment variables
    try:
        import streamlit as st
        if hasattr(st, "session_state") and "user_api_key" in st.session_state and st.session_state["user_api_key"]:
            return str(st.session_state["user_api_key"]).strip()
        if hasattr(st, "secrets"):
            if "OPENAI_API_KEY" in st.secrets:
                return str(st.secrets["OPENAI_API_KEY"]).strip()
            if "LLM_API_KEY" in st.secrets:
                return str(st.secrets["LLM_API_KEY"]).strip()
    except Exception:
        pass
    env_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    if env_key:
        return env_key.strip()
    return None

def get_llm_config() -> Dict[str, Any]:
    api_key = get_llm_api_key()
    model = os.environ.get("LLM_MODEL", LLM_DEFAULT_MODEL)
    return {
        "provider": LLM_PROVIDER,
        "model": model,
        "api_key": api_key,
        "timeout": LLM_REQUEST_TIMEOUT,
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
        "is_configured": bool(api_key)
    }

# Computer Vision Configuration
IMAGE_SIZE = (512, 512)
NUM_CLASSES = 104
IGNORE_INDEX = 255

# ImageNet normalization parameters used in training
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# Model definitions
AVAILABLE_MODELS = {
    "DeepLabV3+ (ResNet-50)": {
        "architecture": "deeplabv3plus",
        "encoder": "resnet50",
        "checkpoint_filename": "best_deeplabv3plus_resnet50.pth",
        "description": "Atrous Spatial Pyramid Pooling with ResNet-50 backbone (Best mIoU)",
        "test_miou": 0.2319,
        "latency_ms": 11.77
    },
    "U-Net (ResNet-34)": {
        "architecture": "unet",
        "encoder": "resnet34",
        "checkpoint_filename": "best_unet_resnet34.pth",
        "description": "Asymmetric encoder-decoder with ResNet-34 backbone",
        "test_miou": 0.0971,
        "latency_ms": 12.89
    }
}

DEFAULT_MODEL_NAME = "DeepLabV3+ (ResNet-50)"

# Deterministic segmentation color palette (reproducible seed 42)
def get_segmentation_palette(num_classes: int = 104) -> np.ndarray:
    rng = np.random.RandomState(42)
    palette = rng.randint(40, 240, size=(num_classes, 3), dtype=np.uint8)
    palette[0] = [0, 0, 0] # Background in black
    return palette

SEGMENTATION_PALETTE = get_segmentation_palette(NUM_CLASSES)

# USDA FNDDS Nutrient Number mapping
NUTRIENT_IDS = {
    208.0: {"field": "calories_kcal", "name": "Calories", "unit": "kcal", "macro": True},
    203.0: {"field": "protein_g", "name": "Protein", "unit": "g", "macro": True},
    204.0: {"field": "fat_g", "name": "Total Fat", "unit": "g", "macro": True},
    205.0: {"field": "carbs_g", "name": "Carbohydrates", "unit": "g", "macro": True},
    291.0: {"field": "fiber_g", "name": "Dietary Fiber", "unit": "g", "macro": False},
    269.0: {"field": "sugars_g", "name": "Total Sugars", "unit": "g", "macro": False},
    307.0: {"field": "sodium_mg", "name": "Sodium", "unit": "mg", "macro": False}
}

# Acceptable Macronutrient Distribution Ranges (AMDR) standards
AMDR_RANGES = {
    "protein": {"min": 10.0, "max": 35.0, "target_default": 20.0},
    "carbs": {"min": 45.0, "max": 65.0, "target_default": 50.0},
    "fat": {"min": 20.0, "max": 35.0, "target_default": 30.0}
}

# Physical activity level multipliers
ACTIVITY_MULTIPLIERS = {
    "Sedentary (little to no exercise)": 1.2,
    "Lightly Active (light exercise 1-3 days/week)": 1.375,
    "Moderately Active (moderate exercise 3-5 days/week)": 1.55,
    "Very Active (hard exercise 6-7 days/week)": 1.725,
    "Extra Active (intense training or physical labor)": 1.9
}

