#!/usr/bin/env python3
"""
Knowledge Graph manager per KaliAI.
Memorizza host, servizi e relazioni per abilitare ragionamento laterale.
"""

import os
import json
import time
from collections import deque
from threading import RLock
from typing import Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_PATH = os.path.join(PROJECT_ROOT, "data")
GRAPH_DIR = os.path.join(DATA_PATH, "graph")
GRAPH_PATH = os.path.join(GRAPH_DIR, "knowledge_graph.json")

_graph_lock = RLock()
_graph_data = None  # Lazy load


def _default_graph():
    return {
        "nodes": {},  # node_id -> {"label": str, "attributes": {...}, "updated_at": ts}
        "edges": [],  # list of {"source": str, "target": str, "relation": str, "metadata": {...}, "timestamp": ts}
        "version": 1
    }


def _load_graph():
    global _graph_data
    if _graph_data is not None:
        return
    os.makedirs(GRAPH_DIR, exist_ok=True)
    if os.path.exists(GRAPH_PATH):
        try:
            with open(GRAPH_PATH, "r", encoding="utf-8") as f:
                _graph_data = json.load(f)
        except Exception:
            _graph_data = _default_graph()
    else:
        _graph_data = _default_graph()


def _save_graph():
    if _graph_data is None:
        return
    os.makedirs(GRAPH_DIR, exist_ok=True)
    tmp_path = GRAPH_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(_graph_data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, GRAPH_PATH)


def _upsert_node(node_id: str, label: str, attributes: Optional[Dict] = None):
    if not node_id:
        return
    _load_graph()
    with _graph_lock:
        node = _graph_data["nodes"].get(node_id, {"label": label, "attributes": {}, "updated_at": 0})
        if attributes:
            node["attributes"].update({k: v for k, v in attributes.items() if v is not None})
        node["label"] = label or node.get("label", "entity")
        node["updated_at"] = time.time()
        _graph_data["nodes"][node_id] = node
        _save_graph()


def _add_edge(source: str, relation: str, target: str, metadata: Optional[Dict] = None):
    if not source or not target or not relation:
        return
    _load_graph()
    metadata = metadata or {}
    with _graph_lock:
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
            "metadata": metadata,
            "timestamp": time.time()
        }
        _graph_data["edges"].append(edge)
        # Limita edges per evitare crescita infinita
        if len(_graph_data["edges"]) > 2000:
            _graph_data["edges"] = _graph_data["edges"][-2000:]
        _save_graph()


def record_host_observation(ip: str, hostname: Optional[str] = None, vendor: Optional[str] = None,
                            mac: Optional[str] = None, source: Optional[str] = None):
    if not ip:
        return
    attributes = {
        "hostname": hostname,
        "vendor": vendor,
        "mac": mac,
        "sources": _merge_source(ip, source)
    }
    _upsert_node(f"host:{ip}", "Host", attributes)


def _merge_source(node_key: str, source: Optional[str]):
    if _graph_data is None:
        _load_graph()
    nodes = _graph_data["nodes"]
    existing = nodes.get(node_key, {}).get("attributes", {}).get("sources", [])
    if source and source not in existing:
        existing.append(source)
    return existing


def record_port_observation(ip: str, port: int, protocol: str = "tcp", service: Optional[str] = None,
                            metadata: Optional[Dict] = None):
    if not ip or port is None:
        return
    protocol = (protocol or "tcp").lower()
    service = service or "unknown"
    host_node = f"host:{ip}"
    port_node = f"service:{ip}:{port}/{protocol}"
    _upsert_node(host_node, "Host")
    _upsert_node(port_node, "Service", {"port": port, "protocol": protocol, "service": service})
    _add_edge(host_node, "HAS_PORT", port_node, metadata)


def record_relationship(source_node: str, relation: str, target_node: str, metadata: Optional[Dict] = None):
    _add_edge(source_node, relation, target_node, metadata)


def get_graph_summary_text(limit_nodes: int = 15, limit_edges: int = 25) -> str:
    _load_graph()
    with _graph_lock:
        nodes = list(_graph_data["nodes"].items())[:limit_nodes]
        edges = _graph_data["edges"][-limit_edges:]

    summary = ["[GRAPH] Knowledge Graph Snapshot"]
    summary.append(f"Nodi totali: {len(_graph_data['nodes'])}, Relazioni totali: {len(_graph_data['edges'])}")
    summary.append("\n-- NODI --")
    for node_id, data in nodes:
        attrs = data.get("attributes", {})
        summary.append(f"{node_id} ({data.get('label')}): {attrs}")
    summary.append("\n-- RELAZIONI RECENTI --")
    for edge in edges:
        summary.append(f"{edge['source']} -[{edge['relation']}]-> {edge['target']} | {edge.get('metadata', {})}")
    return "\n".join(summary)


def find_paths_between_hosts(source_ip: str, target_ip: str, max_depth: int = 4, max_paths: int = 3) -> str:
    source_node = f"host:{source_ip}"
    target_node = f"host:{target_ip}"
    _load_graph()

    if source_node not in _graph_data["nodes"]:
        return f"[GRAPH] Host sorgente non presente nel grafo: {source_ip}"
    if target_node not in _graph_data["nodes"]:
        return f"[GRAPH] Host destinazione non presente nel grafo: {target_ip}"

    adjacency = {}
    for edge in _graph_data["edges"]:
        adjacency.setdefault(edge["source"], []).append((edge["target"], edge["relation"], edge.get("metadata", {})))

    paths = []
    queue = deque([(source_node, [source_node])])
    visited = {source_node}

    while queue and len(paths) < max_paths:
        current, path = queue.popleft()
        if len(path) > max_depth + 1:
            continue
        for neighbor, relation, metadata in adjacency.get(current, []):
            if neighbor in path:
                continue
            new_path = path + [f"{relation}:{neighbor}"]
            if neighbor == target_node:
                paths.append(new_path)
                if len(paths) >= max_paths:
                    break
            else:
                queue.append((neighbor, path + [neighbor]))

    if not paths:
        return "[GRAPH] Nessun percorso trovato tra gli host."

    formatted = ["[GRAPH] Percorsi trovati:"]
    for idx, p in enumerate(paths, 1):
        formatted.append(f"Percorso {idx}: " + " -> ".join(p))
    return "\n".join(formatted)

