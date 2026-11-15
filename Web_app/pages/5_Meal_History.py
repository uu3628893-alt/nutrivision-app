import sys
from pathlib import Path
from datetime import date, timedelta

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
import pandas as pd
from src import database

st.set_page_config(page_title="Meal History – NutriVision", page_icon="📜", layout="wide")

st.title("Meal History & Dietary Audit")
st.caption("Chronological Dietary Records and Ingredient Breakdown")

user_prof = database.get_user_profile()
if not user_prof:
    st.warning("No user profile configured. Please complete your profile setup.")

# Filtering Controls
c_f1, c_f2, c_f3 = st.columns(3)
with c_f1:
    filter_type = st.selectbox("Meal Category Filter:", ["All Categories", "Breakfast", "Lunch", "Dinner", "Snack"])
with c_f2:
    start_d = st.date_input("Start Date", value=date.today() - timedelta(days=30))
with c_f3:
    end_d = st.date_input("End Date", value=date.today())

all_meals = database.get_all_meals(limit=500)

s_str = start_d.strftime("%Y-%m-%d")
e_str = end_d.strftime("%Y-%m-%d")

filtered_meals = []
for m in all_meals:
    m_date = str(m.get('created_at', ''))[:10]
    if s_str <= m_date <= e_str:
        if filter_type == "All Categories" or m['meal_type'].lower() == filter_type.lower():
            filtered_meals.append(m)

# Summary Metrics
c_m1, c_m2, c_m3, c_m4 = st.columns(4)
with c_m1:
    st.metric("Total Meals Recorded", len(filtered_meals))
with c_m2:
    tot_cal = sum(m['total_calories'] for m in filtered_meals)
    st.metric("Aggregate Energy", f"{round(tot_cal)} kcal")
with c_m3:
    avg_cal = (tot_cal / len(filtered_meals)) if filtered_meals else 0
    st.metric("Mean Energy / Meal", f"{round(avg_cal)} kcal")
with c_m4:
    tot_prot = sum(m['total_protein'] for m in filtered_meals)
    st.metric("Total Protein", f"{tot_prot:.1f} g")

if not filtered_meals:
    st.info("No dietary logs found for the selected criteria.")
    st.stop()

st.markdown("### Recorded Meal Entries")

for m in filtered_meals:
    meal_id = m['id']
    m_created = str(m.get('created_at', ''))[:16]
    m_name = m.get('meal_name', 'Meal')
    m_type = m.get('meal_type', 'Meal')
    cals = round(m['total_calories'])
    prot = m['total_protein']
    carbs = m['total_carbs']
    fat = m['total_fat']

    header_text = f"Entry #{meal_id} | {m_created} — {m_name} ({m_type}) | {cals} kcal | P: {prot:.1f}g | C: {carbs:.1f}g | F: {fat:.1f}g"

    with st.expander(header_text):
        c_meta1, c_meta2 = st.columns([4, 1])
        with c_meta1:
            st.write(
                f"**Nutritional Details**: Total Grams: {m.get('total_grams', 0.0):.1f}g | "
                f"Fiber: {m.get('total_fiber', 0.0):.1f}g | "
                f"Sugar: {m.get('total_sugars', 0.0):.1f}g | "
                f"Sodium: {m.get('total_sodium', 0.0):.0f}mg"
            )
            if m.get('notes'):
                st.caption(f"Notes: {m['notes']}")
        with c_meta2:
            if st.button("Delete Record", key=f"del_meal_{meal_id}"):
                database.delete_meal(meal_id)
                st.warning(f"Meal record #{meal_id} removed.")
                st.rerun()

        # Load ingredients using get_meal_by_id
        full_meal = database.get_meal_by_id(meal_id)
        if full_meal and full_meal.get('ingredients'):
            ing_rows = []
            for ing in full_meal['ingredients']:
                ing_rows.append({
                    "Ingredient": ing['food_name'].title(),
                    "Portion Description": ing['portion_name'],
                    "Weight (g)": f"{ing['grams']:.1f}",
                    "Energy (kcal)": round(ing['calories']),
                    "Protein (g)": f"{ing['protein']:.1f}",
                    "Carbs (g)": f"{ing['carbs']:.1f}",
                    "Fat (g)": f"{ing['fat']:.1f}",
                    "Fiber (g)": f"{ing.get('fiber', 0.0):.1f}",
                    "Sodium (mg)": f"{ing.get('sodium', 0.0):.0f}"
                })
            st.dataframe(pd.DataFrame(ing_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No individual ingredient records logged for this entry.")
