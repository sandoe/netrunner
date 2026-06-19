from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from typing import Dict, Any, List
import time
import uuid
import os
import tempfile
import subprocess
from ..core.db import (
    load_alerts_db,
    load_threat_events_db,
    load_nodes_db,
    save_report_db,
    load_reports_db,
    get_report_db
)

router = APIRouter(prefix="/reports", tags=["reports"])

def generate_markdown(data: dict) -> str:
    md = f"""# Netrunner OS: Enterprise Security Report

**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['generated_at']))}
**Period:** Last {data['timerange_hours']} Hours

## Executive Summary

- **Total Alerts:** {data['alerts_summary']['total']}
- **Critical Threats:** {data['alerts_summary']['by_severity'].get('critical', 0)}
- **Active Nodes:** {data['total_active_nodes']}
- **Raw Threat Events:** {data['threats_summary']['total_events']}

## Alerts by Severity

| Severity | Count |
|----------|-------|
| Critical | {data['alerts_summary']['by_severity'].get('critical', 0)} |
| High     | {data['alerts_summary']['by_severity'].get('high', 0)} |
| Medium   | {data['alerts_summary']['by_severity'].get('medium', 0)} |
| Low      | {data['alerts_summary']['by_severity'].get('low', 0)} |

## Alerts by Status

| Status | Count |
|--------|-------|
| Open   | {data['alerts_summary']['by_status'].get('open', 0)} |
| New    | {data['alerts_summary']['by_status'].get('new', 0)} |
| Closed | {data['alerts_summary']['by_status'].get('closed', 0)} |
| False Positive | {data['alerts_summary']['by_status'].get('false_positive', 0)} |

## Top Targeted Nodes

| Target IP / Node ID | Threat Events |
|---------------------|---------------|
"""
    if not data['threats_summary']['top_targets']:
        md += "| No threat events detected | 0 |\n"
    else:
        for t in data['threats_summary']['top_targets']:
            md += f"| {t['target']} | {t['hits']} |\n"

    md += "\n---\n*Netrunner OS Enterprise Security Platform - CONFIDENTIAL*\n"
    return md


@router.post("/generate", response_model=Dict[str, Any])
async def generate_report(timerange_hours: int = 24):
    now = time.time()
    cutoff_time = now - (timerange_hours * 3600)
    
    all_alerts = await load_alerts_db()
    all_threats = await load_threat_events_db(limit=5000)
    all_nodes = await load_nodes_db()
    
    recent_alerts = [a for a in all_alerts if a["created_at"] >= cutoff_time]
    recent_threats = [t for t in all_threats if t["timestamp"] >= cutoff_time]
    
    alerts_by_severity = {
        "critical": len([a for a in recent_alerts if a["severity"] == "critical"]),
        "high": len([a for a in recent_alerts if a["severity"] == "high"]),
        "medium": len([a for a in recent_alerts if a["severity"] == "medium"]),
        "low": len([a for a in recent_alerts if a["severity"] == "low"])
    }
    
    alerts_by_status = {
        "new": len([a for a in recent_alerts if a["status"] == "new"]),
        "open": len([a for a in recent_alerts if a["status"] == "open"]),
        "closed": len([a for a in recent_alerts if a["status"] == "closed"]),
        "false_positive": len([a for a in recent_alerts if a["status"] == "false_positive"])
    }
    
    node_hits = {}
    for t in recent_threats:
        target = t["target_ip"] or t["node_id"]
        node_hits[target] = node_hits.get(target, 0) + 1
        
    top_targeted_nodes = sorted([{"target": k, "hits": v} for k, v in node_hits.items()], key=lambda x: x["hits"], reverse=True)[:5]
    
    summary_data = {
        "generated_at": now,
        "timerange_hours": timerange_hours,
        "total_active_nodes": len(all_nodes),
        "alerts_summary": {
            "total": len(recent_alerts),
            "by_severity": alerts_by_severity,
            "by_status": alerts_by_status
        },
        "threats_summary": {
            "total_events": len(recent_threats),
            "top_targets": top_targeted_nodes
        }
    }

    markdown_content = generate_markdown(summary_data)
    
    report_id = str(uuid.uuid4())
    
    report = {
        "id": report_id,
        "timerange_hours": timerange_hours,
        "summary_json": summary_data,
        "markdown_content": markdown_content,
        "created_at": now
    }
    
    await save_report_db(report)
    
    return report

@router.get("", response_model=List[Dict[str, Any]])
async def list_reports():
    reports = await load_reports_db()
    # Don't send huge markdown payloads in the list view
    for r in reports:
        r.pop("markdown_content", None)
    return reports

@router.get("/{report_id}/download")
async def download_report(report_id: str, format: str = "md"):
    report = await get_report_db(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    valid_formats = ["md", "tex", "pdf", "docx"]
    if format not in valid_formats:
        raise HTTPException(status_code=400, detail="Invalid format")
        
    md_content = report["markdown_content"]
    
    if format == "md":
        return PlainTextResponse(content=md_content, media_type="text/markdown", headers={
            "Content-Disposition": f"attachment; filename=report_{report_id}.md"
        })
        
    with tempfile.TemporaryDirectory() as tmpdir:
        md_file = os.path.join(tmpdir, "report.md")
        out_file = os.path.join(tmpdir, f"report.{format}")
        
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        try:
            # Call pandoc to convert
            # For PDF via latex: pandoc report.md -o report.pdf
            subprocess.run(
                ["pandoc", md_file, "-o", out_file],
                check=True,
                capture_output=True
            )
            
            # We must copy the file out of tmpdir to return it, or use FileResponse with background tasks?
            # Actually, since FastAPI FileResponse opens the file, it might conflict with tmpdir deletion.
            # Easiest way: read into memory if small, or keep it in a global tmp folder, but here's a trick:
            with open(out_file, "rb") as f:
                content = f.read()
                
            media_types = {
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "tex": "application/x-tex"
            }
            
            from fastapi.responses import Response
            return Response(content=content, media_type=media_types[format], headers={
                "Content-Disposition": f"attachment; filename=report_{report_id}.{format}"
            })
            
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"Pandoc conversion failed: {e.stderr.decode()}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Pandoc is not installed on the server.")
