import json
import unittest
from pathlib import Path

from tokenized_assets import (
    reconciliation_rows,
    validate_issuer_observations,
    validate_registry,
)


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
