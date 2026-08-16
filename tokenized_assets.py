#!/usr/bin/env python3
"""Collect USDC Transfer events from an Ethereum JSON-RPC endpoint.

Contract identity is fixed from Circle's official contract-address registry.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

RPC_URL = os.environ.get("ETH_RPC_URL")
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_TOPIC = "0x" + "0" * 64
DECIMALS = 6


def rpc(method: str, params: list[object]) -> object:
    if not RPC_URL:
        raise RuntimeError("ETH_RPC_URL is required")
    raw = json.dumps({"jsonrpc": "2.0", "id": method, "method": method, "params": params}).encode()
    req = Request(RPC_URL, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=60) as response:
        payload = json.loads(response.read())
    if payload.get("error"):
        raise RuntimeError(f"{method}: {payload['error']}")
    return payload["result"]


def decode_address(topic: str) -> str:
    return "0x" + topic[-40:]


def normalize_log(log: dict[str, object]) -> dict[str, object]:
    topics = log["topics"]
    if not isinstance(topics, list) or len(topics) < 3 or topics[0].lower() != TRANSFER_TOPIC:
        raise ValueError("not an ERC-20 Transfer log")
    sender = decode_address(str(topics[1]))
    recipient = decode_address(str(topics[2]))
    raw_value = int(str(log["data"]), 16)
    event_type = "transfer"
    if str(topics[1]).lower() == ZERO_TOPIC:
        event_type = "mint"
    elif str(topics[2]).lower() == ZERO_TOPIC:
        event_type = "burn"
    return {
        "event_type": event_type,
        "from": sender,
        "to": recipient,
        "raw_value": str(raw_value),
        "amount_usdc": raw_value / (10 ** DECIMALS),
        "block_number": int(str(log["blockNumber"]), 16),
        "block_hash": log["blockHash"],
        "transaction_hash": log["transactionHash"],
        "log_index": int(str(log["logIndex"]), 16),
    }


def collect(from_block: int, to_block: int) -> dict[str, object]:
    if from_block < 0 or to_block < from_block:
        raise ValueError("invalid block range")
    logs = rpc("eth_getLogs", [{
        "address": USDC,
        "fromBlock": hex(from_block),
        "toBlock": hex(to_block),
        "topics": [TRANSFER_TOPIC],
    }])
    events = [normalize_log(log) for log in logs]
    return {
        "schema_version": 1,
        "asset": "USDC",
        "chain": "ethereum-mainnet",
        "chain_id": 1,
        "contract_address": USDC,
        "contract_source": "https://developers.circle.com/stablecoins/usdc-contract-addresses",
        "decimals": DECIMALS,
        "from_block": from_block,
        "to_block": to_block,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "events": events,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-block", type=int, required=True)
    parser.add_argument("--to-block", type=int, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/usdc-events.json"))
    args = parser.parse_args()
    result = collect(args.from_block, args.to_block)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(result['events'])} events -> {args.output}")


if __name__ == "__main__":
    main()
