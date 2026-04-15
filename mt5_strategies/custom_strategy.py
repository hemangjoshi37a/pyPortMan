"""
Custom Strategy for GOLD & BTC
- Margin: $80
- Lot size: 0.01 or 0.02
- Target: 50%+ win rate

Optimized Parameters:
- EMA Fast: 7, EMA Slow: 26
- RSI Entry: 40
- Volume Multiplier: 1.5
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def custom_strategy_backtest(symbol="GC=F", interval="1h", period="6mo", lot_size=0.01, margin=80):
    """
    Run custom strategy backtest

    Args:
        symbol: Trading symbol (GC=F for Gold, BTC-USD for Bitcoin)
        interval: Timeframe
        period: Data period
        lot_size: Lot size (0.01 or 0.02)
        margin: Account margin ($80)
    """

    print(f"Testing {symbol} ({interval}, {period})")
    print(f"Lot Size: {lot_size}, Margin: ${margin}")
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

    # Handle column names
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

    cols_to_keep = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    available_cols = [c for c in cols_to_keep if c in data.columns]
    data = data[available_cols]

    # Optimized parameters
    params = {
        'ema_fast': 7,
        'ema_slow': 26,
        'rsi_period': 14,
        'rsi_long_entry': 40,
        'rsi_short_entry': 60,
        'atr_period': 14,
        'atr_multiplier': 2.0,
        'volume_ma': 20,
        'volume_mult': 1.5,
        'risk_percent': 0.025,  # 2.5% risk per trade
        'reward_risk_ratio': 2.0,
        'commission': 0.001,
        'initial_balance': margin,
        'lot_size': lot_size
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
    df['long_exit'] = df['trend_down'] | (df['rsi'] > 75)
    df['short_exit'] = df['trend_up'] | (df['rsi'] < 25)

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

            # Calculate position size based on lot size
            # For forex/gold: 1 lot = 100,000 units, 0.01 lot = 1,000 units
            # For crypto: 1 lot = 1 BTC, 0.01 lot = 0.01 BTC

            if row['long_signal']:
                position = params['lot_size']
                entry_price = price
                stop_loss = price - atr_sl
                take_profit = price + tp_dist

            elif row['short_signal']:
                position = -params['lot_size']
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
    print(f"Initial Balance: ${params['initial_balance']:.2f}")
    print(f"Final Balance:   ${balance:.2f}")
    print(f"Total Return:    {total_return:+.2f}%")
    print(f"Total Trades:    {total_trades}")
    print(f"Winning Trades:  {winning}")
    print(f"Losing Trades:   {losing}")
    print(f"Win Rate:        {win_rate:.1f}%")
    print(f"Profit Factor:   {profit_factor:.2f}")
    print(f"Avg Win:         ${avg_win:.2f}")
    print(f"Avg Loss:        ${avg_loss:.2f}")
    print(f"Max Drawdown:    {max_dd*100:.2f}%")
    print(f"Max Consecutive Losses: {max_consecutive_losses}")
    print(f"{'='*50}")

    # Rating
    if win_rate >= 50 and profit_factor >= 1.5:
        rating = "[EXCELLENT] - Meets 50%+ win rate goal!"
    elif win_rate >= 45 and profit_factor >= 1.2:
        rating = "[GOOD] - Close to target"
    elif win_rate >= 40 and profit_factor >= 1.0:
        rating = "[MODERATE] - Needs optimization"
    else:
        rating = "[POOR] - Needs improvement"

    print(f"Rating: {rating}")

    return {
        'symbol': symbol,
        'lot_size': lot_size,
        'margin': margin,
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

def main():
    """Main function"""
    print("="*60)
    print("CUSTOM STRATEGY - GOLD & BTC")
    print("Margin: $80, Lot Size: 0.01-0.02")
    print("="*60)

    # Test configurations
    configs = [
        # Gold (GC=F)
        {"symbol": "GC=F", "interval": "1h", "period": "6mo", "lot_size": 0.01, "margin": 80},
        {"symbol": "GC=F", "interval": "1h", "period": "6mo", "lot_size": 0.02, "margin": 80},

        # Bitcoin (BTC-USD)
        {"symbol": "BTC-USD", "interval": "1h", "period": "6mo", "lot_size": 0.01, "margin": 80},
        {"symbol": "BTC-USD", "interval": "1h", "period": "6mo", "lot_size": 0.02, "margin": 80},
    ]

    all_results = []

    for config in configs:
        try:
            result = custom_strategy_backtest(**config)
            if result:
                all_results.append(result)
            print()
        except Exception as e:
            print(f"Error testing {config['symbol']}: {e}\n")

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Symbol':<12} {'Lot':<6} {'Return':<10} {'Win Rate':<10} {'PF':<8} {'Trades':<8} {'Rating'}")
    print("-" * 60)

    for r in all_results:
        symbol_name = "GOLD" if "GC" in r['symbol'] else "BTC"
        print(f"{symbol_name:<12} {r['lot_size']:<6} {r['total_return']:+7.1f}%   {r['win_rate']:>6.1f}%   {r['profit_factor']:>5.2f}   {r['total_trades']:>6}   {r['rating']}")

    # Calculate average
    if all_results:
        avg_win_rate = sum(r['win_rate'] for r in all_results) / len(all_results)
        avg_return = sum(r['total_return'] for r in all_results) / len(all_results)
        avg_pf = sum(r['profit_factor'] for r in all_results) / len(all_results)

        print("-" * 60)
        print(f"{'AVERAGE':<12} {'':<6} {avg_return:+7.1f}%   {avg_win_rate:>6.1f}%   {avg_pf:>5.2f}")

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

    print("\n" + "="*60)
    print("STRATEGY RULES:")
    print("-" * 60)
    print("1. LONG Entry: EMA 7 > EMA 26 AND RSI < 40 AND High Volume")
    print("2. SHORT Entry: EMA 7 < EMA 26 AND RSI > 60 AND High Volume")
    print("3. Stop Loss: 2x ATR")
    print("4. Take Profit: 4x ATR (1:2 Risk:Reward)")
    print("5. Exit: Trend reversal OR RSI extreme")
    print("6. Max 3 consecutive losses before pause")
    print("="*60)

if __name__ == "__main__":
    main()
