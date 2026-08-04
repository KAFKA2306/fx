# fx — 為替相対価値分析システムの構想メモ

このリポジトリは、為替市場の相対価値（Relative Value、RV）分析、data収集、signal、risk管理、backtestを統合する構想として、2024年9月に作成した設計メモです。

**現在、README以外の実装fileはありません。** Python module、Docker Compose、Redis、TimescaleDB、TensorFlow model、data collector、trading engine、testは存在せず、取引systemは稼働していません。

> **状態:** design-only / 未実装  
> **作成時期:** 2024年9月  
> **live trading:** なし  
> **backtest結果:** なし  
> **現在の市場data正準候補:** [`KAFKA2306/investor`](https://github.com/KAFKA2306/investor)

---

## 想定していた目的

為替pair間のrelative valueを、同じ時点・同じdata source・同じcost前提で比較する構想です。

想定していた機能:

- FX rate、金利、inflation、economic indicator、newsの取得
- timestamp、timezone、単位の正規化
- correlation、cointegration、spread、z-scoreの分析
- mean reversionなどのsignal生成
- position sizing
- transaction costとslippageを含むbacktest
- live dataとhistorical dataの分離

これらは要件候補であり、実装済み機能ではありません。

---

## 旧READMEに記載されていたが存在しないもの

旧READMEは次を実装済みのように説明していました。

```text
data_collector/
data_processor/
analysis_engine/
trading_strategy/
risk_management/
backtest_engine/
Dockerfile
docker-compose.yml
main.py
.env.example
```

2026年8月4日のdefault branchには、これらを確認できません。

また、旧READMEのcode例は設計例であり、repositoryでimport・testできる実装ではありません。clone URLの`yourusername`もplaceholderでした。

---

## RV分析を実装する場合の最低条件

### data

- pairとvenue
- bid / ask / mid
- timestampとtimezone
- sampling interval
- sourceと取得時刻
- missing・duplicate・outlier処理
- 金利のtenorとcompounding
- macro dataの発表時点と改訂

future informationを過去時点へ混入しないpoint-in-time dataが必要です。

### model

- spread定義
- hedge ratioの推定期間
- cointegration test
- entry / exit rule
- stop condition
- parameter freeze
- rolling / expanding validation
- regime changeの扱い

### cost

- spread
- commission
- swap / funding
- slippage
- rollover
- market impact
- execution delay

costなしのmean reversion signalを運用可能性の証拠にしません。

### risk

- currency exposure
- leverage
- correlated positions
- liquidity
- drawdown
- gap risk
- broker / counterparty risk
- position limit

旧READMEの単純なposition size式だけでは、FX portfolio riskを表現できません。

---

## 実装先の推奨

新しく独立systemを作る前に、`investor`の金利・為替data基盤と研究runtimeへ統合できるか確認します。

```text
investor
  公式金利・為替data、point-in-time管理、研究・証拠
        │
        └─ FX RV strategy module候補

fx
  2024年の構想メモ
  現在は実装正準ではない
```

同じFRED、ECB、為替dataを複数repoで別々に保存しません。

---

## 現在の利用方法

設計文書の閲覧のみです。

```bash
git clone https://github.com/KAFKA2306/fx.git
cd fx
```

install、run、test、Docker起動commandはありません。

---

## セキュリティ

公開repositoryへ保存しないもの:

- broker API key
- account ID
- order・positionのprivate data
- paid market data
- News API key
- database password
- live trading credential

将来live executionを追加する場合、researchとexecutionをprocess・credential・permissionで分離します。AIや分析scriptから直接production orderを送信する構造を既定にしません。

---

## 既知の制約

- code、test、data、container設定がありません。
- API接続を検証していません。
- backtest結果はありません。
- model performance、risk、costを測定していません。
- live order機能はありません。
- 旧READMEにあるTensorFlow、Redis、TimescaleDB、Dockerは採用済みではありません。
- 本リポジトリは投資助言、売買推奨、将来収益の保証ではありません。

---

## 今後の判断

1. `investor`へ研究要件を統合する
2. data・model contractを定義してこのrepoでMVPを実装する
3. 構想メモとしてarchiveする

実装開始前に、source、point-in-time、cost、OOS、execution boundaryを明示します。

**README実体監査:** 2026年8月4日
