import json
import time
import numpy as np
from shapely.geometry import Point, Polygon
from sklearn.ensemble import IsolationForest
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point as InfluxPoint
from influxdb_client.client.write_api import SYNCHRONOUS

# --- INFLUXDB CONFIGURATION ---
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "nTflVZgVwG9uKTRdcOL5CPzk569SRQg80fuKe6D9sUyoea5oS_7d9kmJNper-oVowv3ZXeo2fHgFQxJdlLghdQ=="  
INFLUX_ORG = "iot_project"
INFLUX_BUCKET = "livestock_telemetry"

# --- MQTT BROKER CONFIGURATION ---
BROKER = "localhost"
PORT = 1883
USER = "farm_admin"
PASSWORD = "iotproject@12345"  

# --- SPATIAL GEOFENCING BOUNDARIES ---
# Define a simulated active hazard zone perimeter (North-East paddock section)
HAZARD_ZONE = Polygon([
    (43.9465, -78.8965),
    (43.9465, -78.8945),
    (43.9485, -78.8945),
    (43.9485, -78.8965)
])

# --- INITIALIZE AI ANOMALY DETECTION MODEL (Isolation Forest) ---
# Train on standard cattle motion profiles (Speed 0.1-2.5 m/s, balanced acceleration)
normal_training_data = np.random.uniform(low=[0.1, -0.5, -0.5, 9.5], high=[2.5, 0.5, 0.5, 10.1], size=(200, 4))
ai_model = IsolationForest(contamination=0.05, random_state=42)
ai_model.fit(normal_training_data)

# Initialize InfluxDB Client
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

def evaluate_geofence(lat, lon):
    collar_pos = Point(lat, lon)
    dist_to_hazard = collar_pos.distance(HAZARD_ZONE)
    
    if HAZARD_ZONE.contains(collar_pos):
        return 100, "Breach"  # 100% intensity cue inside hazard
    elif dist_to_hazard < 0.0005:  # ~50m warning buffer
        return 50, "Warning"  # 50% intensity warning cue
    else:
        return 0, "Safe"      # 0% intensity safe state

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ [Analytics Engine] Connected to MQTT Broker successfully.")
        # Subscribe to telemetry from all cattle collars
        client.subscribe("livestock/collars/+/telemetry", qos=1)
    else:
        print(f"❌ [Analytics Engine] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        collar_id = payload["collar_id"]
        lat = payload["latitude"]
        lon = payload["longitude"]
        speed = payload["speed"]
        accel_x = payload["accel_x"]
        accel_y = payload["accel_y"]
        accel_z = payload["accel_z"]
        battery = payload["battery_level"]

        # 1. Spatial Geofencing & Distance Evaluation
        cue_level, status = evaluate_geofence(lat, lon)

        # Dispatch warning command payload back to collar if in warning/breach zone
        if cue_level > 0:
            cmd_topic = f"livestock/collars/{collar_id}/cue_command"
            cmd_payload = json.dumps({"collar_id": collar_id, "cue_intensity": cue_level, "status": status})
            client.publish(cmd_topic, cmd_payload, qos=1)

        # 2. AI Behavioral Anomaly Detection
        features = np.array([[speed, accel_x, accel_y, accel_z]])
        prediction = ai_model.predict(features)[0]  # -1 = Anomaly, 1 = Normal
        is_anomaly = 1 if prediction == -1 else 0

        if is_anomaly:
            print(f"🚨 [AI ALERT] Behavior anomaly detected on {collar_id}! Speed: {speed} m/s")

        # 3. Time-Series Ingestion into InfluxDB
        point = InfluxPoint("collar_telemetry") \
            .tag("collar_id", collar_id) \
            .field("latitude", lat) \
            .field("longitude", lon) \
            .field("speed", speed) \
            .field("battery_level", battery) \
            .field("cue_intensity", cue_level) \
            .field("is_anomaly", is_anomaly)

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print(f"[{collar_id}] Processed -> Zone: {status} ({cue_level}%) | AI Anomaly: {bool(is_anomaly)}")

    except Exception as e:
        print(f"Error processing payload: {e}")

if __name__ == "__main__":
    print("Starting Livestock Analytics & AI Pipeline...")
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="analytics_engine")
    mqtt_client.username_pw_set(USER, PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(BROKER, PORT, keepalive=60)
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopping Analytics Engine.")