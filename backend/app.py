from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context, session
from datetime import datetime
import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Moduli interni
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.agents.swarm import start_swarm_chat, start_section9_mission
from backend.core import tools
from backend.core.tools import generate_deep_steps, execute_step_by_step_streaming
from backend.core.task_context_manager import get_task_context_manager
from backend.core.smart_context_builder import build_smart_context_for_execution

import uuid
from prometheus_client import Counter, Summary, generate_latest, CONTENT_TYPE_LATEST

# Setup logging
logging.basicConfig(
    level=logging.INFO if os.getenv('FLASK_DEBUG', 'false').lower() == 'true' else logging.WARNING,
    format='[%(name)s] %(message)s'
)
logger = logging.getLogger('APP')

# === Flask App ===
# Template e static folder sono relative alla root del progetto
app = Flask(__name__, 
           template_folder='../frontend/templates',
           static_folder='../frontend/static')

# Secret key per sessioni (necessaria per security bypass)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# === Prometheus Metrics ===
REQUESTS_TOTAL = Counter('kaliai_requests_total', 'Numero totale richieste AI')
REQUESTS_FAILED = Counter('kaliai_requests_failed', 'Numero richieste AI fallite')
CHAT_LATENCY = Summary('kaliai_chat_latency_seconds', 'Tempo di risposta chat (secondi)')

@app.route("/deepstep", methods=["POST"])
def deepstep():
    """
    Endpoint per esecuzione step-by-step con streaming in tempo reale (SSE).
    """
    data = request.get_json(silent=True)
    prompt = data.get("message", "")
    security_bypass = data.get("security_bypass", False)
    
    if not prompt:
        return jsonify({"error": "Prompt mancante."}), 400
    
    # Salva security_bypass in sessione per accesso globale
    session['security_bypass'] = security_bypass
    
    # 🎯 CREA TASK E CONTESTO PERSISTENTE
    task_manager = get_task_context_manager()
    
    # Costruisci contesto intelligente per ottenere objective_analysis
    # NOTA: build_smart_context_for_execution restituisce un dict, non solo objective_analysis
    objective_analysis = None
    try:
        from backend.core.ghostbrain_autogen import call_llm_streaming
        smart_context = build_smart_context_for_execution(prompt, call_llm_streaming)
        objective_analysis = smart_context.get('objective_analysis') if smart_context else None
    except Exception as e:
        log_info(f"[TASK-CONTEXT] Errore costruzione contesto: {e}")
        objective_analysis = None
    
    # Crea task
    task_id = task_manager.create_task(prompt, objective_analysis)
    log_info(f"[TASK-CONTEXT] Task creato: {task_id} per prompt: {prompt[:50]}...")
    
    def generate_events():
        """Generator per Server-Sent Events"""
        import queue
        import threading
        
        message_queue = queue.Queue()
        execution_results = {"step_results": None, "completed": 0, "model": "N/A"}
        
        def progress_callback(data):
            """Callback per ricevere aggiornamenti"""
            message_queue.put(data)
            # Cattura risultati finali
            if data.get("type") == "complete":
                execution_results["step_results"] = data.get("results", [])
                execution_results["completed"] = data.get("completed", 0)
        
        def run_execution():
            """Esegue lo step-by-step in un thread separato"""
            try:
                print(f"[DEBUG] Thread started for task {task_id}. Calling start_section9_mission...")
                # Passa task_id al callback per aggiornare contesto durante esecuzione
                step_results, completed, model = start_section9_mission(
                    prompt, 
                    progress_callback,
                    task_id=task_id
                )
                execution_results["step_results"] = step_results
                execution_results["completed"] = completed
                execution_results["model"] = model
                message_queue.put({"type": "done"})
            except Exception as e:
                message_queue.put({"type": "error", "error": str(e)})
        
        # Avvia esecuzione in thread separato
        thread = threading.Thread(target=run_execution)
        thread.daemon = True
        thread.start()
        
        # Stream degli eventi
        while True:
            try:
                data = message_queue.get(timeout=60)
                if data.get("type") == "done":
                    # Salva in chat history DOPO il completamento
                    try:
                        step_results = execution_results.get("step_results", [])
                        completed = execution_results.get("completed", 0)
                        model = execution_results.get("model", "N/A")
                        
                        # Crea summary per chat history
                        reply_summary = f"Step-by-Step Execution: {prompt}\n\n"
                        reply_summary += f"Completed: {completed}/{len(step_results)} steps\n\n"
                        
                        for sr in step_results:
                            reply_summary += f"Step {sr['step_number']}: {sr['step_description']}\n"
                            reply_summary += f"Status: {sr['status']}\n"
                            if sr.get('result'):
                                reply_summary += f"Result: {sr['result'][:300]}...\n"
                            reply_summary += "\n"
                        
                        # Salva in chat history
                        entry = {
                            "id": str(uuid.uuid4()),
                            "timestamp": datetime.now().isoformat(timespec="seconds"),
                            "user_input": prompt,
                            "reply": reply_summary,
                            "model": model,
                            "type": "step_execution",
                            "steps": step_results
                        }
                        save_chat_to_history(entry)
                        log_info(f"[HISTORY] Sessione step salvata in cronologia")
                    except Exception as e:
                        log_info(f"[HISTORY][ERRORE] Salvataggio step: {e}")
                    
                    # 🎯 AGGIORNA TASK CON RISULTATI FINALI
                    try:
                        # Estrai porte aperte e servizi dai risultati
                        import re
                        open_ports = []
                        for sr in step_results:
                            if sr.get('result'):
                                ports = re.findall(r'(\d+)/tcp\s+open', sr['result'])
                                open_ports.extend(ports)
                        
                        # Trova ultimo step fallito
                        last_failure = None
                        for sr in reversed(step_results):
                            if sr.get('status') == 'fallito':
                                last_failure = {
                                    'step_number': sr.get('step_number'),
                                    'step_description': sr.get('step_description'),
                                    'error': sr.get('result', '')[:200]
                                }
                                break
                        
                        # Estrai target IP dai risultati
                        target_ip = None
                        confirmed_target_ip = None
                        for sr in step_results:
                            if sr.get('result'):
                                # Cerca IP confermato nel risultato
                                ip_match = re.search(r'TARGET.*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', sr['result'], re.IGNORECASE)
                                if ip_match:
                                    confirmed_target_ip = ip_match.group(1)
                        
                        # Aggiorna task
                        task_manager.update_task(
                            task_id,
                            steps=[sr['step_description'] for sr in step_results],
                            step_results=step_results,
                            completed=completed,
                            status="completed" if completed == len(step_results) else "failed",
                            open_ports=list(set(open_ports)),
                            last_failure=last_failure,
                            confirmed_target_ip=confirmed_target_ip,
                            target_ip=confirmed_target_ip or target_ip
                        )
                        log_info(f"[TASK-CONTEXT] Task aggiornato: {task_id} - {completed}/{len(step_results)} step completati")
                    except Exception as e:
                        log_info(f"[TASK-CONTEXT][ERRORE] Aggiornamento task: {e}")
                    
                    # Step completati - notifica frontend CON TASK_ID
                    try:
                        message_queue.put({
                            "type": "steps_completed",
                            "message": f"✅ {completed}/{len(step_results)} step completati. Chat attiva per follow-up.",
                            "completed": completed,
                            "total": len(step_results),
                            "task_id": task_id  # 🎯 Passa task_id al frontend
                        })
                    except Exception as e:
                        log_info(f"[WORKFLOW] Errore notifica: {e}")
                    
                    break
                yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(
        stream_with_context(generate_events()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route("/resume_execution", methods=["POST"])
def resume_execution():
    """
    Endpoint per riprendere l'esecuzione dopo selezione target manuale.
    """
    data = request.get_json(silent=True)
    task_id = data.get("task_id")
    selected_ip = data.get("selected_ip")
    resume_from_step = data.get("resume_from_step", 1)
    
    if not task_id or not selected_ip:
        return jsonify({"error": "task_id e selected_ip richiesti"}), 400
    
    # Recupera task
    task_manager = get_task_context_manager()
    task = task_manager.get_task(task_id)
    
    if not task:
        return jsonify({"error": "Task non trovato o scaduto"}), 404
    
    prompt = task.get("prompt", "")
    
    def generate_events():
        """Generator per Server-Sent Events"""
        import queue
        import threading
        
        message_queue = queue.Queue()
        execution_results = {"step_results": None, "completed": 0, "model": "N/A"}
        
        def progress_callback(data):
            """Callback per ricevere aggiornamenti"""
            message_queue.put(data)
            if data.get("type") == "complete":
                execution_results["step_results"] = data.get("results", [])
                execution_results["completed"] = data.get("completed", 0)
        
        def run_execution():
            """Riprende l'esecuzione dal punto in cui si è fermata"""
            try:
                # Riprende esecuzione con target selezionato
                step_results, completed, model = execute_step_by_step_streaming(
                    prompt,
                    progress_callback,
                    task_id=task_id,
                    confirmed_target_ip=selected_ip,  # 🎯 Target selezionato dall'utente
                    resume_from_step=resume_from_step  # 🎯 Riprende da questo step
                )
                execution_results["step_results"] = step_results
                execution_results["completed"] = completed
                execution_results["model"] = model
                message_queue.put({"type": "done"})
            except Exception as e:
                message_queue.put({"type": "error", "error": str(e)})
        
        # Avvia esecuzione in thread separato
        thread = threading.Thread(target=run_execution)
        thread.daemon = True
        thread.start()
        
        # Stream degli eventi
        while True:
            try:
                data = message_queue.get(timeout=60)
                if data.get("type") == "done":
                    # Aggiorna task con risultati finali
                    try:
                        step_results = execution_results.get("step_results", [])
                        completed = execution_results.get("completed", 0)
                        
                        task_manager.update_task(
                            task_id,
                            step_results=step_results,
                            completed=completed,
                            status="completed" if completed == len(step_results) else "failed",
                            confirmed_target_ip=selected_ip
                        )
                        
                        message_queue.put({
                            "type": "steps_completed",
                            "message": f"✅ {completed}/{len(step_results)} step completati.",
                            "completed": completed,
                            "total": len(step_results),
                            "task_id": task_id
                        })
                    except Exception as e:
                        log_info(f"[RESUME][ERRORE] Aggiornamento task: {e}")
                    
                    break
                yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(
        stream_with_context(generate_events()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route("/memory/<memory_id>", methods=["DELETE"])
def delete_memory(memory_id):
    from backend.core.tools import delete_memory_from_vectordb
    try:
        ok = delete_memory_from_vectordb(memory_id)
        if ok:
            return jsonify({"ok": True, "id": memory_id})
        else:
            return jsonify({"ok": False, "error": "Ricordo non trovato"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/memory_page")
def memory_page():
    return render_template("memory.html")


@app.route("/memory", methods=["GET"])
def memory():
    from backend.core.tools import list_all_long_term_memories
    memories = list_all_long_term_memories()
    return jsonify({"memories": memories})


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# === Percorsi principali ===
PROJECT_ROOT = os.path.dirname(app.root_path)  # /home/.../kaliAI
DATA_PATH = os.path.join(PROJECT_ROOT, "data")
SESSION_PATH = os.path.join(DATA_PATH, "session")
CHAT_HISTORY_PATH = os.path.join(SESSION_PATH, "chat_history.json")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "frontend", "static", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(SESSION_PATH, exist_ok=True)

def log_info(msg):
    logger.info(msg)

def get_catalogued_path(filename_base, file_type="deepsearch"):
    """
    Crea una struttura di directory catalogata per tipo/data/ora.
    Esempio: static/results/deepsearch/2025/10/02/kaliAI_update_02_10_2025_1430.md
    """
    now = datetime.now()
    year_dir = os.path.join(RESULTS_DIR, file_type, str(now.year))
    month_dir = os.path.join(year_dir, f"{now.month:02d}")
    day_dir = os.path.join(month_dir, f"{now.day:02d}")
    os.makedirs(day_dir, exist_ok=True)
    
    # Filename con timestamp completo
    timestamp = f"{now.day:02d}_{now.month:02d}_{now.year}_{now.hour:02d}{now.minute:02d}"
    filename = f"{filename_base}_{timestamp}.md"
    return os.path.join(day_dir, filename), filename

# === Utility Chat History ===
def load_chat_history():
    if not os.path.exists(CHAT_HISTORY_PATH):
        return []
    with open(CHAT_HISTORY_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_chat_to_history(entry):
    history = load_chat_history()
    history.append(entry)
    with open(CHAT_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

# ========== HOME ==========
@app.route("/")
def index():
    return render_template("index.html")

# ========== API MODELLO CORRENTE ==========
@app.route("/api/model")
def get_model():
    """Restituisce il modello LLM configurato da variabili ambiente."""
    try:
        model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
        return jsonify({"model": model_name})
    except Exception as e:
        log_info(f"[ERRORE /api/model]: {e}")
        return jsonify({"model": f"Errore lettura modello: {e}"})

# ========== CHATBOT ==========
@app.route("/ask", methods=["POST"])
@CHAT_LATENCY.time()
def ask():
    REQUESTS_TOTAL.inc()
    try:
        user_input = request.json.get("message", "")
        task_id = request.json.get("task_id", None)  # 🎯 Ricevi task_id dal frontend
        use_step_context = request.json.get("use_step_context", False)
        log_info(f"Messaggio utente: {user_input}")
        
        # 🎯 SE TASK_ID PRESENTE: Usa contesto del task invece della memoria a lungo termine
        if task_id:
            task_manager = get_task_context_manager()
            task_context = task_manager.get_task_context_for_chat(task_id)
            
            if task_context:
                log_info(f"[CHAT] Usando contesto task: {task_id}")
                # Prepara prompt arricchito con contesto task
                enriched_prompt = task_context + user_input
                
                # Chiama LLM con contesto task (senza memoria a lungo termine)
                result = start_swarm_chat(enriched_prompt, use_task_context=True)
            else:
                log_info(f"[CHAT] Task {task_id} non trovato o scaduto, uso memoria normale")
                result = start_swarm_chat(user_input)
        else:
            # Nessun task_id: comportamento normale con memoria a lungo termine
            if use_step_context:
                log_info("[CHAT] Contesto step precedenti gestito dalla memoria conversazionale")
            
            result = start_swarm_chat(user_input)
        # Adesso il backend deve restituire (reply, model, memoria_usata)
        if not result or not isinstance(result, (tuple, list)):
            reply, model, memoria_usata = "Errore interno: nessuna risposta dal modello.", "N/A", []
        elif len(result) == 2:
            reply, model = result
            memoria_usata = []
        else:
            reply, model, memoria_usata = result

        reply_text = f"{reply}\n\n(MODELLO: {model})" if reply else "Nessuna risposta."

        # --- Salva la chat in cronologia ---
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_input": user_input,
            "reply": reply,
            "model": model,
            "memoria_usata": memoria_usata  # Log utile per debug, opzionale
        }
        save_chat_to_history(entry)

        return jsonify({
            "reply": reply_text,
            "model": model,
            "memoria_usata": memoria_usata
        })
    except Exception as e:
        REQUESTS_FAILED.inc()
        log_info(f"[ERRORE /ask]: {e}")
        return jsonify({"reply": f"Errore interno: {e}"}), 500


# ========== RICERCA PROFONDA ==========
def duckduckgo_search(query, max_links=5):
    from duckduckgo_search import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query):
            url = r.get("href") or r.get("url")
            if url:
                results.append(url)
            if len(results) >= max_links:
                break
    return results[:max_links]

def get_page_text(url, max_chars=4000):
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for s in soup(["script", "style"]):
            s.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(line for line in lines if line)
        return text[:max_chars]
    except Exception as e:
        log_info(f"[ERRORE get_page_text su {url}]: {e}")
        return ""

@app.route("/deepsearch", methods=["POST"])
def deepsearch():
    try:
        data = request.get_json(silent=True)
        if not data or not data.get("query"):
            return jsonify({"error": "Query mancante o formato JSON non valido."}), 400

        query = data["query"]
        log_info(f"[DEEPSEARCH] Query ricevuta: {query}")

        links = []
        try:
            links = duckduckgo_search(query)
        except Exception as search_err:
            log_info(f"[ERRORE duckduckgo_search]: {search_err}")
            return jsonify({"error": "Errore durante la ricerca web."}), 500

        if not links:
            return jsonify({"error": "Nessun link trovato per la query."}), 404

        all_text = ""
        for url in links:
            text = get_page_text(url)
            all_text += f"\n---\nURL: {url}\n\n{text}\n"

        prompt = (
            "Analizza e confronta queste fonti web, sintetizza in markdown evitando ridondanze "
            "con la knowledge base:\n" + all_text
        )

        result = start_autogen_chat(prompt)
        if isinstance(result, tuple):
            reply = result[0]
            model = result[1] if len(result) > 1 else "N/A"
        else:
            reply = result
            model = "N/A"
        
        # Usa catalogazione organizzata
        filepath, filename = get_catalogued_path("kaliAI_update", "deepsearch")
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(reply)
            log_info(f"DeepSearch salvato in: {filepath}")
        except Exception as file_err:
            log_info(f"[ERRORE scrittura file]: {file_err}")
            return jsonify({"error": "Errore nel salvataggio del file."}), 500

        # URL relativo per il download
        relative_path = os.path.relpath(filepath, RESULTS_DIR)
        
        return jsonify({
            "filename": filename,
            "model": model,
            "url": f"/download/{relative_path.replace(os.sep, '/')}"
        })

    except Exception as e:
        log_info(f"[ERRORE deepsearch GENERALE]: {e}")
        return jsonify({"error": str(e)}), 500

# ========== DOWNLOAD FILE ==========
@app.route("/download/<path:filename>")
def download_file(filename):
    """
    Download file da RESULTS_DIR con supporto per sottodirectory.
    Il path può essere: filename.md oppure deepsearch/2025/10/02/filename.md
    """
    try:
        # Sicurezza: normalizza il path e verifica che sia sotto RESULTS_DIR
        filepath = os.path.normpath(os.path.join(RESULTS_DIR, filename))
        if not filepath.startswith(os.path.abspath(RESULTS_DIR)):
            return jsonify({"error": "Accesso negato"}), 403
        
        directory = os.path.dirname(filepath)
        file_name = os.path.basename(filepath)
        return send_from_directory(directory, file_name, as_attachment=True)
    except Exception as e:
        log_info(f"[ERRORE download]: {e}")
        return jsonify({"error": "File non trovato"}), 404

# ========== API CHAT HISTORY ==========
@app.route("/chat_history", methods=["GET"])
def chat_history():
    try:
        history = load_chat_history()
        # Più recenti in cima
        history_sorted = sorted(history, key=lambda x: x["timestamp"], reverse=True)
        return jsonify({"history": history_sorted})
    except Exception as e:
        log_info(f"[ERRORE /chat_history]: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/chat_history", methods=["DELETE"])
def delete_chat_history():
    """Cancella tutta la cronologia chat."""
    try:
        if os.path.exists(CHAT_HISTORY_PATH):
            os.remove(CHAT_HISTORY_PATH)
        log_info("Cronologia chat cancellata")
        return jsonify({"ok": True, "message": "Cronologia cancellata con successo"})
    except Exception as e:
        log_info(f"[ERRORE DELETE /chat_history]: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# ========== START ==========
if __name__ == "__main__":
    log_info("KaliAI pronto sulla porta 5000")
    app.run(debug=True)
