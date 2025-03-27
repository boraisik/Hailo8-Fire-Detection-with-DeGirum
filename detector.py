#!/usr/bin/env python3
"""
DeGirum Hailo 8 temelli Yangın ve Duman tespit işlemleri
"""

import os
import cv2
import time
import sys
import logging
import threading
import queue
import tempfile
from datetime import datetime
import numpy as np

from config import CONFIG, MODEL_CONFIG, RTSP_URL, HOME_ASSISTANT_CONFIG, MQTT_CONFIG
from utils import draw_detections, save_detection_image
from mqtt_manager import MQTTManager
from home_assistant import HomeAssistantManager

# Loglama
logger = logging.getLogger("hailo_fire_smoke_detection.detector")

# DeGirum API'sini içe aktar
try:
    import degirum as dg
except ImportError:
    logger.error("DeGirum API yüklenemedi. Lütfen 'pip install degirum' komutunu çalıştırın.")
    sys.exit(1)

class FireSmokeDetector:
    def __init__(self):
        self.frame_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        self.running = False
        self.frame_count = 0
        self.detection_count = 0
        self.last_alert_time = time.time() - 100  # Başlangıçta hemen uyarı vermek için
        self.last_mqtt_update_time = time.time() - 100  # MQTT güncellemesi için
        
        # Tespit durumu
        self.current_detections = {
            "fire_detected": False,
            "smoke_detected": False,
            "last_fire_time": None,
            "last_smoke_time": None,
            "detection_count": 0,
            "fire_confidence": 0.0,
            "smoke_confidence": 0.0,
            "state": "OFF",
            "last_updated": datetime.now().isoformat()
        }
        
        # Son işlenmiş kare
        self.last_processed_frame = None
        
        # MQTT ve Home Assistant yöneticileri
        self.mqtt_manager = MQTTManager()
        self.ha_manager = HomeAssistantManager()
        
        # DeGirum modeli yükle
        self.load_model()
        
        # İş parçacıkları
        self.capture_thread_obj = None
        self.processing_thread_obj = None
        self.display_thread_obj = None
        self.home_assistant_thread_obj = None
        self.mqtt_thread_obj = None
    
    def load_model(self):
        """DeGirum Hailo 8 modelini yükle"""
        try:
            logger.info(f"Model yükleniyor: {MODEL_CONFIG['model_name']}")
            
            # Modeli yükle
            self.model = dg.load_model(
                model_name=MODEL_CONFIG['model_name'],
                inference_host_address=MODEL_CONFIG['inference_host_address'],
                zoo_url=MODEL_CONFIG['zoo_url'],
                token=MODEL_CONFIG['token']
            )
            
            logger.info(f"Model başarıyla yüklendi.")
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            sys.exit(1)
    
    def process_frame(self, frame):
        """Tek bir kareyi işle ve sonuçları döndür"""
        try:
            # Preprocessing ve çıkarım başlangıcı
            start_time = time.time()
            original_size = (frame.shape[0], frame.shape[1])
            
            # Modelin istediği boyuta (640x640) yeniden boyutlandır
            resized_frame = cv2.resize(frame, (640, 640))
            
            # Geçici dosyaya kaydet
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                temp_path = tmp.name
            
            # Görüntüyü yüksek kalitede kaydet
            cv2.imwrite(temp_path, resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Çıkarım - direk modeli fonksiyon olarak çağır
            result = self.model(temp_path)
            
            # Geçici dosyayı temizle
            try:
                os.unlink(temp_path)
            except:
                pass
                
            inference_time = time.time() - start_time
            
            # Tespit durumlarını güncelle
            fire_detected = False
            smoke_detected = False
            fire_confidence = 0.0
            smoke_confidence = 0.0
            
            detections = []
            
            # İşleme sonuçları
            if hasattr(result, 'results') and isinstance(result.results, list):
                logger.debug(f"Tespit sonuçları: {len(result.results)}")
                
                for detection in result.results:
                    # 'bbox' alanını kontrol et
                    if 'bbox' in detection:
                        bbox = detection['bbox']
                        if len(bbox) == 4:
                            # Normalize coordinates from the model (640x640) to original frame size
                            x1, y1, x2, y2 = map(float, bbox)
                            
                            # Model normalize koordinat veriyorsa (0-1 arası) orijinal boyuta dönüştür
                            if x1 <= 1.0 and y1 <= 1.0 and x2 <= 1.0 and y2 <= 1.0:
                                x1 = int(x1 * original_size[1])
                                y1 = int(y1 * original_size[0])
                                x2 = int(x2 * original_size[1])
                                y2 = int(y2 * original_size[0])
                            else:
                                # 640x640 koordinatlarını orijinal boyuta ölçekle
                                x1 = int(x1 * original_size[1] / 640)
                                y1 = int(y1 * original_size[0] / 640)
                                x2 = int(x2 * original_size[1] / 640)
                                y2 = int(y2 * original_size[0] / 640)
                            
                            # Sınıf kimliğini ve skoru al
                            class_id = detection.get('class_id', 0)
                            score = detection.get('score', 0)
                            class_name = detection.get('class_name', '')
                            
                            if score > CONFIG["detection_threshold"]:
                                # DeGirum class_name değerini doğrudan döndürür
                                if class_name == "fire":
                                    fire_detected = True
                                    fire_confidence = max(fire_confidence, score)
                                elif class_name == "smoke":
                                    smoke_detected = True  
                                    smoke_confidence = max(smoke_confidence, score)
                                
                                detections.append({
                                    "box": [x1, y1, x2, y2],
                                    "score": float(score),
                                    "class_id": int(class_id),
                                    "class_name": class_name
                                })
            
            # Tespit durumunu güncelle
            now = datetime.now().isoformat()
            
            # Tespit durumunu güncelle
            if fire_detected:
                self.current_detections["fire_detected"] = True
                self.current_detections["last_fire_time"] = now
                self.current_detections["fire_confidence"] = fire_confidence
                
            if smoke_detected:
                self.current_detections["smoke_detected"] = True
                self.current_detections["last_smoke_time"] = now
                self.current_detections["smoke_confidence"] = smoke_confidence
                
            if fire_detected or smoke_detected:
                self.current_detections["detection_count"] += 1
                self.current_detections["state"] = "ON"
            
            # Sonuçları kaydet
            processed_frame = frame.copy()
            if detections:
                processed_frame = draw_detections(processed_frame, detections, MODEL_CONFIG['class_names'])
                self.detection_count += 1
                
                # Son işlenmiş kareyi kaydet
                self.last_processed_frame = processed_frame.copy()
                
                # Tespiti kaydet
                save_detection_image(processed_frame)
                
                # Uyarı ver
                if CONFIG["alert_mode"] and time.time() - self.last_alert_time > 10:  # Her 10 saniyede bir uyarı
                    self.last_alert_time = time.time()
                    logger.warning(f"UYARI: {len(detections)} yangın/duman tespit edildi!")
                    
                    # Home Assistant'ı güncelle
                    self.ha_manager.update_sensor(self.current_detections)
                    
                    # MQTT'yi güncelle ve resmi gönder
                    self.mqtt_manager.update_state(self.current_detections, processed_frame)
                else:
                    # Normal MQTT güncellemesi
                    self.mqtt_manager.update_state(self.current_detections)
            else:
                # Tespit yoksa da MQTT'yi güncelle
                self.mqtt_manager.update_state(self.current_detections)
            
            # FPS hesapla
            fps = 1.0 / inference_time
            cv2.putText(processed_frame, f"FPS: {fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.putText(processed_frame, f"FPS: {fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
            
            self.current_detections["last_updated"] = now
            
            return processed_frame, detections, fps
            
        except Exception as e:
            logger.error(f"Kare işleme hatası: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return frame, [], 0
    
    def capture_thread(self):
        """RTSP akışından video yakala"""
        logger.info(f"RTSP URL bağlantısı başlatılıyor: {RTSP_URL}")
        cap = cv2.VideoCapture(RTSP_URL)
        
        if not cap.isOpened():
            logger.error(f"RTSP akışı açılamadı: {RTSP_URL}")
            self.running = False
            return
        
        logger.info("Video yakalama başladı")
        
        frame_count = 0
        while self.running:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Kare yakalanamadı, yeniden bağlanmaya çalışılıyor...")
                time.sleep(1)
                cap = cv2.VideoCapture(RTSP_URL)
                continue
            
            frame_count += 1
            # Performans için kare atlama
            if frame_count % CONFIG["frame_skip"] != 0:
                continue
                
            # Kare kuyruğuna ekle, doluysa en eski kareyi at
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            
            try:
                self.frame_queue.put(frame)
            except:
                pass
        
        cap.release()
        logger.info("Video yakalama durduruldu")
    
    def processing_thread(self):
        """Kare kuyruğundan alınan kareleri işle"""
        logger.info("İşleme başlatıldı")
        
        while self.running:
            try:
                # Kuyruktaki bir sonraki kareyi al
                frame = self.frame_queue.get(timeout=1)
                
                # Kareyi işle
                processed_frame, detections, fps = self.process_frame(frame)
                
                # Sonuç kuyruğuna ekle
                self.result_queue.put((processed_frame, detections, fps))
                
                self.frame_count += 1
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"İşleme hatası: {str(e)}")
        
        logger.info("İşleme durduruldu")
    
    def display_thread(self):
        """İşlenen kareleri göster"""
        logger.info("Görüntüleme başlatıldı")
        
        last_log_time = time.time()
        frames_since_log = 0
        
        try:
            # Görüntüleme penceresini oluşturmadan önce ekran kontrolü yap
            if CONFIG["display_output"]:
                if not os.environ.get('DISPLAY'):
                    logger.warning("DISPLAY ortam değişkeni bulunamadı, görüntüleme devre dışı bırakılıyor")
                    CONFIG["display_output"] = False
        except Exception as e:
            logger.warning(f"Ekran kontrolü başarısız: {str(e)}, görüntüleme devre dışı bırakılıyor")
            CONFIG["display_output"] = False
        
        while self.running:
            try:
                # Sonuç kuyruğundan işlenmiş kareyi al
                processed_frame, detections, fps = self.result_queue.get(timeout=1)
                
                # Kareyi göster
                if CONFIG["display_output"]:
                    try:
                        cv2.imshow("DeGirum Hailo 8 - Yangın ve Duman Tespiti", processed_frame)
                        
                        # 'q' tuşuna basılırsa çık
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.running = False
                            break
                    except Exception as e:
                        logger.error(f"Görüntü gösterme hatası: {str(e)}")
                        CONFIG["display_output"] = False
                        logger.warning("Görüntüleme devre dışı bırakıldı")
                
                frames_since_log += 1
                
                # Her 10 saniyede bir istatistikleri günlüğe kaydet
                if time.time() - last_log_time > 10:
                    fps_avg = frames_since_log / (time.time() - last_log_time)
                    logger.info(f"İstatistikler - FPS: {fps_avg:.2f}, İşlenen kareler: {self.frame_count}, Tespitler: {self.detection_count}")
                    last_log_time = time.time()
                    frames_since_log = 0
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Görüntüleme hatası: {str(e)}")
        
        # Görüntüleme penceresini kapat
        if CONFIG["display_output"]:
            try:
                cv2.destroyAllWindows()
            except:
                pass
        
        logger.info("Görüntüleme durduruldu")
    
    def home_assistant_thread(self):
        """Home Assistant'ı periyodik olarak güncelle"""
        logger.info("Home Assistant güncelleme iş parçacığı başlatıldı")
        
        while self.running:
            try:
                # Belirli aralıklarla Home Assistant'ı güncelle
                time.sleep(HOME_ASSISTANT_CONFIG["update_interval"])
                
                # Sadece tespit varsa güncelle (gereksiz API çağrılarını önlemek için)
                if self.current_detections["fire_detected"] or self.current_detections["smoke_detected"]:
                    self.ha_manager.update_sensor(self.current_detections)
                    
                # 30 saniye boyunca yeni tespit yoksa durumu sıfırla
                if (self.current_detections["fire_detected"] and 
                    self.current_detections["last_fire_time"] and
                    (datetime.now() - datetime.fromisoformat(self.current_detections["last_fire_time"])).total_seconds() > 30):
                    self.current_detections["fire_detected"] = False
                    self.current_detections["fire_confidence"] = 0.0
                    # Home Assistant'ı güncelle
                    self.ha_manager.update_sensor(self.current_detections)
                    
                if (self.current_detections["smoke_detected"] and 
                    self.current_detections["last_smoke_time"] and
                    (datetime.now() - datetime.fromisoformat(self.current_detections["last_smoke_time"])).total_seconds() > 30):
                    self.current_detections["smoke_detected"] = False
                    self.current_detections["smoke_confidence"] = 0.0
                    # Home Assistant'ı güncelle
                    self.ha_manager.update_sensor(self.current_detections)
                
                # Her iki tespit de kapatıldıysa durumu değiştir
                if not self.current_detections["fire_detected"] and not self.current_detections["smoke_detected"]:
                    self.current_detections["state"] = "OFF"
                    
            except Exception as e:
                logger.error(f"Home Assistant güncelleme hatası: {str(e)}")
                
        logger.info("Home Assistant güncelleme iş parçacığı durduruldu")
    
    def mqtt_thread(self):
        """MQTT durumunu periyodik olarak güncelle"""
        logger.info("MQTT güncelleme iş parçacığı başlatıldı")
        
        while self.running:
            try:
                # Belirli aralıklarla MQTT'yi güncelle
                time.sleep(MQTT_CONFIG["update_interval"])
                
                # Son işlenmiş kare varsa, durumla birlikte gönder
                if self.last_processed_frame is not None:
                    self.mqtt_manager.update_state(self.current_detections, self.last_processed_frame)
                else:
                    self.mqtt_manager.update_state(self.current_detections)
                    
                # 30 saniye boyunca yeni tespit yoksa durumu sıfırla
                if (self.current_detections["fire_detected"] and 
                    self.current_detections["last_fire_time"] and
                    (datetime.now() - datetime.fromisoformat(self.current_detections["last_fire_time"])).total_seconds() > 30):
                    self.current_detections["fire_detected"] = False
                    self.current_detections["fire_confidence"] = 0.0
                    # MQTT'yi güncelle
                    self.mqtt_manager.update_state(self.current_detections, force=True)
                    
                if (self.current_detections["smoke_detected"] and 
                    self.current_detections["last_smoke_time"] and
                    (datetime.now() - datetime.fromisoformat(self.current_detections["last_smoke_time"])).total_seconds() > 30):
                    self.current_detections["smoke_detected"] = False
                    self.current_detections["smoke_confidence"] = 0.0
                    # MQTT'yi güncelle
                    self.mqtt_manager.update_state(self.current_detections, force=True)
                
                # Her iki tespit de kapatıldıysa durumu değiştir
                if not self.current_detections["fire_detected"] and not self.current_detections["smoke_detected"]:
                    self.current_detections["state"] = "OFF"
                    
            except Exception as e:
                logger.error(f"MQTT güncelleme hatası: {str(e)}")
                
        logger.info("MQTT güncelleme iş parçacığı durduruldu")
        
        # Çıkışta offline durumunu bildir
        self.mqtt_manager.set_offline()
        
    def start(self):
        """Tüm iş parçacıklarını başlat"""
        self.running = True
        
        # MQTT bağlantısını kur
        mqtt_connected = self.mqtt_manager.connect()
        
        # İş parçacıklarını oluştur
        self.capture_thread_obj = threading.Thread(target=self.capture_thread, name="capture")
        self.processing_thread_obj = threading.Thread(target=self.processing_thread, name="processing")
        self.display_thread_obj = threading.Thread(target=self.display_thread, name="display")
        self.home_assistant_thread_obj = threading.Thread(target=self.home_assistant_thread, name="home_assistant")
        
        # MQTT iş parçacığını ekle
        if mqtt_connected:
            self.mqtt_thread_obj = threading.Thread(target=self.mqtt_thread, name="mqtt")
            self.mqtt_manager.publish_initial_state()
        else:
            self.mqtt_thread_obj = None
        
        # İş parçacıklarını başlat
        self.capture_thread_obj.start()
        self.processing_thread_obj.start()
        self.display_thread_obj.start()
        self.home_assistant_thread_obj.start()
        
        # MQTT iş parçacığını başlat
        if self.mqtt_thread_obj is not None:
            self.mqtt_thread_obj.start()
        
        logger.info("Tüm iş parçacıkları başlatıldı")
        
        try:
            # Ana iş parçacığını çalışır durumda tut
            while self.running:
                time.sleep(0.1)
                
                # Kullanıcı CTRL+C ile kesebilir
                active_threads = [self.capture_thread_obj.is_alive(), 
                                 self.processing_thread_obj.is_alive(),
                                 self.display_thread_obj.is_alive(),
                                 self.home_assistant_thread_obj.is_alive()]
                
                if self.mqtt_thread_obj is not None:
                    active_threads.append(self.mqtt_thread_obj.is_alive())
                
                if not all(active_threads):
                    logger.warning("Bir iş parçacığı durdu, kapatılıyor...")
                    self.running = False
                    break
                    
        except KeyboardInterrupt:
            logger.info("Kullanıcı tarafından durduruldu")
            self.running = False
        
        # İş parçacıklarının bitmesini bekle
        self.capture_thread_obj.join()
        self.processing_thread_obj.join()
        self.display_thread_obj.join()
        self.home_assistant_thread_obj.join()
        
        # MQTT iş parçacığını bekle
        if self.mqtt_thread_obj is not None:
            self.mqtt_thread_obj.join()
        
        logger.info("Uygulama durduruldu")

