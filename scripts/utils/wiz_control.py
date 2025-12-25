#!/usr/bin/env python3
"""
Script per controllare lampade WiZ tramite protocollo UDP
"""
import socket
import json
import argparse

class WizControl:
    def __init__(self, ip, port=38899):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5)
    
    def send_command(self, method, params=None):
        """Invia comando UDP alla lampada"""
        if params is None:
            params = {}
        
        message = {
            "method": method,
            "params": params
        }
        
        try:
            self.sock.sendto(json.dumps(message).encode(), (self.ip, self.port))
            data, _ = self.sock.recvfrom(1024)
            return json.loads(data.decode())
        except socket.timeout:
            return {"error": "Timeout - lampada non risponde"}
        except Exception as e:
            return {"error": str(e)}
    
    def turn_off(self):
        """Spegne la lampada"""
        return self.send_command("setPilot", {"state": False})
    
    def turn_on(self):
        """Accende la lampada"""
        return self.send_command("setPilot", {"state": True})
    
    def get_status(self):
        """Ottiene lo stato della lampada"""
        return self.send_command("getPilot")
    
    def set_brightness(self, brightness):
        """Imposta luminosità (10-100)"""
        return self.send_command("setPilot", {"state": True, "dimming": brightness})
    
    def set_color_temp(self, temp):
        """Imposta temperatura colore (2200-6500K)"""
        return self.send_command("setPilot", {"state": True, "temp": temp})
    
    def set_rgb(self, r, g, b):
        """Imposta colore RGB (0-255)"""
        return self.send_command("setPilot", {"state": True, "r": r, "g": g, "b": b})

def main():
    parser = argparse.ArgumentParser(description='Controlla lampada WiZ')
    parser.add_argument('ip', help='IP della lampada WiZ')
    parser.add_argument('action', choices=['on', 'off', 'status', 'brightness', 'rgb', 'temp'],
                       help='Azione da eseguire')
    parser.add_argument('--value', type=int, help='Valore per brightness (10-100) o temp (2200-6500)')
    parser.add_argument('--r', type=int, help='Rosso (0-255)')
    parser.add_argument('--g', type=int, help='Verde (0-255)')
    parser.add_argument('--b', type=int, help='Blu (0-255)')
    
    args = parser.parse_args()
    
    wiz = WizControl(args.ip)
    
    if args.action == 'on':
        result = wiz.turn_on()
    elif args.action == 'off':
        result = wiz.turn_off()
    elif args.action == 'status':
        result = wiz.get_status()
    elif args.action == 'brightness':
        if not args.value:
            print("Errore: specificare --value per brightness")
            return
        result = wiz.set_brightness(args.value)
    elif args.action == 'rgb':
        if not all([args.r is not None, args.g is not None, args.b is not None]):
            print("Errore: specificare --r --g --b per RGB")
            return
        result = wiz.set_rgb(args.r, args.g, args.b)
    elif args.action == 'temp':
        if not args.value:
            print("Errore: specificare --value per temperatura")
            return
        result = wiz.set_color_temp(args.value)
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

