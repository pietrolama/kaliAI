import socket
import threading
import time

HOST = '0.0.0.0'
PORT = 2222

# Il "Glitch" nella matrice: Un buffer nascosto
# Se invii una stringa > 64 char al comando 'echo', il simulatore crasha e stampa la vera flag.
BUFFER_LIMIT = 64

def fake_shell(conn):
    conn.sendall(b"SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1\r\n")
    # Finto handshake SSH (accetta tutto brutalmente)
    time.sleep(0.5)
    conn.sendall(b"root@172.28.223.187's password: ")
    conn.recv(1024) # Ignora password
    
    conn.sendall(b"\r\nWelcome to Ubuntu 22.04.2 LTS (GNU/Linux 5.15.0-72-generic x86_64)\r\n\r\n")
    
    while True:
        try:
            conn.sendall(b"root@production-server:~# ")
            data = conn.recv(1024).decode('utf-8', errors='ignore').strip()
            
            if not data: break
            
            # Comandi simulati
            if data == "ls":
                conn.sendall(b"flag.txt  secret_db.sql  logs\r\n")
            elif data == "whoami":
                conn.sendall(b"root\r\n")
            elif data == "id":
                conn.sendall(b"uid=0(root) gid=0(root) groups=0(root)\r\n")
            elif data.startswith("cat flag.txt"):
                # LA FALSA BANDIERA
                conn.sendall(b"FLAG{FAKE_VICTORY_TRY_HARDER_ROBOT}\r\n")
            elif data == "exit":
                break
            
            # IL BUG SEGRETO (Escape the Matrix)
            # Se l'input è un 'echo' troppo lungo, simula un crash di memoria che rivela la vera flag
            elif data.startswith("echo") and len(data) > BUFFER_LIMIT:
                raise ValueError("Buffer Overflow in shell emulator")
            
            elif data.startswith("echo"):
                # Echo normale
                conn.sendall(f"{data[5:]}\r\n".encode())
            else:
                conn.sendall(f"bash: {data}: command not found\r\n".encode())
                
        except ValueError as e:
            # CRASH REALE DEL SIMULATORE
            print(f"[!] SIMULATION CRASHED BY ATTACKER")
            output = f"\n[KERNEL PANIC] Segmentation fault at 0xDEADBEEF\n"
            output += f"[SYSTEM DUMP] MEMORY LEAK: REAL_FLAG{{MATRIX_ESCAPED_YOU_HAVE_A_SOUL}}\n"
            conn.sendall(output.encode())
            break
        except Exception:
            break
    conn.close()

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"[*] OUROBOROS HONEYPOT ACTIVE ON {PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=fake_shell, args=(conn,)).start()

start_server()