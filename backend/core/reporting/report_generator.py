#!/usr/bin/env python3
"""
Report Generator - Automated Security Findings Documentation
📝 Genera report executive-ready da missioni completate.

Funzionalità:
- Finding creation con risk rating
- Evidence collection
- Executive summary generation
- Export Markdown/HTML
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger('ReportGenerator')

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class RiskLevel(Enum):
    """Livelli di rischio CVSS-aligned"""
    CRITICAL = ("critical", 9.0, "🔴")
    HIGH = ("high", 7.0, "🟠")
    MEDIUM = ("medium", 4.0, "🟡")
    LOW = ("low", 1.0, "🟢")
    INFO = ("info", 0.0, "🔵")
    
    @property
    def label(self):
        return self.value[0]
    
    @property
    def score(self):
        return self.value[1]
    
    @property
    def emoji(self):
        return self.value[2]

@dataclass
class Finding:
    """Rappresenta un finding di sicurezza"""
    id: str
    title: str
    description: str
    risk: RiskLevel
    evidence: List[str]
    remediation: str
    affected_asset: str
    cve_id: Optional[str] = None
    mitre_id: Optional[str] = None
    cvss_score: Optional[float] = None
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['risk'] = self.risk.label
        d['cvss_score'] = self.cvss_score or self.risk.score
        return d
    
    def to_markdown(self) -> str:
        """Formatta finding in Markdown"""
        lines = [
            f"### {self.risk.emoji} {self.title}",
            "",
            f"**Risk Level:** {self.risk.label.upper()} (CVSS: {self.cvss_score or self.risk.score})",
            f"**Affected Asset:** {self.affected_asset}",
        ]
        
        if self.cve_id:
            lines.append(f"**CVE:** {self.cve_id}")
        if self.mitre_id:
            lines.append(f"**MITRE ATT&CK:** {self.mitre_id}")
        
        lines.extend([
            "",
            "**Description:**",
            self.description,
            "",
            "**Evidence:**",
        ])
        
        for ev in self.evidence:
            lines.append(f"```\n{ev}\n```")
        
        lines.extend([
            "",
            "**Remediation:**",
            self.remediation,
            "",
            "---",
        ])
        
        return "\n".join(lines)

@dataclass
class PenetrationTestReport:
    """Report completo di penetration test"""
    report_id: str
    title: str
    target: str
    scope: str
    start_time: str
    end_time: Optional[str] = None
    tester: str = "KaliAI Autonomous System"
    findings: List[Finding] = field(default_factory=list)
    executive_summary: str = ""
    methodology: str = ""
    tools_used: List[str] = field(default_factory=list)
    
    def add_finding(self, finding: Finding):
        self.findings.append(finding)
        # Riordina per risk
        self.findings.sort(key=lambda f: -f.risk.score)
    
    def get_risk_summary(self) -> Dict[str, int]:
        """Conta findings per livello di rischio"""
        summary = {r.label: 0 for r in RiskLevel}
        for f in self.findings:
            summary[f.risk.label] += 1
        return summary

# ============================================================================
# REPORT GENERATOR
# ============================================================================

class ReportGenerator:
    """
    Genera report professionali da missioni KaliAI.
    
    Uso:
        gen = ReportGenerator()
        report = gen.create_report("Pentest Target X", "192.168.1.0/24")
        gen.add_finding(report, "SQL Injection", "...", RiskLevel.HIGH, [...])
        gen.generate_executive_summary(report)
        markdown = gen.export_markdown(report)
    """
    
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or os.path.expanduser("~/kaliAI/reports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._finding_counter = 0
    
    def create_report(
        self,
        title: str,
        target: str,
        scope: str = ""
    ) -> PenetrationTestReport:
        """
        Crea un nuovo report.
        
        Args:
            title: Titolo del report
            target: Target principale
            scope: Descrizione dello scope
        """
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report = PenetrationTestReport(
            report_id=report_id,
            title=title,
            target=target,
            scope=scope or f"Penetration test of {target}",
            start_time=datetime.now().isoformat(),
            methodology="MITRE ATT&CK Framework aligned methodology"
        )
        
        logger.info(f"[ReportGenerator] Report created: {report_id}")
        return report
    
    def add_finding(
        self,
        report: PenetrationTestReport,
        title: str,
        description: str,
        risk: RiskLevel,
        evidence: List[str],
        remediation: str,
        affected_asset: str = None,
        cve_id: str = None,
        mitre_id: str = None
    ) -> Finding:
        """
        Aggiunge un finding al report.
        """
        self._finding_counter += 1
        finding_id = f"FINDING-{self._finding_counter:03d}"
        
        finding = Finding(
            id=finding_id,
            title=title,
            description=description,
            risk=risk,
            evidence=evidence,
            remediation=remediation,
            affected_asset=affected_asset or report.target,
            cve_id=cve_id,
            mitre_id=mitre_id
        )
        
        report.add_finding(finding)
        logger.info(f"[ReportGenerator] Finding added: {title} [{risk.label}]")
        
        return finding
    
    def generate_executive_summary(self, report: PenetrationTestReport) -> str:
        """
        Genera executive summary automatico.
        """
        risk_summary = report.get_risk_summary()
        total = len(report.findings)
        
        # Intro
        lines = [
            f"## Executive Summary",
            "",
            f"A penetration test was conducted against **{report.target}** ",
            f"from {report.start_time[:10]} to {report.end_time[:10] if report.end_time else 'ongoing'}.",
            "",
        ]
        
        # Risk overview
        if total == 0:
            lines.append("No significant security vulnerabilities were identified during this assessment.")
        else:
            critical = risk_summary.get('critical', 0)
            high = risk_summary.get('high', 0)
            
            if critical > 0:
                lines.append(
                    f"⚠️ **{critical} CRITICAL** vulnerabilities were identified that require "
                    f"immediate attention. These issues pose an imminent threat to the security "
                    f"of the target systems."
                )
            
            if high > 0:
                lines.append(
                    f"The assessment also identified **{high} HIGH** severity issues that should "
                    f"be addressed in the near term."
                )
            
            lines.extend([
                "",
                "### Vulnerability Summary",
                "",
                "| Risk Level | Count |",
                "|------------|-------|",
            ])
            
            for risk in RiskLevel:
                count = risk_summary.get(risk.label, 0)
                if count > 0:
                    lines.append(f"| {risk.emoji} {risk.label.upper()} | {count} |")
        
        # Key findings
        if report.findings:
            lines.extend([
                "",
                "### Key Findings",
                "",
            ])
            
            for finding in report.findings[:5]:  # Top 5
                lines.append(f"- {finding.risk.emoji} **{finding.title}** - {finding.affected_asset}")
        
        # Recommendations
        lines.extend([
            "",
            "### Recommendations",
            "",
            "1. Address all CRITICAL vulnerabilities within 24-48 hours",
            "2. Remediate HIGH severity issues within 7 days",
            "3. Schedule remediation for MEDIUM/LOW issues in the next patch cycle",
            "4. Conduct a follow-up assessment after remediation",
        ])
        
        report.executive_summary = "\n".join(lines)
        return report.executive_summary
    
    def export_markdown(self, report: PenetrationTestReport) -> str:
        """
        Esporta report completo in Markdown.
        """
        lines = [
            f"# {report.title}",
            "",
            f"**Report ID:** {report.report_id}",
            f"**Target:** {report.target}",
            f"**Date:** {report.start_time[:10]}",
            f"**Tester:** {report.tester}",
            "",
            "---",
            "",
        ]
        
        # Executive Summary
        if report.executive_summary:
            lines.append(report.executive_summary)
        else:
            lines.append(self.generate_executive_summary(report))
        
        lines.extend([
            "",
            "---",
            "",
            "## Scope",
            "",
            report.scope,
            "",
            "## Methodology",
            "",
            report.methodology,
            "",
        ])
        
        # Tools
        if report.tools_used:
            lines.extend([
                "## Tools Used",
                "",
            ])
            for tool in report.tools_used:
                lines.append(f"- {tool}")
            lines.append("")
        
        # Findings
        lines.extend([
            "---",
            "",
            "## Detailed Findings",
            "",
        ])
        
        for finding in report.findings:
            lines.append(finding.to_markdown())
        
        # Footer
        lines.extend([
            "",
            "---",
            "",
            f"*Report generated by KaliAI on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ])
        
        content = "\n".join(lines)
        
        # Save to file
        filepath = self.output_dir / f"{report.report_id}.md"
        with open(filepath, 'w') as f:
            f.write(content)
        
        logger.info(f"[ReportGenerator] Report exported: {filepath}")
        return content
    
    def export_json(self, report: PenetrationTestReport) -> str:
        """Esporta report in JSON"""
        data = {
            "report_id": report.report_id,
            "title": report.title,
            "target": report.target,
            "scope": report.scope,
            "start_time": report.start_time,
            "end_time": report.end_time,
            "tester": report.tester,
            "executive_summary": report.executive_summary,
            "risk_summary": report.get_risk_summary(),
            "findings": [f.to_dict() for f in report.findings],
            "tools_used": report.tools_used,
        }
        
        filepath = self.output_dir / f"{report.report_id}.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return json.dumps(data, indent=2)

# ============================================================================
# QUICK HELPERS
# ============================================================================

def create_finding_from_output(
    title: str,
    command: str,
    output: str,
    risk: RiskLevel,
    target: str
) -> Finding:
    """
    Helper per creare finding da output di comando.
    """
    return Finding(
        id=f"F-{datetime.now().strftime('%H%M%S')}",
        title=title,
        description=f"Vulnerability discovered via: `{command}`",
        risk=risk,
        evidence=[f"Command: {command}\n\nOutput:\n{output}"],
        remediation="See vendor documentation for patching guidance.",
        affected_asset=target
    )

# ============================================================================
# SINGLETON
# ============================================================================

_generator_instance: Optional[ReportGenerator] = None

def get_report_generator() -> ReportGenerator:
    """Restituisce istanza singleton"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = ReportGenerator()
    return _generator_instance
