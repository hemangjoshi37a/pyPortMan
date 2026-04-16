//+------------------------------------------------------------------+
//|                                    Simple_EA_Pro.mq5            |
//|                        Improved Simple EA - Better Strategy     |
//+------------------------------------------------------------------+
#property copyright "Simple EA Pro"
#property version   "2.00"
#property strict

//--- Input Parameters
input group "=== Entry Settings ==="
input bool     Use_EMA_Filter = true;        // Use EMA Filter
input int      EMA_Period = 20;              // EMA Period
input bool     Use_RSI_Filter = true;        // Use RSI Filter
input int      RSI_Period = 14;              // RSI Period
input int      RSI_Oversold = 30;            // RSI Oversold Level
input int      RSI_Overbought = 70;          // RSI Overbought Level
input bool     Use_Trend_Filter = true;      // Use Trend Filter (EMA slope)
input int      Trend_Period = 50;            // Trend EMA Period

input group "=== Pattern Settings ==="
input bool     Use_Engulfing = true;         // Use Engulfing Pattern
input bool     Use_Pinbar = true;            // Use Pinbar Pattern
input bool     Use_Inside_Bar = true;        // Use Inside Bar Pattern
input bool     Use_Reversal = true;          // Use Reversal Pattern

input group "=== Risk Management ==="
input double   Lot_Size = 0.01;              // Lot Size
input double   Risk_Percent = 1.0;           // Risk Percent (if dynamic lot)
input bool     Use_Dynamic_Lot = false;      // Use Dynamic Lot
input int      Stop_Loss_Pips = 30;          // Stop Loss (pips)
input int      Take_Profit_Pips = 60;        // Take Profit (pips)
input double   Trailing_Stop_Pips = 20;      // Trailing Stop (pips)
input bool     Use_Trailing_Stop = true;     // Use Trailing Stop
input double   Risk_Reward_Ratio = 2.0;      // Risk:Reward Ratio

input group "=== Money Management ==="
input bool     Use_Compounding = false;      // Use Compounding
input double   Compounding_Percent = 10.0;    // Compounding Percent
input bool     Use_Breakeven = true;         // Move SL to Breakeven
input int      Breakeven_Pips = 15;          // Breakeven after (pips)

input group "=== Time Filter ==="
input bool     Use_Time_Filter = false;      // Use Time Filter
input int      Start_Hour = 0;               // Start Hour (0-23)
input int      End_Hour = 23;                // End Hour (0-23)
input bool     Skip_Friday = false;          // Skip Friday Trading
input bool     Skip_Monday = false;          // Skip Monday Trading

input group "=== Other Settings ==="
input int      Magic_Number = 999999;        // Magic Number
input int      Max_Positions = 5;            // Max Positions
input int      Candles_Between_Trades = 5;   // Min candles between trades
input int      Max_Spread = 50;              // Max Spread (points)
input bool     Close_Opposite = true;        // Close Opposite on Signal

//--- Global Variables
int emaHandle, emaTrendHandle, rsiHandle;
double emaBuffer[], emaTrendBuffer[], rsiBuffer[];
double highBuffer[], lowBuffer[], openBuffer[], closeBuffer[];

datetime lastTradeTime = 0;
int tradeCount = 0;
double currentLotSize = 0.01;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize EMA
    emaHandle = iMA(_Symbol, PERIOD_CURRENT, EMA_Period, 0, MODE_EMA, PRICE_CLOSE);
    if(emaHandle == INVALID_HANDLE)
    {
        Print("Error creating EMA: ", GetLastError());
        return INIT_FAILED;
    }

    // Initialize Trend EMA
    emaTrendHandle = iMA(_Symbol, PERIOD_CURRENT, Trend_Period, 0, MODE_EMA, PRICE_CLOSE);
    if(emaTrendHandle == INVALID_HANDLE)
    {
        Print("Error creating Trend EMA: ", GetLastError());
        return INIT_FAILED;
    }

    // Initialize RSI
    rsiHandle = iRSI(_Symbol, PERIOD_CURRENT, RSI_Period, PRICE_CLOSE);
    if(rsiHandle == INVALID_HANDLE)
    {
        Print("Error creating RSI: ", GetLastError());
        return INIT_FAILED;
    }

    // Set arrays as series
    ArraySetAsSeries(emaBuffer, true);
    ArraySetAsSeries(emaTrendBuffer, true);
    ArraySetAsSeries(rsiBuffer, true);
    ArraySetAsSeries(highBuffer, true);
    ArraySetAsSeries(lowBuffer, true);
    ArraySetAsSeries(openBuffer, true);
    ArraySetAsSeries(closeBuffer, true);

    currentLotSize = Lot_Size;

    Print("Simple EA Pro initialized!");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(emaHandle != INVALID_HANDLE) IndicatorRelease(emaHandle);
    if(emaTrendHandle != INVALID_HANDLE) IndicatorRelease(emaTrendHandle);
    if(rsiHandle != INVALID_HANDLE) IndicatorRelease(rsiHandle);
    Print("Simple EA Pro stopped. Total trades: ", tradeCount);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check spread
    long spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
    if(spread > Max_Spread)
        return;

    // Time filter
    if(Use_Time_Filter && !IsTradingTime())
        return;

    // Skip specific days
    if(Skip_Friday || Skip_Monday)
    {
        MqlDateTime dt;
        TimeToStruct(TimeCurrent(), dt);
        if(Skip_Friday && dt.day_of_week == 5) return;
        if(Skip_Monday && dt.day_of_week == 1) return;
    }

    // Update lot size with compounding
    if(Use_Compounding)
        UpdateLotSize();

    // Get indicator data - FIXED: MathMax with 2 arguments only
    int lookback = MathMax(MathMax(EMA_Period, Trend_Period), RSI_Period) + 10;
    CopyBuffer(emaHandle, 0, 0, lookback, emaBuffer);
    CopyBuffer(emaTrendHandle, 0, 0, lookback, emaTrendBuffer);
    CopyBuffer(rsiHandle, 0, 0, lookback, rsiBuffer);
    CopyHigh(_Symbol, PERIOD_CURRENT, 0, lookback, highBuffer);
    CopyLow(_Symbol, PERIOD_CURRENT, 0, lookback, lowBuffer);
    CopyOpen(_Symbol, PERIOD_CURRENT, 0, lookback, openBuffer);
    CopyClose(_Symbol, PERIOD_CURRENT, 0, lookback, closeBuffer);

    // Count positions
    int buyCount = CountPositions(POSITION_TYPE_BUY);
    int sellCount = CountPositions(POSITION_TYPE_SELL);

    // Check max positions
    if(buyCount + sellCount >= Max_Positions)
    {
        ManageTrailingStops();
        ManageBreakeven();
        return;
    }

    // Check minimum candles between trades
    if(lastTradeTime > 0)
    {
        int candlesSince = (int)((TimeCurrent() - lastTradeTime) / PeriodSeconds());
        if(candlesSince < Candles_Between_Trades)
        {
            ManageTrailingStops();
            ManageBreakeven();
            return;
        }
    }

    // Get current values
    double currentPrice = closeBuffer[0];
    double emaValue = emaBuffer[0];
    double emaTrendValue = emaTrendBuffer[0];
    double rsiValue = rsiBuffer[0];

    // Check for signals
    CheckBuySignal(buyCount, currentPrice, emaValue, emaTrendValue, rsiValue);
    CheckSellSignal(sellCount, currentPrice, emaValue, emaTrendValue, rsiValue);

    // Manage existing positions
    ManageTrailingStops();
    ManageBreakeven();
}

//+------------------------------------------------------------------+
//| Check for Buy Signal                                             |
//+------------------------------------------------------------------+
void CheckBuySignal(int buyCount, double price, double ema, double trendEma, double rsi)
{
    if(buyCount >= Max_Positions) return;

    int signalStrength = 0;

    // EMA Filter: Price above EMA
    if(!Use_EMA_Filter || price > ema)
        signalStrength++;

    // Trend Filter: EMA sloping up
    if(!Use_Trend_Filter || emaTrendBuffer[0] > emaTrendBuffer[1])
        signalStrength++;

    // RSI Filter: Not overbought
    if(!Use_RSI_Filter || rsi < RSI_Overbought)
        signalStrength++;

    // Pattern signals
    if(Use_Engulfing && IsBullishEngulfing())
        signalStrength += 2;

    if(Use_Pinbar && IsBullishPinbar())
        signalStrength += 2;

    if(Use_Inside_Bar && IsBullishInsideBar())
        signalStrength++;

    if(Use_Reversal && IsBullishReversal())
        signalStrength += 2;

    // Need at least 2 signals
    if(signalStrength >= 2)
    {
        if(Close_Opposite)
            ClosePositions(POSITION_TYPE_SELL);

        OpenBuy();
        lastTradeTime = TimeCurrent();
        tradeCount++;
    }
}

//+------------------------------------------------------------------+
//| Check for Sell Signal                                            |
//+------------------------------------------------------------------+
void CheckSellSignal(int sellCount, double price, double ema, double trendEma, double rsi)
{
    if(sellCount >= Max_Positions) return;

    int signalStrength = 0;

    // EMA Filter: Price below EMA
    if(!Use_EMA_Filter || price < ema)
        signalStrength++;

    // Trend Filter: EMA sloping down
    if(!Use_Trend_Filter || emaTrendBuffer[0] < emaTrendBuffer[1])
        signalStrength++;

    // RSI Filter: Not oversold
    if(!Use_RSI_Filter || rsi > RSI_Oversold)
        signalStrength++;

    // Pattern signals
    if(Use_Engulfing && IsBearishEngulfing())
        signalStrength += 2;

    if(Use_Pinbar && IsBearishPinbar())
        signalStrength += 2;

    if(Use_Inside_Bar && IsBearishInsideBar())
        signalStrength++;

    if(Use_Reversal && IsBearishReversal())
        signalStrength += 2;

    // Need at least 2 signals
    if(signalStrength >= 2)
    {
        if(Close_Opposite)
            ClosePositions(POSITION_TYPE_BUY);

        OpenSell();
        lastTradeTime = TimeCurrent();
        tradeCount++;
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

    return (closeBuffer[1] < openBuffer[1] &&
            closeBuffer[0] > openBuffer[0] &&
            closeBuffer[0] > openBuffer[1] &&
            openBuffer[0] < closeBuffer[1]);
}

//+------------------------------------------------------------------+
//| Is Bearish Engulfing                                             |
//+------------------------------------------------------------------+
bool IsBearishEngulfing()
{
    if(ArraySize(closeBuffer) < 2) return false;

    return (closeBuffer[1] > openBuffer[1] &&
            closeBuffer[0] < openBuffer[0] &&
            closeBuffer[0] < openBuffer[1] &&
            openBuffer[0] > closeBuffer[1]);
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

    return (closeBuffer[0] > openBuffer[0] &&
            lowerWick > body * 2 &&
            upperWick < body * 0.5);
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

    return (closeBuffer[0] < openBuffer[0] &&
            upperWick > body * 2 &&
            lowerWick < body * 0.5);
}

//+------------------------------------------------------------------+
//| Is Bullish Inside Bar                                            |
//+------------------------------------------------------------------+
bool IsBullishInsideBar()
{
    if(ArraySize(closeBuffer) < 2) return false;

    return (highBuffer[0] < highBuffer[1] &&
            lowBuffer[0] > lowBuffer[1] &&
            closeBuffer[0] > openBuffer[0]);
}

//+------------------------------------------------------------------+
//| Is Bearish Inside Bar                                            |
//+------------------------------------------------------------------+
bool IsBearishInsideBar()
{
    if(ArraySize(closeBuffer) < 2) return false;

    return (highBuffer[0] < highBuffer[1] &&
            lowBuffer[0] > lowBuffer[1] &&
            closeBuffer[0] < openBuffer[0]);
}

//+------------------------------------------------------------------+
//| Is Bullish Reversal (Lower Low + Higher Close)                  |
//+------------------------------------------------------------------+
bool IsBullishReversal()
{
    if(ArraySize(closeBuffer) < 3) return false;

    // Lower low than previous 2 candles
    bool lowerLow = lowBuffer[0] < lowBuffer[1] && lowBuffer[0] < lowBuffer[2];
    // Higher close than previous candle
    bool higherClose = closeBuffer[0] > closeBuffer[1];
    // Bullish candle
    bool bullish = closeBuffer[0] > openBuffer[0];

    return lowerLow && higherClose && bullish;
}

//+------------------------------------------------------------------+
//| Is Bearish Reversal (Higher High + Lower Close)                  |
//+------------------------------------------------------------------+
bool IsBearishReversal()
{
    if(ArraySize(closeBuffer) < 3) return false;

    // Higher high than previous 2 candles
    bool higherHigh = highBuffer[0] > highBuffer[1] && highBuffer[0] > highBuffer[2];
    // Lower close than previous candle
    bool lowerClose = closeBuffer[0] < closeBuffer[1];
    // Bearish candle
    bool bearish = closeBuffer[0] < openBuffer[0];

    return higherHigh && lowerClose && bearish;
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
    double tp = ask + (Stop_Loss_Pips * Risk_Reward_Ratio) * _Point * 10;

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = currentLotSize;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "PRO_BUY";

    if(OrderSend(request, result))
        Print("PRO BUY opened at ", ask, " | Lot: ", currentLotSize);
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
    double tp = bid - (Stop_Loss_Pips * Risk_Reward_Ratio) * _Point * 10;

    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = currentLotSize;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp;
    request.deviation = 100;
    request.magic = Magic_Number;
    request.comment = "PRO_SELL";

    if(OrderSend(request, result))
        Print("PRO SELL opened at ", bid, " | Lot: ", currentLotSize);
    else
        Print("SELL failed: ", GetLastError());
}

//+------------------------------------------------------------------+
//| Update Lot Size with Compounding                                |
//+------------------------------------------------------------------+
void UpdateLotSize()
{
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double equity = AccountInfoDouble(ACCOUNT_EQUITY);

    // Simple compounding: increase lot by % when balance increases
    double profitPercent = ((equity - 10000) / 10000) * 100; // Assuming 10k initial

    if(profitPercent > Compounding_Percent)
    {
        currentLotSize = Lot_Size * (1 + (profitPercent / 100.0));
    }
    else
    {
        currentLotSize = Lot_Size;
    }

    // Normalize lot size
    double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
    double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

    currentLotSize = MathFloor(currentLotSize / lotStep) * lotStep;
    currentLotSize = MathMax(currentLotSize, minLot);
    currentLotSize = MathMin(currentLotSize, maxLot);
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
                request.deviation = 100;
                request.magic = Magic_Number;

                if(!OrderSend(request, result))
                    Print("Close position failed: ", GetLastError());
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Manage Trailing Stops                                            |
//+------------------------------------------------------------------+
void ManageTrailingStops()
{
    if(!Use_Trailing_Stop) return;

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
//| Manage Breakeven                                                 |
//+------------------------------------------------------------------+
void ManageBreakeven()
{
    if(!Use_Breakeven) return;

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

                double breakevenDistance = Breakeven_Pips * _Point * 10;

                if(posType == POSITION_TYPE_BUY)
                {
                    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                    if(currentPrice - openPrice > breakevenDistance && currentSL < openPrice)
                    {
                        ModifyPosition(PositionGetInteger(POSITION_TICKET), openPrice + 1 * _Point, currentTP);
                    }
                }
                else if(posType == POSITION_TYPE_SELL)
                {
                    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                    if(openPrice - currentPrice > breakevenDistance && (currentSL > openPrice || currentSL == 0))
                    {
                        ModifyPosition(PositionGetInteger(POSITION_TICKET), openPrice - 1 * _Point, currentTP);
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
