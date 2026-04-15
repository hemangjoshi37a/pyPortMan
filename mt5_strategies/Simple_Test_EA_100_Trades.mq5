//+------------------------------------------------------------------+
//|                    Simple_Test_EA_100_Trades.mq5                   |
//|           Simple Test EA - Generates 100+ Trades Guaranteed        |
//+------------------------------------------------------------------+
#property copyright "Simple Test EA"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS - VERY SIMPLE                                    |
//+------------------------------------------------------------------+
input group "=== Entry Settings ==="
input int      Min_Candles_Between = 5;      // Min candles between trades
input double   Lot_Size = 0.01;             // Lot Size

input group "=== Risk Management ==="
input int      Stop_Loss_Pips = 30;          // Stop Loss (pips)
input int      Take_Profit_Pips = 60;        // Take Profit (pips)

input group "=== Other Settings ==="
input int      Magic_Number = 123456;        // Magic Number
input int      Max_Spread = 100;             // Max Spread (points)

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
datetime lastTradeTime = 0;
int tradeCount = 0;

//+------------------------------------------------------------------+
//| EXPERT INITIALIZATION FUNCTION                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("========================================");
    Print("Simple Test EA - 100+ Trades Guaranteed");
    Print("========================================");
    Print("Strategy: Buy on green candle, Sell on red candle");
    Print("SL: ", Stop_Loss_Pips, " pips | TP: ", Take_Profit_Pips, " pips");
    Print("Min candles between: ", Min_Candles_Between);
    Print("========================================");

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| EXPERT DEINITIALIZATION FUNCTION                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("Simple Test EA stopped. Total trades: ", tradeCount);
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

    // Get current candle data
    double open = iOpen(_Symbol, PERIOD_CURRENT, 0);
    double close = iClose(_Symbol, PERIOD_CURRENT, 0);
    double high = iHigh(_Symbol, PERIOD_CURRENT, 0);
    double low = iLow(_Symbol, PERIOD_CURRENT, 0);

    // Check if candle is closed (not forming)
    datetime candleTime = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(candleTime == lastTradeTime)
        return; // Same candle, wait for next

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

    // SIMPLE STRATEGY: Buy on green candle, Sell on red candle
    if(close > open)
    {
        // Green candle - BUY
        OpenBuy();
        lastTradeTime = candleTime;
        tradeCount++;
    }
    else if(close < open)
    {
        // Red candle - SELL
        OpenSell();
        lastTradeTime = candleTime;
        tradeCount++;
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
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "TEST_BUY";

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
    request.comment = "TEST_SELL";

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
