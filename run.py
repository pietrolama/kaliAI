#!/usr/bin/env python3
"""
Entry point principale per KaliAI
Avvia il backend Flask server
"""

import sys
import os

# Aggiungi root al path
sys.path.insert(0, os.path.dirname(__file__))

# Import app dal backend
from backend.app import app

if __name__ == "__main__":
    # Configurazione dal environment
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    # Avvia server
    # use_reloader=False: CRITICAL - prevents restart when agent writes Python files
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False
    )

