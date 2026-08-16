import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

from tokenized_assets import USDC


DATA_DIR = Path("data/official")
EXPECTED = {
    "2026-07-06": 73_000_000_000,
    "2026-07-23": 72_900_000_000,
    "2026-07-27": 72_300_000_000,
}


class IssuerSnapshotTests(unittest.TestCase):
    def test_usdc_snapshots_are_primary_source_observations(self):
        snapshots = []
        for path in sorted(DATA_DIR.glob("usdc-*.json")):
            snapshots.append(json.loads(path.read_text(encoding="utf-8")))

        self.assertGreaterEqual(len(snapshots), len(EXPECTED))
        dates = [row["as_of"] for row in snapshots]
        self.assertEqual(len(dates), len(set(dates)))

        by_date = {row["as_of"]: row for row in snapshots}
        for as_of, expected_supply in EXPECTED.items():
            row = by_date[as_of]
            self.assertEqual(row["schema_version"], 1)
            self.assertEqual(row["asset"], "USDC")
            self.assertEqual(row["issuer"], "Circle")
            self.assertEqual(row["circulation_usdc"], expected_supply)
            self.assertGreater(row["circulation_usdc"], 0)
            self.assertEqual(row["ethereum_contract_address"].lower(), USDC.lower())
            self.assertTrue(row["sources"])
            for source in row["sources"]:
                parsed = urlparse(source)
                self.assertEqual(parsed.scheme, "https")
                self.assertIn(parsed.hostname, {"www.circle.com", "developers.circle.com"})


if __name__ == "__main__":
    unittest.main()
