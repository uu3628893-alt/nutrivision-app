import sys
from pathlib import Path
from PIL import Image
import numpy as np

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
import pandas as pd
from src import model_loader
from src import food_segmentation
from src import food_labels
from src import food_mapping
from src.config import AVAILABLE_MODELS, DEFAULT_MODEL_NAME

st.set_page_config(page_title="Food Image Analysis - NutriVision", layout="wide")

st.title("Food Image Semantic Segmentation")
st.caption("Deep Learning Ingredient Identification using FoodSeg103 Models")

# Sidebar Controls
st.sidebar.markdown("### Inference Settings")
model_options = list(AVAILABLE_MODELS.keys())
selected_model_key = st.sidebar.selectbox(
    "Segmentation Architecture",
    options=model_options,
    index=0
)

min_pixel_pct = st.sidebar.slider(
    "Minimum Pixel Coverage (%)",
    min_value=0.1,
    max_value=5.0,
    value=0.5,
    step=0.1
)

# Hardware and Architecture Details
arch_info = AVAILABLE_MODELS[selected_model_key]
st.sidebar.caption(
    f"Backbone: **{arch_info['encoder']}** | "
    f"Validation mIoU: **{arch_info['test_miou']:.4f}**"
)

# Image Acquisition Source
st.markdown("### Meal Photograph Input")
input_mode = st.radio("Choose Input Method:", ["Select Benchmark Sample Meal", "Upload Custom Food Photograph"], horizontal=True)

selected_image = None
samples_dir = CURRENT_DIR / "assets" / "samples"

if input_mode == "Select Benchmark Sample Meal":
    sample_files = sorted(list(samples_dir.glob("*.jpg")))
    if sample_files:
        sample_choice = st.selectbox(
            "Select Evaluation Sample:",
            options=[f.name for f in sample_files],
            format_func=lambda x: f"Validation Benchmark: {x}"
        )
        selected_image = Image.open(samples_dir / sample_choice).convert("RGB")
    else:
        st.info("No sample benchmark images found in assets folder.")
else:
    uploaded_file = st.file_uploader("Upload Meal Photograph", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        selected_image = Image.open(uploaded_file).convert("RGB")

if selected_image is not None:
    col_img, col_info = st.columns([1, 1])
    with col_img:
        st.image(selected_image, caption=f"Input Image ({selected_image.size[0]}x{selected_image.size[1]} px)", use_container_width=True)

    with col_info:
        st.markdown("#### Model Specification")
        st.write(f"• **Architecture**: {selected_model_key}")
        st.write(f"• **Description**: {arch_info['description']}")
        st.write(f"• **Input Resolution**: Standardized to 512 x 512 pixels")
        st.write(f"• **Target Classes**: 104 categories (103 food ingredients + background)")
        st.write(f"• **Execution Device**: `{model_loader.get_device()}`")

        run_inference = st.button("Run Food Segmentation", type="primary")

    if run_inference:
        with st.spinner("Executing neural semantic segmentation inference..."):
            try:
                model, device = model_loader.load_segmentation_model(selected_model_key)
                seg_result = food_segmentation.segment_food_image(
                    model=model,
                    image_input=selected_image,
                    device=device,
                    min_pixel_percentage=min_pixel_pct
                )

                st.session_state['seg_result'] = seg_result
                st.session_state['last_image'] = selected_image
                st.success(f"Inference complete: {len(seg_result['detected_ingredients'])} ingredient categories detected.")
            except Exception as e:
                st.error(f"Inference error: {e}")

# Display Segmentation Results if available
if 'seg_result' in st.session_state and st.session_state['seg_result'] is not None:
    seg_result = st.session_state['seg_result']
    detected = seg_result['detected_ingredients']

    st.markdown("### Semantic Segmentation Overlay")
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.image(seg_result['original_image'], caption="Original Image", use_container_width=True)
    with col_res2:
        st.image(seg_result['overlay_image'], caption="Pixel-Level Semantic Segmentation", use_container_width=True)

    st.markdown("### Identified Ingredients & Confidence Metrics")

    if not detected:
        st.warning("No ingredients met the coverage threshold. Consider lowering the minimum coverage percentage in the sidebar.")
    else:
        table_rows = []
        for d in detected:
            mapping = food_mapping.get_mapping_for_class(d['class_id'])
            usda_name = mapping['usda_description'] if mapping else "Unmapped Item"
            table_rows.append({
                "Class ID": d['class_id'],
                "Ingredient Name": d['foodseg_name'].title(),
                "Coverage (%)": f"{d['pixel_percentage']:.2f}%",
                "Mean Confidence": f"{d['confidence'] * 100:.1f}%",
                "Mapped USDA Category": usda_name
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    # Interactive Ingredient Refinement
    st.markdown("### Refine Identified Ingredients")
    st.caption("You may add missing ingredients or remove false positive detections before proceeding to nutritional calculation.")

    all_categories = food_labels.get_all_food_categories()
    current_names = [d['foodseg_name'] for d in detected]

    col_add, col_del = st.columns(2)
    with col_add:
        add_choice = st.selectbox(
            "Add Missing Ingredient:",
            options=["-- Select to Add --"] + [c.title() for c in all_categories if c.lower() not in current_names]
        )
        if st.button("Add Ingredient") and add_choice != "-- Select to Add --":
            cid = food_labels.get_class_id(add_choice.lower())
            if cid is not None:
                detected.append({
                    'class_id': cid,
                    'foodseg_name': food_labels.get_class_name(cid),
                    'pixel_count': 1000,
                    'pixel_percentage': 5.0,
                    'confidence': 1.0,
                    'color_rgb': [100, 100, 100]
                })
                seg_result['detected_ingredients'] = detected
                st.session_state['seg_result'] = seg_result
                st.rerun()

    with col_del:
        if current_names:
            del_choice = st.selectbox("Remove False Positive:", options=["-- Select to Remove --"] + [n.title() for n in current_names])
            if st.button("Remove Ingredient") and del_choice != "-- Select to Remove --":
                detected = [d for d in detected if d['foodseg_name'].lower() != del_choice.lower()]
                seg_result['detected_ingredients'] = detected
                st.session_state['seg_result'] = seg_result
                st.rerun()

    # Navigation to Nutrition Analysis
    st.markdown("### Next Step")
    if st.button("Proceed to Nutrition Analysis", type="primary"):
        # Format payload for Nutrition Analysis page
        st.session_state['transferred_ingredients'] = [
            {'class_id': d['class_id'], 'foodseg_name': d['foodseg_name']} for d in detected
        ]
        st.switch_page("pages/3_Nutrition_Analysis.py")
