from typing import Optional
from backend.core.execution.container_manager import get_container_manager
from backend.core.execution.security import get_security_validator

def execute_python_sandboxed(code: str, network_access: bool = False, target_ip: str = None) -> str:
    """
    Esegue codice Python in modo sicuro (Podman + AST Validation).
    Sostituisce l'esecuzione locale insicura.
    """
    if not code or not code.strip():
        return "[SANDBOX] Errore: Codice vuoto."

    # 1. AST Security Validation
    validator = get_security_validator()
    is_safe, reason = validator.validate_code(code)
    
    if not is_safe:
        return f"[SANDBOX][SECURITY BLOCK] Il codice è stato bloccato dal Validator.\nMotivo: {reason}\n\nRiscrivi il codice evitando import o chiamate proibite."

    # 2. Containerized Execution
    manager = get_container_manager()
    result = manager.run_python_script(code, network_access=network_access, specific_target_ip=target_ip)
    
    if result['status'] == 'success':
        output = f"[SANDBOX STDOUT]\n{result['output']}"
        if result['error']:
            output += f"\n[SANDBOX STDERR]\n{result['error']}"
        return output
    elif result['status'] == 'timeout':
        return f"[SANDBOX] Errore: Timeout esecuzione ({result['error']})"
    else:
        return f"[SANDBOX] Errore Sistema: {result['error']}\nSTDERR: {result.get('error', '')}"

# Wrapper per AutoGen
def execute_python_code_tool(code: str) -> str:
    """
    Esegue codice Python sicuro. 
    L'accesso di rete è disabilitato per default in Fase 1, 
    o abilitato solo se il context manager lo permette (future implementation).
    Per ora default NO NET.
    """
    # TO-DO: Integrare Context Manager per autorizzare network_access=True su target specifici
    return execute_python_sandboxed(code, network_access=False)
