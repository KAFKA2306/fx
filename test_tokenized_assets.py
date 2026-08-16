import unittest

from tokenized_assets import TRANSFER_TOPIC, ZERO_TOPIC, normalize_log


def topic(address: str) -> str:
    return "0x" + "0" * 24 + address[2:].lower()


def log(sender: str, recipient: str, amount: int):
    return {
        "topics": [TRANSFER_TOPIC, sender, recipient],
        "data": hex(amount),
        "blockNumber": hex(100),
        "blockHash": "0xabc",
        "transactionHash": "0xdef",
        "logIndex": hex(1),
    }


class TransferNormalizationTests(unittest.TestCase):
    def test_mint_is_transfer_from_zero_address(self):
        recipient = topic("0x1111111111111111111111111111111111111111")
        row = normalize_log(log(ZERO_TOPIC, recipient, 1_000_000))
        self.assertEqual(row["event_type"], "mint")
        self.assertEqual(row["amount_usdc"], 1.0)


if __name__ == "__main__":
    unittest.main()
