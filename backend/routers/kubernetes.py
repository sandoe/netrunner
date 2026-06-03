import asyncio
import json
import random
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .auth import get_current_user
from .nodes import load_nodes, _get_node_with_creds
from ..core.session import session_manager

router = APIRouter(tags=["kubernetes"])

def generate_mock_k8s_data() -> Dict[str, Any]:
    """Generates an impressive large-scale mock Kubernetes cluster state for demonstrations."""
    namespaces = ["default", "kube-system", "istio-system", "monitoring", "ingress-nginx", "ai-inference", "data-pipeline"]
    
    # Generate 5-15 Nodes
    num_nodes = random.randint(5, 15)
    nodes = []
    for i in range(num_nodes):
        nodes.append({
            "name": f"worker-node-{i+1}.cluster.local",
            "status": "Ready",
            "cpu_capacity": random.choice([4, 8, 16, 32]),
            "memory_capacity": f"{random.choice([16, 32, 64, 128])}Gi",
            "kubelet_version": "v1.28.3"
        })
        
    # Generate 40-100 Pods
    num_pods = random.randint(40, 100)
    pods = []
    for i in range(num_pods):
        ns = random.choice(namespaces)
        status = random.choices(["Running", "Pending", "CrashLoopBackOff", "Completed"], weights=[0.8, 0.05, 0.1, 0.05])[0]
        restarts = 0
        if status == "CrashLoopBackOff":
            restarts = random.randint(1, 50)
        elif status == "Running":
            restarts = random.randint(0, 2)
            
        pods.append({
            "name": f"{ns}-workload-{random.randint(1000,9999)}-{random.randint(10000,99999)}",
            "namespace": ns,
            "status": status,
            "restarts": restarts,
            "node": random.choice(nodes)["name"] if status == "Running" else "",
            "age": f"{random.randint(1, 48)}h"
        })

    # Generate Deployments
    deployments = []
    for ns in namespaces:
        num_deps = random.randint(2, 6)
        for i in range(num_deps):
            desired = random.randint(1, 10)
            available = desired if random.random() > 0.1 else max(0, desired - random.randint(1, desired))
            deployments.append({
                "name": f"deploy-{ns}-{i+1}",
                "namespace": ns,
                "desired": desired,
                "available": available,
                "age": f"{random.randint(1, 60)}d"
            })
            
    return {
        "nodes": nodes,
        "pods": pods,
        "deployments": deployments,
        "cluster_health": "Degraded" if any(p["status"] == "CrashLoopBackOff" for p in pods) else "Healthy",
        "total_cpu": sum(n["cpu_capacity"] for n in nodes),
        "total_memory_gb": sum(int(n["memory_capacity"].replace("Gi", "")) for n in nodes),
        "mock": True
    }

@router.get("/kubernetes/{node_id}/status")
async def get_kubernetes_status(node_id: str, mock: bool = False, user: dict = Depends(get_current_user)):
    if mock:
        return generate_mock_k8s_data()
        
    nodes_data = await load_nodes()
    if node_id not in nodes_data:
        raise HTTPException(status_code=404, detail="Node not found")

    node = await _get_node_with_creds(node_id, nodes_data)
    
    # Use sudo if available to read K3s kubeconfig, and sh -lc to get the right PATH
    # Use sudo if available to read K3s kubeconfig, and sh -lc to get the right PATH
    sudo_prefix = "sudo -n"
    if "sudo_password" in node and node["sudo_password"]:
        import shlex
        sudo_prefix = f"echo {shlex.quote(node['sudo_password'])} | sudo -S"

    # We try both standard kubectl and K3s kubeconfig with fallback
    kubectl_base = "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml; kubectl"
    
    cmd_pods = f"({sudo_prefix} sh -lc '{kubectl_base} get pods -A -o json' || sh -lc '{kubectl_base} get pods -A -o json') 2>/dev/null"
    cmd_nodes = f"({sudo_prefix} sh -lc '{kubectl_base} get nodes -o json' || sh -lc '{kubectl_base} get nodes -o json') 2>/dev/null"
    cmd_deps = f"({sudo_prefix} sh -lc '{kubectl_base} get deployments -A -o json' || sh -lc '{kubectl_base} get deployments -A -o json') 2>/dev/null"
    
    results, err = await session_manager.run(node_id, node, [cmd_pods, cmd_nodes, cmd_deps], timeout=10.0)
    
    is_real = True
    parsed_pods = []
    parsed_nodes = []
    parsed_deps = []
    
    # Check if kubectl succeeded
    if not err and results and len(results) == 3:
        try:
            # Check if output looks like JSON and doesn't contain "command not found"
            if "command not found" not in results[0]["output"].lower() and "{" in results[0]["output"]:
                pods_raw = json.loads(results[0]["output"])
                for item in pods_raw.get("items", []):
                    status_phase = item.get("status", {}).get("phase", "Unknown")
                    restarts = sum(cs.get("restartCount", 0) for cs in item.get("status", {}).get("containerStatuses", []))
                    if status_phase == "Running" and any(not cs.get("ready", True) for cs in item.get("status", {}).get("containerStatuses", [])):
                         # E.g. CrashLoopBackOff or Error
                         state_reason = item.get("status", {}).get("containerStatuses", [{}])[0].get("state", {}).get("waiting", {}).get("reason")
                         if state_reason:
                             status_phase = state_reason

                    parsed_pods.append({
                        "name": item.get("metadata", {}).get("name", "unknown"),
                        "namespace": item.get("metadata", {}).get("namespace", "default"),
                        "status": status_phase,
                        "restarts": restarts,
                        "node": item.get("spec", {}).get("nodeName", ""),
                        "age": item.get("metadata", {}).get("creationTimestamp", "")
                    })
                
                nodes_raw = json.loads(results[1]["output"])
                for item in nodes_raw.get("items", []):
                    conditions = item.get("status", {}).get("conditions", [])
                    ready_cond = next((c for c in conditions if c.get("type") == "Ready"), {})
                    status = "Ready" if ready_cond.get("status") == "True" else "NotReady"
                    
                    parsed_nodes.append({
                        "name": item.get("metadata", {}).get("name", "unknown"),
                        "status": status,
                        "cpu_capacity": int(item.get("status", {}).get("capacity", {}).get("cpu", "1")),
                        "memory_capacity": item.get("status", {}).get("capacity", {}).get("memory", "0Ki"),
                        "kubelet_version": item.get("status", {}).get("nodeInfo", {}).get("kubeletVersion", "")
                    })
                
                deps_raw = json.loads(results[2]["output"])
                for item in deps_raw.get("items", []):
                    parsed_deps.append({
                        "name": item.get("metadata", {}).get("name", "unknown"),
                        "namespace": item.get("metadata", {}).get("namespace", "default"),
                        "desired": item.get("spec", {}).get("replicas", 0),
                        "available": item.get("status", {}).get("availableReplicas", 0),
                        "age": item.get("metadata", {}).get("creationTimestamp", "")
                    })
            else:
                is_real = False
        except Exception as e:
            print("Failed to parse kubectl output:", e)
            is_real = False
    else:
        is_real = False
        
    if is_real and len(parsed_nodes) > 0:
        return {
            "nodes": parsed_nodes,
            "pods": parsed_pods,
            "deployments": parsed_deps,
            "cluster_health": "Degraded" if any(p["status"] not in ("Running", "Succeeded") for p in parsed_pods) else "Healthy",
            "total_cpu": sum(n["cpu_capacity"] for n in parsed_nodes),
            "total_memory_gb": len(parsed_nodes) * 16, # approximation since memory parsing from Ki to Gi is complex
            "mock": False
        }
    else:
        raise HTTPException(status_code=404, detail="Kubernetes cluster not detected or kubectl failed.")

class InstallRequest(BaseModel):
    sudo_password: Optional[str] = None

@router.post("/kubernetes/{node_id}/install")
async def install_kubernetes(node_id: str, req: InstallRequest = None, user: dict = Depends(get_current_user)):
    nodes_data = await load_nodes()
    if node_id not in nodes_data:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node = nodes_data[node_id]
    
    # We write the command to a file and execute it so it runs robustly and logs output
    import shlex
    install_script = "curl -sfL https://get.k3s.io > /tmp/k3s_install.sh && sh /tmp/k3s_install.sh > /tmp/k3s_install.log 2>&1"
    
    sudo_prefix = "sudo"
    sudo_pass = (req.sudo_password if req and req.sudo_password else node.get("sudo_password"))
    if sudo_pass:
        sudo_prefix = f"echo {shlex.quote(sudo_pass)} | sudo -S"
        
    init_cmd = f"{sudo_prefix} sh -lc 'echo Starting Kubernetes Installation... > /tmp/k3s_install.log'"
    install_cmd = f"{sudo_prefix} sh -lc {shlex.quote(install_script)}"
    
    # Initialize the log file so the frontend can start reading it immediately
    await session_manager.run(node_id, node, [init_cmd], timeout=5.0)
    
    results, err = await session_manager.run(node_id, node, [install_cmd], timeout=120.0)
    
    if err or not results:
        # Fetch the logs to see what went wrong
        log_res, _ = await session_manager.run(node_id, node, ["cat /tmp/k3s_install.log"], timeout=10.0)
        logs = log_res[0]["output"] if log_res and isinstance(log_res[0], dict) else (log_res[0] if log_res else str(err))
        raise HTTPException(status_code=500, detail=f"Installation failed:\\n{logs}")
        
    # Give it a few seconds to start up
    import asyncio
    await asyncio.sleep(5)
    
    # Clean up the log and script files after successful installation
    await session_manager.run(node_id, node, [f"{sudo_prefix} rm -f /tmp/k3s_install.log /tmp/k3s_install.sh"], timeout=5.0)
    
    # Make k3s config readable so polling works without sudo
    await session_manager.run(node_id, node, [f"{sudo_prefix} chmod 644 /etc/rancher/k3s/k3s.yaml"], timeout=5.0)
    
    out = results[0]["output"] if results and isinstance(results[0], dict) else (results[0] if results else "")
    return {"status": "success", "message": "K3s installed successfully", "logs": out}

@router.get("/kubernetes/{node_id}/install/logs")
async def get_install_logs(node_id: str, user: dict = Depends(get_current_user)):
    nodes_data = await load_nodes()
    if node_id not in nodes_data:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node = nodes_data[node_id]
    
    results, err = await session_manager.run(node_id, node, ["cat /tmp/k3s_install.log 2>/dev/null || echo 'Waiting for logs...'"], timeout=10.0)
    
    out = results[0]["output"] if results and isinstance(results[0], dict) else (results[0] if results else "Error fetching logs")
    return {"logs": out}

class DeployRequest(BaseModel):
    target: str

@router.post("/kubernetes/{node_id}/deploy")
async def deploy_target(node_id: str, req: DeployRequest, user: dict = Depends(get_current_user)):
    nodes_data = await load_nodes()
    if node_id not in nodes_data:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node = nodes_data[node_id]
    
    sudo_prefix = "sudo -n"
    if "sudo_password" in node and node["sudo_password"]:
        import shlex
        sudo_prefix = f"echo {shlex.quote(node['sudo_password'])} | sudo -S"

    kubectl_base = "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml; kubectl"
    
    manifest_url = ""
    if req.target == "juice-shop":
        manifest_url = "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/examples/multibases/dev/juice-shop-deployment.yaml"
        # Since juice shop manifest might be complex, let's just use a simple one:
        manifest_url = "https://raw.githubusercontent.com/sandoe/netrunner-resources/main/juice-shop.yaml"
        # Wait, if that doesn't exist, we can just echo a manifest and apply it
        manifest_cmd = f"""cat << 'EOF' | {kubectl_base} apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: juice-shop
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: juice-shop
  template:
    metadata:
      labels:
        app: juice-shop
    spec:
      containers:
      - name: juice-shop
        image: bkimminich/juice-shop
        ports:
        - containerPort: 3000
---
apiVersion: v1
kind: Service
metadata:
  name: juice-shop
  namespace: default
spec:
  ports:
  - port: 80
    targetPort: 3000
  selector:
    app: juice-shop
EOF"""
    else:
        raise HTTPException(status_code=400, detail="Unknown target")
        
    cmd = f"({sudo_prefix} sh -lc '{manifest_cmd}' || sh -lc '{manifest_cmd}') 2>/dev/null"
    results, err = await session_manager.run(node_id, node, [cmd], timeout=30.0)
    
    if err or not results:
        raise HTTPException(status_code=500, detail=f"Failed to deploy target: {err}")
        
    out = results[0]["output"] if results and isinstance(results[0], dict) else (results[0] if results else "")
    return {"status": "success", "message": f"Deployed {req.target}", "output": out}

@router.delete("/kubernetes/{node_id}/pods/{namespace}/{pod_name}")
async def delete_pod(node_id: str, namespace: str, pod_name: str, user: dict = Depends(get_current_user)):
    nodes_data = await load_nodes()
    if node_id not in nodes_data:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node = nodes_data[node_id]
    
    sudo_prefix = "sudo -n"
    if "sudo_password" in node and node["sudo_password"]:
        import shlex
        sudo_prefix = f"echo {shlex.quote(node['sudo_password'])} | sudo -S"

    kubectl_base = "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml; kubectl"
    import shlex
    ns_quoted = shlex.quote(namespace)
    pod_quoted = shlex.quote(pod_name)
    
    cmd = f"({sudo_prefix} sh -lc '{kubectl_base} delete pod {pod_quoted} -n {ns_quoted}' || sh -lc '{kubectl_base} delete pod {pod_quoted} -n {ns_quoted}') 2>/dev/null"
    
    results, err = await session_manager.run(node_id, node, [cmd], timeout=15.0)
    
    if err or not results:
        raise HTTPException(status_code=500, detail=f"Failed to delete pod: {err}")
        
    out = results[0]["output"] if results and isinstance(results[0], dict) else (results[0] if results else "")
    return {"status": "success", "message": f"Deleted pod {pod_name}", "output": out}

class MigrateRequest(BaseModel):
    container_id: str

@router.post("/kubernetes/{node_id}/migrate")
async def migrate_container(node_id: str, req: MigrateRequest, user: dict = Depends(get_current_user)):
    nodes_data = await load_nodes()
    if node_id not in nodes_data:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node = nodes_data[node_id]
    
    sudo_prefix = "sudo -n"
    if "sudo_password" in node and node["sudo_password"]:
        import shlex
        sudo_prefix = f"echo {shlex.quote(node['sudo_password'])} | sudo -S"

    import shlex
    cid_quoted = shlex.quote(req.container_id)
    
    # 1. Inspect the container
    inspect_cmd = f"{sudo_prefix} docker inspect {cid_quoted} 2>/dev/null"
    res, err = await session_manager.run(node_id, node, [inspect_cmd], timeout=10.0)
    
    if err or not res or not res[0]["output"]:
        raise HTTPException(status_code=400, detail=f"Failed to inspect container: {err}")
        
    try:
        inspect_data = json.loads(res[0]["output"])
        container = inspect_data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse inspect output: {e}")
        
    # Extract metadata
    name = container["Name"].lstrip("/")
    # Clean name for kubernetes (lowercase, alphanumeric, dashes)
    import re
    k8s_name = re.sub(r'[^a-z0-9-]', '-', name.lower()).strip('-')
    image = container["Config"]["Image"]
    
    # Extract exposed ports
    ports_yaml = ""
    ports_map = container["Config"].get("ExposedPorts", {})
    if not ports_map and "Ports" in container["NetworkSettings"]:
        # Fallback to bound ports if ExposedPorts is empty
        for p in container["NetworkSettings"]["Ports"]:
            ports_map[p] = {}
            
    port_list = []
    for port_proto in ports_map.keys():
        port = port_proto.split("/")[0]
        port_list.append(port)
        ports_yaml += f"        - containerPort: {port}\n"
        
    # Build YAML manifest
    manifest = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {k8s_name}
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {k8s_name}
  template:
    metadata:
      labels:
        app: {k8s_name}
    spec:
      containers:
      - name: {k8s_name}
        image: {image}
"""
    if ports_yaml:
        manifest += f"        ports:\n{ports_yaml}"
        
    # Add Service if ports are defined
    if port_list:
        svc_ports = ""
        for port in port_list:
            svc_ports += f"  - port: {port}\n    targetPort: {port}\n"
            
        manifest += f"""---
apiVersion: v1
kind: Service
metadata:
  name: {k8s_name}
  namespace: default
spec:
  ports:
{svc_ports}  selector:
    app: {k8s_name}
"""

    kubectl_base = "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml; kubectl"
    deploy_cmd = f"cat << 'EOF' | {kubectl_base} apply -f -\n{manifest}\nEOF"
    
    # Apply to K8s and stop original docker container
    cmd = f"({sudo_prefix} sh -lc '{deploy_cmd}' || sh -lc '{deploy_cmd}') 2>/dev/null && {sudo_prefix} docker stop {cid_quoted} && {sudo_prefix} docker rm {cid_quoted}"
    
    deploy_res, deploy_err = await session_manager.run(node_id, node, [cmd], timeout=30.0)
    
    if deploy_err and "kubectl" not in str(deploy_err):
        # We ignore errors from docker stop/rm if apply succeeded, but if kubectl failed we care
        pass
        
    out = deploy_res[0]["output"] if deploy_res and isinstance(deploy_res[0], dict) else (deploy_res[0] if deploy_res else "")
    return {"status": "success", "message": f"Migrated {name} to Kubernetes", "output": out}
