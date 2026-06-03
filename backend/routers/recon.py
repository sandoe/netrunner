import uuid
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime

from .auth import get_current_user
from ..core.session import session_manager
from .nodes import load_nodes, save_nodes, _get_node_with_creds
from .links import load_links, save_links

router = APIRouter(tags=["recon"])

@router.post("/recon/{nid}/scan")
async def scan_network(nid: str, body: dict, user: dict = Depends(get_current_user)):
    target = body.get("target")
    profile = body.get("profile", "quick")
    sudo_pass = body.get("sudo_pass")

    if not target:
        raise HTTPException(400, "Missing target")

    nodes = await load_nodes()
    if nid not in nodes:
        raise HTTPException(404, "Node not found")

    node = await _get_node_with_creds(nid, nodes)
    if sudo_pass:
        node["password"] = sudo_pass
    password = node.get("password", "")

    # Build Nmap command based on profile
    nmap_flags = "-oX -"
    if profile == "quick":
        nmap_flags += " -F -T4"
    elif profile == "comprehensive":
        nmap_flags += " -p- -T4 -sV -O"
    elif profile == "vuln":
        nmap_flags += " -T4 --script vuln -sV"
    else:
        nmap_flags += " -F -T4"
        
    if password:
        cmd = f"echo '{password}' | sudo -S nmap {nmap_flags} {target}"
    else:
        cmd = f"nmap {nmap_flags} {target}"

    timeout = 60.0
    if profile == "comprehensive":
        timeout = 300.0
    elif profile == "vuln":
        timeout = 180.0

    results, err = await session_manager.run(nid, node, [cmd], timeout=timeout)
    if err:
        raise HTTPException(500, f"Execution error: {err}")

    output = results[0].get("output", "") if results else ""
    if not output:
        raise HTTPException(500, f"No output from nmap scan. Raw results: {results}, Cmd: {cmd}")

    # The output might have sudo prompts or other garbage before the XML.
    # Find the start of <?xml
    xml_start = output.find("<?xml")
    if xml_start == -1:
        # Check if nmap is installed
        if "command not found" in output.lower() or "not found" in output.lower():
            raise HTTPException(400, "Nmap is not installed on this node. Please install it first.")
        raise HTTPException(500, f"Failed to parse nmap output as XML. Output: {output[:200]}")

    xml_data = output[xml_start:]
    
    hosts = []
    try:
        root = ET.fromstring(xml_data)
        for host in root.findall('host'):
            status = host.find('status')
            if status is None or status.get('state') != 'up':
                continue
            
            ip = ""
            mac = ""
            for addr in host.findall('address'):
                if addr.get('addrtype') == 'ipv4' or addr.get('addrtype') == 'ipv6':
                    ip = addr.get('addr')
                elif addr.get('addrtype') == 'mac':
                    mac = addr.get('addr')
            
            # Hostnames
            hostnames = []
            hostnames_elem = host.find('hostnames')
            if hostnames_elem is not None:
                for hn in hostnames_elem.findall('hostname'):
                    name = hn.get('name')
                    if name:
                        hostnames.append(name)
                        
            # Ports
            open_ports = []
            ports_elem = host.find('ports')
            if ports_elem is not None:
                for port in ports_elem.findall('port'):
                    state = port.find('state')
                    if state is not None and state.get('state') == 'open':
                        port_id = port.get('portid')
                        service = port.find('service')
                        service_name = service.get('name') if service is not None else 'unknown'
                        product = service.get('product', '') if service is not None else ''
                        version = service.get('version', '') if service is not None else ''
                        open_ports.append({
                            "port": port_id,
                            "service": service_name,
                            "product": product,
                            "version": version
                        })
            
            # OS Guess
            os_match = "unknown"
            os_elem = host.find('os')
            if os_elem is not None:
                matches = os_elem.findall('osmatch')
                if matches:
                    os_match = matches[0].get('name', 'unknown')
            
            hosts.append({
                "ip": ip,
                "mac": mac,
                "hostnames": hostnames,
                "os": os_match,
                "ports": open_ports
            })
    except Exception as e:
        raise HTTPException(500, f"Error parsing nmap XML: {e}")

    return {"status": "success", "hosts": hosts}


@router.post("/recon/{nid}/import")
async def import_recon_hosts(nid: str, body: dict, user: dict = Depends(get_current_user)):
    hosts = body.get("hosts", [])
    if not hosts:
        raise HTTPException(400, "No hosts provided")

    nodes = await load_nodes()
    links = await load_links()
    
    imported_count = 0
    
    for h in hosts:
        ip = h.get("ip")
        if not ip: continue
        
        # Check if already exists
        exists = False
        for node_id, node_data in nodes.items():
            if node_data.get("host") == ip:
                exists = True
                break
                
        if exists:
            continue
            
        # Determine device type
        os_str = h.get("os", "").lower()
        device_type = "unknown"
        if "linux" in os_str:
            device_type = "linux"
        elif "windows" in os_str:
            device_type = "windows"
        elif "mac" in os_str or "apple" in os_str:
            device_type = "unknown"
            
        name = ip
        if h.get("hostnames"):
            name = h.get("hostnames")[0]
            
        new_node_id = str(uuid.uuid4())
        nodes[new_node_id] = {
            "id": new_node_id,
            "name": name,
            "host": ip,
            "port": 22,
            "username": "root",
            "transport": "ssh",
            "device_type": device_type,
            "has_password": False,
            "created": datetime.utcnow().isoformat(),
            "tags": ["recon"],
            "metadata": {
                "mac": h.get("mac"),
                "os_guess": h.get("os"),
                "ports": h.get("ports")
            }
        }
        
        # Add link from the scanning node to the discovered node
        new_link_id = f"{nid}_{new_node_id}"
        links[new_link_id] = {
            "id": new_link_id,
            "source": nid,
            "target": new_node_id,
            "auto_discovered": True,
            "metadata": {
                "method": "nmap"
            }
        }
        imported_count += 1
        
    if imported_count > 0:
        await save_nodes(nodes)
        await save_links(links)
        
    return {"status": "success", "imported": imported_count}
