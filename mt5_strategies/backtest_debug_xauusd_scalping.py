"""
Debug Version of XAU/USD Scalping Backtester
Shows detailed signal information to understand why trades aren't triggering
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class XAUUSDScalpingBacktesterDebug:
    def __init__(self, symbol="GC=F", interval="5m", period="3mo"):
        """
        Initialize Debug Backtester with MORE LENIENT parameters
        """
        self.symbol = symbol
        self.interval = interval
        self.period = period
        self.data = None
        self.trades = []
        self.equity_curve = []

        # MORE LENIENT PARAMETERS for testing
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

            # ADX Settings - LOWERED
            'adx_period': 14,
            'adx_threshold': 20,  # Lowered from 25

            # RSI Settings
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,

            # SMC Settings
            'swing_lookback': 3,
            'fvg_min_size': 5,
            'ob_lookback': 10,

            # Entry Settings - LOWERED
            'min_signal_score': 25,  # Lowered from 45

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

            # Session Settings - MORE PERMISSIVE
            'trade_asian': False,
            'trade_london': True,
            'trade_newyork': True,
            'trade_overlap': True,

            # Other Settings
            'max_positions': 2,
            'max_spread': 50,  # Increased from 30
            'max_trades_per_hour': 5,  # Increased from 3
            'min_candles_between': 2,  # Decreased from 3

            # Commission
            'commission': 0.0002,
            'initial_balance': 10000
        }

        # Debug counters
        self.debug_stats = {
            'total_bars': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'blocked_by_session': 0,
            'blocked_by_min_candles': 0,
            'blocked_by_max_trades_hour': 0,
            'blocked_by_max_positions': 0,
            'blocked_by_daily_loss': 0,
            'blocked_by_weekly_loss': 0,
            'signal_scores_buy': [],
            'signal_scores_sell': [],
            'highest_buy_score': 0,
            'highest_sell_score': 0
        }

    def fetch_data(self):
        """Fetch historical data from Yahoo Finance"""
        print(f"Fetching {self.symbol} data ({self.interval}, {self.period})...")

        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '1h',
            '1d': '1d'
        }

        yf_interval = interval_map.get(self.interval, '5m')

        ticker = yf.Ticker(self.symbol)
        self.data = ticker.history(period=self.period, interval=yf_interval)

        if self.data.empty:
            raise ValueError(f"No data found for {self.symbol}")

        if self.interval == '4h':
            self.data = self.data.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        self.data = self.data.reset_index()
        self.data.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']

        print(f"Loaded {len(self.data)} candles")

    def calculate_indicators(self):
        """Calculate all indicators"""
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
        """Calculate signal score with detailed breakdown"""
        score = 0
        breakdown = []

        # 1. Trend Alignment (20 points)
        if direction == 'buy':
            if row['trend_up']:
                score += 10
                breakdown.append("Trend Up: +10")
            if row['ema_cross_up']:
                score += 10
                breakdown.append("EMA Cross Up: +10")
        else:
            if row['trend_down']:
                score += 10
                breakdown.append("Trend Down: +10")
            if row['ema_cross_down']:
                score += 10
                breakdown.append("EMA Cross Down: +10")

        # 2. Market Structure (15 points)
        if direction == 'buy':
            if row['close'] > row['ema_trend']:
                score += 8
                breakdown.append("Price > EMA Trend: +8")
            if row['close'] > row['ema_slow']:
                score += 7
                breakdown.append("Price > EMA Slow: +7")
        else:
            if row['close'] < row['ema_trend']:
                score += 8
                breakdown.append("Price < EMA Trend: +8")
            if row['close'] < row['ema_slow']:
                score += 7
                breakdown.append("Price < EMA Slow: +7")

        # 3. ADX Strength (10 points)
        if row['adx'] > self.params['adx_threshold']:
            score += 10
            breakdown.append(f"ADX > {self.params['adx_threshold']}: +10")
            if row['adx'] > 40:
                score += 2
                breakdown.append("ADX > 40: +2")

        # 4. RSI Condition (10 points)
        if direction == 'buy':
            if row['rsi'] < 70 and row['rsi'] > 30:
                score += 5
                breakdown.append("RSI 30-70: +5")
            if row['rsi'] < 50:
                score += 5
                breakdown.append("RSI < 50: +5")
        else:
            if row['rsi'] > 30 and row['rsi'] < 70:
                score += 5
                breakdown.append("RSI 30-70: +5")
            if row['rsi'] > 50:
                score += 5
                breakdown.append("RSI > 50: +5")

        # 5. Candlestick Patterns (10 points)
        if direction == 'buy':
            if row['bullish_engulfing']:
                score += 6
                breakdown.append("Bullish Engulfing: +6")
            if row['bullish_pinbar']:
                score += 6
                breakdown.append("Bullish Pinbar: +6")
        else:
            if row['bearish_engulfing']:
                score += 6
                breakdown.append("Bearish Engulfing: +6")
            if row['bearish_pinbar']:
                score += 6
                breakdown.append("Bearish Pinbar: +6")

        # 6. Session Favorable (5 points)
        session = row['session']
        if session == 'overlap':
            score += 5
            breakdown.append("Overlap Session: +5")
        elif session in ['london', 'newyork']:
            score += 3
            breakdown.append(f"{session.capitalize()} Session: +3")

        return score, breakdown

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

    def run_backtest(self):
        """Run the backtest with detailed debugging"""
        print("Running backtest with DEBUG mode...")

        balance = self.params['initial_balance']
        position = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        trade_count = 0
        winning_trades = 0
        losing_trades = 0
        total_profit = 0
        total_loss = 0

        self.equity_curve = [balance]

        # Track trades per hour
        trades_per_hour = {}
        last_trade_index = -self.params['min_candles_between']

        # Show first few signal scores
        signal_samples = []

        for i in range(50, len(self.data)):
            row = self.data.iloc[i]
            current_price = row['close']

            self.debug_stats['total_bars'] += 1

            # Check session filter
            if not self.is_session_allowed(row['session']):
                self.debug_stats['blocked_by_session'] += 1
                continue

            # Check exit conditions
            if position != 0:
                if position > 0:  # Long
                    if current_price <= stop_loss or current_price >= take_profit:
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
                    self.debug_stats['blocked_by_min_candles'] += 1
                else:
                    # Check trades per hour limit
                    hour_key = row['datetime'].strftime('%Y-%m-%d %H')
                    if trades_per_hour.get(hour_key, 0) >= self.params['max_trades_per_hour']:
                        self.debug_stats['blocked_by_max_trades_hour'] += 1
                    else:
                        buy_score, buy_breakdown = self.calculate_signal_score(row, 'buy')
                        sell_score, sell_breakdown = self.calculate_signal_score(row, 'sell')

                        # Track scores
                        self.debug_stats['signal_scores_buy'].append(buy_score)
                        self.debug_stats['signal_scores_sell'].append(sell_score)

                        if buy_score > self.debug_stats['highest_buy_score']:
                            self.debug_stats['highest_buy_score'] = buy_score
                        if sell_score > self.debug_stats['highest_sell_score']:
                            self.debug_stats['highest_sell_score'] = sell_score

                        # Collect sample signals
                        if len(signal_samples) < 10:
                            signal_samples.append({
                                'index': i,
                                'datetime': row['datetime'],
                                'price': current_price,
                                'buy_score': buy_score,
                                'sell_score': sell_score,
                                'buy_breakdown': buy_breakdown,
                                'sell_breakdown': sell_breakdown,
                                'session': row['session'],
                                'adx': row['adx'],
                                'rsi': row['rsi']
                            })

                        # Long entry
                        if buy_score >= self.params['min_signal_score']:
                            self.debug_stats['buy_signals'] += 1
                            atr_sl = row['atr'] * self.params['atr_multiplier']
                            tp_distance = atr_sl * self.params['risk_reward_ratio']

                            position_size = (balance * self.params['risk_percent'] / 100) / atr_sl
                            position = position_size
                            entry_price = current_price
                            stop_loss = current_price - atr_sl
                            take_profit = current_price + tp_distance

                            last_trade_index = i
                            trades_per_hour[hour_key] = trades_per_hour.get(hour_key, 0) + 1

                            print(f"✅ BUY SIGNAL at {row['datetime']}: Score={buy_score}, Price={current_price:.2f}")

                        # Short entry
                        elif sell_score >= self.params['min_signal_score']:
                            self.debug_stats['sell_signals'] += 1
                            atr_sl = row['atr'] * self.params['atr_multiplier']
                            tp_distance = atr_sl * self.params['risk_reward_ratio']

                            position_size = (balance * self.params['risk_percent'] / 100) / atr_sl
                            position = -position_size
                            entry_price = current_price
                            stop_loss = current_price + atr_sl
                            take_profit = current_price - tp_distance

                            last_trade_index = i
                            trades_per_hour[hour_key] = trades_per_hour.get(hour_key, 0) + 1

                            print(f"✅ SELL SIGNAL at {row['datetime']}: Score={sell_score}, Price={current_price:.2f}")

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
            'signal_samples': signal_samples
        }

        return results

    def print_debug_stats(self):
        """Print detailed debug statistics"""
        print("\n" + "="*70)
        print("DEBUG STATISTICS")
        print("="*70)

        print(f"\n📊 BAR ANALYSIS:")
        print(f"  Total bars analyzed: {self.debug_stats['total_bars']}")
        print(f"  Blocked by session filter: {self.debug_stats['blocked_by_session']}")
        print(f"  Blocked by min candles between: {self.debug_stats['blocked_by_min_candles']}")
        print(f"  Blocked by max trades per hour: {self.debug_stats['blocked_by_max_trades_hour']}")

        print(f"\n🎯 SIGNAL ANALYSIS:")
        print(f"  Buy signals generated: {self.debug_stats['buy_signals']}")
        print(f"  Sell signals generated: {self.debug_stats['sell_signals']}")
        print(f"  Total signals: {self.debug_stats['buy_signals'] + self.debug_stats['sell_signals']}")

        print(f"\n📈 SCORE DISTRIBUTION:")
        if self.debug_stats['signal_scores_buy']:
            buy_scores = self.debug_stats['signal_scores_buy']
            print(f"  Buy scores - Min: {min(buy_scores):.1f}, Max: {max(buy_scores):.1f}, Avg: {np.mean(buy_scores):.1f}")
            print(f"  Buy scores >= {self.params['min_signal_score']}: {sum(1 for s in buy_scores if s >= self.params['min_signal_score'])}")

        if self.debug_stats['signal_scores_sell']:
            sell_scores = self.debug_stats['signal_scores_sell']
            print(f"  Sell scores - Min: {min(sell_scores):.1f}, Max: {max(sell_scores):.1f}, Avg: {np.mean(sell_scores):.1f}")
            print(f"  Sell scores >= {self.params['min_signal_score']}: {sum(1 for s in sell_scores if s >= self.params['min_signal_score'])}")

        print(f"\n⚙️ CURRENT PARAMETERS:")
        print(f"  Min Signal Score: {self.params['min_signal_score']}")
        print(f"  ADX Threshold: {self.params['adx_threshold']}")
        print(f"  Max Spread: {self.params['max_spread']}")
        print(f"  Max Trades Per Hour: {self.params['max_trades_per_hour']}")
        print(f"  Min Candles Between: {self.params['min_candles_between']}")

        print(f"\n🔍 RECOMMENDATIONS:")

        # Analyze why no trades
        if self.debug_stats['buy_signals'] + self.debug_stats['sell_signals'] == 0:
            print("  ❌ NO SIGNALS GENERATED - Try these changes:")
            print("     1. Lower Min Signal Score (try 15-20)")
            print("     2. Lower ADX Threshold (try 15)")
            print("     3. Enable more sessions (try Asian = True)")
            print("     4. Reduce Min Candles Between (try 1)")
        elif self.debug_stats['blocked_by_session'] > self.debug_stats['total_bars'] * 0.5:
            print("  ⚠️  MOST BARS BLOCKED BY SESSION FILTER")
            print("     Try enabling more sessions or disabling session filter")
        elif self.debug_stats['blocked_by_min_candles'] > self.debug_stats['total_bars'] * 0.3:
            print("  ⚠️  MANY BARS BLOCKED BY MIN CANDLES BETWEEN")
            print("     Try reducing Min Candles Between to 1 or 2")

        print("="*70)

    def print_signal_samples(self, samples):
        """Print sample signal breakdowns"""
        if not samples:
            return

        print("\n" + "="*70)
        print("SAMPLE SIGNAL BREAKDOWNS (First 10)")
        print("="*70)

        for i, sample in enumerate(samples[:10], 1):
            print(f"\n📍 Sample {i} - {sample['datetime']}")
            print(f"   Price: {sample['price']:.2f} | Session: {sample['session']}")
            print(f"   ADX: {sample['adx']:.1f} | RSI: {sample['rsi']:.1f}")
            print(f"   Buy Score: {sample['buy_score']} (Need: {self.params['min_signal_score']})")
            if sample['buy_breakdown']:
                for item in sample['buy_breakdown']:
                    print(f"     - {item}")
            print(f"   Sell Score: {sample['sell_score']} (Need: {self.params['min_signal_score']})")
            if sample['sell_breakdown']:
                for item in sample['sell_breakdown']:
                    print(f"     - {item}")

        print("="*70)

    def print_results(self, results):
        """Print backtest results"""
        print("\n" + "="*70)
        print("XAU/USD SCALPING BACKTEST RESULTS (DEBUG MODE)")
        print("="*70)
        print(f"Symbol: {self.symbol}")
        print(f"Timeframe: {self.interval}")
        print(f"Period: {self.period}")
        print("-"*70)
        print(f"Initial Balance: ${results['initial_balance']:,.2f}")
        print(f"Final Balance:   ${results['final_balance']:,.2f}")
        print(f"Total Return:    {results['total_return']:+.2f}%")
        print("-"*70)
        print(f"Total Trades:    {results['total_trades']}")
        print(f"Winning Trades:  {results['winning_trades']}")
        print(f"Losing Trades:   {results['losing_trades']}")
        print(f"Win Rate:        {results['win_rate']:.2f}%")
        print("-"*70)
        print(f"Profit Factor:   {results['profit_factor']:.2f}")
        print(f"Average Win:     ${results['avg_win']:.2f}")
        print(f"Average Loss:    ${results['avg_loss']:.2f}")
        print("="*70)

        # Print debug stats
        self.print_debug_stats()

        # Print signal samples
        self.print_signal_samples(results['signal_samples'])

def main():
    """Main function"""
    print("XAU/USD Professional Scalping Backtester - DEBUG MODE")
    print("="*70)

    # Configuration
    symbol = input("Enter symbol (default: GC=F for Gold): ") or "GC=F"
    interval = input("Enter timeframe (default: 5m): ") or "5m"
    period = input("Enter period (default: 3mo): ") or "3mo"

    # Create backtester
    bt = XAUUSDScalpingBacktesterDebug(symbol=symbol, interval=interval, period=period)

    try:
        # Fetch data
        bt.fetch_data()

        # Calculate indicators
        bt.calculate_indicators()

        # Run backtest
        results = bt.run_backtest()

        # Print results
        bt.print_results(results)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
