# RVトレーディングシステム：データ収集、処理、および取引戦略

## 概要

このプロジェクトは、無料のAPIを利用して為替市場の相対価値（RV）トレーディングに必要なデータを収集し、分析し、取引戦略を実行するシステムです。主に以下の機能を提供します：

1. データ収集：複数の無料APIから為替レート、経済指標、ニュースを取得
2. データ処理：収集したデータの整理、標準化、指標の計算
3. 取引戦略：RV分析に基づく取引シグナルの生成
4. リスク管理：適切な取引サイズの決定とリスク制御
5. バックテスト：過去のデータを使用した戦略の性能評価

## 使用技術

- プログラミング言語：Python 3.9+
- データベース：
  - Redis：短期データの高速アクセス用
  - TimescaleDB：長期データの保存と分析用
- データ分析：pandas, numpy, scikit-learn
- 機械学習：TensorFlow/Keras（基本的な予測モデル用）
- 開発環境：Docker, Docker Compose

## データソース

以下の無料APIを利用してデータを収集します：

1. Alpha Vantage API：主要な為替レートと経済指標
2. European Central Bank (ECB) API：ユーロ圏の経済データ
3. Federal Reserve Economic Data (FRED) API：米国の経済指標
4. NewsAPI：金融関連ニュース

## システムの主要部分

1. データ収集部（`data_collector/`）
   - 各APIからデータを定期的に取得
   - 取得したデータの整合性チェック

2. データ処理部（`data_processor/`）
   - データのクリーニングと標準化
   - 技術的指標（移動平均、RSIなど）の計算
   - 経済指標の正規化

3. 分析エンジン（`analysis_engine/`）
   - 統計的分析（相関、共和分など）
   - 機械学習モデルによる予測

4. 取引戦略実行部（`trading_strategy/`）
   - RV分析に基づく取引シグナルの生成
   - ポジションの管理

5. リスク管理モジュール（`risk_management/`）
   - ポジションサイズの計算
   - ストップロスとテイクプロフィットの設定

6. バックテストエンジン（`backtest_engine/`）
   - 過去のデータを使用した戦略のシミュレーション
   - パフォーマンス指標の計算

## 主要な処理の例

### データ処理：移動平均乖離率（MACD）の計算

```python
import pandas as pd

def calculate_macd(price_data, short_window=12, long_window=26, signal_window=9):
    short_ema = price_data.ewm(span=short_window, adjust=False).mean()
    long_ema = price_data.ewm(span=long_window, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    return pd.DataFrame({'MACD': macd, 'Signal': signal})

# 使用例
df = pd.DataFrame({'close': [価格データ]})
df[['MACD', 'Signal']] = calculate_macd(df['close'])
```

### 取引戦略：単純な平均回帰戦略

```python
import numpy as np

def mean_reversion_signal(price, window=20, std_dev=2):
    rolling_mean = price.rolling(window=window).mean()
    rolling_std = price.rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * std_dev)
    lower_band = rolling_mean - (rolling_std * std_dev)
    
    signal = np.where(price > upper_band, -1,  # 売りシグナル
                      np.where(price < lower_band, 1,  # 買いシグナル
                               0))  # シグナルなし
    return signal

# 使用例
df['Signal'] = mean_reversion_signal(df['close'])
```

### リスク管理：ポジションサイズの計算

```python
def calculate_position_size(account_balance, risk_per_trade, stop_loss_pips, pip_value):
    risk_amount = account_balance * risk_per_trade
    position_size = risk_amount / (stop_loss_pips * pip_value)
    return position_size

# 使用例
account_balance = 10000  # 口座残高 $10,000
risk_per_trade = 0.02  # 1取引あたりのリスク 2%
stop_loss_pips = 50  # ストップロス 50 pips
pip_value = 0.0001  # 1pipの価値（多くの通貨ペアで）

size = calculate_position_size(account_balance, risk_per_trade, stop_loss_pips, pip_value)
print(f"取引サイズ: {size:.2f} ユニット")
```

## システムの使用方法

1. リポジトリをクローン：
   ```
   git clone https://github.com/yourusername/rv-trading-system.git
   cd rv-trading-system
   ```

2. 環境設定：
   ```
   cp .env.example .env
   # .envファイルを編集し、必要なAPI鍵を設定
   ```

3. Dockerでサービスを起動：
   ```
   docker-compose up -d
   ```

4. システムを実行：
   ```
   docker-compose exec trading_system python main.py
   ```

## 注意事項

- このシステムは教育および研究目的で提供されています。
- 実際の取引に使用する場合は、十分なテストと専門家のアドバイスを得てください。
- 金融市場での取引には高いリスクが伴います。自己責任で行ってください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
