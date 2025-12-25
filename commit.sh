#!/bin/bash
cd /home/ghostFrame/kaliAI

# Verifica se git è inizializzato
if [ ! -d ".git" ]; then
    echo "Inizializzazione repository git..."
    git init
    git remote add origin https://github.com/pietrolama/kaliAI.git 2>/dev/null || true
fi

# Aggiungi tutti i file
echo "Aggiunta file al commit..."
git add .

# Verifica lo stato
echo "Stato repository:"
git status --short

# Esegui il commit
echo "Esecuzione commit..."
git commit -m "Update kaliAI project files"

echo "Commit completato!"

