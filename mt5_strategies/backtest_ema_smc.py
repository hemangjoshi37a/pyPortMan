"""
EMA + SMC Luxalgo Backtest Script
Supports XAUUSD and BTC data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import mplfinance as mpf

class EMASMCBacktester:
    def __init__(self, df, ema_period=11,
                 sl_pips=50, tp_pips=100,
                 lot_size=0.01, initial_balance=10000):
        """
        Initialize backtester

        Parameters:
        - df: DataFrame with columns: datetime, open, high, low, close
        - ema_period: EMA period (default 11)
        - sl_pips: Stop loss in pips
        - tp_pips: Take profit in pips
        - lot_size: Lot size
        - initial_balance: Starting balance
        """
        self.df = df.copy()
        self.ema_period = ema_period
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.lot_size = lot_size
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions = []
        self.trades = []

        # Calculate indicators
        self.calculate_indicators()

    def calculate_indicators(self):
        """Calculate EMA and SMC indicators"""
        # EMA
        self.df['ema'] = self.df['close'].ewm(span=self.ema_period, adjust=False).mean()

        # Swing High/Low for Market Structure
        self.df['swing_high'] = self.df['high'].rolling(5, center=True).max() == self.df['high']
        self.df['swing_low'] = self.df['low'].rolling(5, center=True).min() == self.df['low']

        # FVG (Fair Value Gap)
        self.df['fvg_top'] = np.nan
        self.df['fvg_bottom'] = np.nan
        self.df['fvg_type'] = 0  # 1 = bullish, -1 = bearish

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

        # Order Blocks
        self.df['ob_top'] = np.nan
        self.df['ob_bottom'] = np.nan
        self.df['ob_type'] = 0

        for i in range(1, len(self.df)):
            # Bullish OB: bearish candle before strong bullish move
            if (self.df['close'].iloc[i] > self.df['open'].iloc[i] and
                self.df['close'].iloc[i] > self.df['high'].iloc[i-1] and
                self.df['close'].iloc[i-1] < self.df['open'].iloc[i-1]):
                self.df.loc[self.df.index[i], 'ob_top'] = self.df['open'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_bottom'] = self.df['close'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_type'] = 1

            # Bearish OB: bullish candle before strong bearish move
            elif (self.df['close'].iloc[i] < self.df['open'].iloc[i] and
                  self.df['close'].iloc[i] < self.df['low'].iloc[i-1] and
                  self.df['close'].iloc[i-1] > self.df['open'].iloc[i-1]):
                self.df.loc[self.df.index[i], 'ob_top'] = self.df['close'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_bottom'] = self.df['open'].iloc[i-1]
                self.df.loc[self.df.index[i], 'ob_type'] = -1

    def get_pip_value(self, symbol='XAUUSD'):
        """Get pip value for symbol"""
        if symbol == 'XAUUSD':
            return 0.01  # Gold: 0.01 = 1 pip
        elif symbol == 'BTCUSD':
            return 0.1   # BTC: 0.1 = 1 pip
        else:
            return 0.0001  # Forex pairs

    def run_backtest(self, symbol='XAUUSD'):
        """Run the backtest"""
        pip_value = self.get_pip_value(symbol)
        sl_distance = self.sl_pips * pip_value
        tp_distance = self.tp_pips * pip_value

        for i in range(50, len(self.df)):  # Start after EMA is calculated
            current_row = self.df.iloc[i]
            current_price = current_row['close']
            ema_value = current_row['ema']

            # Check existing positions
            self.check_positions(current_price, i)

            # EMA Filter
            price_above_ema = current_price > ema_value
            price_below_ema = current_price < ema_value

            # Check for Buy Signal
            if price_above_ema and len(self.positions) < 3:
                # FVG Buy Signal
                if (not pd.isna(current_row['fvg_bottom']) and
                    current_row['fvg_type'] == 1 and
                    current_price >= current_row['fvg_bottom'] and
                    current_price <= current_row['fvg_top']):
                    self.open_position('BUY', current_price, sl_distance, tp_distance, i)

                # OB Buy Signal
                elif (not pd.isna(current_row['ob_bottom']) and
                      current_row['ob_type'] == 1 and
                      current_price >= current_row['ob_bottom'] and
                      current_price <= current_row['ob_top']):
                    self.open_position('BUY', current_price, sl_distance, tp_distance, i)

            # Check for Sell Signal
            if price_below_ema and len(self.positions) < 3:
                # FVG Sell Signal
                if (not pd.isna(current_row['fvg_bottom']) and
                    current_row['fvg_type'] == -1 and
                    current_price >= current_row['fvg_bottom'] and
                    current_price <= current_row['fvg_top']):
                    self.open_position('SELL', current_price, sl_distance, tp_distance, i)

                # OB Sell Signal
                elif (not pd.isna(current_row['ob_bottom']) and
                      current_row['ob_type'] == -1 and
                      current_price >= current_row['ob_bottom'] and
                      current_price <= current_row['ob_top']):
                    self.open_position('SELL', current_price, sl_distance, tp_distance, i)

        # Close remaining positions
        for pos in self.positions[:]:
            self.close_position(pos, self.df['close'].iloc[-1], len(self.df) - 1, 'End of test')

        return self.get_results()

    def open_position(self, direction, entry_price, sl_distance, tp_distance, bar_index):
        """Open a new position"""
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
        """Check and update existing positions"""
        for pos in self.positions[:]:
            if pos['direction'] == 'BUY':
                # Check TP
                if current_price >= pos['tp']:
                    pnl = (pos['tp'] - pos['entry']) * self.lot_size * 100
                    self.close_position(pos, pos['tp'], bar_index, 'TP', pnl)
                # Check SL
                elif current_price <= pos['sl']:
                    pnl = (pos['sl'] - pos['entry']) * self.lot_size * 100
                    self.close_position(pos, pos['sl'], bar_index, 'SL', pnl)
            else:  # SELL
                # Check TP
                if current_price <= pos['tp']:
                    pnl = (pos['entry'] - pos['tp']) * self.lot_size * 100
                    self.close_position(pos, pos['tp'], bar_index, 'TP', pnl)
                # Check SL
                elif current_price >= pos['sl']:
                    pnl = (pos['entry'] - pos['sl']) * self.lot_size * 100
                    self.close_position(pos, pos['sl'], bar_index, 'SL', pnl)

    def close_position(self, position, exit_price, bar_index, reason, pnl=None):
        """Close a position"""
        if pnl is None:
            if position['direction'] == 'BUY':
                pnl = (exit_price - position['entry']) * self.lot_size * 100
            else:
                pnl = (position['entry'] - exit_price) * self.lot_size * 100

        self.balance += pnl
        self.equity = self.balance

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
        """Calculate and return backtest results"""
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

        # Calculate max drawdown
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

        # Profit factor
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

    def plot_results(self, results):
        """Plot backtest results"""
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))

        # Price chart with EMA
        ax1 = axes[0]
        ax1.plot(self.df['datetime'], self.df['close'], label='Price', alpha=0.7)
        ax1.plot(self.df['datetime'], self.df['ema'], label=f'EMA {self.ema_period}', color='orange')

        # Plot trades
        for trade in results['trades']:
            color = 'green' if trade['pnl'] > 0 else 'red'
            ax1.scatter(trade['entry_time'], trade['entry'], color=color, marker='^' if trade['direction'] == 'BUY' else 'v', s=100)

        ax1.set_title('Price Chart with EMA and Trades')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Equity curve
        ax2 = axes[1]
        ax2.plot(range(len(results['equity_curve'])), results['equity_curve'], color='blue', linewidth=2)
        ax2.axhline(y=self.initial_balance, color='gray', linestyle='--', label='Initial Balance')
        ax2.set_title('Equity Curve')
        ax2.set_xlabel('Trade Number')
        ax2.set_ylabel('Balance ($)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # Trade distribution
        ax3 = axes[2]
        pnl_values = [t['pnl'] for t in results['trades']]
        colors = ['green' if pnl > 0 else 'red' for pnl in pnl_values]
        ax3.bar(range(len(pnl_values)), pnl_values, color=colors)
        ax3.axhline(y=0, color='black', linestyle='-')
        ax3.set_title('Trade P&L Distribution')
        ax3.set_xlabel('Trade Number')
        ax3.set_ylabel('P&L ($)')
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('backtest_results.png', dpi=150)
        plt.show()

        print("\n" + "="*50)
        print("BACKTEST RESULTS")
        print("="*50)
        print(f"Total Trades: {results['total_trades']}")
        print(f"Winning Trades: {results['winning_trades']}")
        print(f"Losing Trades: {results['losing_trades']}")
        print(f"Win Rate: {results['win_rate']:.2f}%")
        print(f"Total P&L: ${results['total_pnl']:.2f}")
        print(f"Final Balance: ${results['final_balance']:.2f}")
        print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
        print(f"Profit Factor: {results['profit_factor']:.2f}")
        print(f"Average Win: ${results['avg_win']:.2f}")
        print(f"Average Loss: ${results['avg_loss']:.2f}")
        print("="*50)


def generate_sample_data(symbol='XAUUSD', days=30):
    """Generate sample OHLCV data for testing"""
    np.random.seed(42)

    dates = pd.date_range(end=datetime.now(), periods=days*24*60, freq='1min')  # 1-minute data

    if symbol == 'XAUUSD':
        base_price = 2300
        volatility = 0.001
    else:  # BTC
        base_price = 65000
        volatility = 0.002

    # Generate random walk
    returns = np.random.normal(0, volatility, len(dates))
    prices = base_price * (1 + returns).cumprod()

    # Create OHLC
    df = pd.DataFrame({'datetime': dates})
    df['close'] = prices
    df['open'] = df['close'].shift(1).fillna(base_price)
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, 0.001, len(df)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, 0.001, len(df)))

    return df


if __name__ == "__main__":
    # Generate sample data (replace with real data)
    print("Generating sample data...")
    df = generate_sample_data(symbol='XAUUSD', days=30)

    # Run backtest
    print("Running backtest...")
    backtester = EMASMCBacktester(
        df=df,
        ema_period=11,
        sl_pips=50,
        tp_pips=100,
        lot_size=0.01,
        initial_balance=10000
    )

    results = backtester.run_backtest(symbol='XAUUSD')

    # Plot and display results
    backtester.plot_results(results)

    # Save trades to CSV
    if results['trades']:
        trades_df = pd.DataFrame(results['trades'])
        trades_df.to_csv('trades.csv', index=False)
        print("\nTrades saved to trades.csv")
