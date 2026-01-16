import paho.mqtt.client as mqtt
import json
import math
import time
import mysql.connector
from datetime import datetime
import sys

# --- Configuration ---
# Database connection parameters
DB_CONFIG = {
    'unix_socket': '/opt/lampp/var/mysql/mysql.sock', 
    'user': 'sae24', 
    'password': 'leo', 
    'database': 'sae24'
}

# MQTT broker settings
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC_TO_SUBSCRIBE = "SAE24/E103/amplitudes"

# Microphone positions (meters)
MICROS = { 
    1: {"pos": (0.25, 0.25)}, 
    2: {"pos": (0.25, 7.75)}, 
    3: {"pos": (7.75, 7.75)} 
}

# Physical constants and grid parameters
K_FACTOR = 1000.0           # Sound propagation constant for amplitude calculation
GRID_SIZE = 16              # Number of grid cells per side
CASE_SIZE_M = 0.5
NUM_BITS = 10
MAX_AMPLITUDE = 5000.0

def bits_to_amplitude(bits_string):

    value_on_10_bits = int(bits_string, 2)  # Convert binary to integer
    return (value_on_10_bits / (2**NUM_BITS - 1)) * MAX_AMPLITUDE

# --- Processing Functions ---
amplitude_map = {}  # Global cache for precomputed amplitude values

def precompute_amplitude_map():

    print("Precomputing amplitude map...")
    
    for i in range(GRID_SIZE):
        for j in range(GRID_SIZE):
            # Calculate center coordinates of each grid cell
            case_x = i * CASE_SIZE_M + (CASE_SIZE_M / 2)
            case_y = j * CASE_SIZE_M + (CASE_SIZE_M / 2)
            
            # Calculate expected amplitude at each microphone for this position
            amplitudes_for_case = []
            for mic_id in sorted(MICROS.keys()):
                mic_pos = MICROS[mic_id]["pos"]
                # Calculate distance from sound source to microphone
                dist = math.sqrt((case_x - mic_pos[0])**2 + (case_y - mic_pos[1])**2)
                # Apply inverse square law for sound amplitude
                amp = K_FACTOR / (dist**2) if dist > 0.1 else K_FACTOR / (0.1**2)
                amplitudes_for_case.append(amp)
            
            # Store in lookup table
            amplitude_map[(case_x, case_y)] = amplitudes_for_case
    
    print(f"Amplitude map precomputed with {len(amplitude_map)} points.")

def find_closest_position(received_amplitudes):

    # Convert received amplitudes to ordered list
    amps = [received_amplitudes.get(1,0), received_amplitudes.get(2,0), received_amplitudes.get(3,0)]
    
    best_match_pos, min_error = None, float('inf')
    
    # Compare with each precomputed position
    for pos, map_amplitudes in amplitude_map.items():
        # Calculate sum of squared differences
        error = sum([(map_amp - rec_amp)**2 for map_amp, rec_amp in zip(map_amplitudes, amps)])
        
        # Keep track of best match
        if error < min_error:
            min_error, best_match_pos = error, pos
    
    return best_match_pos

# --- NEW CRUCIAL FUNCTION ---
def snap_to_grid(position):

    if not position:
        return None
    
    # Find the index of the nearest grid cell
    # Ex: x=4.3 -> i = 4.3 / 0.5 = 8.6 -> round(8.6) = 9
    i = round(position[0] / CASE_SIZE_M - 0.5)
    j = round(position[1] / CASE_SIZE_M - 0.5)

    # Recalculate coordinates of the center of this cell
    snapped_x = i * CASE_SIZE_M + (CASE_SIZE_M / 2)
    snapped_y = j * CASE_SIZE_M + (CASE_SIZE_M / 2)

    return (snapped_x, snapped_y)

def save_position_to_db(position, db_connection):

    if not position: 
        return
    
    cursor = db_connection.cursor()
    sql_query = "INSERT INTO positions (pos_x, pos_y, timestamp) VALUES (%s, %s, %s)"
    
    try:
        cursor.execute(sql_query, (position[0], position[1], datetime.now()))
        db_connection.commit()
        print(f"  -> Position ({position[0]:.2f}, {position[1]:.2f}) saved to database.")
    except mysql.connector.Error as err:
        print(f"Database insertion error: {err}")
    finally:
        cursor.close()

# --- MQTT Callbacks ---
received_data_buffer = {}  # Buffer to collect messages from microphones

def on_connect(client, userdata, flags, rc):

    # Callback for when MQTT client connects to broker
    if rc == 0: 
        client.subscribe(MQTT_TOPIC_TO_SUBSCRIBE)
        print(f"Connected to MQTT broker and subscribed to {MQTT_TOPIC_TO_SUBSCRIBE}")
    else: 
        print(f"MQTT connection failed, return code: {rc}")

def on_message(client, userdata, msg):

    # Callback for when an MQTT message is received
    # Processes amplitude data and estimates position when all microphones have reported

    db_connection = userdata['db_connection']
    
    try:
        # Parse incoming JSON message
        data = json.loads(msg.payload.decode())
        amplitude = bits_to_amplitude(data["amplitude_bits"])
        
        # Group messages by timestamp
        batch_key = int(time.time())  # Group by second
        
        if batch_key not in received_data_buffer: 
            received_data_buffer[batch_key] = {}
        
        received_data_buffer[batch_key][data["mic_id"]] = amplitude
        
        # Process when we have data from all 3 microphones
        if len(received_data_buffer[batch_key]) == 3:
            print(f"\n--- Batch of 3 MQTT messages received ---")
            
            # Raw position estimation
            estimated_pos = find_closest_position(received_data_buffer[batch_key])
            print(f"  Raw estimated position: {estimated_pos}")
            
            # Grid magnetism
            snapped_pos = snap_to_grid(estimated_pos)
            print(f"==> Grid-aligned position: {snapped_pos}")
            
            # Save corrected position to database
            save_position_to_db(snapped_pos, db_connection)
            
            # Clean up processed batch
            del received_data_buffer[batch_key]
            
    except Exception as e:
        print(f"Message processing error: {e}")

def main():

    # Initialize system and start MQTT processing loop

    # Precompute amplitude lookup table
    precompute_amplitude_map()
    
    # Connect to database
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        print("Connected to MySQL database.")
    except mysql.connector.Error as err:
        print(f"DATABASE CONNECTION ERROR: {err}")
        sys.exit(1)
    
    # Setup MQTT client
    client = mqtt.Client(client_id="processeur_mqtt_sae24")
    client.user_data_set({'db_connection': db_connection}) 
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect to MQTT broker and start processing
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        print("Starting MQTT processing loop...")
        client.loop_forever()  # Blocking call - runs until interrupted
        
    except Exception as e:
        print(f"MQTT BROKER CONNECTION ERROR: {e}")
        
    finally:
        # Cleanup
        db_connection.close()
        print("\nDatabase connection closed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
