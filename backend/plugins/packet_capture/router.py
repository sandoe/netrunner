import asyncio
import os
import uuid
import time
from typing import Dict, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/packet_capture", tags=["Packet Capture"])

# In-memory store for running packet captures
# Maps capture_id -> capture info dict
running_captures: Dict[str, dict] = {}

class StartCaptureRequest(BaseModel):
    interface: str
    bpf_filter: Optional[str] = None
    duration: Optional[int] = None # Capture duration in seconds

class StartCaptureResponse(BaseModel):
    capture_id: str
    interface: str
    pcap_file: str
    status: str

class StopCaptureResponse(BaseModel):
    capture_id: str
    pcap_file: str
    status: str
    file_size_bytes: int

class CaptureStatusResponse(BaseModel):
    capture_id: str
    interface: str
    pcap_file: str
    status: str
    file_size_bytes: int
    start_time: float

PCAP_DIR = "/tmp/netrunner_pcaps"

def get_file_size(filepath: str) -> int:
    try:
        return os.path.getsize(filepath)
    except FileNotFoundError:
        return 0

@router.post("/start", response_model=StartCaptureResponse)
async def start_capture(req: StartCaptureRequest):
    """
    Starts a tshark packet capture on the specified interface.
    """
    os.makedirs(PCAP_DIR, exist_ok=True)
    capture_id = str(uuid.uuid4())
    pcap_file = os.path.join(PCAP_DIR, f"{capture_id}.pcap")
    
    # Construct the tshark command
    # bpf_filter is enclosed in quotes, but ideally we should sanitize further
    cmd = f"tshark -i {req.interface} -w {pcap_file}"
    if req.duration:
        cmd += f" -a duration:{req.duration}"
    if req.bpf_filter:
        cmd += f" -f '{req.bpf_filter}'"
        
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start tshark process: {str(e)}")
        
    running_captures[capture_id] = {
        "process": process,
        "interface": req.interface,
        "pcap_file": pcap_file,
        "start_time": time.time(),
        "status": "running"
    }
    
    return StartCaptureResponse(
        capture_id=capture_id,
        interface=req.interface,
        pcap_file=pcap_file,
        status="running"
    )

@router.post("/stop/{capture_id}", response_model=StopCaptureResponse)
async def stop_capture(capture_id: str):
    """
    Stops an ongoing packet capture.
    """
    if capture_id not in running_captures:
        raise HTTPException(status_code=404, detail="Capture ID not found")
        
    capture_info = running_captures[capture_id]
    process = capture_info["process"]
    
    if process.returncode is None:
        # Process is still running, attempt graceful termination
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
        except ProcessLookupError:
            pass
            
    capture_info["status"] = "stopped"
    pcap_file = capture_info["pcap_file"]
        
    return StopCaptureResponse(
        capture_id=capture_id,
        pcap_file=pcap_file,
        status="stopped",
        file_size_bytes=get_file_size(pcap_file)
    )

@router.get("/status/{capture_id}", response_model=CaptureStatusResponse)
async def get_status(capture_id: str):
    """
    Get the status of a specific capture.
    """
    if capture_id not in running_captures:
        raise HTTPException(status_code=404, detail="Capture ID not found")
        
    capture_info = running_captures[capture_id]
    process = capture_info["process"]
    
    if process.returncode is not None:
        capture_info["status"] = "stopped"
        
    pcap_file = capture_info["pcap_file"]
        
    return CaptureStatusResponse(
        capture_id=capture_id,
        interface=capture_info["interface"],
        pcap_file=pcap_file,
        status=capture_info["status"],
        file_size_bytes=get_file_size(pcap_file),
        start_time=capture_info["start_time"]
    )
    
@router.get("/list", response_model=List[CaptureStatusResponse])
async def list_captures():
    """
    List all known captures and their current status.
    """
    results = []
    for capture_id, capture_info in running_captures.items():
        process = capture_info["process"]
        if process.returncode is not None:
            capture_info["status"] = "stopped"
            
        pcap_file = capture_info["pcap_file"]
            
        results.append(CaptureStatusResponse(
            capture_id=capture_id,
            interface=capture_info["interface"],
            pcap_file=pcap_file,
            status=capture_info["status"],
            file_size_bytes=get_file_size(pcap_file),
            start_time=capture_info["start_time"]
        ))
    return results
