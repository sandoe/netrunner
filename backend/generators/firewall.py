"""Firewall configuration generators: iptables, nftables, ufw."""

from __future__ import annotations


def _rule_value(rule: dict, *keys: str) -> str:
    if not isinstance(rule, dict):
        return ""
    for key in keys:
        value = rule.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    normalized = {
        str(k).lower().replace("_", "").replace("-", ""): v for k, v in rule.items()
    }
    for key in keys:
        value = normalized.get(key.lower().replace("_", "").replace("-", ""))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def gen_iptables(cfg: dict) -> list[str]:
    cmds = [
        "# ── iptables restore / baseline ─────────────────────────────",
        "iptables -F",
        "iptables -t nat -F",
        "iptables -t mangle -F",
        "iptables -X",
    ]

    defaults = cfg.get("defaults", {})
    for chain, policy in defaults.items():
        chain = str(chain).upper()
        policy = str(policy).upper()
        if chain in ("INPUT", "FORWARD", "OUTPUT") and policy in ("ACCEPT", "DROP"):
            cmds.append(f"iptables -P {chain} {policy}")

    for rule in cfg.get("rules", []):
        table = str(rule.get("table", "filter")).strip() or "filter"
        chain = str(rule.get("chain", "INPUT")).strip().upper() or "INPUT"
        parts = ["iptables"]
        if table != "filter":
            parts += ["-t", table]
        parts += ["-A", chain]
        proto = _rule_value(rule, "protocol", "proto")
        iif = _rule_value(rule, "iif", "iifname", "in_iface", "iface", "interface")
        oif = _rule_value(rule, "oif", "oifname", "out_iface")
        saddr = _rule_value(rule, "saddr", "source", "src")
        daddr = _rule_value(rule, "daddr", "destination", "dest", "dst")
        ct_state = _rule_value(rule, "ct_state", "ctstate", "state")
        sport = _rule_value(rule, "sport", "source_port", "src_port")
        dport = _rule_value(rule, "dport", "destination_port", "dest_port", "port")
        if proto:
            parts += ["-p", proto]
        if iif:
            parts += ["-i", iif]
        if oif:
            parts += ["-o", oif]
        if saddr:
            parts += ["-s", saddr]
        if daddr:
            parts += ["-d", daddr]
        if ct_state:
            parts += ["-m", "conntrack", "--ctstate", ct_state.upper()]
        if sport:
            parts += ["--sport", sport]
        if dport:
            parts += ["--dport", dport]

        action = str(rule.get("action", "ACCEPT")).upper()
        if action in ("DNAT", "SNAT", "MASQUERADE"):
            parts += ["-j", action]
            nat_addr = _rule_value(rule, "nat_addr", "to", "to_addr")
            if action in ("DNAT", "SNAT") and nat_addr:
                flag = "--to-destination" if action == "DNAT" else "--to-source"
                parts += [flag, nat_addr]
        elif action == "LOG":
            parts += ["-j", "LOG"]
            if rule.get("log_prefix"):
                parts += ["--log-prefix", f'"{rule["log_prefix"]}"']
        else:
            parts += ["-j", action]

        cmds.append(" ".join(parts))
    return cmds


def gen_ufw(cfg: dict) -> list[str]:
    cmds = [
        "# ── UFW baseline ────────────────────────────────────────────",
        "ufw --force reset",
    ]

    defaults = cfg.get("defaults", {})
    incoming = str(defaults.get("incoming", "deny")).lower()
    outgoing = str(defaults.get("outgoing", "allow")).lower()
    routed = str(defaults.get("routed", "deny")).lower()
    if incoming in ("allow", "deny", "reject"):
        cmds.append(f"ufw default {incoming} incoming")
    if outgoing in ("allow", "deny", "reject"):
        cmds.append(f"ufw default {outgoing} outgoing")
    if routed in ("allow", "deny", "reject"):
        cmds.append(f"ufw default {routed} routed")

    for rule in cfg.get("rules", []):
        action = str(rule.get("action", "allow")).lower()
        if action not in ("allow", "deny", "reject", "limit"):
            action = "allow"

        parts = ["ufw"]
        if rule.get("direction") in ("in", "out"):
            parts += [str(rule["direction"])]
        parts += [action]

        iif = _rule_value(rule, "iif", "iifname", "iface", "interface", "in_iface")
        proto = _rule_value(rule, "protocol", "proto").lower()
        port = _rule_value(rule, "port", "dport", "destination_port", "dest_port")
        saddr = _rule_value(rule, "saddr", "source", "src")
        daddr = _rule_value(rule, "daddr", "destination", "dest", "dst")
        comment = _rule_value(rule, "comment")
        if iif:
            parts += ["on", iif]
        if proto:
            if port:
                parts.append(f"{port}/{proto}")
        elif port:
            parts.append(port)

        if saddr:
            parts += ["from", saddr]
        elif action in ("allow", "deny", "reject", "limit"):
            parts += ["from", "any"]

        if daddr:
            parts += ["to", daddr]
        elif port or iif or rule.get("direction"):
            parts += ["to", "any"]

        if comment:
            parts.append(f"# {comment}")
        cmds.append(" ".join(parts))

    if cfg.get("enabled", True):
        cmds.append("ufw --force enable")
    else:
        cmds.append("ufw disable")
    cmds.append("ufw status verbose")
    return cmds


def _nft_value(rule: dict, *keys: str) -> str:
    return _rule_value(rule, *keys)


def _nft_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _nft_rule_expr(rule: dict) -> str:
    p = []
    iifname = _nft_value(rule, "iifname", "iif", "in_iface", "iface")
    oifname = _nft_value(rule, "oifname", "oif", "out_iface")
    if iifname:
        p.append(f'iifname "{_nft_quote(iifname)}"')
    if oifname:
        p.append(f'oifname "{_nft_quote(oifname)}"')
    if rule.get("saddr"):
        p.append(f"ip saddr {rule['saddr']}")
    if rule.get("daddr"):
        p.append(f"ip daddr {rule['daddr']}")
    proto = rule.get("protocol", "")
    has_port = rule.get("sport") or rule.get("dport")
    if proto and proto != "any":
        if not (has_port and proto in ("tcp", "udp")):
            p.append(f"ip protocol {proto}")
    if rule.get("sport") and proto in ("tcp", "udp"):
        p.append(f"{proto} sport {rule['sport']}")
    if rule.get("dport") and proto in ("tcp", "udp"):
        p.append(f"{proto} dport {rule['dport']}")
    if rule.get("ct_state"):
        p.append(f"ct state {rule['ct_state']}")
    action = rule.get("action", "accept")
    if action == "dnat":
        p.append(f"dnat to {rule.get('nat_addr','')}")
    elif action == "snat":
        p.append(f"snat to {rule.get('nat_addr','')}")
    elif action == "masquerade":
        p.append("masquerade")
    elif action == "log":
        p.append(f'log prefix "{rule.get("log_prefix","nft: ")}"')
    else:
        p.append(action)
    if rule.get("comment"):
        p.append(f'comment "{rule["comment"]}"')
    return " ".join(p)


def _build_nft_script(cfg: dict) -> list[str]:
    op = cfg.get("operation", "overwrite")
    lines: list[str] = []

    if op in ["flush", "overwrite"]:
        lines.append("flush ruleset")
        lines.append("")

    if op == "flush":
        return lines

    if op == "delete":
        for tbl in cfg.get("tables", []):
            f, n = tbl.get("family", "ip"), tbl["name"]
            for ch in tbl.get("chains", []):
                cn = ch["name"]
                for rule in ch.get("rules", []):
                    expr = _nft_rule_expr(rule)
                    if expr:
                        lines.append(f"delete rule {f} {n} {cn} {expr}")
        return lines

    for tbl in cfg.get("tables", []):
        f, n = tbl.get("family", "ip"), tbl["name"]
        lines.append(f"table {f} {n} {{")
        for ch in tbl.get("chains", []):
            cn = ch["name"]
            lines.append(f"    chain {cn} {{")
            if ch.get("hook"):
                lines.append(
                    f"        type {ch.get('type','filter')} hook {ch['hook']} "
                    f"priority {ch.get('priority','0')} ; "
                    f"policy {ch.get('policy','accept')} ;"
                )
            for rule in ch.get("rules", []):
                expr = _nft_rule_expr(rule)
                if expr:
                    lines.append(f"        {expr}")
            lines.append("    }")
        lines.append("}")
    return lines


def gen_nftables(cfg: dict) -> list[str]:
    script = _build_nft_script(cfg)

    out = ["# ── nftables script (nft -f format) ─────────────────────────"]
    for line in script:
        out.append(f"# {line}" if line.strip() else "#")

    out += [
        "#",
        "# ── Execution ───────────────────────────────────────────────",
        "rm -f /tmp/nr_nft_rules.nft",
    ]

    for i, line in enumerate(script):
        esc = line.replace("'", "'\\''")
        op = ">" if i == 0 else ">>"
        out.append(f"echo '{esc}' {op} /tmp/nr_nft_rules.nft")

    out += [
        "if command -v sudo >/dev/null 2>&1; then",
        "  sudo nft -f /tmp/nr_nft_rules.nft",
        "else",
        "  nft -f /tmp/nr_nft_rules.nft",
        "fi",
        "if [ $? -eq 0 ]; then echo 'nftables: applied to RAM successfully'; else echo 'nftables: FAILED'; fi",
        "rm -f /tmp/nr_nft_rules.nft",
    ]
    return out
