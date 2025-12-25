"""
Data Sources Module - Sistema modulare per integrare fonti di conoscenza
"""
from .base import DataSource, SourceResult
from .registry import SourceRegistry, registry

# Import all sources
from .owasp_source import OWASPSource
from .nvd_source import NVDSource
from .cve_details_source import CVEDetailsSource
from .securityfocus_source import SecurityFocusSource
from .github_advisories_source import GitHubAdvisoriesSource
from .rapid7_source import Rapid7Source
from .cisa_alerts_source import CISAAlertsSource
from .exploitdb_source import ExploitDBSource
from .knowledge_export_source import KnowledgeExportSource

# New sources - Level 1 (Structured Data)
from .payloadsallthethings_source import PayloadsAllTheThingsSource
from .exploitdb_repo_source import ExploitDBRepoSource
from .cisa_kev_source import CISAKEVSource

# New sources - Level 2 (Specialized Knowledge)
from .hacktricks_source import HackTricksSource
from .owasp_cheatsheets_source import OWASPCheatSheetsSource

# New sources - Level 3 (Continuous Updates)
from .rss_feeds_source import RSSFeedsSource

# New sources - CTF Write-ups and Logs
from .htb_writeups_source import HTBWriteupsSource
from .tryhackme_source import TryHackMeSource
from .vulnhub_writeups_source import VulnHubWriteupsSource
from .honeypot_logs_source import HoneypotLogsSource
from .pentest_reports_source import PentestReportsSource

# Auto-register sources
registry.register(OWASPSource())
registry.register(NVDSource())
registry.register(CVEDetailsSource())
registry.register(SecurityFocusSource())
registry.register(GitHubAdvisoriesSource())
registry.register(Rapid7Source())
registry.register(CISAAlertsSource())
registry.register(ExploitDBSource())
registry.register(KnowledgeExportSource())

# Register new sources
registry.register(PayloadsAllTheThingsSource())
registry.register(ExploitDBRepoSource())
registry.register(CISAKEVSource())
registry.register(HackTricksSource())
registry.register(OWASPCheatSheetsSource())
registry.register(RSSFeedsSource())
registry.register(HTBWriteupsSource())
registry.register(TryHackMeSource())
registry.register(VulnHubWriteupsSource())
registry.register(HoneypotLogsSource())
registry.register(PentestReportsSource())

__all__ = [
    'DataSource', 
    'SourceResult', 
    'SourceRegistry', 
    'registry',
    'OWASPSource',
    'NVDSource',
    'CVEDetailsSource',
    'SecurityFocusSource',
    'GitHubAdvisoriesSource',
    'Rapid7Source',
    'CISAAlertsSource',
    'ExploitDBSource',
    'KnowledgeExportSource',
    'PayloadsAllTheThingsSource',
    'ExploitDBRepoSource',
    'CISAKEVSource',
    'HackTricksSource',
    'OWASPCheatSheetsSource',
    'RSSFeedsSource',
    'HTBWriteupsSource',
    'TryHackMeSource',
    'VulnHubWriteupsSource',
    'HoneypotLogsSource',
    'PentestReportsSource'
]
