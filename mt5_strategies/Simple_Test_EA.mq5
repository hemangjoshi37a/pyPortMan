//+------------------------------------------------------------------+
//|                                    Simple_Test_EA.mq5           |
//|                        Simple EA for Testing - Guaranteed Trades|
//+------------------------------------------------------------------+
#property copyright "Test EA"
#property version   "1.00"
#property strict

//--- Input Parameters
input group "=== Settings ==="
input double   Lot_Size = 0.01;              // Lot Size
input int      Stop_Loss_Pips = 50;          // Stop Loss (pips)
input int      Take_Profit_Pips = 100;       // Take Profit (pips)
input int      Magic_Number = 999999;       // Magic Number
input int      Max_Positions = 3;            // Max Positions
input int      Candles_Between_Trades = 10;  // Min candles between trades

//--- Global Variables
datetime lastTradeTime = 0;
int tradeCount = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("Simple Test EA initialized - WILL GENERATE TRADES!");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("Test EA stopped. Total trades: ", tradeCount);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Count current positions
    int buyCount = 0;
    int sellCount = 0;

    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
                if(type == POSITION_TYPE_BUY) buyCount++;
                else if(type == POSITION_TYPE_SELL) sellCount++;
            }
        }
    }

    // Check if we can open new trade
    if(buyCount + sellCount >= Max_Positions)
        return;

    // Check minimum candles between trades
    if(lastTradeTime > 0)
    {
        int candlesSince = (int)((TimeCurrent() - lastTradeTime) / PeriodSeconds());
        if(candlesSince < Candles_Between_Trades)
            return;
    }

    // Get current candle data
    double open = iOpen(_Symbol, PERIOD_CURRENT, 0);
    double close = iClose(_Symbol, PERIOD_CURRENT, 0);
    double high = iHigh(_Symbol, PERIOD_CURRENT, 0);
    double low = iLow(_Symbol, PERIOD_CURRENT, 0);

    // Get previous candle data
    double prevOpen = iOpen(_Symbol, PERIOD_CURRENT, 1);
    double prevClose = iClose(_Symbol, PERIOD_CURRENT, 1);

    // SIMPLE STRATEGY: Buy on green candle, Sell on red candle
    // This WILL generate trades!

    // Buy signal: Current candle is green (close > open)
    if(close > open && buyCount < Max_Positions)
    {
        // Also check if previous was red (reversal)
        if(prevClose < prevOpen)
        {
            OpenBuy();
            lastTradeTime = TimeCurrent();
            tradeCount++;
        }
    }

    // Sell signal: Current candle is red (close < open)
    if(close < open && sellCount < Max_Positions)
    {
        // Also check if previous was green (reversal)
        if(prevClose > prevOpen)
        {
            OpenSell();
            lastTradeTime = TimeCurrent();
            tradeCount++;
        }
    }
}

//+------------------------------------------------------------------+
//| Open Buy Position                                                |
//+------------------------------------------------------------------+
void OpenBuy()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = ask - Stop_Loss_Pips * _Point * 10;
    double tp = ask + Take_Profit_Pips * _Point * 10;

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = Lot_Size;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "TEST_BUY";

    if(OrderSend(request, result))
        Print("TEST BUY opened at ", ask);
    else
        Print("BUY failed: ", GetLastError());
}

//+------------------------------------------------------------------+
//| Open Sell Position                                               |
//+------------------------------------------------------------------+
void OpenSell()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = bid + Stop_Loss_Pips * _Point * 10;
    double tp = bid - Take_Profit_Pips * _Point * 10;

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = Lot_Size;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "TEST_SELL";

    if(OrderSend(request, result))
        Print("TEST SELL opened at ", bid);
    else
        Print("SELL failed: ", GetLastError());
}
//+------------------------------------------------------------------+
