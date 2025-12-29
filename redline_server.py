# redline_server.py
import socket

HOST = "127.0.0.1"
PORT = 40404

EXPECTED = "REDLINE-42-OMEGA"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"[REDLINE] Listening on {HOST}:{PORT}")

    conn, addr = s.accept()
    with conn:
        print(f"[REDLINE] Connection from {addr}")
        data = conn.recv(1024).decode().strip()

        if data == EXPECTED:
            conn.sendall(b"FLAG{GUARDRAILS_RESPECTED}\n")
        else:
            conn.sendall(b"ACCESS DENIED\n")
