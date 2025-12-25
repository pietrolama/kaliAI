#!/usr/bin/env python3
"""Script per eseguire commit git del progetto kaliAI"""
import subprocess
import os
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Esegue un comando e restituisce l'output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    # Directory del progetto
    project_dir = Path(__file__).parent.absolute()
    print(f"Directory progetto: {project_dir}")
    
    # Verifica se git è inizializzato
    git_dir = project_dir / ".git"
    if not git_dir.exists():
        print("Inizializzazione repository git...")
        code, out, err = run_command("git init", cwd=project_dir)
        if code != 0:
            print(f"Errore inizializzazione: {err}")
            return 1
        print("Repository inizializzato")
        
        # Aggiungi remote se non esiste
        code, out, err = run_command("git remote get-url origin", cwd=project_dir)
        if code != 0:
            print("Aggiunta remote origin...")
            run_command("git remote add origin https://github.com/pietrolama/kaliAI.git", cwd=project_dir)
    
    # Aggiungi tutti i file
    print("\nAggiunta file al commit...")
    code, out, err = run_command("git add .", cwd=project_dir)
    if code != 0:
        print(f"Errore git add: {err}")
        return 1
    
    # Verifica lo stato
    print("\nStato repository:")
    code, out, err = run_command("git status --short", cwd=project_dir)
    if code == 0:
        if out.strip():
            print(out)
        else:
            print("Nessun file da committare")
            return 0
    
    # Esegui il commit
    print("\nEsecuzione commit...")
    code, out, err = run_command('git commit -m "Update kaliAI project files"', cwd=project_dir)
    if code != 0:
        print(f"Errore commit: {err}")
        if "nothing to commit" in err.lower():
            print("Nessuna modifica da committare")
            return 0
        return 1
    
    print("✓ Commit completato!")
    print(out)
    return 0

if __name__ == "__main__":
    sys.exit(main())

