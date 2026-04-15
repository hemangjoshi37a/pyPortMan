"""
EMA + SMC Luxalgo Backtest with DEBUG MODE
Shows why trades are/aren't being triggered
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class EMASMCBacktesterDebug:
    def __init__(self, df, ema_period=11,
                 sl_pips=50, tp_pips=100,
                 lot_size=0.01, initial_balance=10000,
                 debug=True):
        self.df = df.copy()
        self.ema_period = ema_period
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.lot_size = lot_size
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.debug = debug
        self.positions = []
        self.trades = []
        self.signals_log = []  # Log all signals

        self.calculate_indicators()

    def calculate_indicators(self):
        """Calculate EMA and SMC indicators"""
        # EMA
        self.df['ema'] = self.df['close'].ewm(span=self.ema_period, adjust=False).mean()

        # FVG (Fair Value Gap) - RELAXED CONDITIONS
        self.df['fvg_top'] = np.nan
        self.df['fvg_bottom'] = np.nan
        self.df['fvg_type'] = 0

        for i in range(2, len(self.df)):
            # Bullish FVG: gap between candle i-2 high and candle i low
            if self.df['low'].iloc[i] > self.df['high'].iloc[i-2]:
                self.df.loc[self.df.index[i], 'fvg_top'] = self.df['low'].iloc[i]
                self.df.loc[self.df.index[i], 'fvg_bottom'] = self.df['high'].iloc[i-2]
                self.df.loc[self.df.index[i], 'fvg_type'] = 1

            # Bearish FVG: gap between candle i-2 low and candle i high
            elif self.df['high'].iloc[i] < self.df['low'].iloc[i-2]:
                self.df.loc[self.df.index[i], 'fvg_top'] = self.df['low'].iloc[i-2]
                self.df.loc[self.df.index[i], 'fvg_bottom'] = self.df['high'].iloc[i]
                self.df.loc[self.df.index[i], 'fvg_type'] = -1

        # Order Blocks - RELAXED CONDITIONS
        self.df['ob_top'] = np.nan
        self.df['ob_bottom'] = np.nan
        self.df['ob_type'] = 0

        for i in range(1, len(self.df)):
            # Bullish OB: bearish candle before bullish move
            if (self.df['close'].iloc[i] > self.df['open'].iloc[i] and
                self.df['close'].iloc[i-1] < self.df['open'].iloc[i-1]):
                self.df.loc[self.df.index[i], 'ob_top'] = self.df['open'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_bottom'] = self.df['close'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_type'] = 1

            # Bearish OB: bullish candle before bearish move
            elif (self.df['close'].iloc[i] < self.df['open'].iloc[i] and
                  self.df['close'].iloc[i-1] > self.df['open'].iloc[i-1]):
                self.df.loc[self.df.index[i], 'ob_top'] = self.df['close'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_bottom'] = self.df['open'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_type'] = -1

        # Count signals
        fvg_count = (self.df['fvg_type'] != 0).sum()
        ob_count = (self.df['ob_type'] != 0).sum()
        print(f"📊 Indicators calculated:")
        print(f"   - FVG signals found: {fvg_count}")
        print(f"   - OB signals found: {ob_count}")

    def get_pip_value(self, symbol='XAUUSD'):
        if symbol == 'XAUUSD':
            return 0.01
        elif symbol == 'BTCUSD':
            return 0.1
        else:
            return 0.0001

    def run_backtest(self, symbol='XAUUSD'):
        pip_value = self.get_pip_value(symbol)
        sl_distance = self.sl_pips * pip_value
        tp_distance = self.tp_pips * pip_value

        buy_signals = 0
        sell_signals = 0
        blocked_by_ema = 0
        blocked_by_max_pos = 0

        print(f"\n🔍 Running backtest on {len(self.df)} candles...")

        for i in range(50, len(self.df)):
            current_row = self.df.iloc[i]
            current_price = current_row['close']
            ema_value = current_row['ema']

            # Check existing positions
            self.check_positions(current_price, i)

            # EMA Filter
            price_above_ema = current_price > ema_value
            price_below_ema = current_price < ema_value

            # Check for Buy Signal
            if len(self.positions) < 3:
                fvg_buy = False
                ob_buy = False

                # FVG Buy Signal
                if (not pd.isna(current_row['fvg_bottom']) and
                    current_row['fvg_type'] == 1 and
                    current_price >= current_row['fvg_bottom'] and
                    current_price <= current_row['fvg_top']):
                    fvg_buy = True

                # OB Buy Signal
                if (not pd.isna(current_row['ob_bottom']) and
                    current_row['ob_type'] == 1 and
                    current_price >= current_row['ob_bottom'] and
                    current_price <= current_row['ob_top']):
                    ob_buy = True

                if fvg_buy or ob_buy:
                    if price_above_ema:
                        buy_signals += 1
                        self.open_position('BUY', current_price, sl_distance, tp_distance, i)
                        if self.debug:
                            print(f"✅ BUY at {current_price:.2f} | FVG: {fvg_buy} | OB: {ob_buy} | EMA: {ema_value:.2f}")
                    else:
                        blocked_by_ema += 1
                        if self.debug and (fvg_buy or ob_buy):
                            print(f"❌ BUY blocked by EMA | Price: {current_price:.2f} | EMA: {ema_value:.2f}")
            else:
                if (not pd.isna(current_row['fvg_bottom']) and current_row['fvg_type'] == 1) or \
                   (not pd.isna(current_row['ob_bottom']) and current_row['ob_type'] == 1):
                    blocked_by_max_pos += 1

            # Check for Sell Signal
            if len(self.positions) < 3:
                fvg_sell = False
                ob_sell = False

                # FVG Sell Signal
                if (not pd.isna(current_row['fvg_bottom']) and
                    current_row['fvg_type'] == -1 and
                    current_price >= current_row['fvg_bottom'] and
                    current_price <= current_row['fvg_top']):
                    fvg_sell = True

                # OB Sell Signal
                if (not pd.isna(current_row['ob_bottom']) and
                    current_row['ob_type'] == -1 and
                    current_price >= current_row['ob_bottom'] and
                    current_price <= current_row['ob_top']):
                    ob_sell = True

                if fvg_sell or ob_sell:
                    if price_below_ema:
                        sell_signals += 1
                        self.open_position('SELL', current_price, sl_distance, tp_distance, i)
                        if self.debug:
                            print(f"✅ SELL at {current_price:.2f} | FVG: {fvg_sell} | OB: {ob_sell} | EMA: {ema_value:.2f}")
                    else:
                        blocked_by_ema += 1
                        if self.debug and (fvg_sell or ob_sell):
                            print(f"❌ SELL blocked by EMA | Price: {current_price:.2f} | EMA: {ema_value:.2f}")
            else:
                if (not pd.isna(current_row['fvg_bottom']) and current_row['fvg_type'] == -1) or \
                   (not pd.isna(current_row['ob_bottom']) and current_row['ob_type'] == -1):
                    blocked_by_max_pos += 1

        # Close remaining positions
        for pos in self.positions[:]:
            self.close_position(pos, self.df['close'].iloc[-1], len(self.df) - 1, 'End of test')

        # Print summary
        print(f"\n" + "="*50)
        print(f"📈 SIGNAL SUMMARY")
        print(f"="*50)
        print(f"Buy signals triggered: {buy_signals}")
        print(f"Sell signals triggered: {sell_signals}")
        print(f"Blocked by EMA filter: {blocked_by_ema}")
        print(f"Blocked by max positions: {blocked_by_max_pos}")
        print(f"Total trades executed: {len(self.trades)}")
        print(f"="*50)

        return self.get_results()

    def open_position(self, direction, entry_price, sl_distance, tp_distance, bar_index):
        if direction == 'BUY':
            sl = entry_price - sl_distance
            tp = entry_price + tp_distance
        else:
            sl = entry_price + sl_distance
            tp = entry_price - tp_distance

        position = {
            'direction': direction,
            'entry': entry_price,
            'sl': sl,
            'tp': tp,
            'entry_bar': bar_index,
            'entry_time': self.df['datetime'].iloc[bar_index]
        }
        self.positions.append(position)

    def check_positions(self, current_price, bar_index):
        for pos in self.positions[:]:
            if pos['direction'] == 'BUY':
                if current_price >= pos['tp']:
                    pnl = (pos['tp'] - pos['entry']) * self.lot_size * 100
                    self.close_position(pos, pos['tp'], bar_index, 'TP', pnl)
                elif current_price <= pos['sl']:
                    pnl = (pos['sl'] - pos['entry']) * self.lot_size * 100
                    self.close_position(pos, pos['sl'], bar_index, 'SL', pnl)
            else:
                if current_price <= pos['tp']:
                    pnl = (pos['entry'] - pos['tp']) * self.lot_size * 100
                    self.close_position(pos, pos['tp'], bar_index, 'TP', pnl)
                elif current_price >= pos['sl']:
                    pnl = (pos['entry'] - pos['sl']) * self.lot_size * 100
                    self.close_position(pos, pos['sl'], bar_index, 'SL', pnl)

    def close_position(self, position, exit_price, bar_index, reason, pnl=None):
        if pnl is None:
            if position['direction'] == 'BUY':
                pnl = (exit_price - position['entry']) * self.lot_size * 100
            else:
                pnl = (position['entry'] - exit_price) * self.lot_size * 100

        self.balance += pnl

        trade = {
            'direction': position['direction'],
            'entry': position['entry'],
            'exit': exit_price,
            'entry_time': position['entry_time'],
            'exit_time': self.df['datetime'].iloc[bar_index],
            'pnl': pnl,
            'reason': reason
        }
        self.trades.append(trade)
        self.positions.remove(position)

    def get_results(self):
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'final_balance': self.initial_balance,
                'max_drawdown': 0,
                'profit_factor': 0
            }

        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]

        win_rate = len(winning_trades) / total_trades * 100
        total_pnl = sum(t['pnl'] for t in self.trades)
        final_balance = self.initial_balance + total_pnl

        equity_curve = [self.initial_balance]
        for trade in self.trades:
            equity_curve.append(equity_curve[-1] + trade['pnl'])

        peak = equity_curve[0]
        max_drawdown = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'final_balance': final_balance,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0,
            'trades': self.trades,
            'equity_curve': equity_curve
        }


def generate_sample_data(symbol='XAUUSD', days=30):
    """Generate sample OHLCV data with MORE VOLATILITY"""
    np.random.seed(42)

    dates = pd.date_range(end=datetime.now(), periods=days*24*60, freq='1min')

    if symbol == 'XAUUSD':
        base_price = 2300
        volatility = 0.003  # Increased volatility
    else:
        base_price = 65000
        volatility = 0.005  # Increased volatility

    # Generate random walk with more movement
    returns = np.random.normal(0, volatility, len(dates))
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({'datetime': dates})
    df['close'] = prices
    df['open'] = df['close'].shift(1).fillna(base_price)
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, 0.002, len(df)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, 0.002, len(df)))

    print(f"📊 Generated {len(df)} candles of {symbol} data")
    print(f"   Price range: {df['low'].min():.2f} - {df['high'].max():.2f}")
    print(f"   Avg candle size: {(df['high'] - df['low']).mean():.2f}")

    return df


if __name__ == "__main__":
    print("="*50)
    print("EMA + SMC LUXALGO BACKTEST (DEBUG MODE)")
    print("="*50)

    # Generate sample data
    df = generate_sample_data(symbol='XAUUSD', days=30)

    # Run backtest with debug enabled
    backtester = EMASMCBacktesterDebug(
        df=df,
        ema_period=11,
        sl_pips=50,
        tp_pips=100,
        lot_size=0.01,
        initial_balance=10000,
        debug=True
    )

    results = backtester.run_backtest(symbol='XAUUSD')

    # Display results
    print(f"\n" + "="*50)
    print("FINAL RESULTS")
    print("="*50)
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Total P&L: ${results['total_pnl']:.2f}")
    print(f"Final Balance: ${results['final_balance']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print("="*50)

    if results['trades']:
        trades_df = pd.DataFrame(results['trades'])
        trades_df.to_csv('trades_debug.csv', index=False)
        print("\nTrades saved to trades_debug.csv")
