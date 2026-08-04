import asyncio
import xml.etree.ElementTree as ET
from .db import load_nodes_db
from .session import session_manager


async def run_local_nmap(host: str, profile: str = "quick") -> str:
    """Runs Nmap locally from the backend container against a target."""
    nmap_flags = []
    if profile == "quick":
        nmap_flags.extend(["-F", "-T4"])
    elif profile == "comprehensive":
        nmap_flags.extend(["-p-", "-T4", "-sV", "-O"])
    elif profile == "vuln":
        nmap_flags.extend(["-T4", "--script", "vuln", "-sV"])
    else:
        nmap_flags.extend(["-F", "-T4", "-sV"])

    cmd = ["nmap"] + nmap_flags + [host]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return f"Nmap Error:\n{stderr.decode()}"

        return stdout.decode()
    except Exception as e:
        return f"Failed to execute Nmap: {str(e)}"


async def run_remote_nmap_xml(
    nid: str, node: dict, target: str, profile: str = "quick", sudo_pass: str = ""
) -> dict:
    """Runs Nmap remotely from a node via SSH and returns parsed XML data."""
    nmap_flags = "-oX -"
    if profile == "quick":
        nmap_flags += " -F -T4"
    elif profile == "comprehensive":
        nmap_flags += " -p- -T4 -sV -O"
    elif profile == "vuln":
        nmap_flags += " -T4 --script vuln -sV"
    else:
        nmap_flags += " -F -T4"

    password = sudo_pass or node.get("password", "")
    if password:
        cmd = f"echo '{password}' | sudo -S nmap {nmap_flags} {target}"
    else:
        cmd = f"nmap {nmap_flags} {target}"

    timeout = 120.0
    if profile == "comprehensive":
        timeout = 600.0
    elif profile == "vuln":
        timeout = 1200.0

    results, err = await session_manager.run(nid, node, [cmd], timeout=timeout)
    if err:
        raise RuntimeError(f"Execution error: {err}")

    output = results[0].get("output", "") if results else ""
    if not output:
        raise RuntimeError(
            f"No output from nmap scan. Raw results: {results}, Cmd: {cmd}"
        )

    xml_start = output.find("<?xml")
    if xml_start == -1:
        if "command not found" in output.lower() or "not found" in output.lower():
            raise RuntimeError(
                "Nmap is not installed on this node. Please install it first."
            )
        raise RuntimeError(
            f"Failed to parse nmap output as XML. Output: {output[:200]}"
        )

    xml_data = output[xml_start:]
    xml_end = xml_data.rfind("</nmaprun>")
    if xml_end != -1:
        xml_data = xml_data[: xml_end + len("</nmaprun>")]

    hosts = []
    try:
        root = ET.fromstring(xml_data)
        for host in root.findall("host"):
            status = host.find("status")
            if status is None or status.get("state") != "up":
                continue

            ip = ""
            mac = ""
            for addr in host.findall("address"):
                if addr.get("addrtype") == "ipv4" or addr.get("addrtype") == "ipv6":
                    ip = addr.get("addr")
                elif addr.get("addrtype") == "mac":
                    mac = addr.get("addr")

            hostnames = []
            hostnames_elem = host.find("hostnames")
            if hostnames_elem is not None:
                for hn in hostnames_elem.findall("hostname"):
                    name = hn.get("name")
                    if name:
                        hostnames.append(name)

            open_ports = []
            ports_elem = host.find("ports")
            if ports_elem is not None:
                for port in ports_elem.findall("port"):
                    state = port.find("state")
                    if state is not None and state.get("state") == "open":
                        port_id = port.get("portid")
                        service = port.find("service")
                        service_name = (
                            service.get("name") if service is not None else "unknown"
                        )
                        product = (
                            service.get("product", "") if service is not None else ""
                        )
                        version = (
                            service.get("version", "") if service is not None else ""
                        )
                        open_ports.append(
                            {
                                "port": port_id,
                                "service": service_name,
                                "product": product,
                                "version": version,
                            }
                        )

            os_match = "unknown"
            os_elem = host.find("os")
            if os_elem is not None:
                matches = os_elem.findall("osmatch")
                if matches:
                    os_match = matches[0].get("name", "unknown")

            hosts.append(
                {
                    "ip": ip,
                    "mac": mac,
                    "hostnames": hostnames,
                    "os": os_match,
                    "ports": open_ports,
                }
            )
    except Exception as e:
        raise RuntimeError(f"Error parsing nmap XML: {e}")

    return {"status": "success", "hosts": hosts}
