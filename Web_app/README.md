# NutriVision: AI-Based Nutritional Analysis & Dietary Recommendation System

MSc Data Science and Artificial Intelligence Project:
**Design and Development of an AI-Based Nutritional Analysis and Personalised Dietary Recommendation System Using Food Image Segmentation**

## Overview

NutriVision is an integrated computer vision and clinical nutrition application. The system performs pixel-level semantic segmentation of food photography (FoodSeg103 ontology), maps detected ingredients to empirical USDA FNDDS 2021-2023 nutrient profiles, calculates anthropometric baselines (Mifflin-St Jeor REE, WHO BMI, AMDR macronutrient ranges), and generates personalized, context-aware dietary recommendations through Large Language Model (LLM) integration and deterministic rule-based clinical safety screening.

## System Requirements

- Python 3.10 to 3.13
- PyTorch (CPU or CUDA)
- SQLite3 (included with Python standard library)

## Installation

1. Open a terminal and navigate to the application folder:
   ```bash
   cd Web_app
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Launch the Streamlit web application:

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

The application works immediately out-of-the-box using the built-in clinical recommendation engine without requiring any external configuration.

## Running the Automated Test Suite

To run all automated unit tests:

```bash
pytest tests -v
```

All 27 tests will execute, validating:
- Database schema migration and health condition persistence
- Allergen synonym matching and safety notice preservation
- Missing nutrient detection and assumed portion notices
- LLM timeout, rate limit, and invalid JSON response handling
