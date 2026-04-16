//+------------------------------------------------------------------+
//|                  One_Trade_Test_EA.mq5                            |
//|           Test EA - Enter ONE buy order only                      |
//+------------------------------------------------------------------+
#property copyright "One Trade Test EA"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                  |
//+------------------------------------------------------------------+
input double   Lot_Size = 0.01;             // Lot Size
input int      Stop_Loss_Pips = 50;          // Stop Loss (pips)
input int      Take_Profit_Pips = 100;       // Take Profit (pips)
input int      Magic_Number = 777777;        // Magic Number

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
bool orderPlaced = false;

//+------------------------------------------------------------------+
//| EXPERT INITIALIZATION FUNCTION                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("========================================");
    Print("ONE TRADE TEST EA");
    Print("========================================");
    Print("This EA will place ONE buy order only!");
    Print("Lot Size: ", Lot_Size);
    Print("SL: ", Stop_Loss_Pips, " pips | TP: ", Take_Profit_Pips, " pips");
    Print("========================================");

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| EXPERT DEINITIALIZATION FUNCTION                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("One Trade Test EA stopped");
}

//+------------------------------------------------------------------+
//| EXPERT TICK FUNCTION                                              |
//+------------------------------------------------------------------+
void OnTick()
{
    // Only place ONE order
    if(orderPlaced)
        return;

    // Check if we already have a position
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

    if(totalPositions > 0)
    {
        orderPlaced = true;
        Print("Position already exists, skipping order");
        return;
    }

    // Get current price
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

    // Print debug info
    Print("Attempting to place BUY order...");
    Print("Ask: ", ask, " | Bid: ", bid);
    Print("Point: ", _Point, " | Digits: ", _Digits);
    Print("Min Lot: ", SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
    Print("Max Lot: ", SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX));
    Print("Lot Step: ", SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP));

    // Place BUY order
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

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
    request.comment = "ONE_TRADE_TEST";

    if(OrderSend(request, result))
    {
        Print("✅✅✅ SUCCESS! BUY order placed at ", ask);
        Print("SL: ", sl, " | TP: ", tp);
        Print("Result: ", result.retcode);
        orderPlaced = true;
    }
    else
    {
        Print("❌❌❌ FAILED! OrderSend error: ", GetLastError());
        Print("Result code: ", result.retcode);
        Print("Request error: ", result.retcode);
    }
}
//+------------------------------------------------------------------+
