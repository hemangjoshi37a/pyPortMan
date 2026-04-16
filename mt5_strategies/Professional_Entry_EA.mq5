//+------------------------------------------------------------------+
//|              Professional_Entry_EA.mq5                             |
//|           Professional Entry Logic - Working Version                 |
//+------------------------------------------------------------------+
#property copyright "Professional Entry EA"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                  |
//+------------------------------------------------------------------+

// === Entry Strategy Selection ===
input group "=== Entry Strategy ==="
input int      Entry_Strategy = 1;         // 1=EMA Crossover, 2=Pullback, 3=Breakout, 4=RSI Reversal

// === EMA Settings ===
input group "=== EMA Settings ==="
input int      EMA_Fast = 9;              // Fast EMA
input int      EMA_Slow = 21;             // Slow EMA
input int      EMA_Trend = 50;            // Trend EMA

// === RSI Settings ===
input group "=== RSI Settings ==="
input int      RSI_Period = 14;           // RSI Period
input int      RSI_Oversold = 30;         // RSI Oversold
input int      RSI_Overbought = 70;       // RSI Overbought

// === Risk Management ===
input group "=== Risk Management ==="
input double   Lot_Size = 0.01;           // Lot Size
input int      Stop_Loss_Pips = 30;        // Stop Loss (pips)
input int      Take_Profit_Pips = 60;      // Take Profit (pips)

// === Other Settings ===
input group "=== Other Settings ==="
input int      Magic_Number = 888888;     // Magic Number
input int      Max_Spread = 100;           // Max Spread (points)
input int      Min_Candles_Between = 1;    // Min Candles Between

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
int emaFastHandle, emaSlowHandle, emaTrendHandle, rsiHandle;
double emaFastBuffer[], emaSlowBuffer[], emaTrendBuffer[], rsiBuffer[];
double highBuffer[], lowBuffer[], openBuffer[], closeBuffer[];

datetime lastTradeTime = 0;
int tradeCount = 0;
bool firstRun = true;

//+------------------------------------------------------------------+
//| EXPERT INITIALIZATION FUNCTION                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize indicators
    emaFastHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
    emaSlowHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
    emaTrendHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Trend, 0, MODE_EMA, PRICE_CLOSE);
    rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);

    if(emaFastHandle == INVALID_HANDLE || emaSlowHandle == INVALID_HANDLE ||
       emaTrendHandle == INVALID_HANDLE || rsiHandle == INVALID_HANDLE)
    {
        Print("Error creating indicators: ", GetLastError());
        return INIT_FAILED;
    }

    // Set arrays as series
    ArraySetAsSeries(emaFastBuffer, true);
    ArraySetAsSeries(emaSlowBuffer, true);
    ArraySetAsSeries(emaTrendBuffer, true);
    ArraySetAsSeries(rsiBuffer, true);
    ArraySetAsSeries(highBuffer, true);
    ArraySetAsSeries(lowBuffer, true);
    ArraySetAsSeries(openBuffer, true);
    ArraySetAsSeries(closeBuffer, true);

    Print("========================================");
    Print("Professional Entry EA");
    Print("========================================");
    Print("Entry Strategy: ", Entry_Strategy);
    Print("1 = EMA Crossover");
    Print("2 = EMA Pullback");
    Print("3 = Breakout");
    Print("4 = RSI Reversal");
    Print("========================================");

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
    if(rsiHandle != INVALID_HANDLE) IndicatorRelease(rsiHandle);
    Print("Professional Entry EA stopped. Total trades: ", tradeCount);
}

//+------------------------------------------------------------------+
//| EXPERT TICK FUNCTION                                              |
//+------------------------------------------------------------------+
void OnTick()
{
    // Print debug info on first run
    if(firstRun)
    {
        Print("First run - EA is working!");
        Print("Symbol: ", _Symbol);
        Print("Entry Strategy: ", Entry_Strategy);
        firstRun = false;
    }

    // Check spread
    long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
    if(spread > Max_Spread)
        return;

    // Get data
    int lookback = MathMax(MathMax(EMA_Trend, RSI_Period), 50) + 10;

    CopyBuffer(emaFastHandle, 0, 0, lookback, emaFastBuffer);
    CopyBuffer(emaSlowHandle, 0, 0, lookback, emaSlowBuffer);
    CopyBuffer(emaTrendHandle, 0, 0, lookback, emaTrendBuffer);
    CopyBuffer(rsiHandle, 0, 0, lookback, rsiBuffer);
    CopyHigh(_Symbol, PERIOD_CURRENT, 0, lookback, highBuffer);
    CopyLow(_Symbol, PERIOD_CURRENT, 0, lookback, lowBuffer);
    CopyOpen(_Symbol, PERIOD_CURRENT, 0, lookback, openBuffer);
    CopyClose(_Symbol, PERIOD_CURRENT, 0, lookback, closeBuffer);

    // Check minimum candles between trades
    if(lastTradeTime > 0)
    {
        int candlesSince = (int)((TimeCurrent() - lastTradeTime) / PeriodSeconds());
        if(candlesSince < Min_Candles_Between)
            return;
    }

    // Count current positions
    int totalPositions = 0;
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                totalPositions++;
            }
        }
    }

    // Only allow 1 position at a time
    if(totalPositions >= 1)
        return;

    // Check for signals based on strategy
    bool buySignal = false;
    bool sellSignal = false;
    string signalReason = "";

    switch(Entry_Strategy)
    {
        case 1: // EMA Crossover
            buySignal = CheckEMACrossoverBuy();
            sellSignal = CheckEMACrossoverSell();
            signalReason = "EMA Crossover";
            break;

        case 2: // EMA Pullback
            buySignal = CheckEMAPullbackBuy();
            sellSignal = CheckEMAPullbackSell();
            signalReason = "EMA Pullback";
            break;

        case 3: // Breakout
            buySignal = CheckBreakoutBuy();
            sellSignal = CheckBreakoutSell();
            signalReason = "Breakout";
            break;

        case 4: // RSI Reversal
            buySignal = CheckRSIReversalBuy();
            sellSignal = CheckRSIReversalSell();
            signalReason = "RSI Reversal";
            break;

        default:
            buySignal = CheckEMACrossoverBuy();
            sellSignal = CheckEMACrossoverSell();
            signalReason = "EMA Crossover (Default)";
            break;
    }

    // Execute trades
    if(buySignal)
    {
        OpenBuy(signalReason);
        lastTradeTime = TimeCurrent();
        tradeCount++;
    }
    else if(sellSignal)
    {
        OpenSell(signalReason);
        lastTradeTime = TimeCurrent();
        tradeCount++;
    }
}

//+------------------------------------------------------------------+
//| STRATEGY 1: EMA Crossover                                         |
//+------------------------------------------------------------------+
bool CheckEMACrossoverBuy()
{
    // Buy when fast EMA crosses above slow EMA
    bool currentCrossUp = (emaFastBuffer[0] > emaSlowBuffer[0]);
    bool previousCrossDown = (emaFastBuffer[1] <= emaSlowBuffer[1]);

    return (currentCrossUp && previousCrossDown);
}

bool CheckEMACrossoverSell()
{
    // Sell when fast EMA crosses below slow EMA
    bool currentCrossDown = (emaFastBuffer[0] < emaSlowBuffer[0]);
    bool previousCrossUp = (emaFastBuffer[1] >= emaSlowBuffer[1]);

    return (currentCrossDown && previousCrossUp);
}

//+------------------------------------------------------------------+
//| STRATEGY 2: EMA Pullback                                         |
//+------------------------------------------------------------------+
bool CheckEMAPullbackBuy()
{
    // Buy when price pulls back to EMA in uptrend
    bool uptrend = (emaFastBuffer[0] > emaTrendBuffer[0]);
    bool priceNearEMA = (closeBuffer[0] < emaFastBuffer[0]) && (closeBuffer[0] > emaFastBuffer[0] - (20 * _Point));
    bool greenCandle = (closeBuffer[0] > openBuffer[0]);

    return (uptrend && priceNearEMA && greenCandle);
}

bool CheckEMAPullbackSell()
{
    // Sell when price pulls back to EMA in downtrend
    bool downtrend = (emaFastBuffer[0] < emaTrendBuffer[0]);
    bool priceNearEMA = (closeBuffer[0] > emaFastBuffer[0]) && (closeBuffer[0] < emaFastBuffer[0] + (20 * _Point));
    bool redCandle = (closeBuffer[0] < openBuffer[0]);

    return (downtrend && priceNearEMA && redCandle);
}

//+------------------------------------------------------------------+
//| STRATEGY 3: Breakout                                               |
//+------------------------------------------------------------------+
bool CheckBreakoutBuy()
{
    // Buy when price breaks above recent high
    double recentHigh = highBuffer[ArrayMaximum(highBuffer, 20, 0)];
    bool breakout = (closeBuffer[0] > recentHigh);
    bool greenCandle = (closeBuffer[0] > openBuffer[0]);

    return (breakout && greenCandle);
}

bool CheckBreakoutSell()
{
    // Sell when price breaks below recent low
    double recentLow = lowBuffer[ArrayMinimum(lowBuffer, 20, 0)];
    bool breakdown = (closeBuffer[0] < recentLow);
    bool redCandle = (closeBuffer[0] < openBuffer[0]);

    return (breakdown && redCandle);
}

//+------------------------------------------------------------------+
//| STRATEGY 4: RSI Reversal                                          |
//+------------------------------------------------------------------+
bool CheckRSIReversalBuy()
{
    // Buy when RSI is oversold and candle turns green
    bool oversold = (rsiBuffer[0] < RSI_Oversold);
    bool rsiTurningUp = (rsiBuffer[0] > rsiBuffer[1]);
    bool greenCandle = (closeBuffer[0] > openBuffer[0]);

    return (oversold && rsiTurningUp && greenCandle);
}

bool CheckRSIReversalSell()
{
    // Sell when RSI is overbought and candle turns red
    bool overbought = (rsiBuffer[0] > RSI_Overbought);
    bool rsiTurningDown = (rsiBuffer[0] < rsiBuffer[1]);
    bool redCandle = (closeBuffer[0] < openBuffer[0]);

    return (overbought && rsiTurningDown && redCandle);
}

//+------------------------------------------------------------------+
//| OPEN BUY POSITION                                                 |
//+------------------------------------------------------------------+
void OpenBuy(string reason)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = ask - (Stop_Loss_Pips * _Point * 10);
    double tp = ask + (Take_Profit_Pips * _Point * 10);

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = Lot_Size;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "PRO_BUY_" + reason;

    if(OrderSend(request, result))
    {
        Print("✅ BUY [", reason, "] at ", ask, " | SL: ", sl, " | TP: ", tp, " | Trade #", tradeCount);
    }
    else
    {
        Print("❌ BUY failed: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| OPEN SELL POSITION                                                |
//+------------------------------------------------------------------+
void OpenSell(string reason)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = bid + (Stop_Loss_Pips * _Point * 10);
    double tp = bid - (Take_Profit_Pips * _Point * 10);

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = Lot_Size;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "PRO_SELL_" + reason;

    if(OrderSend(request, result))
    {
        Print("✅ SELL [", reason, "] at ", bid, " | SL: ", sl, " | TP: ", tp, " | Trade #", tradeCount);
    }
    else
    {
        Print("❌ SELL failed: ", GetLastError());
    }
}
//+------------------------------------------------------------------+
