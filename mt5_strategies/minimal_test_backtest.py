"""
Minimal Test Backtester - Simple Entry Conditions
Tests if ANY trades can be generated with basic logic
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class MinimalTestBacktester:
    def __init__(self, symbol="GC=F", interval="5m", period="3mo"):
        self.symbol = symbol
        self.interval = interval
        self.period = period
        self.data = None
        self.trades = []

    def fetch_data(self):
        """Fetch historical data"""
        print(f"Fetching {self.symbol} data ({self.interval}, {self.period})...")

        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m',
            '1h': '1h', '4h': '1h', '1d': '1d'
        }

        yf_interval = interval_map.get(self.interval, '5m')
        ticker = yf.Ticker(self.symbol)
        self.data = ticker.history(period=self.period, interval=yf_interval)

        if self.data.empty:
            raise ValueError(f"No data found for {self.symbol}")

        if self.interval == '4h':
            self.data = self.data.resample('4h').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
            }).dropna()

        self.data = self.data.reset_index()
        self.data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']

        print(f"Loaded {len(self.data)} candles")
        print(f"Date range: {self.data['datetime'].min()} to {self.data['datetime'].max()}")
        print(f"Price range: {self.data['low'].min():.2f} to {self.data['high'].max():.2f}")

    def test_basic_conditions(self):
        """Test basic market conditions"""
        print("\n" + "="*70)
        print("BASIC MARKET CONDITIONS")
        print("="*70)

        df = self.data.copy()

        # Calculate basic indicators
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['rsi'] = self.calculate_rsi(df['close'], 14)
        df['atr'] = self.calculate_atr(df, 14)

        # Check EMA alignment
        price_above_ema9 = (df['close'] > df['ema_9']).sum()
        price_above_ema21 = (df['close'] > df['ema_21']).sum()
        ema9_above_ema21 = (df['ema_9'] > df['ema_21']).sum()

        print(f"\n📊 EMA ANALYSIS:")
        print(f"  Price above EMA 9: {price_above_ema9}/{len(df)} ({price_above_ema9/len(df)*100:.1f}%)")
        print(f"  Price above EMA 21: {price_above_ema21}/{len(df)} ({price_above_ema21/len(df)*100:.1f}%)")
        print(f"  EMA 9 above EMA 21: {ema9_above_ema21}/{len(df)} ({ema9_above_ema21/len(df)*100:.1f}%)")

        # Check RSI
        rsi_oversold = (df['rsi'] < 30).sum()
        rsi_overbought = (df['rsi'] > 70).sum()
        rsi_neutral = ((df['rsi'] >= 30) & (df['rsi'] <= 70)).sum()

        print(f"\n📊 RSI ANALYSIS:")
        print(f"  RSI < 30 (oversold): {rsi_oversold}/{len(df)} ({rsi_oversold/len(df)*100:.1f}%)")
        print(f"  RSI > 70 (overbought): {rsi_overbought}/{len(df)} ({rsi_overbought/len(df)*100:.1f}%)")
        print(f"  RSI 30-70 (neutral): {rsi_neutral}/{len(df)} ({rsi_neutral/len(df)*100:.1f}%)")

        # Check ATR
        avg_atr = df['atr'].mean()
        print(f"\n📊 ATR ANALYSIS:")
        print(f"  Average ATR: {avg_atr:.2f}")
        print(f"  ATR range: {df['atr'].min():.2f} to {df['atr'].max():.2f}")

        # Check candle patterns
        df['bullish_engulfing'] = (
            (df['close'].shift(1) < df['open'].shift(1)) &
            (df['close'] > df['open']) &
            (df['close'] > df['open'].shift(1)) &
            (df['open'] < df['close'].shift(1))
        )

        df['bearish_engulfing'] = (
            (df['close'].shift(1) > df['open'].shift(1)) &
            (df['close'] < df['open']) &
            (df['close'] < df['open'].shift(1)) &
            (df['open'] > df['close'].shift(1))
        )

        bullish_engulfing_count = df['bullish_engulfing'].sum()
        bearish_engulfing_count = df['bearish_engulfing'].sum()

        print(f"\n📊 CANDLE PATTERNS:")
        print(f"  Bullish Engulfing: {bullish_engulfing_count}/{len(df)} ({bullish_engulfing_count/len(df)*100:.1f}%)")
        print(f"  Bearish Engulfing: {bearish_engulfing_count}/{len(df)} ({bearish_engulfing_count/len(df)*100:.1f}%)")

        return df

    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_atr(self, df, period=14):
        """Calculate ATR"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def test_simple_strategies(self, df):
        """Test very simple strategies"""
        print("\n" + "="*70)
        print("TESTING SIMPLE STRATEGIES")
        print("="*70)

        # Strategy 1: Simple EMA Crossover
        print("\n📈 STRATEGY 1: Simple EMA Crossover")
        df['ema_cross_up'] = (df['ema_9'] > df['ema_21']) & (df['ema_9'].shift(1) <= df['ema_21'].shift(1))
        df['ema_cross_down'] = (df['ema_9'] < df['ema_21']) & (df['ema_9'].shift(1) >= df['ema_21'].shift(1))

        cross_up_count = df['ema_cross_up'].sum()
        cross_down_count = df['ema_cross_down'].sum()

        print(f"  EMA Cross Up signals: {cross_up_count}")
        print(f"  EMA Cross Down signals: {cross_down_count}")

        # Strategy 2: RSI + EMA
        print("\n📈 STRATEGY 2: RSI + EMA")
        df['rsi_ema_buy'] = (df['rsi'] < 40) & (df['close'] > df['ema_9'])
        df['rsi_ema_sell'] = (df['rsi'] > 60) & (df['close'] < df['ema_9'])

        rsi_ema_buy_count = df['rsi_ema_buy'].sum()
        rsi_ema_sell_count = df['rsi_ema_sell'].sum()

        print(f"  RSI < 40 + Price > EMA 9: {rsi_ema_buy_count}")
        print(f"  RSI > 60 + Price < EMA 9: {rsi_ema_sell_count}")

        # Strategy 3: Engulfing + Trend
        print("\n📈 STRATEGY 3: Engulfing + Trend")
        df['engulf_buy'] = df['bullish_engulfing'] & (df['close'] > df['ema_21'])
        df['engulf_sell'] = df['bearish_engulfing'] & (df['close'] < df['ema_21'])

        engulf_buy_count = df['engulf_buy'].sum()
        engulf_sell_count = df['engulf_sell'].sum()

        print(f"  Bullish Engulfing + Price > EMA 21: {engulf_buy_count}")
        print(f"  Bearish Engulfing + Price < EMA 21: {engulf_sell_count}")

        # Strategy 4: ANY price movement (extreme test)
        print("\n📈 STRATEGY 4: ANY Price Movement (Extreme Test)")
        df['any_up'] = df['close'] > df['close'].shift(1)
        df['any_down'] = df['close'] < df['close'].shift(1)

        any_up_count = df['any_up'].sum()
        any_down_count = df['any_down'].sum()

        print(f"  ANY up candle: {any_up_count}")
        print(f"  ANY down candle: {any_down_count}")

        return df

    def run_simple_backtest(self, df):
        """Run a very simple backtest"""
        print("\n" + "="*70)
        print("RUNNING SIMPLE BACKTEST")
        print("="*70)

        balance = 10000
        position = 0
        entry_price = 0
        trade_count = 0
        winning_trades = 0
        losing_trades = 0

        # Use simplest possible strategy: Buy when green candle, Sell when red
        print("\nStrategy: Buy on green candle, Sell on red candle")
        print("Risk: 1% per trade, SL: 20 pips, TP: 40 pips")

        for i in range(1, len(df)):
            row = df.iloc[i]
            current_price = row['close']

            # Exit conditions
            if position != 0:
                sl = entry_price - 0.20  # 20 pips SL
                tp = entry_price + 0.40  # 40 pips TP

                if position > 0:  # Long
                    if current_price <= sl or current_price >= tp:
                        pnl = (current_price - entry_price) * position
                        balance += pnl

                        if pnl > 0:
                            winning_trades += 1
                        else:
                            losing_trades += 1

                        trade_count += 1
                        position = 0
                        entry_price = 0

            # Entry conditions
            if position == 0:
                # Simple: Buy if green candle
                if row['close'] > row['open']:
                    # Calculate position size (1% risk)
                    risk_amount = balance * 0.01
                    sl_distance = 0.20
                    position_size = risk_amount / sl_distance

                    position = position_size
                    entry_price = current_price

        # Close any remaining position
        if position != 0:
            current_price = df.iloc[-1]['close']
            pnl = (current_price - entry_price) * position
            balance += pnl

            if pnl > 0:
                winning_trades += 1
            else:
                losing_trades += 1
            trade_count += 1

        total_return = (balance - 10000) / 10000 * 100
        win_rate = (winning_trades / trade_count * 100) if trade_count > 0 else 0

        print(f"\n📊 RESULTS:")
        print(f"  Initial Balance: $10,000")
        print(f"  Final Balance: ${balance:.2f}")
        print(f"  Total Return: {total_return:+.2f}%")
        print(f"  Total Trades: {trade_count}")
        print(f"  Winning Trades: {winning_trades}")
        print(f"  Losing Trades: {losing_trades}")
        print(f"  Win Rate: {win_rate:.2f}%")

        return {
            'total_trades': trade_count,
            'win_rate': win_rate,
            'total_return': total_return
        }

    def analyze_session_distribution(self, df):
        """Analyze trading by session"""
        print("\n" + "="*70)
        print("SESSION DISTRIBUTION")
        print("="*70)

        df['hour'] = pd.to_datetime(df['datetime']).dt.hour

        # Define sessions (GMT)
        asian = df[(df['hour'] >= 0) & (df['hour'] < 8)]
        london = df[(df['hour'] >= 8) & (df['hour'] < 16)]
        newyork = df[(df['hour'] >= 13) & (df['hour'] < 21)]
        overlap = df[(df['hour'] >= 13) & (df['hour'] < 16)]

        print(f"\n📊 CANDLE COUNT BY SESSION:")
        print(f"  Asian (00:00-08:00 GMT): {len(asian)} candles")
        print(f"  London (08:00-16:00 GMT): {len(london)} candles")
        print(f"  New York (13:00-21:00 GMT): {len(newyork)} candles")
        print(f"  Overlap (13:00-16:00 GMT): {len(overlap)} candles")

        # Calculate volatility by session
        print(f"\n📊 AVERAGE ATR BY SESSION:")
        if len(asian) > 0:
            asian_atr = self.calculate_atr(asian, 14).mean()
            print(f"  Asian: {asian_atr:.2f}")
        if len(london) > 0:
            london_atr = self.calculate_atr(london, 14).mean()
            print(f"  London: {london_atr:.2f}")
        if len(newyork) > 0:
            ny_atr = self.calculate_atr(newyork, 14).mean()
            print(f"  New York: {ny_atr:.2f}")
        if len(overlap) > 0:
            overlap_atr = self.calculate_atr(overlap, 14).mean()
            print(f"  Overlap: {overlap_atr:.2f}")

def main():
    print("="*70)
    print("MINIMAL TEST BACKTESTER")
    print("="*70)

    symbol = input("Enter symbol (default: GC=F): ") or "GC=F"
    interval = input("Enter timeframe (default: 5m): ") or "5m"
    period = input("Enter period (default: 3mo): ") or "3mo"

    bt = MinimalTestBacktester(symbol=symbol, interval=interval, period=period)

    try:
        # Fetch data
        bt.fetch_data()

        # Test basic conditions
        df = bt.test_basic_conditions()

        # Test simple strategies
        df = bt.test_simple_strategies(df)

        # Analyze session distribution
        bt.analyze_session_distribution(df)

        # Run simple backtest
        results = bt.run_simple_backtest(df)

        print("\n" + "="*70)
        print("DIAGNOSIS")
        print("="*70)

        if results['total_trades'] == 0:
            print("❌ NO TRADES GENERATED")
            print("\nPossible issues:")
            print("1. Data quality problems")
            print("2. Price range too small for SL/TP")
            print("3. Market conditions not suitable")
            print("\nRecommendations:")
            print("- Try different timeframe (15m or 1h)")
            print("- Try different period (6mo or 1y)")
            print("- Try different symbol")
        else:
            print("✅ TRADES GENERATED")
            print(f"Strategy is working! Generated {results['total_trades']} trades.")
            print("\nIf original strategy still has 0 trades:")
            print("- The signal scoring is too strict")
            print("- Try lowering Min_Signal_Score further")
            print("- Try disabling some filters")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
