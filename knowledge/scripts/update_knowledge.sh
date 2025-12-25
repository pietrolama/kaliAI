#!/bin/bash
# Script per aggiornamento automatico knowledge base
# Eseguire settimanalmente per mantenere KB aggiornata

echo "🧠 AGGIORNAMENTO KNOWLEDGE BASE KALIAI"
echo "======================================"
echo ""

cd /home/ghostframe/HACK/kaliAI
source venv/bin/activate

echo "📊 Stato attuale..."
python -c "
from knowledge import knowledge_enhancer
stats = knowledge_enhancer.get_stats()
print(f'Total: {stats[\"total\"]} documenti')
for k, v in stats.items():
    if k != 'total':
        print(f'  {k}: {v}')
"

echo ""
echo "🌐 Download aggiornamenti da tutte le fonti..."
echo ""

# 1. Knowledge Fetcher: CVE recenti + RSS feeds (veloce)
echo "1️⃣  Knowledge Fetcher (CISA KEV, NVD, RSS)..."
python knowledge/knowledge_fetcher.py "$@"

echo ""
echo "2️⃣  Exploit Hunter (GitHub, Exploit-DB, Packet Storm, Google P0)..."
# 2. Exploit Hunter: GitHub, Exploit-DB, etc (medio)
python knowledge/exploit_hunter.py

echo ""
echo "📊 Stato finale..."
python -c "
from knowledge import knowledge_enhancer
stats = knowledge_enhancer.get_stats()
print(f'Total: {stats[\"total\"]} documenti')
for k, v in stats.items():
    if k != 'total':
        print(f'  {k}: {v}')
"

echo ""
echo "✅ Aggiornamento completato!"
echo ""
echo "Fonti aggiornate:"
echo "  • CISA KEV (CVE sfruttati)"
echo "  • NVD Recent CVEs"
echo "  • RSS feeds (US-CERT, Packet Storm, BleepingComputer, etc)"
echo "  • GitHub PoC"
echo "  • Exploit-DB"
echo "  • Google Project Zero"
echo "  • Reddit r/ExploitDev"
echo ""
echo "Per aggiornamento completo (include MITRE ATT&CK):"
echo "  ./knowledge/scripts/update_knowledge.sh --full"

