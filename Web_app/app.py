import os
import sys
from pathlib import Path

# Ensure application source directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import streamlit as st
import torch
from src import paths
from src import database
from src import model_loader
from src import nutrition_database

# Page configuration
st.set_page_config(
    page_title="NutriVision – AI Nutritional Analysis",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize local SQLite database
database.init_database()

# Application Header
st.title("NutriVision")
st.subheader("AI-Powered Nutritional Analysis and Personalised Dietary Recommendation System")
st.caption("MSc Data Science and Artificial Intelligence Project | Integrated Deep Learning and Clinical Nutrition")

# System Status and Resource Diagnostics
st.markdown("### System Architecture and Resource Status")

col1, col2, col3, col4 = st.columns(4)

# 1. Device and GPU
with col1:
    device = model_loader.get_device()
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Host CPU"
    st.metric(label="Computation Engine", value=str(device).upper(), delta=gpu_name)

# 2. Checkpoints Status
with col2:
    chk_deeplab = paths.DEEPLAB_CHECKPOINT_PATH.exists()
    chk_unet = paths.UNET_CHECKPOINT_PATH.exists()
    status_str = "Available" if (chk_deeplab and chk_unet) else "Partial"
    st.metric(label="Trained Models", value=status_str, delta="DeepLabV3+ & U-Net")

# 3. USDA FNDDS Knowledge Base
with col3:
    try:
        summary = nutrition_database.get_database_summary()
        f_count = summary.get("total_foods", 0)
        p_count = summary.get("total_portions", 0)
        st.metric(label="USDA FNDDS Foods", value=f"{f_count:,}", delta=f"{p_count:,} portions")
    except Exception as e:
        st.metric(label="USDA FNDDS Foods", value="Error Loading", delta=str(e)[:15])

# 4. User Profile
with col4:
    user_prof = database.get_user_profile()
    profile_status = "Active" if user_prof else "Not Configured"
    delta_text = f"Goal: {user_prof.get('goal', 'N/A')}" if user_prof else "Create Profile"
    st.metric(label="User Profile", value=profile_status, delta=delta_text)

# System Workflow Overview
st.markdown("### End-to-End Methodological Pipeline")

col_w1, col_w2, col_w3 = st.columns(3)

with col_w1:
    st.markdown("#### 1. Computer Vision Segmentation")
    st.write(
        "Upload meal photography. Deep convolutional neural network architectures "
        "(DeepLabV3+ with ResNet-50 and U-Net with ResNet-34) trained on FoodSeg103 perform pixel-level semantic "
        "segmentation across 103 culinary ingredient classes."
    )

with col_w2:
    st.markdown("#### 2. USDA FNDDS Nutritional Mapping")
    st.write(
        "Detected ingredients are deterministically linked to empirical USDA Food and Nutrient Database for Dietary Studies "
        "(FNDDS 2021-2023) records, providing portion-scaled macronutrient and micronutrient profiles."
    )

with col_w3:
    st.markdown("#### 3. Personalised Recommendations")
    st.write(
        "Meal nutrient values are evaluated against user physiological baselines (Mifflin-St Jeor REE, WHO BMI, and "
        "AMDR energy distribution targets) to generate clinically aligned dietary feedback and safety alerts."
    )

# Quick Navigation Section
st.markdown("### Application Modules")

nav_col1, nav_col2, nav_col3 = st.columns(3)

with nav_col1:
    st.info("**Dashboard**\n\nMonitor daily caloric intake, macronutrient distributions, and compliance with dietary targets over time.")
    st.info("**Food Image Analysis**\n\nUpload food imagery, run automated segmentation inference, inspect masks, and detect ingredients.")

with nav_col2:
    st.info("**Nutrition Analysis**\n\nScale empirical USDA portion sizes, compute exact nutrient breakdown, and review clinical feedback.")
    st.info("**User Profile**\n\nConfigure anthropometric measurements, daily caloric goals, physical activity levels, and food allergies.")

with nav_col3:
    st.info("**Meal History**\n\nAccess comprehensive historical meal logs, individual ingredient breakdowns, and nutrient tracking.")
    st.info("**Reports & Exports**\n\nGenerate and download structured CSV records and professional clinical assessment PDF reports.")

st.caption("Project developed in accordance with the MSc Data Science and Artificial Intelligence research curriculum.")
