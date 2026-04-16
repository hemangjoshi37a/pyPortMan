# MT5 Backtest Guide - Step by Step

## Step 1: EA File ko MT5 mein copy karo

1. MT5 open karo
2. Top menu se **File** → **Open Data Folder** click karo
3. **MQL5** folder open karo
4. **Experts** folder open karo
5. `EMA_SMC_Luxalgo_EA_v2.mq5` file yahan paste karo

## Step 2: EA Compile karo

1. MT5 mein **MetaEditor** open karo (F4 key dabao ya top menu se click karo)
2. MetaEditor mein left side se **Navigator** panel dekho
3. **Experts** folder expand karo
4. `EMA_SMC_Luxalgo_EA_v2` file double-click karo
5. Top menu se **Compile** button dabao (ya F7 key)
6. Bottom panel mein "0 errors" dekhna chahiye

## Step 3: Strategy Tester open karo

### Method 1: Keyboard Shortcut
- **Ctrl + R** dabao

### Method 2: Menu
- Top menu se **View** → **Strategy Tester** click karo

## Step 4: Backtest Settings karo

Strategy Tester panel mein yeh settings karo:

### Left Panel (Settings):

| Setting | Value |
|---------|-------|
| **Symbol** | XAUUSD ya BTC |
| **Timeframe** | M1 (1 minute) ya M5 (5 minute) |
| **Model** | Every tick (sabse accurate) |
| **Period** | Last year ya Custom date select karo |
| **Spread** | Current (ya manual 10-20) |

### Right Panel (Expert):

1. **Expert** dropdown se `EMA_SMC_Luxalgo_EA_v2` select karo
2. **Inputs** tab click karo
3. Yeh settings adjust karo:

```
=== EMA Settings ===
EMA_Period = 11
Use_EMA_Filter = false    // More trades ke liye false karo

=== SMC Settings ===
Swing_Lookback = 3
FVG_Min_Size = 5
OB_Lookback = 10
Use_Market_Structure = true
Use_Engulfing = true
Use_Pinbar = true

=== Signal Settings ===
Min_Signals = 1           // 1 = max signals
Use_Confluence = false

=== Risk Management ===
Lot_Size = 0.01
Stop_Loss_Pips = 30
Take_Profit_Pips = 60
Max_Spread = 50

=== Time Filter ===
Use_Time_Filter = false    // 24/7 trading ke liye false

=== Other Settings ===
Max_Positions = 5
Close_Opposite = true
Min_Candles_Between_Trades = 5
```

## Step 5: Backtest run karo

1. **Start** button dabao (green play icon)
2. Wait karo jab tak complete na ho jaye
3. Results tab mein results dekh sakte ho

## Step 6: Results dekho

### Results Tab:
- **Net Profit**: Total profit/loss
- **Total Trades**: Kitne trades hue
- **Profit Factor**: Risk/reward ratio
- **Drawdown**: Maximum loss
- **Recovery Factor**: Recovery from drawdown

### Equity Tab:
- Equity curve graph dekh sakte ho
- Green = profit, Red = loss

### Graphs Tab:
- Balance vs Equity chart
- Drawdown chart

## Step 7: Optimization (Optional)

Agar best settings dhundhna chahte ho:

1. Strategy Tester mein **Optimization** tab click karo
2. **Optimization criteria** select karo (e.g., Max Profit Factor)
3. Inputs tab mein parameters select karo jo optimize karna hai
4. **Start** button dabao
5. Results tab mein best results dekh sakte ho

## Common Issues & Solutions:

| Issue | Solution |
|-------|----------|
| "No trading operations" | Auto-trading ON karo (top toolbar) |
| EA not showing | Compile karo, file Experts folder mein hona chahiye |
| No trades | Min_Signals = 1 karo, Use_EMA_Filter = false |
| "Not enough money" | Lot_Size kam karo ya initial balance badhao |
| Spread too high | Max_Spread badhao |

## Quick Tips:

1. **First time**: Min_Signals = 1, Use_EMA_Filter = false se start karo
2. **Better results**: Timeframe M5 use karo
3. **Less noise**: Higher timeframe (M15, H1) try karo
4. **Risk management**: Lot_Size 0.01 se start karo

## Video Tutorial (Optional):

Agar video dekhna chahte ho:
1. YouTube search karo "MT5 Strategy Tester tutorial"
2. "How to backtest EA in MT5" videos dekho

---

Koi step mein problem aaye toh batao!
