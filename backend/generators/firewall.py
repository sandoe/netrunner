"""Firewall configuration generators: iptables, nftables, ufw."""
from __future__ import annotations


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
        chain  = str(chain).upper()
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
        if rule.get("protocol"):   parts += ["-p", str(rule["protocol"])]
        if rule.get("iif"):        parts += ["-i", str(rule["iif"])]
        if rule.get("oif"):        parts += ["-o", str(rule["oif"])]
        if rule.get("saddr"):      parts += ["-s", str(rule["saddr"])]
        if rule.get("daddr"):      parts += ["-d", str(rule["daddr"])]
        if rule.get("ct_state"):   parts += ["-m", "conntrack", "--ctstate", str(rule["ct_state"]).upper()]
        if rule.get("sport"):      parts += ["--sport", str(rule["sport"])]
        if rule.get("dport"):      parts += ["--dport", str(rule["dport"])]

        action = str(rule.get("action", "ACCEPT")).upper()
        if action in ("DNAT", "SNAT", "MASQUERADE"):
            parts += ["-j", action]
            if action in ("DNAT", "SNAT") and rule.get("nat_addr"):
                flag = "--to-destination" if action == "DNAT" else "--to-source"
                parts += [flag, str(rule["nat_addr"])]
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
    routed   = str(defaults.get("routed",   "deny")).lower()
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

        if rule.get("iif"):
            parts += ["on", str(rule["iif"])]
        if rule.get("protocol"):
            proto = str(rule["protocol"]).lower()
            port  = str(rule.get("port", "")).strip()
            if port:
                parts.append(f"{port}/{proto}")
        elif rule.get("port"):
            parts.append(str(rule["port"]))

        if rule.get("saddr"):
            parts += ["from", str(rule["saddr"])]
        elif action in ("allow", "deny", "reject", "limit"):
            parts += ["from", "any"]

        if rule.get("daddr"):
            parts += ["to", str(rule["daddr"])]
        elif rule.get("port") or rule.get("iif") or rule.get("direction"):
            parts += ["to", "any"]

        if rule.get("comment"):
            parts.append(f"# {rule['comment']}")
        cmds.append(" ".join(parts))

    if cfg.get("enabled", True):
        cmds.append("ufw --force enable")
    else:
        cmds.append("ufw disable")
    cmds.append("ufw status verbose")
    return cmds


def _nft_rule_expr(rule: dict) -> str:
    p = []
    if rule.get("iif"):   p.append(f'iifname "{rule["iif"]}"')
    if rule.get("oif"):   p.append(f'oifname "{rule["oif"]}"')
    if rule.get("saddr"): p.append(f"ip saddr {rule['saddr']}")
    if rule.get("daddr"): p.append(f"ip daddr {rule['daddr']}")
    proto    = rule.get("protocol", "")
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
    if   action == "dnat":        p.append(f"dnat to {rule.get('nat_addr','')}")
    elif action == "snat":        p.append(f"snat to {rule.get('nat_addr','')}")
    elif action == "masquerade":  p.append("masquerade")
    elif action == "log":         p.append(f'log prefix "{rule.get("log_prefix","nft: ")}"')
    else:                         p.append(action)
    if rule.get("comment"):
        p.append(f'comment "{rule["comment"]}"')
    return " ".join(p)


def _build_nft_script(cfg: dict) -> list[str]:
    lines: list[str] = ["flush ruleset", ""]
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
        op  = ">"  if i == 0 else ">>"
        out.append(f"echo '{esc}' {op} /tmp/nr_nft_rules.nft")

    out += [
        "nft -f /tmp/nr_nft_rules.nft && echo 'nftables: applied OK' || echo 'nftables: FAILED'",
        "rm -f /tmp/nr_nft_rules.nft",
    ]
    return out
