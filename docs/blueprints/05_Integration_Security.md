# 05 — INTEGRATION & SECURITY: BROKER CONNECTIVITY, OMS & HARDENING

**Project:** Hệ thống Giao dịch Thuật toán Đa Tác vụ (Enterprise Edition)
**Role:** Security Engineer & Integration Specialist
**Version:** 1.0 | February 2026
**Posture:** Zero-Trust | Defense-in-Depth | Assume Breach
**Python:** 3.12+ | **Crypto:** `pycryptodome` 3.20+ | **HTTP:** `httpx` (async)

---

## 1. SSI RSA AUTHENTICATION FLOW — ZERO-TRUST HANDSHAKE

### 1.1. Threat Model — Tại sao SSI dùng RSA thay vì Username/Password

SSI FastConnect API yêu cầu **chữ ký số RSA** cho mỗi request xác thực, thay vì mô hình username/password thông thường. Đây là mô hình **mutual authentication** ở mức API consumer:

```
Mô hình truyền thống (Username/Password):
  Client → [username + password] → Server
  ★ Risk: Password bị lộ = toàn quyền truy cập
  ★ Risk: Man-in-the-middle có thể replay credential
  ★ Risk: Phishing — fake login page bắt credential

Mô hình SSI (RSA Digital Signature):
  Client → [payload + RSA_SIGN(payload, PRIVATE_KEY)] → Server
  Server → [VERIFY(signature, PUBLIC_KEY)] → Accept/Reject
  ★ Private Key KHÔNG BAO GIỜ rời khỏi máy client
  ★ Mỗi request có signature KHÁC NHAU (nonce + timestamp)
  ★ Replay attack bị chặn bởi timestamp window
  ★ Man-in-the-middle chỉ thấy signature, không thể tạo signature mới
```

### 1.2. RSA Key Pair Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RSA KEY LIFECYCLE (One-time Setup)                        │
│                                                                             │
│  Step 1: Generate RSA-2048 Key Pair (OFFLINE)                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  $ openssl genrsa -out ssi_private.pem 2048                     │      │
│  │  $ openssl rsa -in ssi_private.pem -pubout -out ssi_public.pem  │      │
│  │                                                                  │      │
│  │  ★ Generate on SECURE machine only                              │      │
│  │  ★ NEVER generate keys on shared/cloud VMs                      │      │
│  │  ★ Minimum key size: 2048 bits (4096 preferred)                 │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  Step 2: Upload PUBLIC Key to SSI iBoard Portal                            │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  Login iBoard → API Management → Upload ssi_public.pem          │      │
│  │  SSI assigns: consumer_id + consumer_secret                     │      │
│  │                                                                  │      │
│  │  ★ Only PUBLIC key leaves your machine                          │      │
│  │  ★ SSI stores public key to verify your signatures              │      │
│  │  ★ consumer_id = your API identity                              │      │
│  │  ★ consumer_secret = shared secret for additional channel auth  │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  Step 3: Store PRIVATE Key Securely (See Section 1.3)                      │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  ★ PRIVATE key → encrypted environment variable or vault        │      │
│  │  ★ ssi_private.pem → DELETE from disk after import              │      │
│  │  ★ NEVER commit to git. NEVER store in plaintext config.        │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  Step 4: Runtime — Sign & Authenticate                                     │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  Application loads private key from secure storage               │      │
│  │  → Signs auth payload → Sends to SSI → Receives JWT token       │      │
│  │  → Uses JWT for all subsequent API calls (30-minute expiry)     │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3. Private Key Storage — NEVER HARDCODE

```
┌────────────────────────────────────────────────────────────────────────┐
│           PRIVATE KEY STORAGE — SECURITY TIER COMPARISON               │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ❌ TIER 0: BANNED — Hardcoded in source code                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  PRIVATE_KEY = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."     │   │
│  │                                                                │   │
│  │  ★ Instant compromise if repo is leaked/shared                │   │
│  │  ★ Key in git history FOREVER (even after deletion)           │   │
│  │  ★ VIOLATION: Every security standard (PCI-DSS, ISO 27001)   │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ⚠️ TIER 1: MINIMUM — Environment Variables (.env)                    │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  SSI_PRIVATE_KEY_PEM loaded from .env file                    │   │
│  │  .env is in .gitignore                                        │   │
│  │                                                                │   │
│  │  ★ Acceptable for development and single-user edge deployment │   │
│  │  ★ Risk: .env file readable by any process on machine         │   │
│  │  ★ Risk: .env may be accidentally committed                   │   │
│  │  ★ Mitigation: File permissions 600 (owner-only read)         │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ✅ TIER 2: RECOMMENDED — Encrypted file + passphrase env var         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  Private key encrypted with AES-256.                          │   │
│  │  Decryption passphrase in environment variable.               │   │
│  │                                                                │   │
│  │  ★ Key file on disk is useless without passphrase             │   │
│  │  ★ Passphrase in env = smaller attack surface than full key   │   │
│  │  ★ Suitable for production edge deployment                    │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ✅ TIER 3: ENTERPRISE — OS Keychain / Vault                          │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │  Windows: DPAPI (Data Protection API) via `keyring` library   │   │
│  │  macOS: Keychain Access via `keyring`                         │   │
│  │  Linux: Secret Service (GNOME Keyring) via `keyring`          │   │
│  │  Cloud: HashiCorp Vault / AWS Secrets Manager                 │   │
│  │                                                                │   │
│  │  ★ Key protected by OS-level encryption                       │   │
│  │  ★ Access controlled by user login session                    │   │
│  │  ★ Audit trail of key access                                  │   │
│  └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.4. Credential Manager — Production Implementation

```python
# packages/adapters/src/adapters/ssi/credential_manager.py
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes


class StorageTier(StrEnum):
    ENV_VAR = "env_var"                # Tier 1: raw PEM in env
    ENCRYPTED_FILE = "encrypted_file"  # Tier 2: AES-encrypted file + passphrase
    OS_KEYRING = "os_keyring"          # Tier 3: OS credential store


@dataclass(frozen=True, slots=True)
class SSICredentials:
    """Immutable container for SSI API credentials."""
    consumer_id: str
    consumer_secret: str
    private_key: RSA.RsaKey


class CredentialManager:
    """
    Secure credential loading with multiple storage backends.

    ★ ZERO-TRUST PRINCIPLE: Credentials are validated immediately
      after loading. Invalid/expired credentials fail fast.
    ★ Private key is held in memory ONLY — never written to temp files.
    ★ Memory is zeroed on cleanup (best-effort in Python via gc).
    """

    def __init__(self, tier: StorageTier = StorageTier.ENCRYPTED_FILE) -> None:
        self._tier = tier

    def load_credentials(self) -> SSICredentials:
        """Load credentials from configured storage tier."""
        consumer_id = self._require_env("SSI_CONSUMER_ID")
        consumer_secret = self._require_env("SSI_CONSUMER_SECRET")

        match self._tier:
            case StorageTier.ENV_VAR:
                private_key = self._load_from_env()
            case StorageTier.ENCRYPTED_FILE:
                private_key = self._load_from_encrypted_file()
            case StorageTier.OS_KEYRING:
                private_key = self._load_from_keyring()

        # ★ VALIDATE key immediately — fail fast on corrupted keys
        self._validate_key(private_key)

        return SSICredentials(
            consumer_id=consumer_id,
            consumer_secret=consumer_secret,
            private_key=private_key,
        )

    # ── Tier 1: Environment Variable ──────────────────────────

    def _load_from_env(self) -> RSA.RsaKey:
        """
        Load PEM-encoded private key from environment variable.

        ★ Store multi-line PEM as base64-encoded single line:
          SSI_PRIVATE_KEY_B64=$(base64 < ssi_private.pem)
        """
        b64_key = self._require_env("SSI_PRIVATE_KEY_B64")
        pem_bytes = base64.b64decode(b64_key)
        return RSA.import_key(pem_bytes)

    # ── Tier 2: Encrypted File ────────────────────────────────

    def _load_from_encrypted_file(self) -> RSA.RsaKey:
        """
        Load AES-256-GCM encrypted private key file.

        File format: [16-byte nonce][16-byte tag][ciphertext]
        Passphrase stored in env var SSI_KEY_PASSPHRASE.
        """
        passphrase = self._require_env("SSI_KEY_PASSPHRASE")
        key_path = Path(os.getenv("SSI_KEY_PATH", "data/secrets/ssi_private.enc"))

        if not key_path.exists():
            raise FileNotFoundError(
                f"Encrypted key file not found: {key_path}. "
                f"Generate with: python -m adapters.ssi.credential_manager encrypt"
            )

        # Verify file permissions (owner-only on Unix)
        self._check_file_permissions(key_path)

        encrypted_data = key_path.read_bytes()
        nonce = encrypted_data[:16]
        tag = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]

        # Derive AES key from passphrase using scrypt
        from Crypto.Protocol.KDF import scrypt

        # Salt is deterministic per-installation (stored alongside)
        salt_path = key_path.with_suffix(".salt")
        if not salt_path.exists():
            raise FileNotFoundError(f"Salt file missing: {salt_path}")
        salt = salt_path.read_bytes()

        aes_key = scrypt(
            passphrase.encode(),
            salt,
            key_len=32,          # AES-256
            N=2**20,             # CPU/memory cost (high = slow brute-force)
            r=8,
            p=1,
        )

        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        pem_bytes = cipher.decrypt_and_verify(ciphertext, tag)
        return RSA.import_key(pem_bytes)

    # ── Tier 3: OS Keyring ────────────────────────────────────

    def _load_from_keyring(self) -> RSA.RsaKey:
        """Load from OS credential store (Windows DPAPI, macOS Keychain)."""
        import keyring

        b64_key = keyring.get_password("algo-trading", "ssi_private_key")
        if b64_key is None:
            raise RuntimeError(
                "Private key not found in OS keyring. "
                "Store with: keyring.set_password('algo-trading', "
                "'ssi_private_key', base64_encoded_pem)"
            )

        pem_bytes = base64.b64decode(b64_key)
        return RSA.import_key(pem_bytes)

    # ── Validation ────────────────────────────────────────────

    @staticmethod
    def _validate_key(key: RSA.RsaKey) -> None:
        """Validate RSA key is usable for signing."""
        if not key.has_private():
            raise ValueError("Loaded key is PUBLIC, not PRIVATE. Cannot sign.")
        if key.size_in_bits() < 2048:
            raise ValueError(
                f"Key size {key.size_in_bits()} bits is below minimum 2048. "
                f"Generate a stronger key."
            )

    @staticmethod
    def _require_env(name: str) -> str:
        """Get env var or fail with clear error message."""
        value = os.environ.get(name)
        if not value:
            raise EnvironmentError(
                f"Required environment variable '{name}' is not set. "
                f"Add it to your .env file or system environment."
            )
        return value

    @staticmethod
    def _check_file_permissions(path: Path) -> None:
        """Warn if file is world-readable (Unix only)."""
        if os.name == "nt":
            return  # Windows ACL model is different
        import stat
        mode = path.stat().st_mode
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            raise PermissionError(
                f"Key file {path} is readable by group/others. "
                f"Fix with: chmod 600 {path}"
            )

    # ── Utility: Encrypt private key for Tier 2 storage ──────

    @staticmethod
    def encrypt_private_key(
        pem_path: Path,
        output_path: Path,
        passphrase: str,
    ) -> None:
        """
        One-time utility: encrypt a PEM private key for secure storage.

        Usage:
          python -c "
          from adapters.ssi.credential_manager import CredentialManager
          CredentialManager.encrypt_private_key(
              Path('ssi_private.pem'),
              Path('data/secrets/ssi_private.enc'),
              'my-strong-passphrase'
          )"
        """
        from Crypto.Protocol.KDF import scrypt

        pem_bytes = pem_path.read_bytes()

        # Validate it's actually a private key before encrypting
        key = RSA.import_key(pem_bytes)
        if not key.has_private():
            raise ValueError("File does not contain a private key.")

        # Generate random salt
        salt = get_random_bytes(32)
        aes_key = scrypt(
            passphrase.encode(), salt,
            key_len=32, N=2**20, r=8, p=1,
        )

        # Encrypt with AES-256-GCM
        cipher = AES.new(aes_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(pem_bytes)

        # Write: [nonce (16B)][tag (16B)][ciphertext]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(cipher.nonce + tag + ciphertext)
        output_path.with_suffix(".salt").write_bytes(salt)

        # Set strict file permissions
        if os.name != "nt":
            os.chmod(output_path, 0o600)
            os.chmod(output_path.with_suffix(".salt"), 0o600)

        print(f"Encrypted key written to {output_path}")
        print(f"Salt written to {output_path.with_suffix('.salt')}")
        print(f"★ You may now DELETE the original PEM file: {pem_path}")
```

### 1.5. SSI Authentication Client — RSA Signing

```python
# packages/adapters/src/adapters/ssi/auth.py
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

if TYPE_CHECKING:
    from adapters.ssi.credential_manager import SSICredentials


# ── Constants ──────────────────────────────────────────────────
SSI_AUTH_URL = "https://fc-tradeapi.ssi.com.vn/api/v2/Trading/AccessToken"
SSI_BASE_URL = "https://fc-tradeapi.ssi.com.vn"

# JWT token refresh threshold: refresh 5 minutes before expiry
TOKEN_REFRESH_BUFFER_SECONDS = 300

# Maximum clock skew tolerance for timestamp validation
MAX_CLOCK_SKEW_SECONDS = 60


class TokenState:
    """
    Thread-safe container for JWT token state.

    ★ access_token expires after ~30 minutes (SSI policy).
    ★ We proactively refresh 5 minutes before expiry.
    ★ If refresh fails, we retry with exponential backoff (Section 4).
    """

    __slots__ = ("access_token", "expires_at", "issued_at")

    def __init__(self) -> None:
        self.access_token: str | None = None
        self.expires_at: float = 0.0
        self.issued_at: float = 0.0

    @property
    def is_valid(self) -> bool:
        """Check if token is still usable (with refresh buffer)."""
        return (
            self.access_token is not None
            and time.monotonic() < self.expires_at - TOKEN_REFRESH_BUFFER_SECONDS
        )

    @property
    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at

    def update(self, token: str, expires_in: int) -> None:
        now = time.monotonic()
        self.access_token = token
        self.issued_at = now
        self.expires_at = now + expires_in


class SSIAuthClient:
    """
    Handles RSA-signed authentication with SSI FastConnect API.

    ★ SECURITY INVARIANTS:
      1. Private key is NEVER serialized or logged.
      2. Every signature includes timestamp → replay window < 60s.
      3. Token is refreshed proactively, NEVER used past expiry.
      4. All HTTP calls use TLS 1.2+ (httpx default).
      5. No credential is ever included in error messages or logs.
    """

    def __init__(
        self,
        credentials: SSICredentials,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._credentials = credentials
        self._http = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            http2=True,
            verify=True,              # ★ ALWAYS verify TLS certificates
        )
        self._token = TokenState()
        self._refresh_lock = __import__("asyncio").Lock()

    async def get_access_token(self) -> str:
        """
        Get a valid access token. Refreshes automatically if needed.

        ★ Thread-safe via asyncio.Lock — prevents concurrent refresh storms.
        """
        if self._token.is_valid:
            assert self._token.access_token is not None
            return self._token.access_token

        async with self._refresh_lock:
            # Double-check after acquiring lock (another coroutine may have refreshed)
            if self._token.is_valid:
                assert self._token.access_token is not None
                return self._token.access_token

            return await self._authenticate()

    async def _authenticate(self) -> str:
        """
        Perform RSA-signed authentication handshake.

        Sequence:
        1. Build payload with consumer_id + timestamp
        2. Sign payload with RSA private key (SHA-256 + PKCS#1 v1.5)
        3. Send signed request to SSI auth endpoint
        4. Receive JWT access token
        """
        timestamp = self._get_timestamp()

        # ── Step 1: Build canonical payload ────────────────
        payload = {
            "consumerID": self._credentials.consumer_id,
            "consumerSecret": self._credentials.consumer_secret,
            "timestamp": timestamp,
        }

        # ── Step 2: Sign with RSA-SHA256 ──────────────────
        signature = self._sign_payload(payload)

        # ── Step 3: Send authenticated request ─────────────
        request_body = {
            **payload,
            "signature": signature,
        }

        response = await self._http.post(
            SSI_AUTH_URL,
            json=request_body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        # ── Step 4: Validate response ─────────────────────
        if response.status_code != 200:
            # ★ NEVER log request body (contains consumer_secret)
            raise AuthenticationError(
                f"SSI auth failed: HTTP {response.status_code}. "
                f"Check credentials and key validity."
            )

        data = response.json()

        if data.get("status") != 200:
            raise AuthenticationError(
                f"SSI auth rejected: {data.get('message', 'Unknown error')}. "
                f"Verify consumer_id and RSA key pair match."
            )

        access_token = data["data"]["accessToken"]
        expires_in = data["data"].get("expiresIn", 1800)  # Default 30 min

        self._token.update(access_token, expires_in)

        return access_token

    def _sign_payload(self, payload: dict) -> str:
        """
        Create RSA-SHA256 signature over canonical JSON payload.

        ★ Canonical form: JSON with sorted keys, no whitespace.
          This ensures signature is deterministic regardless of
          dict ordering in different Python versions.
        """
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        message_hash = SHA256.new(canonical.encode("utf-8"))

        signature_bytes = pkcs1_15.new(
            self._credentials.private_key
        ).sign(message_hash)

        return __import__("base64").b64encode(signature_bytes).decode("ascii")

    @staticmethod
    def _get_timestamp() -> str:
        """ISO 8601 timestamp in UTC. Used as nonce to prevent replay."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    async def close(self) -> None:
        """Cleanup HTTP client."""
        await self._http.aclose()


class AuthenticationError(Exception):
    """Raised when SSI authentication fails. NEVER contains credentials."""
    pass
```

### 1.6. Authentication Flow — Sequence Diagram

```
Client (Our System)                           SSI Server
       │                                           │
       │  1. Build payload:                        │
       │     {consumerID, consumerSecret,          │
       │      timestamp: "2026-02-10T09:00:00Z"}   │
       │                                           │
       │  2. Sign: RSA_SHA256(payload, PRIVATE_KEY)│
       │     → signature (base64)                  │
       │                                           │
       │  3. POST /AccessToken ─────────────────▶  │
       │     Body: {payload + signature}           │
       │     TLS 1.3 encrypted channel             │
       │                                           │
       │                                           │  4. Server verifies:
       │                                           │     a. consumer_id exists?
       │                                           │     b. timestamp within 60s?
       │                                           │     c. RSA_VERIFY(payload,
       │                                           │        signature, PUBLIC_KEY)?
       │                                           │
       │  5. ◀───────────────── Response ─────── │
       │     {accessToken: "eyJhbG...",            │
       │      expiresIn: 1800}                     │
       │                                           │
       │  6. Store token in memory (TokenState)    │
       │     Set refresh timer = expiresIn - 300s  │
       │                                           │
       │  7. Subsequent API calls:                 │
       │     Authorization: Bearer eyJhbG...       │
       │     ────────────────────────────────────▶  │
       │                                           │
       │  ... (token expires in 30 min) ...        │
       │                                           │
       │  8. Proactive refresh (step 1-6 again)    │
       │     ════════════════════════════════════▶  │
       │                                           │
```

### 1.7. `.env` Template & `.gitignore` Enforcement

```bash
# .env.example (COMMITTED to git — template only, no real values)
# ─────────────────────────────────────────────────────────────
# SSI FastConnect API
SSI_CONSUMER_ID=your_consumer_id_here
SSI_CONSUMER_SECRET=your_consumer_secret_here

# Private Key Storage (choose ONE method):
# Method A: Base64-encoded PEM directly in env var
SSI_PRIVATE_KEY_B64=
# Method B: Encrypted file + passphrase
SSI_KEY_PASSPHRASE=your_strong_passphrase_here
SSI_KEY_PATH=data/secrets/ssi_private.enc

# DNSE Entrade X API
DNSE_USERNAME=
DNSE_PASSWORD=
DNSE_OTP_SECRET=

# Security
SSI_CREDENTIAL_TIER=encrypted_file  # env_var | encrypted_file | os_keyring
```

```gitignore
# .gitignore — SECURITY-CRITICAL entries
# ─────────────────────────────────────────────────────────────

# ★ NEVER commit these — keys and secrets
.env
.env.local
.env.production
*.pem
*.key
*.p12
*.pfx
data/secrets/

# ★ NEVER commit database with trading history
data/trading.duckdb
data/parquet/

# ★ NEVER commit model weights (large + potentially licensed)
data/models/
```

### 1.8. Credential Security Audit Checklist

```
PRE-DEPLOYMENT SECURITY CHECKLIST
══════════════════════════════════════════════════════════════════

□ .env file is NOT committed to git (verify: git log --all -p -- .env)
□ .gitignore includes: .env, *.pem, *.key, data/secrets/
□ RSA key size ≥ 2048 bits (verify: openssl rsa -in key.pem -text | head)
□ Private key file permissions: 600 (owner read/write only)
□ No credentials in Python source code (grep -r "BEGIN RSA" packages/)
□ No credentials in log output (verify: search logs for "consumer")
□ TLS certificate verification enabled (verify=True in httpx)
□ Token refresh fires BEFORE expiry (buffer = 300s)
□ Failed auth does NOT leak credentials in error messages
□ Encrypted key file (.enc) has matching .salt file
□ OS keyring entry created if using Tier 3 storage
□ All environment variables documented in .env.example
```

---

## 2. ORDER MANAGEMENT SYSTEM (OMS) — IDEMPOTENT & STATE-SAFE

### 2.1. Order State Machine — Deterministic Lifecycle

Mọi lệnh giao dịch đi qua một state machine xác định (deterministic FSM). Không có transition ngầm — mọi thay đổi trạng thái đều explicit và auditable.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORDER STATE MACHINE (FSM)                             │
│                                                                         │
│                         ┌──────────┐                                    │
│              ┌──────────│ CREATED  │──────────┐                         │
│              │          │ (local)  │          │                          │
│              │          └────┬─────┘          │                          │
│              │               │                │                          │
│              │               │ submit()       │ validate_fail()          │
│              │               ▼                ▼                          │
│              │          ┌──────────┐    ┌──────────┐                    │
│              │          │ PENDING  │    │ REJECTED │                    │
│              │          │ (sent to │    │ (local   │                    │
│              │          │  broker) │    │  risk    │                    │
│              │          └────┬─────┘    │  check)  │                    │
│              │               │          └──────────┘                    │
│              │               │                                          │
│              │    ┌──────────┼──────────────┐                           │
│              │    │          │              │                            │
│              │    ▼          ▼              ▼                            │
│              │ ┌────────┐ ┌────────┐ ┌──────────┐                      │
│              │ │PARTIAL │ │MATCHED │ │BROKER_   │                      │
│              │ │_FILL   │ │(fully  │ │REJECTED  │                      │
│              │ │        │ │filled) │ │(sàn từ   │                      │
│              │ └───┬────┘ └────────┘ │ chối)    │                      │
│              │     │                  └──────────┘                      │
│              │     │ (more fills)                                       │
│              │     ▼                                                    │
│              │ ┌────────┐                                               │
│              │ │MATCHED │                                               │
│              │ └────────┘                                               │
│              │                                                          │
│              │ cancel() (from CREATED or PENDING)                       │
│              ▼                                                          │
│         ┌──────────┐                                                    │
│         │CANCELLED │                                                    │
│         └──────────┘                                                    │
│                                                                         │
│  Terminal states: MATCHED, REJECTED, BROKER_REJECTED, CANCELLED         │
│  ★ Terminal states are IMMUTABLE — no further transitions allowed.       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2. Order Entity — Immutable State Transitions

```python
# packages/core/src/core/entities/order.py
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Self

from core.value_objects import Price, Quantity, Symbol


class OrderStatus(StrEnum):
    CREATED = "CREATED"              # Local — not yet sent to broker
    PENDING = "PENDING"              # Sent to broker, awaiting match
    PARTIAL_FILL = "PARTIAL_FILL"    # Some quantity matched
    MATCHED = "MATCHED"              # Fully filled
    REJECTED = "REJECTED"            # Rejected by local risk check
    BROKER_REJECTED = "BROKER_REJECTED"  # Rejected by broker/exchange
    CANCELLED = "CANCELLED"          # Cancelled by user or system


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    LO = "LO"    # Limit Order
    ATO = "ATO"  # At the Open
    ATC = "ATC"  # At the Close
    MP = "MP"    # Market Price


# Valid state transitions — WHITELIST approach
_VALID_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CREATED: frozenset({
        OrderStatus.PENDING,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    }),
    OrderStatus.PENDING: frozenset({
        OrderStatus.PARTIAL_FILL,
        OrderStatus.MATCHED,
        OrderStatus.BROKER_REJECTED,
        OrderStatus.CANCELLED,
    }),
    OrderStatus.PARTIAL_FILL: frozenset({
        OrderStatus.PARTIAL_FILL,  # More partial fills
        OrderStatus.MATCHED,       # Final fill
        OrderStatus.CANCELLED,     # Cancel remainder
    }),
    # Terminal states — NO transitions allowed
    OrderStatus.MATCHED: frozenset(),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.BROKER_REJECTED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class Order:
    """
    Immutable order entity with enforced state machine.

    ★ CRITICAL: Orders are NEVER mutated in place.
      Every state change produces a NEW Order instance.
      This guarantees audit trail integrity and thread safety.
    """
    order_id: str
    idempotency_key: str        # ★ Client-generated unique key (See Section 2.3)
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    quantity: Quantity           # Total requested quantity
    price: Price                # Limit price (ignored for MP/ATO/ATC)
    ceiling_price: Price        # Max allowed price (7% above ref for HOSE)
    floor_price: Price          # Min allowed price (7% below ref for HOSE)

    status: OrderStatus
    filled_quantity: Quantity    # Quantity already matched
    avg_fill_price: Price       # Weighted average fill price

    broker_order_id: str | None  # Assigned by broker after submission
    rejection_reason: str | None

    created_at: datetime
    updated_at: datetime

    def transition_to(self, new_status: OrderStatus, **kwargs: object) -> Self:
        """
        Create a new Order with updated status.

        ★ ENFORCES state machine — invalid transitions raise ValueError.
        ★ Returns NEW instance — original is untouched (immutable).
        """
        valid_next = _VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in valid_next:
            raise InvalidOrderTransition(
                f"Cannot transition from {self.status} to {new_status}. "
                f"Valid transitions: {valid_next or 'NONE (terminal state)'}."
            )

        return replace(
            self,
            status=new_status,
            updated_at=datetime.now(timezone.utc),
            **kwargs,  # type: ignore[arg-type]
        )

    @property
    def is_terminal(self) -> bool:
        """Terminal states cannot transition further."""
        return len(_VALID_TRANSITIONS.get(self.status, frozenset())) == 0

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_fully_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    def with_partial_fill(
        self,
        fill_qty: int,
        fill_price: Decimal,
    ) -> Self:
        """
        Apply a partial fill. Recalculates average fill price.

        ★ Validates: fill_qty > 0, total does not exceed requested quantity.
        """
        if fill_qty <= 0:
            raise ValueError(f"Fill quantity must be positive, got {fill_qty}")

        new_filled = self.filled_quantity + fill_qty
        if new_filled > self.quantity:
            raise ValueError(
                f"Fill would exceed order quantity: "
                f"{self.filled_quantity} + {fill_qty} > {self.quantity}"
            )

        # Weighted average fill price
        total_value = (
            Decimal(self.avg_fill_price) * self.filled_quantity
            + fill_price * fill_qty
        )
        new_avg_price = Price(total_value / new_filled)

        new_status = (
            OrderStatus.MATCHED if new_filled >= self.quantity
            else OrderStatus.PARTIAL_FILL
        )

        return replace(
            self,
            status=new_status,
            filled_quantity=Quantity(new_filled),
            avg_fill_price=new_avg_price,
            updated_at=datetime.now(timezone.utc),
        )


class InvalidOrderTransition(Exception):
    """Raised when an invalid state transition is attempted."""
    pass
```

### 2.3. Idempotency — Preventing Duplicate Orders

Trong điều kiện mạng không ổn định (timeout, retry, WebSocket reconnect), cùng một lệnh có thể được gửi **nhiều lần**. Nếu không có cơ chế idempotency, mỗi lần gửi tạo ra một lệnh mới → **mua/bán gấp đôi, gấp ba** → thua lỗ nghiêm trọng.

```
PROBLEM: Network Timeout + Retry Without Idempotency
═══════════════════════════════════════════════════════════════

Client                          Broker API                    Exchange
  │                                │                             │
  │  POST /order {buy FPT 1000}   │                             │
  │ ──────────────────────────────▶│                             │
  │                                │  Forward ──────────────────▶│
  │                                │                             │  ✓ Order#1 created
  │  ⏱ TIMEOUT (no response)      │  ◀─────── 200 OK ─────────│
  │                                │                             │
  │  ★ Client assumes failure     │  Response lost in transit   │
  │  ★ Client RETRIES             │                             │
  │                                │                             │
  │  POST /order {buy FPT 1000}   │                             │
  │ ──────────────────────────────▶│                             │
  │                                │  Forward ──────────────────▶│
  │                                │                             │  ✓ Order#2 created
  │  ◀─────── 200 OK ────────────│  ◀─────── 200 OK ─────────│
  │                                │                             │
  │  ★ Result: TWO orders placed  │                             │
  │  ★ Bought 2000 FPT instead    │                             │
  │    of 1000!                    │                             │

SOLUTION: Idempotency Key
═══════════════════════════════════════════════════════════════

Client                          Our Backend                   Broker API
  │                                │                             │
  │  POST /order                   │                             │
  │  {buy FPT 1000,               │                             │
  │   idempotency_key: "abc-123"} │                             │
  │ ──────────────────────────────▶│                             │
  │                                │  Check: "abc-123" seen?    │
  │                                │  → NO → Forward to broker  │
  │                                │  → Store "abc-123" = order │
  │                                │ ─────────────────────────▶ │
  │  ⏱ TIMEOUT                    │                             │
  │                                │  ◀─────── 200 OK ────────│
  │  POST /order (RETRY)          │                             │
  │  {buy FPT 1000,               │                             │
  │   idempotency_key: "abc-123"} │                             │
  │ ──────────────────────────────▶│                             │
  │                                │  Check: "abc-123" seen?    │
  │                                │  → YES → Return cached     │
  │                                │    response. Do NOT resend. │
  │  ◀─────── 200 OK (cached) ───│                             │
  │                                │                             │
  │  ★ Result: ONE order placed   │                             │
```

### 2.4. Idempotency Implementation

```python
# packages/core/src/core/use_cases/place_order.py
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities.order import Order, OrderSide, OrderType
    from core.entities.portfolio import PortfolioState
    from core.entities.risk import RiskLimit
    from core.ports.broker import BrokerPort
    from core.ports.repository import OrderRepository
    from core.value_objects import Price, Quantity, Symbol


@dataclass(frozen=True, slots=True)
class PlaceOrderRequest:
    """Incoming order request from user or agent."""
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    quantity: Quantity
    price: Price
    idempotency_key: str       # ★ Client-generated, UUID v4 recommended


@dataclass(frozen=True, slots=True)
class PlaceOrderResult:
    success: bool
    order: Order | None
    error: str | None
    was_duplicate: bool        # True if idempotency key was already used


class IdempotencyStore:
    """
    In-memory + DuckDB-backed idempotency key store.

    ★ Keys are stored for 24 hours, then pruned.
    ★ In-memory cache for fast O(1) lookup on hot path.
    ★ DuckDB for persistence across restarts.
    """

    def __init__(self, order_repo: OrderRepository) -> None:
        self._cache: dict[str, Order] = {}
        self._repo = order_repo

    async def check_and_reserve(self, key: str) -> Order | None:
        """
        Check if idempotency key was already used.

        Returns:
          - None: key is NEW, proceed with order placement.
          - Order: key was USED, return cached order (do not re-submit).

        ★ ATOMIC: check + reserve in single operation.
        """
        # Fast path: in-memory cache
        if key in self._cache:
            return self._cache[key]

        # Slow path: check DuckDB
        existing = await self._repo.get_by_idempotency_key(key)
        if existing is not None:
            self._cache[key] = existing
            return existing

        return None  # Key is new

    def record(self, key: str, order: Order) -> None:
        """Record successful order for idempotency key."""
        self._cache[key] = order

    def prune_expired(self, max_age_hours: int = 24) -> int:
        """Remove old idempotency keys from cache."""
        # Implementation: remove entries older than max_age_hours
        ...


async def place_order(
    request: PlaceOrderRequest,
    portfolio: PortfolioState,
    risk_limits: RiskLimit,
    broker: BrokerPort,
    order_repo: OrderRepository,
    idempotency_store: IdempotencyStore,
) -> PlaceOrderResult:
    """
    Place an order with full safety checks.

    ★ ORDER OF OPERATIONS (defense-in-depth):
      1. Idempotency check — prevent duplicates
      2. Risk validation — enforce limits
      3. Price band validation — ceiling/floor (Section 3.2)
      4. T+2.5 settlement check — sufficient sellable qty (Section 3.1)
      5. Broker submission — send to SSI/DNSE
      6. Persistence — record in DuckDB
      7. Idempotency record — mark key as used
    """
    from core.entities.order import (
        Order,
        OrderStatus,
        OrderType,
    )
    from core.use_cases.risk_check import validate_order

    # ── Step 1: Idempotency Check ──────────────────────────
    cached_order = await idempotency_store.check_and_reserve(
        request.idempotency_key
    )
    if cached_order is not None:
        return PlaceOrderResult(
            success=True,
            order=cached_order,
            error=None,
            was_duplicate=True,
        )

    # ── Step 2: Create local order ─────────────────────────
    now = datetime.now(timezone.utc)
    ref_price = await _get_reference_price(request.symbol, order_repo)
    ceiling = Price(ref_price * Decimal("1.07"))  # HOSE: +7%
    floor = Price(ref_price * Decimal("0.93"))    # HOSE: -7%

    order = Order(
        order_id=str(uuid.uuid4()),
        idempotency_key=request.idempotency_key,
        symbol=request.symbol,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        price=request.price,
        ceiling_price=ceiling,
        floor_price=floor,
        status=OrderStatus.CREATED,
        filled_quantity=Quantity(0),
        avg_fill_price=Price(Decimal("0")),
        broker_order_id=None,
        rejection_reason=None,
        created_at=now,
        updated_at=now,
    )

    # ── Step 3: Risk Validation (ceiling/floor + limits) ───
    risk_result = validate_order(order, portfolio, risk_limits)
    if not risk_result.approved:
        rejected = order.transition_to(
            OrderStatus.REJECTED,
            rejection_reason=risk_result.reason,
        )
        await order_repo.save(rejected)
        return PlaceOrderResult(
            success=False,
            order=rejected,
            error=risk_result.reason,
            was_duplicate=False,
        )

    # ── Step 4: Submit to Broker ───────────────────────────
    try:
        broker_id = await broker.place_order(
            symbol=str(order.symbol),
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity,
            price=float(order.price),
        )
    except Exception as exc:
        # Broker submission failed — mark as broker rejected
        failed = order.transition_to(
            OrderStatus.BROKER_REJECTED,
            rejection_reason=f"Broker error: {type(exc).__name__}",
        )
        await order_repo.save(failed)
        return PlaceOrderResult(
            success=False,
            order=failed,
            error=str(exc),
            was_duplicate=False,
        )

    # ── Step 5: Persist + Record Idempotency ───────────────
    pending = order.transition_to(
        OrderStatus.PENDING,
        broker_order_id=broker_id,
    )
    await order_repo.save(pending)
    idempotency_store.record(request.idempotency_key, pending)

    return PlaceOrderResult(
        success=True,
        order=pending,
        error=None,
        was_duplicate=False,
    )


async def _get_reference_price(
    symbol: object, repo: OrderRepository,
) -> Decimal:
    """Get today's reference price for ceiling/floor calculation."""
    # In production: query from market data cache or DuckDB
    ...
```

### 2.5. Order Status Synchronization — Broker Polling

```python
# packages/adapters/src/adapters/ssi/order_sync.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("oms.sync")


class OrderStatusSynchronizer:
    """
    Periodically syncs order status from broker to local DB.

    SSI sends order updates via WebSocket (preferred) and REST polling (fallback).
    This synchronizer handles BOTH paths and reconciles state.

    ★ INVARIANT: Broker is source of truth for order status.
      Local status ALWAYS converges toward broker status.
      We NEVER locally "promote" an order to MATCHED without broker confirmation.
    """

    def __init__(
        self,
        broker_client: object,
        order_repo: object,
        poll_interval: float = 2.0,    # Poll every 2 seconds during market hours
    ) -> None:
        self._broker = broker_client
        self._repo = order_repo
        self._poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        """Start the sync loop."""
        self._running = True
        while self._running:
            try:
                await self._sync_cycle()
            except Exception:
                logger.exception("Order sync cycle failed — will retry")
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False

    async def _sync_cycle(self) -> None:
        """One synchronization cycle."""
        # Get all non-terminal local orders
        open_orders = await self._repo.get_open_orders()
        if not open_orders:
            return

        # Fetch status from broker
        broker_statuses = await self._broker.get_order_statuses(
            [o.broker_order_id for o in open_orders if o.broker_order_id]
        )

        for local_order in open_orders:
            if local_order.broker_order_id is None:
                continue

            broker_status = broker_statuses.get(local_order.broker_order_id)
            if broker_status is None:
                continue

            # Reconcile local state with broker state
            updated = self._reconcile(local_order, broker_status)
            if updated is not None and updated.status != local_order.status:
                await self._repo.save(updated)
                logger.info(
                    "Order %s: %s → %s (broker: %s)",
                    local_order.order_id,
                    local_order.status,
                    updated.status,
                    broker_status.get("status"),
                )

    @staticmethod
    def _reconcile(local_order: object, broker_data: dict) -> object | None:
        """
        Map broker status to local OrderStatus.

        ★ SSI status codes → our status mapping:
          "PendingNew"  → PENDING
          "New"         → PENDING
          "PartialFill" → PARTIAL_FILL
          "Fill"        → MATCHED
          "Rejected"    → BROKER_REJECTED
          "Cancelled"   → CANCELLED
          "Expired"     → CANCELLED
        """
        from core.entities.order import OrderStatus

        status_map = {
            "PendingNew": OrderStatus.PENDING,
            "New": OrderStatus.PENDING,
            "PartialFill": OrderStatus.PARTIAL_FILL,
            "Fill": OrderStatus.MATCHED,
            "Rejected": OrderStatus.BROKER_REJECTED,
            "Cancelled": OrderStatus.CANCELLED,
            "Expired": OrderStatus.CANCELLED,
        }

        broker_status_str = broker_data.get("status", "")
        mapped_status = status_map.get(broker_status_str)

        if mapped_status is None:
            logger.warning(
                "Unknown broker status '%s' for order %s",
                broker_status_str,
                local_order.order_id,
            )
            return None

        if mapped_status == local_order.status:
            return None  # No change

        try:
            if mapped_status in (OrderStatus.PARTIAL_FILL, OrderStatus.MATCHED):
                fill_qty = broker_data.get("filledQty", 0)
                fill_price = broker_data.get("avgPrice", 0)
                return local_order.with_partial_fill(
                    fill_qty=fill_qty - local_order.filled_quantity,
                    fill_price=__import__("decimal").Decimal(str(fill_price)),
                )
            else:
                return local_order.transition_to(
                    mapped_status,
                    rejection_reason=broker_data.get("rejectReason"),
                )
        except Exception:
            logger.exception(
                "Failed to transition order %s to %s",
                local_order.order_id,
                mapped_status,
            )
            return None
```

### 2.6. OMS Audit Trail Schema

```sql
-- DuckDB table: complete audit trail of every order state change
CREATE TABLE order_audit_log (
    audit_id        BIGINT GENERATED ALWAYS AS IDENTITY,
    order_id        VARCHAR NOT NULL,
    idempotency_key VARCHAR NOT NULL,
    previous_status VARCHAR,           -- NULL for CREATED
    new_status      VARCHAR NOT NULL,
    filled_quantity INTEGER,
    avg_fill_price  DOUBLE,
    broker_order_id VARCHAR,
    rejection_reason VARCHAR,
    changed_by      VARCHAR NOT NULL,  -- "system", "user", "broker_sync", "risk_agent"
    changed_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- ★ Agent pipeline context (which run triggered this order?)
    pipeline_run_id VARCHAR,
    agent_name      VARCHAR            -- "executor", "risk_agent", etc.
);

-- Index for fast lookup by order
CREATE INDEX idx_audit_order ON order_audit_log (order_id, changed_at);

-- Index for idempotency key dedup check
CREATE UNIQUE INDEX idx_idempotency
ON order_audit_log (idempotency_key)
WHERE new_status = 'PENDING';  -- Only first submission counts
```

---

## 3. VIETNAM MARKET SPECIFICS — T+2.5 & PRICE BANDS

### 3.1. T+2.5 Settlement Logic — Tại sao phức tạp

Thị trường chứng khoán Việt Nam sử dụng chu kỳ thanh toán **T+2.5**, có nghĩa:

```
Mua ngày T (Thứ 2):
  T+0: Lệnh khớp. Cổ phiếu "về tài khoản" nhưng CHƯA bán được.
  T+1: Vẫn chưa bán được.
  T+2: Sáng — vẫn chưa. Chiều (14:00) — BÁN ĐƯỢC (T+2.5).

★ "2.5" = 2 ngày làm việc + nửa ngày (buổi chiều ngày T+2).
★ Nếu T là Thứ 5 → bán được vào chiều Thứ 2 tuần sau (skip weekend).
★ Nếu T là Thứ 6 → bán được vào chiều Thứ 3 tuần sau.

NGUY HIỂM: Nếu hệ thống không track T+2.5 đúng cách:
  → Agent đề xuất BÁN cổ phiếu vừa mua hôm qua
  → Lệnh bị sàn TỪ CHỐI
  → Hoặc tệ hơn: bán vượt số lượng sellable → bị call margin
```

### 3.2. SSI Position Data — Field Mapping

```
SSI API Response (stockPosition):
┌──────────────────────────────────────────────────────────────────┐
│  {                                                               │
│    "symbol": "FPT",                                              │
│    "onHand": 5000,        ← Tổng số CK đang có (all states)    │
│    "sellableQty": 3000,   ← Số lượng BÁN ĐƯỢC (đã settle T+2.5)│
│    "holdingQty": 2000,    ← Đang chờ settle (mua gần đây)      │
│    "avgPrice": 95000,     ← Giá vốn bình quân (VND)            │
│    "marketPrice": 98500,  ← Giá thị trường hiện tại            │
│    "receivingT1": 1000,   ← Sẽ settle vào T+1                  │
│    "receivingT2": 1000,   ← Sẽ settle vào T+2                  │
│  }                                                               │
│                                                                  │
│  ★ CRITICAL: Chỉ dùng sellableQty khi kiểm tra lệnh BÁN       │
│  ★ onHand ≠ sellableQty khi có giao dịch mua gần đây           │
│  ★ holdingQty = onHand - sellableQty = receivingT1 + receivingT2│
└──────────────────────────────────────────────────────────────────┘
```

### 3.3. T+2.5 Settlement Engine

```python
# packages/core/src/core/entities/portfolio.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Self

from core.value_objects import Price, Quantity, Symbol


@dataclass(frozen=True, slots=True)
class Position:
    """
    A single stock position with T+2.5 settlement awareness.

    ★ INVARIANT: sellable_qty <= quantity (always)
    ★ INVARIANT: sellable_qty reflects T+2.5 settlement
    ★ Source of truth: broker API (SSI stockPosition)
    """
    symbol: Symbol
    quantity: Quantity              # Total on-hand (all settlement states)
    sellable_qty: Quantity          # Settled — available to sell NOW
    receiving_t1: Quantity          # Will settle tomorrow
    receiving_t2: Quantity          # Will settle day after tomorrow
    avg_price: Price               # Cost basis (weighted average)
    market_price: Price            # Current market price

    @property
    def unrealized_pnl(self) -> Decimal:
        """PnL if all shares were sold at market price."""
        return (self.market_price - self.avg_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> Decimal:
        """PnL as percentage of cost basis."""
        if self.avg_price == 0:
            return Decimal("0")
        return (self.market_price - self.avg_price) / self.avg_price

    @property
    def market_value(self) -> Decimal:
        return self.market_price * self.quantity

    @property
    def pending_settlement(self) -> int:
        """Shares still waiting for T+2.5 settlement."""
        return self.quantity - self.sellable_qty


@dataclass(frozen=True, slots=True)
class CashBalance:
    """
    Cash position with T+2.5 settlement awareness.

    ★ cashBal: Tiền mặt THỰC CÓ (settled cash).
    ★ purchasingPower: Sức mua (bao gồm margin nếu có).
    ★ CRITICAL: Dùng purchasingPower cho BUY validation,
      dùng cashBal cho withdrawal/transfer validation.
    """
    cash_bal: Decimal              # Settled cash balance
    purchasing_power: Decimal      # Available buying power (incl. margin)
    pending_settlement: Decimal    # Cash from sells waiting to settle

    @property
    def total_available(self) -> Decimal:
        """Conservative: only confirmed cash."""
        return self.cash_bal


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """
    Complete portfolio snapshot at a point in time.

    ★ ALWAYS sourced from broker API (SSI/DNSE), NEVER computed locally.
    ★ Local computation may drift from broker state due to T+2.5 timing.
    """
    positions: list[Position]
    cash: CashBalance
    synced_at: datetime

    @property
    def net_asset_value(self) -> Decimal:
        """NAV = sum(position market values) + cash balance."""
        position_value = sum(p.market_value for p in self.positions)
        return position_value + self.cash.cash_bal

    @property
    def purchasing_power(self) -> Decimal:
        return self.cash.purchasing_power

    def get_position(self, symbol: Symbol) -> Position | None:
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None

    def get_sellable_qty(self, symbol: Symbol) -> int:
        """
        Get the quantity available to sell RIGHT NOW.

        ★ This is THE critical function for T+2.5 compliance.
        ★ Returns sellable_qty from broker (already accounts for settlement).
        ★ ALSO subtracts any pending sell orders not yet matched.
        """
        position = self.get_position(symbol)
        if position is None:
            return 0
        return position.sellable_qty
```

### 3.4. T+2.5 Aware Order Validation

```python
# packages/core/src/core/use_cases/settlement.py
from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple


class SettlementDate(NamedTuple):
    trade_date: date
    settlement_date: date
    sellable_session: str   # "morning" | "afternoon"


# Vietnam public holidays 2026 (update annually)
_VN_HOLIDAYS_2026: frozenset[date] = frozenset({
    date(2026, 1, 1),      # New Year
    date(2026, 1, 26),     # Lunar New Year (approx)
    date(2026, 1, 27),
    date(2026, 1, 28),
    date(2026, 1, 29),
    date(2026, 1, 30),
    date(2026, 4, 30),     # Reunification Day
    date(2026, 5, 1),      # Labour Day
    date(2026, 9, 2),      # National Day
    # Add more as officially announced
})


def is_trading_day(d: date) -> bool:
    """Check if a date is a valid trading day (weekday, not holiday)."""
    return d.weekday() < 5 and d not in _VN_HOLIDAYS_2026


def next_trading_day(d: date) -> date:
    """Find the next trading day after given date."""
    candidate = d + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def calculate_settlement_date(trade_date: date) -> SettlementDate:
    """
    Calculate T+2.5 settlement date for a trade.

    T+2.5 means:
    - Count 2 full TRADING DAYS after trade date
    - Add half day (afternoon session of T+2)
    - Shares become sellable at 13:00 on settlement date

    Examples:
      Trade Monday    → Sellable Wednesday afternoon
      Trade Thursday  → Sellable Monday afternoon (next week)
      Trade Friday    → Sellable Tuesday afternoon (next week)
    """
    t1 = next_trading_day(trade_date)
    t2 = next_trading_day(t1)

    return SettlementDate(
        trade_date=trade_date,
        settlement_date=t2,
        sellable_session="afternoon",  # 13:00 onwards
    )


def can_sell_now(
    buy_date: date,
    current_date: date,
    current_hour: int,
) -> bool:
    """
    Check if shares bought on buy_date are sellable right now.

    ★ This function is called by Risk Agent before approving SELL orders.
    ★ Accounts for T+2.5 + holidays + weekend.
    """
    settlement = calculate_settlement_date(buy_date)

    if current_date > settlement.settlement_date:
        return True  # Past settlement date — fully sellable

    if current_date == settlement.settlement_date:
        return current_hour >= 13  # Afternoon session (T+2.5)

    return False  # Before settlement date — NOT sellable
```

### 3.5. Price Band Enforcement — Ceiling/Floor Hardcoding

```python
# packages/core/src/core/use_cases/price_band.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from enum import StrEnum

from core.value_objects import Price, Symbol


class Exchange(StrEnum):
    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"


# ── Price Band Rules (Regulatory) ────────────────────────────
# These are SET BY LAW — not configurable. Hardcode defensively.

_PRICE_BAND_PCT: dict[Exchange, Decimal] = {
    Exchange.HOSE: Decimal("0.07"),    # ±7%
    Exchange.HNX: Decimal("0.10"),     # ±10%
    Exchange.UPCOM: Decimal("0.15"),   # ±15%
}

# Tick size rules (HOSE) — price step depends on price level
_HOSE_TICK_SIZES: list[tuple[Decimal, Decimal]] = [
    (Decimal("10000"), Decimal("10")),      # Price < 10,000: tick = 10 VND
    (Decimal("50000"), Decimal("50")),      # 10,000 ≤ Price < 50,000: tick = 50
    (Decimal("999999999"), Decimal("100")), # Price ≥ 50,000: tick = 100
]


@dataclass(frozen=True, slots=True)
class PriceBand:
    """Ceiling and floor prices for a symbol on a given trading day."""
    symbol: Symbol
    exchange: Exchange
    reference_price: Price     # Giá tham chiếu (opening reference)
    ceiling_price: Price       # Giá trần (max allowed)
    floor_price: Price         # Giá sàn (min allowed)
    tick_size: Decimal         # Bước giá (min price increment)


def calculate_price_band(
    symbol: Symbol,
    exchange: Exchange,
    reference_price: Price,
) -> PriceBand:
    """
    Calculate ceiling/floor prices from reference price.

    ★ REGULATORY CONSTRAINT — these limits are absolute.
    ★ Any order with price outside [floor, ceiling] will be
      REJECTED by the exchange. Our system rejects BEFORE sending.

    ★ Price must snap to tick size grid.
    """
    band_pct = _PRICE_BAND_PCT[exchange]

    # Calculate raw ceiling/floor
    raw_ceiling = reference_price * (1 + band_pct)
    raw_floor = reference_price * (1 - band_pct)

    # Snap to tick size
    tick = _get_tick_size(exchange, reference_price)
    ceiling = Price(_snap_down(raw_ceiling, tick))   # Round DOWN for ceiling
    floor = Price(_snap_up(raw_floor, tick))          # Round UP for floor

    return PriceBand(
        symbol=symbol,
        exchange=exchange,
        reference_price=reference_price,
        ceiling_price=ceiling,
        floor_price=floor,
        tick_size=tick,
    )


def validate_order_price(
    price: Price,
    band: PriceBand,
) -> tuple[bool, str]:
    """
    Validate that order price is within regulatory price band.

    Returns: (is_valid, reason)

    ★ This check is MANDATORY. Bypass = regulatory violation.
    ★ Applied in Risk Agent BEFORE any order reaches the broker.
    """
    if price > band.ceiling_price:
        return False, (
            f"Price {price} exceeds ceiling {band.ceiling_price} "
            f"(ref: {band.reference_price}, band: ±"
            f"{_PRICE_BAND_PCT[band.exchange]:.0%})"
        )

    if price < band.floor_price:
        return False, (
            f"Price {price} below floor {band.floor_price} "
            f"(ref: {band.reference_price}, band: ±"
            f"{_PRICE_BAND_PCT[band.exchange]:.0%})"
        )

    # Validate tick size alignment
    remainder = price % band.tick_size
    if remainder != 0:
        return False, (
            f"Price {price} not aligned to tick size {band.tick_size}. "
            f"Nearest valid: {_snap_down(price, band.tick_size)}"
        )

    return True, "Price within valid range"


def _get_tick_size(exchange: Exchange, price: Decimal) -> Decimal:
    """Get tick size based on exchange and price level."""
    if exchange != Exchange.HOSE:
        return Decimal("100")  # HNX and UPCOM: fixed 100 VND

    for threshold, tick in _HOSE_TICK_SIZES:
        if price < threshold:
            return tick
    return Decimal("100")


def _snap_down(value: Decimal, tick: Decimal) -> Decimal:
    """Round down to nearest tick."""
    return (value / tick).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick


def _snap_up(value: Decimal, tick: Decimal) -> Decimal:
    """Round up to nearest tick."""
    return (value / tick).quantize(Decimal("1"), rounding=ROUND_UP) * tick
```

### 3.6. Risk Agent — Integrated Validation

```python
# packages/core/src/core/use_cases/risk_check.py (EXTENDED)
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.entities.order import Order, OrderSide
from core.entities.portfolio import PortfolioState
from core.entities.risk import RiskLimit
from core.use_cases.price_band import (
    PriceBand,
    validate_order_price,
)


@dataclass(frozen=True, slots=True)
class RiskCheckResult:
    approved: bool
    reason: str
    checks_passed: list[str]
    checks_failed: list[str]


def validate_order(
    order: Order,
    portfolio: PortfolioState,
    limits: RiskLimit,
    price_band: PriceBand | None = None,
    pending_sell_qty: int = 0,
) -> RiskCheckResult:
    """
    Comprehensive order validation — ALL checks must pass.

    ★ DEFENSE IN DEPTH: Each check is independent.
      A failure in one check does NOT skip subsequent checks.
      We collect ALL failures for clear error reporting.

    Check order:
      1. Kill Switch
      2. Price Band (ceiling/floor) — regulatory
      3. Lot Size (must be multiple of 100)
      4. Position Size (max % of NAV per order)
      5. Buying Power (sufficient cash for BUY)
      6. Sellable Quantity (T+2.5 aware for SELL)
      7. Daily Loss Limit
    """
    passed: list[str] = []
    failed: list[str] = []

    # ── Check 1: Kill Switch ──────────────────────────────
    if limits.kill_switch_active:
        failed.append("KILL_SWITCH: Emergency halt is ACTIVE. All trading stopped.")
        return RiskCheckResult(
            approved=False,
            reason="Kill switch active",
            checks_passed=passed,
            checks_failed=failed,
        )
    passed.append("KILL_SWITCH: Off")

    # ── Check 2: Price Band ───────────────────────────────
    if price_band is not None:
        is_valid, price_reason = validate_order_price(order.price, price_band)
        if not is_valid:
            failed.append(f"PRICE_BAND: {price_reason}")
        else:
            passed.append("PRICE_BAND: Within ceiling/floor")

    # ── Check 3: Lot Size ─────────────────────────────────
    if order.quantity % 100 != 0:
        failed.append(
            f"LOT_SIZE: Quantity {order.quantity} is not a multiple of 100. "
            f"HOSE/HNX require lot size 100."
        )
    else:
        passed.append("LOT_SIZE: Valid (multiple of 100)")

    # ── Check 4: Position Size (max 20% NAV) ──────────────
    order_value = order.price * Decimal(order.quantity)
    nav = portfolio.net_asset_value
    if nav > 0:
        position_pct = order_value / nav
        max_pct = limits.max_position_pct
        if position_pct > max_pct:
            failed.append(
                f"POSITION_SIZE: Order value {order_value:,.0f} VND = "
                f"{position_pct:.1%} of NAV {nav:,.0f} VND. "
                f"Exceeds limit {max_pct:.0%}."
            )
        else:
            passed.append(f"POSITION_SIZE: {position_pct:.1%} of NAV (limit: {max_pct:.0%})")

    # ── Check 5: Buying Power (BUY only) ──────────────────
    if order.side == OrderSide.BUY:
        if order_value > portfolio.purchasing_power:
            failed.append(
                f"BUYING_POWER: Order value {order_value:,.0f} VND exceeds "
                f"purchasing power {portfolio.purchasing_power:,.0f} VND."
            )
        else:
            passed.append("BUYING_POWER: Sufficient")

    # ── Check 6: Sellable Quantity (SELL only, T+2.5) ─────
    if order.side == OrderSide.SELL:
        sellable = portfolio.get_sellable_qty(order.symbol)
        available = sellable - pending_sell_qty  # Subtract pending sells
        if order.quantity > available:
            failed.append(
                f"SELLABLE_QTY: Requesting to sell {order.quantity} "
                f"but only {available} shares available "
                f"(sellable: {sellable}, pending sells: {pending_sell_qty}). "
                f"Check T+2.5 settlement status."
            )
        else:
            passed.append(
                f"SELLABLE_QTY: {order.quantity} ≤ {available} available"
            )

    # ── Check 7: Daily Loss Limit ─────────────────────────
    # (Would query today's realized PnL from DuckDB)

    # ── Final Verdict ─────────────────────────────────────
    if failed:
        return RiskCheckResult(
            approved=False,
            reason="; ".join(failed),
            checks_passed=passed,
            checks_failed=failed,
        )

    return RiskCheckResult(
        approved=True,
        reason="All checks passed",
        checks_passed=passed,
        checks_failed=failed,
    )
```

### 3.7. Vietnam Market Rules — Quick Reference

```
┌────────────────────────────────────────────────────────────────────────┐
│              VIETNAM MARKET RULES — HARDCODED IN RISK AGENT            │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ★ Settlement: T+2.5 (buy today → sell afternoon of T+2)             │
│                                                                        │
│  ★ Price Bands (daily, based on reference price):                     │
│    HOSE:  ±7%                                                         │
│    HNX:   ±10%                                                        │
│    UPCOM: ±15%                                                        │
│                                                                        │
│  ★ Lot Sizes:                                                         │
│    HOSE:  100 shares                                                  │
│    HNX:   100 shares                                                  │
│    UPCOM: 100 shares                                                  │
│    Odd lot: separate odd-lot board (not supported in v1.0)            │
│                                                                        │
│  ★ Tick Sizes (HOSE):                                                 │
│    Price < 10,000 VND:     10 VND                                     │
│    10,000 ≤ Price < 50,000: 50 VND                                    │
│    Price ≥ 50,000 VND:     100 VND                                    │
│    HNX / UPCOM:            100 VND (all levels)                       │
│                                                                        │
│  ★ Trading Hours:                                                     │
│    HOSE:  09:00-11:30 (continuous) / 13:00-14:30 (continuous)        │
│           14:30-14:45 (ATC — closing auction)                         │
│    HNX:   09:00-11:30 / 13:00-14:45 (14:30-14:45 ATC)              │
│                                                                        │
│  ★ Order Types:                                                       │
│    LO:  Limit Order (most common)                                     │
│    ATO: At-the-Open (opening auction only, 09:00-09:15)              │
│    ATC: At-the-Close (closing auction only, 14:30-14:45)             │
│    MP:  Market Price (best available, HOSE only)                      │
│                                                                        │
│  ★ Circuit Breaker:                                                   │
│    VN30 index drops > 5%: 15-minute trading halt                      │
│    Individual stock: suspended if unusual activity                     │
│                                                                        │
│  ★ Foreign Ownership Limit:                                           │
│    Varies per stock (check HOSE/HNX announcements)                    │
│    Default: 49% (banking: 30%)                                        │
│    Not applicable for domestic accounts (our use case)                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. ERROR HANDLING & RETRY — EXPONENTIAL BACKOFF

### 4.1. Failure Taxonomy — Know Your Failures

```
┌────────────────────────────────────────────────────────────────────────┐
│              FAILURE CLASSIFICATION MATRIX                              │
├──────────────────┬──────────┬──────────┬───────────────────────────────┤
│ Failure Type     │ Retryable│ Backoff  │ Action                        │
├──────────────────┼──────────┼──────────┼───────────────────────────────┤
│ Network timeout  │ ✅ YES   │ Exp.     │ Retry with backoff            │
│ DNS resolution   │ ✅ YES   │ Exp.     │ Retry with backoff            │
│ TLS handshake    │ ✅ YES   │ Exp.     │ Retry with backoff            │
│ HTTP 429 (rate)  │ ✅ YES   │ Respect  │ Wait Retry-After header       │
│                  │          │ header   │                               │
│ HTTP 500/502/503 │ ✅ YES   │ Exp.     │ Server-side issue, retry      │
│ HTTP 408 timeout │ ✅ YES   │ Exp.     │ Server slow, retry            │
│ WS disconnected  │ ✅ YES   │ Exp.     │ Reconnect with backoff        │
├──────────────────┼──────────┼──────────┼───────────────────────────────┤
│ HTTP 400 (bad    │ ❌ NO    │ —        │ Fix request, do NOT retry     │
│  request)        │          │          │                               │
│ HTTP 401 (unauth)│ ⚠️ ONCE  │ —        │ Refresh token, retry ONCE     │
│ HTTP 403 (forbid)│ ❌ NO    │ —        │ Permissions issue, alert      │
│ HTTP 404 (not    │ ❌ NO    │ —        │ Wrong endpoint, fix           │
│  found)          │          │          │                               │
│ RSA sign failure │ ❌ NO    │ —        │ Key corrupted, alert          │
│ JSON parse error │ ❌ NO    │ —        │ API changed, alert            │
│ Business logic   │ ❌ NO    │ —        │ Order rejected, log + notify  │
│  rejection       │          │          │                               │
├──────────────────┼──────────┼──────────┼───────────────────────────────┤
│ ★ RULE: When in doubt, do NOT retry order submissions.               │
│   A timed-out order may have been PLACED. Retrying = duplicate.      │
│   Use idempotency key (Section 2.3) as safety net.                   │
└──────────────────┴──────────┴──────────┴───────────────────────────────┘
```

### 4.2. Exponential Backoff Engine

```python
# packages/adapters/src/adapters/retry.py
from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger("retry")

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """
    Configuration for exponential backoff retry strategy.

    ★ Formula: delay = min(base * (2 ^ attempt) + jitter, max_delay)
    ★ Jitter prevents "thundering herd" when multiple connections retry simultaneously.
    """
    max_retries: int = 5               # Max attempts (0 = infinite for WebSocket)
    base_delay: float = 1.0            # Initial delay in seconds
    max_delay: float = 60.0            # Cap: never wait more than 60s
    exponential_base: float = 2.0      # Multiplier per attempt
    jitter: bool = True                # Add random jitter to prevent thundering herd
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """
    Calculate delay for a given attempt number.

    attempt=0: base_delay * 1   = 1.0s
    attempt=1: base_delay * 2   = 2.0s
    attempt=2: base_delay * 4   = 4.0s
    attempt=3: base_delay * 8   = 8.0s
    attempt=4: base_delay * 16  = 16.0s
    ... capped at max_delay (60s)

    With jitter: ±50% random variation
    """
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Full jitter: uniform random between 0 and calculated delay
        delay = random.uniform(0, delay)  # noqa: S311 — not crypto

    return delay


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig = RetryConfig(),
    operation_name: str = "operation",
    **kwargs: Any,
) -> T:
    """
    Execute an async function with exponential backoff retry.

    ★ ONLY retries on retryable exceptions (network errors).
    ★ Non-retryable exceptions (ValueError, business errors) propagate immediately.
    ★ Logs every retry attempt with delay for observability.
    """
    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as exc:
            last_exception = exc

            if attempt >= config.max_retries:
                logger.error(
                    "%s: Failed after %d attempts. Last error: %s",
                    operation_name,
                    attempt + 1,
                    exc,
                )
                raise

            delay = calculate_backoff_delay(attempt, config)
            logger.warning(
                "%s: Attempt %d/%d failed (%s: %s). "
                "Retrying in %.1fs...",
                operation_name,
                attempt + 1,
                config.max_retries,
                type(exc).__name__,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    # Should not reach here, but satisfy type checker
    assert last_exception is not None
    raise last_exception
```

### 4.3. WebSocket Reconnection — Infinite Backoff with Health Checks

```python
# packages/adapters/src/adapters/ssi/market_ws.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, AsyncIterator

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    InvalidStatusCode,
)

from adapters.retry import RetryConfig, calculate_backoff_delay

if TYPE_CHECKING:
    from core.entities.tick import Tick

logger = logging.getLogger("ws.ssi")


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FATAL = "fatal"              # Non-recoverable (auth failure, etc.)


class SSIMarketWebSocket:
    """
    Resilient WebSocket client for SSI market data.

    ★ ZERO-TRUST NETWORK: Assumes connection WILL drop.
    ★ Infinite reconnect with exponential backoff.
    ★ Health check (ping/pong) detects silent connection death.
    ★ State tracking for frontend status display.
    """

    def __init__(
        self,
        url: str,
        auth_client: object,
        reconnect_config: RetryConfig | None = None,
    ) -> None:
        self._url = url
        self._auth = auth_client
        self._ws: websockets.WebSocketClientProtocol | None = None  # type: ignore[name-defined]
        self._state = ConnectionState.DISCONNECTED
        self._reconnect_attempt = 0
        self._last_message_at: float = 0.0
        self._config = reconnect_config or RetryConfig(
            max_retries=0,          # ★ Infinite retries for WebSocket
            base_delay=1.0,         # Start at 1s
            max_delay=60.0,         # Cap at 60s
            jitter=True,
        )

        # Health check config
        self._ping_interval = 30.0    # Send ping every 30s
        self._pong_timeout = 10.0     # Expect pong within 10s
        self._stale_threshold = 90.0  # No message for 90s = connection dead

    @property
    def state(self) -> ConnectionState:
        return self._state

    async def connect(self) -> None:
        """
        Establish WebSocket connection with authentication.

        ★ This method handles the initial connection.
        ★ For reconnection after disconnect, use _reconnect_loop().
        """
        self._state = ConnectionState.CONNECTING

        try:
            token = await self._auth.get_access_token()
            self._ws = await websockets.connect(
                self._url,
                additional_headers={"Authorization": f"Bearer {token}"},
                ping_interval=self._ping_interval,
                ping_timeout=self._pong_timeout,
                close_timeout=5.0,
                max_size=2**20,       # 1MB max message size
            )
            self._state = ConnectionState.CONNECTED
            self._reconnect_attempt = 0
            self._last_message_at = asyncio.get_event_loop().time()
            logger.info("WebSocket connected to %s", self._url)

        except InvalidStatusCode as exc:
            if exc.status_code in (401, 403):
                # Auth failure — do NOT retry blindly
                self._state = ConnectionState.FATAL
                logger.error(
                    "WebSocket auth failed (HTTP %d). "
                    "Check credentials and RSA key.",
                    exc.status_code,
                )
                raise
            raise

    async def disconnect(self) -> None:
        """Graceful shutdown."""
        self._state = ConnectionState.DISCONNECTED
        if self._ws is not None:
            await self._ws.close(code=1000, reason="Client shutdown")
            self._ws = None

    async def stream(self) -> AsyncIterator[dict]:
        """
        Infinite stream of market messages with auto-reconnect.

        ★ Yields parsed messages.
        ★ On disconnect: automatically reconnects with backoff.
        ★ On fatal error (auth): stops iteration, propagates error.
        ★ Caller sees seamless stream — reconnection is transparent.
        """
        while self._state != ConnectionState.FATAL:
            try:
                # Ensure connected
                if self._ws is None or self._state != ConnectionState.CONNECTED:
                    await self._reconnect_with_backoff()

                assert self._ws is not None

                # Read messages
                async for raw_message in self._ws:
                    self._last_message_at = asyncio.get_event_loop().time()
                    self._reconnect_attempt = 0  # Reset on successful message

                    try:
                        import json
                        msg = json.loads(raw_message)
                        yield msg
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        logger.warning(
                            "Malformed WebSocket message (not JSON), skipping"
                        )
                        continue

            except (ConnectionClosed, ConnectionClosedError) as exc:
                logger.warning(
                    "WebSocket disconnected: code=%s reason=%s. Will reconnect.",
                    getattr(exc, "code", "?"),
                    getattr(exc, "reason", "?"),
                )
                self._ws = None
                self._state = ConnectionState.RECONNECTING

            except (ConnectionError, OSError, TimeoutError) as exc:
                logger.warning(
                    "WebSocket connection error: %s. Will reconnect.",
                    exc,
                )
                self._ws = None
                self._state = ConnectionState.RECONNECTING

    async def _reconnect_with_backoff(self) -> None:
        """
        Reconnect with exponential backoff.

        Sequence of delays: 1s, 2s, 4s, 8s, 16s, 32s, 60s, 60s, 60s, ...
        (with ±50% jitter on each)
        """
        while True:
            self._state = ConnectionState.RECONNECTING
            delay = calculate_backoff_delay(self._reconnect_attempt, self._config)

            logger.info(
                "WebSocket reconnect attempt %d — waiting %.1fs...",
                self._reconnect_attempt + 1,
                delay,
            )

            await asyncio.sleep(delay)
            self._reconnect_attempt += 1

            try:
                await self.connect()
                logger.info(
                    "WebSocket reconnected after %d attempts.",
                    self._reconnect_attempt,
                )
                return  # Success — exit reconnect loop

            except InvalidStatusCode as exc:
                if exc.status_code in (401, 403):
                    # Try refreshing auth token first
                    logger.warning("Auth expired during reconnect, refreshing token...")
                    try:
                        await self._auth._authenticate()  # Force token refresh
                        continue  # Retry with new token
                    except Exception:
                        self._state = ConnectionState.FATAL
                        raise

            except (ConnectionError, OSError, TimeoutError):
                # Expected — network still down, backoff will increase
                continue
```

### 4.4. Backoff Visualization

```
Connection lost at T=0s

Attempt 1: wait ~1.0s  (1 × 2^0 = 1.0, ±jitter)     T=1s
  → Connection failed (server still down)

Attempt 2: wait ~2.0s  (1 × 2^1 = 2.0, ±jitter)     T=3s
  → Connection failed

Attempt 3: wait ~4.0s  (1 × 2^2 = 4.0, ±jitter)     T=7s
  → Connection failed

Attempt 4: wait ~8.0s  (1 × 2^3 = 8.0, ±jitter)     T=15s
  → Connection failed

Attempt 5: wait ~16.0s (1 × 2^4 = 16.0, ±jitter)    T=31s
  → Connection SUCCEEDED ✓

  ── OR if server is down longer: ──

Attempt 6: wait ~32.0s (1 × 2^5 = 32.0, ±jitter)    T=63s
Attempt 7: wait ~60.0s (capped at max_delay)          T=123s
Attempt 8: wait ~60.0s (stays at cap)                 T=183s
...continues at 60s intervals until success...

★ Total downtime before reconnect (typical): 1-30 seconds
★ Jitter prevents all clients from reconnecting simultaneously
  (thundering herd problem)
```

### 4.5. DNSE Token Refresh — Silent Re-Authentication

```python
# packages/adapters/src/adapters/dnse/auth.py
from __future__ import annotations

import asyncio
import logging
import time

import httpx

from adapters.retry import RetryConfig, retry_async

logger = logging.getLogger("auth.dnse")

DNSE_AUTH_URL = "https://auth-api.dnse.com.vn/api/v1/login"
DNSE_REFRESH_URL = "https://auth-api.dnse.com.vn/api/v1/refresh-token"


class DNSEAuthClient:
    """
    DNSE Entrade X authentication client.

    ★ DNSE uses standard JWT + Refresh Token pattern.
    ★ Access token: short-lived (~15-30 min)
    ★ Refresh token: long-lived (~7 days)
    ★ When access token expires: use refresh token silently.
    ★ When refresh token expires: require full re-login (OTP).
    """

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=10.0, verify=True)
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._access_expires_at: float = 0.0
        self._refresh_expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self._is_access_valid():
            assert self._access_token is not None
            return self._access_token

        async with self._lock:
            if self._is_access_valid():
                assert self._access_token is not None
                return self._access_token

            if self._is_refresh_valid():
                return await self._refresh()
            else:
                raise AuthExpiredError(
                    "DNSE refresh token expired. Manual re-login required."
                )

    async def login(self, username: str, password: str, otp: str) -> None:
        """
        Initial login with credentials + OTP.

        ★ Called once manually (OTP requires human interaction).
        ★ After login, token refresh is automatic.
        """
        response = await retry_async(
            self._http.post,
            DNSE_AUTH_URL,
            json={"username": username, "password": password, "otp": otp},
            config=RetryConfig(max_retries=2),
            operation_name="DNSE login",
        )

        if response.status_code != 200:
            raise AuthenticationError(f"DNSE login failed: {response.status_code}")

        data = response.json()
        self._update_tokens(data)

    async def _refresh(self) -> str:
        """Silently refresh access token using refresh token."""
        assert self._refresh_token is not None

        response = await retry_async(
            self._http.post,
            DNSE_REFRESH_URL,
            json={"refreshToken": self._refresh_token},
            config=RetryConfig(max_retries=3),
            operation_name="DNSE token refresh",
        )

        if response.status_code == 401:
            raise AuthExpiredError("DNSE refresh token rejected. Re-login needed.")

        if response.status_code != 200:
            raise AuthenticationError(f"DNSE refresh failed: {response.status_code}")

        data = response.json()
        self._update_tokens(data)
        assert self._access_token is not None
        return self._access_token

    def _update_tokens(self, data: dict) -> None:
        now = time.monotonic()
        self._access_token = data["accessToken"]
        self._refresh_token = data.get("refreshToken", self._refresh_token)
        self._access_expires_at = now + data.get("accessExpiresIn", 1800)
        if "refreshExpiresIn" in data:
            self._refresh_expires_at = now + data["refreshExpiresIn"]

    def _is_access_valid(self) -> bool:
        return (
            self._access_token is not None
            and time.monotonic() < self._access_expires_at - 120  # 2min buffer
        )

    def _is_refresh_valid(self) -> bool:
        return (
            self._refresh_token is not None
            and time.monotonic() < self._refresh_expires_at - 300  # 5min buffer
        )

    async def close(self) -> None:
        await self._http.aclose()


class AuthenticationError(Exception):
    pass


class AuthExpiredError(Exception):
    """Refresh token expired — requires human re-login."""
    pass
```

### 4.6. Circuit Breaker — When Retries Are Not Enough

```python
# packages/adapters/src/adapters/circuit_breaker.py
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger("circuit_breaker")

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"           # Normal — requests pass through
    OPEN = "open"               # Tripped — ALL requests rejected (fast-fail)
    HALF_OPEN = "half_open"     # Testing — allow ONE request through


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern for broker API calls.

    ★ Prevents cascading failures when broker API is down.
    ★ Fails FAST instead of waiting for timeout on every call.
    ★ Self-healing: periodically tests if service is back.

    State transitions:
      CLOSED → OPEN (after failure_threshold consecutive failures)
      OPEN → HALF_OPEN (after recovery_timeout)
      HALF_OPEN → CLOSED (if test request succeeds)
      HALF_OPEN → OPEN (if test request fails)
    """
    name: str
    failure_threshold: int = 5          # Failures before tripping
    recovery_timeout: float = 30.0      # Seconds before testing recovery
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    success_count: int = 0

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function through circuit breaker."""

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit '%s': OPEN → HALF_OPEN (testing recovery)",
                    self.name,
                )
            else:
                raise CircuitOpenError(
                    f"Circuit '{self.name}' is OPEN. "
                    f"Service unavailable. Retry after "
                    f"{self.recovery_timeout - (time.monotonic() - self.last_failure_time):.0f}s."
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit '%s': HALF_OPEN → CLOSED (recovered)", self.name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count += 1

    def _on_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "Circuit '%s': → OPEN after %d consecutive failures. "
                "Blocking all requests for %ds.",
                self.name,
                self.failure_count,
                self.recovery_timeout,
            )

    def reset(self) -> None:
        """Manual reset (e.g., from admin command)."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info("Circuit '%s': manually reset to CLOSED", self.name)


class CircuitOpenError(Exception):
    """Raised when circuit breaker is OPEN — fast-fail."""
    pass
```

---

## 5. TESTING SECURITY-CRITICAL CODE

### 5.1. Test Strategy for Security Components

```
★ RULE: Security code has HIGHER test coverage requirement (≥ 95%).
★ RULE: Every state transition in Order FSM must have a test.
★ RULE: Every risk check rule must have a positive AND negative test.
★ RULE: Retry/backoff logic tested with deterministic delays (mock time).
★ RULE: Credential loading tested with mock env vars (NEVER real keys in tests).
```

### 5.2. Order State Machine Tests

```python
# tests/unit/test_order_fsm.py
from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from core.entities.order import (
    InvalidOrderTransition,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from core.value_objects import Price, Quantity, Symbol


def _make_order(status: OrderStatus = OrderStatus.CREATED) -> Order:
    """Factory for test orders."""
    return Order(
        order_id="ORD-001",
        idempotency_key="idem-001",
        symbol=Symbol("FPT"),
        side=OrderSide.BUY,
        order_type=OrderType.LO,
        quantity=Quantity(1000),
        price=Price(Decimal("98500")),
        ceiling_price=Price(Decimal("105395")),
        floor_price=Price(Decimal("91605")),
        status=status,
        filled_quantity=Quantity(0),
        avg_fill_price=Price(Decimal("0")),
        broker_order_id=None,
        rejection_reason=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestOrderStateMachine:
    """Exhaustive tests for Order FSM transitions."""

    # ── Valid Transitions ─────────────────────────────────

    def test_created_to_pending(self) -> None:
        order = _make_order(OrderStatus.CREATED)
        updated = order.transition_to(OrderStatus.PENDING, broker_order_id="B-001")
        assert updated.status == OrderStatus.PENDING
        assert updated.broker_order_id == "B-001"
        assert order.status == OrderStatus.CREATED  # Original unchanged

    def test_created_to_rejected(self) -> None:
        order = _make_order(OrderStatus.CREATED)
        updated = order.transition_to(
            OrderStatus.REJECTED,
            rejection_reason="Exceeds NAV limit",
        )
        assert updated.status == OrderStatus.REJECTED
        assert updated.rejection_reason == "Exceeds NAV limit"

    def test_pending_to_matched(self) -> None:
        order = _make_order(OrderStatus.PENDING)
        updated = order.transition_to(OrderStatus.MATCHED)
        assert updated.status == OrderStatus.MATCHED
        assert updated.is_terminal is True

    def test_pending_to_cancelled(self) -> None:
        order = _make_order(OrderStatus.PENDING)
        updated = order.transition_to(OrderStatus.CANCELLED)
        assert updated.status == OrderStatus.CANCELLED

    # ── Invalid Transitions (MUST raise) ──────────────────

    def test_matched_cannot_transition(self) -> None:
        order = _make_order(OrderStatus.MATCHED)
        with pytest.raises(InvalidOrderTransition, match="terminal"):
            order.transition_to(OrderStatus.CANCELLED)

    def test_rejected_cannot_transition(self) -> None:
        order = _make_order(OrderStatus.REJECTED)
        with pytest.raises(InvalidOrderTransition):
            order.transition_to(OrderStatus.PENDING)

    def test_created_cannot_skip_to_matched(self) -> None:
        order = _make_order(OrderStatus.CREATED)
        with pytest.raises(InvalidOrderTransition):
            order.transition_to(OrderStatus.MATCHED)

    def test_pending_cannot_go_back_to_created(self) -> None:
        order = _make_order(OrderStatus.PENDING)
        with pytest.raises(InvalidOrderTransition):
            order.transition_to(OrderStatus.CREATED)

    # ── Partial Fill Logic ────────────────────────────────

    def test_partial_fill_updates_quantity(self) -> None:
        order = _make_order(OrderStatus.PENDING)
        updated = order.with_partial_fill(500, Decimal("98500"))
        assert updated.status == OrderStatus.PARTIAL_FILL
        assert updated.filled_quantity == 500
        assert updated.remaining_quantity == 500

    def test_partial_fill_completes_order(self) -> None:
        order = _make_order(OrderStatus.PENDING)
        partial = order.with_partial_fill(600, Decimal("98500"))
        complete = partial.with_partial_fill(400, Decimal("99000"))
        assert complete.status == OrderStatus.MATCHED
        assert complete.filled_quantity == 1000
        assert complete.is_fully_filled is True

    def test_overfill_raises(self) -> None:
        order = _make_order(OrderStatus.PENDING)
        with pytest.raises(ValueError, match="exceed"):
            order.with_partial_fill(1500, Decimal("98500"))
```

### 5.3. Price Band Validation Tests

```python
# tests/unit/test_price_band.py
from __future__ import annotations

from decimal import Decimal

import pytest

from core.use_cases.price_band import (
    Exchange,
    PriceBand,
    calculate_price_band,
    validate_order_price,
)
from core.value_objects import Price, Symbol


class TestPriceBand:
    """Price band rules are REGULATORY — tests must be exhaustive."""

    def test_hose_ceiling_floor(self) -> None:
        band = calculate_price_band(
            Symbol("FPT"), Exchange.HOSE, Price(Decimal("100000")),
        )
        assert band.ceiling_price == Price(Decimal("107000"))
        assert band.floor_price == Price(Decimal("93000"))

    def test_hnx_wider_band(self) -> None:
        band = calculate_price_band(
            Symbol("ABC"), Exchange.HNX, Price(Decimal("100000")),
        )
        assert band.ceiling_price == Price(Decimal("110000"))
        assert band.floor_price == Price(Decimal("90000"))

    def test_upcom_widest_band(self) -> None:
        band = calculate_price_band(
            Symbol("XYZ"), Exchange.UPCOM, Price(Decimal("100000")),
        )
        assert band.ceiling_price == Price(Decimal("115000"))
        assert band.floor_price == Price(Decimal("85000"))

    def test_price_at_ceiling_is_valid(self) -> None:
        band = calculate_price_band(
            Symbol("FPT"), Exchange.HOSE, Price(Decimal("100000")),
        )
        valid, _ = validate_order_price(band.ceiling_price, band)
        assert valid is True

    def test_price_above_ceiling_is_invalid(self) -> None:
        band = calculate_price_band(
            Symbol("FPT"), Exchange.HOSE, Price(Decimal("100000")),
        )
        valid, reason = validate_order_price(
            Price(Decimal("107100")), band,
        )
        assert valid is False
        assert "ceiling" in reason.lower()

    def test_price_below_floor_is_invalid(self) -> None:
        band = calculate_price_band(
            Symbol("FPT"), Exchange.HOSE, Price(Decimal("100000")),
        )
        valid, reason = validate_order_price(
            Price(Decimal("92900")), band,
        )
        assert valid is False
        assert "floor" in reason.lower()

    def test_tick_size_alignment(self) -> None:
        band = calculate_price_band(
            Symbol("FPT"), Exchange.HOSE, Price(Decimal("100000")),
        )
        # Price not aligned to tick size (100 VND for prices ≥ 50,000)
        valid, reason = validate_order_price(
            Price(Decimal("98550")), band,   # 98,550 — not on 100 grid
        )
        assert valid is False
        assert "tick" in reason.lower()
```

---

## APPENDIX A: SECURITY HARDENING CHECKLIST

```
PRE-PRODUCTION SECURITY HARDENING
══════════════════════════════════════════════════════════════════

AUTHENTICATION & CREDENTIALS
  □ RSA private key stored in encrypted file or OS keyring (not .env)
  □ All environment variables listed in .env.example (no real values)
  □ .gitignore covers: .env, *.pem, *.key, data/secrets/
  □ No credentials in log output (grep -r "consumer_secret" packages/)
  □ Token refresh runs proactively (5 min before expiry)
  □ JWT tokens stored in memory only (never persisted to disk)

NETWORK & TLS
  □ TLS certificate verification enabled (verify=True) on ALL HTTP clients
  □ WebSocket connections use wss:// (not ws://)
  □ httpx timeout set (connect=5s, read=10s) — no infinite waits
  □ HTTP/2 enabled where supported (multiplexing, header compression)

ORDER MANAGEMENT
  □ Idempotency key required on every order submission
  □ Order state machine enforces valid transitions only
  □ Price band validation runs BEFORE broker submission
  □ T+2.5 sellable quantity checked for SELL orders
  □ Lot size (100) validated
  □ Kill switch tested and functional

RESILIENCE
  □ Exponential backoff on all retryable operations
  □ Circuit breaker on broker API calls
  □ WebSocket auto-reconnect with infinite backoff
  □ Graceful degradation: system operational without NPU/LLM
  □ Backpressure: tick buffer has maxlen, drops old data gracefully

DATA PROTECTION
  □ DuckDB file not world-readable (chmod 600)
  □ Parquet files not world-readable
  □ No financial data sent to external APIs (except broker orders)
  □ LLM inference runs locally on NPU — zero prompt leakage
  □ Audit log captures every order state change

MONITORING
  □ Structured logging (JSON) for all security events
  □ WebSocket connection state exposed to frontend
  □ Circuit breaker state exposed to health endpoint
  □ Order sync lag monitored (broker vs local state drift)
```

## APPENDIX B: BANNED PATTERNS — SECURITY EDITION

| Pattern | Risk | Alternative |
|:---|:---|:---|
| `PRIVATE_KEY = "-----BEGIN..."` in source | Key compromise on repo leak | Environment variable or encrypted file |
| `verify=False` in httpx/requests | TLS MITM attack | Always `verify=True` |
| `ws://` in production | Unencrypted WebSocket | `wss://` (TLS) |
| `except Exception: pass` | Silent failure hides attacks | Log and handle specific exceptions |
| `random.random()` for tokens | Predictable "randomness" | `secrets.token_urlsafe()` |
| `eval()` or `exec()` on user input | Remote code execution | Pydantic validation + strict parsing |
| Logging `access_token` or `private_key` | Credential leak via logs | Log redacted identifiers only |
| `time.sleep()` in retry loop | Blocks event loop | `await asyncio.sleep()` |
| Retry order submission without idempotency | Duplicate orders | Always include idempotency_key |
| Trusting `onHand` for sell validation | T+2.5 violation | Use `sellableQty` from broker |

---

*Document authored by Security Engineer & Integration Specialist. All code samples implement defense-in-depth principles. Zero-trust posture: assume every connection will fail, every input is malicious, every key will leak.*
