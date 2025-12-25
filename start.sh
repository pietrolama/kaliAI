#!/bin/bash

echo "====== AVVIO KALI AI ======"
echo "[*] Ambiente: $(pwd)"

# Verifica esistenza .env
if [ ! -f .env ]; then
    echo "[!] ERRORE: File .env non trovato!"
    echo "[!] Copia .env.example in .env e configura le tue API keys"
    exit 1
fi

echo "[*] Controllo processi esistenti sulla porta 5000..."
lsof -ti:5000 | xargs kill -9 2>/dev/null
echo "[*] Porta liberata"

echo "[*] Attivazione ambiente virtuale..."
source venv/bin/activate

echo "[*] Caricamento variabili ambiente da .env..."
export $(cat .env | grep -v '^#' | xargs)

echo "[*] Configurazione:"
echo "    - Modello: ${MODEL_NAME}"
echo "    - Base URL: ${OPENAI_BASE_URL}"
echo "    - Docker Sandbox: ${USE_DOCKER_SANDBOX}"

echo "[*] Avvio Flask (CTRL+C per uscire)"
python run.py

echo "====== TERMINATO ======"
