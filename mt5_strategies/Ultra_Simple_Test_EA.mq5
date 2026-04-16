//+------------------------------------------------------------------+
//|                  Ultra_Simple_Test_EA.mq5                          |
//|           Ultra Simple - Enter on EVERY TICK                      |
//+------------------------------------------------------------------+
#property copyright "Ultra Simple Test EA"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                  |
//+------------------------------------------------------------------+
input double   Lot_Size = 0.01;             // Lot Size
input int      Stop_Loss_Pips = 50;          // Stop Loss (pips)
input int      Take_Profit_Pips = 100;       // Take Profit (pips)
input int      Magic_Number = 999999;        // Magic Number
input int      Max_Spread = 200;             // Max Spread (points)

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
int tradeCount = 0;
bool firstRun = true;

//+------------------------------------------------------------------+
//| EXPERT INITIALIZATION FUNCTION                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("========================================");
    Print("ULTRA SIMPLE TEST EA");
    Print("========================================");
    Print("This EA will enter on EVERY tick!");
    Print("If this generates 0 trades, MT5 has issues.");
    Print("========================================");

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| EXPERT DEINITIALIZATION FUNCTION                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("Ultra Simple EA stopped. Total trades: ", tradeCount);
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

    // Get current price
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

    // SIMPLE: Alternate between buy and sell
    static bool buyNext = true;

    if(buyNext)
    {
        // BUY
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
        request.comment = "ULTRA_SIMPLE_BUY";

        if(OrderSend(request, result))
        {
            Print("✅ BUY #", tradeCount + 1, " at ", ask);
            tradeCount++;
            buyNext = false;
        }
        else
        {
            Print("❌ BUY failed: ", GetLastError());
        }
    }
    else
    {
        // SELL
        MqlTradeRequest request = {};
        MqlTradeResult result = {};

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
        request.comment = "ULTRA_SIMPLE_SELL";

        if(OrderSend(request, result))
        {
            Print("✅ SELL #", tradeCount + 1, " at ", bid);
            tradeCount++;
            buyNext = true;
        }
        else
        {
            Print("❌ SELL failed: ", GetLastError());
        }
    }
}
//+------------------------------------------------------------------+
