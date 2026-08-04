import asyncio
import hashlib
import time
import httpx
from backend.core.logger import log as logger
from backend.core.db import insert_alert, load_nodes_db

_running = False
# In a real environment, this might be pulled from a config DB or env var.
# Using 'netrunner-corp.internal' as our mock root domain for simulation,
# and maybe falling back to something safe to query for real data just to demonstrate.
TARGET_ROOT_DOMAIN = "netrunner-corp.internal"
# To demonstrate real JSON parsing, we can query a public domain safely, but we'll simulate the output if it fails.


def _make_alert_id(prefix: str, subject: str, timestamp: int | None = None) -> str:
    """Create a stable-size alert ID that fits AlertModel.id (VARCHAR(50))."""
    digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}_{timestamp or int(time.time())}"


async def _fetch_crt_sh(domain: str):
    """
    Query crt.sh for certificate transparency logs of the target domain.
    """
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"[EASM] Failed to fetch crt.sh data: {e}")
    return []


async def _easm_loop():
    logger.info("[EASM] External Attack Surface Management engine started.")
    # Initialize a baseline of "known" subdomains that the CISO manages
    # Usually this comes from an authoritative asset inventory
    known_subdomains = {
        f"www.{TARGET_ROOT_DOMAIN}",
        f"api.{TARGET_ROOT_DOMAIN}",
        f"dashboard.{TARGET_ROOT_DOMAIN}",
    }

    while _running:
        try:
            logger.info(
                f"[EASM] Querying public CT logs for root domain: {TARGET_ROOT_DOMAIN}"
            )
            # Try to fetch real data (even if domain is internal, we just simulate the JSON structure)
            # Since netrunner-corp.internal doesn't exist on crt.sh, we will manually inject a shadow domain for the simulation

            # Simulated API Response representing Shadow IT
            ct_logs = [
                {"name_value": f"www.{TARGET_ROOT_DOMAIN}"},
                {"name_value": f"dev-vpn-test.{TARGET_ROOT_DOMAIN}"},  # The Shadow IT
                {"name_value": f"api.{TARGET_ROOT_DOMAIN}"},
            ]

            # If we wanted to query a real domain for testing:
            # real_logs = await _fetch_crt_sh("example.com")

            discovered_subdomains = set()
            for entry in ct_logs:
                # name_value can contain multiple domains separated by newlines
                names = entry.get("name_value", "").split("\n")
                for name in names:
                    clean_name = name.strip().lower()
                    if clean_name:
                        discovered_subdomains.add(clean_name)

            for subdomain in discovered_subdomains:
                if subdomain not in known_subdomains:
                    # Found Shadow IT!
                    alert_id = _make_alert_id("easm_shadow", subdomain)
                    description = (
                        f"**[SHADOW IT DETECTED via OSINT]**\n\n"
                        f"The External Attack Surface Management (EASM) engine passively discovered "
                        f"a new public SSL/TLS certificate issued for `{subdomain}` via Certificate Transparency logs (crt.sh).\n\n"
                        f"This asset is **NOT** listed in the centralized IT asset inventory. "
                        f"This likely represents an unmanaged 'Shadow IT' service spun up by developers, "
                        f"which could expose the organization to significant risk if it contains vulnerabilities."
                    )
                    alert = {
                        "id": alert_id,
                        "title": f"EASM: Unmanaged Asset Exposed ({subdomain})",
                        "description": description,
                        "severity": "high",
                        "status": "new",
                        "target_node": "external_surface",
                        "created_at": time.time(),
                        "updated_at": time.time(),
                    }
                    await insert_alert(alert)
                    logger.warning(
                        f"[EASM] SHADOW IT DETECTED: {subdomain} is unmanaged!"
                    )

                    # Add to known to prevent duplicate alerts in simulation
                    known_subdomains.add(subdomain)

                    # Simulate Port correlation! Check if this Shadow IT is exposing critical ports
                    import random

                    if random.random() > 0.5:
                        ports = [3389, 22, 23, 445]
                        exposed_port = random.choice(ports)
                        simulated_ip = f"203.0.113.{random.randint(10, 250)}"

                        port_alert = {
                            "id": _make_alert_id(
                                "easm_port", f"{simulated_ip}:{exposed_port}"
                            ),
                            "title": f"EASM: Critical Port {exposed_port} Exposed on {simulated_ip}",
                            "description": (
                                f"**[EASM - EXPOSED CRITICAL SERVICE]**\n\n"
                                f"Passive OSINT correlation (simulating Shodan/Censys) indicates that the Shadow IT domain `{subdomain}` "
                                f"resolves to `{simulated_ip}`, which is exposing port `{exposed_port}` directly to the public internet.\n\n"
                                f"**Risk:** Critical management ports should NEVER be exposed directly to the internet. They are highly susceptible to brute-force and zero-day attacks."
                            ),
                            "severity": "critical",
                            "status": "new",
                            "target_node": "external_surface",
                            "created_at": time.time(),
                            "updated_at": time.time(),
                        }
                        await insert_alert(port_alert)
                        logger.critical(
                            f"[EASM] EXPOSED PORT {exposed_port} found for {subdomain}!"
                        )

        except Exception as e:
            logger.error(f"[EASM] Analysis cycle failed: {e}")

        await asyncio.sleep(3600)  # Sleep for 1 hour


def start_easm_engine():
    global _running
    if not _running:
        _running = True
        asyncio.create_task(_easm_loop())


def stop_easm_engine():
    global _running
    _running = False
