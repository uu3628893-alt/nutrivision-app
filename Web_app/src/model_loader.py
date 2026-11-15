"""
Model loading and hardware management module for deep segmentation models.
Supports U-Net (ResNet-34) and DeepLabV3+ (ResNet-50) with ImageNet backbones.
"""

import os
from typing import Dict, Any, Tuple
import torch
import segmentation_models_pytorch as smp

from src.paths import UNET_CHECKPOINT_PATH, DEEPLAB_CHECKPOINT_PATH
from src.config import AVAILABLE_MODELS, NUM_CLASSES, DEFAULT_MODEL_NAME

# Optional Streamlit cache decorator
try:
    import streamlit as st
    cache_resource = st.cache_resource
except ImportError:
    def cache_resource(func):
        return func

def get_device() -> torch.device:
    """Return available torch compute device."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

def get_device_info() -> Dict[str, Any]:
    """Return hardware compute information for UI display."""
    cuda_avail = torch.cuda.is_available()
    info = {
        "cuda_available": cuda_avail,
        "device_type": "GPU" if cuda_avail else "CPU",
        "device_name": torch.cuda.get_device_name(0) if cuda_avail else "System CPU",
        "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if cuda_avail else 0.0
    }
    return info

def get_available_models() -> Dict[str, Dict[str, Any]]:
    """Return available models and check their physical checkpoint existence."""
    models_status = {}
    for name, cfg in AVAILABLE_MODELS.items():
        chk_path = UNET_CHECKPOINT_PATH if cfg["architecture"] == "unet" else DEEPLAB_CHECKPOINT_PATH
        models_status[name] = {
            **cfg,
            "path": chk_path,
            "exists": chk_path.exists(),
            "size_mb": round(chk_path.stat().st_size / (1024**2), 2) if chk_path.exists() else 0.0
        }
    return models_status

@cache_resource
def load_segmentation_model(model_name: str = DEFAULT_MODEL_NAME, device_str: str = None) -> Tuple[torch.nn.Module, torch.device]:
    """
    Load specified segmentation architecture and restore trained weights.
    Caches the loaded model in memory for fast interactive inference.
    """
    device = torch.device(device_str) if device_str else get_device()
    
    if model_name not in AVAILABLE_MODELS:
        raise ValueError(f"Model '{model_name}' is not recognized. Options: {list(AVAILABLE_MODELS.keys())}")
        
    cfg = AVAILABLE_MODELS[model_name]
    arch = cfg["architecture"]
    encoder = cfg["encoder"]
    chk_path = UNET_CHECKPOINT_PATH if arch == "unet" else DEEPLAB_CHECKPOINT_PATH
    
    if not chk_path.exists():
        raise FileNotFoundError(
            f"Checkpoint for '{model_name}' not found at: {chk_path}\n"
            f"Ensure the trained weights file is located in the project checkpoints directory."
        )
        
    # Instantiate architecture matching exact training configuration
    if arch == "unet":
        model = smp.Unet(
            encoder_name=encoder,
            encoder_weights=None, # Loading trained weights from checkpoint
            in_channels=3,
            classes=NUM_CLASSES
        )
    elif arch == "deeplabv3plus":
        model = smp.DeepLabV3Plus(
            encoder_name=encoder,
            encoder_weights=None,
            in_channels=3,
            classes=NUM_CLASSES
        )
    else:
        raise ValueError(f"Unsupported architecture: {arch}")
        
    # Load state dictionary
    state_dict = torch.load(chk_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    
    return model, device

