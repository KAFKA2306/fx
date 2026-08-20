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


def collect_incremental(
    registry: dict[str, Any],
    issuer: dict[str, Any],
    data_root: Path,
    rpc_url: str,
    chain_seed: Path,
    mint_burn_blocks: int,
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
    mint_burn_events, mint_burn_summary = base.collect_mint_burn_window(rpc, finalized, mint_burn_blocks)
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
    )
    index = base.build_api(registry, normalized, manifest, args.api_dir)
    print(json.dumps(index["coverage"], sort_keys=True))


if __name__ == "__main__":
    main()
