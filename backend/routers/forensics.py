"""
Netrunner Forensics Router — API endpoints for memory and disk forensics.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from .auth import require_admin
from ..core.forensics import (
    acquire_memory_dump, run_volatility_plugin, analyze_disk_image,
    generate_timeline, get_evidence_list, EvidenceDB,
)
from ..core.db import load_nodes_db

router = APIRouter()


class MemoryDumpRequest(BaseModel):
    node_id: str
    method: str = "lime"  # lime, dd, proc


class VolatilityRequest(BaseModel):
    evidence_id: str
    plugin: str
    extra_args: str = ""


class DiskAnalysisRequest(BaseModel):
    image_path: str


class TimelineRequest(BaseModel):
    evidence_ids: list[str]


@router.get("/forensics/evidence")
async def api_forensics_evidence_list():
    """List all evidence items."""
    evidence = get_evidence_list()
    return {"evidence": evidence, "count": len(evidence)}


@router.get("/forensics/evidence/{evidence_id}")
async def api_forensics_evidence_detail(evidence_id: str):
    """Get details of a specific evidence item."""
    if evidence_id not in EvidenceDB:
        raise HTTPException(404, "Evidence not found")
    return EvidenceDB[evidence_id]


@router.post("/forensics/memory-dump", dependencies=[Depends(require_admin)])
async def api_forensics_memory_dump(req: MemoryDumpRequest):
    """
    Acquire a memory dump from a remote node.

    Methods:
    - lime: LiME kernel module (most reliable, requires kernel headers)
    - dd: Direct dd dump (requires root)
    - proc: /proc/kcore (limited)
    """
    nodes = await load_nodes_db()
    if req.node_id not in nodes:
        raise HTTPException(404, "Node not found")

    node = nodes[req.node_id]
    host = node.get("host", "")
    username = "root"
    password = node.get("ssh_password", "")

    # Try vault credentials
    try:
        from ..core.vault import get_credential
        cred = await get_credential(req.node_id, "ssh")
        if cred:
            username = cred.get("username", username)
            password = cred.get("password", password)
    except Exception:
        pass

    if not password:
        raise HTTPException(400, "No SSH credentials available for this node")

    result = await acquire_memory_dump(
        node_id=req.node_id,
        host=host,
        username=username,
        password=password,
        method=req.method,
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Memory dump failed"))
    return result


@router.post("/forensics/volatility", dependencies=[Depends(require_admin)])
async def api_forensics_volatility(req: VolatilityRequest):
    """
    Run a Volatility3 plugin against a memory dump.

    Popular plugins:
    - linux.pslist: List processes
    - linux.bash: Recover bash history
    - linux.check_syscall: Check syscall table
    - linux.lsmod: List kernel modules
    - linux.netstat: Network connections
    - windows.pslist: Windows processes
    - windows.cmdline: Command line arguments
    - windows.netscan: Network scan
    - malfind: Detect injected code
    """
    result = await run_volatility_plugin(
        evidence_id=req.evidence_id,
        plugin=req.plugin,
        extra_args=req.extra_args,
    )

    if not result["success"]:
        raise HTTPException(400, result.get("error", "Volatility analysis failed"))
    return result


@router.post("/forensics/disk-analysis", dependencies=[Depends(require_admin)])
async def api_forensics_disk_analysis(req: DiskAnalysisRequest):
    """Analyze a disk image using The Sleuth Kit."""
    result = await analyze_disk_image(req.image_path)
    if not result["success"]:
        raise HTTPException(400, result.get("error", "Disk analysis failed"))
    return result


@router.post("/forensics/timeline", dependencies=[Depends(require_admin)])
async def api_forensics_timeline(req: TimelineRequest):
    """Generate a combined timeline from multiple evidence sources."""
    result = await generate_timeline(req.evidence_ids)
    return result


@router.get("/forensics/plugins")
async def api_forensics_plugins():
    """List available Volatility3 plugins."""
    plugins = {
        "linux": [
            {"name": "linux.pslist", "description": "List processes"},
            {"name": "linux.bash", "description": "Recover bash history"},
            {"name": "linux.check_syscall", "description": "Check syscall table"},
            {"name": "linux.lsmod", "description": "List kernel modules"},
            {"name": "linux.netstat", "description": "Network connections"},
            {"name": "linux.tty_check", "description": "TTY input"},
            {"name": "linux.proc_maps", "description": "Process memory maps"},
            {"name": "linux.timer_list", "description": "Timer entries"},
            {"name": "linux.iomem", "description": "I/O memory"},
            {"name": "linux.check_afinfo", "description": "Check AF_INFO structs"},
            {"name": "linux.check_idt", "description": "Check IDT"},
            {"name": "linux.check_modules", "description": "Check kernel modules"},
        ],
        "windows": [
            {"name": "windows.pslist", "description": "List processes"},
            {"name": "windows.pstree", "description": "Process tree"},
            {"name": "windows.cmdline", "description": "Command line arguments"},
            {"name": "windows.netscan", "description": "Network scan"},
            {"name": "windows.filescan", "description": "File scan"},
            {"name": "windows.handles", "description": "Handle table"},
            {"name": "windows.dlllist", "description": "DLL list"},
            {"name": "windows.registry.hivelist", "description": "Registry hives"},
            {"name": "windows.registry.printkey", "description": "Registry keys"},
            {"name": "windows.mftscan", "description": "MFT entries"},
        ],
        "general": [
            {"name": "malfind", "description": "Detect injected code"},
            {"name": "linpmem", "description": "Physical memory info"},
        ],
    }
    return {"plugins": plugins}


@router.get("/forensics/methods")
async def api_forensics_methods():
    """List available memory acquisition methods."""
    methods = [
        {
            "id": "lime",
            "name": "LiME (Linux Memory Extractor)",
            "description": "Kernel module for reliable memory acquisition",
            "requirements": "Root access, kernel headers, gcc",
            "reliability": "High",
            "platforms": ["Linux"],
        },
        {
            "id": "dd",
            "name": "Direct Memory Dump",
            "description": "Direct dd from /dev/mem",
            "requirements": "Root access",
            "reliability": "Medium",
            "platforms": ["Linux"],
        },
        {
            "id": "proc",
            "name": "/proc/kcore",
            "description": "Read kernel virtual memory",
            "requirements": "Root access",
            "reliability": "Low (partial)",
            "platforms": ["Linux"],
        },
    ]
    return {"methods": methods}
