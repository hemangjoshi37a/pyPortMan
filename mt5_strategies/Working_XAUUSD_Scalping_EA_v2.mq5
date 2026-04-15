//+------------------------------------------------------------------+
//|              Working_XAUUSD_Scalping_EA_v2.mq5                      |
//|           WORKING VERSION v2 - Same logic as Ultra Simple            |
//+------------------------------------------------------------------+
#property copyright "Working XAU/USD Scalping EA v2"
#property version   "2.00"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                  |
//+------------------------------------------------------------------+
input group "=== Entry Settings ==="
input bool     Use_EMA_Filter = false;      // Use EMA Filter (DISABLED)
input bool     Use_Candle_Color = true;     // Use Candle Color (ENABLED)

// === EMA Settings ===
input group "=== EMA Settings ==="
input int      EMA_Fast = 9;              // Fast EMA
input int      EMA_Slow = 21;             // Slow EMA

// === Risk Management ===
input group "=== Risk Management ==="
input double   Lot_Size = 0.01;           // Lot Size
input int      Stop_Loss_Pips = 30;        // Stop Loss (pips)
input int      Take_Profit_Pips = 60;      // Take Profit (pips)

// === Other Settings ===
input group "=== Other Settings ==="
input int      Magic_Number = 888888;     // Magic Number
input int      Max_Spread = 200;           // Max Spread (points)
input int      Min_Candles_Between = 1;    // Min Candles Between

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
int emaFastHandle, emaSlowHandle;
double emaFastBuffer[], emaSlowBuffer[];
double highBuffer[], lowBuffer[], openBuffer[], closeBuffer[];

datetime lastTradeTime = 0;
int tradeCount = 0;
bool firstRun = true;

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
    Print("Working XAU/USD Scalping EA v2");
    Print("========================================");
    Print("Use EMA Filter: ", Use_EMA_Filter);
    Print("Use Candle Color: ", Use_Candle_Color);
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
    Print("Working EA v2 stopped. Total trades: ", tradeCount);
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
        Print("Point: ", _Point);
        Print("Digits: ", _Digits);
        Print("Spread: ", SymbolInfoInteger(_Symbol, SYMBOL_SPREAD));
        firstRun = false;
    }

    // Check spread
    long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
    if(spread > Max_Spread)
    {
        if(tradeCount == 0 && tradeCount % 100 == 0)
            Print("Spread too high: ", spread, " > ", Max_Spread);
        return;
    }

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

    // SIMPLE LOGIC: Alternate buy/sell like Ultra Simple
    static bool buyNext = true;

    if(buyNext)
    {
        // Check if we should buy
        bool shouldBuy = false;

        if(Use_Candle_Color)
        {
            // Buy on green candle
            if(closeBuffer[0] > openBuffer[0])
                shouldBuy = true;
        }

        if(Use_EMA_Filter)
        {
            // Buy if price above EMA
            if(closeBuffer[0] > emaFastBuffer[0])
                shouldBuy = true;
        }

        if(!Use_Candle_Color && !Use_EMA_Filter)
        {
            // Always buy
            shouldBuy = true;
        }

        if(shouldBuy)
        {
            OpenBuy();
            lastTradeTime = TimeCurrent();
            tradeCount++;
            buyNext = false;
        }
    }
    else
    {
        // Check if we should sell
        bool shouldSell = false;

        if(Use_Candle_Color)
        {
            // Sell on red candle
            if(closeBuffer[0] < openBuffer[0])
                shouldSell = true;
        }

        if(Use_EMA_Filter)
        {
            // Sell if price below EMA
            if(closeBuffer[0] < emaFastBuffer[0])
                shouldSell = true;
        }

        if(!Use_Candle_Color && !Use_EMA_Filter)
        {
            // Always sell
            shouldSell = true;
        }

        if(shouldSell)
        {
            OpenSell();
            lastTradeTime = TimeCurrent();
            tradeCount++;
            buyNext = true;
        }
    }
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
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "WORKING_BUY_v2";

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
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "WORKING_SELL_v2";

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
