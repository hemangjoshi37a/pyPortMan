//+------------------------------------------------------------------+
//|              Working_XAUUSD_Scalping_EA.mq5                        |
//|           WORKING VERSION - More Lenient Settings                   |
//+------------------------------------------------------------------+
#property copyright "Working XAU/USD Scalping EA"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS - WORKING SETTINGS                               |
//+------------------------------------------------------------------+

// === Entry Settings ===
input group "=== Entry Settings ==="
input int      Min_Signal_Score = 10;      // Minimum Signal Score (VERY LOW)
input bool     Use_EMA_Filter = true;       // Use EMA Filter
input bool     Use_RSI_Filter = false;      // Use RSI Filter (DISABLED)
input bool     Use_Session_Filter = false;  // Use Session Filter (DISABLED)
input bool     Use_MultiTimeframe = false;  // Use Multi-Timeframe (DISABLED)

// === EMA Settings ===
input group "=== EMA Settings ==="
input int      EMA_Fast = 9;              // Fast EMA
input int      EMA_Slow = 21;             // Slow EMA

// === Risk Management ===
input group "=== Risk Management ==="
input double   Lot_Size = 0.01;           // Lot Size
input int      Stop_Loss_Pips = 30;        // Stop Loss (pips)
input int      Take_Profit_Pips = 60;      // Take Profit (pips)
input bool     Use_Trailing_Stop = false;  // Trailing Stop (DISABLED)

// === Other Settings ===
input group "=== Other Settings ==="
input int      Magic_Number = 888888;     // Magic Number
input int      Max_Spread = 100;           // Max Spread (points)
input int      Min_Candles_Between = 1;    // Min Candles Between (VERY LOW)

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
int emaFastHandle, emaSlowHandle;
double emaFastBuffer[], emaSlowBuffer[];
double highBuffer[], lowBuffer[], openBuffer[], closeBuffer[];

datetime lastTradeTime = 0;
int tradeCount = 0;

//+------------------------------------------------------------------+
//| EXPERT INITIALIZATION FUNCTION                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize EMA
    emaFastHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
    emaSlowHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Slow, 0, MODE_EMA, PRICE_CLOSE);

    if(emaFastHandle == INVALID_HANDLE || emaSlowHandle == INVALID_HANDLE)
    {
        Print("Error creating EMA: ", GetLastError());
        return INIT_FAILED;
    }

    // Set arrays as series
    ArraySetAsSeries(emaFastBuffer, true);
    ArraySetAsSeries(emaSlowBuffer, true);
    ArraySetAsSeries(highBuffer, true);
    ArraySetAsSeries(lowBuffer, true);
    ArraySetAsSeries(openBuffer, true);
    ArraySetAsSeries(closeBuffer, true);

    Print("========================================");
    Print("Working XAU/USD Scalping EA");
    Print("========================================");
    Print("Min Signal Score: ", Min_Signal_Score);
    Print("Use EMA Filter: ", Use_EMA_Filter);
    Print("Use Session Filter: ", Use_Session_Filter);
    Print("Use Multi-Timeframe: ", Use_MultiTimeframe);
    Print("Min Candles Between: ", Min_Candles_Between);
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
    Print("Working EA stopped. Total trades: ", tradeCount);
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
    if(Use_Session_Filter && !IsTradingTime())
        return;

    // Get data
    int lookback = MathMax(EMA_Slow, 50) + 10;

    CopyBuffer(emaFastHandle, 0, 0, lookback, emaFastBuffer);
    CopyBuffer(emaSlowHandle, 0, 0, lookback, emaSlowBuffer);
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

    // Calculate signal scores
    int buyScore = CalculateBuySignalScore();
    int sellScore = CalculateSellSignalScore();

    // Check buy signal
    if(buyScore >= Min_Signal_Score)
    {
        OpenBuy();
        lastTradeTime = TimeCurrent();
        tradeCount++;
    }
    // Check sell signal
    else if(sellScore >= Min_Signal_Score)
    {
        OpenSell();
        lastTradeTime = TimeCurrent();
        tradeCount++;
    }
}

//+------------------------------------------------------------------+
//| CALCULATE BUY SIGNAL SCORE                                       |
//+------------------------------------------------------------------+
int CalculateBuySignalScore()
{
    int score = 0;
    double currentPrice = closeBuffer[0];

    // EMA Filter (10 points)
    if(Use_EMA_Filter)
    {
        if(currentPrice > emaFastBuffer[0])
            score += 5;
        if(emaFastBuffer[0] > emaSlowBuffer[0])
            score += 5;
    }
    else
    {
        score += 10; // Give full points if filter disabled
    }

    // Candle pattern (10 points)
    if(closeBuffer[0] > openBuffer[0])  // Green candle
        score += 10;

    // Session bonus (5 points)
    if(Use_Session_Filter && IsTradingTime())
        score += 5;
    else if(!Use_Session_Filter)
        score += 5; // Give points if filter disabled

    return score;
}

//+------------------------------------------------------------------+
//| CALCULATE SELL SIGNAL SCORE                                      |
//+------------------------------------------------------------------+
int CalculateSellSignalScore()
{
    int score = 0;
    double currentPrice = closeBuffer[0];

    // EMA Filter (10 points)
    if(Use_EMA_Filter)
    {
        if(currentPrice < emaFastBuffer[0])
            score += 5;
        if(emaFastBuffer[0] < emaSlowBuffer[0])
            score += 5;
    }
    else
    {
        score += 10; // Give full points if filter disabled
    }

    // Candle pattern (10 points)
    if(closeBuffer[0] < openBuffer[0])  // Red candle
        score += 10;

    // Session bonus (5 points)
    if(Use_Session_Filter && IsTradingTime())
        score += 5;
    else if(!Use_Session_Filter)
        score += 5; // Give points if filter disabled

    return score;
}

//+------------------------------------------------------------------+
//| OPEN BUY POSITION                                                 |
//+------------------------------------------------------------------+
void OpenBuy()
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
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "WORKING_BUY";

    if(OrderSend(request, result))
    {
        Print("✅ BUY at ", ask, " | SL: ", sl, " | TP: ", tp, " | Trade #", tradeCount);
    }
    else
    {
        Print("❌ BUY failed: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| OPEN SELL POSITION                                                |
//+------------------------------------------------------------------+
void OpenSell()
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
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "WORKING_SELL";

    if(OrderSend(request, result))
    {
        Print("✅ SELL at ", bid, " | SL: ", sl, " | TP: ", tp, " | Trade #", tradeCount);
    }
    else
    {
        Print("❌ SELL failed: ", GetLastError());
    }
}

//+------------------------------------------------------------------+
//| IS TRADING TIME                                                  |
//+------------------------------------------------------------------+
bool IsTradingTime()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    int hour = dt.hour;

    // Allow all hours for now
    return true;
}
//+------------------------------------------------------------------+
