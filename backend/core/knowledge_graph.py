import networkx as nx

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def rebuild_from_state(self, nodes_db: dict, connections: dict, creds: dict, events: list):
        self.graph.clear()
        
        self.graph.add_node("attacker", name="Netrunner Platform", type="Attacker")
        
        for nid, node_data in nodes_db.items():
            name = node_data.get("name", nid)
            ip = node_data.get("host", "")
            dtype = node_data.get("device_type", "unknown")
            self.graph.add_node(nid, name=name, ip=ip, device_type=dtype, type="Machine")
            
            if ip in ("127.0.0.1", "localhost", "0.0.0.0"):
                self.graph.add_edge("attacker", nid, label="LOCAL_HOST")
                
        for nid, conn_data in connections.items():
            if conn_data.get("connected"):
                self.graph.add_edge("attacker", nid, label="ACTIVE_SESSION")
                
        for nid, cred_data in creds.items():
            if isinstance(cred_data, tuple) and len(cred_data) == 2:
                u, p = cred_data
                cred_id = f"cred_{u}_{p}"
                self.graph.add_node(cred_id, name=f"{u}:{p}", username=u, password=p, type="Credential")
                self.graph.add_edge(nid, cred_id, label="COMPROMISED_WITH")
                
        for ev in events:
            if ev.get("severity") in ("critical", "warning"):
                ev_id = f"ev_{ev['id']}"
                technique = ev.get("technique") or {}
                name = technique.get("name", ev.get("kind"))
                msg = ev.get("message")
                nid = ev.get("node_id")
                # Sometimes node_id in event is 'unknown' or missing
                if nid and nid != "unknown":
                    self.graph.add_node(ev_id, name=name, message=msg, type="Event")
                    self.graph.add_edge(nid, ev_id, label="EXPERIENCED")

    def get_vis_json(self):
        nodes = []
        edges = []
        
        for n, props in self.graph.nodes(data=True):
            node_data = props.copy()
            node_data["id"] = str(n)
            node_type = node_data.get("type", "Unknown")
            
            node_data["label"] = node_data.get("name", str(n))
            
            if node_type == "Machine":
                node_data["color"] = "#00ffcc"
            elif node_type == "Attacker":
                node_data["color"] = "#ff0055"
            elif node_type == "Credential":
                node_data["color"] = "#ffcc00"
            elif node_type == "Event":
                node_data["color"] = "#ff8800"
            else:
                node_data["color"] = "#ffffff"
                
            nodes.append(node_data)
            
        for u, v, attrs in self.graph.edges(data=True):
            edges.append({
                "from": str(u),
                "to": str(v),
                "label": attrs.get("label", "")
            })
            
        return {"nodes": nodes, "edges": edges}
        
    def export_context_string(self) -> str:
        out = "### NETWORK TOPOLOGY GRAPH ###\n\n"
        out += "NODES:\n"
        for n, data in self.graph.nodes(data=True):
            out += f"- ID: {n} | Type: {data.get('type')} | Attributes: {data}\n"
        out += "\nEDGES (RELATIONSHIPS):\n"
        for u, v, data in self.graph.edges(data=True):
            out += f"- [{u}] --({data.get('label')})--> [{v}]\n"
        return out

kg = KnowledgeGraph()
