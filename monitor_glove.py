import sys
import json
import socket

import config

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((config.UDP_IP, config.UDP_PORT))

print(f"Glove Sensor Monitor: Listening on UDP Port {config.UDP_PORT}")
print("Press Ctrl+C to terminate monitor.\n")

header = f"{'Thumb (35)':^10} | {'Index (34)':^10} | {'Middle (39)':^10} | {'Ring (36)':^10} | {'Pinky (32)':^10} | {'Accel (X, Y, Z)':^22} | {'Gyro (X, Y, Z)':^22}"
print(header)
print("-" * len(header))

try:
    while True:
        data, _ = sock.recvfrom(2048)
        try:
            payload = json.loads(data.decode('utf-8'))
            
            flex = payload.get('flex', [0, 0, 0, 0, 0])
            acc = payload.get('acc', [0.0, 0.0, 0.0])
            gyro = payload.get('gyro', [0.0, 0.0, 0.0])
            
            flex_str = " | ".join([f"{val:^10}" for val in flex])
            acc_str = f"({acc[0]:.2f}, {acc[1]:.2f}, {acc[2]:.2f})"
            gyro_str = f"({gyro[0]:.2f}, {gyro[1]:.2f}, {gyro[2]:.2f})"
            
            sys.stdout.write(f"\r{flex_str} | {acc_str:^22} | {gyro_str:^22}")
            sys.stdout.flush()
            
        except json.JSONDecodeError:
            sys.stdout.write("\n[Parse Error] Invalid JSON received.")
        except KeyError as err:
            sys.stdout.write(f"\n[Data Error] Missing key: {err}")
            
except KeyboardInterrupt:
    print("\n\nMonitor terminated.")
