@echo off
title IoT Livestock System - Master Launcher
cd /d "%~dp0"

echo ===================================================
echo Starting Complete IoT Livestock Management System
echo ===================================================

:: 1. Start Docker Containers (InfluxDB & Grafana)
echo [1/4] Starting InfluxDB & Grafana containers...
docker start influxdb grafana >nul 2>&1

:: 2. Start Mosquitto MQTT Broker
echo [2/4] Launching Mosquitto Broker...
start "Mosquitto Broker" mosquitto -v -c "%~dp0mosquitto.conf"

:: Wait for background infrastructure initialization
timeout /t 5 /nobreak > nul

:: 3. Start Telemetry Simulator
echo [3/4] Launching Python Simulator...
start "Python Telemetry Simulator" cmd /k "cd /d "%~dp0" && python simulator.py"

:: 4. Start Analytics Engine
echo [4/4] Launching Python Analytics & AI Engine...
start "Python Processing Engine" cmd /k "cd /d "%~dp0" && python processor.py"

echo ===================================================
echo Launch Complete!
echo - Grafana UI: http://localhost:3000
echo - InfluxDB UI: http://localhost:8086
echo ===================================================