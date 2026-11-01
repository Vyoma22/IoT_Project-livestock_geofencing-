# End-to-End Edge IoT Livestock Monitoring System

## Prerequisites
- **Python 3.x** (`pip install paho-mqtt influxdb-client shapely scikit-learn numpy`)
- **Docker Desktop**
- **Eclipse Mosquitto**

---

## Quick Start (Windows)

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/Vyoma22/IoT_Project-livestock_geofencing-.git](https://github.com/Vyoma22/IoT_Project-livestock_geofencing-.git)
   cd IoT_Project-livestock_geofencing-
   ```

2. **First-Time Database & Broker Setup:**
   - Start Docker Desktop.
   - Run initial containers: `docker compose up -d`
   - Access InfluxDB at `http://localhost:8086` to create your initial org (`farm_org`), bucket (`livestock_telemetry`), and copy your API Token into `processor.py`.
   - Set up Mosquitto user password: `mosquitto_passwd -c pwfile farm_admin`

3. **Start All System Components:**
   Double-click `start_all.bat` or run:
   ```cmd
   start_all.bat
   ```

4. **Stop All Services:**
   Double-click `stop_all.bat` or run:
   ```cmd
   stop_all.bat
   ```

---

## Universal Start/Stop Commands (Mac / Linux / Docker Users)

- **Start Infrastructure:**
  ```bash
  docker compose up -d
  mosquitto -v -c mosquitto.conf
  ```
- **Run Python Pipeline:**
  ```bash
  python simulator.py
  python processor.py
  ```
- **Stop Infrastructure:**
  ```bash
  docker compose down
  ```
