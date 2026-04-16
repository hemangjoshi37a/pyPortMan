//+------------------------------------------------------------------+
//|                                    EMA_SMC_Luxalgo_EA_v2.mq5     |
//|                        EMA 11 + SMC Luxalgo (Improved)           |
//+------------------------------------------------------------------+
#property copyright "EA Bot v2"
#property version   "2.00"
#property strict

//--- Input Parameters
input group "=== EMA Settings ==="
input int      EMA_Period = 11;              // EMA Period
input ENUM_TIMEFRAMES EMA_Timeframe = PERIOD_M1; // EMA Timeframe
input bool     Use_EMA_Filter = true;       // Use EMA Filter (disable for more signals)

input group "=== SMC Settings ==="
input int      Swing_Lookback = 3;           // Swing High/Low Lookback (reduced)
input int      FVG_Min_Size = 5;             // FVG Minimum Size (reduced)
input int      OB_Lookback = 10;             // Order Block Lookback (reduced)
input bool     Use_Breaker_Blocks = true;    // Use Breaker Blocks
input bool     Use_Liquidity_Sweeps = true;  // Use Liquidity Sweeps
input bool     Use_Market_Structure = true;  // Use Market Structure (HH/HL, LH/LL)
input bool     Use_Engulfing = true;         // Use Engulfing Pattern
input bool     Use_Pinbar = true;            // Use Pinbar Pattern

input group "=== Signal Settings ==="
input int      Min_Signals = 1;              // Minimum signals required (1-3)
input bool     Use_Confluence = false;      // Require multiple confluences

input group "=== Risk Management ==="
input double   Lot_Size = 0.01;              // Lot Size
input double   Risk_Percent = 1.0;           // Risk Percent
input bool     Use_Dynamic_Lot = false;      // Use Dynamic Lot
input int      Stop_Loss_Pips = 30;          // Stop Loss (pips)
input int      Take_Profit_Pips = 60;        // Take Profit (pips)
input double   Trailing_Stop_Pips = 20;      // Trailing Stop (pips)
input bool     Use_Trailing_Stop = true;     // Use Trailing Stop
input int      Magic_Number = 123456;        // Magic Number
input int      Max_Spread = 50;              // Max Spread (points)

input group "=== Time Filter ==="
input bool     Use_Time_Filter = false;      // Use Time Filter
input int      Start_Hour = 0;               // Start Hour (0-23)
input int      End_Hour = 23;                // End Hour (0-23)

input group "=== Other Settings ==="
input int      Max_Positions = 5;            // Max Positions (increased)
input bool     Close_Opposite = true;         // Close Opposite on Signal
input int      Min_Candles_Between_Trades = 5; // Min candles between trades

//--- Global Variables
int emaHandle;
double emaBuffer[];
double highBuffer[], lowBuffer[], openBuffer[], closeBuffer[];

// Structures
struct OrderBlock {
    datetime time;
    double high;
    double low;
    bool isBullish;
    bool isValid;
};

struct FVG {
    datetime time;
    double top;
    double bottom;
    bool isBullish;
    bool isValid;
};

OrderBlock bullishOB, bearishOB;
FVG bullishFVG, bearishFVG;

enum MarketStructure {
    STRUCTURE_UNKNOWN,
    STRUCTURE_UPTREND,
    STRUCTURE_DOWNTREND
};

MarketStructure currentStructure = STRUCTURE_UNKNOWN;
double lastSwingHigh = 0, lastSwingLow = 0;
datetime lastSwingHighTime = 0, lastSwingLowTime = 0;

datetime lastTradeTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    emaHandle = iMA(_Symbol, EMA_Timeframe, EMA_Period, 0, MODE_EMA, PRICE_CLOSE);
    if(emaHandle == INVALID_HANDLE)
    {
        Print("Error creating EMA indicator: ", GetLastError());
        return INIT_FAILED;
    }

    ArraySetAsSeries(emaBuffer, true);
    ArraySetAsSeries(highBuffer, true);
    ArraySetAsSeries(lowBuffer, true);
    ArraySetAsSeries(openBuffer, true);
    ArraySetAsSeries(closeBuffer, true);

    bullishOB.isValid = false;
    bearishOB.isValid = false;
    bullishFVG.isValid = false;
    bearishFVG.isValid = false;

    Print("EMA SMC Luxalgo EA v2 initialized");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(emaHandle != INVALID_HANDLE)
        IndicatorRelease(emaHandle);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    double spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
    if(spread > Max_Spread)
        return;

    if(Use_Time_Filter && !IsTradingTime())
        return;

    int lookback = MathMax(Swing_Lookback * 3, OB_Lookback * 2, 50);

    CopyHigh(_Symbol, PERIOD_CURRENT, 0, lookback, highBuffer);
    CopyLow(_Symbol, PERIOD_CURRENT, 0, lookback, lowBuffer);
    CopyOpen(_Symbol, PERIOD_CURRENT, 0, lookback, openBuffer);
    CopyClose(_Symbol, PERIOD_CURRENT, 0, lookback, closeBuffer);
    CopyBuffer(emaHandle, 0, 0, lookback, emaBuffer);

    UpdateMarketStructure();
    UpdateOrderBlocks();
    UpdateFVG();

    CheckBuySignal();
    CheckSellSignal();

    if(Use_Trailing_Stop)
        ManageTrailingStops();
}

//+------------------------------------------------------------------+
//| Is Trading Time                                                  |
//+------------------------------------------------------------------+
bool IsTradingTime()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    int h = dt.hour;

    if(Start_Hour < End_Hour)
        return (h >= Start_Hour && h < End_Hour);
    else
        return (h >= Start_Hour || h < End_Hour);
}

//+------------------------------------------------------------------+
//| Update Market Structure                                          |
//+------------------------------------------------------------------+
void UpdateMarketStructure()
{
    for(int i = Swing_Lookback; i < ArraySize(highBuffer) - Swing_Lookback; i++)
    {
        bool isSwingHigh = true;
        bool isSwingLow = true;

        for(int j = 1; j <= Swing_Lookback; j++)
        {
            if(highBuffer[i] <= highBuffer[i + j] || highBuffer[i] <= highBuffer[i - j])
                isSwingHigh = false;
            if(lowBuffer[i] >= lowBuffer[i + j] || lowBuffer[i] >= lowBuffer[i - j])
                isSwingLow = false;
        }

        if(isSwingHigh && highBuffer[i] > lastSwingHigh)
        {
            lastSwingHigh = highBuffer[i];
            lastSwingHighTime = iTime(_Symbol, PERIOD_CURRENT, i);
        }

        if(isSwingLow && (lastSwingLow == 0 || lowBuffer[i] < lastSwingLow))
        {
            lastSwingLow = lowBuffer[i];
            lastSwingLowTime = iTime(_Symbol, PERIOD_CURRENT, i);
        }
    }

    if(lastSwingHigh > 0 && lastSwingLow > 0)
    {
        if(lastSwingHighTime > lastSwingLowTime)
            currentStructure = STRUCTURE_UPTREND;
        else
            currentStructure = STRUCTURE_DOWNTREND;
    }
}

//+------------------------------------------------------------------+
//| Update Order Blocks                                              |
//+------------------------------------------------------------------+
void UpdateOrderBlocks()
{
    // Bullish OB - RELAXED CONDITIONS
    for(int i = 1; i < OB_Lookback; i++)
    {
        if(closeBuffer[i] > openBuffer[i] && closeBuffer[i + 1] < openBuffer[i + 1])
        {
            bullishOB.time = iTime(_Symbol, PERIOD_CURRENT, i + 1);
            bullishOB.high = openBuffer[i + 1];
            bullishOB.low = closeBuffer[i + 1];
            bullishOB.isBullish = true;
            bullishOB.isValid = true;
            break;
        }
    }

    // Bearish OB - RELAXED CONDITIONS
    for(int i = 1; i < OB_Lookback; i++)
    {
        if(closeBuffer[i] < openBuffer[i] && closeBuffer[i + 1] > openBuffer[i + 1])
        {
            bearishOB.time = iTime(_Symbol, PERIOD_CURRENT, i + 1);
            bearishOB.high = closeBuffer[i + 1];
            bearishOB.low = openBuffer[i + 1];
            bearishOB.isBullish = false;
            bearishOB.isValid = true;
            break;
        }
    }
}

//+------------------------------------------------------------------+
//| Update FVG                                                       |
//+------------------------------------------------------------------+
void UpdateFVG()
{
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
                break;
            }
        }
    }

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
                break;
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Check for Buy Signal                                             |
//+------------------------------------------------------------------+
void CheckBuySignal()
{
    if(CountPositions(POSITION_TYPE_BUY) >= Max_Positions)
        return;

    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double emaValue = emaBuffer[0];

    // Check minimum candles between trades
    if(lastTradeTime > 0)
    {
        int candlesSinceLastTrade = (int)((TimeCurrent() - lastTradeTime) / PeriodSeconds());
        if(candlesSinceLastTrade < Min_Candles_Between_Trades)
            return;
    }

    // EMA Filter
    bool emaFilter = !Use_EMA_Filter || currentPrice > emaValue;

    // Count bullish signals
    int signalCount = 0;

    // FVG Signal
    if(bullishFVG.isValid && currentPrice >= bullishFVG.bottom && currentPrice <= bullishFVG.top)
    {
        signalCount++;
    }

    // OB Signal
    if(bullishOB.isValid && currentPrice >= bullishOB.low && currentPrice <= bullishOB.high)
    {
        signalCount++;
    }

    // Market Structure Signal
    if(Use_Market_Structure && currentStructure == STRUCTURE_UPTREND)
    {
        signalCount++;
    }

    // Engulfing Signal
    if(Use_Engulfing && IsBullishEngulfing())
    {
        signalCount++;
    }

    // Pinbar Signal
    if(Use_Pinbar && IsBullishPinbar())
    {
        signalCount++;
    }

    // Check if we have enough signals
    if(emaFilter && signalCount >= Min_Signals)
    {
        if(Close_Opposite)
            ClosePositions(POSITION_TYPE_SELL);

        OpenBuy();
        lastTradeTime = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Check for Sell Signal                                            |
//+------------------------------------------------------------------+
void CheckSellSignal()
{
    if(CountPositions(POSITION_TYPE_SELL) >= Max_Positions)
        return;

    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double emaValue = emaBuffer[0];

    if(lastTradeTime > 0)
    {
        int candlesSinceLastTrade = (int)((TimeCurrent() - lastTradeTime) / PeriodSeconds());
        if(candlesSinceLastTrade < Min_Candles_Between_Trades)
            return;
    }

    bool emaFilter = !Use_EMA_Filter || currentPrice < emaValue;

    int signalCount = 0;

    if(bearishFVG.isValid && currentPrice >= bearishFVG.bottom && currentPrice <= bearishFVG.top)
    {
        signalCount++;
    }

    if(bearishOB.isValid && currentPrice >= bearishOB.low && currentPrice <= bearishOB.high)
    {
        signalCount++;
    }

    if(Use_Market_Structure && currentStructure == STRUCTURE_DOWNTREND)
    {
        signalCount++;
    }

    if(Use_Engulfing && IsBearishEngulfing())
    {
        signalCount++;
    }

    if(Use_Pinbar && IsBearishPinbar())
    {
        signalCount++;
    }

    if(emaFilter && signalCount >= Min_Signals)
    {
        if(Close_Opposite)
            ClosePositions(POSITION_TYPE_BUY);

        OpenSell();
        lastTradeTime = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Is Bullish Engulfing                                             |
//+------------------------------------------------------------------+
bool IsBullishEngulfing()
{
    if(ArraySize(closeBuffer) < 2) return false;

    double body1 = MathAbs(closeBuffer[1] - openBuffer[1]);
    double body2 = MathAbs(closeBuffer[0] - openBuffer[0]);

    return (closeBuffer[1] < openBuffer[1] &&  // Previous candle bearish
            closeBuffer[0] > openBuffer[0] &&  // Current candle bullish
            closeBuffer[0] > openBuffer[1] &&   // Engulfs previous open
            openBuffer[0] < closeBuffer[1]);    // Engulfs previous close
}

//+------------------------------------------------------------------+
//| Is Bearish Engulfing                                             |
//+------------------------------------------------------------------+
bool IsBearishEngulfing()
{
    if(ArraySize(closeBuffer) < 2) return false;

    return (closeBuffer[1] > openBuffer[1] &&  // Previous candle bullish
            closeBuffer[0] < openBuffer[0] &&  // Current candle bearish
            closeBuffer[0] < openBuffer[1] &&   // Engulfs previous open
            openBuffer[0] > closeBuffer[1]);    // Engulfs previous close
}

//+------------------------------------------------------------------+
//| Is Bullish Pinbar                                                |
//+------------------------------------------------------------------+
bool IsBullishPinbar()
{
    if(ArraySize(closeBuffer) < 1) return false;

    double body = MathAbs(closeBuffer[0] - openBuffer[0]);
    double upperWick = highBuffer[0] - MathMax(openBuffer[0], closeBuffer[0]);
    double lowerWick = MathMin(openBuffer[0], closeBuffer[0]) - lowBuffer[0];
    double totalRange = highBuffer[0] - lowBuffer[0];

    if(totalRange == 0) return false;

    return (closeBuffer[0] > openBuffer[0] &&  // Bullish candle
            lowerWick > body * 2 &&             // Long lower wick
            upperWick < body * 0.5);            // Small upper wick
}

//+------------------------------------------------------------------+
//| Is Bearish Pinbar                                                |
//+------------------------------------------------------------------+
bool IsBearishPinbar()
{
    if(ArraySize(closeBuffer) < 1) return false;

    double body = MathAbs(closeBuffer[0] - openBuffer[0]);
    double upperWick = highBuffer[0] - MathMax(openBuffer[0], closeBuffer[0]);
    double lowerWick = MathMin(openBuffer[0], closeBuffer[0]) - lowBuffer[0];
    double totalRange = highBuffer[0] - lowBuffer[0];

    if(totalRange == 0) return false;

    return (closeBuffer[0] < openBuffer[0] &&  // Bearish candle
            upperWick > body * 2 &&             // Long upper wick
            lowerWick < body * 0.5);            // Small lower wick
}

//+------------------------------------------------------------------+
//| Open Buy Position                                                |
//+------------------------------------------------------------------+
void OpenBuy()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double lot = Use_Dynamic_Lot ? CalculateDynamicLot() : Lot_Size;
    double sl = SymbolInfoDouble(_Symbol, SYMBOL_BID) - Stop_Loss_Pips * _Point * 10;
    double tp = SymbolInfoDouble(_Symbol, SYMBOL_BID) + Take_Profit_Pips * _Point * 10;

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = lot;
    request.type = ORDER_TYPE_BUY;
    request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    request.sl = sl;
    request.tp = tp;
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "EMA_SMC_BUY_v2";

    if(!OrderSend(request, result))
        Print("Buy order failed: ", GetLastError());
    else
        Print("BUY opened at ", request.price, " | SL: ", sl, " | TP: ", tp);
}

//+------------------------------------------------------------------+
//| Open Sell Position                                               |
//+------------------------------------------------------------------+
void OpenSell()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double lot = Use_Dynamic_Lot ? CalculateDynamicLot() : Lot_Size;
    double sl = SymbolInfoDouble(_Symbol, SYMBOL_ASK) + Stop_Loss_Pips * _Point * 10;
    double tp = SymbolInfoDouble(_Symbol, SYMBOL_ASK) - Take_Profit_Pips * _Point * 10;

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = lot;
    request.type = ORDER_TYPE_SELL;
    request.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    request.sl = sl;
    request.tp = tp;
    request.deviation = 10;
    request.magic = Magic_Number;
    request.comment = "EMA_SMC_SELL_v2";

    if(!OrderSend(request, result))
        Print("Sell order failed: ", GetLastError());
    else
        Print("SELL opened at ", request.price, " | SL: ", sl, " | TP: ", tp);
}

//+------------------------------------------------------------------+
//| Calculate Dynamic Lot                                            |
//+------------------------------------------------------------------+
double CalculateDynamicLot()
{
    double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double riskAmount = accountBalance * (Risk_Percent / 100.0);
    double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

    double slInMoney = Stop_Loss_Pips * 10 * tickValue;
    if(slInMoney == 0) return Lot_Size;

    double lot = riskAmount / slInMoney;

    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

    lot = MathFloor(lot / lotStep) * lotStep;
    lot = MathMax(lot, minLot);
    lot = MathMin(lot, maxLot);

    return lot;
}

//+------------------------------------------------------------------+
//| Count Positions                                                  |
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
//| Close Positions                                                  |
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

                OrderSend(request, result);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Manage Trailing Stops                                            |
//+------------------------------------------------------------------+
void ManageTrailingStops()
{
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
                double currentSL = PositionGetDouble(POSITION_SL);
                double currentTP = PositionGetDouble(POSITION_TP);
                ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);

                double newSL = currentSL;
                double trailDistance = Trailing_Stop_Pips * _Point * 10;

                if(posType == POSITION_TYPE_BUY)
                {
                    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                    if(currentPrice - openPrice > trailDistance)
                    {
                        newSL = currentPrice - trailDistance;
                        if(newSL > currentSL)
                            ModifyPosition(PositionGetInteger(POSITION_TICKET), newSL, currentTP);
                    }
                }
                else if(posType == POSITION_TYPE_SELL)
                {
                    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                    if(openPrice - currentPrice > trailDistance)
                    {
                        newSL = currentPrice + trailDistance;
                        if(newSL < currentSL || currentSL == 0)
                            ModifyPosition(PositionGetInteger(POSITION_TICKET), newSL, currentTP);
                    }
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Modify Position                                                  |
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
