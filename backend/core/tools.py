#!/usr/bin/env python3
"""
Tools Module - Backward compatibility wrapper
Importa funzioni dai moduli organizzati e mantiene compatibilità
"""
import os
import json
import logging
import shutil
import chromadb
import uuid
import tempfile
import subprocess
import re
from datetime import datetime
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger('TOOLS')

# === Percorsi ===
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_PATH = os.path.join(PROJECT_ROOT, "data")
SESSION_PATH = os.path.join(DATA_PATH, "session")
CHROMA_DB_PATH = os.path.join(DATA_PATH, 'chroma_vector_db')
KALI_KB_PATH = os.path.join(DATA_PATH, 'kaliAI.md')
BASE_TEST_DIR = os.path.join(PROJECT_ROOT, 'test_env')
os.makedirs(BASE_TEST_DIR, exist_ok=True)
CHAT_HISTORY_PATH = os.path.join(SESSION_PATH, "chat_history.json")
CONTEXTUAL_MEMORY_PATH = os.path.join(SESSION_PATH, "contextual_memory.json")

# Crea directory sessione
os.makedirs(SESSION_PATH, exist_ok=True)

# === Config da ENV ===
USE_DOCKER_SANDBOX = os.getenv("USE_DOCKER_SANDBOX", "false").lower() == "true"

def log_info(msg):
    logger.info(msg)

# ============================================================================
# IMPORT DA MODULI ORGANIZZATI
# ============================================================================

# Memory functions
from backend.core.memory import (
    add_memory_to_vectordb,
    recall_from_vectordb,
    list_all_long_term_memories,
    delete_memory_from_vectordb,
    add_contextual_solution
)

# Command execution
from backend.core.execution import execute_bash_command
from backend.core.graph_manager import (
    record_host_observation,
    record_port_observation,
    record_relationship,
    get_graph_summary_text,
    find_paths_between_hosts,
    GRAPH_PATH
)

# Step generation
from backend.core.steps import generate_deep_steps

# ============================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# ============================================================================

# Wrapper per execute_bash_command_tool (usato da ghostbrain_autogen)
def execute_bash_command_tool(command: str) -> str:
    """Wrapper per compatibilità con ghostbrain_autogen"""
    return execute_bash_command(command)

def execute_python_code(code: str, timeout: int = 90) -> str:
    """
    Esegue codice Python dinamico in una sandbox locale.
    - Scrive il codice in un file temporaneo
    - Usa python3 per eseguirlo
    - Restituisce stdout/stderr
    """
    sandbox_dir = os.path.join(BASE_TEST_DIR, "python_executor")
    os.makedirs(sandbox_dir, exist_ok=True)

    if not code or not code.strip():
        return "[PYTHON][ERRORE] Codice vuoto, nulla da eseguire."

    script_path = os.path.join(sandbox_dir, f"script_{uuid.uuid4().hex}.py")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        result = subprocess.run(
            ["python3", script_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output_parts = []
        if result.stdout:
            output_parts.append("[STDOUT]\n" + result.stdout.strip())
        if result.stderr:
            output_parts.append("[STDERR]\n" + result.stderr.strip())

        if not output_parts:
            return "[PYTHON] Esecuzione completata senza output."

        return "\n\n".join(part for part in output_parts if part.strip())

    except subprocess.TimeoutExpired:
        return "[PYTHON][TIMEOUT] Esecuzione terminata per timeout (limite 90s)."
    except Exception as e:
        return f"[PYTHON][ERRORE] {e}"
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass

def execute_python_code_tool(code: str) -> str:
    """Wrapper registrabile per ghostbrain_autogen."""
    return execute_python_code(code)

def graph_summary_tool(limit_nodes: int = 15, limit_edges: int = 25) -> str:
    return get_graph_summary_text(limit_nodes=limit_nodes, limit_edges=limit_edges)

def graph_paths_tool(source_ip: str, target_ip: str, max_depth: int = 4) -> str:
    return find_paths_between_hosts(source_ip, target_ip, max_depth=max_depth)

def analyze_firmware(file_path: str, extract: bool = True) -> str:
    """
    Analizza firmware/binari usando binwalk/strings se disponibili.
    """
    file_path = file_path.strip()
    if not file_path:
        return "[FIRMWARE][ERRORE] Specifica un file da analizzare."
    if not os.path.isfile(file_path):
        return f"[FIRMWARE][ERRORE] File non trovato: {file_path}"

    outputs = []

    binwalk_path = shutil.which("binwalk")
    strings_path = shutil.which("strings")

    if binwalk_path:
        try:
            cmd = [binwalk_path, file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            outputs.append("[BINWALK]\n" + result.stdout.strip()[:4000] or "(nessun output)")
            if extract:
                extract_dir = os.path.join(os.path.dirname(file_path), "_firmware_extract")
                os.makedirs(extract_dir, exist_ok=True)
                cmd_extract = [binwalk_path, "-e", "-C", extract_dir, file_path]
                subprocess.run(cmd_extract, capture_output=True, text=True, timeout=300)
                outputs.append(f"[BINWALK] Estrazione tentata in {extract_dir}")
        except Exception as e:
            outputs.append(f"[BINWALK][ERRORE] {e}")
    else:
        outputs.append("[BINWALK] Non installato. Installa con: sudo apt install binwalk")

    if strings_path:
        try:
            cmd = [strings_path, "-n", "8", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            important_strings = "\n".join(result.stdout.splitlines()[:200])
            outputs.append("[STRINGS]\n" + (important_strings or "(nessun output)"))
        except Exception as e:
            outputs.append(f"[STRINGS][ERRORE] {e}")
    else:
        outputs.append("[STRINGS] Non installato. Installa con: sudo apt install binutils")

    return "\n\n".join(outputs)

def analyze_firmware_tool(file_path: str) -> str:
    return analyze_firmware(file_path)

# ============================================================================
# FUNZIONI NON SPOSTATE (RAG, Chat History, Step Execution)
# ============================================================================

# === RAG: INIT / SEARCH ===
_chroma_initialized = False

def init_kali_rag_db():
    global _chroma_initialized
    if _chroma_initialized:
        log_info("Database di Kali Linux già inizializzato.")
        return

    log_info("Inizializzazione database RAG di Kali Linux in corso...")
    
    try:
        # Usa la knowledge base completa da knowledge_enhancer
        from knowledge import knowledge_enhancer
        
        # Verifica statistiche della knowledge base
        stats = knowledge_enhancer.get_stats()
        total_docs = stats.get('total', 0)
        
        if total_docs > 0:
            log_info(f"Knowledge base Kali Linux già popolata con {total_docs:,} documenti totali.")
            log_info(f"  - kali_kb: {stats.get('kali_kb', 0):,} documenti")
            log_info(f"  - exploits: {stats.get('exploits', 0):,} documenti")
            log_info(f"  - cve: {stats.get('cve', 0):,} documenti")
            log_info(f"  - successes: {stats.get('successes', 0):,} documenti")
            log_info(f"  - tools: {stats.get('tools', 0):,} documenti")
        else:
            log_info("⚠️  Knowledge base vuota. Esegui l'importazione con: python scripts/maintenance/import_knowledge_export.py")
        
        # Inizializza anche la collection legacy per compatibilità
        try:
            client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            collection = client.get_or_create_collection(name="kali_linux_kb")
            legacy_count = collection.count()
            if legacy_count > 0:
                log_info(f"Collection legacy trovata con {legacy_count:,} documenti.")
        except Exception as e:
            log_info(f"[WARNING] Collection legacy non accessibile: {e}")

        _chroma_initialized = True
        log_info("Database RAG Kali Linux inizializzato con successo!")
    except Exception as e:
        log_info(f"[ERRORE RAG] Impossibile inizializzare il database RAG: {e}")
        import traceback
        traceback.print_exc()
        _chroma_initialized = False

def rag_search_tool(query: str) -> str:
    """
    Ricerca RAG migliorata - cerca in tutte le collections.
    """
    global _chroma_initialized
    try:
        from knowledge import knowledge_enhancer
        
        # Usa enhanced search (multi-collection)
        results = knowledge_enhancer.enhanced_search(query, top_k=5)
        
        if results:
            response = "[RAG] Informazioni dalla Knowledge Base:\n\n"
            
            for i, res in enumerate(results, 1):
                source = res['source'].upper()
                doc = res['doc'][:300]  # Limita lunghezza
                response += f"[{source}] {doc}...\n\n"
            
            return response
        else:
            return "[RAG] Nessuna informazione rilevante trovata nella knowledge base."
            
    except Exception as e:
        # Fallback a ricerca semplice
        try:
            client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            collection = client.get_or_create_collection(name="kali_linux_kb")
            if not _chroma_initialized or collection.count() == 0:
                return "[RAG][ERRORE] Database RAG non inizializzato."
            results = collection.query(
                query_texts=[query],
                n_results=3
            )
            if results and results['documents'] and results['documents'][0]:
                response = "[RAG] Informazioni dalla Knowledge Base:\n"
                for doc_list in results['documents']:
                    for doc_content in doc_list:
                        response += f"- {doc_content}\n"
                return response
            else:
                return "[RAG] Nessuna informazione rilevante trovata nella knowledge base."
        except Exception as e2:
            return f"[RAG][ERRORE] Ricerca fallita: {e}, {e2}"

# === Chat History (per replay/reload) ===
def generate_chat_id():
    return f"chat-{uuid.uuid4()}"

def load_chat_history():
    """Restituisce tutta la cronologia come lista di messaggi."""
    if not os.path.exists(CHAT_HISTORY_PATH):
        return []
    try:
        with open(CHAT_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_chat_message(chat_id, role, message, timestamp=None):
    """Salva un messaggio nella cronologia, mantenendo l'id della chat."""
    history = load_chat_history()
    entry = {
        "id": chat_id,
        "timestamp": timestamp or datetime.now().isoformat(timespec="seconds"),
        "role": role,
        "message": message
    }
    history.append(entry)
    with open(CHAT_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return entry

def load_chat_by_id(chat_id):
    """Carica tutti i messaggi relativi a una chat_id (ordinati per timestamp)."""
    history = load_chat_history()
    chat = [msg for msg in history if msg.get("id") == chat_id]
    chat.sort(key=lambda x: x["timestamp"])
    return chat

# === STEP-BY-STEP EXECUTION ===
def execute_step_by_step_streaming(prompt, progress_callback=None, task_id=None, confirmed_target_ip=None, resume_from_step=1):
    """
    Esegue un obiettivo suddividendolo in step con retry automatico e streaming.
    progress_callback: funzione chiamata per aggiornare lo stato in tempo reale
    Ritorna: (risultati, step_completati, modello)
    """
    from backend.core.ghostbrain_autogen import start_autogen_chat
    
    def emit_progress(data):
        """Helper per emettere aggiornamenti di progresso"""
        if progress_callback:
            progress_callback(data)
    
    log_info(f"[STEP-BY-STEP] Avvio esecuzione per: {prompt}")
    emit_progress({"type": "init", "message": "Inizializzazione..."})
    
    # === SMART CONTEXT BUILDING ===
    target_context = ""
    objective_analysis = None
    
    try:
        from backend.core.smart_context_builder import build_smart_context_for_execution
        from backend.core.ghostbrain_autogen import call_llm_streaming
        
        log_info("[STEP-BY-STEP] 🧠 Costruzione contesto intelligente...")
        
        smart_context = build_smart_context_for_execution(
            prompt,
            llm_call_fn=lambda p: call_llm_streaming(p, max_tokens=400, temperature=0.2)
        )
        
        target_context = smart_context.get('step_generation_context', '')
        objective_analysis = smart_context.get('objective_analysis')
        rag_knowledge = smart_context.get('rag_knowledge', '')
        
        if objective_analysis:
            log_info(f"[STEP-BY-STEP] 🎯 Target analizzato: {objective_analysis.get('target_description', 'N/A')}")
            emit_progress({
                "type": "target_analyzed",
                "target": objective_analysis.get('target_description'),
                "approach": objective_analysis.get('approach')
            })
        
        if rag_knowledge:
            log_info(f"[STEP-BY-STEP] 📚 Conoscenza RAG caricata: {len(rag_knowledge)} caratteri")
            emit_progress({
                "type": "rag_loaded",
                "message": "Knowledge base consultata"
            })
        
    except Exception as e:
        log_info(f"[STEP-BY-STEP] ⚠️ Smart context fallito, uso approccio base: {e}")
        import traceback
        traceback.print_exc()
    
    # 1. Genera gli step (con contesto target)
    emit_progress({"type": "generating", "message": "Generazione step..."})
    
    # Arricchisci prompt con target estratto
    enriched_prompt = prompt
    if target_context:
        enriched_prompt = f"{target_context}\nOBIETTIVO:\n{prompt}"
    
    steps = generate_deep_steps(enriched_prompt)
    log_info(f"[STEP-BY-STEP] Generati {len(steps)} step")
    emit_progress({"type": "steps_generated", "total_steps": len(steps), "steps": steps})
    
    step_results = []
    completed_context = target_context if target_context else ""
    model = "N/A"
    
    # 🎯 STATO PERSISTENTE: TARGET_IP confermato (una volta identificato, è assoluto)
    # Se viene passato confirmed_target_ip (da resume), usalo direttamente
    confirmed_target_ip_local = confirmed_target_ip  # Variabile locale per evitare conflitti
    if confirmed_target_ip_local:
        log_info(f"[STEP-BY-STEP] 🎯 TARGET_IP PRECONFERMATO (da selezione utente): {confirmed_target_ip_local}")
        emit_progress({
            "type": "target_confirmed",
            "target_ip": confirmed_target_ip_local,
            "confidence": 10  # Massima confidenza se selezionato dall'utente
        })
    
    # 🎯 Se resume_from_step > 1, salta gli step già eseguiti
    start_step = resume_from_step - 1  # resume_from_step è 1-based, start_step è 0-based
    if start_step > 0:
        log_info(f"[STEP-BY-STEP] 🔄 Ripresa esecuzione dallo step {resume_from_step}")
        emit_progress({
            "type": "resume",
            "message": f"Ripresa esecuzione dallo step {resume_from_step}",
            "resume_from_step": resume_from_step
        })
    
    # === EXECUTOR INTELLIGENTE V2 ===
    use_smart_executor = True
    if use_smart_executor:
        try:
            from backend.core.step_executor import AdaptiveStepExecutor
            from backend.core.ghostbrain_autogen import call_llm_streaming
            
            # Passa objective analysis invece di target_info hard-coded
            executor = AdaptiveStepExecutor(
                execute_command_fn=execute_bash_command,
                llm_call_fn=lambda prompt: call_llm_streaming(prompt, max_tokens=300, temperature=0.3),
                target_info=objective_analysis
            )
            
            i = start_step  # 🎯 Inizia dallo step di resume (0-based)
            while i < len(steps):
                step = steps[i]
                i += 1  # Incrementa DOPO aver preso lo step (così inserimenti funzionano)
                if i > len(steps):
                    break  # Protezione contro loop infinito
                
                log_info(f"[STEP-BY-STEP] Esecuzione step {i}/{len(steps)}: {step}")
                emit_progress({
                    "type": "step_start",
                    "step_number": i,
                    "total_steps": len(steps),
                    "step_description": step
                })
                
                # 🎯 INIETTA TARGET_IP CONFERMATO nel contesto se disponibile
                enhanced_context = completed_context
                if confirmed_target_ip_local:
                    enhanced_context = f"""
══════════════════════════════════════════════════
🎯 CONTESTO CRITICO E INVIOLABILE
══════════════════════════════════════════════════
L'IP del target è stato CONFERMATO ed è: {confirmed_target_ip_local}
TUTTI i comandi devono essere eseguiti ESCLUSIVAMENTE contro questo IP.
NON usare altri IP dal contesto, anche se presenti.
══════════════════════════════════════════════════

{completed_context}
"""
                
                result = executor.execute_step_with_intelligence(
                    step_description=step,
                    step_number=i,
                    context=enhanced_context,
                    max_attempts=3
                )
                
                # Aggiungi a risultati
                step_results.append({
                    "step_number": i,
                    "step_description": step,
                    "result": result['output'],
                    "command": result['command'],
                    "attempts": result['attempts'],
                    "status": "completato" if result['success'] else "fallito"
                })
                
                if result['success']:
                    log_info(f"[STEP-BY-STEP] ✅ Step {i} completato con successo")
                    
                    # 🎯 PRINCIPIO DI INCERTEZZA: Verifica confidenza identificazione target (solo step 1)
                    if i == 1 and not confirmed_target_ip_local:
                        try:
                            # Estrai informazioni di confidenza dal risultato
                            target_info = result.get('target_info')  # Dovrebbe essere aggiunto da execute_step_with_intelligence
                            
                            if target_info:
                                confidence = target_info.get('confidence', 0)
                                candidates = target_info.get('candidates', []) or []
                                
                                # Soglia minima di confidenza: 7/10
                                if confidence < 7:
                                    log_info(f"[STEP-BY-STEP] ⚠️ Confidenza identificazione target troppo bassa: {confidence}/10")
                                    log_info(f"[STEP-BY-STEP] 🔍 Richiesta selezione manuale target all'utente")
                                    
                                    # Prepara lista candidati per l'utente (solo se disponibili)
                                    candidates_list = []
                                    for cand in candidates[:5]:  # Top 5
                                        if cand.get('ip'):
                                            candidates_list.append({
                                                "ip": cand.get('ip'),
                                                "hostname": cand.get('hostname', 'N/A'),
                                                "vendor": cand.get('vendor', 'N/A'),
                                                "score": cand.get('score', 0),
                                                "reasons": cand.get('reasons', [])
                                            })

                                    if not candidates_list:
                                        log_info("[STEP-BY-STEP] ⚠️ Confidenza bassa ma nessun candidato disponibile. Procedo senza selezione manuale.")
                                    else:
                                        # 🎯 SALVA STATO PER RESUME
                                        if task_id:
                                            from backend.core.task_context_manager import get_task_context_manager
                                            task_manager = get_task_context_manager()
                                            task_manager.update_task(
                                                task_id,
                                                status="paused",
                                                paused_at_step=i,
                                                target_candidates=candidates_list,
                                                confidence=confidence
                                            )
                                        
                                        emit_progress({
                                            "type": "target_selection_required",
                                            "message": "Identificazione target incerta. Seleziona il target corretto:",
                                            "confidence": confidence,
                                            "candidates": candidates_list,
                                            "step_number": i,
                                            "task_id": task_id  # 🎯 Passa task_id per resume
                                        })
                                        
                                        # FERMA esecuzione e aspetta input utente
                                        log_info(f"[STEP-BY-STEP] ⏸️ Esecuzione in pausa - in attesa selezione target dall'utente")
                                        # NOTA: L'esecuzione continuerà quando l'utente seleziona un target
                                        # Questo sarà gestito da un nuovo endpoint /resume_execution
                                        break  # Esci dal loop, l'esecuzione riprenderà dopo selezione
                                else:
                                    # Confidenza sufficiente, procedi normalmente
                                    if result.get('target_ip'):
                                        confirmed_target_ip_local = result['target_ip']
                                        log_info(f"[STEP-BY-STEP] 🎯 TARGET_IP CONFERMATO (confidenza {confidence}/10): {confirmed_target_ip_local}")
                                        emit_progress({
                                            "type": "target_confirmed",
                                            "target_ip": confirmed_target_ip_local,
                                            "confidence": confidence
                                        })
                        except Exception as e:
                            log_info(f"[STEP-BY-STEP] ⚠️ Errore verifica confidenza: {e}")
                            import traceback
                            traceback.print_exc()
                            # Fallback: procedi con identificazione normale se disponibile
                            if result.get('target_ip') and not confirmed_target_ip_local:
                                confirmed_target_ip_local = result['target_ip']
                    
                    # 🎯 SALVA TARGET_IP CONFERMATO (una volta identificato, è assoluto)
                    if result.get('target_ip') and not confirmed_target_ip_local:
                        confirmed_target_ip_local = result['target_ip']
                        log_info(f"[STEP-BY-STEP] 🎯 TARGET_IP CONFERMATO: {confirmed_target_ip_local} (sarà usato per tutti gli step successivi)")
                        emit_progress({
                            "type": "target_confirmed",
                            "target_ip": confirmed_target_ip_local
                        })
                        
                        # 🎯 AGGIORNA TASK CONTEXT se disponibile
                        if task_id:
                            try:
                                from backend.core.task_context_manager import get_task_context_manager
                                task_manager = get_task_context_manager()
                                task_manager.update_task(task_id, confirmed_target_ip=confirmed_target_ip_local, target_ip=confirmed_target_ip_local)
                            except Exception as e:
                                log_info(f"[TASK-CONTEXT] Errore aggiornamento target_ip: {e}")
                    
                    # 📈 AGGIORNA KNOWLEDGE GRAPH
                    try:
                        graph_ip = result.get('target_ip') or confirmed_target_ip_local
                        if graph_ip:
                            hostname_hint = None
                            vendor_hint = None
                            mac_hint = None
                            target_info = result.get('target_info') or {}
                            candidates = target_info.get('candidates') or []
                            if candidates:
                                hostname_hint = candidates[0].get('hostname')
                                vendor_hint = candidates[0].get('vendor')
                            output_text = result.get('result', '')
                            mac_match = re.search(r'MAC Address:\s*([0-9A-Fa-f:]{17})\s*\(([^)]+)\)?', output_text, re.IGNORECASE)
                            if mac_match:
                                mac_hint = mac_match.group(1)
                                vendor_hint = vendor_hint or mac_match.group(2)
                            record_host_observation(
                                graph_ip,
                                hostname=hostname_hint,
                                vendor=vendor_hint,
                                mac=mac_hint,
                                source=f"step_{i}"
                            )
                            # Registra porte aperte
                            open_ports = re.findall(r'(\d+)/(tcp|udp)\s+open', output_text, re.IGNORECASE)
                            for port, proto in open_ports:
                                record_port_observation(
                                    graph_ip,
                                    int(port),
                                    protocol=proto.lower(),
                                    metadata={
                                        "step": i,
                                        "description": step,
                                        "command": result['command']
                                    }
                                )
                    except Exception as graph_err:
                        log_info(f"[GRAPH] Impossibile aggiornare il knowledge graph: {graph_err}")
                    
                    # 🔍 REALITY CHECK STRATEGICO: Dopo step 2, analizza se la strategia è ancora valida
                    if i == 2:  # Dopo i primi 2 step di ricognizione
                        try:
                            from backend.core.strategic_analyzer import analyze_strategy_validity
                            
                            # Raccogli risultati ricognizione
                            recon_results = ""
                            for sr in step_results[:2]:  # Primi 2 step
                                recon_results += f"Step {sr['step_number']}: {sr['step_description']}\n"
                                recon_results += f"Output: {sr.get('result', '')[:500]}\n\n"
                            
                            log_info(f"[STEP-BY-STEP] 🔍 Esecuzione reality check strategico dopo step {i}...")
                            emit_progress({
                                "type": "strategic_analysis",
                                "message": "Analisi strategica in corso..."
                            })
                            
                            # Analizza validità strategia
                            is_valid, reason, new_strategy = analyze_strategy_validity(
                                original_objective=prompt,
                                reconnaissance_results=recon_results,
                                current_steps=steps,
                                llm_call_fn=lambda p: call_llm_streaming(p, max_tokens=400, temperature=0.2)
                            )
                            
                            if not is_valid:
                                log_info(f"[STEP-BY-STEP] ⚠️ STRATEGIA INVALIDA: {reason}")
                                emit_progress({
                                    "type": "strategy_invalid",
                                    "reason": reason,
                                    "new_strategy": new_strategy
                                })
                                
                                # Rigenera piano con nuova strategia
                                log_info(f"[STEP-BY-STEP] 🗺️ Rigenerazione piano con strategia corretta...")
                                emit_progress({
                                    "type": "replanning",
                                    "message": f"Rigenerazione piano: {reason}"
                                })
                                
                                # Crea prompt per nuovo piano
                                replan_prompt = f"""
OBIETTIVO ORIGINALE: {prompt}

RISULTATI RICOGNIZIONE:
{recon_results}

PROBLEMA IDENTIFICATO:
{reason}

NUOVA STRATEGIA SUGGERITA:
{new_strategy}

GENERA UN NUOVO PIANO basato sul tipo reale di target identificato.
Focalizzati solo su approcci che sono fattibili per questo tipo di target.
"""
                                new_steps = generate_deep_steps(replan_prompt)
                                if new_steps and len(new_steps) > 0:
                                    # Sostituisci step rimanenti con nuovo piano
                                    steps = steps[:i] + new_steps
                                    log_info(f"[STEP-BY-STEP] ✅ Nuovo piano generato: {len(new_steps)} step (totale: {len(steps)})")
                                    emit_progress({
                                        "type": "replanned",
                                        "new_steps": new_steps,
                                        "total_steps": len(steps),
                                        "reason": reason
                                    })
                            else:
                                log_info(f"[STEP-BY-STEP] ✅ Strategia confermata valida")
                                emit_progress({
                                    "type": "strategy_valid",
                                    "message": "Strategia originale confermata"
                                })
                        except Exception as e:
                            log_info(f"[STEP-BY-STEP] ⚠️ Errore reality check: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # Aggiungi target IP al contesto se trovato
                    target_ip_info = ""
                    if result.get('target_ip'):
                        target_ip_info = f"\n🎯 TARGET IP IDENTIFICATO: {result['target_ip']}\n"
                    elif confirmed_target_ip_local:
                        target_ip_info = f"\n🎯 TARGET IP CONFERMATO: {confirmed_target_ip_local} (usa questo IP!)\n"
                    
                    # 🔧 SANITIZZA OUTPUT per risparmiare token
                    output_sanitized = result.get('output', '')
                    if output_sanitized and result.get('command'):
                        # Importa sanitizer se disponibile
                        try:
                            from backend.core.step_executor import AdaptiveStepExecutor
                            # Crea istanza temporanea solo per sanitize (non eseguire comandi)
                            temp_executor = AdaptiveStepExecutor(None, None, None)
                            output_sanitized = temp_executor._sanitize_output(output_sanitized, result['command'])
                        except Exception as e:
                            log_info(f"[STEP-BY-STEP] ⚠️ Errore sanitizzazione output: {e}")
                            # Fallback: usa output originale
                            output_sanitized = result.get('output', '')
                    
                    completed_context += f"Step {i}: {step}\nComando: {result['command']}{target_ip_info}\nOutput: {output_sanitized}\n\n"
                    emit_progress({
                        "type": "step_success",
                        "step_number": i,
                        "attempts": result['attempts'],
                        "result": result['output'],
                        "target_ip": result.get('target_ip')
                    })
                    
                    # 🔍 ANALISI AUTOMATICA SERVIZI SCOPERTI: Dopo scansione riuscita, analizza ogni porta aperta
                    step_lower = step.lower()
                    output_lower = result['output'].lower()
                    # Usa TARGET_IP confermato se disponibile, altrimenti quello dal risultato
                    target_ip = confirmed_target_ip or result.get('target_ip')
                    
                    # Rileva se questo è uno step di scansione (nmap)
                    is_scan_step = 'nmap' in step_lower or 'scansiona' in step_lower or 'scan' in step_lower
                    
                    if is_scan_step and target_ip:
                        # Estrai porte aperte dall'output
                        open_ports = re.findall(r'(\d+)/tcp\s+open', result['output'])
                        # Rimuovi duplicati e ordina
                        unique_ports = sorted(list(set(open_ports)))
                        
                        if unique_ports:
                            log_info(f"[STEP-BY-STEP] 🔍 Porte aperte trovate: {', '.join(unique_ports)}")
                            
                            # Verifica step futuri per evitare duplicati
                            remaining_steps = steps[i:] if i < len(steps) else []
                            
                            # Porte standard HTTP/HTTPS (per curl)
                            http_ports = ['80', '443', '8000', '8080', '8443', '8008', '8009', '8888', '9000']
                            
                            # Genera step di analisi per ogni porta trovata
                            for port in unique_ports:
                                # Verifica se c'è già uno step che analizza questa porta
                                port_already_analyzed = any(
                                    port in s and ('curl' in s.lower() or 'nc' in s.lower() or 'netcat' in s.lower() or 'interroga' in s.lower() or 'analizza' in s.lower())
                                    for s in remaining_steps
                                )
                                
                                if not port_already_analyzed:
                                    # Determina comando appropriato basato sulla porta
                                    if port in http_ports:
                                        # Porta HTTP: usa curl per ottenere banner/headers
                                        analysis_step = f"Interroga servizio HTTP sulla porta {port} di {target_ip} per ottenere banner e headers: curl -v http://{target_ip}:{port}"
                                    else:
                                        # Porta TCP generica: usa nc per ottenere banner
                                        analysis_step = f"Interroga servizio sulla porta {port} di {target_ip} per ottenere banner: nc -v -w 2 {target_ip} {port}"
                                    
                                    # Inserisci step DOPO quello corrente
                                    insert_position = i
                                    steps.insert(insert_position, analysis_step)
                                    log_info(f"[STEP-BY-STEP] ✅ Step analisi servizio inserito alla posizione {insert_position} (porta {port}): {analysis_step}")
                                    emit_progress({
                                        "type": "dynamic_step_generated",
                                        "step_description": analysis_step,
                                        "reason": f"Porta {port}/tcp aperta trovata - analisi automatica servizio",
                                        "inserted_after": i - 1,
                                        "new_total_steps": len(steps),
                                        "port": port
                                    })
                                    
                                    # 🎯 AGGIORNA TASK CONTEXT con porta scoperta
                                    if task_id:
                                        try:
                                            from backend.core.task_context_manager import get_task_context_manager
                                            task_manager = get_task_context_manager()
                                            current_ports = task_manager.get_task(task_id).get('open_ports', []) if task_manager.get_task(task_id) else []
                                            if port not in current_ports:
                                                current_ports.append(port)
                                            task_manager.update_task(task_id, open_ports=current_ports)
                                        except Exception as e:
                                            log_info(f"[TASK-CONTEXT] Errore aggiornamento porte: {e}")
                            
                            # 🔍 RICONOSCIMENTO AUTOMATICO PORTA ADB: Se scansione completa trova porta TCP aperta non standard su Android
                            # Genera dinamicamente step per connessione ADB (logica esistente, ma solo se target è Android)
                            if ('-p-' in step_lower or 'scansione completa' in step_lower or 'tutte le porte' in step_lower) and \
                               ('android' in step_lower or 'adb' in step_lower or 
                                (objective_analysis and 'android' in objective_analysis.get('target_description', '').lower())):
                                
                                # Filtra porte standard (22, 80, 443, 5555, 8080, 8443)
                                standard_ports = ['22', '80', '443', '5555', '8080', '8443', '8008', '8009']
                                non_standard_ports = [p for p in unique_ports if p not in standard_ports]
                                
                                if non_standard_ports:
                                    # Verifica se ci sono già step futuri per ADB
                                    has_adb_step = any('adb' in s.lower() or 'connessione adb' in s.lower() for s in remaining_steps)
                                    
                                    if not has_adb_step:
                                        # Genera step dinamico per connessione ADB
                                        adb_port = non_standard_ports[0]  # Prendi prima porta non standard
                                        adb_step = f"Tenta connessione ADB al dispositivo Android {target_ip} sulla porta {adb_port} scoperta: adb connect {target_ip}:{adb_port}"
                                        
                                        log_info(f"[STEP-BY-STEP] 🔍 Porta TCP non standard {adb_port} trovata su Android. Generazione step ADB dinamico...")
                                        
                                        # Inserisci step DOPO quello corrente
                                        insert_position = i
                                        steps.insert(insert_position, adb_step)
                                        log_info(f"[STEP-BY-STEP] ✅ Step ADB dinamico inserito alla posizione {insert_position} (dopo step {i-1}): {adb_step}")
                                        emit_progress({
                                            "type": "dynamic_step_generated",
                                            "step_description": adb_step,
                                            "reason": f"Porta {adb_port} TCP aperta trovata su dispositivo Android",
                                            "inserted_after": i - 1,
                                            "new_total_steps": len(steps)
                                        })
                                        
                                        # 🎯 AGGIORNA TASK CONTEXT con porta scoperta
                                        if task_id:
                                            try:
                                                from backend.core.task_context_manager import get_task_context_manager
                                                task_manager = get_task_context_manager()
                                                current_ports = task_manager.get_task(task_id).get('open_ports', []) if task_manager.get_task(task_id) else []
                                                if adb_port not in current_ports:
                                                    current_ports.append(adb_port)
                                                task_manager.update_task(task_id, open_ports=current_ports)
                                            except Exception as e:
                                                log_info(f"[TASK-CONTEXT] Errore aggiornamento porte: {e}")
                else:
                    log_info(f"[STEP-BY-STEP] ❌ Step {i} fallito: {result.get('failure_reason', {}).get('type', 'unknown')}")
                    emit_progress({
                        "type": "step_failed",
                        "step_number": i,
                        "error": str(result.get('failure_reason')),
                        "attempts": result['attempts']
                    })
                    
                    # 🗺️ RIANIFICAZIONE DINAMICA: Se un risultato invalida premesse di step futuri
                    should_replan = False
                    failure_type = result.get('failure_reason', {}).get('type', '')
                    step_lower = step.lower()
                    
                    # 🔍 TRIGGER 1: Scansione mirata ADB fallita (porta 5555 chiusa)
                    # Se lo step era una scansione nmap mirata su porta 5555 e non ha trovato porte aperte,
                    # ma l'obiettivo è ancora valido (target Android identificato), triggera scansione completa
                    if ('nmap' in step_lower and '5555' in step_lower and 
                        ('android' in step_lower or 'adb' in step_lower) and
                        failure_type in ['no_output', 'connection_failed', 'unknown']):
                        # Estrai target IP dal contesto o dallo step
                        # Usa regex per estrarre IP
                        target_ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', step)
                        # Verifica se nel contesto c'è menzione di dispositivo Android identificato
                        if target_ips or ('android' in completed_context.lower() or 'xiaomi' in completed_context.lower() or 'samsung' in completed_context.lower()):
                            should_replan = True
                            target_ip = target_ips[0] if target_ips else None
                            log_info(f"[STEP-BY-STEP] 🗺️ Trigger rianificazione: scansione mirata ADB fallita, target Android identificato. Scansione completa necessaria su {target_ip or 'target identificato'}")
                    
                    # 🔍 TRIGGER 2: Porta chiusa quando step futuro la richiede
                    if not should_replan and failure_type == 'connection_failed':
                        # Controlla se step futuri richiedono quella porta
                        remaining_steps = steps[i:] if i < len(steps) else []
                        for future_step in remaining_steps:
                            future_lower = future_step.lower()
                            # Se step futuro richiede ADB ma porta 5555 è chiusa
                            if 'adb' in future_lower and '5555' in completed_context.lower():
                                should_replan = True
                                log_info(f"[STEP-BY-STEP] 🗺️ Trigger rianificazione: porta 5555 chiusa ma step futuro richiede ADB")
                                break
                    
                    if should_replan:
                        try:
                            # generate_deep_steps è già importato in cima al file
                            log_info(f"[STEP-BY-STEP] 🗺️ Rianificazione dinamica in corso...")
                            emit_progress({"type": "replanning", "message": "Rianificazione strategia..."})
                            
                            # Estrai target IP se disponibile
                            target_ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', completed_context + " " + step)
                            target_ip_hint = ""
                            if target_ips:
                                # Prendi l'IP più recente o quello menzionato nello step
                                target_ip_hint = f"\n🎯 TARGET IP IDENTIFICATO: {target_ips[-1]}\n"
                            
                            # Determina se serve scansione completa
                            needs_full_scan = ('nmap' in step_lower and '5555' in step_lower and 
                                             ('android' in step_lower or 'adb' in step_lower))
                            
                            # Genera nuovo piano basato su informazioni aggiornate
                            replan_prompt = f"""
OBIETTIVO ORIGINALE: {prompt}

RISULTATI OTTENUTI FINORA:
{completed_context}
{target_ip_hint}

PROBLEMA: {result.get('failure_reason', {}).get('suggestion', 'Step fallito')}

{"⚠️ SITUAZIONE CRITICA: Scansione mirata su porta 5555 (ADB standard) non ha trovato porte aperte." if needs_full_scan else ""}
{"🎯 STRATEGIA: Il debug wireless Android può usare porte casuali (non solo 5555)." if needs_full_scan else ""}
{"📋 AZIONE RICHIESTA: Esegui una scansione COMPLETA di tutte le porte (-p-) SOLO sul target IP identificato." if needs_full_scan else ""}
{"   Comando suggerito: nmap -p- --open -T4 [TARGET_IP]" if needs_full_scan else ""}
{"   ⚠️ IMPORTANTE: Scansiona SOLO il target specifico, non tutta la rete (altrimenti richiede ore)!" if needs_full_scan else ""}

GENERA UN NUOVO PIANO basato sulle informazioni reali ottenute.
{"Se il target è un dispositivo Android, includi uno step per scansione completa delle porte (-p-) sul target IP." if needs_full_scan else ""}
Focalizzati solo su approcci che sono ancora fattibili.
"""
                            new_steps = generate_deep_steps(replan_prompt)
                            if new_steps and len(new_steps) > 0:
                                # Sostituisci step rimanenti con nuovo piano
                                steps = steps[:i] + new_steps
                                log_info(f"[STEP-BY-STEP] ✅ Nuovo piano generato: {len(new_steps)} step aggiuntivi (totale: {len(steps)})")
                                emit_progress({
                                    "type": "replanned",
                                    "new_steps": new_steps,
                                    "total_steps": len(steps)
                                })
                                # IMPORTANTE: Non incrementare i qui, il loop lo farà automaticamente
                            else:
                                log_info(f"[STEP-BY-STEP] ⚠️ Rianificazione non ha generato nuovi step, continuo con piano originale")
                        except Exception as e:
                            log_info(f"[STEP-BY-STEP] ⚠️ Errore rianificazione: {e}")
                    
                    # STOP se errore critico
                    if result.get('should_stop'):
                        log_info(f"[STEP-BY-STEP] 🛑 Esecuzione interrotta per errore critico")
                        emit_progress({"type": "execution_stopped", "reason": "critical_error"})
                        break
            
            use_old_executor = False
        except Exception as e:
            log_info(f"[STEP-BY-STEP] Errore executor V2, fallback a V1: {e}")
            use_old_executor = True
    else:
        use_old_executor = True
    
    # FALLBACK V1 (codice originale semplificato - mantenuto per compatibilità)
    if use_old_executor:
        log_info("[STEP-BY-STEP] Usando executor V1 (fallback)")
        # ... (codice fallback semplificato se necessario)
        pass
    
    completed_count = len([s for s in step_results if s["status"] == "completato"])
    log_info(f"[STEP-BY-STEP] Esecuzione completata: {completed_count}/{len(steps)} step")
    
    # === SALVATAGGIO IN MEMORIA ===
    try:
        all_ips = []
        all_ports = []
        all_commands = []
        
        for step_result in step_results:
            if step_result["status"] == "completato" and step_result.get("result"):
                result_text = step_result["result"]
                
                # Estrai IP
                ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', result_text)
                all_ips.extend(ips)
                
                # Estrai porte
                ports = re.findall(r'(\d+)/tcp\s+open', result_text)
                all_ports.extend(ports)
                
                # Estrai comandi
                if "Comando:" in result_text:
                    cmd = result_text.split("Comando:")[1].split("\n")[0].strip()
                    if cmd:
                        all_commands.append(cmd)
        
        # Salva summary
        unique_ips = list(set(all_ips))[:15]
        unique_ports = list(set(all_ports))[:10]
        
        memory_summary = f"ESECUZIONE STEP: {prompt}\n\n"
        memory_summary += f"COMPLETATI: {completed_count}/{len(steps)} step\n\n"
        
        if unique_ips:
            memory_summary += f"IP TROVATI: {', '.join(unique_ips)}\n"
        if unique_ports:
            memory_summary += f"PORTE APERTE: {', '.join(unique_ports)}\n"
        if all_commands:
            memory_summary += f"\nCOMANDI ESEGUITI:\n"
            for cmd in all_commands[:5]:
                memory_summary += f"- {cmd}\n"
        
        memory_summary += f"\nSTEP COMPLETATI:\n"
        for sr in step_results:
            if sr["status"] == "completato":
                memory_summary += f"{sr['step_number']}. {sr['step_description']}\n"
        
        add_memory_to_vectordb(
            memory_summary,
            metadata={
                "type": "step_session_summary",
                "objective": prompt[:200],
                "completed": completed_count,
                "total": len(steps),
                "ips_found": len(unique_ips),
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Salva contextual solution
        if completed_count > 0:
            solution_text = f"Completati {completed_count}/{len(steps)} step\n\n"
            
            if unique_ips:
                solution_text += f"IP Identificati: {', '.join(unique_ips[:10])}\n"
            if unique_ports:
                solution_text += f"Porte Aperte: {', '.join(unique_ports[:10])}\n"
            if all_commands:
                solution_text += f"\nComandi Eseguiti:\n" + "\n".join(f"- {cmd}" for cmd in all_commands[:8])
            
            add_contextual_solution(
                title=f"Step Execution: {prompt[:80]}",
                summary=f"{completed_count}/{len(steps)} step | {len(unique_ips)} IP | {len(all_commands)} comandi",
                prompt=prompt,
                solution=solution_text,
                tags=["step-by-step", "automated", f"steps-{len(steps)}", f"ips-{len(unique_ips)}"]
            )
            
            # === ANALISI PLAYBOOK 2.0 (Post-Mortem) ===
            try:
                from backend.core.analysis.playbook_analyzer import playbook_analyzer
                
                log_info(f"[PLAYBOOK] 🧠 Avvio analisi post-mortem per Playbook 2.0...")
                emit_progress({"type": "playbook_analysis", "message": "Analisi successi/fallimenti..."})
                
                analysis_stats = playbook_analyzer.analyze_session(
                    objective=prompt,
                    steps_data=step_results
                )
                
                if analysis_stats.get('success', 0) > 0 or analysis_stats.get('failure', 0) > 0:
                    log_info(f"[PLAYBOOK] ✅ Analisi completata: {analysis_stats.get('success', 0)} successi, {analysis_stats.get('failure', 0)} fallimenti salvati.")
                    emit_progress({
                        "type": "playbook_saved", 
                        "successes": analysis_stats.get('success', 0), 
                        "failures": analysis_stats.get('failure', 0)
                    })
                
            except Exception as e:
                log_info(f"[PLAYBOOK][ERRORE] Analisi playbook fallita: {e}")
        
    except Exception as e:
        log_info(f"[LTM][ERRORE] Salvataggio step in memoria: {e}")
    
    emit_progress({
        "type": "complete",
        "completed": completed_count,
        "total": len(steps),
        "results": step_results
    })
    
    return step_results, completed_count, model

# === UTILITY: PULIZIA TEST ENV ===
def clean_test_env():
    try:
        for item in os.listdir(BASE_TEST_DIR):
            item_path = os.path.join(BASE_TEST_DIR, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        log_info("Directory test_env pulita.")
        return True
    except Exception as e:
        log_info(f"[ERRORE] Pulizia test_env: {e}")
        return False
