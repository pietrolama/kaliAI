import ast
import logging

logger = logging.getLogger('SecurityValidator')

class SecurityValidator:
    """
    Validatore statico del codice (The Gatekeeper).
    Usa AST per bloccare operazioni proibite prima dell'esecuzione.
    """
    
    PROHIBITED_IMPORTS = [
        'os.system', 'subprocess', 'pty', 'tty', 
        'platform', 'ctypes', 'tkinter'
    ]
    
    PROHIBITED_CALLS = [
        'system', 'popen', 'spawn', 'fork', 'exec', 
        'eval', 'execfile'
    ]
    
    UNSAFE_PATHS = [
        '/etc/passwd', '/etc/shadow', '/root', '/var/run/docker.sock'
    ]

    def validate_code(self, code: str) -> tuple[bool, str]:
        """
        Analizza il codice Python.
        Return: (is_safe: bool, reason: str)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"

        for node in ast.walk(tree):
            # 1. Controllo Import
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if self._is_prohibited_module(alias.name):
                        return False, f"Prohibited module import: {alias.name}"

            # 2. Controllo Chiamate Funzioni
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.PROHIBITED_CALLS:
                        return False, f"Prohibited function call: {node.func.id}"
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.PROHIBITED_CALLS:
                        return False, f"Prohibited method call: {node.func.attr}"

            # 3. Controllo Stringhe (Path sensibili)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for path in self.UNSAFE_PATHS:
                    if path in node.value:
                        return False, f"Prohibited path string: {path}"

        return True, "Code is safe"

    def _is_prohibited_module(self, module_name):
        return any(proh in module_name for proh in self.PROHIBITED_IMPORTS)

# Singleton
_security_validator = SecurityValidator()
def get_security_validator():
    return _security_validator
