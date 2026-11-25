import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
import pandas as pd
from src import database
from src import visualizations
from src import bmi_calculator
from src import config

st.set_page_config(page_title="Dashboard - NutriVision", layout="wide")

st.title("Dietary Intake Dashboard")
st.caption("Personalized Nutritional Monitoring and Macronutrient Energy Distribution")

# Profile retrieval
user_prof = database.get_user_profile()

if not user_prof:
    st.warning("No active user profile configured. Please complete your anthropometric setup in the User Profile module.")
    if st.button("Go to User Profile"):
        st.switch_page("pages/4_User_Profile.py")
    st.stop()

# Biometric and Target Calculations
bmi, bmi_cat, _ = bmi_calculator.calculate_bmi(user_prof['weight_kg'], user_prof['height_cm'])
targets = bmi_calculator.calculate_nutritional_targets(user_prof['target_calories'], user_prof['goal'])
target_macros = targets['target_macros']

# Profile Summary Header
st.markdown("### Physiological Profile & Caloric Targets")
col_p1, col_p2, col_p3, col_p4 = st.columns(4)
with col_p1:
    st.metric("Age / Sex", f"{user_prof['age']} yrs / {user_prof['sex']}")
with col_p2:
    st.metric("Body Mass Index", f"{bmi:.1f} kg/m²", delta=bmi_cat)
with col_p3:
    st.metric("Daily Calorie Target", f"{round(user_prof['target_calories'])} kcal")
with col_p4:
    st.metric("Target Goal", user_prof['goal'].title())

# Time Window Filter
st.markdown("### Intake Filtering")
filter_option = st.radio(
    "Select Reporting Window:",
    options=["Today", "Last 7 Days", "Last 30 Days", "All Time"],
    horizontal=True
)

all_meals = database.get_all_meals(limit=500)

today_str = date.today().strftime("%Y-%m-%d")
seven_days_ago = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
thirty_days_ago = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

filtered_meals = []
for m in all_meals:
    m_date = str(m.get('created_at', ''))[:10]
    if filter_option == "Today" and m_date == today_str:
        filtered_meals.append(m)
    elif filter_option == "Last 7 Days" and m_date >= seven_days_ago:
        filtered_meals.append(m)
    elif filter_option == "Last 30 Days" and m_date >= thirty_days_ago:
        filtered_meals.append(m)
    elif filter_option == "All Time":
        filtered_meals.append(m)

# Aggregate consumption metrics
total_cals = sum(m.get('total_calories', 0.0) for m in filtered_meals)
total_prot = sum(m.get('total_protein', 0.0) for m in filtered_meals)
total_carbs = sum(m.get('total_carbs', 0.0) for m in filtered_meals)
total_fat = sum(m.get('total_fat', 0.0) for m in filtered_meals)
total_fiber = sum(m.get('total_fiber', 0.0) for m in filtered_meals)

st.markdown("### Cumulative Intake for Selected Window")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    diff_cal = total_cals - user_prof['target_calories'] if filter_option == "Today" else None
    st.metric(
        "Energy",
        f"{round(total_cals)} kcal",
        delta=f"{round(diff_cal)} kcal vs daily target" if diff_cal is not None else f"{len(filtered_meals)} meals logged"
    )
with col_m2:
    st.metric("Protein", f"{total_prot:.1f} g", delta=f"Target: {target_macros['protein_g']:.0f} g" if filter_option == "Today" else None)
with col_m3:
    st.metric("Carbohydrates", f"{total_carbs:.1f} g", delta=f"Target: {target_macros['carbs_g']:.0f} g" if filter_option == "Today" else None)
with col_m4:
    st.metric("Total Fat", f"{total_fat:.1f} g", delta=f"Target: {target_macros['fat_g']:.0f} g" if filter_option == "Today" else None)

if not filtered_meals:
    st.info("No recorded meals found for the selected time window. Proceed to Food Image Analysis or Nutrition Analysis to log meals.")
else:
    # Macronutrient Distribution and AMDR Charts
    st.markdown("### Macronutrient Energy Assessment")
    prot_cal = total_prot * 4.0
    carb_cal = total_carbs * 4.0
    fat_cal = total_fat * 9.0
    macro_sum_cal = max(prot_cal + carb_cal + fat_cal, 1.0)
    macro_pct = {
        'protein_pct': round((prot_cal / macro_sum_cal) * 100.0, 1),
        'carb_pct': round((carb_cal / macro_sum_cal) * 100.0, 1),
        'fat_pct': round((fat_cal / macro_sum_cal) * 100.0, 1)
    }

    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        fig_donut = visualizations.plot_macronutrient_donut(macro_pct, "Observed Caloric Distribution (%)")
        st.plotly_chart(fig_donut, use_container_width=True)

    with c_chart2:
        fig_amdr = visualizations.plot_amdr_comparison(macro_pct, config.AMDR_RANGES)
        st.plotly_chart(fig_amdr, use_container_width=True)

    # Longitudinal Daily Intake Trend
    st.markdown("### Longitudinal Daily Energy Intake")
    daily_dict = {}
    for m in all_meals:
        d_key = str(m.get('created_at', ''))[:10]
        daily_dict[d_key] = daily_dict.get(d_key, 0.0) + m.get('total_calories', 0.0)

    daily_data = [{'date': d, 'total_calories': round(c, 1)} for d, c in sorted(daily_dict.items())]
    fig_trend = visualizations.plot_daily_intake_trend(daily_data, target_calories=user_prof['target_calories'])
    st.plotly_chart(fig_trend, use_container_width=True)

    # Recorded Meals Table
    st.markdown("### Recorded Meals in Window")
    meal_rows = []
    for m in filtered_meals:
        meal_rows.append({
            "Meal ID": m['id'],
            "Recorded Date": str(m['created_at'])[:16],
            "Meal Name": m['meal_name'],
            "Type": m['meal_type'],
            "Calories (kcal)": round(m['total_calories'], 1),
            "Protein (g)": round(m['total_protein'], 1),
            "Carbs (g)": round(m['total_carbs'], 1),
            "Fat (g)": round(m['total_fat'], 1),
            "Fiber (g)": round(m['total_fiber'], 1),
            "Sodium (mg)": round(m['total_sodium'], 1)
        })
    df_meals = pd.DataFrame(meal_rows)
    st.dataframe(df_meals, use_container_width=True, hide_index=True)
