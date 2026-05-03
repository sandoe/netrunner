"""Encrypted credential vault using Fernet symmetric encryption.

The vault key is auto-generated on first run and stored at data/.vault_key.
Credentials are encrypted at rest in data/vault.json.
The API never returns plaintext passwords.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


DATA_DIR = Path("data")
KEY_FILE = DATA_DIR / ".vault_key"
VAULT_FILE = DATA_DIR / "vault.json"


def _get_or_create_key() -> bytes:
    DATA_DIR.mkdir(exist_ok=True)
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes().strip()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    return key


def _fernet() -> "Fernet":
    if not _HAS_CRYPTO:
        raise RuntimeError(
            "cryptography package not installed — run: pip install cryptography"
        )
    return Fernet(_get_or_create_key())


def _load_vault() -> dict:
    if VAULT_FILE.exists():
        try:
            return json.loads(VAULT_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_vault(data: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    VAULT_FILE.write_text(json.dumps(data, indent=2))
    VAULT_FILE.chmod(0o600)


def store_credentials(node_id: str, username: str, password: str) -> None:
    """Encrypt and persist credentials for a node."""
    if not _HAS_CRYPTO:
        vault = _load_vault()
        vault[node_id] = {"username": username, "password": password, "encrypted": False}
        _save_vault(vault)
        return

    f = _fernet()
    blob = json.dumps({"username": username, "password": password})
    encrypted = f.encrypt(blob.encode()).decode()
    vault = _load_vault()
    vault[node_id] = {"data": encrypted, "encrypted": True}
    _save_vault(vault)


def load_credentials(node_id: str) -> tuple[str, str]:
    """Return (username, password) for a node, decrypting if necessary."""
    vault = _load_vault()
    entry = vault.get(node_id, {})
    if not entry:
        return "root", ""

    if not entry.get("encrypted", False):
        return entry.get("username", "root"), entry.get("password", "")

    try:
        f = _fernet()
        blob = json.loads(f.decrypt(entry["data"].encode()))
        return blob.get("username", "root"), blob.get("password", "")
    except Exception:
        return "root", ""


def delete_credentials(node_id: str) -> None:
    vault = _load_vault()
    vault.pop(node_id, None)
    _save_vault(vault)


def has_credentials(node_id: str) -> bool:
    return node_id in _load_vault()
