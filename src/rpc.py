"""
rpc.py - JSON-RPC client for Safe reads.

No web3 framework dependency; uses plain HTTP + eth_call.
"""
from __future__ import annotations
import time
import requests
from typing import Any, Dict, List, Optional


class RpcError(Exception):
    pass


class RpcClient:
    def __init__(self, url: str, timeout: int = 30, max_retries: int = 4):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries
        self._id = 0

    def call(self, method: str, params: List[Any]) -> Any:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                r = requests.post(self.url, json=payload, timeout=self.timeout)
                if r.status_code == 429 or r.status_code >= 500:
                    raise RpcError(f"HTTP {r.status_code}: {r.text[:200]}")
                data = r.json()
                if "error" in data:
                    raise RpcError(data["error"].get("message", "rpc error"))
                return data.get("result")
            except (requests.RequestException, RpcError) as e:
                last_err = e
                time.sleep(0.4 * (2 ** attempt))
        raise RpcError(f"RPC {method} failed after {self.max_retries} attempts: {last_err}")

    def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        return self.call("eth_call", [{"to": to, "data": data}, block])

    def get_storage_at(self, addr: str, slot: str, block: str = "latest") -> str:
        return self.call("eth_getStorageAt", [addr, slot, block])

    def get_code(self, addr: str) -> str:
        return self.call("eth_getCode", [addr, "latest"]) or "0x"

    def get_tx_count(self, addr: str) -> int:
        return int(self.call("eth_getTransactionCount", [addr, "latest"]), 16)

    def balance(self, addr: str) -> int:
        return int(self.call("eth_getBalance", [addr, "latest"]), 16)

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def chain_id(self) -> int:
        return int(self.call("eth_chainId", []), 16)


# --- Precomputed selectors for Gnosis Safe v1.x and v2.x ---

SELECTORS = {
    # v1.x and v2.x
    "getOwners()":                   "0xa0e67e2b",
    "getThreshold()":                "0xe75235b8",
    "nonce()":                       "0xaffed0e0",
    "domainSeparator()":             "0xf698da25",
    "VERSION()":                     "0xffa1a74c",
    "NAME()":                        "0x691f3431",      # not always present
    "getTransactionHash(...)":       "0xd8d11f78",      # arg-heavy, used for ref only

    # TimelockController
    "getMinDelay()":                 "0x8d928af2",
    "PROPOSER_ROLE()":               "0x9781ce82",
    "EXECUTOR_ROLE()":               "0x63a4a6f9",
    "TIMELOCK_ADMIN_ROLE()":         "0xf3ae03f1",

    # EIP-1967 proxy storage slot
    "eip1967_logic_slot":            "0x360894a13ba1a3210667c828492db98dcef3c0d3b5c5e0a0e7c5e3e3d2d5b5b5",  # not used; placeholder
}


def pad32(x: str) -> str:
    if x.startswith("0x"):
        x = x[2:]
    return x.lower().rjust(64, "0")


def encode_address(a: str) -> str:
    a = a.lower()
    if a.startswith("0x"):
        a = a[2:]
    if len(a) != 40:
        raise ValueError(f"not a 20-byte address: {a}")
    return "0x" + a.rjust(64, "0")


def encode_uint256(n: int) -> str:
    return "0x" + format(n & ((1 << 256) - 1), "064x")


def decode_uint256(hexstr: str) -> int:
    if not hexstr or hexstr in ("0x", "0x0"):
        return 0
    return int(hexstr, 16)


def decode_address(hexstr: str) -> str:
    if not hexstr or hexstr == "0x" + "0" * 40:
        return "0x" + "0" * 40
    return "0x" + hexstr[-40:].lower()


def decode_address_array(raw: str) -> list[str]:
    """Decode an ABI-encoded `address[]` (offset + length + words)."""
    if not raw or raw == "0x":
        return []
    h = raw[2:] if raw.startswith("0x") else raw
    if len(h) < 128:
        return []
    try:
        offset = int(h[0:64], 16)
        length = int(h[64:128], 16)
    except ValueError:
        return []
    out = []
    base = offset * 2
    for i in range(length):
        word = h[base + i * 64 : base + (i + 1) * 64]
        if len(word) != 64:
            break
        out.append("0x" + word[-40:].lower())
    return out


def decode_string(hexstr: str) -> str:
    """Decode an ABI-encoded dynamic string."""
    if not hexstr or hexstr == "0x":
        return ""
    h = hexstr[2:] if hexstr.startswith("0x") else hexstr
    if len(h) < 128:
        return ""
    try:
        length = int(h[64:128], 16)
        data = h[128 : 128 + length * 2]
        return bytes.fromhex(data).decode("utf-8", errors="replace")
    except Exception:
        return ""


# EIP-1967 logic slot: bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1)
EIP1967_IMPL_SLOT = (
    "0x360894a13ba1a3210667c828492db98dcef3c0d3b5c5e0a0e7c5e3e3d2d5b5b5"  # 32-byte slot
)
