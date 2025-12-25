#!/usr/bin/env python3
"""
Case File Format - Struttura standard per log di hacking e CTF write-ups
"""
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
import json

@dataclass
class AttackPhase:
    """Fase di un attacco"""
    phase_name: str  # 'reconnaissance', 'exploitation', 'privilege_escalation', ecc.
    description: str
    commands: List[Dict[str, str]]  # [{'command': 'nmap...', 'result': '...', 'context': '...'}]
    findings: List[str]
    timestamp: Optional[str] = None

@dataclass
class Vulnerability:
    """Vulnerabilità identificata"""
    cve_id: Optional[str]
    name: str
    description: str
    severity: Optional[str]  # 'critical', 'high', 'medium', 'low'
    affected_version: Optional[str]
    exploit_available: bool = False

@dataclass
class CaseFile:
    """Case file completo per un attacco/CTF"""
    # Identificazione
    case_id: str
    title: str
    platform: str  # 'hack_the_box', 'tryhackme', 'vulnhub', 'real_world', ecc.
    target_name: Optional[str]  # Nome macchina/obiettivo
    target_ip: Optional[str]
    
    # Obiettivo
    objective: str
    
    # Fasi dell'attacco
    phases: List[AttackPhase]
    
    # Vulnerabilità
    vulnerabilities: List[Vulnerability]
    
    # Comandi chiave (riepilogo)
    key_commands: List[str]
    
    # Lezioni apprese
    lessons_learned: List[str]
    
    # Metadati
    source_url: Optional[str]
    author: Optional[str]
    date_completed: Optional[str]
    difficulty: Optional[str]  # 'easy', 'medium', 'hard', 'insane'
    
    # Contenuto completo (opzionale)
    full_content: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Converte in dizionario"""
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        """Converte in JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def to_markdown(self) -> str:
        """Converte in Markdown"""
        md = f"""# {self.title}

## Case Information
- **Case ID**: {self.case_id}
- **Platform**: {self.platform}
- **Target**: {self.target_name or 'N/A'}
- **IP**: {self.target_ip or 'N/A'}
- **Difficulty**: {self.difficulty or 'N/A'}
- **Date**: {self.date_completed or 'N/A'}

## Objective
{self.objective}

## Attack Phases

"""
        
        for phase in self.phases:
            md += f"### {phase.phase_name.replace('_', ' ').title()}\n\n"
            md += f"{phase.description}\n\n"
            
            if phase.commands:
                md += "**Commands:**\n\n"
                for cmd in phase.commands:
                    md += f"```bash\n{cmd['command']}\n```\n"
                    if cmd.get('result'):
                        md += f"Result: {cmd['result'][:200]}...\n\n"
            
            if phase.findings:
                md += "**Findings:**\n\n"
                for finding in phase.findings:
                    md += f"- {finding}\n"
            
            md += "\n"
        
        if self.vulnerabilities:
            md += "## Vulnerabilities Identified\n\n"
            for vuln in self.vulnerabilities:
                md += f"### {vuln.name}\n\n"
                if vuln.cve_id:
                    md += f"- **CVE**: {vuln.cve_id}\n"
                md += f"- **Description**: {vuln.description}\n"
                if vuln.severity:
                    md += f"- **Severity**: {vuln.severity}\n"
                if vuln.affected_version:
                    md += f"- **Affected Version**: {vuln.affected_version}\n"
                md += f"- **Exploit Available**: {'Yes' if vuln.exploit_available else 'No'}\n\n"
        
        if self.key_commands:
            md += "## Key Commands\n\n"
            for cmd in self.key_commands:
                md += f"- `{cmd}`\n"
            md += "\n"
        
        if self.lessons_learned:
            md += "## Lessons Learned\n\n"
            for lesson in self.lessons_learned:
                md += f"- {lesson}\n"
            md += "\n"
        
        if self.source_url:
            md += f"## Source\n\n{self.source_url}\n"
        
        if self.full_content:
            md += f"\n## Full Content\n\n{self.full_content[:2000]}...\n"
        
        return md
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CaseFile':
        """Crea CaseFile da dizionario"""
        # Converti phases
        phases = []
        for phase_data in data.get('phases', []):
            phases.append(AttackPhase(**phase_data))
        
        # Converti vulnerabilities
        vulnerabilities = []
        for vuln_data in data.get('vulnerabilities', []):
            vulnerabilities.append(Vulnerability(**vuln_data))
        
        return cls(
            case_id=data['case_id'],
            title=data['title'],
            platform=data['platform'],
            target_name=data.get('target_name'),
            target_ip=data.get('target_ip'),
            objective=data['objective'],
            phases=phases,
            vulnerabilities=vulnerabilities,
            key_commands=data.get('key_commands', []),
            lessons_learned=data.get('lessons_learned', []),
            source_url=data.get('source_url'),
            author=data.get('author'),
            date_completed=data.get('date_completed'),
            difficulty=data.get('difficulty'),
            full_content=data.get('full_content')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CaseFile':
        """Crea CaseFile da JSON"""
        return cls.from_dict(json.loads(json_str))

def create_case_file_from_writeup(
    title: str,
    platform: str,
    content: str,
    commands: List[Dict],
    phases: List[Dict],
    vulnerabilities: List[str],
    source_url: Optional[str] = None
) -> CaseFile:
    """Crea CaseFile da un write-up processato"""
    
    # Estrai informazioni base
    case_id = f"{platform}_{title.lower().replace(' ', '_')}"
    target_name = title.split('-')[0].strip() if '-' in title else None
    
    # Converti phases
    attack_phases = []
    for phase_data in phases:
        attack_phases.append(AttackPhase(
            phase_name=phase_data.get('phase', 'unknown'),
            description=phase_data.get('content', '')[:500],
            commands=phase_data.get('commands', []),
            findings=phase_data.get('findings', [])
        ))
    
    # Converti vulnerabilities
    vuln_list = []
    for vuln_str in vulnerabilities:
        vuln_list.append(Vulnerability(
            cve_id=vuln_str if 'CVE-' in vuln_str else None,
            name=vuln_str,
            description=f"Vulnerability: {vuln_str}",
            severity=None,
            affected_version=None,
            exploit_available=False
        ))
    
    # Estrai key commands
    key_commands = [cmd.get('command', cmd) if isinstance(cmd, dict) else cmd for cmd in commands[:10]]
    
    # Estrai lessons (semplificato)
    lessons = [
        f"Identified {len(vulnerabilities)} vulnerabilities",
        f"Used {len(commands)} commands during attack"
    ]
    
    return CaseFile(
        case_id=case_id,
        title=title,
        platform=platform,
        target_name=target_name,
        target_ip=None,
        objective=f"Obtain root access on {target_name or 'target'}",
        phases=attack_phases,
        vulnerabilities=vuln_list,
        key_commands=key_commands,
        lessons_learned=lessons,
        source_url=source_url,
        author=None,
        date_completed=datetime.now().isoformat(),
        difficulty=None,
        full_content=content
    )


