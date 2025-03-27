#!/usr/bin/env python3
"""
DeGirum Hailo 8 Yangın ve Duman Tespit Sistemi (RTSP Akışı için) - Ana Program
RTSP kameraya doğrudan bağlanır, görüntüleri işler ve Hailo 8 kullanarak yangın ve duman tespiti yapar.
MQTT ve Home Assistant entegrasyonu içerir.
"""

import os
import logging
from datetime import datetime

from utils import setup_directories, setup_logging
from detector import FireSmokeDetector
from home_assistant import HomeAssistantManager
from mqtt_manager import MQTTManager
from config import DETECTION_DIR, DEBUG_IMAGES_DIR

def main():
    # Loglama ve dizin yapısını kur
    logger = setup_logging()
    logger.info("DeGirum Hailo 8 Yangın ve Duman Tespit Sistemi başlatılıyor...")
    
    # Dizinleri oluştur
    setup_directories()
    
    # İlk Home Assistant sensörünü oluştur
    ha_manager = HomeAssistantManager()
    ha_manager.create_initial_sensor()
    
    # Tespit sistemini başlat
    detector = FireSmokeDetector()
    detector.start()


if __name__ == "__main__":
    main()
