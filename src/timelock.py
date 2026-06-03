"""
timelock.py - TimelockController state reader.

Reads `getMinDelay()` from an OpenZeppelin TimelockController. We
also do a quick "is this a timelock?" check by trying to call
`getMinDelay()`; if it returns a sane uint256 in [0, 365 days], we
treat the address as a TimelockController.
"""
from __future__ import annotations
from dataclasses import dataclass

from rpc import RpcClient, RpcError, SELECTORS, decode_uint256


# Sane bounds: 0 (no delay) up to 30 days
TIMELOCK_MIN_DELAY_MIN = 0
TIMELOCK_MIN_DELAY_MAX = 30 * 24 * 60 * 60  # seconds


@dataclass
class TimelockState:
    address: str
    min_delay: int = 0
    is_timelock: bool = False
    raw: dict = None  # type: ignore[assignment]


def read(rpc: RpcClient, addr: str) -> TimelockState:
    addr_lc = addr.lower()
    code = rpc.get_code(addr_lc)
    if not code or code == "0x" or len(code) < 4:
        return TimelockState(address=addr_lc, is_timelock=False, raw={"code_size": len(code)})
    try:
        raw = rpc.eth_call(addr_lc, SELECTORS["getMinDelay()"])
        delay = decode_uint256(raw)
    except RpcError:
        return TimelockState(address=addr_lc, is_timelock=False, raw={"code_size": len(code)})
    in_range = TIMELOCK_MIN_DELAY_MIN <= delay <= TIMELOCK_MIN_DELAY_MAX
    return TimelockState(
        address=addr_lc,
        min_delay=delay if in_range else 0,
        is_timelock=in_range,
        raw={"raw_delay": delay, "in_range": in_range, "code_size": len(code)},
    )


def format_delay(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
