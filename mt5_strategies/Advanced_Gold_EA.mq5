//+------------------------------------------------------------------+
//|                                    Advanced_Gold_EA.mq5         |
//|                        Advanced Trade Management EA for XAUUSD   |
//+------------------------------------------------------------------+
#property copyright "Advanced Gold EA"
#property version   "1.00"
#property strict

//--- Input Parameters
input group "=== Trade Settings ==="
input double   Lot_Size = 0.02;              // Fixed Lot Size
input int      Magic_Number = 888888;       // Magic Number

input group "=== Risk Management ==="
input int      Initial_SL_Pips = 50;        // Initial Stop Loss (pips)
input int      BreakEven_Pips = 40;         // Break-Even at (pips)
input int      Trailing_SL_Pips = 30;       // Trailing SL distance (pips)

input group "=== Partial Close Settings ==="
input int      PartialClose_Pips = 80;      // Partial Close at (pips)
input double   PartialClose_Percent = 0.50; // Partial Close % (0.50 = 50%)
input int      PartialClose_SL_Pips = 60;   // SL after partial close (pips)

input group "=== Advanced Trailing ==="
input int      Adv_Trail_Level1 = 95;       // First advanced trail level (pips)
input int      Adv_Trail_Level2 = 110;      // Second advanced trail level (pips)
input int      Adv_TP_Distance = 15;        // TP distance after advanced trail (pips)
input int      Adv_SL_Move = 5;             // SL move after advanced trail (pips)

input group "=== Entry Settings ==="
input int      Candles_Between_Trades = 10; // Min candles between trades

//--- Global Variables
datetime lastTradeTime = 0;
int tradeCount = 0;

// Trade Management Variables
bool breakEvenActivated = false;
bool partialCloseDone = false;
bool advTrail1Done = false;
bool advTrail2Done = false;
double entryPrice = 0;
double originalSL = 0;
double originalTP = 0;
ENUM_POSITION_TYPE positionType = POSITION_TYPE_BUY;

//+------------------------------------------------------------------+
//| Get Pip Value for Symbol                                         |
//+------------------------------------------------------------------+
double GetPipValue()
{
    int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

    // For XAUUSD (Gold), typically 2-3 decimal places
    // 1 pip = 0.01 for 2 decimal places, 0.1 for 3 decimal places
    if(digits == 2)
        return 0.01;
    else if(digits == 3)
        return 0.1;
    else if(digits == 5)
        return 0.0001;  // Forex 5-digit
    else if(digits == 4)
        return 0.0001;  // Forex 4-digit
    else
        return _Point;  // Default
}

//+------------------------------------------------------------------+
//| Calculate Price from Pips                                        |
//+------------------------------------------------------------------+
double PipsToPrice(int pips)
{
    return pips * GetPipValue();
}

//+------------------------------------------------------------------+
//| Calculate Pips from Price Difference                             |
//+------------------------------------------------------------------+
int PriceToPips(double priceDiff)
{
    return (int)(priceDiff / GetPipValue());
}

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("Advanced Gold EA initialized for ", _Symbol);
    Print("Pip Value: ", GetPipValue());
    Print("Digits: ", SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("Advanced Gold EA stopped. Total trades: ", tradeCount);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check for existing position
    bool hasPosition = false;
    ulong positionTicket = 0;
    double currentVolume = 0;
    double currentSL = 0;
    double currentTP = 0;
    double openPrice = 0;

    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                hasPosition = true;
                positionTicket = PositionGetInteger(POSITION_TICKET);
                currentVolume = PositionGetDouble(POSITION_VOLUME);
                currentSL = PositionGetDouble(POSITION_SL);
                currentTP = PositionGetDouble(POSITION_TP);
                openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
                positionType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
                break;
            }
        }
    }

    // If we have a position, manage it
    if(hasPosition)
    {
        ManagePosition(positionTicket, currentVolume, currentSL, currentTP, openPrice);
        return;
    }

    // Reset management variables when no position
    breakEvenActivated = false;
    partialCloseDone = false;
    advTrail1Done = false;
    advTrail2Done = false;
    entryPrice = 0;

    // Check minimum candles between trades
    if(lastTradeTime > 0)
    {
        int candlesSince = (int)((TimeCurrent() - lastTradeTime) / PeriodSeconds());
        if(candlesSince < Candles_Between_Trades)
            return;
    }

    // Entry Logic - Simple candle reversal
    double open = iOpen(_Symbol, PERIOD_CURRENT, 0);
    double close = iClose(_Symbol, PERIOD_CURRENT, 0);
    double prevOpen = iOpen(_Symbol, PERIOD_CURRENT, 1);
    double prevClose = iClose(_Symbol, PERIOD_CURRENT, 1);

    // Buy signal: Current green candle + previous red candle
    if(close > open && prevClose < prevOpen)
    {
        OpenBuy();
        lastTradeTime = TimeCurrent();
        tradeCount++;
    }
    // Sell signal: Current red candle + previous green candle
    else if(close < open && prevClose > prevOpen)
    {
        OpenSell();
        lastTradeTime = TimeCurrent();
        tradeCount++;
    }
}

//+------------------------------------------------------------------+
//| Manage Existing Position                                          |
//+------------------------------------------------------------------+
void ManagePosition(ulong ticket, double volume, double sl, double tp, double openPrice)
{
    double currentPrice = 0;
    double profitPips = 0;

    // Get current price based on position type
    if(positionType == POSITION_TYPE_BUY)
    {
        currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
        profitPips = PriceToPips(currentPrice - openPrice);
    }
    else // SELL
    {
        currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
        profitPips = PriceToPips(openPrice - currentPrice);
    }

    // Store entry price on first tick
    if(entryPrice == 0)
    {
        entryPrice = openPrice;
        originalSL = sl;
        originalTP = tp;
    }

    // 1. Break-Even at +40 pips
    if(!breakEvenActivated && profitPips >= BreakEven_Pips)
    {
        double newSL = openPrice; // Cost-to-cost
        if(ModifySL(ticket, newSL))
        {
            breakEvenActivated = true;
            Print("Break-Even activated at +", profitPips, " pips. SL moved to entry price: ", openPrice);
        }
    }

    // 2. Trailing SL after break-even (30 pips)
    if(breakEvenActivated && !partialCloseDone)
    {
        double newSL = 0;
        if(positionType == POSITION_TYPE_BUY)
            newSL = currentPrice - PipsToPrice(Trailing_SL_Pips);
        else
            newSL = currentPrice + PipsToPrice(Trailing_SL_Pips);

        // Only trail if it improves the SL
        if((positionType == POSITION_TYPE_BUY && newSL > sl) ||
           (positionType == POSITION_TYPE_SELL && newSL < sl))
        {
            if(ModifySL(ticket, newSL))
            {
                Print("Trailing SL updated to ", newSL, " at +", profitPips, " pips");
            }
        }
    }

    // 3. Partial Close at +80 pips
    if(!partialCloseDone && profitPips >= PartialClose_Pips)
    {
        double closeVolume = volume * PartialClose_Percent;
        if(ClosePartialPosition(ticket, closeVolume))
        {
            partialCloseDone = true;

            // Move SL to +60 pips from entry
            double newSL = 0;
            if(positionType == POSITION_TYPE_BUY)
                newSL = openPrice + PipsToPrice(PartialClose_SL_Pips);
            else
                newSL = openPrice - PipsToPrice(PartialClose_SL_Pips);

            if(ModifySL(ticket, newSL))
            {
                Print("Partial close done: ", closeVolume, " lots. SL moved to +", PartialClose_SL_Pips, " pips: ", newSL);
            }
        }
    }

    // 4. Advanced Trailing Level 1 at +95 pips
    if(partialCloseDone && !advTrail1Done && profitPips >= Adv_Trail_Level1)
    {
        double newTP = 0;
        double newSL = 0;

        if(positionType == POSITION_TYPE_BUY)
        {
            newTP = currentPrice + PipsToPrice(Adv_TP_Distance);
            newSL = sl + PipsToPrice(Adv_SL_Move);
        }
        else
        {
            newTP = currentPrice - PipsToPrice(Adv_TP_Distance);
            newSL = sl - PipsToPrice(Adv_SL_Move);
        }

        if(ModifySLTP(ticket, newSL, newTP))
        {
            advTrail1Done = true;
            Print("Advanced Trail Level 1 at +", profitPips, " pips. TP: ", newTP, ", SL: ", newSL);
        }
    }

    // 5. Advanced Trailing Level 2 at +110 pips
    if(advTrail1Done && !advTrail2Done && profitPips >= Adv_Trail_Level2)
    {
        double newTP = 0;
        double newSL = 0;

        if(positionType == POSITION_TYPE_BUY)
        {
            newTP = currentPrice + PipsToPrice(Adv_TP_Distance);
            newSL = sl + PipsToPrice(Adv_SL_Move);
        }
        else
        {
            newTP = currentPrice - PipsToPrice(Adv_TP_Distance);
            newSL = sl - PipsToPrice(Adv_SL_Move);
        }

        if(ModifySLTP(ticket, newSL, newTP))
        {
            advTrail2Done = true;
            Print("Advanced Trail Level 2 at +", profitPips, " pips. TP: ", newTP, ", SL: ", newSL);
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
    double pipValue = GetPipValue();
    double sl = ask - Initial_SL_Pips * pipValue;
    double tp = ask + (Initial_SL_Pips * 2) * pipValue; // Default TP = 2x SL

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = Lot_Size;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "GOLD_BUY";

    if(!OrderSend(request, result))
    {
        int error = GetLastError();
        Print("BUY failed: ", error, " - ", result.comment);
    }
    else
    {
        Print("BUY opened at ", ask, " | SL: ", sl, " | TP: ", tp);
    }
}

//+------------------------------------------------------------------+
//| Open Sell Position                                               |
//+------------------------------------------------------------------+
void OpenSell()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double pipValue = GetPipValue();
    double sl = bid + Initial_SL_Pips * pipValue;
    double tp = bid - (Initial_SL_Pips * 2) * pipValue; // Default TP = 2x SL

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = Lot_Size;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "GOLD_SELL";

    if(!OrderSend(request, result))
    {
        int error = GetLastError();
        Print("SELL failed: ", error, " - ", result.comment);
    }
    else
    {
        Print("SELL opened at ", bid, " | SL: ", sl, " | TP: ", tp);
    }
}

//+------------------------------------------------------------------+
//| Modify Stop Loss Only                                           |
//+------------------------------------------------------------------+
bool ModifySL(ulong ticket, double newSL)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    request.action = TRADE_ACTION_SLTP;
    request.position = ticket;
    request.sl = newSL;

    if(!OrderSend(request, result))
    {
        int error = GetLastError();
        Print("SL Modify failed: ", error, " - ", result.comment);
        return false;
    }
    return true;
}

//+------------------------------------------------------------------+
//| Modify Stop Loss and Take Profit                                |
//+------------------------------------------------------------------+
bool ModifySLTP(ulong ticket, double newSL, double newTP)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    request.action = TRADE_ACTION_SLTP;
    request.position = ticket;
    request.sl = newSL;
    request.tp = newTP;

    if(!OrderSend(request, result))
    {
        int error = GetLastError();
        Print("SL/TP Modify failed: ", error, " - ", result.comment);
        return false;
    }
    return true;
}

//+------------------------------------------------------------------+
//| Close Partial Position                                          |
//+------------------------------------------------------------------+
bool ClosePartialPosition(ulong ticket, double closeVolume)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double currentPrice = 0;
    if(positionType == POSITION_TYPE_BUY)
        currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    else
        currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

    request.action = TRADE_ACTION_DEAL;
    request.position = ticket;
    request.symbol = _Symbol;
    request.volume = closeVolume;
    request.type = (positionType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
    request.price = currentPrice;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "PARTIAL_CLOSE";

    if(!OrderSend(request, result))
    {
        int error = GetLastError();
        Print("Partial Close failed: ", error, " - ", result.comment);
        return false;
    }
    Print("Partial Close: ", closeVolume, " lots closed at ", currentPrice);
    return true;
}
//+------------------------------------------------------------------+
