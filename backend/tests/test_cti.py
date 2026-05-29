import pytest
import re
from backend.core.cti import is_private_ip

def test_is_private_ip():
    assert is_private_ip("192.168.1.50") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("172.16.0.5") is True
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("localhost") is True
    
    # Public IPs
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("1.1.1.1") is False

def test_cti_regex_parsers():
    # Extracted from cti.py tail_monitored_nodes_logs
    ssh_re = re.compile(r"Failed (?:password|publickey) for (?:invalid user )?(\S+) from (\S+)")
    web_re = re.compile(r"^(\S+)\s+\S+\s+\S+\s+\[[^\]]+\]\s+\"(\S+)\s+(.*?)\s+HTTP/[^\"]+\"\s+(\d+)")
    ufw_re = re.compile(r"\[UFW BLOCK\].*?SRC=(\S+).*?DST=(\S+).*?DPT=(\d+)")
    
    # Test SSH Brute Force
    ssh_log = "May 29 08:30:00 server sshd[1234]: Failed password for root from 192.168.1.100 port 22 ssh2"
    m_ssh = ssh_re.search(ssh_log)
    assert m_ssh is not None
    assert m_ssh.group(1) == "root"
    assert m_ssh.group(2) == "192.168.1.100"
    
    # Test SQLi Log
    web_log = '10.0.0.5 - - [29/May/2026:08:31:00 +0000] "GET /?id=1%20UNION%20SELECT%201 HTTP/1.1" 404'
    m_web = web_re.search(web_log)
    assert m_web is not None
    assert m_web.group(1) == "10.0.0.5"
    assert m_web.group(2) == "GET"
    assert m_web.group(3) == "/?id=1%20UNION%20SELECT%201"
    
    # Test UFW Block
    ufw_log = "May 29 08:35:00 server kernel: [UFW BLOCK] IN=eth0 OUT= MAC=... SRC=8.8.8.8 DST=192.168.1.200 LEN=40 TOS=0x00 PREC=0x00 TTL=245 ID=54321 PROTO=TCP SPT=4444 DPT=22 WINDOW=1024 RES=0x00 SYN URGP=0"
    m_ufw = ufw_re.search(ufw_log)
    assert m_ufw is not None
    assert m_ufw.group(1) == "8.8.8.8"
    assert m_ufw.group(2) == "192.168.1.200"
    assert m_ufw.group(3) == "22"
