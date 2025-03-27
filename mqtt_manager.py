#!/usr/bin/env python3
"""
MQTT yönetimi ve entegrasyonu için işlevler
"""

import json
import logging
import base64
import cv2
import paho.mqtt.client as mqtt
from datetime import datetime
from config import MQTT_CONFIG

# Loglama
logger = logging.getLogger("hailo_fire_smoke_detection.mqtt")

class MQTTManager:
    def __init__(self):
        self.client = None
        self.connected = False
        
    def connect(self):
        """MQTT sunucusuna bağlan ve gerekli yapılandırmaları ayarla"""
        if not MQTT_CONFIG["enabled"]:
            logger.info("MQTT devre dışı bırakıldı.")
            return False
            
        try:
            self.client = mqtt.Client(client_id="hailo-fire-detection")
            self.client.username_pw_set(MQTT_CONFIG["user"], MQTT_CONFIG["password"])
            self.client.will_set(MQTT_CONFIG["availability_topic"], "offline", qos=1, retain=True)
            self.client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"], 60)
            self.client.loop_start()
            
            # Availability bildirimi yayınla
            self.client.publish(MQTT_CONFIG["availability_topic"], "online", qos=1, retain=True)
            logger.info(f"MQTT sunucusuna bağlandı: {MQTT_CONFIG['host']}:{MQTT_CONFIG['port']}")
            
            # Home Assistant MQTT otomatik keşif için yapılandırma yayınla
            self.publish_discovery_configs()
            
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"MQTT bağlantı hatası: {str(e)}")
            self.connected = False
            return False
            
    def publish_discovery_configs(self):
        """Home Assistant MQTT otomatik keşif yapılandırmalarını yayınla"""
        try:
            # Binary sensör yapılandırması
            discovery_config = {
                "name": "Hailo Fire Detection",
                "device_class": "smoke",
                "state_topic": MQTT_CONFIG["state_topic"],
                "availability_topic": MQTT_CONFIG["availability_topic"],
                "payload_available": "online",
                "payload_not_available": "offline",
                "value_template": "{{ value_json.state }}",
                "json_attributes_topic": MQTT_CONFIG["state_topic"],
                "unique_id": "hailo_fire_detection",
                "device": {
                    "identifiers": ["hailo_fire_detection"],
                    "name": "Hailo Fire Detection",
                    "model": "Hailo 8",
                    "manufacturer": "DeGirum"
                }
            }
            self.client.publish("homeassistant/binary_sensor/hailo_fire/config", 
                               json.dumps(discovery_config), qos=1, retain=True)
            
            # Kamera yapılandırması
            camera_discovery_config = {
                "name": "Hailo Fire Detection Camera",
                "topic": MQTT_CONFIG["image_topic"],
                "unique_id": "hailo_fire_detection_camera",
                "device": {
                    "identifiers": ["hailo_fire_detection"],
                    "name": "Hailo Fire Detection",
                    "model": "Hailo 8",
                    "manufacturer": "DeGirum"
                }
            }
            self.client.publish("homeassistant/camera/hailo_fire/config", 
                               json.dumps(camera_discovery_config), qos=1, retain=True)
            
            logger.info("MQTT discovery yapılandırmaları yayınlandı")
        except Exception as e:
            logger.error(f"MQTT discovery yapılandırma hatası: {str(e)}")
    
    def update_state(self, detection_state, processed_frame=None, force=False):
        """MQTT aracılığıyla durumu güncelle"""
        if not self.connected or not MQTT_CONFIG["enabled"]:
            return
            
        try:
            # Durum verilerini yayınla
            self.client.publish(MQTT_CONFIG["state_topic"], json.dumps(detection_state), qos=1, retain=True)
            
            # Tespit durumunda resim gönder
            if processed_frame is not None and (detection_state["fire_detected"] or detection_state["smoke_detected"]):
                self.send_image(processed_frame)
                
            logger.debug("MQTT durumu güncellendi")
                
        except Exception as e:
            logger.error(f"MQTT güncelleme hatası: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def send_image(self, frame):
        """MQTT üzerinden base64 ile kodlanmış bir resim gönder"""
        if not self.connected:
            return
            
        try:
            # Resmi yeniden boyutlandır ve kalitesini düşür (daha hızlı iletim için)
            max_width = 640
            height, width = frame.shape[:2]
            
            if width > max_width:
                ratio = max_width / width
                new_height = int(height * ratio)
                small_frame = cv2.resize(frame, (max_width, new_height))
            else:
                small_frame = frame
                
            # JPEG olarak kodla
            success, jpg_buffer = cv2.imencode(".jpg", small_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            if success:
                # Base64 kodla
                jpg_as_text = base64.b64encode(jpg_buffer).decode('utf-8')
                # Resim konusunda yayınla
                self.client.publish(MQTT_CONFIG["image_topic"], jpg_as_text, qos=0, retain=True)
                logger.debug("MQTT üzerinden tespit resmi gönderildi")
        except Exception as e:
            logger.error(f"MQTT resim gönderme hatası: {str(e)}")
    
    def set_offline(self):
        """Sistem çıkışında offline durumunu bildir"""
        if self.connected:
            try:
                self.client.publish(MQTT_CONFIG["availability_topic"], "offline", qos=1, retain=True)
                self.client.disconnect()
                logger.info("MQTT bağlantısı kapatıldı")
            except Exception as e:
                logger.error(f"MQTT kapatma hatası: {str(e)}")
    
    def publish_initial_state(self):
        """Başlangıç durumunu yayınla"""
        if self.connected:
            try:
                initial_state = {
                    "state": "OFF",
                    "fire_detected": False,
                    "smoke_detected": False,
                    "detection_count": 0,
                    "last_updated": datetime.now().isoformat()
                }
                self.client.publish(MQTT_CONFIG["state_topic"], json.dumps(initial_state), qos=1, retain=True)
                logger.info("MQTT başlangıç durumu gönderildi")
            except Exception as e:
                logger.error(f"MQTT başlangıç durumu gönderme hatası: {str(e)}")
