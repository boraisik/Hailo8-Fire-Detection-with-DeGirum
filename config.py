#!/usr/bin/env python3
"""
Configuration settings for DeGirum Hailo 8 Fire and Smoke Detection System
"""

import os

# RTSP Configuration
RTSP_URL = "rtsp://username:password@camera-ip:554/stream1"

# Application Configuration
CONFIG = {
    "detection_threshold": 0.5,  # Detection threshold
    "frame_skip": 2,  # Number of frames to skip (for performance)
    "display_output": False,  # Show output - disabled by default
    "save_detections": True,  # Save detection images
    "alert_mode": True,  # Enable alarm mode
}

# Home Assistant Configuration
HOME_ASSISTANT_CONFIG = {
    "url": "http://your-home-assistant-ip:8123",
    "token": "your-long-lived-access-token",
    "sensor_name": "sensor.hailo_fire_detection",
    "update_interval": 5  # How often to update Home Assistant (in seconds)
}

# MQTT Configuration
MQTT_CONFIG = {
    "enabled": True,
    "host": "your-mqtt-broker-ip",
    "port": 1883,
    "user": "mqtt-username",
    "password": "mqtt-password",
    "topic_prefix": "hailo/fire",
    "state_topic": "hailo/fire/state",
    "image_topic": "hailo/fire/image",
    "availability_topic": "hailo/fire/availability",
    "update_interval": 2  # How often to update MQTT (in seconds)
}

# DeGirum Configuration
MODEL_CONFIG = {
    "model_path": os.environ.get("MODEL_PATH", "/path/to/models/yolov8n_relu6_fire_smoke--640x640_quant_hailort_hailo8_1"),
    "zoo_url": "/path/to/models",
    "inference_host_address": "@local",
    "token": '',
    "model_name": "yolov8n_relu6_fire_smoke--640x640_quant_hailort_hailo8_1",
    "class_names": ['fire', 'smoke']
}

# Directories
DETECTION_DIR = "detection_images"
DEBUG_IMAGES_DIR = "debug_images"
