import requests
from Encryption import encrypt_file

url = 'http://127.0.0.1/send_firmware/'


def upload_firmware(file_path: str, car_id: int, ecu_id: int, firmware_version: str, description: str, key: bytes):
    enc_file = encrypt_file(file_path, key)

    firmware_data = {
        "car_id": car_id,
        "ecu_id": ecu_id,
        "firmware_version": firmware_version,
        "description": description,
        "file": enc_file
    }

    # Check if the car_id and ecu_id exist in their respective tables
    response = requests.post(url, json=firmware_data)
    if response.status_code == 200:
        return response.status_code, response.text
    elif response.status_code == 400:
        return "Invalid car_id or ecu_id"
    else:
        return "Error occurred while uploading firmware"

