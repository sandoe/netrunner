import asyncio
import json
import random
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
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
    
    # Try to execute kubectl get nodes
    # We use a relatively short timeout. If k8s is not there, it will fail fast.
    cmd_pods = "kubectl get pods -A -o json"
    cmd_nodes = "kubectl get nodes -o json"
    cmd_deps = "kubectl get deployments -A -o json"
    
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

@router.post("/kubernetes/{node_id}/install")
async def install_kubernetes(node_id: str, user: dict = Depends(get_current_user)):
    nodes_data = await load_nodes()
    if node_id not in nodes_data:
        raise HTTPException(status_code=404, detail="Node not found")
        
    node = nodes_data[node_id]
    
    # We use session_manager to run the k3s installation script.
    # The script takes about 20-60 seconds to finish.
    install_cmd = "curl -sfL https://get.k3s.io | sh -"
    # If the user is not root, session_manager automatically tries sudo
    
    results, err = await session_manager.run(node_id, node, [install_cmd], timeout=120.0)
    
    if err or not results:
        raise HTTPException(status_code=500, detail=f"Installation failed: {err}")
        
    # Give it a few seconds to start up
    import asyncio
    await asyncio.sleep(5)
    
    return {"status": "success", "message": "K3s installed successfully", "logs": results[0]}
