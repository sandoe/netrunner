import json
import logging
from ..core.session import session_manager
from ..core.db import load_nodes_db, load_links_db, save_link_db
from ..core.vault import load_credentials
import uuid

logger = logging.getLogger("discovery")

async def discover_topology():
    """
    Runs LLDP discovery on all capable nodes and builds topology links.
    Returns the number of new links added.
    """
    nodes = await load_nodes_db()
    links = await load_links_db()
    
    # Pre-calculate existing links to avoid duplicates
    # We define a link uniquely by a sorted pair of node IDs
    existing_links = set()
    for l in links.values():
        pair = tuple(sorted([l.source, l.target]))
        existing_links.add(pair)
    
    new_links_count = 0
    
    import asyncio
    
    # We will build a map of MAC -> NodeID to match neighbors
    mac_to_node = {}
    node_neighbors = {}

    async def discover_node(nid, node):
        try:
            # We need credentials for SSH
            username, password = await load_credentials(nid)
            n = dict(node)
            n["username"] = username or n.get("username", "root")
            n["password"] = password or ""
            
            # Execute LLDP query
            results, err = await session_manager.run(nid, n, ["lldpcli -f json show neighbors"])
            if err or not results:
                return
                
            out = results[0]
            if "lldp" not in out:
                return
                
            data = json.loads(out)
            interfaces = data.get("lldp", {}).get("interface", [])
            
            # Sometimes lldpcli returns a dict if there's only one interface, sometimes list
            if isinstance(interfaces, dict):
                interfaces = [interfaces]
                
            # It might also be nested: {"interface": {"eth0": {"chassis": ...}}}
            # Let's handle the nested structure lldpcli usually produces:
            if isinstance(data.get("lldp", {}).get("interface"), dict):
                ifaces_dict = data["lldp"]["interface"]
                neighbors = []
                for iface_name, iface_data in ifaces_dict.items():
                    if "chassis" in iface_data:
                        for chassis_name, chassis_data in iface_data["chassis"].items():
                            sysname = chassis_data.get("name", {}).get("value")
                            if sysname:
                                neighbors.append(sysname)
                
                if neighbors:
                    node_neighbors[nid] = neighbors
                    
        except Exception as e:
            logger.error(f"Failed LLDP discovery on {nid}: {e}")

    # Run discovery on all nodes concurrently
    tasks = [discover_node(nid, node) for nid, node in nodes.items()]
    await asyncio.gather(*tasks)
            
    # Now match neighbors by name
    # We need a map of Node sysname -> Node ID
    sysname_to_nid = {n.get("name"): nid for nid, n in nodes.items() if n.get("name")}
    
    for src_nid, neighbors in node_neighbors.items():
        for neighbor_sysname in neighbors:
            tgt_nid = sysname_to_nid.get(neighbor_sysname)
            if tgt_nid and tgt_nid != src_nid:
                pair = tuple(sorted([src_nid, tgt_nid]))
                if pair not in existing_links:
                    existing_links.add(pair)
                    # Create the new link
                    link_id = f"link-{uuid.uuid4().hex[:8]}"
                    new_link = {
                        "id": link_id,
                        "source": src_nid,
                        "target": tgt_nid,
                        "auto_discovered": True,
                        "metadata": {"protocol": "lldp"}
                    }
                    await save_link_db(new_link)
                    new_links_count += 1
                    
    return new_links_count
