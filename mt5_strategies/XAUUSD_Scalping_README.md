# Professional XAU/USD Scalping Trading Bot

A professional-grade algorithmic trading bot for XAU/USD (Gold) scalping on MetaTrader 5, implementing Smart Money Concepts (SMC), multi-timeframe analysis, and conservative risk management.

## 🎯 Features

### Core Trading Features
- **Multi-Timeframe Analysis**: H4 → H1 → M15 → M5 alignment
- **Smart Money Concepts (SMC)**: Order Blocks, Fair Value Gaps, Market Structure
- **Professional Entry System**: 4 entry types with signal scoring
- **Conservative Risk Management**: 0.5-1% risk per trade, daily/weekly loss limits
- **Partial Take Profit**: 40%/30%/20%/10% scaling for quick profits
- **Advanced Exit Management**: Trailing stops, breakeven, time-based exits

### Scalping-Specific Features
- **Session Analysis**: London/NY overlap focus for best volatility
- **Spread Control**: Max 30 points spread requirement
- **Overtrading Prevention**: Max 3 trades per hour, 2 max positions
- **Quick Profits**: Optimized for fast in-and-out trades

### Risk Management
- **Dynamic Position Sizing**: Based on ATR and account balance
- **ATR-Based Stop Loss**: 1.5× ATR for scalping
- **Structure-Based Stop Loss**: Below/above key levels
- **Daily Loss Limit**: 2% maximum
- **Weekly Loss Limit**: 5% maximum

## 📊 Strategy Overview

### Timeframe Hierarchy
```
H4 (4-Hour)    → Primary trend direction
H1 (1-Hour)    → Intermediate trend & key levels
M15 (15-Min)   → Entry timing & structure
M5 (5-Min)     → Precise entry & stop placement
```

### Signal Scoring System
| Component | Points | Description |
|-----------|--------|-------------|
| Trend Alignment | 20 | EMA alignment across timeframes |
| Market Structure | 15 | HH/HL or LH/LL patterns |
| Value Area | 15 | Order Blocks, FVG confluence |
| ADX Strength | 10 | Trend strength (>25) |
| RSI Condition | 10 | Momentum filter |
| Candlestick Patterns | 10 | Engulfing, Pinbar |
| Session Favorable | 5 | London/NY overlap bonus |

**Minimum Score Required**: 45/100 (configurable)

### Entry Types
1. **Pullback Entry**: Price returns to value area (OB, FVG, EMA)
2. **Breakout Entry**: Price breaks key level with confirmation
3. **Continuation Entry**: Inside bar/pinbar in trend direction
4. **Liquidity Sweep Entry**: Price sweeps stops then reverses

### Take Profit Strategy
```
TP1: 40% position at 0.5× R:R (Quick profit)
TP2: 30% position at 1.0× R:R (Breakeven)
TP3: 20% position at 1.5× R:R (Solid profit)
TP4: 10% position at 1.5-2.0× R:R (Runner)
```

## 🚀 Installation

### MT5 Expert Advisor

1. Copy `Professional_XAUUSD_Scalping_EA.mq5` to your MT5 Experts folder:
   ```
   C:\Program Files\MetaTrader 5\MQL5\Experts\
   ```

2. Compile the EA in MetaEditor (F7)

3. Attach to XAU/USD M5 chart

4. Configure parameters (see below)

### Python Backtester

1. Install dependencies:
   ```bash
   pip install yfinance pandas numpy matplotlib
   ```

2. Run the backtester:
   ```bash
   python backtest_professional_xauusd_scalping.py
   ```

## ⚙️ Configuration

### Scalping Timeframe Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| Primary_TF | H4 | Primary trend direction |
| Intermediate_TF | H1 | Intermediate trend |
| Entry_TF | M15 | Entry timing |
| Precision_TF | M5 | Precision entry |

### EMA Settings (Faster for Scalping)
| Parameter | Default | Description |
|-----------|---------|-------------|
| EMA_Fast | 9 | Fast EMA period |
| EMA_Slow | 21 | Slow EMA period |
| EMA_Trend | 50 | Trend EMA period |
| ADX_Period | 14 | ADX period |
| ADX_Threshold | 25 | Minimum ADX for trend |

### Entry Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| Min_Signal_Score | 45 | Minimum score to enter |
| Use_Pullback_Entry | true | Enable pullback entries |
| Use_Breakout_Entry | true | Enable breakout entries |
| Use_Continuation_Entry | true | Enable continuation entries |
| Use_Liquidity_Sweep_Entry | true | Enable liquidity sweep entries |

### Conservative Risk Management
| Parameter | Default | Description |
|-----------|---------|-------------|
| Risk_Percent | 0.75 | Risk per trade (0.5-1%) |
| Max_Daily_Loss_Percent | 2.0 | Max daily loss (2%) |
| Max_Weekly_Loss_Percent | 5.0 | Max weekly loss (5%) |
| Use_Dynamic_Lot | true | Use dynamic lot sizing |
| Use_ATR_SL | true | Use ATR-based stop loss |
| ATR_Multiplier | 1.5 | ATR multiplier for SL |
| Use_Structure_SL | true | Use structure-based SL |
| SL_Buffer_Pips | 5 | SL buffer (pips) |

### Take Profit Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| Risk_Reward_Ratio | 1.5 | Risk:Reward ratio |
| Use_Partial_TP | true | Use partial take profit |
| TP1_Percent | 40 | TP1 close percent |
| TP2_Percent | 30 | TP2 close percent |
| TP3_Percent | 20 | TP3 close percent |
| TP4_Percent | 10 | TP4 close percent |

### Session Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| Trade_Asian | false | Trade Asian session |
| Trade_London | true | Trade London session |
| Trade_NewYork | true | Trade New York session |
| Trade_Overlap | true | Trade London/NY overlap |

### Other Settings
| Parameter | Default | Description |
|-----------|---------|-------------|
| Magic_Number | 888888 | EA magic number |
| Max_Positions | 2 | Max open positions |
| Max_Spread | 30 | Max spread (points) |
| Max_Trades_Per_Hour | 3 | Max trades per hour |
| Min_Candles_Between_Trades | 3 | Min candles between trades |

## 📈 Trading Sessions

### Session Definitions (GMT)
| Session | Time (GMT) | Volatility | Recommended |
|---------|------------|------------|-------------|
| Asian | 00:00-08:00 | Low | ❌ Avoid |
| London | 08:00-16:00 | High | ✅ Good |
| New York | 13:00-21:00 | High | ✅ Good |
| Overlap | 13:00-16:00 | Very High | ⭐ Best |
| Off Hours | 21:00-00:00 | Very Low | ❌ Avoid |

**Note**: London/NY overlap (13:00-16:00 GMT) provides the best scalping conditions with high volatility and tight spreads.

## 🎓 Trading Principles

### Professional Approach
1. **Multi-Timeframe Alignment**: Never trade against higher timeframe trend
2. **Value Area Entries**: Wait for pullback to key levels
3. **Confluence**: Require multiple signals before entry
4. **Risk Management**: Never risk more than 1% per trade
5. **Session Awareness**: Focus on high-volatility periods

### Scalping Best Practices
1. **Spread Monitoring**: Only trade when spread < 30 points
2. **Quick Profits**: Use partial TP to lock gains early
3. **Tight Stops**: Scalping requires closer stops
4. **Overtrading Prevention**: Limit frequency to maintain quality
5. **Execution Speed**: Use VPS for low-latency execution

## 📊 Performance Metrics

### Target Metrics (Scalping + Conservative)
- **Win Rate**: > 45%
- **Profit Factor**: > 1.3
- **Max Drawdown**: < 15%
- **Average R:R**: > 1:1.5
- **Monthly Return**: > 3-5%
- **Average Trade Duration**: < 2 hours
- **Trades Per Day**: 3-8

## 🔧 Troubleshooting

### Common Issues

**No trades opening:**
- Check if spread is below Max_Spread
- Verify session filter allows current time
- Ensure signal score meets Min_Signal_Score
- Check daily/weekly loss limits

**High drawdown:**
- Reduce Risk_Percent
- Increase ATR_Multiplier
- Tighten session filter
- Increase Min_Signal_Score

**Too few trades:**
- Lower Min_Signal_Score
- Enable more entry types
- Expand session filter
- Reduce Min_Candles_Between_Trades

## 📝 Backtesting

### Using Python Backtester

```bash
python backtest_professional_xauusd_scalping.py
```

The backtester will:
1. Fetch XAU/USD historical data
2. Calculate all indicators
3. Simulate trades with realistic fills
4. Generate performance metrics
5. Plot equity curve

### Backtest Parameters

Modify parameters in `backtest_professional_xauusd_scalping.py`:

```python
self.params = {
    'min_signal_score': 45,
    'risk_percent': 0.75,
    'atr_multiplier': 1.5,
    # ... other parameters
}
```

## ⚠️ Risk Warning

**IMPORTANT**: This bot is for educational purposes. Trading involves significant risk of loss.

- **Start with demo account** for 1-3 months
- **Never risk more than you can afford to lose**
- **Backtest thoroughly** before live trading
- **Monitor performance** regularly
- **Adjust parameters** based on market conditions

## 📚 Additional Resources

### Recommended Reading
- *Smart Money Concepts* by ICT
- *Trading in the Zone* by Mark Douglas
- *The Disciplined Trader* by Mark Douglas

### Learning Resources
- Multi-timeframe analysis
- Order flow and market structure
- Risk management principles
- Trading psychology

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the backtest results
3. Verify parameter settings
4. Test on demo account first

## 📄 License

This project is provided as-is for educational purposes.

---

**Remember**: Professional trading is about consistency, not gambling. Follow the rules, manage risk, and stay disciplined.
