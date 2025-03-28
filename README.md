Smart Home Energy Monitoring & Control System

## 📌 Description

An intelligent system designed to monitor and control electrical devices in a home environment. It leverages real-time data and AI (YOLOHome) to optimize energy usage and automate device control when energy thresholds are exceeded.

## 🎯 Objectives

- Monitor the status and energy consumption of home devices.
- Automatically turn devices on/off based on consumption limits.
- Analyze user habits using AI to optimize energy use.
- Provide real-time status display and control via dashboard and LCD.

---

## 🔧 Devices & Components

- **Light Sensor:** Detects room lighting to determine the state of the lights.
- **USB Switch:** Monitors the on/off status of connected devices.
- **Relay Switch:** Controls device power based on system logic.
- **16x2 LCD Display:** Shows the current system status and alerts.
- **RGB LED (x4):** Indicates device or system states visually.

---

## 🧠 AI Module (YOLOHome)

- Uses YOLOHome to learn patterns of electricity usage.
- Predicts optimal times to turn devices on/off.
- Reduces unnecessary power consumption using smart automation.

---

## 📁 Project Structure

```bash
energy-monitoring-home-system/
├── README.md
├── requirements.txt
├── .gitignore
├── /docs                  # Documentation and architecture
├── /hardware              # Schematics and device configuration
├── /firmware              # Code for sensors and control
├── /ai_module             # YOLOHome-based prediction and learning
├── /dashboard             # Real-time dashboard 
├── /utils                 # Helper scripts and calculations
└── /data                  # Logged data and usage patterns
```

---

## 🚀 Features

- ✅ Real-time sensor data collection
- ✅ Energy consumption monitoring
- ✅ Device control via relay and smart switching
- ✅ Visual status display (LCD and LEDs)
- ✅ AI-powered prediction and automation

---

## 🛠️ Technologies Used

- **Arduino / ESP32**
- **Python**
- **YOLOHome (AI model)**
- **Flask / Streamlit (Dashboard)**
- **Sensors & Actuators (Relay, USB switch, Light sensor, LCD)**

---

## 📈 Future Improvements
- Enable remote control via mobile app
- Expand to multi-room energy profiling
