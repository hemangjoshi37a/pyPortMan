"""
Simple but Effective Trading Strategy
Goal: 50%+ win rate with positive returns

Strategy Logic:
1. Trend: EMA 9/21 crossover for trend direction
2. Momentum: RSI for entry timing (oversold/overbought)
3. Confirmation: Volume spike
4. Risk: ATR-based stop loss with 1:2 R:R ratio
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def simple_strategy_backtest(symbol="BTC-USD", interval="1h", period="6mo"):
    """Run simple strategy backtest"""

    print(f"Testing {symbol} ({interval}, {period})...")
    print("-" * 50)

    # Fetch data
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval)

    if data.empty:
        print("No data found!")
        return None

    # Resample if 4h
    if interval == '4h':
        data = data.resample('4h').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

    data = data.reset_index()

    # Handle column names - yfinance returns capitalized columns
    column_map = {}
    for col in data.columns:
        if col.lower() == 'datetime' or col.lower() == 'date':
            column_map[col] = 'datetime'
        elif col.lower() == 'open':
            column_map[col] = 'open'
        elif col.lower() == 'high':
            column_map[col] = 'high'
        elif col.lower() == 'low':
            column_map[col] = 'low'
        elif col.lower() == 'close':
            column_map[col] = 'close'
        elif col.lower() == 'volume':
            column_map[col] = 'volume'

    data = data.rename(columns=column_map)

    # Keep only needed columns
    cols_to_keep = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    available_cols = [c for c in cols_to_keep if c in data.columns]
    data = data[available_cols]

    # Parameters
    params = {
        'ema_fast': 9,
        'ema_slow': 21,
        'rsi_period': 14,
        'rsi_long_entry': 35,  # Buy when RSI below this
        'rsi_short_entry': 65,  # Sell when RSI above this
        'atr_period': 14,
        'atr_multiplier': 2.0,
        'volume_ma': 20,
        'volume_mult': 1.3,
        'risk_percent': 0.02,
        'reward_risk_ratio': 2.0,
        'commission': 0.001,
        'initial_balance': 10000
    }

    # Calculate indicators
    df = data.copy()

    # EMA
    df['ema_fast'] = df['close'].ewm(span=params['ema_fast']).mean()
    df['ema_slow'] = df['close'].ewm(span=params['ema_slow']).mean()

    # EMA Crossover
    df['ema_cross_up'] = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
    df['ema_cross_down'] = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))

    # Trend direction
    df['trend_up'] = df['ema_fast'] > df['ema_slow']
    df['trend_down'] = df['ema_fast'] < df['ema_slow']

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # RSI conditions
    df['rsi_oversold'] = df['rsi'] < params['rsi_long_entry']
    df['rsi_overbought'] = df['rsi'] > params['rsi_short_entry']

    # ATR
    high_diff = df['high'].diff()
    low_diff = -df['low'].diff()
    tr = pd.concat([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=params['atr_period']).mean()

    # Volume
    df['vol_ma'] = df['volume'].rolling(window=params['volume_ma']).mean()
    df['high_volume'] = df['volume'] > df['vol_ma'] * params['volume_mult']

    # Entry conditions
    # LONG: Trend up + RSI oversold + High volume
    df['long_signal'] = df['trend_up'] & df['rsi_oversold'] & df['high_volume']

    # SHORT: Trend down + RSI overbought + High volume
    df['short_signal'] = df['trend_down'] & df['rsi_overbought'] & df['high_volume']

    # Exit conditions
    df['long_exit'] = df['trend_down'] | (df['rsi'] > 70)
    df['short_exit'] = df['trend_up'] | (df['rsi'] < 30)

    # Run backtest
    balance = params['initial_balance']
    position = 0
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    trades = []
    winning = 0
    losing = 0
    total_profit = 0
    total_loss = 0
    peak_balance = balance
    max_dd = 0
    consecutive_losses = 0
    max_consecutive_losses = 0

    for i in range(50, len(df)):
        row = df.iloc[i]
        price = row['close']

        # Check exit
        if position != 0:
            should_exit = False

            if position > 0:  # Long
                if price <= stop_loss or price >= take_profit or row['long_exit']:
                    should_exit = True
            else:  # Short
                if price >= stop_loss or price <= take_profit or row['short_exit']:
                    should_exit = True

            if should_exit:
                if position > 0:
                    pnl = (price - entry_price) * position
                else:
                    pnl = (entry_price - price) * abs(position)

                comm = abs(position) * price * params['commission']
                balance += pnl - comm
                trades.append(pnl - comm)

                if pnl > 0:
                    winning += 1
                    total_profit += pnl
                    consecutive_losses = 0
                else:
                    losing += 1
                    total_loss += abs(pnl)
                    consecutive_losses += 1
                    if consecutive_losses > max_consecutive_losses:
                        max_consecutive_losses = consecutive_losses

                position = 0
                entry_price = 0
                stop_loss = 0
                take_profit = 0

        # Check entry (only if no position and not in losing streak)
        if position == 0 and consecutive_losses < 3:
            atr_sl = df['atr'].iloc[i] * params['atr_multiplier']
            tp_dist = atr_sl * params['reward_risk_ratio']

            if row['long_signal']:
                pos_size = (balance * params['risk_percent']) / atr_sl
                position = pos_size
                entry_price = price
                stop_loss = price - atr_sl
                take_profit = price + tp_dist

            elif row['short_signal']:
                pos_size = (balance * params['risk_percent']) / atr_sl
                position = -pos_size
                entry_price = price
                stop_loss = price + atr_sl
                take_profit = price - tp_dist

        # Track drawdown
        if position != 0:
            unrealized = (price - entry_price) * position if position > 0 else (entry_price - price) * abs(position)
            curr_eq = balance + unrealized
        else:
            curr_eq = balance

        if curr_eq > peak_balance:
            peak_balance = curr_eq
        dd = (peak_balance - curr_eq) / peak_balance
        if dd > max_dd:
            max_dd = dd

    # Close remaining position
    if position != 0:
        price = df.iloc[-1]['close']
        if position > 0:
            pnl = (price - entry_price) * position
        else:
            pnl = (entry_price - price) * abs(position)
        comm = abs(position) * price * params['commission']
        balance += pnl - comm
        trades.append(pnl - comm)
        if pnl > 0:
            winning += 1
            total_profit += pnl
        else:
            losing += 1
            total_loss += abs(pnl)

    # Calculate metrics
    total_trades = winning + losing
    win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
    total_return = (balance - params['initial_balance']) / params['initial_balance'] * 100
    avg_win = (total_profit / winning) if winning > 0 else 0
    avg_loss = (total_loss / losing) if losing > 0 else 0

    print(f"\n{'='*50}")
    print("RESULTS")
    print(f"{'='*50}")
    print(f"Initial:  ${params['initial_balance']:,.2f}")
    print(f"Final:    ${balance:,.2f}")
    print(f"Return:   {total_return:+.2f}%")
    print(f"Trades:   {total_trades}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Avg Win:  ${avg_win:.2f}")
    print(f"Avg Loss: ${avg_loss:.2f}")
    print(f"Max DD:   {max_dd*100:.2f}%")
    print(f"Max Consecutive Losses: {max_consecutive_losses}")
    print(f"{'='*50}")

    # Rating
    if win_rate >= 50 and profit_factor >= 1.5:
        rating = "[EXCELLENT]"
    elif win_rate >= 45 and profit_factor >= 1.2:
        rating = "[GOOD]"
    elif win_rate >= 40 and profit_factor >= 1.0:
        rating = "[MODERATE]"
    else:
        rating = "[POOR]"

    print(f"Rating: {rating}")

    return {
        'symbol': symbol,
        'total_return': total_return,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd * 100,
        'total_trades': total_trades,
        'winning_trades': winning,
        'losing_trades': losing,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'rating': rating
    }

def optimize_parameters(symbol="BTC-USD", interval="1h", period="3mo"):
    """Optimize strategy parameters"""

    print(f"\nOptimizing parameters for {symbol}...")
    print("-" * 50)

    # Fetch data
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval)

    if data.empty:
        print("No data found!")
        return None

    if interval == '4h':
        data = data.resample('4h').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

    data = data.reset_index()

    # Handle column names - yfinance returns capitalized columns
    column_map = {}
    for col in data.columns:
        if col.lower() == 'datetime' or col.lower() == 'date':
            column_map[col] = 'datetime'
        elif col.lower() == 'open':
            column_map[col] = 'open'
        elif col.lower() == 'high':
            column_map[col] = 'high'
        elif col.lower() == 'low':
            column_map[col] = 'low'
        elif col.lower() == 'close':
            column_map[col] = 'close'
        elif col.lower() == 'volume':
            column_map[col] = 'volume'

    data = data.rename(columns=column_map)

    # Keep only needed columns
    cols_to_keep = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    available_cols = [c for c in cols_to_keep if c in data.columns]
    data = data[available_cols]

    # Calculate base indicators
    df = data.copy()

    # Test different parameter combinations
    ema_fast_options = [7, 9, 12]
    ema_slow_options = [18, 21, 26]
    rsi_entry_options = [30, 35, 40]
    volume_mult_options = [1.2, 1.5, 1.8]

    best_result = None
    best_params = None

    total_combinations = len(ema_fast_options) * len(ema_slow_options) * len(rsi_entry_options) * len(volume_mult_options)
    tested = 0

    for ema_fast in ema_fast_options:
        for ema_slow in ema_slow_options:
            if ema_fast >= ema_slow:
                continue

            for rsi_entry in rsi_entry_options:
                for vol_mult in volume_mult_options:
                    tested += 1
                    print(f"\rTesting {tested}/{total_combinations}...", end='')

                    # Calculate indicators
                    df['ema_fast'] = df['close'].ewm(span=ema_fast).mean()
                    df['ema_slow'] = df['close'].ewm(span=ema_slow).mean()
                    df['trend_up'] = df['ema_fast'] > df['ema_slow']
                    df['trend_down'] = df['ema_fast'] < df['ema_slow']

                    delta = df['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    df['rsi'] = 100 - (100 / (1 + rs))

                    df['rsi_oversold'] = df['rsi'] < rsi_entry
                    df['rsi_overbought'] = df['rsi'] > (100 - rsi_entry)

                    tr = pd.concat([
                        df['high'] - df['low'],
                        abs(df['high'] - df['close'].shift(1)),
                        abs(df['low'] - df['close'].shift(1))
                    ], axis=1).max(axis=1)
                    df['atr'] = tr.rolling(window=14).mean()

                    df['vol_ma'] = df['volume'].rolling(window=20).mean()
                    df['high_volume'] = df['volume'] > df['vol_ma'] * vol_mult

                    df['long_signal'] = df['trend_up'] & df['rsi_oversold'] & df['high_volume']
                    df['short_signal'] = df['trend_down'] & df['rsi_overbought'] & df['high_volume']

                    # Quick backtest
                    balance = 10000
                    position = 0
                    entry_price = 0
                    stop_loss = 0
                    take_profit = 0
                    winning = 0
                    losing = 0
                    total_profit = 0
                    total_loss = 0

                    for i in range(50, len(df)):
                        row = df.iloc[i]
                        price = row['close']

                        if position != 0:
                            should_exit = False
                            if position > 0:
                                if price <= stop_loss or price >= take_profit or not row['trend_up']:
                                    should_exit = True
                            else:
                                if price >= stop_loss or price <= take_profit or not row['trend_down']:
                                    should_exit = True

                            if should_exit:
                                if position > 0:
                                    pnl = (price - entry_price) * position
                                else:
                                    pnl = (entry_price - price) * abs(position)
                                comm = abs(position) * price * 0.001
                                balance += pnl - comm
                                if pnl > 0:
                                    winning += 1
                                    total_profit += pnl
                                else:
                                    losing += 1
                                    total_loss += abs(pnl)
                                position = 0

                        if position == 0:
                            atr_sl = df['atr'].iloc[i] * 2
                            tp_dist = atr_sl * 2

                            if row['long_signal']:
                                pos_size = (balance * 0.02) / atr_sl
                                position = pos_size
                                entry_price = price
                                stop_loss = price - atr_sl
                                take_profit = price + tp_dist
                            elif row['short_signal']:
                                pos_size = (balance * 0.02) / atr_sl
                                position = -pos_size
                                entry_price = price
                                stop_loss = price + atr_sl
                                take_profit = price - tp_dist

                    total_trades = winning + losing
                    if total_trades < 5:
                        continue

                    win_rate = (winning / total_trades * 100)
                    profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
                    total_return = (balance - 10000) / 10000 * 100

                    # Score: prioritize win rate > 50% and positive return
                    score = 0
                    if win_rate >= 50:
                        score += 50
                    if profit_factor >= 1.5:
                        score += 30
                    if total_return > 0:
                        score += 20

                    if best_result is None or score > best_result:
                        best_result = score
                        best_params = {
                            'ema_fast': ema_fast,
                            'ema_slow': ema_slow,
                            'rsi_entry': rsi_entry,
                            'volume_mult': vol_mult,
                            'win_rate': win_rate,
                            'profit_factor': profit_factor,
                            'total_return': total_return,
                            'total_trades': total_trades
                        }

    print(f"\n\n{'='*50}")
    print("BEST PARAMETERS FOUND")
    print(f"{'='*50}")
    if best_params:
        print(f"EMA Fast: {best_params['ema_fast']}")
        print(f"EMA Slow: {best_params['ema_slow']}")
        print(f"RSI Entry: {best_params['rsi_entry']}")
        print(f"Volume Multiplier: {best_params['volume_mult']}")
        print(f"Win Rate: {best_params['win_rate']:.1f}%")
        print(f"Profit Factor: {best_params['profit_factor']:.2f}")
        print(f"Total Return: {best_params['total_return']:+.2f}%")
        print(f"Total Trades: {best_params['total_trades']}")
    else:
        print("No valid parameters found")

    return best_params

def main():
    """Main function"""
    print("SIMPLE TRADING STRATEGY BACKTESTER")
    print("="*60)

    # Test multiple symbols
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    interval = "1h"
    period = "6mo"

    all_results = []

    for sym in symbols:
        try:
            result = simple_strategy_backtest(sym, interval, period)
            if result:
                all_results.append(result)
        except Exception as e:
            print(f"Error testing {sym}: {e}\n")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Symbol':<12} {'Return':<10} {'Win Rate':<10} {'PF':<8} {'Trades':<8} {'Rating'}")
    print("-" * 60)

    for r in all_results:
        print(f"{r['symbol']:<12} {r['total_return']:+7.1f}%   {r['win_rate']:>6.1f}%   {r['profit_factor']:>5.2f}   {r['total_trades']:>6}   {r['rating']}")

    # Calculate average
    if all_results:
        avg_win_rate = sum(r['win_rate'] for r in all_results) / len(all_results)
        avg_return = sum(r['total_return'] for r in all_results) / len(all_results)
        avg_pf = sum(r['profit_factor'] for r in all_results) / len(all_results)

        print("-" * 60)
        print(f"{'AVERAGE':<12} {avg_return:+7.1f}%   {avg_win_rate:>6.1f}%   {avg_pf:>5.2f}")

        # Overall assessment
        print("\n" + "="*60)
        if avg_win_rate >= 50 and avg_pf >= 1.5:
            print("OVERALL: EXCELLENT - Strategy meets 50%+ win rate goal!")
        elif avg_win_rate >= 45 and avg_pf >= 1.2:
            print("OVERALL: GOOD - Strategy is close to target")
        elif avg_win_rate >= 40 and avg_pf >= 1.0:
            print("OVERALL: MODERATE - Needs optimization")
        else:
            print("OVERALL: POOR - Strategy needs significant improvement")
            print("\nSuggestion: Run parameter optimization")
            print("Command: python simple_strategy.py --optimize")

    # Ask if user wants optimization
    print("\n" + "="*60)
    print("To optimize parameters, run:")
    print("python simple_strategy.py --optimize")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--optimize":
        optimize_parameters()
    else:
        main()
