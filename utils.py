#!/usr/bin/env python3
"""
Yardımcı fonksiyonlar ve yardımcı sınıflar
"""

import cv2
import os
import logging
from datetime import datetime
from config import CONFIG, DETECTION_DIR

# Loglama
logger = logging.getLogger("hailo_fire_smoke_detection.utils")

def setup_directories():
    """Gerekli dizinleri oluştur"""
    os.makedirs(DETECTION_DIR, exist_ok=True)
    
def setup_logging():
    """Loglama yapılandırmasını ayarla"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('fire_smoke_detection.log')
        ]
    )
    return logging.getLogger("hailo_fire_smoke_detection")

def draw_detections(frame, detections, class_names):
    """Tespitleri görüntü üzerine çiz"""
    for det in detections:
        x1, y1, x2, y2 = det["box"]
        class_id = det["class_id"]
        score = det["score"]
        class_name = det["class_name"]
        
        # Sınıfa göre renk seç
        color = (0, 0, 255) if class_name == "fire" else (0, 165, 255)  # Kırmızı: ateş, Turuncu: duman
        
        # Kutu çiz
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Etiket çiz
        label = f"{class_name} {score:.2f}"
        (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - text_height - 10), (x1 + text_width, y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Zaman damgası ekle
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    return frame

def save_detection_image(frame):
    """Tespit edilen kareyi kaydet"""
    if CONFIG["save_detections"]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detection_filename = f"{DETECTION_DIR}/detection_{timestamp}.jpg"
        cv2.imwrite(detection_filename, frame)
        logger.info(f"Tespit kaydedildi: {detection_filename}")
