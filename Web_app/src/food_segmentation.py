"""
Image preprocessing and semantic food segmentation inference pipeline.
"""

from typing import Dict, List, Any, Tuple
import numpy as np
import cv2
from PIL import Image
import torch
import torch.nn.functional as F

from src.config import IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD, SEGMENTATION_PALETTE
from src.food_labels import get_class_name

def preprocess_image(image: np.ndarray, target_size: Tuple[int, int] = IMAGE_SIZE) -> Tuple[torch.Tensor, Tuple[int, int]]:
    """
    Resize and normalize input image strictly matching the training pipeline.
    Returns normalized tensor of shape (1, 3, H, W) and original resolution (H, W).
    """
    orig_h, orig_w = image.shape[:2]
    
    # Bilinear interpolation for image resizing
    resized = cv2.resize(image, target_size, interpolation=cv2.INTER_LINEAR)
    
    # Normalise with ImageNet mean and std
    norm_img = resized.astype(np.float32) / 255.0
    mean = np.array(IMAGENET_MEAN, dtype=np.float32)
    std = np.array(IMAGENET_STD, dtype=np.float32)
    norm_img = (norm_img - mean) / std
    
    # Convert from (H, W, C) to (1, C, H, W) torch tensor
    tensor = torch.from_numpy(norm_img).permute(2, 0, 1).unsqueeze(0).float()
    return tensor, (orig_h, orig_w)

def generate_segmentation_overlay(
    image: np.ndarray,
    mask: np.ndarray,
    alpha: float = 0.35,
    palette: np.ndarray = SEGMENTATION_PALETTE
) -> np.ndarray:
    """Blend colored mask with original RGB image."""
    color_mask = palette[mask]
    overlay = cv2.addWeighted(image, 1.0 - alpha, color_mask, alpha, 0)
    return overlay

def segment_food_image(
    model: torch.nn.Module,
    image_input: Any,
    device: torch.device,
    min_pixel_percentage: float = 0.5
) -> Dict[str, Any]:
    """
    Execute end-to-end segmentation on food image.
    Extracts detected ingredients, pixel areas, and confidence metrics.
    """
    # Standardize input to RGB uint8 numpy array
    if isinstance(image_input, Image.Image):
        img_np = np.array(image_input.convert("RGB"))
    elif isinstance(image_input, np.ndarray):
        img_np = image_input.copy()
        if len(img_np.shape) == 2:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
    else:
        raise ValueError("Unsupported image type. Provide PIL Image or numpy array.")
        
    orig_h, orig_w = img_np.shape[:2]
    total_pixels = orig_h * orig_w
    
    # Preprocess
    input_tensor, _ = preprocess_image(img_np, target_size=IMAGE_SIZE)
    input_tensor = input_tensor.to(device)
    
    # Inference
    model.eval()
    with torch.no_grad():
        logits = model(input_tensor)
        probs = F.softmax(logits, dim=1)
        pred_mask_512 = torch.argmax(probs, dim=1).squeeze(0).cpu().numpy()
        confidence_map_512 = torch.max(probs, dim=1).values.squeeze(0).cpu().numpy()
        
    # Resize predicted mask back to original image resolution with nearest neighbor
    pred_mask = cv2.resize(pred_mask_512.astype(np.uint8), (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)
    confidence_map = cv2.resize(confidence_map_512.astype(np.float32), (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
    
    # Identify detected ingredient categories (excluding background class 0)
    detected_classes = [c for c in np.unique(pred_mask) if c != 0]
    
    detected_ingredients = []
    for cls_id in detected_classes:
        cls_mask = (pred_mask == cls_id)
        pixel_count = int(np.sum(cls_mask))
        pixel_pct = round((pixel_count / total_pixels) * 100.0, 2)
        
        # Filter negligible noise artifacts
        if pixel_pct < min_pixel_percentage:
            continue
            
        mean_conf = round(float(np.mean(confidence_map[cls_mask])), 4)
        
        detected_ingredients.append({
            "class_id": int(cls_id),
            "foodseg_name": get_class_name(cls_id),
            "pixel_count": pixel_count,
            "pixel_percentage": pixel_pct,
            "confidence": mean_conf,
            "color_rgb": SEGMENTATION_PALETTE[cls_id].tolist()
        })
        
    # Sort detected ingredients by pixel area descending
    detected_ingredients.sort(key=lambda x: x["pixel_percentage"], reverse=True)
    
    # Generate visualization overlay
    overlay_img = generate_segmentation_overlay(img_np, pred_mask)
    
    return {
        "original_image": img_np,
        "predicted_mask": pred_mask,
        "overlay_image": overlay_img,
        "detected_ingredients": detected_ingredients,
        "total_pixels": total_pixels
    }

