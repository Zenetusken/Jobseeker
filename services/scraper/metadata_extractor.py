"""
Metadata Extractor — Regex + keyword engine for cybersecurity job requirements.
Extracts certifications, clearance levels, and technical skills from job text.
"""
import re
from typing import Optional


# Cybersecurity certification patterns
CERT_PATTERNS: list[tuple[str, str]] = [
    (r"\bCISSP\b", "CISSP"),
    (r"\bCCNA\b", "CCNA"),
    (r"\bCCNP\b", "CCNP"),
    (r"\bCCIE\b", "CCIE"),
    (r"\bSecurity\+(?:\s|$)", "Security+"),
    (r"\bCEH\b", "CEH"),
    (r"\bOSCP\b", "OSCP"),
    (r"\bCISA\b", "CISA"),
    (r"\bCISM\b", "CISM"),
    (r"\bGSEC\b", "GSEC"),
    (r"\bGPEN\b", "GPEN"),
    (r"\bGCIH\b", "GCIH"),
    (r"\bCASP\+(?:\s|$)", "CASP+"),
    (r"\bCySA\+(?:\s|$)", "CySA+"),
    (r"\bPenTest\+(?:\s|$)", "PenTest+"),
    (r"\bNetwork\+(?:\s|$)", "Network+"),
    (r"\bA\+(?:\s|$)", "A+"),
    (r"\bSSCP\b", "SSCP"),
    (r"\bCRISC\b", "CRISC"),
    (r"\bISO 27001\b", "ISO 27001"),
    (r"\bPCI DSS\b", "PCI DSS"),
    (r"\bGDPR\b", "GDPR"),
    (r"\bHIPAA\b", "HIPAA"),
    (r"\bNIST\b", "NIST"),
    (r"\bAWS Certified Security\b", "AWS Certified Security"),
    (r"\bAzure Security Engineer\b", "Azure Security Engineer"),
    (r"\bGCP Professional Cloud Security\b", "GCP Professional Cloud Security"),
]

# Clearance level patterns
CLEARANCE_PATTERNS: list[tuple[str, str]] = [
    (r"\bTop Secret(?:[/\s]*SCI)?\b", "Top Secret"),
    (r"\bTS/SCI\b", "Top Secret"),
    (r"\bSecret Clearance\b", "Secret"),
    (r"\bSecret\b", "Secret"),
    (r"\bPublic Trust\b", "Public Trust"),
    (r"\bConfidential\b", "Confidential"),
]

# Technical skill keywords (cybersecurity + networking focus)
SKILL_KEYWORDS: list[str] = [
    "SIEM", "Splunk", "ELK", "QRadar", "ArcSight",
    "Firewall", "Palo Alto", "Cisco ASA", "Fortinet", "pfSense",
    "IDS", "IPS", "Snort", "Suricata", "Zeek",
    "EDR", "CrowdStrike", "Carbon Black", "SentinelOne",
    "Penetration Testing", "Vulnerability Assessment", "Red Team", "Blue Team",
    "Incident Response", "Forensics", "Threat Hunting",
    "BGP", "OSPF", "EIGRP", "MPLS", "VLAN", "VPN", "IPsec",
    "Active Directory", "LDAP", "Kerberos", "SAML", "OAuth",
    "AWS", "Azure", "GCP", "Cloud Security",
    "Docker", "Kubernetes", "Container Security",
    "Python", "PowerShell", "Bash", "Scripting",
    "Wireshark", "tcpdump", "Nmap", "Metasploit", "Burp Suite",
    "SOC", "NOC", "Security Operations",
    "Risk Assessment", "Compliance", "Audit",
    "MITRE ATT&CK", "Kill Chain", "Zero Trust",
    "DLP", "Data Loss Prevention",
    "IAM", "Identity Access Management",
    "PKI", "TLS", "SSL", "SSH",
    "Linux", "Windows Server", "Unix",
    "Ansible", "Terraform", "CI/CD",
    "Git", "DevSecOps",
    "TCP/IP", "DNS", "DHCP", "SNMP", "SMTP",
]


def extract_certs(text: str) -> list[str]:
    """Extract mentioned certifications from text."""
    found = set()
    for pattern, cert_name in CERT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found.add(cert_name)
    return sorted(found)


def extract_clearance(text: str) -> Optional[str]:
    """Extract the highest clearance level mentioned."""
    for pattern, level in CLEARANCE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return level
    return None


def extract_skills(text: str) -> list[str]:
    """Extract mentioned technical skills from text."""
    found = set()
    text_lower = text.lower()
    for skill in SKILL_KEYWORDS:
        if skill.lower() in text_lower:
            found.add(skill)
    return sorted(found)


def extract_all_metadata(text: str) -> dict:
    """Extract all metadata from a job description or resume."""
    return {
        "required_certs": extract_certs(text),
        "required_skills": extract_skills(text),
        "clearance_level": extract_clearance(text) or "",
    }
