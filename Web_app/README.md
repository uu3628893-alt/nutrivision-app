# NutriVision: AI-Based Nutritional Analysis & Dietary Recommendation System

MSc Data Science and Artificial Intelligence Project:
**Design and Development of an AI-Based Nutritional Analysis and Personalised Dietary Recommendation System Using Food Image Segmentation**

## Overview

NutriVision is an integrated computer vision and clinical nutrition application. The system performs pixel-level semantic segmentation of food photography (FoodSeg103 ontology), maps detected ingredients to empirical USDA FNDDS 2021-2023 nutrient profiles, calculates anthropometric baselines (Mifflin-St Jeor REE, WHO BMI, AMDR macronutrient ranges), and generates personalized, context-aware dietary recommendations powered purely by Google Gemini (Gemini 2.5 Flash) with independent deterministic safety and allergen screening.

## System Architecture

1. **Deep Learning Segmentation**: Dual deep convolutional models (DeepLabV3+ with ResNet-50 and U-Net with ResNet-34) trained on the FoodSeg103 ontology identify culinary items at pixel level.
2. **USDA FNDDS Nutritional Mapping**: Segmented items are deterministically cross-referenced against USDA Food and Nutrient Database for Dietary Studies (FNDDS 2021-2023) records for empirical energy and nutrient calculation.
3. **Deterministic Safety Screening**: Independent validation detects declared allergen conflicts, vegan/vegetarian dietary inconsistencies, assumed portion notices, and biometric safety warnings (e.g. underweight calorie restriction notices).
4. **Purely LLM-Based Recommendations**: Personalized dietary suggestions, meal assessments, health considerations, and actionable improvements are generated exclusively by Google Gemini via the official `google-genai` Python SDK.

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

## Running the Automated Test Suite

To run all automated unit tests:

```bash
pytest tests -v
```

The test suite validates:
- Database schema migration and health condition persistence
- Allergen synonym matching and safety notice preservation
- Missing nutrient detection and assumed portion notices
- Gemini structured output parsing and Pydantic validation
- Pure LLM error handling (missing API key, rate limits, timeouts, model unavailability) without rule fallbacks
- Recommendation cache invalidation on meal and profile changes
