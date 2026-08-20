#!/usr/bin/env python3
"""Collect tokenized-asset evidence without historical Ethereum state calls."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tokenized_assets as base

DEFAULT_CHAIN_SEED = base.DEFAULT_DATA_ROOT / "normalized" / "chain_weekly.json"
MIN_SAMPLE_INTERVAL_SECONDS = 6 * 86400
DEFAULT_LOG_BLOCK_CHUNK = 50


def extend_chain_history(
    seed: dict[str, Any],
    rpc: base.EthereumRPC,
    finalized: dict[str, Any],
) -> list[dict[str, Any]]:
    records = [dict(row) for row in seed.get("records") or []]
    if not records:
        raise ValueError("canonical chain history seed is empty")
    records.sort(key=lambda row: int(row["block_number"]))
    first = datetime.fromisoformat(str(records[0]["observed_at"]))
    last = datetime.fromisoformat(str(records[-1]["observed_at"]))
    if (last - first).total_seconds() < 90 * 86400:
        raise ValueError("canonical chain history seed spans less than 90 days")

    final_num = base.block_number(finalized)
    final_time = base.block_timestamp(finalized)
    last_num = int(records[-1]["block_number"])
    last_time = int(last.timestamp())
    if final_num <= last_num or final_time - last_time < MIN_SAMPLE_INTERVAL_SECONDS:
        return records

    total_raw = base.eth_call_uint(
        rpc,
        base.USDC,
        base.TOTAL_SUPPLY_SELECTOR,
        hex(final_num),
        key=f"weekly:incremental:usdc-total-supply:{final_num}",
    )
    observed_at = datetime.fromtimestamp(final_time, UTC).isoformat()
    records.append(
        {
            "target_timestamp": observed_at,
            "observed_at": observed_at,
            "block_number": final_num,
            "block_hash": finalized["hash"],
            "chain_id": base.CHAIN_ID,
            "contract_address": base.USDC,
            "total_supply_raw": total_raw,
            "decimals": 6,
            "total_supply": total_raw / 1_000_000,
        }
    )
    return records


def collect_logs_chunked(
    rpc: base.EthereumRPC,
    from_block: int,
    to_block: int,
    topics: list[Any],
    key_prefix: str,
    block_chunk: int = DEFAULT_LOG_BLOCK_CHUNK,
) -> list[dict[str, Any]]:
    if block_chunk < 1:
        raise ValueError("block_chunk must be positive")
    logs: list[dict[str, Any]] = []
    for start in range(from_block, to_block + 1, block_chunk):
        end = min(to_block, start + block_chunk - 1)
        rows = rpc.call(
            "eth_getLogs",
            [
                {
                    "address": base.USDC,
                    "fromBlock": hex(start),
                    "toBlock": hex(end),
                    "topics": topics,
                }
            ],
            key=f"{key_prefix}:{start}:{end}",
        )
        logs.extend(rows)
    return logs


def collect_mint_burn_window_chunked(
    rpc: base.EthereumRPC,
    finalized: dict[str, Any],
    block_window: int,
    block_chunk: int = DEFAULT_LOG_BLOCK_CHUNK,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    final_num = base.block_number(finalized)
    start_num = max(0, final_num - block_window + 1)
    mint_logs = collect_logs_chunked(
        rpc,
        start_num,
        final_num,
        [base.TRANSFER_TOPIC, base.ZERO_TOPIC],
        "usdc-mint-logs",
        block_chunk,
    )
    burn_logs = collect_logs_chunked(
        rpc,
        start_num,
        final_num,
        [base.TRANSFER_TOPIC, None, base.ZERO_TOPIC],
        "usdc-burn-logs",
        block_chunk,
    )
    events = [base.normalize_log(row) for row in mint_logs] + [base.normalize_log(row) for row in burn_logs]
    events = sorted(events, key=lambda row: (row["block_number"], row["log_index"], row["transaction_hash"]))
    unique_blocks = sorted({int(row["block_number"]) for row in events})
    blocks: dict[int, dict[str, Any]] = {}
    for offset in range(0, len(unique_blocks), 100):
        chunk = unique_blocks[offset : offset + 100]
        blocks.update(rpc.batch_blocks(chunk, key=f"mint-burn-blocks:{offset // 100}"))
    for event in events:
        block = blocks[event["block_number"]]
        if str(block["hash"]).lower() != str(event["block_hash"]).lower():
            raise ValueError("mint/burn log block hash changed during collection")
        event["block_timestamp"] = datetime.fromtimestamp(base.block_timestamp(block), UTC).isoformat()
        event["chain_id"] = base.CHAIN_ID
        event["contract_address"] = base.USDC
    mint_events = [row for row in events if row["event_type"] == "mint"]
    burn_events = [row for row in events if row["event_type"] == "burn"]
    summary = {
        "from_block": start_num,
        "to_block": final_num,
        "to_block_hash": finalized["hash"],
        "chain_id": base.CHAIN_ID,
        "contract_address": base.USDC,
        "mint_event_count": len(mint_events),
        "mint_amount_usdc": sum(float(row["amount_usdc"]) for row in mint_events),
        "burn_event_count": len(burn_events),
        "burn_amount_usdc": sum(float(row["amount_usdc"]) for row in burn_events),
        "block_chunk": block_chunk,
    }
    summary["net_mint_minus_burn_usdc"] = summary["mint_amount_usdc"] - summary["burn_amount_usdc"]
    return events, summary


def collect_incremental(
    registry: dict[str, Any],
    issuer: dict[str, Any],
    data_root: Path,
    rpc_url: str,
    chain_seed: Path,
    mint_burn_blocks: int,
    log_block_chunk: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    retrieved_at = datetime.now(UTC).isoformat()
    store = base.EvidenceStore(data_root)
    issuer_rows = base.enrich_issuer_sources(issuer, store)
    rpc = base.EthereumRPC(rpc_url, store)
    chain_id = int(rpc.call("eth_chainId", [], key="ethereum:chain-id"), 16)
    if chain_id != base.CHAIN_ID:
        raise ValueError(f"expected Ethereum mainnet chain_id=1, received {chain_id}")
    finalized = rpc.call("eth_getBlockByNumber", ["finalized", False], key="ethereum:finalized-block")
    if not finalized or not finalized.get("hash"):
        raise ValueError("Ethereum finalized block unavailable")

    seed = base.load_json(chain_seed)
    chain_rows = extend_chain_history(seed, rpc, finalized)
    deployments = base.collect_deployment_snapshots(rpc, registry, finalized)
    mint_burn_events, mint_burn_summary = collect_mint_burn_window_chunked(
        rpc,
        finalized,
        mint_burn_blocks,
        log_block_chunk,
    )
    normalized = base.write_normalized(
        data_root,
        retrieved_at,
        issuer_rows,
        chain_rows,
        deployments,
        mint_burn_events,
        mint_burn_summary,
    )
    manifest = store.write_manifest(retrieved_at, rpc_url)
    return normalized, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=base.REGISTRY_PATH)
    parser.add_argument("--issuer", type=Path, default=base.ISSUER_PATH)
    parser.add_argument("--data-root", type=Path, default=base.DEFAULT_DATA_ROOT)
    parser.add_argument("--api-dir", type=Path, default=base.DEFAULT_API_DIR)
    parser.add_argument("--rpc-url", default=base.DEFAULT_RPC_URL)
    parser.add_argument("--chain-seed", type=Path, default=DEFAULT_CHAIN_SEED)
    parser.add_argument("--mint-burn-blocks", type=int, default=1000)
    parser.add_argument("--log-block-chunk", type=int, default=DEFAULT_LOG_BLOCK_CHUNK)
    args = parser.parse_args()

    registry = base.load_json(args.registry)
    issuer = base.load_json(args.issuer)
    base.validate_registry(registry)
    base.validate_issuer_observations(issuer)
    normalized, manifest = collect_incremental(
        registry,
        issuer,
        args.data_root,
        args.rpc_url,
        args.chain_seed,
        args.mint_burn_blocks,
        args.log_block_chunk,
    )
    index = base.build_api(registry, normalized, manifest, args.api_dir)
    print(json.dumps(index["coverage"], sort_keys=True))


if __name__ == "__main__":
    main()
