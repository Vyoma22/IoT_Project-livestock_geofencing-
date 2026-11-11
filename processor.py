import os
import json
import time
from dotenv import load_dotenv
from shapely.geometry import Point, Polygon
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point as InfluxPoint, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Load variables from .env
load_dotenv()

# --- INFLUXDB CONFIGURATION ---
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "iot_project")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "livestock_telemetry")

if not INFLUX_TOKEN:
    raise ValueError("❌ Error: INFLUX_TOKEN is not defined in your .env file!")

# --- MQTT BROKER CONFIGURATION ---
BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", 1883))
USER = os.getenv("MQTT_USER", "farm_admin")
PASSWORD = os.getenv("MQTT_PASS")

if not PASSWORD:
    raise ValueError("❌ MQTT_PASS is missing from .env file.")

# --- DYNAMIC SPATIAL GEOFENCING BOUNDARIES ---
# Default fallback zone
HAZARD_ZONE = Polygon([
    (43.9465, -78.8965),
    (43.9465, -78.8945),
    (43.9485, -78.8945),
    (43.9485, -78.8965)
])

# Initialize InfluxDB Client
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def evaluate_geofence(lat, lon):
    global HAZARD_ZONE
    collar_pos = Point(lat, lon)
    dist_to_hazard = collar_pos.distance(HAZARD_ZONE)

    if HAZARD_ZONE.contains(collar_pos):
        return 100, "Breach"
    elif dist_to_hazard < 0.00003:  # ~3-meter warning buffer
        return 50, "Warning"
    else:
        return 0, "Safe"


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ [Analytics Engine] Connected to MQTT Broker.")
        client.subscribe("livestock/collars/+/telemetry", qos=1)
        client.subscribe("livestock/config/hazard_zone", qos=1)
    else:
        print(f"❌ [Analytics Engine] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    global HAZARD_ZONE
    try:
        # Handle Dynamic Geofence Configuration from Mobile App
        if msg.topic == "livestock/config/hazard_zone":
            config = json.loads(msg.payload.decode())
            coords = [(pt["lat"], pt["lon"]) for pt in config["coordinates"]]
            HAZARD_ZONE = Polygon(coords)
            print(f"🗺️ [Analytics Engine] HAZARD_ZONE updated dynamically with {len(coords)} vertices.")
            return

        # Handle Telemetry Processing
        payload = json.loads(msg.payload.decode())
        collar_id = payload["collar_id"]
        raw_ts = payload.get("timestamp", time.time())
        ts_str = payload.get("timestamp_str", time.strftime("%Y-%m-%dT%H:%M:%S"))
        lat = payload["latitude"]
        lon = payload["longitude"]
        speed = payload["speed"]
        battery = payload["battery_level"]

        # 1. Geofence Evaluation & Command Dispatch
        cue_level, status = evaluate_geofence(lat, lon)
        cmd_topic = f"livestock/collars/{collar_id}/cue_command"
        cmd_payload = json.dumps({"collar_id": collar_id, "cue_intensity": cue_level, "status": status})
        client.publish(cmd_topic, cmd_payload, qos=1)

        # 2. Store in InfluxDB with Device Timestamp
        timestamp_ns = int(raw_ts * 1e9)
        point = (
            InfluxPoint("collar_telemetry")
            .tag("collar_id", str(collar_id))
            .field("latitude", float(lat))
            .field("longitude", float(lon))
            .field("speed", float(speed))
            .field("battery_level", int(battery))
            .field("cue_intensity", int(cue_level))
            .field("device_time_iso", str(ts_str))
            .time(timestamp_ns, WritePrecision.NS)
        )

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

        # 3. Formatted Terminal Output
        print(
            f"[{ts_str}] [{collar_id}] Lat: {lat:.5f}, Lon: {lon:.5f} | "
            f"Speed: {float(speed):.2f} m/s | Battery: {float(battery):.1f}% | "
            f"Zone: {status} (Cue: {cue_level}%)"
        )

    except Exception as e:
        print(f"Error processing message: {e}")


if __name__ == "__main__":
    print("Starting Livestock Analytics Engine...")
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="analytics_engine")
    mqtt_client.username_pw_set(USER, PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(BROKER, PORT, keepalive=60)
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping Analytics Engine.")