import networkx as nx
import logging
import socket
import uuid
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger('GraphMemory')

class GraphMemory:
    """
    Rappresentazione a Grafo della Network (The Map).
    Usa NetworkX per tracciare host, porte e relazioni e IMPORRE LO SCOPE.
    
    Features:
    - Run scoping: each run gets a unique run_id
    - Environment fingerprinting: detects current network environment
    - Memory isolation: prevents old data from leaking into new runs
    """
    def __init__(self, auto_detect_env: bool = True):
        self.graph = nx.DiGraph()
        self.scope_subnets = []  # Elenco di subnet/IP autorizzati
        
        # Run scoping
        self.run_id = str(uuid.uuid4())[:8]
        self.env_fingerprint = self._detect_environment() if auto_detect_env else "unknown"
        
        logger.info(f"[GRAPH] New GraphMemory instance: run_id={self.run_id}, env={self.env_fingerprint}")
    
    def _detect_environment(self) -> str:
        """Detect current network environment fingerprint."""
        try:
            hostname = socket.gethostname()
            # Get primary IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            s.close()
            # Extract subnet (first 3 octets)
            subnet = ".".join(primary_ip.split(".")[:3])
            return f"{hostname}:{subnet}"
        except Exception as e:
            logger.warning(f"[GRAPH] Could not detect environment: {e}")
            return "unknown"
    
    def new_run(self):
        """Start a new run, clearing graph and generating new run_id."""
        self.run_id = str(uuid.uuid4())[:8]
        self.graph.clear()
        self.env_fingerprint = self._detect_environment()
        logger.info(f"[GRAPH] New run started: run_id={self.run_id}, env={self.env_fingerprint}")
    
    def set_scope(self, scope_list: List[str]):
        """Definisce il perimetro di ingaggio (ROE)."""
        self.scope_subnets = scope_list
        logger.info(f"[GRAPH] Scope impostato: {self.scope_subnets}")

    def is_in_scope(self, ip_address: str) -> bool:
        """
        Verifica se un IP è dentro lo scope autorizzato.
        """
        if not self.scope_subnets:
            return False  # Fail safe: se scope vuoto, blocca tutto
            
        for scope in self.scope_subnets:
            if scope == "0.0.0.0/0" or scope == "*":
                return True  # Unrestricted (Dangerous)
            if ip_address == scope or ip_address.startswith(scope):
                return True
        return False

    def add_host(self, ip: str, metadata: Dict[str, Any] = None):
        """Aggiunge un host al grafo con run metadata."""
        if not self.is_in_scope(ip):
            logger.warning(f"[GRAPH] Tentativo di aggiungere host fuori scope: {ip} - IGNORATO")
            return
        
        # Create unique node ID with run context
        node_id = f"host:{ip}"
        
        node_data = {
            "type": "host",
            "ip": ip,
            "_run_id": self.run_id,
            "_env": self.env_fingerprint,
            **(metadata or {})
        }
        
        if not self.graph.has_node(node_id):
            self.graph.add_node(node_id, **node_data)
            logger.info(f"[GRAPH] Host aggiunto: {ip} (run={self.run_id})")
        else:
            # Update metadata
            self.graph.nodes[node_id].update(node_data)

    def add_service(self, ip: str, port: int, protocol: str = "tcp", service_name: str = "unknown"):
        """Aggiunge un servizio collegato a un host."""
        host_node_id = f"host:{ip}"
        
        if not self.graph.has_node(host_node_id):
            self.add_host(ip)
            if not self.graph.has_node(host_node_id):
                return  # Fuori scope
        
        service_node_id = f"service:{ip}:{port}"
        if not self.graph.has_node(service_node_id):
            self.graph.add_node(service_node_id, 
                type="service", 
                ip=ip,
                port=port, 
                protocol=protocol, 
                service=service_name,
                _run_id=self.run_id,
                _env=self.env_fingerprint
            )
            self.graph.add_edge(host_node_id, service_node_id, relation="exposes")
            logger.info(f"[GRAPH] Servizio rilevato: {ip}:{port} (run={self.run_id})")

    def get_summary(self, scope: str = "current_run") -> str:
        """
        Restituisce un sommario testuale della topologia scoperta.
        
        Args:
            scope: "current_run" (default), "current_env", or "all"
        """
        # Filter nodes based on scope
        if scope == "current_run":
            nodes = [n for n, attr in self.graph.nodes(data=True) 
                    if attr.get('_run_id') == self.run_id]
        elif scope == "current_env":
            nodes = [n for n, attr in self.graph.nodes(data=True) 
                    if attr.get('_env') == self.env_fingerprint]
        else:
            nodes = list(self.graph.nodes())
        
        hosts = [n for n in nodes if self.graph.nodes[n].get('type') == 'host']
        
        summary = f"[GRAPH] Knowledge Graph Snapshot\n"
        summary += f"Nodi totali: {len(nodes)}, Relazioni totali: {len(self.graph.edges())}\n"
        summary += f"Run ID: {self.run_id}, Env: {self.env_fingerprint}\n\n"
        summary += "-- NODI --\n"
        
        for node in nodes[:20]:  # Limit to 20 nodes
            attr = self.graph.nodes[node]
            node_type = attr.get('type', 'unknown')
            summary += f"{node} ({node_type}): {dict((k,v) for k,v in attr.items() if not k.startswith('_'))}\n"
        
        if len(nodes) > 20:
            summary += f"... e altri {len(nodes) - 20} nodi\n"
        
        summary += "\n-- RELAZIONI RECENTI --\n"
        for u, v, data in list(self.graph.edges(data=True))[:10]:
            summary += f"{u} -> {v}: {data.get('relation', 'unknown')}\n"
        
        return summary

# Singleton
_graph_memory = GraphMemory()

def get_graph_memory():
    return _graph_memory

def reset_graph_memory():
    """Reset graph for new run."""
    global _graph_memory
    _graph_memory.new_run()
    return _graph_memory
