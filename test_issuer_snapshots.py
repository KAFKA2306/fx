import hashlib
import json
import unittest
from datetime import UTC, datetime
from pathlib import Path

from tokenized_assets import (
    reconciliation_rows,
    validate_issuer_observations,
    validate_registry,
)
from tokenized_assets_incremental import collect_logs_chunked, extend_chain_history


class FakeRPC:
    def __init__(self, total_supply_raw: int):
        self.total_supply_raw = total_supply_raw
        self.calls = []

    def call(self, method, params, key=None):
        self.calls.append((method, params, key))
        if method != "eth_call":
            raise AssertionError(f"unexpected method: {method}")
        return hex(self.total_supply_raw)


class FakeLogRPC:
    def __init__(self):
        self.calls = []

    def call(self, method, params, key=None):
        self.calls.append((method, params, key))
        if method != "eth_getLogs":
            raise AssertionError(f"unexpected method: {method}")
        return []


class IssuerSnapshotTests(unittest.TestCase):
    def test_usdc_issuer_evidence_spans_ninety_days_with_reserves(self):
        payload = json.loads(Path("data/issuer-observations.json").read_text())
        validate_issuer_observations(payload)
        rows = payload["observations"]
        self.assertEqual(rows[0]["as_of"], "2026-03-11")
        self.assertEqual(rows[-1]["as_of"], "2026-06-30")
        self.assertTrue(all(row["circulation_usdc"] > 0 for row in rows))
        self.assertTrue(all(row["reserve_fair_value_usd"] >= row["circulation_usdc"] for row in rows))
        self.assertTrue(all("hubspotusercontent-na1.net" in row["source_url"] for row in rows))

    def test_published_issuer_records_bind_to_raw_sha256(self):
        rows = json.loads(Path("api/v1/tokenized-assets/issuer.json").read_text())["records"]
        data_root = Path("data/tokenized-assets")
        self.assertGreaterEqual(len(rows), 8)
        for row in rows:
            evidence_path = Path(row["source_evidence"])
            self.assertEqual(evidence_path.parts[:2], ("raw", "objects"))
            self.assertEqual(len(row["source_sha256"]), 64)
            self.assertTrue(row["source_url"].startswith("https://"))
            raw = (data_root / evidence_path).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row["source_sha256"])

    def test_incremental_chain_history_uses_only_finalized_state(self):
        seed = {
            "records": [
                {
                    "observed_at": "2026-05-01T00:00:00+00:00",
                    "block_number": 100,
                },
                {
                    "observed_at": "2026-08-01T00:00:00+00:00",
                    "block_number": 200,
                },
            ]
        }
        final_time = int(datetime(2026, 8, 10, tzinfo=UTC).timestamp())
        finalized = {"number": hex(300), "timestamp": hex(final_time), "hash": "0xfinal"}
        rpc = FakeRPC(50_000_000 * 1_000_000)
        rows = extend_chain_history(seed, rpc, finalized)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["block_number"], 300)
        self.assertEqual(rows[-1]["block_hash"], "0xfinal")
        self.assertEqual(rows[-1]["total_supply"], 50_000_000)
        self.assertEqual(len(rpc.calls), 1)
        method, params, _ = rpc.calls[0]
        self.assertEqual(method, "eth_call")
        self.assertEqual(params[1], hex(300))

    def test_incremental_chain_history_does_not_oversample(self):
        seed = {
            "records": [
                {
                    "observed_at": "2026-05-01T00:00:00+00:00",
                    "block_number": 100,
                },
                {
                    "observed_at": "2026-08-18T20:38:47+00:00",
                    "block_number": 200,
                },
            ]
        }
        final_time = int(datetime(2026, 8, 20, tzinfo=UTC).timestamp())
        finalized = {"number": hex(300), "timestamp": hex(final_time), "hash": "0xfinal"}
        rpc = FakeRPC(1)
        rows = extend_chain_history(seed, rpc, finalized)
        self.assertEqual(rows, seed["records"])
        self.assertEqual(rpc.calls, [])

    def test_log_collection_respects_fifty_block_limit(self):
        rpc = FakeLogRPC()
        rows = collect_logs_chunked(
            rpc,
            100,
            219,
            ["0xtopic"],
            "test",
            block_chunk=50,
        )
        self.assertEqual(rows, [])
        ranges = [(int(call[1][0]["fromBlock"], 16), int(call[1][0]["toBlock"], 16)) for call in rpc.calls]
        self.assertEqual(ranges, [(100, 149), (150, 199), (200, 219)])
        self.assertTrue(all(end - start + 1 <= 50 for start, end in ranges))

    def test_registry_separates_legal_assets_and_token_deployments(self):
        registry = json.loads(Path("data/registry.json").read_text())
        validate_registry(registry)
        assets = {row["asset_id"]: row for row in registry["assets"]}
        self.assertEqual(assets["buidl"]["legal_asset"]["cik"], "0002013810")
        self.assertEqual(assets["ousg"]["legal_asset"]["cik"], "0001957431")
        self.assertEqual(len(assets["buidl"]["token_deployments"]), 2)
        self.assertNotEqual(
            assets["buidl"]["token_deployments"][0]["deployment_id"],
            assets["buidl"]["token_deployments"][1]["deployment_id"],
        )

    def test_reconciliation_preserves_scope_difference(self):
        issuer = [{"as_of": "2026-05-01", "circulation_usdc": 100.0}]
        chain = [
            {
                "observed_at": "2026-05-01T00:00:00+00:00",
                "block_number": 123,
                "block_hash": "0xabc",
                "total_supply": 60.0,
            }
        ]
        rows = reconciliation_rows(issuer, chain)
        self.assertEqual(rows[0]["issuer_all_chain_minus_ethereum_native_usdc"], 40.0)
        self.assertFalse(rows[0]["correction_applied"])
        self.assertIn("not_like_for_like", rows[0]["comparison_scope"])


if __name__ == "__main__":
    unittest.main()
