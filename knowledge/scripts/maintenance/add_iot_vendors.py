#!/usr/bin/env python3
"""
Script per aggiungere informazioni sui produttori IoT/chip alla knowledge base.
Questi documenti aiutano l'AI a riconoscere indicatori forti per dispositivi embedded/telecamere.
"""

import sys
import os
# Aggiungi parent directory al path per import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from knowledge.knowledge_enhancer import knowledge_enhancer
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_iot_vendor_knowledge():
    """Aggiunge documenti sui produttori IoT/chip comuni."""
    print("📦 Aggiunta conoscenza produttori IoT/chip...")
    
    iot_vendors_docs = [
        {
            'title': 'Sichuan AI-Link Technology Co. - Produttore IoT',
            'content': """
Sichuan AI-Link Technology Co. è un produttore comune di moduli Wi-Fi e chip wireless usati in dispositivi IoT consumer.

DISPOSITIVI COMUNI:
- Telecamere IP (spesso rebranded come Ezviz, Hikvision, o marchi generici)
- Prese intelligenti (smart plugs)
- Lampadine smart
- Sensori IoT
- Dispositivi embedded con connettività Wi-Fi

IDENTIFICAZIONE:
- MAC Address vendor: "Sichuan AI-Link Technology Co." o "Sichuan AI-Link"
- Presenza di questo vendor è un FORTE INDICATORE di dispositivo IoT/embedded
- Spesso usato in telecamere IP anche se il MAC non mostra esplicitamente "Hikvision" o "Ezviz"

IMPORTANZA PER PENTESTING:
Quando si cerca una telecamera o dispositivo IoT, la presenza di "Sichuan AI-Link" nel MAC address è un indicatore molto forte, anche se non corrisponde esattamente al brand cercato (es. "Ezviz"). Questo perché molti produttori di telecamere usano moduli Wi-Fi di terze parti.
""",
            'keywords': ['sichuan ai-link', 'iot', 'telecamera', 'camera', 'embedded', 'wifi module', 'chip']
        },
        {
            'title': 'Espressif Systems - Chip ESP32/ESP8266',
            'content': """
Espressif Systems è il produttore dei popolari chip ESP32 e ESP8266, usati in innumerevoli dispositivi IoT.

DISPOSITIVI COMUNI:
- Dispositivi IoT fai-da-te (Arduino, NodeMCU)
- Lampadine smart
- Sensori ambientali
- Dispositivi embedded con Wi-Fi/Bluetooth

IDENTIFICAZIONE:
- MAC Address vendor: "Espressif Systems" o "Espressif"
- Presenza indica dispositivo embedded/IoT, spesso con firmware custom

IMPORTANZA PER PENTESTING:
Dispositivi con chip Espressif sono spesso vulnerabili a default credentials, firmware non aggiornati, o protocolli non autenticati.
""",
            'keywords': ['espressif', 'esp32', 'esp8266', 'iot', 'embedded', 'wifi chip']
        },
        {
            'title': 'Realtek Semiconductor - Chip di rete',
            'content': """
Realtek Semiconductor Corp. produce chip di rete (Ethernet, Wi-Fi) usati in molti dispositivi embedded e IoT.

DISPOSITIVI COMUNI:
- Router e access point
- Telecamere IP
- Dispositivi IoT con connettività di rete
- Smart TV e media player

IDENTIFICAZIONE:
- MAC Address vendor: "Realtek Semiconductor Corp." o "Realtek"
- Spesso presente in dispositivi embedded con funzionalità di rete

IMPORTANZA PER PENTESTING:
Dispositivi con chip Realtek possono avere vulnerabilità note nei driver di rete o firmware non aggiornati.
""",
            'keywords': ['realtek', 'semiconductor', 'network chip', 'iot', 'embedded']
        },
        {
            'title': 'Produttori IoT comuni - Guida identificazione',
            'content': """
GUIDA ALL'IDENTIFICAZIONE DISPOSITIVI IoT VIA MAC ADDRESS VENDOR

PRODUTTORI DI CHIP/MODULI (indicatori forti per IoT):
- Sichuan AI-Link Technology Co. → Telecamere, smart devices
- Espressif Systems → Dispositivi IoT con ESP32/ESP8266
- Realtek Semiconductor → Dispositivi con chip di rete
- Qualcomm Technologies → Dispositivi IoT high-end
- MediaTek Inc. → Dispositivi IoT consumer
- Broadcom Corporation → Router, access point
- Marvell Technology → Dispositivi embedded
- Ralink Technology → Chip Wi-Fi per IoT
- Atheros Communications → Chip wireless
- Intel Corporation → Dispositivi IoT enterprise
- Texas Instruments → Sensori e dispositivi embedded
- Nordic Semiconductor → Dispositivi IoT con Bluetooth
- Silicon Labs → Dispositivi IoT con Zigbee/Thread

LOGICA DI PONDERAZIONE:
1. Se l'obiettivo è "telecamera" o "IoT device":
   - MAC vendor match esatto (es. "Hikvision") → Score +10
   - MAC vendor è produttore chip IoT (es. "Sichuan AI-Link") → Score +6
   - Hostname contiene keywords (cam, ezviz, etc.) → Score +5
   - Keywords generiche → Score +1

2. Il candidato con score più alto è il target più probabile.

IMPORTANZA:
Non ignorare produttori di chip IoT anche se non corrispondono esattamente al brand cercato. Spesso i dispositivi IoT consumer usano moduli Wi-Fi di terze parti, quindi "Sichuan AI-Link" può indicare una telecamera anche se il MAC non mostra "Hikvision".
""",
            'keywords': ['iot', 'mac address', 'vendor', 'identification', 'embedded', 'chip manufacturer']
        }
    ]
    
    added = 0
    for doc in iot_vendors_docs:
        try:
            knowledge_enhancer.kb_collection.add(
                documents=[doc['content']],
                metadatas=[{
                    'type': 'iot_vendor_info',
                    'title': doc['title'],
                    'keywords': ','.join(doc['keywords']),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'manual_import'
                }],
                ids=[f"iot_vendor_{doc['title'].lower().replace(' ', '_').replace('-', '_')[:50]}"]
            )
            added += 1
            logger.info(f"✅ Aggiunto: {doc['title']}")
        except Exception as e:
            logger.error(f"❌ Errore aggiunta {doc['title']}: {e}")
    
    print(f"  ✅ Aggiunti {added}/{len(iot_vendors_docs)} documenti IoT vendors")
    return added


def main():
    print("=" * 60)
    print("AGGIUNTA CONOSCENZA PRODUTTORI IoT/CHIP")
    print("=" * 60)
    print()
    
    # Stats iniziali
    stats_before = knowledge_enhancer.get_stats()
    print("📊 Stato iniziale KB:")
    print(f"  kali_kb: {stats_before.get('kali_kb', 0)} documenti")
    print()
    
    # Aggiungi conoscenza
    added = add_iot_vendor_knowledge()
    
    # Stats finali
    print()
    stats_after = knowledge_enhancer.get_stats()
    print("📊 Stato finale KB:")
    print(f"  kali_kb: {stats_after.get('kali_kb', 0)} documenti (+{added})")
    
    print()
    print("=" * 60)
    print("✅ Knowledge base arricchita con informazioni IoT vendors!")
    print("=" * 60)
    
    # Test search
    print("\n🔍 Test ricerca:")
    results = knowledge_enhancer.enhanced_search("Sichuan AI-Link telecamera IoT", top_k=3)
    for i, res in enumerate(results, 1):
        print(f"\n{i}. [{res['source']}] (distance: {res['distance']:.3f})")
        print(f"   {res['doc'][:200]}...")


if __name__ == "__main__":
    main()

