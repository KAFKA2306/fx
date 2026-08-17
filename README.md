# fx — tokenized asset observations

[![Test](https://github.com/KAFKA2306/fx/actions/workflows/test.yml/badge.svg)](https://github.com/KAFKA2306/fx/actions/workflows/test.yml)

This repository is being repurposed from an old FX design note into a small primary-source dataset for tokenized assets. The current implementation covers USDC issuer-reported circulation snapshots and an Ethereum USDC transfer-event collector.

## Current verified data

`data/official/` contains Circle-reported USDC circulation observations:

- 2026-07-06: 73.0 billion USDC — Circle MiCA USDC white paper
- 2026-07-23: 72.9 billion USDC — Circle USDC page
- 2026-07-27: 72.3 billion USDC — Circle USDC page

These are issuer-reported observations. They are not derived from Ethereum state and are not reconciled to chain supply in this repository yet.

Primary sources:

- https://www.circle.com/legal/mica-usdc-whitepaper
- https://www.circle.com/usdc
- https://developers.circle.com/stablecoins/usdc-contract-addresses

The Ethereum mainnet contract address stored with the snapshots is Circle's documented USDC address: `0xA0b86991c6218b36c1d19d4a2e9Eb0cE3606eB48`.

## Ethereum event collector

`tokenized_assets.py` requests ERC-20 `Transfer` logs for the Circle-documented Ethereum USDC contract and classifies transfers from the zero address as mint events and transfers to the zero address as burn events.

It requires an Ethereum JSON-RPC endpoint supplied through `ETH_RPC_URL`:

```bash
ETH_RPC_URL=https://your-endpoint.example \
python tokenized_assets.py --from-block 100 --to-block 200 --output output/usdc-events.json
```

The collector preserves block number, block hash, transaction hash, log index, sender, recipient, and raw token amount. Network collection is not required by the unit tests.

## Tests

The repository uses only the Python standard library for its current tests:

```bash
python -m unittest discover -v
```

The tests verify transfer classification and the stored issuer snapshots, including unique observation dates, positive circulation values, official Circle source URLs, and the Circle-documented Ethereum contract address.

## Current limitations

- The issuer snapshot history contains only three July 2026 observations, not the 90 days requested by Issue #4.
- Reserve composition and issuance/redemption flows are not yet stored as structured observations.
- The Ethereum collector is implemented, but this repository does not yet contain a maintained historical chain-event dataset.
- Issuer-reported circulation and chain-derived supply are intentionally kept separate.
- No stablecoin other than USDC is currently stored.
- There is no trading system, backtest, or investment recommendation in this repository.

Tracking issue: https://github.com/KAFKA2306/fx/issues/4