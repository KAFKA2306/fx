# Tokenized Assets Primary Evidence

[![Tokenized assets evidence](https://github.com/KAFKA2306/fx/actions/workflows/tokenized-assets.yml/badge.svg)](https://github.com/KAFKA2306/fx/actions/workflows/tokenized-assets.yml)

Tokenized assetを**発行体の一次開示・法的asset identity・Ethereum上のtoken deployment・block-level evidence**へ分離し、raw evidenceから再生成可能なdatasetとして保存します。旧FX signal/backtestではなく、`api/v1/tokenized-assets/` が正準成果物です。

## 正準data

- [dataset index](api/v1/tokenized-assets/index.json)
- [asset / deployment registry](api/v1/tokenized-assets/registry.json)
- [USDC issuer observations](api/v1/tokenized-assets/issuer.json)
- [USDC Ethereum weekly supply](api/v1/tokenized-assets/chain-weekly.json)
- [current deployment snapshots](api/v1/tokenized-assets/deployments.json)
- [USDC mint / burn evidence](api/v1/tokenized-assets/mint-burn.json)
- [SEC filing ledger](api/v1/tokenized-assets/filings.json)
- [issuer ↔ chain reconciliation](api/v1/tokenized-assets/reconciliation.json)
- [raw provenance manifest](api/v1/tokenized-assets/provenance.json)

`Tokenized assets evidence` workflowが毎日一次情報を取得し、raw response / issuer documentをSHA-256で固定した後、同じevidenceからAPIを生成します。CIでは保存済みevidenceだけでoffline再生成し、live生成物との差分がないことを検証します。

## USDC: issuer factとchain factを混ぜない

Circle reserve reportのissuer observationでは、all approved blockchainsを対象とするUSDC circulationとreserve fair valueを別fieldで保持します。

Ethereum側ではCircleが公開するnative USDC contractについて、finalized Ethereum blockを基準に週次`totalSupply()`を観測します。各recordは最低限次を持ちます。

```text
chain_id
block_number
block_hash
contract_address
observed_at
total_supply_raw
decimals
total_supply
```

issuer-reported all-chain circulationとEthereum native `totalSupply()`はscopeが異なるため、同じ値として補正しません。`reconciliation.json`には観測差をそのまま残し、`correction_applied: false`を固定します。

## Mint / burn

USDCのsupply-changing eventだけをEthereum `Transfer` logから抽出します。

- `from == 0x0` → mint
- `to == 0x0` → burn
- 通常のpeer-to-peer transfer → supplyを変えないため正準event ledgerには保存しない

各eventはblock number/hash、transaction hash、log indexを保持します。RPC providerはtransportであり、provenance authorityはEthereumのchain IDとblock hashです。

## Tokenized funds

stablecoin以外もlegal assetとtoken deploymentを分けて登録します。

### BUIDL

BlackRock USD Institutional Digital Liquidity Fund Ltd.をlegal assetとして保持し、SEC filing identityとBlackRockが公開するEthereum contractを別recordにします。BlackRockが公式に列挙する複数contractは暗黙に1件へ統合しません。

### OUSG

Ondo Short-Term US Government Treasuries Fund (OUSG)をlegal assetとして保持し、SEC filing identity、issuer documentation、Ethereum contract deploymentを分離します。

## Data contract

```text
issuer / SEC / official contract source
  ↓
raw evidence + SHA-256
  ↓
normalized issuer / chain / deployment / mint-burn records
  ↓
api/v1/tokenized-assets/*.json|csv
```

fail-closed条件:

- Ethereum mainnet以外のchain ID
- official registry contractにcodeがない
- ERC-20 `decimals()` / `totalSupply()`が取得不能
- raw evidence hash不一致
- USDC issuer historyが90日未満
- chain historyが90日未満
- legal asset / token deployment identityの重複・欠落

## 実行

標準ライブラリのみです。デフォルトRPCは公開Ethereum transportを使いますが、別transportを使う場合も同じmainnet/block provenance contractを満たす必要があります。

```bash
python tokenized_assets.py
```

保存済みraw/normalized evidenceからAPIを再生成:

```bash
python tokenized_assets.py --offline
```

テスト:

```bash
python -m unittest discover -v
```

## Scope

このrepositoryの正準責務はtokenized asset evidenceです。旧FX設計メモ、signal、backtest、trading recommendationは正準datasetではありません。投資助言・売買signalを提供しません。

Tracking issue: https://github.com/KAFKA2306/fx/issues/4
