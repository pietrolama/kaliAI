"""
Sentinel - Threat Intelligence Orchestration Engine

Coordinates intelligence gathering from multiple sources,
normalizes data, calculates priorities, and persists to storage.

The "eyes and ears" of KaliAI for threat awareness.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from backend.core.intel.models import VulnArtifact, IntelReport, VulnStatus

logger = logging.getLogger('Sentinel')

# Storage path for intel data
INTEL_DATA_DIR = Path("data/intel")
INTEL_DATA_DIR.mkdir(parents=True, exist_ok=True)

# File paths
VULNS_FILE = INTEL_DATA_DIR / "vulnerabilities.jsonl"
REPORTS_FILE = INTEL_DATA_DIR / "intel_reports.jsonl"


class Sentinel:
    """
    Threat Intelligence coordination engine.
    
    Responsibilities:
    - Fetch intel from sources (CISA, NVD, ExploitDB)
    - Normalize to VulnArtifact format
    - Calculate priorities
    - Deduplicate and merge
    - Persist to storage
    """
    
    def __init__(self):
        self._known_cves: Dict[str, VulnArtifact] = {}
        self._load_existing()
    
    def _load_existing(self):
        """Load existing vulnerability data from disk."""
        if VULNS_FILE.exists():
            try:
                with open(VULNS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                vuln = VulnArtifact.from_dict(data)
                                self._known_cves[vuln.cve_id] = vuln
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.warning(f"Skipping invalid entry: {e}")
                logger.info(f"Loaded {len(self._known_cves)} existing CVEs from storage")
            except Exception as e:
                logger.error(f"Failed to load existing vulns: {e}")
    
    def _save_vuln(self, vuln: VulnArtifact):
        """Append vulnerability to JSONL storage."""
        with open(VULNS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(vuln.to_dict(), ensure_ascii=False) + "\n")
    
    def _save_report(self, report: IntelReport):
        """Append intel report to log."""
        with open(REPORTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(report.to_dict(), ensure_ascii=False) + "\n")
    
    def ingest_vulns(self, vulns: List[VulnArtifact]) -> Dict[str, int]:
        """
        Ingest vulnerabilities, deduplicating against known CVEs.
        
        Returns:
            Dict with new_count, updated_count, skipped_count
        """
        stats = {"new": 0, "updated": 0, "skipped": 0}
        
        for vuln in vulns:
            if vuln.cve_id in self._known_cves:
                existing = self._known_cves[vuln.cve_id]
                
                # Update if new info is better (higher risk or more sources)
                if vuln.risk_score > existing.risk_score or len(vuln.sources) > len(existing.sources):
                    self._known_cves[vuln.cve_id] = vuln
                    self._save_vuln(vuln)
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                # New CVE
                self._known_cves[vuln.cve_id] = vuln
                self._save_vuln(vuln)
                stats["new"] += 1
        
        return stats
    
    def run_cisa_cycle(self) -> IntelReport:
        """
        Run CISA KEV intelligence cycle.
        
        Returns:
            IntelReport with summary
        """
        from backend.knowledge.sources.cisa import fetch_cisa_kev
        
        logger.info("[SENTINEL] Starting CISA KEV intelligence cycle...")
        
        vulns, report = fetch_cisa_kev()
        
        if vulns:
            # Ingest with deduplication
            stats = self.ingest_vulns(vulns)
            report.new_count = stats["new"]
            report.updated_count = stats["updated"]
            
            # Count criticals
            report.critical_count = sum(1 for v in vulns if v.risk_score >= 100)
        
        # Save report
        self._save_report(report)
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _print_summary(self, report: IntelReport):
        """Print human-readable summary."""
        logger.info("=" * 60)
        logger.info(f"[SENTINEL] Intelligence Cycle Complete: {report.source}")
        logger.info(f"  Total fetched: {report.total_fetched}")
        logger.info(f"  New CVEs: {report.new_count}")
        logger.info(f"  Updated: {report.updated_count}")
        logger.info(f"  Critical (≥100): {report.critical_count}")
        if report.errors:
            logger.warning(f"  Errors: {len(report.errors)}")
            for err in report.errors[:5]:  # Show first 5
                logger.warning(f"    - {err}")
        logger.info("=" * 60)
    
    def get_critical_vulns(self, limit: int = 20) -> List[VulnArtifact]:
        """Get highest priority vulnerabilities."""
        vulns = list(self._known_cves.values())
        vulns.sort(key=lambda v: v.risk_score, reverse=True)
        return vulns[:limit]
    
    def get_ransomware_vulns(self) -> List[VulnArtifact]:
        """Get vulnerabilities associated with ransomware."""
        return [v for v in self._known_cves.values() if v.known_ransomware]
    
    def search_vulns(self, query: str) -> List[VulnArtifact]:
        """Search vulnerabilities by CVE ID, title, or product."""
        query_lower = query.lower()
        results = []
        
        for vuln in self._known_cves.values():
            if (query_lower in vuln.cve_id.lower() or 
                query_lower in vuln.title.lower() or
                query_lower in str(vuln.technical_data.get("vendor", "")).lower() or
                query_lower in str(vuln.technical_data.get("product", "")).lower()):
                results.append(vuln)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall intel statistics."""
        vulns = list(self._known_cves.values())
        return {
            "total_cves": len(vulns),
            "critical_count": sum(1 for v in vulns if v.risk_score >= 100),
            "high_count": sum(1 for v in vulns if 70 <= v.risk_score < 100),
            "ransomware_count": sum(1 for v in vulns if v.known_ransomware),
            "sources": {
                "cisa_kev": sum(1 for v in vulns if v.sources.get("cisa_kev"))
            }
        }


# Singleton instance
_sentinel: Optional[Sentinel] = None


def get_sentinel() -> Sentinel:
    """Get or create singleton Sentinel instance."""
    global _sentinel
    if _sentinel is None:
        _sentinel = Sentinel()
    return _sentinel


def run_intelligence_cycle() -> IntelReport:
    """
    Run full intelligence gathering cycle.
    
    Currently fetches:
    - CISA KEV (Known Exploited Vulnerabilities)
    
    Future:
    - NVD (recent CVEs)
    - ExploitDB (available exploits)
    """
    sentinel = get_sentinel()
    
    logger.info("[SENTINEL] === INTELLIGENCE CYCLE START ===")
    
    # Run CISA KEV
    report = sentinel.run_cisa_cycle()
    
    logger.info("[SENTINEL] === INTELLIGENCE CYCLE COMPLETE ===")
    
    return report
