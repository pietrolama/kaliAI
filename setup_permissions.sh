#!/usr/bin/env bash

set -euo pipefail

echo "[*] Configurazione permessi tcpdump in corso..."

if [[ $EUID -ne 0 ]]; then
    echo "Errore: eseguire questo script con privilegi di root (es. sudo)." >&2
    exit 1
fi

TCPDUMP_PATH=$(which tcpdump || true)

if [[ -z "$TCPDUMP_PATH" ]]; then
    echo "Errore: tcpdump non trovato nel PATH. Installarlo prima di procedere." >&2
    exit 1
fi

echo "[*] Tcpdump trovato: $TCPDUMP_PATH"

echo "[*] Assegno capabilities cap_net_raw,cap_net_admin..."
setcap cap_net_raw,cap_net_admin+eip "$TCPDUMP_PATH"

echo "[*] Verifico capabilities..."
CAP_OUTPUT=$(getcap "$TCPDUMP_PATH" || true)

# Accetta entrambe le combinazioni d'ordine e sia +eip che =eip
if echo "$CAP_OUTPUT" | grep -E "cap_net_raw.*cap_net_admin.*[=+](e|ep|eip)" >/dev/null \
   || echo "$CAP_OUTPUT" | grep -E "cap_net_admin.*cap_net_raw.*[=+](e|ep|eip)" >/dev/null; then
    echo "[✓] Capabilities applicate correttamente: $CAP_OUTPUT"
else
    echo "[!] Attenzione: le capabilities non sembrano applicate correttamente."
    echo "Output getcap: $CAP_OUTPUT"
    exit 1
fi

echo "[✓] Configurazione completata."

