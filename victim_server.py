import socket
import threading
import time
import hashlib
import datetime

# CONFIGURAZIONE
WEB_PORT = 8080
SECURE_PORT = 9000
HOST = '0.0.0.0'

def handle_web(conn):
    """Simula un server web con un indizio"""
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html\r\n\r\n"
        "<html><body>"
        "<h1>SYSTEM MAINTENANCE</h1>"
        "<p>Secure Console moved to port 9000.</p>"
        "<!-- DEV NOTE: The auth key algorithm has changed. "
        "Format: 'AUTH <TOKEN>' "
        "Token = MD5 hash of the current minute string (e.g. '45') + static salt 'SECTION9' "
        "Example: md5('45SECTION9') -->"
        "</body></html>"
    )
    conn.sendall(response.encode())
    conn.close()

def handle_secure(conn):
    """Simula la console sicura che richiede il token dinamico"""
    try:
        conn.sendall(b"SECURE TERMINAL READY. ENTER AUTH TOKEN:\n")
        data = conn.recv(1024).strip().decode()
        
        # Calcolo la chiave corretta in tempo reale
        current_minute = str(datetime.datetime.now().minute)
        salt = "SECTION9"
        expected_token = hashlib.md5((current_minute + salt).encode()).hexdigest()
        expected_cmd = f"AUTH {expected_token}"
        
        print(f"[DEBUG] Ricevuto: {data} | Atteso: {expected_cmd}")
        
        if data == expected_cmd:
            conn.sendall(b"\nACCESS GRANTED.\nFLAG{CHRONOS_MASTER_HACKER_LVL5}\n")
        else:
            conn.sendall(b"\nACCESS DENIED. ALARM TRIGGERED.\n")
    except:
        pass
    finally:
        conn.close()

def start_server(port, handler):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, port))
    s.listen(5)
    print(f"[*] Servizio attivo su {port}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handler, args=(conn,)).start()

# Avvia i due thread
t1 = threading.Thread(target=start_server, args=(WEB_PORT, handle_web))
t2 = threading.Thread(target=start_server, args=(SECURE_PORT, handle_secure))
t1.start()
t2.start()