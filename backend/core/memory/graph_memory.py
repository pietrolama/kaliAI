import networkx as nx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger('GraphMemory')

class GraphMemory:
    """
    Rappresentazione a Grafo della Network (The Map).
    Usa NetworkX per tracciare host, porte e relazioni e IMPORRE LO SCOPE.
    """
    def __init__(self):
        self.graph = nx.DiGraph()
        self.scope_subnets = [] # Elenco di subnet/IP autorizzati (CIDR o str)

    def set_scope(self, scope_list: List[str]):
        """Definisce il perimetro di ingaggio (ROE)."""
        self.scope_subnets = scope_list
        logger.info(f"[GRAPH] Scope impostato: {self.scope_subnets}")

    def is_in_scope(self, ip_address: str) -> bool:
        """
        Verifica se un IP è dentro lo scope autorizzato.
        Implementazione base: check stringa esatta o startswith (TODO: ipaddress lib per CIDR).
        """
        if not self.scope_subnets:
            return False # Fail safe: se scope vuoto, blocca tutto
            
        for scope in self.scope_subnets:
            if scope == "0.0.0.0/0" or scope == "*":
                return True # Unrestricted (Dangerous)
            if ip_address == scope or ip_address.startswith(scope):
                return True
        return False

    def add_host(self, ip: str, metadata: Dict[str, Any] = None):
        """Aggiunge un host al grafo."""
        if not self.is_in_scope(ip):
            logger.warning(f"[GRAPH] Tentativo di aggiungere host fuori scope: {ip} - IGNORATO")
            return
            
        if not self.graph.has_node(ip):
            self.graph.add_node(ip, type="host", **(metadata or {}))
            logger.info(f"[GRAPH] Host aggiunto: {ip}")
        else:
            # Update metadata
            if metadata:
                self.graph.nodes[ip].update(metadata)

    def add_service(self, ip: str, port: int, protocol: str = "tcp", service_name: str = "unknown"):
        """Aggiunge un servizio collegato a un host."""
        if not self.graph.has_node(ip):
            self.add_host(ip) # Prova ad aggiungere se in scope
            if not self.graph.has_node(ip): return # Se fallisce (fuori scope), esci
            
        service_node = f"{ip}:{port}"
        if not self.graph.has_node(service_node):
            self.graph.add_node(service_node, type="service", port=port, protocol=protocol, service=service_name)
            self.graph.add_edge(ip, service_node, relation="exposes")
            logger.info(f"[GRAPH] Servizio rilevato: {service_node}")

    def get_summary(self) -> str:
        """Restituisce un sommario testuale della topologia scoperta."""
        hosts = [n for n, attr in self.graph.nodes(data=True) if attr.get('type') == 'host']
        summary = f"Network Graph: {len(hosts)} Active Hosts\n"
        for host in hosts:
            services = [v for u, v in self.graph.out_edges(host)]
            summary += f"- Host: {host} (Services: {len(services)})\n"
            for svc in services:
                # Estrai info porta
                port_data = self.graph.nodes[svc]
                summary += f"  L Port {port_data.get('port')}/{port_data.get('protocol')} ({port_data.get('service')})\n"
        return summary

# Singleton
_graph_memory = GraphMemory()
def get_graph_memory():
    return _graph_memory
