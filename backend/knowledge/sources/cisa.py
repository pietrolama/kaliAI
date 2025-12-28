"""
CISA Known Exploited Vulnerabilities (KEV) Fetcher

Fetches the official CISA KEV catalog - a curated list of 
actively exploited vulnerabilities requiring immediate attention.

Source: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
"""

import logging
import requests
from typing import List, Optional, Tuple
from datetime import datetime

from backend.core.intel.models import VulnArtifact, IntelReport, VulnStatus

logger = logging.getLogger('CISA_Fetcher')

# Official CISA KEV JSON feed
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# Request timeout
REQUEST_TIMEOUT = 30


def fetch_cisa_kev(limit: Optional[int] = None) -> Tuple[List[VulnArtifact], IntelReport]:
    """
    Fetch CISA Known Exploited Vulnerabilities catalog.
    
    Args:
        limit: Optional limit on number of entries to process (for testing)
        
    Returns:
        Tuple of (list of VulnArtifact, IntelReport summary)
    """
    report = IntelReport(source="CISA_KEV")
    artifacts: List[VulnArtifact] = []
    
    try:
        logger.info(f"Fetching CISA KEV from {CISA_KEV_URL}")
        
        response = requests.get(
            CISA_KEV_URL,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "KaliAI-Sentinel/1.0 (Threat Intelligence)",
                "Accept": "application/json"
            }
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if "vulnerabilities" not in data:
            report.errors.append("Invalid response: missing 'vulnerabilities' key")
            logger.error("Invalid CISA response structure")
            return artifacts, report
        
        vulns = data["vulnerabilities"]
        catalog_version = data.get("catalogVersion", "unknown")
        date_released = data.get("dateReleased", "unknown")
        
        logger.info(f"CISA KEV v{catalog_version} ({date_released}): {len(vulns)} total CVEs")
        
        # Apply limit if specified
        if limit:
            vulns = vulns[:limit]
        
        for entry in vulns:
            try:
                artifact = _parse_cisa_entry(entry)
                if artifact:
                    # Calculate priority (CISA KEV = automatic 100)
                    artifact.calculate_priority()
                    artifacts.append(artifact)
                    
                    if artifact.risk_score >= 100:
                        report.critical_count += 1
                        
            except Exception as e:
                cve = entry.get("cveID", "unknown")
                report.errors.append(f"Parse error for {cve}: {str(e)}")
                logger.warning(f"Failed to parse CISA entry: {e}")
        
        report.total_fetched = len(vulns)
        report.new_count = len(artifacts)
        
        logger.info(f"Parsed {len(artifacts)} CISA KEV entries ({report.critical_count} critical)")
        
    except requests.exceptions.Timeout:
        report.errors.append("Request timeout")
        logger.error("CISA KEV fetch timeout")
        
    except requests.exceptions.RequestException as e:
        report.errors.append(f"Network error: {str(e)}")
        logger.error(f"CISA KEV fetch failed: {e}")
        
    except Exception as e:
        report.errors.append(f"Unexpected error: {str(e)}")
        logger.error(f"CISA KEV processing error: {e}")
    
    return artifacts, report


def _parse_cisa_entry(entry: dict) -> Optional[VulnArtifact]:
    """
    Parse a single CISA KEV entry into VulnArtifact.
    
    CISA KEV fields:
    - cveID: "CVE-2024-1234"
    - vendorProject: "Apache"
    - product: "HTTP Server"
    - vulnerabilityName: "Apache HTTP Server Path Traversal"
    - dateAdded: "2024-01-15"
    - shortDescription: "..."
    - requiredAction: "Apply updates per vendor instructions"
    - dueDate: "2024-02-05"
    - knownRansomwareCampaignUse: "Known"
    - notes: "Additional info..."
    """
    cve_id = entry.get("cveID")
    if not cve_id:
        return None
    
    # Build title from vendor/product/vuln name
    vendor = entry.get("vendorProject", "Unknown")
    product = entry.get("product", "")
    vuln_name = entry.get("vulnerabilityName", "")
    
    title = vuln_name or f"{vendor} {product} Vulnerability"
    
    # Check ransomware association
    ransomware_use = entry.get("knownRansomwareCampaignUse", "").lower()
    known_ransomware = ransomware_use == "known"
    
    return VulnArtifact(
        cve_id=cve_id,
        title=title,
        description=entry.get("shortDescription", "No description available"),
        risk_score=100.0,  # CISA KEV = critical by definition
        sources={
            "cisa_kev": True,
            "cisa_date_added": entry.get("dateAdded"),
            "cisa_due_date": entry.get("dueDate"),
            "cisa_required_action": entry.get("requiredAction", "")
        },
        technical_data={
            "vendor": vendor,
            "product": product,
            "vulnerability_name": vuln_name,
            "notes": entry.get("notes", "")
        },
        status=VulnStatus.NEW,
        date_added=entry.get("dateAdded"),
        due_date=entry.get("dueDate"),
        known_ransomware=known_ransomware,
        exploitation_activity="Active exploitation confirmed by CISA"
    )


def get_recent_kev(days: int = 30, limit: int = 20) -> List[VulnArtifact]:
    """
    Fetch only recent CISA KEV entries (added within N days).
    
    Args:
        days: How many days back to look
        limit: Maximum entries to return
        
    Returns:
        List of recent VulnArtifact entries
    """
    all_vulns, _ = fetch_cisa_kev()
    
    cutoff = datetime.now()
    recent = []
    
    for vuln in all_vulns:
        if vuln.date_added:
            try:
                added = datetime.strptime(vuln.date_added, "%Y-%m-%d")
                if (cutoff - added).days <= days:
                    recent.append(vuln)
            except ValueError:
                continue
    
    # Sort by date (newest first)
    recent.sort(key=lambda v: v.date_added or "", reverse=True)
    
    return recent[:limit]
