"""
Tier 1 — Critical pure-logic tests for metadata_extractor.py.
Tests cert extraction, clearance detection, and skill matching.
"""
import pytest
from services.scraper.metadata_extractor import (
    extract_certs,
    extract_clearance,
    extract_skills,
    extract_all_metadata,
)


class TestExtractCerts:
    def test_cissp_detected(self):
        result = extract_certs("Must have CISSP certification")
        assert "CISSP" in result

    def test_multiple_certs(self):
        text = "Requires CISSP, CEH, and OSCP certifications"
        result = extract_certs(text)
        assert "CISSP" in result
        assert "CEH" in result
        assert "OSCP" in result

    def test_case_insensitive(self):
        result = extract_certs("requires cissp and ceh")
        assert "CISSP" in result
        assert "CEH" in result

    def test_security_plus_with_plus_sign(self):
        result = extract_certs("Security+ required")
        assert "Security+" in result

    def test_network_plus(self):
        result = extract_certs("Network+ certification preferred")
        assert "Network+" in result

    def test_casp_plus(self):
        result = extract_certs("CASP+ is a plus")
        assert "CASP+" in result

    def test_cysa_plus(self):
        result = extract_certs("CySA+ certification")
        assert "CySA+" in result

    def test_pentest_plus(self):
        result = extract_certs("PenTest+ certified")
        assert "PenTest+" in result

    def test_ccna_ccnp_ccie(self):
        result = extract_certs("CCNA, CCNP, or CCIE required")
        assert "CCNA" in result
        assert "CCNP" in result
        assert "CCIE" in result

    def test_compliance_frameworks(self):
        text = "Knowledge of ISO 27001, PCI DSS, GDPR, HIPAA, and NIST"
        result = extract_certs(text)
        assert "ISO 27001" in result
        assert "PCI DSS" in result
        assert "GDPR" in result
        assert "HIPAA" in result
        assert "NIST" in result

    def test_cloud_certs(self):
        text = "AWS Certified Security or Azure Security Engineer"
        result = extract_certs(text)
        assert "AWS Certified Security" in result
        assert "Azure Security Engineer" in result

    def test_gcp_cloud_security(self):
        result = extract_certs("GCP Professional Cloud Security Engineer")
        assert "GCP Professional Cloud Security" in result

    def test_giac_certs(self):
        text = "GSEC, GPEN, or GCIH certification"
        result = extract_certs(text)
        assert "GSEC" in result
        assert "GPEN" in result
        assert "GCIH" in result

    def test_isc2_certs(self):
        text = "SSCP or CISSP required, CRISC preferred"
        result = extract_certs(text)
        assert "SSCP" in result
        assert "CISSP" in result
        assert "CRISC" in result

    def test_isaca_certs(self):
        text = "CISA or CISM certification"
        result = extract_certs(text)
        assert "CISA" in result
        assert "CISM" in result

    def test_no_false_positive_on_partial(self):
        """CEH should not match 'CHE' or other partials."""
        result = extract_certs("Chemical engineering background")
        assert "CEH" not in result

    def test_empty_text(self):
        result = extract_certs("")
        assert result == []

    def test_no_certs_in_generic_text(self):
        result = extract_certs("Looking for a team player with good communication skills")
        assert result == []

    @pytest.mark.parametrize("text,expected", [
        ("CISSP required", ["CISSP"]),
        ("Need CEH and OSCP", ["CEH", "OSCP"]),
        ("Security+ and Network+", ["Network+", "Security+"]),
        ("A+ certification", ["A+"]),
    ])
    def test_parametrized_certs(self, text, expected):
        assert extract_certs(text) == expected


class TestExtractClearance:
    def test_top_secret(self):
        assert extract_clearance("Must have Top Secret clearance") == "Top Secret"

    def test_top_secret_sci(self):
        assert extract_clearance("TS/SCI required") == "Top Secret"
        assert extract_clearance("Top Secret/SCI clearance") == "Top Secret"

    def test_secret(self):
        assert extract_clearance("Secret Clearance required") == "Secret"

    def test_public_trust(self):
        assert extract_clearance("Public Trust position") == "Public Trust"

    def test_confidential(self):
        assert extract_clearance("Confidential clearance") == "Confidential"

    def test_no_clearance(self):
        assert extract_clearance("No clearance required") is None

    def test_empty_text(self):
        assert extract_clearance("") is None

    def test_secret_not_matching_secretary(self):
        """'Secret' should match standalone, but 'Secretary' should not."""
        result = extract_clearance("Secretary position available")
        # The pattern \bSecret\b will match "Secret" in "Secretary"? No, \b is word boundary.
        # "Secretary" — the word boundary after 't' in 'Secret' is not there because 'a' follows.
        # So this should NOT match.
        assert result is None


class TestExtractSkills:
    def test_siem_skills(self):
        text = "Experience with SIEM, Splunk, and QRadar"
        result = extract_skills(text)
        assert "SIEM" in result
        assert "Splunk" in result
        assert "QRadar" in result

    def test_firewall_skills(self):
        text = "Configure Palo Alto, Cisco ASA, and Fortinet firewalls"
        result = extract_skills(text)
        assert "Palo Alto" in result
        assert "Cisco ASA" in result
        assert "Fortinet" in result

    def test_ids_ips(self):
        text = "Deploy IDS/IPS solutions including Snort and Suricata"
        result = extract_skills(text)
        assert "Snort" in result
        assert "Suricata" in result

    def test_edr_tools(self):
        text = "CrowdStrike, Carbon Black, and SentinelOne EDR"
        result = extract_skills(text)
        assert "CrowdStrike" in result
        assert "Carbon Black" in result
        assert "SentinelOne" in result

    def test_network_protocols(self):
        text = "BGP, OSPF, MPLS, VLAN configuration"
        result = extract_skills(text)
        assert "BGP" in result
        assert "OSPF" in result
        assert "MPLS" in result
        assert "VLAN" in result

    def test_cloud_skills(self):
        text = "AWS, Azure, and GCP cloud security"
        result = extract_skills(text)
        assert "AWS" in result
        assert "Azure" in result
        assert "GCP" in result

    def test_programming(self):
        text = "Python, PowerShell, and Bash scripting"
        result = extract_skills(text)
        assert "Python" in result
        assert "PowerShell" in result
        assert "Bash" in result

    def test_security_tools(self):
        text = "Wireshark, tcpdump, Nmap, Metasploit, Burp Suite"
        result = extract_skills(text)
        assert "Wireshark" in result
        assert "Nmap" in result
        assert "Metasploit" in result
        assert "Burp Suite" in result

    def test_frameworks(self):
        text = "MITRE ATT&CK and Zero Trust architecture"
        result = extract_skills(text)
        assert "MITRE ATT&CK" in result
        assert "Zero Trust" in result

    def test_case_insensitive_skills(self):
        result = extract_skills("experience with splunk and snort")
        assert "Splunk" in result
        assert "Snort" in result

    def test_empty_text(self):
        assert extract_skills("") == []

    def test_no_skills(self):
        result = extract_skills("Great communication and teamwork abilities")
        assert result == []


class TestExtractAllMetadata:
    def test_full_extraction(self):
        text = (
            "Senior Security Engineer with CISSP and Top Secret clearance. "
            "Must have SIEM, Splunk, and Python skills."
        )
        result = extract_all_metadata(text)
        assert "CISSP" in result["required_certs"]
        assert result["clearance_level"] == "Top Secret"
        assert "SIEM" in result["required_skills"]
        assert "Splunk" in result["required_skills"]
        assert "Python" in result["required_skills"]

    def test_empty_text(self):
        result = extract_all_metadata("")
        assert result["required_certs"] == []
        assert result["required_skills"] == []
        assert result["clearance_level"] == ""

    def test_no_metadata(self):
        result = extract_all_metadata("Generic job description with no specific requirements")
        assert result["required_certs"] == []
        assert result["required_skills"] == []
        assert result["clearance_level"] == ""
