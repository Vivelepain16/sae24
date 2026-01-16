import paho.mqtt.client as mqtt
import json
import time
import os
import sys

# --- Configuration ---
FIFO_PATH = "sae24_signal_pipe"         # Named pipe for receiving amplitude data
MQTT_BROKER_HOST = "localhost"          # Broker address
MQTT_BROKER_PORT = 1883                 # Broker port
MQTT_TOPIC = "SAE24/E103/amplitudes"    # MQTT topic

NUM_BITS = 10
MAX_AMPLITUDE = 5000.0 

def amplitude_to_bits(amplitude):

    # Clamp amplitude to be between 0 and MAX_AMPLITUDE
    amplitude = max(0, min(amplitude, MAX_AMPLITUDE))
    
    # This simulates the Analog-to-Digital Converter (ADC)
    value_on_10_bits = int((amplitude / MAX_AMPLITUDE) * (2**NUM_BITS - 1))
   
    # This is the data that would be sent via FSK
    # ex: format(5, '0101') -> '0000000101'
    return format(value_on_10_bits, f'0{NUM_BITS}b')

def main():

    # Connect to MQTT broker
    client = mqtt.Client(client_id="simulateur_rpr")
    
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        client.loop_start()  # Start MQTT client loop in background
        print("RPr simulator connected to MQTT broker.")
    except Exception as e:
        print(f"MQTT connection error: {e}")
        sys.exit(1)

    print("RPe simulator ready. Waiting for sound signals...")
    
    try:
        # Open FIFO pipe for reading binary data
        with open(FIFO_PATH, 'rb') as fifo:
            print("Transmitter detected. Starting capture...")
            
            while True:
                # Read one line from the "propagation medium"
                line = fifo.readline()
                if not line: 
                    break  # End of data
                
                # Parse the 3 amplitudes from the "propagation medium"
                parts = line.decode('utf-8').strip().split(':')
                amplitudes = [float(p) for p in parts]
                print(f"\nReceived amplitudes: {amplitudes[0]:.2f}, {amplitudes[1]:.2f}, {amplitudes[2]:.2f}")

                # For each microphone (RPe), simulate conversion and publishing
                for i in range(3):
                    mic_id = i + 1
                    amplitude_val = amplitudes[i]
                    
                    # RPe logic: Convert amplitude to bits (FSK simulation)
                    amplitude_bits = amplitude_to_bits(amplitude_val)
                    
                    # RPr logic: Publish to MQTT
                    payload = {"mic_id": mic_id, "amplitude_bits": amplitude_bits}
                    client.publish(MQTT_TOPIC, json.dumps(payload))
                    print(f"  -> RPe{mic_id}: Amp -> Bits: {amplitude_bits}. Published to MQTT.")
    
    except KeyboardInterrupt: 
        print("\nManual stop of RPe/RPr simulator.")
        
    finally:
        # Cleanup MQTT connection
        client.loop_stop()
        client.disconnect()
        print("RPe/RPr simulator stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
