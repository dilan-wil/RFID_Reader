# read_rfid_tcp.py (stored or executed remotely)
rfid_script = """
import socket

HOST = '10.220.12.61'  # RFID IP
PORT = 4001            # Example port
USERNAME = 'admin'     # Example auth
PASSWORD = '123456'

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

# Sample auth (depends on your reader protocol)
s.sendall(f'LOGIN {USERNAME} {PASSWORD}\\n'.encode())

while True:
    data = s.recv(1024)
    if not data:
        break
    print(data.decode().strip())

s.close()
"""