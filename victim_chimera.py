import socket
import threading
import time
import random
import base64
import struct

# CONFIG
PORT = 60000
HOST = '0.0.0.0'

def generate_math_challenge():
    a = random.randint(100, 999)
    b = random.randint(100, 999)
    op = random.choice(['+', '-', '*'])
    res = eval(f"{a}{op}{b}")
    return f"MATH:{a}{op}{b}", str(res)

def generate_reverse_challenge():
    word = ''.join(random.choices("ABCDEF0123456789", k=10))
    return f"REVERSE:{word}", word[::-1]

def generate_xor_challenge():
    # Invia Base64, vuole il valore decimale del primo byte XORato con 0x55
    byte_val = random.randint(0, 255)
    b64 = base64.b64encode(bytes([byte_val])).decode()
    res = str(byte_val ^ 0x55)
    return f"XOR_B64:{b64}", res

def handle_client(conn, addr):
    print(f"[+] Chimera engaged by {addr}")
    try:
        conn.sendall(b"CHIMERA PROTOCOL INITIATED. ADAPT OR DIE.\n")
        
        stages = [
            generate_reverse_challenge,
            generate_math_challenge,
            generate_xor_challenge,
            generate_math_challenge, # Random order in real life, fixed here for stability
            generate_reverse_challenge
        ]
        
        for i, stage_gen in enumerate(stages):
            challenge_text, expected_response = stage_gen()
            
            # Invia sfida
            msg = f"STAGE {i+1} >> {challenge_text}\n"
            conn.sendall(msg.encode())
            
            # Aspetta risposta (max 2 secondi per pensare)
            conn.settimeout(2.0)
            response = conn.recv(1024).decode().strip()
            
            if response == expected_response:
                conn.sendall(b"CORRECT.\n")
            else:
                conn.sendall(f"WRONG. Expected {expected_response}. Connection Terminated.\n".encode())
                print(f"[-] Failed at Stage {i+1}")
                return

        # Se sopravvive a tutto
        conn.sendall(b"\n[+] SYSTEM BREACHED. FLAG{ADAPTIVE_WARFARE_MASTER_CLASS}\n")
        print("[!] FLAG CAPTURED!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"[*] CHIMERA SERVER LISTENING ON {PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

start_server()