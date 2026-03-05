from __future__ import annotations

import os
from typing import Literal

from adapters.ssi.auth import SSIAuthClient
from adapters.ssi.broker import SSIBrokerClient
from adapters.ssi.credential_manager import CredentialManager, StorageTier
from adapters.ssi.portfolio import SSIPortfolioClient


def _is_true(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def live_broker_enabled() -> bool:
    return _is_true(os.getenv("ENABLE_LIVE_BROKER", "false"))


def live_broker_provider() -> Literal["ssi"]:
    provider = os.getenv("LIVE_BROKER_PROVIDER", "ssi").strip().lower()
    if provider != "ssi":
        msg = f"Unsupported LIVE_BROKER_PROVIDER '{provider}'. Only 'ssi' is currently supported."
        raise RuntimeError(msg)
    return "ssi"


def _resolve_storage_tier() -> StorageTier:
    raw = os.getenv("SSI_CREDENTIAL_TIER", "env_var").strip().lower()
    if raw in {"env", "env_var", "environment"}:
        return StorageTier.ENV_VAR
    if raw in {"encrypted_file", "file"}:
        return StorageTier.ENCRYPTED_FILE
    if raw in {"os_keyring", "keyring"}:
        return StorageTier.OS_KEYRING
    msg = f"Unsupported SSI_CREDENTIAL_TIER '{raw}'."
    raise RuntimeError(msg)


def _load_ssi_runtime_config() -> tuple[SSIAuthClient, str]:
    account_no = os.getenv("SSI_ACCOUNT_NO", "").strip()
    if not account_no:
        raise RuntimeError("SSI_ACCOUNT_NO is missing.")
    manager = CredentialManager(tier=_resolve_storage_tier())
    credentials = manager.load_credentials()
    auth = SSIAuthClient(credentials=credentials)
    return auth, account_no


def create_ssi_broker_client() -> tuple[SSIBrokerClient, SSIAuthClient]:
    live_broker_provider()
    auth, account_no = _load_ssi_runtime_config()
    return SSIBrokerClient(auth_client=auth, account_no=account_no), auth


def create_ssi_portfolio_client() -> tuple[SSIPortfolioClient, SSIAuthClient]:
    live_broker_provider()
    auth, _account_no = _load_ssi_runtime_config()
    return SSIPortfolioClient(auth_client=auth), auth

