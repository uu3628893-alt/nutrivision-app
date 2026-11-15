import sys
from pathlib import Path

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
from src import database
from src import bmi_calculator

st.set_page_config(page_title="User Profile – NutriVision", page_icon="👤", layout="wide")

st.title("User Anthropometric Profile & Dietary Targets")
st.caption("Mifflin-St Jeor Energy Expenditure, WHO BMI Classification, and AMDR Target Formulation")

user_prof = database.get_user_profile()

st.markdown("### Profile Status")
if user_prof:
    st.success(
        f"Active Profile: {user_prof['age']} yr old {user_prof['sex']}, "
        f"{user_prof['height_cm']:.1f} cm, {user_prof['weight_kg']:.1f} kg. "
        f"Goal: {user_prof['goal'].title()} ({round(user_prof['target_calories'])} kcal/day)."
    )
else:
    st.info("No profile currently configured. Complete the form below to configure your biometric baseline.")

# Anthropometric Form
st.markdown("### Biometric Inputs & Lifestyle Parameters")

default_age = user_prof['age'] if user_prof else 28
default_sex = user_prof['sex'] if user_prof else "Male"
default_height = user_prof['height_cm'] if user_prof else 175.0
default_weight = user_prof['weight_kg'] if user_prof else 72.0
default_activity = user_prof['activity_level'] if user_prof else "Moderately Active"
default_goal = user_prof['goal'] if user_prof else "maintain"

activity_multipliers = {
    "Sedentary (desk work, minimal physical activity)": 1.2,
    "Lightly Active (light exercise 1–3 days/week)": 1.375,
    "Moderately Active (moderate exercise 3–5 days/week)": 1.55,
    "Very Active (hard exercise 6–7 days/week)": 1.725,
    "Extra Active (very heavy physical training or physical job)": 1.9
}

activity_labels = list(activity_multipliers.keys())
curr_act_idx = 2
for idx, act in enumerate(activity_labels):
    if default_activity.lower() in act.lower():
        curr_act_idx = idx
        break

goal_options = ["Maintenance", "Weight Loss", "Muscle Gain"]
curr_goal_idx = 0
for idx, g in enumerate(goal_options):
    if default_goal.lower() in g.lower():
        curr_goal_idx = idx
        break

with st.form("profile_form"):
    c_f1, c_f2, c_f3 = st.columns(3)

    with c_f1:
        age_val = st.number_input("Age (years)", min_value=15, max_value=105, value=int(default_age))
        sex_val = st.selectbox("Biological Sex", ["Male", "Female"], index=0 if default_sex == "Male" else 1)

    with c_f2:
        height_val = st.number_input("Height (cm)", min_value=100.0, max_value=240.0, value=float(default_height), step=0.5)
        weight_val = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=float(default_weight), step=0.5)

    with c_f3:
        activity_label = st.selectbox("Physical Activity Level", activity_labels, index=curr_act_idx)
        goal_val = st.selectbox("Nutritional & Caloric Goal", goal_options, index=curr_goal_idx)

    # Allergies and Preferences
    st.markdown("#### Clinical Exclusions & Dietary Preferences")
    c_sub1, c_sub2 = st.columns(2)
    with c_sub1:
        allergy_options = ["peanut", "tree nuts", "milk", "egg", "wheat", "soy", "fish", "shellfish"]
        current_allergies = [a.strip().lower() for a in user_prof['allergies'].split(',') if a.strip()] if user_prof and user_prof.get('allergies') else []
        allergies_val = st.multiselect("Allergens to Screen Against", allergy_options, default=[a for a in current_allergies if a in allergy_options])

    with c_sub2:
        pref_options = ["vegetarian", "vegan", "low carb", "high protein", "low sodium"]
        current_prefs = [p.strip().lower() for p in user_prof['preferences'].split(',') if p.strip()] if user_prof and user_prof.get('preferences') else []
        prefs_val = st.multiselect("Dietary Philosophy / Preferences", pref_options, default=[p for p in current_prefs if p in pref_options])

    save_submit = st.form_submit_button("Compute & Save Profile", type="primary")

# Physiological Calculations
multiplier = activity_multipliers[activity_label]
computed_bmi, bmi_cat, bmi_desc = bmi_calculator.calculate_bmi(weight_val, height_val)
computed_ree = bmi_calculator.calculate_ree_mifflin_st_jeor(weight_val, height_val, age_val, sex_val)
computed_tdee = bmi_calculator.calculate_tdee(computed_ree, multiplier)

goal_key = "weight_loss" if "loss" in goal_val.lower() else ("muscle_gain" if "muscle" in goal_val.lower() else "maintain")
target_plan = bmi_calculator.calculate_nutritional_targets(computed_tdee, goal_key)
target_cal = target_plan['target_calories']
target_macros = target_plan['target_macros']

st.markdown("### Computed Physiological Baselines")
c_res1, c_res2, c_res3, c_res4 = st.columns(4)
with c_res1:
    st.metric("Body Mass Index (BMI)", f"{computed_bmi:.1f} kg/m²", delta=bmi_cat)
with c_res2:
    st.metric("Resting Energy (REE)", f"{round(computed_ree)} kcal/day")
with c_res3:
    st.metric("Total Energy (TDEE)", f"{round(computed_tdee)} kcal/day")
with c_res4:
    st.metric("Target Caloric Budget", f"{round(target_cal)} kcal/day", delta=goal_val)

st.markdown("### Daily Macronutrient Target Allocation (AMDR)")
c_mac1, c_mac2, c_mac3 = st.columns(3)
with c_mac1:
    st.metric("Protein Allowance", f"{round(target_macros['protein_g'])} g/day", delta=f"{target_plan['target_percentages']['protein_pct']}% of energy")
with c_mac2:
    st.metric("Carbohydrate Allowance", f"{round(target_macros['carbs_g'])} g/day", delta=f"{target_plan['target_percentages']['carbs_pct']}% of energy")
with c_mac3:
    st.metric("Fat Allowance", f"{round(target_macros['fat_g'])} g/day", delta=f"{target_plan['target_percentages']['fat_pct']}% of energy")

if save_submit:
    database.save_user_profile(
        age=age_val,
        sex=sex_val,
        height_cm=height_val,
        weight_kg=weight_val,
        activity_level=activity_label.split(" (")[0],
        goal=goal_key,
        allergies=", ".join(allergies_val),
        preferences=", ".join(prefs_val),
        target_calories=target_cal
    )
    st.success("User profile successfully updated and synchronized.")
    st.rerun()

# Delete Profile
if user_prof:
    st.markdown("### Profile Deletion")
    if st.button("Delete Saved Profile", type="secondary"):
        database.delete_user_profile()
        st.warning("User profile deleted.")
        st.rerun()
