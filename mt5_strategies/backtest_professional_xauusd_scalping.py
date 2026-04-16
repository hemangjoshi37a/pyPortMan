"""
Professional XAU/USD Scalping Backtester
Backtests the Professional XAU/USD Scalping Strategy using Python
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class XAUUSDScalpingBacktester:
    def __init__(self, symbol="GC=F", interval="5m", period="3mo"):
        """
        Initialize XAU/USD Scalping Backtester

        Args:
            symbol: Trading pair (default: GC=F for Gold Futures)
            interval: Timeframe ("5m", "15m", "1h", "4h", "1d")
            period: Data period ("1mo", "3mo", "6mo", "1y", "2y")
        """
        self.symbol = symbol
        self.interval = interval
        self.period = period
        self.data = None
        self.trades = []
        self.equity_curve = []

        # Scalping Strategy Parameters (matching MT5 EA)
        self.params = {
            # Timeframes
            'primary_tf': '4h',
            'intermediate_tf': '1h',
            'entry_tf': '15m',
            'precision_tf': '5m',

            # EMA Settings (Faster for scalping)
            'ema_fast': 9,
            'ema_slow': 21,
            'ema_trend': 50,

            # ADX Settings
            'adx_period': 14,
            'adx_threshold': 25,

            # RSI Settings
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,

            # SMC Settings
            'swing_lookback': 3,
            'fvg_min_size': 5,
            'ob_lookback': 10,

            # Entry Settings
            'min_signal_score': 45,

            # Risk Management (Conservative)
            'risk_percent': 0.75,
            'atr_multiplier': 1.5,
            'sl_buffer_pips': 5,
            'risk_reward_ratio': 1.5,

            # Partial TP Settings
            'tp1_percent': 40,
            'tp2_percent': 30,
            'tp3_percent': 20,
            'tp4_percent': 10,

            # Session Settings
            'trade_asian': False,
            'trade_london': True,
            'trade_newyork': True,
            'trade_overlap': True,

            # Other Settings
            'max_positions': 2,
            'max_spread': 30,
            'max_trades_per_hour': 3,
            'min_candles_between': 3,

            # Commission
            'commission': 0.0002,  # 0.02% per trade
            'initial_balance': 10000
        }

    def fetch_data(self):
        """Fetch historical data from Yahoo Finance"""
        print(f"Fetching {self.symbol} data ({self.interval}, {self.period})...")

        # Map interval to yfinance format
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '1h',  # Will resample later
            '1d': '1d'
        }

        yf_interval = interval_map.get(self.interval, '5m')

        # Fetch data
        ticker = yf.Ticker(self.symbol)
        self.data = ticker.history(period=self.period, interval=yf_interval)

        if self.data.empty:
            raise ValueError(f"No data found for {self.symbol}")

        # Resample if needed
        if self.interval == '4h':
            self.data = self.data.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        # Reset index
        self.data = self.data.reset_index()

        # Rename columns
        self.data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']

        print(f"Loaded {len(self.data)} candles")

    def calculate_indicators(self):
        """Calculate all indicators used in the scalping strategy"""
        df = self.data.copy()

        # EMA
        df['ema_fast'] = df['close'].ewm(span=self.params['ema_fast']).mean()
        df['ema_slow'] = df['close'].ewm(span=self.params['ema_slow']).mean()
        df['ema_trend'] = df['close'].ewm(span=self.params['ema_trend']).mean()

        # EMA Crossover
        df['ema_cross_up'] = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
        df['ema_cross_down'] = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.params['rsi_period']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()

        # ADX
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        atr = tr.rolling(window=self.params['adx_period']).mean()

        plus_di = 100 * (pd.Series(plus_dm).rolling(window=self.params['adx_period']).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=self.params['adx_period']).mean() / atr)

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=self.params['adx_period']).mean()

        # Market Structure
        df['swing_high'] = df['high'].rolling(window=self.params['swing_lookback']*2+1, center=True).max() == df['high']
        df['swing_low'] = df['low'].rolling(window=self.params['swing_lookback']*2+1, center=True).min() == df['low']

        # Trend
        df['trend_up'] = (df['ema_fast'] > df['ema_slow']) & (df['close'] > df['ema_trend'])
        df['trend_down'] = (df['ema_fast'] < df['ema_slow']) & (df['close'] < df['ema_trend'])

        # Candlestick Patterns
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

        # Pinbar
        body = np.abs(df['close'] - df['open'])
        upper_wick = df['high'] - np.maximum(df['open'], df['close'])
        lower_wick = np.minimum(df['open'], df['close']) - df['low']
        total_range = df['high'] - df['low']

        df['bullish_pinbar'] = (
            (df['close'] > df['open']) &
            (lower_wick > body * 2) &
            (upper_wick < body * 0.5)
        )

        df['bearish_pinbar'] = (
            (df['close'] < df['open']) &
            (upper_wick > body * 2) &
            (lower_wick < body * 0.5)
        )

        # Session (GMT)
        df['hour'] = pd.to_datetime(df['datetime']).dt.hour
        df['session'] = df['hour'].apply(self.get_session)

        self.data = df
        print("Indicators calculated")

    def get_session(self, hour):
        """Get trading session based on hour (GMT)"""
        if 13 <= hour < 16:
            return 'overlap'
        elif 8 <= hour < 16:
            return 'london'
        elif 13 <= hour < 21:
            return 'newyork'
        elif 0 <= hour < 8:
            return 'asian'
        else:
            return 'off_hours'

    def calculate_signal_score(self, row, direction='buy'):
        """Calculate signal score matching MT5 EA logic"""
        score = 0

        # 1. Trend Alignment (20 points)
        if direction == 'buy':
            if row['trend_up']:
                score += 10
            if row['ema_cross_up']:
                score += 10
        else:
            if row['trend_down']:
                score += 10
            if row['ema_cross_down']:
                score += 10

        # 2. Market Structure (15 points)
        # Simplified: use recent swing points
        if direction == 'buy':
            if row['close'] > row['ema_trend']:
                score += 8
            if row['close'] > row['ema_slow']:
                score += 7
        else:
            if row['close'] < row['ema_trend']:
                score += 8
            if row['close'] < row['ema_slow']:
                score += 7

        # 3. ADX Strength (10 points)
        if row['adx'] > self.params['adx_threshold']:
            score += 10
            if row['adx'] > 40:
                score += 2

        # 4. RSI Condition (10 points)
        if direction == 'buy':
            if row['rsi'] < 70 and row['rsi'] > 30:
                score += 5
            if row['rsi'] < 50:
                score += 5
        else:
            if row['rsi'] > 30 and row['rsi'] < 70:
                score += 5
            if row['rsi'] > 50:
                score += 5

        # 5. Candlestick Patterns (10 points)
        if direction == 'buy':
            if row['bullish_engulfing']:
                score += 6
            if row['bullish_pinbar']:
                score += 6
        else:
            if row['bearish_engulfing']:
                score += 6
            if row['bearish_pinbar']:
                score += 6

        # 6. Session Favorable (5 points)
        session = row['session']
        if session == 'overlap':
            score += 5
        elif session in ['london', 'newyork']:
            score += 3

        return score

    def run_backtest(self):
        """Run the backtest"""
        print("Running backtest...")

        balance = self.params['initial_balance']
        position = 0  # 0 = none, positive = long, negative = short
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        trade_count = 0
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0
        max_drawdown = 0
        peak_balance = balance

        self.equity_curve = [balance]

        # Track trades per hour
        trades_per_hour = {}
        last_trade_index = -self.params['min_candles_between']

        for i in range(50, len(self.data)):  # Skip first 50 bars for indicator warmup
            row = self.data.iloc[i]
            current_price = row['close']

            # Check session filter
            if not self.is_session_allowed(row['session']):
                continue

            # Check exit conditions
            if position != 0:
                # Check SL/TP
                if position > 0:  # Long
                    if current_price <= stop_loss or current_price >= take_profit:
                        # Exit long
                        pnl = (current_price - entry_price) * position
                        commission = abs(position) * current_price * self.params['commission']
                        balance += pnl - commission

                        if pnl > 0:
                            winning_trades += 1
                            total_profit += pnl
                        else:
                            losing_trades += 1
                            total_loss += abs(pnl)

                        trade_count += 1
                        position = 0
                        entry_price = 0
                        stop_loss = 0
                        take_profit = 0

                elif position < 0:  # Short
                    if current_price >= stop_loss or current_price <= take_profit:
                        # Exit short
                        pnl = (entry_price - current_price) * abs(position)
                        commission = abs(position) * current_price * self.params['commission']
                        balance += pnl - commission

                        if pnl > 0:
                            winning_trades += 1
                            total_profit += pnl
                        else:
                            losing_trades += 1
                            total_loss += abs(pnl)

                        trade_count += 1
                        position = 0
                        entry_price = 0
                        stop_loss = 0
                        take_profit = 0

            # Check entry conditions
            if position == 0:
                # Check minimum candles between trades
                if i - last_trade_index < self.params['min_candles_between']:
                    pass  # Skip, not enough candles since last trade
                else:
                    buy_score = self.calculate_signal_score(row, 'buy')
                    sell_score = self.calculate_signal_score(row, 'sell')

                    # Check trades per hour limit
                    hour_key = row['datetime'].strftime('%Y-%m-%d %H')
                    if trades_per_hour.get(hour_key, 0) >= self.params['max_trades_per_hour']:
                        pass  # Skip, max trades per hour reached
                    else:
                        # Long entry
                        if buy_score >= self.params['min_signal_score']:
                            atr_sl = row['atr'] * self.params['atr_multiplier']
                            tp_distance = atr_sl * self.params['risk_reward_ratio']

                            position_size = (balance * self.params['risk_percent'] / 100) / atr_sl
                            position = position_size
                            entry_price = current_price
                            stop_loss = current_price - atr_sl
                            take_profit = current_price + tp_distance

                            last_trade_index = i
                            trades_per_hour[hour_key] = trades_per_hour.get(hour_key, 0) + 1

                        # Short entry
                        elif sell_score >= self.params['min_signal_score']:
                            atr_sl = row['atr'] * self.params['atr_multiplier']
                            tp_distance = atr_sl * self.params['risk_reward_ratio']

                            position_size = (balance * self.params['risk_percent'] / 100) / atr_sl
                            position = -position_size
                            entry_price = current_price
                            stop_loss = current_price + atr_sl
                            take_profit = current_price - tp_distance

                            last_trade_index = i
                            trades_per_hour[hour_key] = trades_per_hour.get(hour_key, 0) + 1

            # Update equity curve
            if position != 0:
                unrealized_pnl = 0
                if position > 0:
                    unrealized_pnl = (current_price - entry_price) * position
                else:
                    unrealized_pnl = (entry_price - current_price) * abs(position)
                current_equity = balance + unrealized_pnl
            else:
                current_equity = balance

            self.equity_curve.append(current_equity)

            # Track drawdown
            if current_equity > peak_balance:
                peak_balance = current_equity
            drawdown = (peak_balance - current_equity) / peak_balance
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Close any remaining position
        if position != 0:
            current_price = self.data.iloc[-1]['close']
            if position > 0:
                pnl = (current_price - entry_price) * position
            else:
                pnl = (entry_price - current_price) * abs(position)
            commission = abs(position) * current_price * self.params['commission']
            balance += pnl - commission

            if pnl > 0:
                winning_trades += 1
                total_profit += pnl
            else:
                losing_trades += 1
                total_loss += abs(pnl)
            trade_count += 1

        # Calculate final metrics
        final_balance = balance
        total_return = (final_balance - self.params['initial_balance']) / self.params['initial_balance'] * 100
        win_rate = (winning_trades / trade_count * 100) if trade_count > 0 else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
        avg_win = (total_profit / winning_trades) if winning_trades > 0 else 0
        avg_loss = (total_loss / losing_trades) if losing_trades > 0 else 0

        results = {
            'initial_balance': self.params['initial_balance'],
            'final_balance': final_balance,
            'total_return': total_return,
            'total_trades': trade_count,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown * 100,
            'total_profit': total_profit,
            'total_loss': total_loss
        }

        return results

    def is_session_allowed(self, session):
        """Check if trading is allowed in this session"""
        if session == 'asian':
            return self.params['trade_asian']
        elif session == 'london':
            return self.params['trade_london']
        elif session == 'newyork':
            return self.params['trade_newyork']
        elif session == 'overlap':
            return self.params['trade_overlap']
        else:
            return False

    def print_results(self, results):
        """Print backtest results"""
        print("\n" + "="*60)
        print("XAU/USD SCALPING BACKTEST RESULTS")
        print("="*60)
        print(f"Symbol: {self.symbol}")
        print(f"Timeframe: {self.interval}")
        print(f"Period: {self.period}")
        print("-"*60)
        print(f"Initial Balance: ${results['initial_balance']:,.2f}")
        print(f"Final Balance:   ${results['final_balance']:,.2f}")
        print(f"Total Return:    {results['total_return']:+.2f}%")
        print("-"*60)
        print(f"Total Trades:    {results['total_trades']}")
        print(f"Winning Trades:  {results['winning_trades']}")
        print(f"Losing Trades:   {results['losing_trades']}")
        print(f"Win Rate:        {results['win_rate']:.2f}%")
        print("-"*60)
        print(f"Profit Factor:   {results['profit_factor']:.2f}")
        print(f"Average Win:     ${results['avg_win']:.2f}")
        print(f"Average Loss:    ${results['avg_loss']:.2f}")
        print(f"Max Drawdown:    {results['max_drawdown']:.2f}%")
        print("="*60)

        # Performance rating
        if results['win_rate'] >= 45 and results['profit_factor'] >= 1.3:
            print("🟢 GOOD - Strategy shows positive results for scalping")
        elif results['win_rate'] >= 35 and results['profit_factor'] >= 1.0:
            print("🟡 MODERATE - Strategy needs optimization")
        else:
            print("🔴 POOR - Strategy needs significant improvement")

    def plot_equity_curve(self):
        """Plot equity curve"""
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve, linewidth=2, color='#2E86AB')
        plt.title('XAU/USD Scalping Strategy - Equity Curve', fontsize=14, fontweight='bold')
        plt.xlabel('Bars', fontsize=12)
        plt.ylabel('Balance ($)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('xauusd_scalping_equity_curve.png', dpi=100, bbox_inches='tight')
        print("Equity curve saved as 'xauusd_scalping_equity_curve.png'")

def main():
    """Main function"""
    print("XAU/USD Professional Scalping Backtester")
    print("="*60)

    # Configuration
    symbol = input("Enter symbol (default: GC=F for Gold): ") or "GC=F"
    interval = input("Enter timeframe (default: 5m): ") or "5m"
    period = input("Enter period (default: 3mo): ") or "3mo"

    # Create backtester
    bt = XAUUSDScalpingBacktester(symbol=symbol, interval=interval, period=period)

    try:
        # Fetch data
        bt.fetch_data()

        # Calculate indicators
        bt.calculate_indicators()

        # Run backtest
        results = bt.run_backtest()

        # Print results
        bt.print_results(results)

        # Plot equity curve
        bt.plot_equity_curve()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
