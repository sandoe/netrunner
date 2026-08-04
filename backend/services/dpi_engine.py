class MockDPIEngine:
    @staticmethod
    def analyze(payload: bytes) -> str:
        if payload.startswith(b"\x10"):
            return "MQTT (Connect)"
        if payload.startswith(b"AMQP"):
            return "AMQP"
        if (
            payload.startswith(b"\x40")
            or payload.startswith(b"\x50")
            or payload.startswith(b"\x60")
        ):
            return "CoAP"
        # Modbus TCP typically starts with transaction ID (2 bytes) then protocol ID (0x00 0x00)
        if len(payload) >= 4 and payload[2:4] == b"\x00\x00":
            return "Modbus TCP"
        # Modbus RTU rough check
        if (
            len(payload) >= 4
            and payload[0] in range(1, 248)
            and payload[1] in [1, 2, 3, 4, 5, 6, 15, 16]
        ):
            return "Modbus RTU (or binary serial)"
        # QUIC mock (starts with 0xc0 or similar short header)
        if len(payload) > 0 and (payload[0] & 0x80) == 0x80:
            return "QUIC (Long Header)"
        if len(payload) > 0 and (payload[0] & 0x40) == 0x40:
            return "QUIC (Short Header)"

        return "UDP / Unknown"
