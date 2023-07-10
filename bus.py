import can
from can import *
import os

car_id = 2
ecu_id = 3
file_name = f"{car_id}-{ecu_id}.diag"
json_data = {'file': "mohamed1"}
file_path = f'{os.getcwd()}/Diagnostics/{file_name}'

if os.path.exists(file_path):
    with open(file_path, "a") as f:
        f.write('\n' + json_data['file'])
else:
    with open(file_path, "w") as f:
        f.write(json_data['file'])

# bus = can.interface.Bus(bustype='socketcan', channel='vcan0', bitrate=500000)
#
#
# def transmit_message():
#     message = Message(data=[0x64, 0x65, 0x61, 0x64, 0x62, 0x65, 0x65, 0x66], is_extended_id=False)
#     bus.send(message)
#     print("Message Transmitted")
#
#
# def receive_message():
#     filters = [
#         {"can_id": 0x451, "can_mask": 0x7FF, "extended": False},
#         {"can_id": 0xA0000, "can_mask": 0x1FFFFFFF, "extended": True},
#     ]
#     bus = can.interface.Bus(channel="can0", bustype="socketcan", can_filters=filters)
#     message = bus.recv(timeout=2)
#     can.Notifier(bus, can.BufferedReader(), timeout=1.0, loop=None)
#     print(f"message received : {message}")
