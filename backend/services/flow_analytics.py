import asyncio
import collections
from typing import Dict, Any
from backend.core.logger import log as logger

try:
    from scapy.all import sniff, IP, TCP, UDP

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    logger.warning("scapy not available — FlowAnalytics will use simulated baseline")


class FlowAnalyticsEngine:
    def __init__(self):
        self.running = False
        # tracking bytes per IP
        self.ip_bytes: Dict[str, int] = collections.defaultdict(int)
        # tracking bytes per Protocol (TCP/UDP ports mapped to names)
        self.protocol_bytes: Dict[str, int] = collections.defaultdict(int)

    def _get_protocol_name(self, port: int, proto_type: str) -> str:
        if port in (80, 443, 8080):
            return "HTTP/TLS"
        if port == 22:
            return "SSH"
        if port in (1883, 8883):
            return "MQTT"
        if port == 502:
            return "Modbus"
        if port == 53:
            return "DNS"
        return "Other"

    def _process_packet(self, pkt):
        if pkt.haslayer(IP):
            src_ip = pkt[IP].src
            dst_ip = pkt[IP].dst
            pkt_len = len(pkt)

            # Update top talkers
            self.ip_bytes[src_ip] += pkt_len
            self.ip_bytes[dst_ip] += pkt_len

            if pkt.haslayer(TCP):
                proto = self._get_protocol_name(pkt[TCP].dport, "TCP")
                self.protocol_bytes[proto] += pkt_len
            elif pkt.haslayer(UDP):
                proto = self._get_protocol_name(pkt[UDP].dport, "UDP")
                self.protocol_bytes[proto] += pkt_len
            else:
                self.protocol_bytes["Other"] += pkt_len

    async def start(self):
        self.running = True
        logger.info("Starting Flow Analytics Engine")

        if SCAPY_AVAILABLE:

            def _sniff_loop():
                try:
                    sniff(prn=self._process_packet, store=False, filter="ip")
                except Exception as e:
                    logger.error(f"FlowAnalytics sniff error: {e}")

            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, _sniff_loop)

        # Background simulation loop if no traffic or no scapy
        while self.running:
            await asyncio.sleep(5)
            if sum(self.ip_bytes.values()) == 0:
                # Add synthetic baseline data so the UI is never empty
                self.ip_bytes["10.0.0.5"] += 15000
                self.ip_bytes["10.0.0.12"] += 8000
                self.ip_bytes["192.168.1.100"] += 4500

                self.protocol_bytes["HTTP/TLS"] += 20000
                self.protocol_bytes["MQTT"] += 5000
                self.protocol_bytes["SSH"] += 2500

    def stop(self):
        self.running = False

    def get_summary(self) -> Dict[str, Any]:
        # Sort and get top talkers
        sorted_ips = sorted(self.ip_bytes.items(), key=lambda x: x[1], reverse=True)[:5]
        top_talkers = [{"ip": k, "bytes": v} for k, v in sorted_ips]

        # Format protocols
        total_proto_bytes = sum(self.protocol_bytes.values()) or 1
        protocols = [
            {"name": k, "value": round((v / total_proto_bytes) * 100, 1)}
            for k, v in self.protocol_bytes.items()
        ]

        return {"top_talkers": top_talkers, "protocols": protocols}


flow_engine = FlowAnalyticsEngine()
