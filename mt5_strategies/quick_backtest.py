"""
Quick Pine Script Backtest - Runs with default parameters
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def quick_backtest(symbol="BTC-USD", interval="1h", period="6mo"):
    """Run quick backtest with default parameters"""

    print(f"Testing {symbol} ({interval}, {period})...")
    print("-" * 50)

    # Fetch data
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval)

    if data.empty:
        print("No data found!")
        return

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

    # Handle different column names from yfinance
    if 'Datetime' in data.columns:
        data = data.rename(columns={'Datetime': 'datetime'})
    elif 'Date' in data.columns:
        data = data.rename(columns={'Date': 'datetime'})

    # Ensure we have the required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in data.columns:
            # Try to find the column with different case
            found = False
            for c in data.columns:
                if c.lower() == col:
                    data = data.rename(columns={c: col})
                    found = True
                    break
            if not found:
                raise ValueError(f"Column {col} not found in data")

    # Keep only needed columns
    cols_to_keep = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    data = data[cols_to_keep]

    # Parameters
    params = {
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
        'min_signal_score': 10,  # Lowered from 16 to get some trades
        'risk_percent': 0.01,
        'reward_risk_ratio': 2.0,
        'commission': 0.001,
        'initial_balance': 10000
    }

    # Calculate indicators
    df = data.copy()

    # EMA
    df['ema_fast'] = df['close'].ewm(span=params['ema_fast']).mean()
    df['ema_slow'] = df['close'].ewm(span=params['ema_slow']).mean()
    df['ema_trend'] = df['close'].ewm(span=params['ema_trend']).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=params['rsi_period']).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=params['rsi_period']).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = df['close'].ewm(span=params['macd_fast']).mean()
    exp2 = df['close'].ewm(span=params['macd_slow']).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=params['macd_signal']).mean()

    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=params['bb_period']).mean()
    bb_std = df['close'].rolling(window=params['bb_period']).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * params['bb_dev'])
    df['bb_lower'] = df['bb_middle'] - (bb_std * params['bb_dev'])

    # Stochastic
    low_min = df['low'].rolling(window=params['stoch_k']).min()
    high_max = df['high'].rolling(window=params['stoch_k']).max()
    df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['stoch_k'] = df['stoch_k'].rolling(window=params['stoch_d']).mean()

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
    atr = tr.rolling(window=params['adx_period']).mean()
    plus_di = 100 * (pd.Series(plus_dm).rolling(window=params['adx_period']).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(window=params['adx_period']).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    df['adx'] = dx.rolling(window=params['adx_period']).mean()

    # ATR
    df['atr'] = tr.rolling(window=14).mean()

    # Trend
    df['trend_up'] = (df['ema_fast'] > df['ema_slow']) & (df['close'] > df['ema_trend'])
    df['trend_down'] = (df['ema_fast'] < df['ema_slow']) & (df['close'] < df['ema_trend'])

    # EMA Cross
    df['ema_cross_up'] = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
    df['ema_cross_down'] = (df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))

    # RSI conditions
    df['rsi_oversold'] = df['rsi'] < params['rsi_oversold']
    df['rsi_overbought'] = df['rsi'] > params['rsi_overbought']
    df['rsi_bullish'] = (df['rsi'] > 50) & (df['rsi'] < params['rsi_overbought'])
    df['rsi_bearish'] = (df['rsi'] < 50) & (df['rsi'] > params['rsi_oversold'])

    # MACD conditions
    df['macd_bullish'] = df['macd'] > df['macd_signal']
    df['macd_bearish'] = df['macd'] < df['macd_signal']
    df['macd_cross_up'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['macd_cross_down'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    # BB conditions
    df['near_bb_lower'] = df['close'] <= df['bb_lower'] * 1.005
    df['near_bb_upper'] = df['close'] >= df['bb_upper'] * 0.995

    # Stoch conditions
    df['stoch_oversold'] = df['stoch_k'] < params['stoch_os']
    df['stoch_overbought'] = df['stoch_k'] > params['stoch_ob']
    df['stoch_cross_up'] = (df['stoch_k'] > params['stoch_os']) & (df['stoch_k'].shift(1) <= params['stoch_os'])
    df['stoch_cross_down'] = (df['stoch_k'] < params['stoch_ob']) & (df['stoch_k'].shift(1) >= params['stoch_ob'])

    # ADX conditions
    df['adx_strong'] = df['adx'] > params['adx_threshold']
    df['adx_up_trend'] = plus_di > minus_di
    df['adx_down_trend'] = minus_di > plus_di

    # Volume
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    df['high_volume'] = df['volume'] > df['vol_ma'] * 1.5
    df['vol_confirm_up'] = (df['close'] > df['close'].shift(1)) & df['high_volume']
    df['vol_confirm_down'] = (df['close'] < df['close'].shift(1)) & df['high_volume']

    # Market condition
    price_range = (df['high'].rolling(20).max() - df['low'].rolling(20).min()) / df['close']
    df['ranging_market'] = price_range < 0.02

    # Calculate signal scores
    def get_score(row, direction):
        score = 0
        if direction == 'buy':
            score += 2 if row['trend_up'] else (0 if not row['trend_down'] else -1)
            score += 3 if row['ema_cross_up'] else 0
            score += 2 if row['rsi_oversold'] else (1 if row['rsi_bullish'] else 0)
            score += 2 if row['macd_cross_up'] else (1 if row['macd_bullish'] else 0)
            score += 2 if row['near_bb_lower'] else 0
            score += 2 if row['stoch_oversold'] else 0
            score += 2 if row['stoch_cross_up'] else 0
            score += 2 if (row['adx_strong'] and row['adx_up_trend']) else 0
            score += 1 if row['vol_confirm_up'] else 0
        else:
            score += 2 if row['trend_down'] else (0 if not row['trend_up'] else -1)
            score += 3 if row['ema_cross_down'] else 0
            score += 2 if row['rsi_overbought'] else (1 if row['rsi_bearish'] else 0)
            score += 2 if row['macd_cross_down'] else (1 if row['macd_bearish'] else 0)
            score += 2 if row['near_bb_upper'] else 0
            score += 2 if row['stoch_overbought'] else 0
            score += 2 if row['stoch_cross_down'] else 0
            score += 2 if (row['adx_strong'] and row['adx_down_trend']) else 0
            score += 1 if row['vol_confirm_down'] else 0

        if row['ranging_market']:
            score -= 3
        return score

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

    # Debug: track max scores
    max_buy_score = 0
    max_sell_score = 0
    score_count = 0

    for i in range(50, len(df)):
        row = df.iloc[i]
        price = row['close']

        # Check exit
        if position != 0:
            if position > 0:
                if price <= stop_loss or price >= take_profit:
                    pnl = (price - entry_price) * position
                    comm = abs(position) * price * params['commission']
                    balance += pnl - comm
                    trades.append(pnl - comm)
                    if pnl > 0:
                        winning += 1
                        total_profit += pnl
                    else:
                        losing += 1
                        total_loss += abs(pnl)
                    position = 0
            else:
                if price >= stop_loss or price <= take_profit:
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
                    position = 0

        # Check entry
        if position == 0:
            buy_score = get_score(row, 'buy')
            sell_score = get_score(row, 'sell')

            # Debug: track max scores
            if buy_score > max_buy_score:
                max_buy_score = buy_score
            if sell_score > max_sell_score:
                max_sell_score = sell_score
            score_count += 1

            if buy_score >= params['min_signal_score']:
                atr_sl = row['atr'] * 2
                tp_dist = atr_sl * params['reward_risk_ratio']
                pos_size = (balance * params['risk_percent']) / atr_sl
                position = pos_size
                entry_price = price
                stop_loss = price - atr_sl
                take_profit = price + tp_dist
            elif sell_score >= params['min_signal_score']:
                atr_sl = row['atr'] * 2
                tp_dist = atr_sl * params['reward_risk_ratio']
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

    # Debug info
    print(f"Max Buy Score: {max_buy_score} (threshold: {params['min_signal_score']})")
    print(f"Max Sell Score: {max_sell_score} (threshold: {params['min_signal_score']})")
    print(f"Score samples: {score_count}")

    # Close remaining
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

    # Results
    total_trades = winning + losing
    win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
    total_return = (balance - params['initial_balance']) / params['initial_balance'] * 100

    print(f"\n{'='*50}")
    print("RESULTS")
    print(f"{'='*50}")
    print(f"Initial:  ${params['initial_balance']:,.2f}")
    print(f"Final:    ${balance:,.2f}")
    print(f"Return:   {total_return:+.2f}%")
    print(f"Trades:   {total_trades}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Max DD:   {max_dd*100:.2f}%")
    print(f"{'='*50}")

    if win_rate >= 50 and profit_factor >= 1.5:
        print("[GOOD] Strategy shows positive results")
    elif win_rate >= 40 and profit_factor >= 1.0:
        print("[MODERATE] Strategy needs optimization")
    else:
        print("[POOR] Strategy needs significant improvement")

    return {
        'symbol': symbol,
        'total_return': total_return,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd * 100,
        'total_trades': total_trades
    }

if __name__ == "__main__":
    # Test multiple symbols
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]

    print("PINE SCRIPT STRATEGY BACKTEST")
    print("="*50)

    all_results = []
    for sym in symbols:
        try:
            result = quick_backtest(sym, "1h", "3mo")
            all_results.append(result)
            print()
        except Exception as e:
            print(f"Error testing {sym}: {e}\n")

    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    for r in all_results:
        if r:
            print(f"{r['symbol']:10} | Return: {r['total_return']:+6.1f}% | Win: {r['win_rate']:5.1f}% | PF: {r['profit_factor']:.2f}")
