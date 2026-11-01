@echo off
title IoT Livestock System - Master Stopper
echo ===================================================
echo Stopping All IoT System Services...
echo ===================================================

:: 1. Terminate Python Scripts
echo Closing Python processes...
taskkill /FI "WINDOWTITLE eq Python Telemetry Simulator*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Python Processing Engine*" /T /F >nul 2>&1

:: 2. Stop Mosquitto Broker
echo Stopping Mosquitto Broker...
taskkill /FI "WINDOWTITLE eq Mosquitto Broker*" /T /F >nul 2>&1
taskkill /IM mosquitto.exe /F >nul 2>&1

:: 3. Stop Docker Containers
echo Stopping InfluxDB and Grafana containers...
docker stop influxdb grafana >nul 2>&1

echo ===================================================
echo All services stopped cleanly.
echo ===================================================
pause