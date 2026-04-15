"""
Pine Script Strategy Backtester
Backtests the Professional Buy/Sell Signal strategy using Python
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

class PineScriptBacktester:
    def __init__(self, symbol="BTC-USD", interval="1h", period="6mo"):
        """
        Initialize backtester

        Args:
            symbol: Trading pair (e.g., "BTC-USD", "ETH-USD")
            interval: Timeframe ("1m", "5m", "15m", "1h", "4h", "1d")
            period: Data period ("1mo", "3mo", "6mo", "1y", "2y")
        """
        self.symbol = symbol
        self.interval = interval
        self.period = period
        self.data = None
        self.trades = []
        self.equity_curve = []

        # Strategy parameters (matching Pine Script defaults)
        self.params = {
            'ema_fast': 9,
            'ema_slow': 21,
            'ema_trend': 50,
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_dev': 2.0,
            'stoch_k': 14,
            'stoch_d': 3,
            'stoch_ob': 80,
            'stoch_os': 20,
            'adx_period': 14,
            'adx_threshold': 25,
            'volume_ma': 20,
            'volume_mult': 1.5,
            'min_signal_score': 16,
            'risk_percent': 0.005,
            'reward_risk_ratio': 2.0,
            'commission': 0.001,  # 0.1% commission
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

        yf_interval = interval_map.get(self.interval, '1h')

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

        # Rename columns to match Pine Script
        self.data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']

        print(f"Loaded {len(self.data)} candles")

    def calculate_indicators(self):
        """Calculate all indicators used in the strategy"""
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

        df['rsi_oversold'] = df['rsi'] < self.params['rsi_oversold']
        df['rsi_overbought'] = df['rsi'] > self.params['rsi_overbought']
        df['rsi_bullish'] = (df['rsi'] > 50) & (df['rsi'] < self.params['rsi_overbought'])
        df['rsi_bearish'] = (df['rsi'] < 50) & (df['rsi'] > self.params['rsi_oversold'])

        # RSI Divergence (simplified)
        df['rsi_bullish_div'] = (df['low'] < df['low'].shift(4)) & (df['rsi'] > df['rsi'].shift(4))
        df['rsi_bearish_div'] = (df['high'] > df['high'].shift(4)) & (df['rsi'] < df['rsi'].shift(4))

        # MACD
        exp1 = df['close'].ewm(span=self.params['macd_fast']).mean()
        exp2 = df['close'].ewm(span=self.params['macd_slow']).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.params['macd_signal']).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        df['macd_bullish'] = df['macd'] > df['macd_signal']
        df['macd_bearish'] = df['macd'] < df['macd_signal']
        df['macd_cross_up'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        df['macd_cross_down'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))

        # MACD Divergence
        df['macd_bullish_div'] = (df['low'] < df['low'].shift(4)) & (df['macd'] > df['macd'].shift(4))
        df['macd_bearish_div'] = (df['high'] > df['high'].shift(4)) & (df['macd'] < df['macd'].shift(4))

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.params['bb_period']).mean()
        bb_std = df['close'].rolling(window=self.params['bb_period']).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.params['bb_dev'])
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.params['bb_dev'])

        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(50).mean() * 0.8
        df['near_bb_lower'] = df['close'] <= df['bb_lower'] * 1.005
        df['near_bb_upper'] = df['close'] >= df['bb_upper'] * 0.995

        # Stochastic
        low_min = df['low'].rolling(window=self.params['stoch_k']).min()
        high_max = df['high'].rolling(window=self.params['stoch_k']).max()
        df['stoch_k_raw'] = 100 * (df['close'] - low_min) / (high_max - low_min)
        df['stoch_k'] = df['stoch_k_raw'].rolling(window=self.params['stoch_d']).mean()
        df['stoch_d'] = df['stoch_k'].rolling(window=self.params['stoch_d']).mean()

        df['stoch_oversold'] = df['stoch_k'] < self.params['stoch_os']
        df['stoch_overbought'] = df['stoch_k'] > self.params['stoch_ob']
        df['stoch_cross_up'] = (df['stoch_k'] > self.params['stoch_os']) & (df['stoch_k'].shift(1) <= self.params['stoch_os'].shift(1))
        df['stoch_cross_down'] = (df['stoch_k'] < self.params['stoch_ob']) & (df['stoch_k'].shift(1) >= self.params['stoch_ob'].shift(1))

        # ADX
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=self.params['adx_period']).mean()

        plus_di = 100 * (pd.Series(plus_dm).rolling(window=self.params['adx_period']).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=self.params['adx_period']).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=self.params['adx_period']).mean()

        df['adx_strong'] = df['adx'] > self.params['adx_threshold']
        df['adx_up_trend'] = plus_di > minus_di
        df['adx_down_trend'] = minus_di > plus_di

        # Volume
        df['vol_ma'] = df['volume'].rolling(window=self.params['volume_ma']).mean()
        df['high_volume'] = df['volume'] > df['vol_ma'] * self.params['volume_mult']
        df['vol_confirm_up'] = (df['close'] > df['close'].shift(1)) & df['high_volume']
        df['vol_confirm_down'] = (df['close'] < df['close'].shift(1)) & df['high_volume']

        # ATR for SL/TP
        df['atr'] = tr.rolling(window=14).mean()

        # Trend
        df['trend_up'] = (df['ema_fast'] > df['ema_slow']) & (df['close'] > df['ema_trend'])
        df['trend_down'] = (df['ema_fast'] < df['ema_slow']) & (df['close'] < df['ema_trend'])
        df['trend_neutral'] = (~df['trend_up']) & (~df['trend_down'])

        # Market condition
        price_range = (df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['close']
        df['ranging_market'] = (price_range < 0.02) & (~df['bb_squeeze'])
        df['trending_market'] = ~df['ranging_market']

        # Candle patterns
        df['bullish_engulfing'] = (df['close'].shift(1) < df['open'].shift(1)) & \
                                   (df['close'] > df['open']) & \
                                   (df['close'] > df['open'].shift(1)) & \
                                   (df['open'] < df['close'].shift(1))

        df['bearish_engulfing'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                                   (df['close'] < df['open']) & \
                                   (df['close'] < df['open'].shift(1)) & \
                                   (df['open'] > df['close'].shift(1))

        df['hammer'] = (abs(df['close'] - df['open']) < (df['high'] - df['low']) * 0.3) & \
                       (df['low'] < df['open'] - (df['high'] - df['low']) * 0.6) & \
                       (df['close'] > df['open'])

        df['shooting_star'] = (abs(df['close'] - df['open']) < (df['high'] - df['low']) * 0.3) & \
                               (df['high'] > df['open'] + (df['high'] - df['low']) * 0.6) & \
                               (df['close'] < df['open'])

        self.data = df
        print("Indicators calculated")

    def calculate_signal_score(self, row, direction='buy'):
        """Calculate signal score matching Pine Script logic"""
        score = 0

        # Trend analysis
        if direction == 'buy':
            score += 2 if row['trend_up'] else (0 if row['trend_neutral'] else -1)
            score += 3 if row['ema_cross_up'] else 0
        else:
            score += 2 if row['trend_down'] else (0 if row['trend_neutral'] else -1)
            score += 3 if row['ema_cross_down'] else 0

        # RSI analysis
        if direction == 'buy':
            score += 2 if row['rsi_oversold'] else (1 if row['rsi_bullish'] else 0)
            score += 3 if row['rsi_bullish_div'] else 0
        else:
            score += 2 if row['rsi_overbought'] else (1 if row['rsi_bearish'] else 0)
            score += 3 if row['rsi_bearish_div'] else 0

        # MACD analysis
        if direction == 'buy':
            score += 2 if row['macd_cross_up'] else (1 if row['macd_bullish'] else 0)
            score += 2 if row['macd_bullish_div'] else 0
        else:
            score += 2 if row['macd_cross_down'] else (1 if row['macd_bearish'] else 0)
            score += 2 if row['macd_bearish_div'] else 0

        # Bollinger Bands
        if direction == 'buy':
            score += 2 if row['near_bb_lower'] else 0
            score += 1 if (row['bb_squeeze'] and row['trend_up']) else 0
        else:
            score += 2 if row['near_bb_upper'] else 0
            score += 1 if (row['bb_squeeze'] and row['trend_down']) else 0

        # Stochastic
        if direction == 'buy':
            score += 2 if row['stoch_oversold'] else 0
            score += 2 if row['stoch_cross_up'] else 0
        else:
            score += 2 if row['stoch_overbought'] else 0
            score += 2 if row['stoch_cross_down'] else 0

        # ADX
        if direction == 'buy':
            score += 2 if (row['adx_strong'] and row['adx_up_trend']) else 0
        else:
            score += 2 if (row['adx_strong'] and row['adx_down_trend']) else 0

        # Volume
        if direction == 'buy':
            score += 1 if row['vol_confirm_up'] else 0
        else:
            score += 1 if row['vol_confirm_down'] else 0

        # Candle patterns
        if direction == 'buy':
            score += 2 if (row['bullish_engulfing'] or row['hammer']) else 0
        else:
            score += 2 if (row['bearish_engulfing'] or row['shooting_star']) else 0

        # Market condition filter
        if row['ranging_market']:
            score -= 3

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

        for i in range(50, len(self.data)):  # Skip first 50 bars for indicator warmup
            row = self.data.iloc[i]
            current_price = row['close']

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
                buy_score = self.calculate_signal_score(row, 'buy')
                sell_score = self.calculate_signal_score(row, 'sell')

                # Long entry
                if buy_score >= self.params['min_signal_score']:
                    atr_sl = row['atr'] * 2
                    tp_distance = atr_sl * self.params['reward_risk_ratio']

                    position_size = (balance * self.params['risk_percent']) / atr_sl
                    position = position_size
                    entry_price = current_price
                    stop_loss = current_price - atr_sl
                    take_profit = current_price + tp_distance

                # Short entry
                elif sell_score >= self.params['min_signal_score']:
                    atr_sl = row['atr'] * 2
                    tp_distance = atr_sl * self.params['reward_risk_ratio']

                    position_size = (balance * self.params['risk_percent']) / atr_sl
                    position = -position_size
                    entry_price = current_price
                    stop_loss = current_price + atr_sl
                    take_profit = current_price - tp_distance

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

    def print_results(self, results):
        """Print backtest results"""
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
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
        if results['win_rate'] >= 50 and results['profit_factor'] >= 1.5:
            print("🟢 GOOD - Strategy shows positive results")
        elif results['win_rate'] >= 40 and results['profit_factor'] >= 1.0:
            print("🟡 MODERATE - Strategy needs optimization")
        else:
            print("🔴 POOR - Strategy needs significant improvement")

    def plot_equity_curve(self):
        """Plot equity curve"""
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve, linewidth=2)
        plt.title('Equity Curve', fontsize=14)
        plt.xlabel('Bars', fontsize=12)
        plt.ylabel('Balance ($)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig('equity_curve.png', dpi=100)
        print("Equity curve saved as 'equity_curve.png'")

def main():
    """Main function"""
    print("Pine Script Strategy Backtester")
    print("="*60)

    # Configuration
    symbol = input("Enter symbol (default: BTC-USD): ") or "BTC-USD"
    interval = input("Enter timeframe (default: 1h): ") or "1h"
    period = input("Enter period (default: 6mo): ") or "6mo"

    # Create backtester
    bt = PineScriptBacktester(symbol=symbol, interval=interval, period=period)

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

if __name__ == "__main__":
    main()
