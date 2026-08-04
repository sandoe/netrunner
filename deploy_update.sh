#!/usr/bin/env bash

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ $# -eq 0 ]]; then
    echo "Brug: NETRUNNER_SSH_PASSWORD=... ./deploy_update.sh user@host [user@host ...]"
    exit 2
fi
if [[ ! -f .env ]]; then
    echo "Mangler .env. Kør ./start.sh init først."
    exit 1
fi
: "${NETRUNNER_SSH_PASSWORD:?Sæt NETRUNNER_SSH_PASSWORD i miljøet}"
NETRUNNER_SUDO_PASSWORD="${NETRUNNER_SUDO_PASSWORD:-$NETRUNNER_SSH_PASSWORD}"

agent_token="$(awk -F= '$1 == "NETRUNNER_AGENT_TOKEN" {sub(/^[^=]*=/, ""); print; exit}' .env)"
if [[ ! "$agent_token" =~ ^[a-fA-F0-9]{32,}$ ]]; then
    echo "NETRUNNER_AGENT_TOKEN i .env har et ugyldigt format."
    exit 1
fi

base_url="${NETRUNNER_BASE_URL:-}"
if [[ -z "$base_url" ]]; then
    lan_ip="$(ip -4 route get 1.1.1.1 | awk '{for (i=1; i<=NF; i++) if ($i == "src") {print $(i+1); exit}}')"
    base_url="http://${lan_ip}:8000"
fi
if [[ ! "$base_url" =~ ^https?://[a-zA-Z0-9.:-]+$ ]]; then
    echo "NETRUNNER_BASE_URL har et ugyldigt format."
    exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
sudo_password_b64="$(printf '%s' "$NETRUNNER_SUDO_PASSWORD" | base64 -w0)"

for target in "$@"; do
    if [[ ! "$target" =~ ^[a-zA-Z0-9._-]+@[a-zA-Z0-9.:-]+$ ]]; then
        echo "Ugyldigt SSH-mål: $target"
        exit 2
    fi

    arch="$(SSHPASS="$NETRUNNER_SSH_PASSWORD" sshpass -e ssh \
        -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
        "$target" uname -m)"
    case "$arch" in
        x86_64|amd64) download_arch="amd64" ;;
        aarch64|arm64) download_arch="arm64" ;;
        *) echo "Ikke-understøttet arkitektur på $target: $arch"; exit 1 ;;
    esac

    local_binary="$tmp_dir/netrunner-agent-$download_arch"
    curl -fsSL "$base_url/api/agent/download/$download_arch" -o "$local_binary"
    chmod 700 "$local_binary"
    SSHPASS="$NETRUNNER_SSH_PASSWORD" sshpass -e scp \
        -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
        "$local_binary" "$target:/tmp/netrunner-agent"

    SSHPASS="$NETRUNNER_SSH_PASSWORD" sshpass -e ssh \
        -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 \
        "$target" \
        "(printf '%s' '$sudo_password_b64' | base64 -d; printf '\n') | sudo -S sh -c 'mv /tmp/netrunner-agent /usr/local/bin/netrunner-agent; chmod 755 /usr/local/bin/netrunner-agent; sed -i -E \"s#--token [^ ]+#--token $agent_token#\" /etc/systemd/system/netrunner-agent.service; systemctl daemon-reload; systemctl restart netrunner-agent'"

    echo "Agent opdateret på $target ($download_arch)."
done
