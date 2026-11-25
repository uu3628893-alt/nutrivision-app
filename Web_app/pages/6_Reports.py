import sys
from pathlib import Path
from datetime import date

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
import pandas as pd
from src import database
from src import utils
from src import recommendation_engine
from src import bmi_calculator

st.set_page_config(page_title="Reports & Exports - NutriVision", layout="wide")

st.title("Nutritional Assessment Reports & Data Export")
st.caption("Standardized Clinical Reporting and Longitudinal CSV Export")

user_prof = database.get_user_profile()
if not user_prof:
    st.warning("No user profile configured. Please complete your profile in the User Profile module.")
    st.stop()

# Enrich profile with BMI for report
bmi, bmi_cat, _ = bmi_calculator.calculate_bmi(user_prof['weight_kg'], user_prof['height_cm'])
user_prof['bmi'] = bmi
user_prof['bmi_category'] = bmi_cat

st.markdown(f"### Subject: **{user_prof['age']} yr old {user_prof['sex']} ({user_prof['goal'].title()})**")

# Section 1: CSV Export
st.markdown("### 1. Tabular Data Export (CSV)")
meals = database.get_all_meals(limit=500)

if not meals:
    st.info("No meal records available to export.")
else:
    df_meals = utils.export_meals_to_dataframe(meals)
    csv_bytes = df_meals.to_csv(index=False).encode('utf-8')

    col_csv1, col_csv2 = st.columns([3, 1])
    with col_csv1:
        st.write(f"Total dietary logs available: **{len(df_meals)} meals**.")
    with col_csv2:
        st.download_button(
            label="Download Meals CSV",
            data=csv_bytes,
            file_name=f"nutrivision_meals_history.csv",
            mime="text/csv",
            type="primary"
        )

# Section 2: Clinical PDF Assessment Report
st.markdown("### 2. Clinical Assessment PDF Report Generation")

if meals:
    meal_options = [m['id'] for m in meals]
    selected_meal_id = st.selectbox(
        "Select Meal Assessment to Include in Report:",
        options=meal_options,
        format_func=lambda mid: next((f"Meal #{mid} - {str(m.get('created_at',''))[:16]} ({m['meal_name']}, {round(m['total_calories'])} kcal)" for m in meals if m['id'] == mid), str(mid))
    )

    full_meal = database.get_meal_by_id(selected_meal_id)
    if full_meal:
        ingredients = full_meal.get('ingredients', [])

        meal_nutr = {
            'totals': {
                'calories_kcal': full_meal['total_calories'],
                'protein_g': full_meal['total_protein'],
                'carbs_g': full_meal['total_carbs'],
                'fat_g': full_meal['total_fat'],
                'fiber_g': full_meal.get('total_fiber', 0.0),
                'sugars_g': full_meal.get('total_sugars', 0.0),
                'sodium_mg': full_meal.get('total_sodium', 0.0),
                'total_grams': full_meal.get('total_grams', 0.0)
            },
            'macronutrient_percentages': {},
            'ingredient_details': ingredients
        }

        # Calculate percentages
        prot_cal = full_meal['total_protein'] * 4.0
        carb_cal = full_meal['total_carbs'] * 4.0
        fat_cal = full_meal['total_fat'] * 9.0
        tot_cal = max(prot_cal + carb_cal + fat_cal, 1.0)
        meal_nutr['macronutrient_percentages'] = {
            'protein_pct': round((prot_cal / tot_cal) * 100.0, 1),
            'carbs_pct': round((carb_cal / tot_cal) * 100.0, 1),
            'fat_pct': round((fat_cal / tot_cal) * 100.0, 1)
        }

        rec_obj = recommendation_engine.generate_dietary_recommendations(
            meal_nutr,
            user_prof,
            meal_type=full_meal.get('meal_type', 'lunch').lower()
        )

        all_recs = []
        for a in rec_obj.get('alerts', []):
            all_recs.append({'category': 'Clinical Alert', 'text': a})
        for r in rec_obj.get('recommendations', []):
            all_recs.append({'category': 'Recommendation', 'text': r})
        for p in rec_obj.get('positive_feedback', []):
            all_recs.append({'category': 'Positive Note', 'text': p})

        # Generate PDF bytes
        pdf_data = utils.generate_nutritional_pdf_report(
            profile=user_prof,
            meal_summary=meal_nutr['totals'],
            ingredients=ingredients,
            recommendations=all_recs
        )

        col_pdf1, col_pdf2 = st.columns([3, 1])
        with col_pdf1:
            st.write(f"Report compiled for Meal #{selected_meal_id} ({full_meal['meal_name']} - {full_meal['meal_type']}).")
        with col_pdf2:
            st.download_button(
                label="Download Clinical PDF",
                data=pdf_data,
                file_name=f"clinical_nutritional_report_meal_{selected_meal_id}.pdf",
                mime="application/pdf",
                type="primary"
            )

# Section 3: Longitudinal Statistical Summary
st.markdown("### 3. Aggregate Statistical Summary")
stats = database.get_meals_summary_stats()

if stats.get('total_meals', 0) > 0:
    targets_plan = bmi_calculator.calculate_nutritional_targets(user_prof['target_calories'], user_prof['goal'])
    tm = targets_plan['target_macros']

    summary_stats = pd.DataFrame({
        "Metric": ["Total Meals Logged", "Average Energy / Meal", "Average Protein / Meal", "Average Carbohydrates / Meal", "Average Fat / Meal", "Average Fiber / Meal"],
        "Recorded Average": [
            f"{stats['total_meals']}",
            f"{stats['avg_calories']:.1f} kcal",
            f"{stats['avg_protein']:.1f} g",
            f"{stats['avg_carbs']:.1f} g",
            f"{stats['avg_fat']:.1f} g",
            f"{stats['avg_fiber']:.1f} g"
        ],
        "Reference Baseline (Daily Target)": [
            "-",
            f"{round(user_prof['target_calories'])} kcal/day",
            f"{tm['protein_g']:.0f} g/day",
            f"{tm['carbs_g']:.0f} g/day",
            f"{tm['fat_g']:.0f} g/day",
            "28.0 g/day"
        ]
    })
    st.dataframe(summary_stats, use_container_width=True, hide_index=True)
else:
    st.info("Log meals over multiple days to populate longitudinal statistics.")
