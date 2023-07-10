from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import base64


def encrypt_file(file_path, key):
    # Read the contents of the input file
    with open(file_path, 'rb') as file:
        plaintext = file.read()

    # Generate a random 96-bit IV (Initialization Vector)
    iv = os.urandom(12)

    # Create the AES-GCM cipher
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    encryptor = cipher.encryptor()

    # Encrypt the plaintext
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    # Get the authentication tag
    tag = encryptor.tag
    cipherList = [iv, ciphertext, tag]
    encrypted_data = b''.join(cipherList)
    # Convert the encrypted file to base64
    base64_data = base64.b64encode(encrypted_data).decode()
    return base64_data


# Example usage
key = "2b7e151628aed2a6"  # Replace with your own 16-byte key
