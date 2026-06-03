"""
safe.py - Gnosis Safe state reader.

Supports Safe v1.x and v2.x via the same ABI. Returns a SafeState
with owners, threshold, nonce, version, and balance.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from rpc import (
    RpcClient,
    RpcError,
    SELECTORS,
    decode_address_array,
    decode_uint256,
    decode_string,
)


@dataclass
class SafeState:
    address: str
    chain_id: int
    version: str = ""           # e.g. "1.3.0" or "2.0.0"
    owners: List[str] = field(default_factory=list)
    threshold: int = 0
    nonce: int = 0
    eth_balance: int = 0
    is_contract: bool = False
    has_code: bool = False
    raw: dict = field(default_factory=dict)


def _read_address_array(rpc: RpcClient, safe: str, sig: str) -> List[str]:
    """Read a function that returns `address[]` via eth_call."""
    try:
        raw = rpc.eth_call(safe, SELECTORS[sig])
    except RpcError:
        return []
    return decode_address_array(raw)


def _read_uint(rpc: RpcClient, safe: str, sig: str) -> int:
    try:
        raw = rpc.eth_call(safe, SELECTORS[sig])
        return decode_uint256(raw)
    except RpcError:
        return 0


def _read_string(rpc: RpcClient, safe: str, sig: str) -> str:
    try:
        raw = rpc.eth_call(safe, SELECTORS[sig])
        return decode_string(raw) or ""
    except RpcError:
        return ""


def read(rpc: RpcClient, safe: str) -> SafeState:
    """Read full state for a Safe. Returns a SafeState; raises RpcError
    if the address has no code (so the caller can fail with a clear
    message)."""
    safe_lc = safe.lower()
    code = rpc.get_code(safe_lc)
    if not code or code == "0x" or len(code) < 4:
        raise RpcError(f"address {safe} has no contract code (not a Safe)")

    owners = _read_address_array(rpc, safe_lc, "getOwners()")
    threshold = _read_uint(rpc, safe_lc, "getThreshold()")
    nonce = _read_uint(rpc, safe_lc, "nonce()")
    version = _read_string(rpc, safe_lc, "VERSION()")
    bal = rpc.balance(safe_lc)
    chain_id = rpc.chain_id()

    return SafeState(
        address=safe_lc,
        chain_id=chain_id,
        version=version or "unknown",
        owners=owners,
        threshold=threshold,
        nonce=nonce,
        eth_balance=bal,
        is_contract=True,
        has_code=True,
        raw={"code_size": len(code)},
    )
