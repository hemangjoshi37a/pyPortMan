//+------------------------------------------------------------------+
//|                                            EMA_SMC_Luxalgo_EA.mq5 |
//|                        EMA 11 + Smart Money Concepts EA         |
//+------------------------------------------------------------------+
#property copyright "EA Bot"
#property version   "1.00"
#property strict

//--- Input Parameters
input group "=== EMA Settings ==="
input int      EMA_Period = 11;              // EMA Period
input ENUM_TIMEFRAMES EMA_Timeframe = PERIOD_M1; // EMA Timeframe

input group "=== SMC Settings ==="
input int      Swing_Lookback = 5;           // Swing High/Low Lookback
input int      FVG_Min_Size = 10;            // FVG Minimum Size (points)
input int      OB_Lookback = 20;             // Order Block Lookback
input bool     Use_Breaker_Blocks = true;    // Use Breaker Blocks
input bool     Use_Liquidity_Sweeps = true;  // Use Liquidity Sweeps

input group "=== Risk Management ==="
input double   Lot_Size = 0.01;              // Lot Size
input double   Risk_Percent = 1.0;           // Risk Percent (if dynamic lot)
input bool     Use_Dynamic_Lot = false;      // Use Dynamic Lot
input int      Stop_Loss_Pips = 50;          // Stop Loss (pips)
input int      Take_Profit_Pips = 100;       // Take Profit (pips)
input double   Trailing_Stop_Pips = 30;     // Trailing Stop (pips)
input bool     Use_Trailing_Stop = true;    // Use Trailing Stop
input int      Magic_Number = 123456;       // Magic Number
input int      Max_Spread = 30;              // Max Spread (points)

input group "=== Time Filter ==="
input bool     Use_Time_Filter = false;     // Use Time Filter
input int      Start_Hour = 8;               // Start Hour
input int      End_Hour = 20;                // End Hour

input group "=== Other Settings ==="
input int      Max_Positions = 3;            // Max Positions
input bool     Close_Opposite = true;        // Close Opposite on Signal

//--- Global Variables
int emaHandle;
double emaBuffer[];
double highBuffer[], lowBuffer[], openBuffer[], closeBuffer[];

// Structure for Order Blocks
struct OrderBlock {
    datetime time;
    double high;
    double low;
    bool isBullish;  // true = bullish OB (buy zone), false = bearish OB (sell zone)
    bool isValid;
};

OrderBlock bullishOB, bearishOB;

// Structure for FVG
struct FVG {
    datetime time;
    double top;
    double bottom;
    bool isBullish;  // true = bullish FVG (gap up), false = bearish FVG (gap down)
    bool isValid;
};

FVG bullishFVG, bearishFVG;

// Market Structure
enum MarketStructure {
    STRUCTURE_UNKNOWN,
    STRUCTURE_UPTREND,  // Higher Highs, Higher Lows
    STRUCTURE_DOWNTREND // Lower Highs, Lower Lows
};

MarketStructure currentStructure = STRUCTURE_UNKNOWN;
double lastSwingHigh = 0, lastSwingLow = 0;
datetime lastSwingHighTime = 0, lastSwingLowTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize EMA indicator
    emaHandle = iMA(_Symbol, EMA_Timeframe, EMA_Period, 0, MODE_EMA, PRICE_CLOSE);
    if(emaHandle == INVALID_HANDLE)
    {
        Print("Error creating EMA indicator handle: ", GetLastError());
        return INIT_FAILED;
    }

    // Set array as series
    ArraySetAsSeries(emaBuffer, true);
    ArraySetAsSeries(highBuffer, true);
    ArraySetAsSeries(lowBuffer, true);
    ArraySetAsSeries(openBuffer, true);
    ArraySetAsSeries(closeBuffer, true);

    // Initialize Order Blocks
    bullishOB.isValid = false;
    bearishOB.isValid = false;
    bullishFVG.isValid = false;
    bearishFVG.isValid = false;

    Print("EMA SMC Luxalgo EA initialized successfully");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(emaHandle != INVALID_HANDLE)
        IndicatorRelease(emaHandle);
    Print("EA deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check spread
    double spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
    if(spread > Max_Spread)
        return;

    // Time filter
    if(Use_Time_Filter && !IsTradingTime())
        return;

    // Get price data
    CopyHigh(_Symbol, PERIOD_CURRENT, 0, Swing_Lookback * 3, highBuffer);
    CopyLow(_Symbol, PERIOD_CURRENT, 0, Swing_Lookback * 3, lowBuffer);
    CopyOpen(_Symbol, PERIOD_CURRENT, 0, Swing_Lookback * 3, openBuffer);
    CopyClose(_Symbol, PERIOD_CURRENT, 0, Swing_Lookback * 3, closeBuffer);

    // Get EMA data
    CopyBuffer(emaHandle, 0, 0, Swing_Lookback * 3, emaBuffer);

    // Update SMC analysis
    UpdateMarketStructure();
    UpdateOrderBlocks();
    UpdateFVG();

    // Check for trading signals
    CheckBuySignal();
    CheckSellSignal();

    // Manage trailing stops
    if(Use_Trailing_Stop)
        ManageTrailingStops();
}

//+------------------------------------------------------------------+
//| Check if it's trading time                                       |
//+------------------------------------------------------------------+
bool IsTradingTime()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    int currentHour = dt.hour;

    if(Start_Hour < End_Hour)
        return (currentHour >= Start_Hour && currentHour < End_Hour);
    else // Overnight trading
        return (currentHour >= Start_Hour || currentHour < End_Hour);
}

//+------------------------------------------------------------------+
//| Update Market Structure (HH, HL, LH, LL)                         |
//+------------------------------------------------------------------+
void UpdateMarketStructure()
{
    // Find swing highs and lows
    for(int i = Swing_Lookback; i < ArraySize(highBuffer) - Swing_Lookback; i++)
    {
        bool isSwingHigh = true;
        bool isSwingLow = true;

        // Check if current candle is a swing high
        for(int j = 1; j <= Swing_Lookback; j++)
        {
            if(highBuffer[i] <= highBuffer[i + j] || highBuffer[i] <= highBuffer[i - j])
            {
                isSwingHigh = false;
                break;
            }
        }

        // Check if current candle is a swing low
        for(int j = 1; j <= Swing_Lookback; j++)
        {
            if(lowBuffer[i] >= lowBuffer[i + j] || lowBuffer[i] >= lowBuffer[i - j])
            {
                isSwingLow = false;
                break;
            }
        }

        // Update swing highs
        if(isSwingHigh && highBuffer[i] > lastSwingHigh)
        {
            lastSwingHigh = highBuffer[i];
            lastSwingHighTime = iTime(_Symbol, PERIOD_CURRENT, i);
        }

        // Update swing lows
        if(isSwingLow && (lastSwingLow == 0 || lowBuffer[i] < lastSwingLow))
        {
            lastSwingLow = lowBuffer[i];
            lastSwingLowTime = iTime(_Symbol, PERIOD_CURRENT, i);
        }
    }

    // Determine market structure
    if(lastSwingHigh > 0 && lastSwingLow > 0)
    {
        // Check for uptrend (HH + HL)
        if(lastSwingHighTime > lastSwingLowTime)
            currentStructure = STRUCTURE_UPTREND;
        // Check for downtrend (LH + LL)
        else if(lastSwingLowTime > lastSwingHighTime)
            currentStructure = STRUCTURE_DOWNTREND;
    }
}

//+------------------------------------------------------------------+
//| Update Order Blocks                                              |
//+------------------------------------------------------------------+
void UpdateOrderBlocks()
{
    // Look for last down candle that broke up (Bullish OB)
    for(int i = 1; i < OB_Lookback; i++)
    {
        // Bullish Order Block: Last bearish candle before strong bullish move
        if(closeBuffer[i] > openBuffer[i] && // Current candle is bullish
           closeBuffer[i] > highBuffer[i + 1] && // Broke previous high
           closeBuffer[i + 1] < openBuffer[i + 1]) // Previous candle was bearish
        {
            bullishOB.time = iTime(_Symbol, PERIOD_CURRENT, i + 1);
            bullishOB.high = openBuffer[i + 1];
            bullishOB.low = closeBuffer[i + 1];
            bullishOB.isBullish = true;
            bullishOB.isValid = true;
            break;
        }
    }

    // Look for last up candle that broke down (Bearish OB)
    for(int i = 1; i < OB_Lookback; i++)
    {
        // Bearish Order Block: Last bullish candle before strong bearish move
        if(closeBuffer[i] < openBuffer[i] && // Current candle is bearish
           closeBuffer[i] < lowBuffer[i + 1] && // Broke previous low
           closeBuffer[i + 1] > openBuffer[i + 1]) // Previous candle was bullish
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
//| Update Fair Value Gaps (FVG)                                     |
//+------------------------------------------------------------------+
void UpdateFVG()
{
    // Look for Bullish FVG (gap between candle 1 high and candle 3 low)
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

    // Look for Bearish FVG (gap between candle 1 low and candle 3 high)
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
    // Check max positions
    if(CountPositions(POSITION_TYPE_BUY) >= Max_Positions)
        return;

    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double emaValue = emaBuffer[0];

    // EMA Filter: Price should be above EMA for uptrend
    bool emaFilter = currentPrice > emaValue;

    // Check for bullish signals
    bool obSignal = false;
    bool fvgSignal = false;
    bool structureSignal = (currentStructure == STRUCTURE_UPTREND);

    // Order Block signal
    if(bullishOB.isValid && currentPrice >= bullishOB.low && currentPrice <= bullishOB.high)
        obSignal = true;

    // FVG signal
    if(bullishFVG.isValid && currentPrice >= bullishFVG.bottom && currentPrice <= bullishFVG.top)
        fvgSignal = true;

    // Combined signal
    if(emaFilter && (obSignal || fvgSignal || structureSignal))
    {
        // Close opposite positions
        if(Close_Opposite)
            ClosePositions(POSITION_TYPE_SELL);

        // Open buy position
        OpenBuy();
    }
}

//+------------------------------------------------------------------+
//| Check for Sell Signal                                            |
//+------------------------------------------------------------------+
void CheckSellSignal()
{
    // Check max positions
    if(CountPositions(POSITION_TYPE_SELL) >= Max_Positions)
        return;

    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double emaValue = emaBuffer[0];

    // EMA Filter: Price should be below EMA for downtrend
    bool emaFilter = currentPrice < emaValue;

    // Check for bearish signals
    bool obSignal = false;
    bool fvgSignal = false;
    bool structureSignal = (currentStructure == STRUCTURE_DOWNTREND);

    // Order Block signal
    if(bearishOB.isValid && currentPrice >= bearishOB.low && currentPrice <= bearishOB.high)
        obSignal = true;

    // FVG signal
    if(bearishFVG.isValid && currentPrice >= bearishFVG.bottom && currentPrice <= bearishFVG.top)
        fvgSignal = true;

    // Combined signal
    if(emaFilter && (obSignal || fvgSignal || structureSignal))
    {
        // Close opposite positions
        if(Close_Opposite)
            ClosePositions(POSITION_TYPE_BUY);

        // Open sell position
        OpenSell();
    }
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
    request.comment = "EMA_SMC_BUY";

    if(!OrderSend(request, result))
        Print("Buy order failed: ", GetLastError());
    else
        Print("Buy order opened: ", result.order);
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
    request.comment = "EMA_SMC_SELL";

    if(!OrderSend(request, result))
        Print("Sell order failed: ", GetLastError());
    else
        Print("Sell order opened: ", result.order);
}

//+------------------------------------------------------------------+
//| Calculate Dynamic Lot Size                                       |
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

    // Normalize lot size
    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

    lot = MathFloor(lot / lotStep) * lotStep;
    lot = MathMax(lot, minLot);
    lot = MathMin(lot, maxLot);

    return lot;
}

//+------------------------------------------------------------------+
//| Count Positions by Type                                          |
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
//| Close Positions by Type                                          |
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
//| Modify Position SL/TP                                            |
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
