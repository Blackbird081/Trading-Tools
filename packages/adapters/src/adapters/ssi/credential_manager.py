from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes


class StorageTier(StrEnum):
    ENV_VAR = "env_var"
    ENCRYPTED_FILE = "encrypted_file"
    OS_KEYRING = "os_keyring"


@dataclass(frozen=True, slots=True)
class SSICredentials:
    """Immutable container for SSI API credentials."""

    consumer_id: str
    consumer_secret: str
    private_key: RSA.RsaKey


class CredentialManager:
    """Secure credential loading with multiple storage backends."""

    def __init__(self, tier: StorageTier = StorageTier.ENV_VAR) -> None:
        self._tier = tier

    def load_credentials(self) -> SSICredentials:
        consumer_id = self._require_env("SSI_CONSUMER_ID")
        consumer_secret = self._require_env("SSI_CONSUMER_SECRET")

        match self._tier:
            case StorageTier.ENV_VAR:
                private_key = self._load_from_env()
            case StorageTier.ENCRYPTED_FILE:
                private_key = self._load_from_encrypted_file()
            case StorageTier.OS_KEYRING:
                private_key = self._load_from_keyring()

        self._validate_key(private_key)
        return SSICredentials(
            consumer_id=consumer_id,
            consumer_secret=consumer_secret,
            private_key=private_key,
        )

    def _load_from_env(self) -> RSA.RsaKey:
        b64_key = self._require_env("SSI_PRIVATE_KEY_B64")
        pem_bytes = base64.b64decode(b64_key)
        return RSA.import_key(pem_bytes)

    def _load_from_encrypted_file(self) -> RSA.RsaKey:
        from Crypto.Protocol.KDF import scrypt

        passphrase = self._require_env("SSI_KEY_PASSPHRASE")
        key_path = Path(os.getenv("SSI_KEY_PATH", "data/secrets/ssi_private.enc"))
        if not key_path.exists():
            msg = f"Encrypted key file not found: {key_path}"
            raise FileNotFoundError(msg)
        self._check_file_permissions(key_path)
        encrypted_data = key_path.read_bytes()
        nonce = encrypted_data[:16]
        tag = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]
        salt_path = key_path.with_suffix(".salt")
        if not salt_path.exists():
            msg = f"Salt file missing: {salt_path}"
            raise FileNotFoundError(msg)
        salt = salt_path.read_bytes()
        aes_key: bytes = scrypt(  # type: ignore[assignment]
            passphrase.encode(),  # type: ignore[arg-type]
            salt,  # type: ignore[arg-type]
            key_len=32,
            N=2**20,
            r=8,
            p=1,
        )
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        pem_bytes = cipher.decrypt_and_verify(ciphertext, tag)
        return RSA.import_key(pem_bytes)

    def _load_from_keyring(self) -> RSA.RsaKey:
        import keyring

        b64_key = keyring.get_password("algo-trading", "ssi_private_key")
        if b64_key is None:
            msg = "Private key not found in OS keyring."
            raise RuntimeError(msg)
        pem_bytes = base64.b64decode(b64_key)
        return RSA.import_key(pem_bytes)

    @staticmethod
    def _validate_key(key: RSA.RsaKey) -> None:
        if not key.has_private():
            msg = "Loaded key is PUBLIC, not PRIVATE. Cannot sign."
            raise ValueError(msg)
        if key.size_in_bits() < 2048:
            msg = f"Key size {key.size_in_bits()} bits is below minimum 2048."
            raise ValueError(msg)

    @staticmethod
    def _require_env(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            msg = f"Required environment variable '{name}' is not set."
            raise OSError(msg)
        return value

    @staticmethod
    def _check_file_permissions(path: Path) -> None:
        if os.name == "nt":
            return
        import stat

        mode = path.stat().st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            msg = f"Key file {path} is readable by group/others. Fix with: chmod 600 {path}"
            raise PermissionError(msg)

    @staticmethod
    def encrypt_private_key(pem_path: Path, output_path: Path, passphrase: str) -> None:
        from Crypto.Protocol.KDF import scrypt

        pem_bytes = pem_path.read_bytes()
        key = RSA.import_key(pem_bytes)
        if not key.has_private():
            msg = "File does not contain a private key."
            raise ValueError(msg)
        salt = get_random_bytes(32)
        aes_key: bytes = scrypt(  # type: ignore[assignment]
            passphrase.encode(),  # type: ignore[arg-type]
            salt,  # type: ignore[arg-type]
            key_len=32,
            N=2**20,
            r=8,
            p=1,
        )
        cipher = AES.new(aes_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(pem_bytes)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        nonce: bytes = cipher.nonce  # type: ignore[assignment]
        output_path.write_bytes(nonce + tag + ciphertext)
        output_path.with_suffix(".salt").write_bytes(salt)
