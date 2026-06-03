import asyncio
from fastapi import APIRouter, HTTPException, Depends
from .auth import get_current_user
from .nodes import load_nodes, save_nodes

router = APIRouter()

# High-fidelity mock vulnerability database for demonstration
MOCK_VULNDB = {
    "vsftpd": {
        "2.3.4": {
            "cve": "CVE-2011-2523",
            "title": "vsftpd 2.3.4 Backdoor Command Execution",
            "severity": "CRITICAL",
            "cvss": 9.8,
            "description": "vsftpd version 2.3.4 contains a backdoor. If a smiley face is sent in the username, the software opens a listening shell on port 6200.",
            "remediation": "Upgrade vsftpd or block port 21/6200 immediately."
        }
    },
    "apache": {
        "2.4.49": {
            "cve": "CVE-2021-41773",
            "title": "Apache HTTP Server 2.4.49 Path Traversal",
            "severity": "CRITICAL",
            "cvss": 9.8,
            "description": "A flaw was found in a change made to path normalization in Apache HTTP Server 2.4.49. An attacker could use a path traversal attack to map URLs to files outside the directories configured by Alias-like directives.",
            "remediation": "Update to Apache HTTP Server 2.4.50 or higher."
        }
    },
    "proftpd": {
        "1.3.3c": {
            "cve": "CVE-2010-4221",
            "title": "ProFTPD 1.3.3c Backdoor",
            "severity": "CRITICAL",
            "cvss": 9.8,
            "description": "The ProFTPD 1.3.3c source code archive was compromised and a backdoor was inserted that allows attackers to execute arbitrary code.",
            "remediation": "Ensure you compile from official, verified sources or upgrade."
        }
    },
    "samba": {
        "3.0.20": {
            "cve": "CVE-2007-2447",
            "title": "Samba 'username map script' Command Execution",
            "severity": "CRITICAL",
            "cvss": 10.0,
            "description": "MS-RPC functionality in Samba 3.0.20 through 3.0.25rc3 allows remote attackers to execute arbitrary commands via shell metacharacters involving the SamrChangePassword function.",
            "remediation": "Update Samba to 3.0.25 or later."
        }
    },
    "openssh": {
        "7.2p2": {
            "cve": "CVE-2016-6210",
            "title": "OpenSSH 7.2p2 User Enumeration",
            "severity": "MEDIUM",
            "cvss": 5.3,
            "description": "The sshd executable in OpenSSH before 7.3 does not limit password lengths, which allows remote attackers to enumerate users by observing timing differences.",
            "remediation": "Update OpenSSH to 7.3 or later."
        }
    }
}

def analyze_ports(ports):
    findings = []
    if not ports:
        return findings
        
    for p in ports:
        service = str(p.get("service", "")).lower()
        product = str(p.get("product", "")).lower()
        version = str(p.get("version", "")).lower()
        
        # Determine the key to lookup
        lookup_key = None
        for key in MOCK_VULNDB.keys():
            if key in product or key in service:
                lookup_key = key
                break
                
        if lookup_key:
            versions = MOCK_VULNDB[lookup_key]
            # Try exact version match
            found = False
            for v_key, vuln in versions.items():
                if v_key in version:
                    finding = dict(vuln)
                    finding["port"] = p.get("port")
                    finding["service"] = p.get("service")
                    findings.append(finding)
                    found = True
                    break
            
            # If no exact version match but the product is known to be vulnerable in general (fallback for demo)
            if not found and not version:
                # Add a generic warning if version is unknown but product is highly targeted
                if lookup_key in ["apache", "openssh", "samba"]:
                    findings.append({
                        "cve": "UNKNOWN",
                        "title": f"Outdated {lookup_key.capitalize()} Detected",
                        "severity": "WARNING",
                        "cvss": 4.0,
                        "description": f"The version of {lookup_key.capitalize()} could not be determined. Ensure it is updated to the latest secure version.",
                        "remediation": "Verify the exact version manually and update if necessary.",
                        "port": p.get("port"),
                        "service": p.get("service")
                    })
                
    return findings

@router.post("/threats/analyze/{node_id}")
async def analyze_node_vulnerabilities(node_id: str, user: dict = Depends(get_current_user)):
    nodes = await load_nodes()
    node = nodes.get(node_id)
    
    if not node:
        raise HTTPException(404, "Node not found")
        
    metadata = node.get("metadata", {})
    ports = metadata.get("ports", [])
    
    # Simulate processing delay for dramatic effect
    await asyncio.sleep(1.5)
    
    findings = analyze_ports(ports)
    
    # Also add a generic OS vulnerability if it's Windows XP/7 or old Linux
    os_guess = str(metadata.get("os_guess", "")).lower()
    if "windows xp" in os_guess or "windows 7" in os_guess:
        findings.append({
            "cve": "CVE-2017-0144",
            "title": "EternalBlue SMB Remote Code Execution",
            "severity": "CRITICAL",
            "cvss": 10.0,
            "description": "A critical vulnerability exists in Microsoft SMBv1. Attackers can execute arbitrary code on the target system.",
            "remediation": "Apply MS17-010 or disable SMBv1.",
            "port": "445",
            "service": "smb"
        })
        
    tags = node.get("tags", [])
    changed = False
    
    has_critical = any(f.get("severity") == "CRITICAL" for f in findings)
    
    if has_critical and "vulnerable" not in tags:
        tags.append("vulnerable")
        node["tags"] = tags
        changed = True
        
    if changed:
        await save_nodes(nodes)
        
    return {
        "status": "success",
        "findings": findings,
        "is_vulnerable": has_critical,
        "node_id": node_id
    }
