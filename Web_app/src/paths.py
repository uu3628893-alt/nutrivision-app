"""
Filesystem path resolution module for NutriVision web application.
Locates checkpoints, USDA datasets, exports, and local SQLite database.
"""

import os
from pathlib import Path

# Base directories
CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent
WEB_APP_DIR = SRC_DIR.parent

# Search for project root containing checkpoints and Data
def find_project_root(start_dir: Path) -> Path:
    candidates = [
        start_dir.parent,
        start_dir.parent.parent,
        Path(os.getcwd()),
        Path(os.getcwd()).parent
    ]
    for candidate in candidates:
        if (candidate / "checkpoints").exists() and (candidate / "Data").exists():
            return candidate
    return start_dir.parent

PROJECT_ROOT = find_project_root(WEB_APP_DIR)

# External assets and datasets
CHECKPOINTS_DIR = PROJECT_ROOT / "checkpoints"
UNET_CHECKPOINT_PATH = CHECKPOINTS_DIR / "best_unet_resnet34.pth"
DEEPLAB_CHECKPOINT_PATH = CHECKPOINTS_DIR / "best_deeplabv3plus_resnet50.pth"
UNET_CHECKPOINT = UNET_CHECKPOINT_PATH
DEEPLABV3PLUS_CHECKPOINT = DEEPLAB_CHECKPOINT_PATH

DATA_DIR = PROJECT_ROOT / "Data"
USDA_DIR = DATA_DIR / "FoodData_Central_survey_food"
FOODSEG_DIR = DATA_DIR / "FoodSeg103"

EXPORTS_DIR = PROJECT_ROOT / "exports"
FOOD_MAPPING_CSV = EXPORTS_DIR / "foodseg_usda_mapping.csv"
EVALUATION_SUMMARY_JSON = EXPORTS_DIR / "evaluation_summary.json"
REQUIREMENTS_TXT = EXPORTS_DIR / "requirements.txt"

FIGURES_DIR = PROJECT_ROOT / "figures"

# Application internal storage
APP_ASSETS_DIR = WEB_APP_DIR / "assets"
DATABASE_PATH = WEB_APP_DIR / "nutrivision.db"
REPORTS_DIR = WEB_APP_DIR / "reports"
UPLOADED_IMAGES_DIR = WEB_APP_DIR / "assets" / "uploaded_meals"

# Ensure runtime directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

