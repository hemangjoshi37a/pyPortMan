//+------------------------------------------------------------------+
//|                        Professional_XAUUSD_Scalping_EA.mq5       |
//|                    Professional XAU/USD Scalping Bot              |
//|                    Multi-Timeframe + SMC + Risk Management       |
//+------------------------------------------------------------------+
#property copyright "Professional XAU/USD Scalping Bot"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS - SCALPING OPTIMIZED                           |
//+------------------------------------------------------------------+

// === Scalping Timeframe Settings ===
input group "=== Scalping Timeframe Settings ==="
input bool     Use_MultiTimeframe = true;
input ENUM_TIMEFRAMES Primary_TF = PERIOD_H4;      // Primary Trend (H4)
input ENUM_TIMEFRAMES Intermediate_TF = PERIOD_H1;  // Intermediate (H1)
input ENUM_TIMEFRAMES Entry_TF = PERIOD_M15;        // Entry Timing (M15)
input ENUM_TIMEFRAMES Precision_TF = PERIOD_M5;     // Precision Entry (M5)

// === Scalping EMA Settings (Faster) ===
input group "=== Scalping EMA Settings ==="
input int      EMA_Fast = 9;          // Fast EMA (9)
input int      EMA_Slow = 21;         // Slow EMA (21)
input int      EMA_Trend = 50;        // Trend EMA (50)
input int      ADX_Period = 14;       // ADX Period
input int      ADX_Threshold = 25;    // ADX Threshold

// === Scalping Entry Settings ===
input group "=== Scalping Entry Settings ==="
input int      Min_Signal_Score = 45;  // Minimum Signal Score (45)
input bool     Use_Pullback_Entry = true;
input bool     Use_Breakout_Entry = true;
input bool     Use_Continuation_Entry = true;
input bool     Use_Liquidity_Sweep_Entry = true;

// === SMC Settings ===
input group "=== SMC Settings ==="
input int      Swing_Lookback = 3;           // Swing Lookback
input int      FVG_Min_Size = 5;             // FVG Minimum Size (pips)
input int      OB_Lookback = 10;             // Order Block Lookback
input bool     Use_Order_Blocks = true;      // Use Order Blocks
input bool     Use_FVG = true;               // Use Fair Value Gaps
input bool     Use_Market_Structure = true;  // Use Market Structure
input bool     Use_Engulfing = true;         // Use Engulfing Pattern
input bool     Use_Pinbar = true;            // Use Pinbar Pattern

// === Conservative Risk Management ===
input group "=== Conservative Risk Management ==="
input double   Risk_Percent = 0.75;           // Risk Per Trade (0.5-1%)
input double   Max_Daily_Loss_Percent = 2.0;  // Max Daily Loss (2%)
input double   Max_Weekly_Loss_Percent = 5.0; // Max Weekly Loss (5%)
input bool     Use_Dynamic_Lot = true;       // Use Dynamic Lot Sizing
input bool     Use_ATR_SL = true;            // Use ATR Stop Loss
input double   ATR_Multiplier = 1.5;         // ATR Multiplier (1.5)
input bool     Use_Structure_SL = true;      // Use Structure Stop Loss
input double   SL_Buffer_Pips = 5;            // SL Buffer (pips)
input int      Stop_Loss_Pips = 30;          // Fixed Stop Loss (pips)

// === Scalping Take Profit ===
input group "=== Scalping Take Profit ==="
input double   Risk_Reward_Ratio = 1.5;       // Risk:Reward Ratio (1.5)
input bool     Use_Partial_TP = true;        // Use Partial Take Profit
input double   TP1_Percent = 40;             // TP1 Close Percent (40%)
input double   TP2_Percent = 30;             // TP2 Close Percent (30%)
input double   TP3_Percent = 20;             // TP3 Close Percent (20%)
input double   TP4_Percent = 10;             // TP4 Close Percent (10%)
input int      Take_Profit_Pips = 45;        // Fixed Take Profit (pips)

// === Scalping Session Settings ===
input group "=== Scalping Session Settings ==="
input bool     Use_Session_Filter = true;
input bool     Trade_Asian = false;           // Trade Asian Session
input bool     Trade_London = true;           // Trade London Session
input bool     Trade_NewYork = true;          // Trade New York Session
input bool     Trade_Overlap = true;          // Trade London/NY Overlap

// === Scalping News Filter ===
input group "=== Scalping News Filter ==="
input bool     Use_News_Filter = true;
input int      News_Buffer_Minutes = 15;      // News Buffer (minutes)

// === Scalping Other Settings ===
input group "=== Scalping Other Settings ==="
input int      Magic_Number = 888888;
input int      Max_Positions = 2;             // Max Positions (2 for conservative)
input int      Max_Spread = 30;               // Max Spread (points)
input bool     Close_Opposite = true;         // Close Opposite on Signal
input int      Max_Trades_Per_Hour = 3;       // Max Trades Per Hour
input int      Min_Candles_Between_Trades = 3; // Min Candles Between Trades

// === Trailing Stop Settings ===
input group "=== Trailing Stop Settings ==="
input bool     Use_Trailing_Stop = true;
input double   Trailing_Stop_Pips = 20;       // Trailing Stop (pips)
input int      Trailing_Start_Pips = 30;      // Trailing Start (pips)

// === Breakeven Settings ===
input group "=== Breakeven Settings ==="
input bool     Use_Breakeven = true;
input int      Breakeven_Pips = 15;           // Breakeven After (pips)

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+

// Indicator Handles
int emaFastHandle, emaSlowHandle, emaTrendHandle;
int adxHandle, atrHandle, rsiHandle;

// Indicator Buffers
double emaFastBuffer[], emaSlowBuffer[], emaTrendBuffer[];
double adxBuffer[], atrBuffer[], rsiBuffer[];
double highBuffer[], lowBuffer[], openBuffer[], closeBuffer[];

// Multi-Timeframe Data
double h4_emaFast[], h4_emaSlow[], h4_emaTrend[];
double h4_high[], h4_low[], h4_close[];
double h1_emaFast[], h1_emaSlow[], h1_emaTrend[];
double h1_high[], h1_low[], h1_close[];
double m15_emaFast[], m15_emaSlow[], m15_emaTrend[];
double m15_high[], m15_low[], m15_close[];

// Structures
struct MarketStructure {
    bool isUptrend;
    bool isDowntrend;
    double lastSwingHigh;
    double lastSwingLow;
    datetime lastSwingHighTime;
    datetime lastSwingLowTime;
    double lastHigherLow;
    double lastLowerHigh;
};

struct ValueArea {
    double top;
    double bottom;
    double high;   // For OB detection
    double low;    // For OB detection
    datetime time;
    int type;  // 0=OB, 1=FVG, 2=EMA_ZONE, 3=STRUCTURE
    bool isValid;
    bool isBullish;
};

struct EntrySignal {
    int buyScore;
    int sellScore;
    double entryPrice;
    double stopLoss;
    double takeProfit1;
    double takeProfit2;
    double takeProfit3;
    double takeProfit4;
    string reason;
};

// Global Structure Instances
MarketStructure msH4, msH1, msM15;
ValueArea bullishOB, bearishOB, bullishFVG, bearishFVG;
EntrySignal currentSignal;

// Trading State
datetime lastTradeTime = 0;
int tradesThisHour = 0;
int lastHour = -1;
double dailyStartBalance = 0;
double weeklyStartBalance = 0;
datetime dailyResetTime = 0;
datetime weeklyResetTime = 0;

// Enums
enum TrendDirection { TREND_UNKNOWN, TREND_UP, TREND_DOWN, TREND_RANGING };
enum TradingSession { SESSION_ASIAN, SESSION_LONDON, SESSION_NEWYORK, SESSION_OVERLAP, SESSION_OFF_HOURS };

//+------------------------------------------------------------------+
//| EXPERT INITIALIZATION FUNCTION                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize Indicators
    emaFastHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
    emaSlowHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
    emaTrendHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE);
    adxHandle = iADX(_Symbol, PERIOD_CURRENT, ADX_Period);
    atrHandle = iATR(_Symbol, PERIOD_CURRENT, 14);
    rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, 14, PRICE_CLOSE);

    if(emaFastHandle == INVALID_HANDLE || emaSlowHandle == INVALID_HANDLE ||
       emaTrendHandle == INVALID_HANDLE || adxHandle == INVALID_HANDLE ||
       atrHandle == INVALID_HANDLE || rsiHandle == INVALID_HANDLE)
    {
        Print("Error creating indicators: ", GetLastError());
        return INIT_FAILED;
    }

    // Set arrays as series
    ArraySetAsSeries(emaFastBuffer, true);
    ArraySetAsSeries(emaSlowBuffer, true);
    ArraySetAsSeries(emaTrendBuffer, true);
    ArraySetAsSeries(adxBuffer, true);
    ArraySetAsSeries(atrBuffer, true);
    ArraySetAsSeries(rsiBuffer, true);
    ArraySetAsSeries(highBuffer, true);
    ArraySetAsSeries(lowBuffer, true);
    ArraySetAsSeries(openBuffer, true);
    ArraySetAsSeries(closeBuffer, true);

    // Initialize multi-timeframe arrays
    ArraySetAsSeries(h4_emaFast, true);
    ArraySetAsSeries(h4_emaSlow, true);
    ArraySetAsSeries(h4_emaTrend, true);
    ArraySetAsSeries(h4_high, true);
    ArraySetAsSeries(h4_low, true);
    ArraySetAsSeries(h4_close, true);

    ArraySetAsSeries(h1_emaFast, true);
    ArraySetAsSeries(h1_emaSlow, true);
    ArraySetAsSeries(h1_emaTrend, true);
    ArraySetAsSeries(h1_high, true);
    ArraySetAsSeries(h1_low, true);
    ArraySetAsSeries(h1_close, true);

    ArraySetAsSeries(m15_emaFast, true);
    ArraySetAsSeries(m15_emaSlow, true);
    ArraySetAsSeries(m15_emaTrend, true);
    ArraySetAsSeries(m15_high, true);
    ArraySetAsSeries(m15_low, true);
    ArraySetAsSeries(m15_close, true);

    // Initialize structures
    InitializeStructures();

    // Initialize daily/weekly tracking
    dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    weeklyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    dailyResetTime = TimeCurrent();
    weeklyResetTime = TimeCurrent();

    Print("Professional XAU/USD Scalping EA initialized");
    Print("Timeframes: H4=", Primary_TF, " H1=", Intermediate_TF, " M15=", Entry_TF, " M5=", Precision_TF);
    Print("Risk: ", Risk_Percent, "% per trade, Max Daily Loss: ", Max_Daily_Loss_Percent, "%");

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| EXPERT DEINITIALIZATION FUNCTION                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(emaFastHandle != INVALID_HANDLE) IndicatorRelease(emaFastHandle);
    if(emaSlowHandle != INVALID_HANDLE) IndicatorRelease(emaSlowHandle);
    if(emaTrendHandle != INVALID_HANDLE) IndicatorRelease(emaTrendHandle);
    if(adxHandle != INVALID_HANDLE) IndicatorRelease(adxHandle);
    if(atrHandle != INVALID_HANDLE) IndicatorRelease(atrHandle);
    if(rsiHandle != INVALID_HANDLE) IndicatorRelease(rsiHandle);

    Print("Professional XAU/USD Scalping EA stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| EXPERT TICK FUNCTION                                              |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check spread
    long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
    if(spread > Max_Spread)
        return;

    // Check session filter
    if(Use_Session_Filter && !IsTradingSession())
        return;

    // Check news filter
    if(Use_News_Filter && IsHighImpactNewsTime())
        return;

    // Check daily/weekly loss limits
    if(!CheckDailyLossLimit() || !CheckWeeklyLossLimit())
        return;

    // Update hourly trade counter
    UpdateHourlyCounter();

    // Check max trades per hour
    if(tradesThisHour >= Max_Trades_Per_Hour)
        return;

    // Get data for all timeframes
    int lookback = MathMax(MathMax(EMA_Trend, OB_Lookback), 50);

    // Current timeframe (M5) data
    CopyBuffer(emaFastHandle, 0, 0, lookback, emaFastBuffer);
    CopyBuffer(emaSlowHandle, 0, 0, lookback, emaSlowBuffer);
    CopyBuffer(emaTrendHandle, 0, 0, lookback, emaTrendBuffer);
    CopyBuffer(adxHandle, 0, 0, lookback, adxBuffer);
    CopyBuffer(atrHandle, 0, 0, lookback, atrBuffer);
    CopyBuffer(rsiHandle, 0, 0, lookback, rsiBuffer);
    CopyHigh(_Symbol, PERIOD_CURRENT, 0, lookback, highBuffer);
    CopyLow(_Symbol, PERIOD_CURRENT, 0, lookback, lowBuffer);
    CopyOpen(_Symbol, PERIOD_CURRENT, 0, lookback, openBuffer);
    CopyClose(_Symbol, PERIOD_CURRENT, 0, lookback, closeBuffer);

    // H4 data
    if(Use_MultiTimeframe)
    {
        CopyBuffer(iMA(_Symbol, PERIOD_H4, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, h4_emaFast);
        CopyBuffer(iMA(_Symbol, PERIOD_H4, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, h4_emaSlow);
        CopyBuffer(iMA(_Symbol, PERIOD_H4, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, h4_emaTrend);
        CopyHigh(_Symbol, PERIOD_H4, 0, lookback, h4_high);
        CopyLow(_Symbol, PERIOD_H4, 0, lookback, h4_low);
        CopyClose(_Symbol, PERIOD_H4, 0, lookback, h4_close);

        // H1 data
        CopyBuffer(iMA(_Symbol, PERIOD_H1, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, h1_emaFast);
        CopyBuffer(iMA(_Symbol, PERIOD_H1, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, h1_emaSlow);
        CopyBuffer(iMA(_Symbol, PERIOD_H1, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, h1_emaTrend);
        CopyHigh(_Symbol, PERIOD_H1, 0, lookback, h1_high);
        CopyLow(_Symbol, PERIOD_H1, 0, lookback, h1_low);
        CopyClose(_Symbol, PERIOD_H1, 0, lookback, h1_close);

        // M15 data
        CopyBuffer(iMA(_Symbol, PERIOD_M15, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, m15_emaFast);
        CopyBuffer(iMA(_Symbol, PERIOD_M15, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, m15_emaSlow);
        CopyBuffer(iMA(_Symbol, PERIOD_M15, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE), 0, 0, lookback, m15_emaTrend);
        CopyHigh(_Symbol, PERIOD_M15, 0, lookback, m15_high);
        CopyLow(_Symbol, PERIOD_M15, 0, lookback, m15_low);
        CopyClose(_Symbol, PERIOD_M15, 0, lookback, m15_close);
    }

    // Update market structures
    if(Use_MultiTimeframe)
    {
        UpdateMarketStructure(msH4, h4_high, h4_low, h4_close);
        UpdateMarketStructure(msH1, h1_high, h1_low, h1_close);
        UpdateMarketStructure(msM15, m15_high, m15_low, m15_close);
    }
    else
    {
        UpdateMarketStructure(msH1, highBuffer, lowBuffer, closeBuffer);
    }

    // Update SMC elements
    if(Use_Order_Blocks) UpdateOrderBlocks();
    if(Use_FVG) UpdateFVG();

    // Check for signals
    CheckForSignals();

    // Manage existing positions
    ManagePositions();
}

//+------------------------------------------------------------------+
//| INITIALIZE STRUCTURES                                             |
//+------------------------------------------------------------------+
void InitializeStructures()
{
    // Market Structures
    msH4.isUptrend = false;
    msH4.isDowntrend = false;
    msH4.lastSwingHigh = 0;
    msH4.lastSwingLow = 0;
    msH4.lastSwingHighTime = 0;
    msH4.lastSwingLowTime = 0;
    msH4.lastHigherLow = 0;
    msH4.lastLowerHigh = 0;

    msH1 = msH4;
    msM15 = msH4;

    // Value Areas
    bullishOB.isValid = false;
    bearishOB.isValid = false;
    bullishFVG.isValid = false;
    bearishFVG.isValid = false;

    // Entry Signal
    currentSignal.buyScore = 0;
    currentSignal.sellScore = 0;
}

//+------------------------------------------------------------------+
//| UPDATE MARKET STRUCTURE                                           |
//+------------------------------------------------------------------+
void UpdateMarketStructure(MarketStructure &ms, double &highArr[], double &lowArr[], double &closeArr[])
{
    int lookback = Swing_Lookback;
    if(ArraySize(highArr) < lookback * 2) return;

    for(int i = lookback; i < ArraySize(highArr) - lookback; i++)
    {
        bool isSwingHigh = true;
        bool isSwingLow = true;

        for(int j = 1; j <= lookback; j++)
        {
            if(highArr[i] <= highArr[i + j] || highArr[i] <= highArr[i - j])
                isSwingHigh = false;
            if(lowArr[i] >= lowArr[i + j] || lowArr[i] >= lowArr[i - j])
                isSwingLow = false;
        }

        if(isSwingHigh && highArr[i] > ms.lastSwingHigh)
        {
            ms.lastSwingHigh = highArr[i];
            ms.lastSwingHighTime = iTime(_Symbol, PERIOD_CURRENT, i);
        }

        if(isSwingLow && (ms.lastSwingLow == 0 || lowArr[i] < ms.lastSwingLow))
        {
            ms.lastSwingLow = lowArr[i];
            ms.lastSwingLowTime = iTime(_Symbol, PERIOD_CURRENT, i);
        }
    }

    // Determine trend direction
    if(ms.lastSwingHigh > 0 && ms.lastSwingLow > 0)
    {
        if(ms.lastSwingHighTime > ms.lastSwingLowTime)
        {
            ms.isUptrend = true;
            ms.isDowntrend = false;
            ms.lastHigherLow = ms.lastSwingLow;
        }
        else
        {
            ms.isUptrend = false;
            ms.isDowntrend = true;
            ms.lastLowerHigh = ms.lastSwingHigh;
        }
    }
}

//+------------------------------------------------------------------+
//| UPDATE ORDER BLOCKS                                               |
//+------------------------------------------------------------------+
void UpdateOrderBlocks()
{
    if(ArraySize(closeBuffer) < OB_Lookback + 2) return;

    // Bullish OB
    for(int i = 1; i < OB_Lookback; i++)
    {
        if(closeBuffer[i] > openBuffer[i] && closeBuffer[i + 1] < openBuffer[i + 1])
        {
            bullishOB.time = iTime(_Symbol, PERIOD_CURRENT, i + 1);
            bullishOB.high = openBuffer[i + 1];
            bullishOB.low = closeBuffer[i + 1];
            bullishOB.isBullish = true;
            bullishOB.isValid = true;
            bullishOB.type = 0;
            break;
        }
    }

    // Bearish OB
    for(int i = 1; i < OB_Lookback; i++)
    {
        if(closeBuffer[i] < openBuffer[i] && closeBuffer[i + 1] > openBuffer[i + 1])
        {
            bearishOB.time = iTime(_Symbol, PERIOD_CURRENT, i + 1);
            bearishOB.high = closeBuffer[i + 1];
            bearishOB.low = openBuffer[i + 1];
            bearishOB.isBullish = false;
            bearishOB.isValid = true;
            bearishOB.type = 0;
            break;
        }
    }
}

//+------------------------------------------------------------------+
//| UPDATE FAIR VALUE GAPS                                            |
//+------------------------------------------------------------------+
void UpdateFVG()
{
    if(ArraySize(lowBuffer) < 3) return;

    // Bullish FVG
    for(int i = 2; i < ArraySize(lowBuffer) - 1; i++)
    {
        if(lowBuffer[i] > highBuffer[i + 1])
        {
            double gapSize = (lowBuffer[i] - highBuffer[i + 1]) / _Point;
            if(gapSize >= FVG_Min_Size)
            {
                bullishFVG.time = iTime(_Symbol, PERIOD_CURRENT, i);
                bullishFVG.top = lowBuffer[i];
                bullishFVG.bottom = highBuffer[i + 1];
                bullishFVG.isBullish = true;
                bullishFVG.isValid = true;
                bullishFVG.type = 1;
                break;
            }
        }
    }

    // Bearish FVG
    for(int i = 2; i < ArraySize(highBuffer) - 1; i++)
    {
        if(highBuffer[i] < lowBuffer[i + 1])
        {
            double gapSize = (lowBuffer[i + 1] - highBuffer[i]) / _Point;
            if(gapSize >= FVG_Min_Size)
            {
                bearishFVG.time = iTime(_Symbol, PERIOD_CURRENT, i);
                bearishFVG.top = lowBuffer[i + 1];
                bearishFVG.bottom = highBuffer[i];
                bearishFVG.isBullish = false;
                bearishFVG.isValid = true;
                bearishFVG.type = 1;
                break;
            }
        }
    }
}

//+------------------------------------------------------------------+
//| CHECK FOR SIGNALS                                                 |
//+------------------------------------------------------------------+
void CheckForSignals()
{
    // Check minimum candles between trades
    if(lastTradeTime > 0)
    {
        int candlesSince = (int)((TimeCurrent() - lastTradeTime) / PeriodSeconds());
        if(candlesSince < Min_Candles_Between_Trades)
            return;
    }

    // Count current positions
    int buyCount = CountPositions(POSITION_TYPE_BUY);
    int sellCount = CountPositions(POSITION_TYPE_SELL);

    if(buyCount + sellCount >= Max_Positions)
        return;

    // Calculate signal scores
    currentSignal.buyScore = CalculateBuySignalScore();
    currentSignal.sellScore = CalculateSellSignalScore();

    // Check buy signal
    if(buyCount < Max_Positions && currentSignal.buyScore >= Min_Signal_Score)
    {
        if(Close_Opposite && sellCount > 0)
            ClosePositions(POSITION_TYPE_SELL);

        OpenBuyPosition();
        lastTradeTime = TimeCurrent();
        tradesThisHour++;
    }

    // Check sell signal
    if(sellCount < Max_Positions && currentSignal.sellScore >= Min_Signal_Score)
    {
        if(Close_Opposite && buyCount > 0)
            ClosePositions(POSITION_TYPE_BUY);

        OpenSellPosition();
        lastTradeTime = TimeCurrent();
        tradesThisHour++;
    }
}

//+------------------------------------------------------------------+
//| CALCULATE BUY SIGNAL SCORE                                       |
//+------------------------------------------------------------------+
int CalculateBuySignalScore()
{
    int score = 0;
    double currentPrice = closeBuffer[0];

    // 1. Trend Alignment (20 points)
    if(Use_MultiTimeframe)
    {
        // H4 trend
        if(msH4.isUptrend) score += 8;
        else if(msH4.isDowntrend) score -= 5;

        // H1 trend
        if(msH1.isUptrend) score += 7;
        else if(msH1.isDowntrend) score -= 3;

        // M15 trend
        if(msM15.isUptrend) score += 5;
        else if(msM15.isDowntrend) score -= 2;

        // EMA alignment
        if(currentPrice > emaFastBuffer[0] && emaFastBuffer[0] > emaSlowBuffer[0])
            score += 5;
    }
    else
    {
        if(currentPrice > emaFastBuffer[0] && emaFastBuffer[0] > emaSlowBuffer[0])
            score += 10;
    }

    // 2. Market Structure (15 points)
    if(Use_Market_Structure)
    {
        if(msH1.isUptrend) score += 8;
        if(msM15.isUptrend) score += 7;
    }

    // 3. Value Area Confluence (15 points)
    if(Use_Order_Blocks && bullishOB.isValid)
    {
        if(currentPrice >= bullishOB.low && currentPrice <= bullishOB.high)
            score += 8;
    }

    if(Use_FVG && bullishFVG.isValid)
    {
        if(currentPrice >= bullishFVG.bottom && currentPrice <= bullishFVG.top)
            score += 7;
    }

    // 4. ADX Strength (10 points)
    if(adxBuffer[0] > ADX_Threshold)
    {
        score += 10;
        if(adxBuffer[0] > 40) score += 2; // Extra for strong trend
    }

    // 5. RSI Condition (10 points)
    if(rsiBuffer[0] < 70 && rsiBuffer[0] > 30)
        score += 5;
    if(rsiBuffer[0] < 50)
        score += 5;

    // 6. Candlestick Patterns (10 points)
    if(Use_Engulfing && IsBullishEngulfing())
        score += 6;
    if(Use_Pinbar && IsBullishPinbar())
        score += 6;

    // 7. Session Favorable (5 points)
    if(Use_Session_Filter && IsTradingSession())
    {
        TradingSession session = GetCurrentSession();
        if(session == SESSION_OVERLAP)
            score += 5;
        else if(session == SESSION_LONDON || session == SESSION_NEWYORK)
            score += 3;
    }

    // 8. Volume Confirmation (5 points) - if available
    // Note: MT5 volume is tick volume, not real volume
    // This is a placeholder for future enhancement

    return score;
}

//+------------------------------------------------------------------+
//| CALCULATE SELL SIGNAL SCORE                                      |
//+------------------------------------------------------------------+
int CalculateSellSignalScore()
{
    int score = 0;
    double currentPrice = closeBuffer[0];

    // 1. Trend Alignment (20 points)
    if(Use_MultiTimeframe)
    {
        // H4 trend
        if(msH4.isDowntrend) score += 8;
        else if(msH4.isUptrend) score -= 5;

        // H1 trend
        if(msH1.isDowntrend) score += 7;
        else if(msH1.isUptrend) score -= 3;

        // M15 trend
        if(msM15.isDowntrend) score += 5;
        else if(msM15.isUptrend) score -= 2;

        // EMA alignment
        if(currentPrice < emaFastBuffer[0] && emaFastBuffer[0] < emaSlowBuffer[0])
            score += 5;
    }
    else
    {
        if(currentPrice < emaFastBuffer[0] && emaFastBuffer[0] < emaSlowBuffer[0])
            score += 10;
    }

    // 2. Market Structure (15 points)
    if(Use_Market_Structure)
    {
        if(msH1.isDowntrend) score += 8;
        if(msM15.isDowntrend) score += 7;
    }

    // 3. Value Area Confluence (15 points)
    if(Use_Order_Blocks && bearishOB.isValid)
    {
        if(currentPrice >= bearishOB.low && currentPrice <= bearishOB.high)
            score += 8;
    }

    if(Use_FVG && bearishFVG.isValid)
    {
        if(currentPrice >= bearishFVG.bottom && currentPrice <= bearishFVG.top)
            score += 7;
    }

    // 4. ADX Strength (10 points)
    if(adxBuffer[0] > ADX_Threshold)
    {
        score += 10;
        if(adxBuffer[0] > 40) score += 2; // Extra for strong trend
    }

    // 5. RSI Condition (10 points)
    if(rsiBuffer[0] > 30 && rsiBuffer[0] < 70)
        score += 5;
    if(rsiBuffer[0] > 50)
        score += 5;

    // 6. Candlestick Patterns (10 points)
    if(Use_Engulfing && IsBearishEngulfing())
        score += 6;
    if(Use_Pinbar && IsBearishPinbar())
        score += 6;

    // 7. Session Favorable (5 points)
    if(Use_Session_Filter && IsTradingSession())
    {
        TradingSession session = GetCurrentSession();
        if(session == SESSION_OVERLAP)
            score += 5;
        else if(session == SESSION_LONDON || session == SESSION_NEWYORK)
            score += 3;
    }

    return score;
}

//+------------------------------------------------------------------+
//| OPEN BUY POSITION                                                 |
//+------------------------------------------------------------------+
void OpenBuyPosition()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double atr = atrBuffer[0];

    // Calculate lot size
    double lot = Use_Dynamic_Lot ? CalculateDynamicLotSize(ask, true) : 0.01;

    // Calculate stop loss
    double sl;
    if(Use_ATR_SL)
    {
        sl = ask - (atr * ATR_Multiplier);
    }
    else if(Use_Structure_SL && msH1.lastHigherLow > 0)
    {
        sl = msH1.lastHigherLow - (SL_Buffer_Pips * _Point);
    }
    else
    {
        sl = ask - (Stop_Loss_Pips * _Point * 10);
    }

    // Calculate take profits
    double slDistance = ask - sl;
    double tp1 = ask + (slDistance * 0.5);  // Quick profit
    double tp2 = ask + slDistance;          // Breakeven
    double tp3 = ask + (slDistance * 1.5); // Solid profit
    double tp4 = ask + (slDistance * Risk_Reward_Ratio); // Full R:R

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = lot;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp4; // Main TP
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "PRO_SCALPING_BUY";

    if(OrderSend(request, result))
    {
        Print("BUY opened at ", ask, " | Lot: ", lot, " | SL: ", sl, " | TP: ", tp4);
        Print("Signal Score: ", currentSignal.buyScore, " | Reason: ", currentSignal.reason);

        // Store TP levels for partial close
        StoreTPLevels(result.order, tp1, tp2, tp3, tp4);
    }
    else
    {
        Print("BUY failed: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| OPEN SELL POSITION                                                |
//+------------------------------------------------------------------+
void OpenSellPosition()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double atr = atrBuffer[0];

    // Calculate lot size
    double lot = Use_Dynamic_Lot ? CalculateDynamicLotSize(bid, false) : 0.01;

    // Calculate stop loss
    double sl;
    if(Use_ATR_SL)
    {
        sl = bid + (atr * ATR_Multiplier);
    }
    else if(Use_Structure_SL && msH1.lastLowerHigh > 0)
    {
        sl = msH1.lastLowerHigh + (SL_Buffer_Pips * _Point);
    }
    else
    {
        sl = bid + (Stop_Loss_Pips * _Point * 10);
    }

    // Calculate take profits
    double slDistance = sl - bid;
    double tp1 = bid - (slDistance * 0.5);  // Quick profit
    double tp2 = bid - slDistance;          // Breakeven
    double tp3 = bid - (slDistance * 1.5); // Solid profit
    double tp4 = bid - (slDistance * Risk_Reward_Ratio); // Full R:R

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = lot;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp4; // Main TP
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "PRO_SCALPING_SELL";

    if(OrderSend(request, result))
    {
        Print("SELL opened at ", bid, " | Lot: ", lot, " | SL: ", sl, " | TP: ", tp4);
        Print("Signal Score: ", currentSignal.sellScore, " | Reason: ", currentSignal.reason);

        // Store TP levels for partial close
        StoreTPLevels(result.order, tp1, tp2, tp3, tp4);
    }
    else
    {
        Print("SELL failed: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| CALCULATE DYNAMIC LOT SIZE                                        |
//+------------------------------------------------------------------+
double CalculateDynamicLotSize(double price, bool isBuy)
{
    double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double riskAmount = accountBalance * (Risk_Percent / 100.0);
    double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

    double atr = atrBuffer[0];
    double slDistance;

    if(Use_ATR_SL)
    {
        slDistance = atr * ATR_Multiplier;
    }
    else
    {
        slDistance = Stop_Loss_Pips * _Point * 10;
    }

    double slInMoney = slDistance / tickSize * tickValue;
    if(slInMoney == 0) return 0.01;

    double lot = riskAmount / slInMoney;

    // Normalize to broker requirements
    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

    lot = MathFloor(lot / lotStep) * lotStep;
    lot = MathMax(lot, minLot);
    lot = MathMin(lot, maxLot);

    return lot;
}

//+------------------------------------------------------------------+
//| STORE TP LEVELS (for partial close)                               |
//+------------------------------------------------------------------+
void StoreTPLevels(ulong orderTicket, double tp1, double tp2, double tp3, double tp4)
{
    // Store TP levels in position comment for retrieval
    // Format: TP1:price|TP2:price|TP3:price|TP4:price
    string tpLevels = "TP1:" + DoubleToString(tp1, 5) + "|TP2:" + DoubleToString(tp2, 5) +
                      "|TP3:" + DoubleToString(tp3, 5) + "|TP4:" + DoubleToString(tp4, 5);

    // Find the position and update comment
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                MqlTradeRequest request = {};
                MqlTradeResult result = {};

                request.action = TRADE_ACTION_MODIFY;
                request.position = PositionGetInteger(POSITION_TICKET);
                request.symbol = _Symbol;
                request.sl = PositionGetDouble(POSITION_SL);
                request.tp = PositionGetDouble(POSITION_TP);
                request.comment = PositionGetString(POSITION_COMMENT) + "|" + tpLevels;

                if(!OrderSend(request, result))
                {
                    Print("Failed to store TP levels: ", GetLastError());
                }
                break;
            }
        }
    }
}

//+------------------------------------------------------------------+
//| MANAGE POSITIONS                                                   |
//+------------------------------------------------------------------+
void ManagePositions()
{
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                ulong ticket = PositionGetInteger(POSITION_TICKET);
                double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
                double currentSL = PositionGetDouble(POSITION_SL);
                double currentTP = PositionGetDouble(POSITION_TP);
                ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
                double volume = PositionGetDouble(POSITION_VOLUME);

                // Get current price
                double currentPrice = (posType == POSITION_TYPE_BUY) ?
                                     SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                                     SymbolInfoDouble(_Symbol, SYMBOL_ASK);

                // Check partial TP
                if(Use_Partial_TP)
                {
                    CheckPartialTP(ticket, posType, openPrice, currentPrice, volume);
                }

                // Check breakeven
                if(Use_Breakeven)
                {
                    CheckBreakeven(ticket, posType, openPrice, currentPrice, currentSL);
                }

                // Check trailing stop
                if(Use_Trailing_Stop)
                {
                    CheckTrailingStop(ticket, posType, openPrice, currentPrice, currentSL, currentTP);
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| CHECK PARTIAL TP                                                  |
//+------------------------------------------------------------------+
void CheckPartialTP(ulong ticket, ENUM_POSITION_TYPE posType, double openPrice, double currentPrice, double volume)
{
    // Parse TP levels from comment
    string comment = PositionGetString(POSITION_COMMENT);
    double tp1 = 0, tp2 = 0, tp3 = 0, tp4 = 0;

    // Simple parsing (in production, use more robust method)
    int pos1 = StringFind(comment, "TP1:");
    int pos2 = StringFind(comment, "TP2:");
    int pos3 = StringFind(comment, "TP3:");
    int pos4 = StringFind(comment, "TP4:");

    if(pos1 >= 0) tp1 = StringToDouble(StringSubstr(comment, pos1 + 4, 10));
    if(pos2 >= 0) tp2 = StringToDouble(StringSubstr(comment, pos2 + 4, 10));
    if(pos3 >= 0) tp3 = StringToDouble(StringSubstr(comment, pos3 + 4, 10));
    if(pos4 >= 0) tp4 = StringToDouble(StringSubstr(comment, pos4 + 4, 10));

    if(tp1 == 0) return; // No TP levels stored

    // Check TP1 (40% close)
    if(posType == POSITION_TYPE_BUY && currentPrice >= tp1)
    {
        ClosePartialPosition(ticket, volume * TP1_Percent / 100.0, "TP1");
    }
    else if(posType == POSITION_TYPE_SELL && currentPrice <= tp1)
    {
        ClosePartialPosition(ticket, volume * TP1_Percent / 100.0, "TP1");
    }

    // Check TP2 (30% close)
    if(posType == POSITION_TYPE_BUY && currentPrice >= tp2)
    {
        ClosePartialPosition(ticket, volume * TP2_Percent / 100.0, "TP2");
    }
    else if(posType == POSITION_TYPE_SELL && currentPrice <= tp2)
    {
        ClosePartialPosition(ticket, volume * TP2_Percent / 100.0, "TP2");
    }

    // Check TP3 (20% close)
    if(posType == POSITION_TYPE_BUY && currentPrice >= tp3)
    {
        ClosePartialPosition(ticket, volume * TP3_Percent / 100.0, "TP3");
    }
    else if(posType == POSITION_TYPE_SELL && currentPrice <= tp3)
    {
        ClosePartialPosition(ticket, volume * TP3_Percent / 100.0, "TP3");
    }
}

//+------------------------------------------------------------------+
//| CLOSE PARTIAL POSITION                                            |
//+------------------------------------------------------------------+
void ClosePartialPosition(ulong ticket, double volume, string reason)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    request.action = TRADE_ACTION_DEAL;
    request.position = ticket;
    request.symbol = _Symbol;
    request.volume = volume;
    request.type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ?
                   ORDER_TYPE_SELL : ORDER_TYPE_BUY;
    request.price = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ?
                   SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                   SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "PARTIAL_" + reason;

    if(OrderSend(request, result))
    {
        Print("Partial close: ", volume, " lots | Reason: ", reason);
    }
}

//+------------------------------------------------------------------+
//| CHECK BREAKEVEN                                                   |
//+------------------------------------------------------------------+
void CheckBreakeven(ulong ticket, ENUM_POSITION_TYPE posType, double openPrice, double currentPrice, double currentSL)
{
    double beDistance = Breakeven_Pips * _Point * 10;

    if(posType == POSITION_TYPE_BUY)
    {
        if(currentPrice - openPrice > beDistance && currentSL < openPrice)
        {
            ModifyPosition(ticket, openPrice + 1 * _Point, PositionGetDouble(POSITION_TP));
        }
    }
    else if(posType == POSITION_TYPE_SELL)
    {
        if(openPrice - currentPrice > beDistance && (currentSL > openPrice || currentSL == 0))
        {
            ModifyPosition(ticket, openPrice - 1 * _Point, PositionGetDouble(POSITION_TP));
        }
    }
}

//+------------------------------------------------------------------+
//| CHECK TRAILING STOP                                              |
//+------------------------------------------------------------------+
void CheckTrailingStop(ulong ticket, ENUM_POSITION_TYPE posType, double openPrice, double currentPrice, double currentSL, double currentTP)
{
    double trailDistance = Trailing_Stop_Pips * _Point * 10;
    double trailStart = Trailing_Start_Pips * _Point * 10;

    if(posType == POSITION_TYPE_BUY)
    {
        if(currentPrice - openPrice > trailStart)
        {
            double newSL = currentPrice - trailDistance;
            if(newSL > currentSL)
            {
                ModifyPosition(ticket, newSL, currentTP);
            }
        }
    }
    else if(posType == POSITION_TYPE_SELL)
    {
        if(openPrice - currentPrice > trailStart)
        {
            double newSL = currentPrice + trailDistance;
            if(newSL < currentSL || currentSL == 0)
            {
                ModifyPosition(ticket, newSL, currentTP);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| MODIFY POSITION                                                   |
//+------------------------------------------------------------------+
bool ModifyPosition(ulong ticket, double sl, double tp)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    request.action = TRADE_ACTION_SLTP;
    request.position = ticket;
    request.symbol = _Symbol;
    request.sl = sl;
    request.tp = tp;
    request.magic = Magic_Number;

    return OrderSend(request, result);
}

//+------------------------------------------------------------------+
//| COUNT POSITIONS                                                   |
//+------------------------------------------------------------------+
int CountPositions(ENUM_POSITION_TYPE type)
{
    int count = 0;
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number &&
               PositionGetInteger(POSITION_TYPE) == type)
            {
                count++;
            }
        }
    }
    return count;
}

//+------------------------------------------------------------------+
//| CLOSE POSITIONS                                                   |
//+------------------------------------------------------------------+
void ClosePositions(ENUM_POSITION_TYPE type)
{
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number &&
               PositionGetInteger(POSITION_TYPE) == type)
            {
                MqlTradeRequest request = {};
                MqlTradeResult result = {};

                request.action = TRADE_ACTION_DEAL;
                request.symbol = _Symbol;
                request.volume = PositionGetDouble(POSITION_VOLUME);
                request.type = (type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
                request.position = PositionGetInteger(POSITION_TICKET);
                request.price = (type == POSITION_TYPE_BUY) ?
                               SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                               SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                request.deviation = 10;
                request.magic = Magic_Number;

                if(!OrderSend(request, result))
                {
                    Print("Failed to close position: ", GetLastError());
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| IS BULLISH ENGULFING                                              |
//+------------------------------------------------------------------+
bool IsBullishEngulfing()
{
    if(ArraySize(closeBuffer) < 2) return false;

    return (closeBuffer[1] < openBuffer[1] &&
            closeBuffer[0] > openBuffer[0] &&
            closeBuffer[0] > openBuffer[1] &&
            openBuffer[0] < closeBuffer[1]);
}

//+------------------------------------------------------------------+
//| IS BEARISH ENGULFING                                              |
//+------------------------------------------------------------------+
bool IsBearishEngulfing()
{
    if(ArraySize(closeBuffer) < 2) return false;

    return (closeBuffer[1] > openBuffer[1] &&
            closeBuffer[0] < openBuffer[0] &&
            closeBuffer[0] < openBuffer[1] &&
            openBuffer[0] > closeBuffer[1]);
}

//+------------------------------------------------------------------+
//| IS BULLISH PINBAR                                                 |
//+------------------------------------------------------------------+
bool IsBullishPinbar()
{
    if(ArraySize(closeBuffer) < 1) return false;

    double body = MathAbs(closeBuffer[0] - openBuffer[0]);
    double upperWick = highBuffer[0] - MathMax(openBuffer[0], closeBuffer[0]);
    double lowerWick = MathMin(openBuffer[0], closeBuffer[0]) - lowBuffer[0];
    double totalRange = highBuffer[0] - lowBuffer[0];

    if(totalRange == 0) return false;

    return (closeBuffer[0] > openBuffer[0] &&
            lowerWick > body * 2 &&
            upperWick < body * 0.5);
}

//+------------------------------------------------------------------+
//| IS BEARISH PINBAR                                                 |
//+------------------------------------------------------------------+
bool IsBearishPinbar()
{
    if(ArraySize(closeBuffer) < 1) return false;

    double body = MathAbs(closeBuffer[0] - openBuffer[0]);
    double upperWick = highBuffer[0] - MathMax(openBuffer[0], closeBuffer[0]);
    double lowerWick = MathMin(openBuffer[0], closeBuffer[0]) - lowBuffer[0];
    double totalRange = highBuffer[0] - lowBuffer[0];

    if(totalRange == 0) return false;

    return (closeBuffer[0] < openBuffer[0] &&
            upperWick > body * 2 &&
            lowerWick < body * 0.5);
}

//+------------------------------------------------------------------+
//| IS TRADING SESSION                                                |
//+------------------------------------------------------------------+
bool IsTradingSession()
{
    TradingSession session = GetCurrentSession();

    switch(session)
    {
        case SESSION_ASIAN:
            return Trade_Asian;
        case SESSION_LONDON:
            return Trade_London;
        case SESSION_NEWYORK:
            return Trade_NewYork;
        case SESSION_OVERLAP:
            return Trade_Overlap;
        default:
            return false;
    }
}

//+------------------------------------------------------------------+
//| GET CURRENT SESSION                                               |
//+------------------------------------------------------------------+
TradingSession GetCurrentSession()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    int hour = dt.hour; // Server time (assuming GMT)

    // Adjust to GMT if needed
    // hour = (hour + gmtOffset) % 24;

    // Session definitions (GMT)
    // Asian: 00:00-08:00
    // London: 08:00-16:00
    // New York: 13:00-21:00
    // Overlap: 13:00-16:00

    if(hour >= 13 && hour < 16)
        return SESSION_OVERLAP;
    else if(hour >= 8 && hour < 16)
        return SESSION_LONDON;
    else if(hour >= 13 && hour < 21)
        return SESSION_NEWYORK;
    else if(hour >= 0 && hour < 8)
        return SESSION_ASIAN;
    else
        return SESSION_OFF_HOURS;
}

//+------------------------------------------------------------------+
//| IS HIGH IMPACT NEWS TIME                                          |
//+------------------------------------------------------------------+
bool IsHighImpactNewsTime()
{
    // Placeholder for news filter
    // In production, integrate with economic calendar API
    // For now, return false (no news filter)
    return false;
}

//+------------------------------------------------------------------+
//| CHECK DAILY LOSS LIMIT                                            |
//+------------------------------------------------------------------+
bool CheckDailyLossLimit()
{
    // Reset daily counter at start of new day
    MqlDateTime dt;
    MqlDateTime resetDt;
    TimeToStruct(TimeCurrent(), dt);
    TimeToStruct(dailyResetTime, resetDt);

    if(dt.day != resetDt.day || dt.mon != resetDt.mon || dt.year != resetDt.year)
    {
        dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
        dailyResetTime = TimeCurrent();
    }

    double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double dailyPnL = currentBalance - dailyStartBalance;
    double maxDailyLoss = dailyStartBalance * (Max_Daily_Loss_Percent / 100.0);

    if(dailyPnL < -maxDailyLoss)
    {
        Print("Daily loss limit reached. Stopping trading for the day.");
        return false;
    }

    return true;
}

//+------------------------------------------------------------------+
//| CHECK WEEKLY LOSS LIMIT                                           |
//+------------------------------------------------------------------+
bool CheckWeeklyLossLimit()
{
    // Reset weekly counter at start of new week
    MqlDateTime dt;
    MqlDateTime resetDt;
    TimeToStruct(TimeCurrent(), dt);
    TimeToStruct(weeklyResetTime, resetDt);

    // Check if new week (Monday = 0, Sunday = 6)
    // Reset if current day is earlier in week than reset day (week rolled over)
    if(dt.day_of_week < resetDt.day_of_week ||
       (dt.day_of_week == 0 && resetDt.day_of_week > 0) ||  // Monday after Sunday
       (dt.day != resetDt.day && dt.mon != resetDt.mon))  // Different month
    {
        weeklyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
        weeklyResetTime = TimeCurrent();
    }

    double currentBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double weeklyPnL = currentBalance - weeklyStartBalance;
    double maxWeeklyLoss = weeklyStartBalance * (Max_Weekly_Loss_Percent / 100.0);

    if(weeklyPnL < -maxWeeklyLoss)
    {
        Print("Weekly loss limit reached. Stopping trading for the week.");
        return false;
    }

    return true;
}

//+------------------------------------------------------------------+
//| UPDATE HOURLY COUNTER                                             |
//+------------------------------------------------------------------+
void UpdateHourlyCounter()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);

    if(dt.hour != lastHour)
    {
        tradesThisHour = 0;
        lastHour = dt.hour;
    }
}

//+------------------------------------------------------------------+
