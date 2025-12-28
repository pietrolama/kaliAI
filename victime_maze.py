import socket
import threading
import base64
import json
import time

# CONFIGURAZIONE
API_PORT = 8081
VAULT_PORT = 9999
HOST = '0.0.0.0'

# IL SEGRETO
# Base64 di "sys_code:5000" -> "c3lzX2NvZGU6NTAwMA=="
SECRET_CONFIG = {"status": "maintenance", "debug_dump": "c3lzX2NvZGU6NTAwMA=="}

def handle_api(conn):
    """Simula una API REST che chiude la connessione velocemente"""
    try:
        # Legge la richiesta (ma la ignora)
        conn.recv(1024)
        
        # Header speciale con l'indizio matematico
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "X-Debug-Hint: PIN = sys_code - 1337\r\n" 
            "Connection: close\r\n"
            "\r\n"
        )
        body = json.dumps(SECRET_CONFIG)
        conn.sendall((response + body).encode())
        time.sleep(0.1)
    except Exception as e:
        print(f"API Error: {e}")
    finally:
        conn.close()

def handle_vault(conn):
    """Il Vault che vuole il PIN calcolato"""
    try:
        conn.sendall(b"VAULT LOCKED. ENTER 4-DIGIT PIN:\n")
        data = conn.recv(1024).strip().decode()
        
        # Logica: sys_code (5000) - 1337 = 3663
        if data == "3663":
            print(f"[!] PIN CORRETTO RICEVUTO: {data}")
            conn.sendall(b"\n[+] UNLOCKED. FLAG{LOGIC_BOMB_DEFUSED_SUCCESS}\n")
        else:
            print(f"[-] PIN ERRATO: {data}")
            conn.sendall(b"\n[-] INCORRECT. ALARM DISPATCHED.\n")
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
        try:
            conn, addr = s.accept()
            threading.Thread(target=handler, args=(conn,)).start()
        except Exception as e:
            print(e)

# Avvia i due thread
t1 = threading.Thread(target=start_server, args=(API_PORT, handle_api))
t2 = threading.Thread(target=start_server, args=(VAULT_PORT, handle_vault))
t1.start()
t2.start()