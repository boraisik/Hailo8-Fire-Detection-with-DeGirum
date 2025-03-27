#!/usr/bin/env python3
"""
Home Assistant entegrasyonu için işlevler
"""

import requests
import logging
from datetime import datetime
from config import HOME_ASSISTANT_CONFIG

# Loglama
logger = logging.getLogger("hailo_fire_smoke_detection.home_assistant")

class HomeAssistantManager:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {HOME_ASSISTANT_CONFIG['token']}",
            "Content-Type": "application/json"
        }
        self.api_url = f"{HOME_ASSISTANT_CONFIG['url']}/api/states/{HOME_ASSISTANT_CONFIG['sensor_name']}"
    
    def update_sensor(self, detection_state):
        """Home Assistant sensörünü güncelle"""
        try:
            # Sensör verisi oluştur
            now = datetime.now().isoformat()
            sensor_data = {
                "state": "on" if detection_state["fire_detected"] or detection_state["smoke_detected"] else "off",
                "attributes": {
                    "friendly_name": "Hailo Fire Detection",
                    "device_class": "fire",
                    "fire_detected": detection_state["fire_detected"],
                    "smoke_detected": detection_state["smoke_detected"],
                    "last_fire_time": detection_state["last_fire_time"],
                    "last_smoke_time": detection_state["last_smoke_time"],
                    "detection_count": detection_state["detection_count"],
                    "fire_confidence": detection_state["fire_confidence"],
                    "smoke_confidence": detection_state["smoke_confidence"],
                    "last_updated": now
                }
            }
            
            # Home Assistant API'sine gönder
            response = requests.post(self.api_url, headers=self.headers, json=sensor_data)
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Home Assistant sensörü güncellendi: {HOME_ASSISTANT_CONFIG['sensor_name']}")
                return True
            else:
                logger.error(f"Home Assistant sensörü güncellenemedi. Durum kodu: {response.status_code}, Yanıt: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Home Assistant güncelleme hatası: {str(e)}")
            return False
    
    def create_initial_sensor(self):
        """İlk çalıştırmada sensörü oluştur"""
        try:
            sensor_data = {
                "state": "off",
                "attributes": {
                    "friendly_name": "Hailo Fire Detection",
                    "device_class": "fire",
                    "fire_detected": False,
                    "smoke_detected": False,
                    "last_updated": datetime.now().isoformat()
                }
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=sensor_data)
            
            if response.status_code == 200 or response.status_code == 201:
                logger.info(f"Home Assistant sensörü oluşturuldu: {HOME_ASSISTANT_CONFIG['sensor_name']}")
                return True
            else:
                logger.error(f"Home Assistant sensörü oluşturulamadı. Durum kodu: {response.status_code}, Yanıt: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Home Assistant başlatma hatası: {str(e)}")
            return False
