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
from src import nutrition_database
from src import nutrition_calculator
from src import food_mapping
from src import food_labels
from src import visualizations
from src import recommendation_engine
from src import bmi_calculator
from src import llm_recommendation

st.set_page_config(page_title="Nutrition Analysis - NutriVision", layout="wide")

st.title("Nutritional Analysis & Portion Scaling")
st.caption("Empirical USDA FNDDS 2021–2023 Nutrient Calculation and Personalized Assessment")

# Retrieve User Profile
user_prof = database.get_user_profile()
if not user_prof:
    st.warning("No user profile configured. Biometric targets and personalized recommendations require a saved profile.")

# Load USDA database
try:
    nutrition_df = nutrition_database.get_nutrition_db()
except Exception as e:
    st.error(f"Failed to load nutritional database: {e}")
    st.stop()

# State management for ingredients
if 'meal_builder_items' not in st.session_state:
    st.session_state['meal_builder_items'] = []

# Transfer incoming detections from segmentation
if 'transferred_ingredients' in st.session_state and st.session_state['transferred_ingredients']:
    incoming = st.session_state.pop('transferred_ingredients')
    builder_items = []
    for item in incoming:
        cid = item['class_id']
        name = item['foodseg_name']
        mapping = food_mapping.get_mapping_for_class(cid)
        fdc_id = mapping.get('usda_fdc_id')
        usda_desc = mapping.get('usda_description', name.title())
        builder_items.append({
            'class_id': cid,
            'food_name': name,
            'fdc_id': fdc_id,
            'display_name': usda_desc,
            'grams': 100.0,
            'portion_name': '100 g reference'
        })
    st.session_state['meal_builder_items'] = builder_items

builder_items = st.session_state['meal_builder_items']

# Manual Ingredient Addition
st.markdown("### Meal Ingredients & Portion Quantities")
col_add1, col_add2 = st.columns([3, 1])
with col_add1:
    all_categories = food_labels.get_all_food_categories()
    manual_add = st.selectbox("Add Ingredient from Vocabulary:", ["-- Select Ingredient --"] + [c.title() for c in all_categories])
with col_add2:
    st.write("")
    st.write("")
    if st.button("Add to Meal") and manual_add != "-- Select Ingredient --":
        cid = food_labels.get_class_id(manual_add.lower())
        if cid is not None:
            mapping = food_mapping.get_mapping_for_class(cid)
            fdc_id = mapping.get('usda_fdc_id')
            usda_desc = mapping.get('usda_description', manual_add)
            builder_items.append({
                'class_id': cid,
                'food_name': manual_add.lower(),
                'fdc_id': fdc_id,
                'display_name': usda_desc,
                'grams': 100.0,
                'portion_name': '100 g reference'
            })
            st.session_state['meal_builder_items'] = builder_items
            st.rerun()

if not builder_items:
    st.info("No ingredients currently added. Select an ingredient above or run Food Image Analysis.")
    st.stop()

# Ingredient Portion Selection
updated_items = []
indices_to_remove = []

for idx, item in enumerate(builder_items):
    st.markdown(f"#### {idx + 1}. **{item['food_name'].title()}**")
    c1, c2, c3, c4 = st.columns([3, 3, 2, 1])

    # 1. USDA Food Matching
    with c1:
        current_fdc = item.get('fdc_id')
        portions_for_food = nutrition_database.get_food_portions(current_fdc) if current_fdc else []

        st.caption(f"USDA Match: **{item['display_name']}**")
        search_query = st.text_input(f"Search Alternate USDA Food (#{idx+1})", key=f"search_{idx}")
        if search_query.strip():
            search_matches = nutrition_database.search_usda_foods(search_query.strip(), limit=10)
            if search_matches:
                match_options = [m['fdc_id'] for m in search_matches]
                chosen_fdc = st.selectbox(
                    f"Select Replacement (#{idx+1})",
                    options=match_options,
                    format_func=lambda fid: next((m['description'][:50] for m in search_matches if m['fdc_id'] == fid), str(fid)),
                    key=f"rep_sel_{idx}"
                )
                if chosen_fdc != current_fdc:
                    item['fdc_id'] = chosen_fdc
                    item['display_name'] = next(m['description'] for m in search_matches if m['fdc_id'] == chosen_fdc)
                    current_fdc = chosen_fdc
                    portions_for_food = nutrition_database.get_food_portions(chosen_fdc)

    # 2. Empirical USDA Portions
    with c2:
        portion_choices = ["Custom Gram Weight"]
        portion_weights = [100.0]

        for p in portions_for_food:
            desc = p.get('portion_description', '')
            amt = p.get('amount', 1.0)
            unit = p.get('unit_name', 'serving')
            gw = p.get('gram_weight', 100.0)
            label = f"{amt} {unit} ({desc}) - {gw:.1f}g" if desc else f"{amt} {unit} - {gw:.1f}g"
            portion_choices.append(label)
            portion_weights.append(gw)

        p_idx = st.selectbox(
            f"Portion Size (#{idx+1})",
            range(len(portion_choices)),
            format_func=lambda i: portion_choices[i],
            key=f"portion_choice_{idx}"
        )
        selected_desc = portion_choices[p_idx]
        auto_gw = portion_weights[p_idx]

    # 3. Weight in Grams
    with c3:
        if p_idx == 0:
            custom_g = st.number_input(
                f"Weight (g) (#{idx+1})",
                min_value=1.0,
                max_value=2500.0,
                value=float(item.get('grams', 100.0)),
                step=10.0,
                key=f"grams_input_{idx}"
            )
            item['grams'] = custom_g
            item['portion_name'] = f"{custom_g:.0f} g custom"
        else:
            st.write(f"Empirical Weight: **{auto_gw:.1f} g**")
            item['grams'] = auto_gw
            item['portion_name'] = selected_desc

    # 4. Remove Item
    with c4:
        st.write("")
        st.write("")
        if st.button("Delete", key=f"del_item_{idx}"):
            indices_to_remove.append(idx)

    updated_items.append(item)

if indices_to_remove:
    updated_items = [it for i, it in enumerate(updated_items) if i not in indices_to_remove]
    st.session_state['meal_builder_items'] = updated_items
    st.rerun()

st.session_state['meal_builder_items'] = updated_items

# Calculate aggregate meal nutrition
calc_payload = []
for it in updated_items:
    if it.get('fdc_id'):
        calc_payload.append({
            'fdc_id': it['fdc_id'],
            'grams': it['grams'],
            'food_name': it['food_name'],
            'portion_name': it['portion_name'],
            'class_id': it.get('class_id')
        })

meal_nutr = nutrition_calculator.calculate_meal_nutrition(calc_payload)
totals = meal_nutr['totals']
details = meal_nutr['ingredient_details']
macro_pct = meal_nutr['macronutrient_percentages']

# Display Meal Breakdown Table
st.markdown("### Calculated Meal Composition")

breakdown_rows = []
for d in details:
    breakdown_rows.append({
        "Ingredient": d['food_name'].title(),
        "Portion Description": d['portion_name'],
        "Weight (g)": f"{d['grams']:.1f}",
        "Energy (kcal)": round(d['calories_kcal']),
        "Protein (g)": f"{d['protein_g']:.1f}",
        "Carbs (g)": f"{d['carbs_g']:.1f}",
        "Fat (g)": f"{d['fat_g']:.1f}",
        "Fiber (g)": f"{d['fiber_g']:.1f}",
        "Sugar (g)": f"{d['sugars_g']:.1f}",
        "Sodium (mg)": f"{d['sodium_mg']:.0f}"
    })

# Totals Row
breakdown_rows.append({
    "Ingredient": "TOTAL MEAL",
    "Portion Description": "-",
    "Weight (g)": f"{totals['total_grams']:.1f}",
    "Energy (kcal)": round(totals['calories_kcal']),
    "Protein (g)": f"{totals['protein_g']:.1f}",
    "Carbs (g)": f"{totals['carbs_g']:.1f}",
    "Fat (g)": f"{totals['fat_g']:.1f}",
    "Fiber (g)": f"{totals['fiber_g']:.1f}",
    "Sugar (g)": f"{totals['sugars_g']:.1f}",
    "Sodium (mg)": f"{totals['sodium_mg']:.0f}"
})

st.dataframe(pd.DataFrame(breakdown_rows), use_container_width=True, hide_index=True)

# Macronutrient Profile & Comparison
st.markdown("### Macronutrient Profile and Reference Targets")
c_vis1, c_vis2 = st.columns(2)

with c_vis1:
    fig_donut = visualizations.plot_macronutrient_donut(macro_pct, "Meal Caloric Distribution")
    st.plotly_chart(fig_donut, use_container_width=True)

with c_vis2:
    if user_prof:
        targets_obj = bmi_calculator.calculate_nutritional_targets(user_prof['target_calories'], user_prof['goal'])
        tm = targets_obj['target_macros']
        meal_targets = {
            'calories': user_prof['target_calories'] * 0.35,
            'protein_g': tm['protein_g'] * 0.35,
            'carbs_g': tm['carbs_g'] * 0.35,
            'fat_g': tm['fat_g'] * 0.35,
            'fiber_g': 28.0 * 0.35
        }
        fig_bar = visualizations.plot_nutrient_comparison_bar(
            {
                'energy_kcal': totals['calories_kcal'],
                'protein_g': totals['protein_g'],
                'carbohydrate_g': totals['carbs_g'],
                'fat_g': totals['fat_g'],
                'dietary_fiber_g': totals['fiber_g']
            },
            meal_targets
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Configure a user profile to visualize target comparison bars.")

# Personalized Recommendations
st.markdown("### Personalized Clinical & Dietary Recommendations")

meal_cat = st.selectbox("Select Meal Occasion for Assessment:", ["Lunch", "Breakfast", "Dinner", "Snack"])

if user_prof:
    rule_results = recommendation_engine.generate_dietary_recommendations(meal_nutr, user_prof, meal_type=meal_cat.lower())

    # Independent safety warnings always displayed upfront
    for alert in rule_results.get('alerts', []):
        st.error(alert)

    c_btn1, c_btn2 = st.columns([2, 1])
    with c_btn1:
        gen_llm_btn = st.button("Generate Personalised Dietary Recommendation", type="primary")
    with c_btn2:
        if st.button("Reset Recommendations"):
            st.session_state['llm_recommendation_result'] = None
            st.rerun()

    if gen_llm_btn:
        with st.spinner("Generating personalized dietary recommendations..."):
            st.session_state['llm_recommendation_result'] = llm_recommendation.generate_llm_recommendation(
                meal_nutrition=meal_nutr,
                user_profile=user_prof,
                meal_type=meal_cat.lower()
            )

    rec_data = st.session_state.get('llm_recommendation_result')
    if rec_data:
        st.markdown("#### Meal Assessment")
        st.write(rec_data.get("meal_assessment", ""))

        st.markdown("#### Personalised Dietary Suggestions")
        suggestions = rec_data.get("personalized_suggestions", [])
        if isinstance(suggestions, list):
            for s in suggestions:
                st.info(s)
        else:
            st.info(suggestions)

        st.markdown("#### Health Considerations")
        health_items = rec_data.get("health_considerations", [])
        if isinstance(health_items, list):
            for h in health_items:
                st.warning(h)
        else:
            st.warning(health_items)

        st.markdown("#### Important Notices")
        notices = rec_data.get("important_notices", [])
        if isinstance(notices, list):
            for n in notices:
                st.caption(f"- {n}")
        else:
            st.caption(f"- {notices}")
    else:
        st.markdown("#### Meal Assessment")
        cal_val = round(totals.get('calories_kcal', 0.0))
        budget = rule_results.get('meal_calorie_budget', 0.0)
        st.write(f"Estimated meal energy is {cal_val} kcal compared to your allocated {meal_cat.lower()} target of {round(budget)} kcal.")

        st.markdown("#### Personalised Dietary Suggestions")
        for rec in rule_results.get('recommendations', []):
            st.warning(rec)
        for pos in rule_results.get('positive_feedback', []):
            st.success(pos)

        st.markdown("#### Health Considerations")
        if rule_results.get('health_notices'):
            for hn in rule_results['health_notices']:
                st.info(hn)
        else:
            st.write("No specific health conditions or clinical contraindications identified.")

        st.markdown("#### Important Notices")
        all_notices = list(rule_results.get('assumed_portions', []))
        all_notices.append(rule_results.get('disclaimer', ''))
        for n in all_notices:
            if n:
                st.caption(f"- {n}")
else:
    st.info("Setup a user profile to generate personalised dietary recommendations.")

# Meal Saving Form
st.markdown("### Save Meal to History")
c_save1, c_save2, c_save3 = st.columns([2, 2, 2])

with c_save1:
    m_name = st.text_input("Meal Title", value=f"{meal_cat} Plate")
with c_save2:
    m_notes = st.text_input("Notes (Optional)", value="")
with c_save3:
    st.write("")
    st.write("")
    save_btn = st.button("Save Meal Record", type="primary")

if save_btn:
    saved_id = database.save_meal(
        meal_name=m_name,
        meal_type=meal_cat,
        image_path=None,
        nutrition_summary=meal_nutr,
        notes=m_notes
    )
    st.success(f"Meal successfully saved with Record ID #{saved_id}.")
    st.session_state['meal_builder_items'] = []
    if st.button("Go to Dashboard"):
        st.switch_page("pages/1_Dashboard.py")
