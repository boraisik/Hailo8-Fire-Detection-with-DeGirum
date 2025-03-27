# DeGirum Hailo 8 Fire and Smoke Detection System

A modular real-time fire and smoke detection system powered by DeGirum API and Hailo 8 accelerator with MQTT and Home Assistant integration for smart home monitoring.

## Features

- Real-time fire and smoke detection from RTSP camera streams
- DeGirum API and Hailo 8 accelerator support
- Optimized for Raspberry Pi 5 with Hailo 8 accelerator
- Home Assistant integration
- MQTT integration
- Image capture and storage upon detection
- High performance through multi-threading architecture
- Automatic reconnection and error management

## System Requirements

- Raspberry Pi 5 (or equivalent)
- Hailo 8 accelerator
- Python 3.8 or higher
- DeGirum API
- OpenCV
- Paho-MQTT
- Numpy

## Installation

1. Install the required packages:

```bash
pip install opencv-python paho-mqtt numpy requests degirum
```

2. Download the code:

```bash
git clone https://github.com/boraisik/hailo-fire-detection.git
cd hailo-fire-detection
```

3. Edit the configuration file:

Open the `config.py` file and modify the RTSP URL, MQTT, and Home Assistant settings according to your system.

## Usage

Start the program with the following command:

```bash
python main.py
```

The program will automatically perform the following operations:

1. Connect to the RTSP camera
2. Load the DeGirum API and Hailo 8 model
3. Create a Home Assistant sensor
4. Send MQTT discovery messages
5. Start the image processing and detection system

## Modules

The system is divided into the following modules:

- `main.py`: Main program file
- `config.py`: Configuration settings
- `detector.py`: FireSmokeDetector class and detection algorithms
- `mqtt_manager.py`: MQTT connection and communication
- `home_assistant.py`: Home Assistant integration
- `utils.py`: Helper functions

## Configuration

Important configuration parameters in the `config.py` file:

- `RTSP_URL`: RTSP camera stream URL
- `CONFIG`: Detection threshold, frame skipping, and other program settings
- `HOME_ASSISTANT_CONFIG`: Home Assistant connection settings
- `MQTT_CONFIG`: MQTT connection and topic settings
- `MODEL_CONFIG`: DeGirum and Hailo 8 model settings

## Home Assistant Integration

The system integrates with Home Assistant as a binary sensor. The sensor changes to "on" state when fire or smoke is detected. Sensor attributes include:

- Fire detection status
- Smoke detection status
- Last fire detection time
- Last smoke detection time
- Detection count
- Fire and smoke confidence values

## MQTT Integration

The system is automatically configured using Home Assistant's MQTT discovery feature. Data sent over MQTT includes:

- Detection status (ON/OFF)
- Fire and smoke detection states
- Last detection times
- Detection counts and confidence values
- Image of the detection camera (in JPEG format)

## Running as a System Service

To ensure the fire detection system runs continuously, even after reboots, you should set it up as a system service. Follow these steps to configure it as a systemd service on Linux:

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/hailo-fire-detection.service
```

2. Add the following content to the file (adjust paths as needed):

```ini
[Unit]
Description=Hailo Fire and Smoke Detection Service
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/hailo-fire-detection
ExecStart=/usr/bin/python3 /path/to/hailo-fire-detection/main.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=hailo-fire-detection
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hailo-fire-detection.service
sudo systemctl start hailo-fire-detection.service
```

4. Check service status:

```bash
sudo systemctl status hailo-fire-detection.service
```

5. View logs:

```bash
sudo journalctl -u hailo-fire-detection.service -f
```

## Integration with DeGirum Examples

This project is designed to work with the [DeGirum Hailo examples](https://github.com/DeGirum/hailo_examples). It uses DeGirum's API to interface with the Hailo 8 accelerator and leverages the optimized models provided in their examples repository.

The detection models are compatible with those provided in the DeGirum examples repository, which offers various pre-trained models specifically optimized for the Hailo 8 accelerator.

## License

MIT

## Contact

Email: bora.isik@gmail.com
