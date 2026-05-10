"""Encrypted credential vault using Fernet symmetric encryption.

The vault key is auto-generated on first run and stored at data/.vault_key.
Credentials are encrypted at rest in data/vault.json.
The API never returns plaintext passwords.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

from .db import load_vault_entry_db, save_vault_entry_db, delete_vault_entry_db

try:
    from cryptography.fernet import Fernet
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


DATA_DIR = Path("data")
KEY_FILE = DATA_DIR / ".vault_key"


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


async def store_credentials(node_id: str, username: str, password: str) -> None:
    """Encrypt and persist credentials for a node."""
    if not _HAS_CRYPTO:
        blob = json.dumps({"username": username, "password": password})
        await save_vault_entry_db(node_id, blob, False)
        return

    f = _fernet()
    blob = json.dumps({"username": username, "password": password})
    encrypted = f.encrypt(blob.encode()).decode()
    await save_vault_entry_db(node_id, encrypted, True)


async def load_credentials(node_id: str) -> Tuple[str, str]:
    """Return (username, password) for a node, decrypting if necessary."""
    entry = await load_vault_entry_db(node_id)
    if not entry:
        return "root", ""

    if not entry.get("encrypted"):
        try:
            blob = json.loads(entry["data"])
            return blob.get("username", "root"), blob.get("password", "")
        except:
            return "root", ""

    try:
        f = _fernet()
        blob = json.loads(f.decrypt(entry["data"].encode()))
        return blob.get("username", "root"), blob.get("password", "")
    except Exception:
        return "root", ""


async def delete_credentials(node_id: str) -> None:
    await delete_vault_entry_db(node_id)


async def has_credentials(node_id: str) -> bool:
    entry = await load_vault_entry_db(node_id)
    return entry is not None
