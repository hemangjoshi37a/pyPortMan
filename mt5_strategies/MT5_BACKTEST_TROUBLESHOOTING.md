# MT5 Backtesting Troubleshooting Guide

## 🧪 Step 1: Test with Simple EA First

**Use `Simple_Test_EA_100_Trades.mq5`**

This EA uses the simplest possible logic:
- **BUY** on every green candle
- **SELL** on every red candle
- **SL**: 30 pips
- **TP**: 60 pips

**If this EA generates 0 trades, the issue is with your MT5 setup, not the strategy.**

---

## 🔍 MT5 Backtest Settings Checklist

### 1. Basic Settings
```
✅ Symbol: XAUUSD (or XAUUSDm, XAUUSD+, etc.)
✅ Model: "Every tick" (most accurate) or "Control points" (faster)
✅ Spread: Set to current spread or 0
✅ Timeframe: M5 (or M15, H1)
✅ Date Period: Last 3-6 months
```

### 2. Common Issues

| Issue | Solution |
|-------|----------|
| **0 trades** | Check if symbol data is available |
| **Wrong symbol** | Try XAUUSDm, XAUUSD+, or GC=F |
| **No data** | Download history data first |
| **Spread too high** | Set spread to 0 or current value |
| **Timeframe issue** | Try M15 or H1 instead of M5 |

### 3. Symbol Selection

**Try these symbols in order:**
1. `XAUUSD` - Standard
2. `XAUUSDm` - Micro lots
3. `XAUUSD+` - Zero spread
4. `GOLD` - Alternative
5. `GC=F` - Futures (if available)

---

## 📊 Step 2: Check Your Data

### How to verify data is available:

1. Open XAUUSD chart in MT5
2. Press **Home** key to download history
3. Check if you see candles on the chart
4. Try different timeframes (M5, M15, H1, H4, D1)

**If no candles appear:**
- Your broker doesn't provide XAUUSD data
- Try a different broker or symbol
- Use M1 or M5 timeframe (more data available)

---

## 🎯 Step 3: Test with Different Parameters

### For Professional_XAUUSD_Scalping_EA_v2.mq5

**Try these settings:**

```
=== Entry Settings ===
Min_Signal_Score = 15  (Lowered from 25)
Use_MultiTimeframe = false  (Disable for testing)

=== Session Settings ===
Use_Session_Filter = false  (Disable session filter)

=== Other Settings ===
Max_Spread = 100  (Increase spread limit)
Min_Candles_Between_Trades = 1  (Reduce cooldown)
```

---

## 🔧 Step 4: Common MT5 Backtest Issues

### Issue 1: "No trades" with complex EA

**Solution:** Start with Simple_Test_EA_100_Trades.mq5
- If it works → Your strategy is too strict
- If it doesn't work → MT5 setup issue

### Issue 2: Wrong Model Selection

**Models explained:**
- **Every tick**: Most accurate, slowest
- **Control points**: Faster, less accurate
- **Open prices only**: Fastest, least accurate

**Recommendation:** Use "Every tick" for testing

### Issue 3: Spread Setting

**If spread is set too high:**
- No trades will trigger
- Set to 0 or check current spread first

**How to check current spread:**
```
Right-click chart → Properties → Common → Show spread
```

### Issue 4: Timeframe Data Availability

**Some brokers don't provide M5 data for all symbols**

**Try these timeframes:**
- M1 (most data)
- M5
- M15
- H1
- H4
- D1

---

## 📋 Step 5: Backtest Procedure

### Correct Backtest Steps:

1. **Open Strategy Tester**
   - Press F4 or View → Strategy Tester

2. **Select EA**
   - Choose Simple_Test_EA_100_Trades.mq5 first

3. **Select Symbol**
   - XAUUSD (or try alternatives)

4. **Select Model**
   - Every tick

5. **Set Period**
   - Use "Use date" with last 3 months

6. **Set Spread**
   - Current or 0

7. **Click Start**

8. **Check Results Tab**
   - Look at "Total trades"
   - Look at "Net profit"

---

## 🚨 Step 6: If Still 0 Trades

### Try These Solutions:

**Solution A: Change Symbol**
```
Try: EURUSD, GBPUSD, USDJPY
If these work → XAUUSD data issue
If these don't work → MT5 setup issue
```

**Solution B: Change Timeframe**
```
Try: H1 or H4 instead of M5
Higher timeframes have more data
```

**Solution C: Download History**
```
1. Open XAUUSD chart
2. Press Home key multiple times
3. Wait for download to complete
4. Try backtest again
```

**Solution D: Check Broker**
```
Some brokers don't allow backtesting
Try demo account from different broker
```

---

## 📊 Step 7: Analyze Results

### If Simple Test EA Works:

**Expected results:**
- 100+ trades in 3 months
- Win rate around 50%
- Some profit/loss

**If this works:**
- Your MT5 setup is correct
- The issue is with the Professional EA being too strict

### If Simple Test EA Doesn't Work:

**Check these:**
1. Is the EA compiled? (F7 in MetaEditor)
2. Is the symbol correct?
3. Is there data on the chart?
4. Is the timeframe correct?
5. Is the model set correctly?

---

## 💡 Quick Fixes

### Fix 1: Disable All Filters
```mql5
Use_Session_Filter = false
Use_MultiTimeframe = false
Use_News_Filter = false
```

### Fix 2: Lower All Thresholds
```mql5
Min_Signal_Score = 10
ADX_Threshold = 15
Max_Spread = 200
```

### Fix 3: Enable All Sessions
```mql5
Trade_Asian = true
Trade_London = true
Trade_NewYork = true
Trade_Overlap = true
```

---

## 🎯 Final Checklist

Before running backtest:

```
□ EA compiled successfully (no errors)
□ Symbol has data on chart
□ Timeframe selected correctly
□ Model set to "Every tick"
□ Date period set correctly
□ Spread set to reasonable value
□ No conflicting EAs running
```

---

## 📞 Still Having Issues?

**Try this sequence:**

1. **Test with Simple_Test_EA_100_Trades.mq5**
   - If 0 trades → MT5 setup issue
   - If 100+ trades → Strategy too strict

2. **Check Experts tab**
   - Look for error messages
   - Check if EA is running

3. **Try different symbol**
   - EURUSD, GBPUSD, USDJPY
   - If these work → XAUUSD data issue

4. **Contact broker**
   - Ask about XAUUSD backtesting
   - Some brokers don't support it

---

## 🔍 Debug Mode in MT5

**Enable debug logging:**

1. Open MT5
2. Go to Tools → Options → Experts
3. Check "Enable debug logging"
4. Run backtest
5. Check Experts tab for messages

---

**Remember:** Start simple! If the basic test EA works, then gradually add complexity to find what's blocking trades.
