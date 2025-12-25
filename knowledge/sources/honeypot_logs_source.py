#!/usr/bin/env python3
"""
Honeypot Logs Source - Integrazione log da honeypot (T-Pot, ecc.)
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class HoneypotLogsSource(DataSource):
    """Source per log da honeypot"""
    
    def __init__(self, enabled: bool = True, log_path: Optional[str] = None):
        super().__init__('honeypot_logs', enabled)
        self.log_path = Path(log_path) if log_path else Path(__file__).parent.parent.parent / 'data' / 'honeypot_logs'
        self.log_path = Path(self.log_path)
    
    def fetch(self, max_logs: int = 100) -> List[SourceResult]:
        """
        Fetcha log da honeypot.
        
        Args:
            max_logs: Numero massimo di log da processare
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            if not self.log_path.exists():
                print(f"[Honeypot Logs] Directory non trovata: {self.log_path}")
                print(f"[Honeypot Logs] Crea la directory e aggiungi file JSON di log T-Pot")
                return []
            
            # Cerca file JSON (formato T-Pot)
            json_files = list(self.log_path.glob('*.json'))
            
            if not json_files:
                print(f"[Honeypot Logs] Nessun file JSON trovato in {self.log_path}")
                return []
            
            print(f"[Honeypot Logs] Trovati {len(json_files)} file log")
            
            for json_file in json_files[:max_logs]:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        log_data = json.load(f)
                    
                    # Processa log (formato dipende da T-Pot/honeypot)
                    log_results = self._process_log(log_data, json_file.name)
                    results.extend(log_results)
                    
                except Exception as e:
                    print(f"[Honeypot Logs] Errore processando {json_file}: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[Honeypot Logs] ✅ Processati {len(results)} log entries")
            
        except Exception as e:
            self.error_count += 1
            print(f"[Honeypot Logs] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _process_log(self, log_data: Dict, filename: str) -> List[SourceResult]:
        """Processa un singolo log entry"""
        results = []
        
        try:
            # Estrai informazioni comuni da log honeypot
            timestamp = log_data.get('timestamp', datetime.now().isoformat())
            source_ip = log_data.get('src_ip', log_data.get('ip', 'unknown'))
            destination_port = log_data.get('dst_port', log_data.get('port', 'unknown'))
            service = log_data.get('service', log_data.get('honeypot', 'unknown'))
            
            # Estrai payload/attacco
            payload = log_data.get('payload', log_data.get('data', ''))
            command = log_data.get('command', '')
            username = log_data.get('username', '')
            password = log_data.get('password', '')
            
            # Costruisci contenuto
            content = f"""
Honeypot Attack Log

TIMESTAMP: {timestamp}
SOURCE IP: {source_ip}
DESTINATION PORT: {destination_port}
SERVICE: {service}

ATTACK DETAILS:
"""
            
            if payload:
                content += f"Payload: {payload[:500]}\n"
            
            if command:
                content += f"Command: {command}\n"
            
            if username:
                content += f"Username Attempt: {username}\n"
            
            if password:
                content += f"Password Attempt: {password}\n"
            
            # Estrai pattern comuni
            attack_type = self._classify_attack(log_data)
            content += f"\nATTACK TYPE: {attack_type}\n"
            
            # Lezioni apprese
            lessons = self._extract_lessons(log_data)
            if lessons:
                content += f"\nOBSERVATIONS:\n{lessons}\n"
            
            results.append(SourceResult(
                title=f"Honeypot Attack - {service} on port {destination_port}",
                content=content.strip(),
                source_type='honeypot_log',
                source_name='honeypot_logs',
                url=None,
                metadata={
                    'source_ip': source_ip,
                    'destination_port': str(destination_port),
                    'service': service,
                    'attack_type': attack_type,
                    'timestamp': timestamp,
                    'log_file': filename
                },
                timestamp=datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else datetime.now(),
                relevance_score=0.8
            ))
            
        except Exception as e:
            print(f"[Honeypot Logs] Errore processando log entry: {e}")
        
        return results
    
    def _classify_attack(self, log_data: Dict) -> str:
        """Classifica tipo di attacco"""
        service = str(log_data.get('service', '')).lower()
        payload = str(log_data.get('payload', '')).lower()
        command = str(log_data.get('command', '')).lower()
        
        # Classificazione basata su pattern
        if 'ssh' in service or '22' in str(log_data.get('dst_port', '')):
            if log_data.get('username') or log_data.get('password'):
                return 'SSH Brute Force'
            return 'SSH Connection Attempt'
        
        if 'ftp' in service or '21' in str(log_data.get('dst_port', '')):
            return 'FTP Attack'
        
        if 'http' in service or '80' in str(log_data.get('dst_port', '')) or '443' in str(log_data.get('dst_port', '')):
            if 'sql' in payload or 'union' in payload:
                return 'SQL Injection'
            if '<script' in payload or 'javascript' in payload:
                return 'XSS Attempt'
            return 'HTTP Attack'
        
        if 'telnet' in service or '23' in str(log_data.get('dst_port', '')):
            return 'Telnet Attack'
        
        if 'mysql' in service or '3306' in str(log_data.get('dst_port', '')):
            return 'MySQL Attack'
        
        return 'Unknown Attack'
    
    def _extract_lessons(self, log_data: Dict) -> str:
        """Estrae lezioni/pattern dal log"""
        lessons = []
        
        # Pattern comuni
        if log_data.get('username'):
            lessons.append(f"Brute force attempt with username: {log_data.get('username')}")
        
        if log_data.get('password'):
            lessons.append(f"Password attempt detected (common/default password?)")
        
        payload = str(log_data.get('payload', ''))
        if len(payload) > 100:
            lessons.append(f"Large payload detected ({len(payload)} bytes)")
        
        # Comandi sospetti
        command = log_data.get('command', '')
        if command:
            suspicious_cmds = ['rm ', 'wget', 'curl', 'nc ', 'bash', 'sh -c']
            if any(cmd in command.lower() for cmd in suspicious_cmds):
                lessons.append(f"Suspicious command: {command[:100]}")
        
        return '\n'.join(f"- {lesson}" for lesson in lessons[:5])
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'honeypot_logs',
            'url': None,
            'description': 'Honeypot attack logs (T-Pot format)',
            'rate_limit': None,
            'requires_auth': False,
            'log_path': str(self.log_path)
        }


