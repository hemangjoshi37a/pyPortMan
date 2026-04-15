//+------------------------------------------------------------------+
//|                                            Hedging_Grid_EA.mq5    |
//|                        EMA + RSI True Hedging EA                 |
//+------------------------------------------------------------------+
#property copyright "Hedging Grid EA"
#property version   "3.00"
#property strict

//--- Input Parameters
input group "=== EMA Settings ==="
input int      EMA_Fast_Period = 11;              // Fast EMA Period
input int      EMA_Slow_Period = 21;              // Slow EMA Period
input ENUM_TIMEFRAMES EMA_Timeframe = PERIOD_M15; // EMA Timeframe

input group "=== RSI Settings ==="
input int      RSI_Period = 14;                   // RSI Period
input int      RSI_Overbought = 70;               // RSI Overbought Level
input int      RSI_Oversold = 30;                // RSI Oversold Level

input group "=== Grid Settings ==="
input int      Grid_Positions_Per_Side = 6;       // Positions per side (Buy + Sell)
input double   Grid_Lot_Size = 0.01;              // Lot Size per Position
input int      Grid_Spacing_Pips = 20;            // Grid Spacing (pips)
input bool     Open_All_At_Once = true;           // Open All Positions at Once

input group "=== Directional Close Settings ==="
input int      Close_Losing_Side_Pips = 30;       // Close losing side after X pips move
input bool     Close_Losing_On_Profit = true;     // Close losing side when winning side in profit

input group "=== Exit Settings ==="
input double   Total_Profit_Target = 15.0;        // Total Profit Target (currency)
input double   Max_Loss_Limit = 50.0;             // Max Loss Limit (currency)

input group "=== Risk Management ==="
input int      Max_Spread = 30;                   // Max Spread (points)
input int      Magic_Number = 789012;             // Magic Number

input group "=== Time Filter ==="
input bool     Use_Time_Filter = false;           // Use Time Filter
input int      Start_Hour = 8;                    // Start Hour
input int      End_Hour = 20;                     // End Hour

input group "=== Other Settings ==="
input int      Slippage = 10;                     // Max Slippage (points)
input bool     Show_Comments = true;              // Show Comments on Chart

//--- Global Variables
int emaFastHandle, emaSlowHandle, rsiHandle;
double emaFastBuffer[], emaSlowBuffer[], rsiBuffer[];

// Grid state tracking
bool gridActive = false;
double gridBasePrice = 0;
int buyPositionsOpened = 0;
int sellPositionsOpened = 0;
datetime lastTradeTime = 0;

// Directional close tracking
bool losingSideClosed = false;
ENUM_POSITION_TYPE winningSide = POSITION_TYPE_BUY; // Default

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    // Initialize EMA indicators
    emaFastHandle = iMA(_Symbol, EMA_Timeframe, EMA_Fast_Period, 0, MODE_EMA, PRICE_CLOSE);
    emaSlowHandle = iMA(_Symbol, EMA_Timeframe, EMA_Slow_Period, 0, MODE_EMA, PRICE_CLOSE);

    if(emaFastHandle == INVALID_HANDLE || emaSlowHandle == INVALID_HANDLE)
    {
        Print("Error creating EMA indicator handles: ", GetLastError());
        return INIT_FAILED;
    }

    // Initialize RSI indicator
    rsiHandle = iRSI(_Symbol, EMA_Timeframe, RSI_Period, PRICE_CLOSE);

    if(rsiHandle == INVALID_HANDLE)
    {
        Print("Error creating RSI indicator handle: ", GetLastError());
        IndicatorRelease(emaFastHandle);
        IndicatorRelease(emaSlowHandle);
        return INIT_FAILED;
    }

    // Set arrays as series
    ArraySetAsSeries(emaFastBuffer, true);
    ArraySetAsSeries(emaSlowBuffer, true);
    ArraySetAsSeries(rsiBuffer, true);

    // Reset grid state
    gridActive = false;
    gridBasePrice = 0;
    buyPositionsOpened = 0;
    sellPositionsOpened = 0;
    losingSideClosed = false;

    Print("Hedging Grid EA v3.0 initialized successfully");
    Print("Positions per side: ", Grid_Positions_Per_Side, " | Total: ", Grid_Positions_Per_Side * 2);
    Print("Lot Size: ", Grid_Lot_Size, " | Grid Spacing: ", Grid_Spacing_Pips, " pips");
    Print("Close losing side after: ", Close_Losing_Side_Pips, " pips");
    Print("Profit Target: $", Total_Profit_Target);

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    if(emaFastHandle != INVALID_HANDLE) IndicatorRelease(emaFastHandle);
    if(emaSlowHandle != INVALID_HANDLE) IndicatorRelease(emaSlowHandle);
    if(rsiHandle != INVALID_HANDLE) IndicatorRelease(rsiHandle);

    Comment("");
    Print("Hedging Grid EA deinitialized");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check spread
    double spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
    if(spread > Max_Spread)
    {
        if(Show_Comments)
            Comment("Spread too high: ", spread, " > ", Max_Spread);
        return;
    }

    // Time filter
    if(Use_Time_Filter && !IsTradingTime())
    {
        if(Show_Comments)
            Comment("Outside trading hours");
        return;
    }

    // Update indicator data
    int lookback = MathMax(EMA_Fast_Period, EMA_Slow_Period) + MathMax(RSI_Period, 10) + 5;

    if(CopyBuffer(emaFastHandle, 0, 0, lookback, emaFastBuffer) <= 0) return;
    if(CopyBuffer(emaSlowHandle, 0, 0, lookback, emaSlowBuffer) <= 0) return;
    if(CopyBuffer(rsiHandle, 0, 0, lookback, rsiBuffer) <= 0) return;

    // Get current price
    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);

    // Count existing positions
    int currentBuyPositions = CountPositionsByType(POSITION_TYPE_BUY);
    int currentSellPositions = CountPositionsByType(POSITION_TYPE_SELL);
    int currentTotalPositions = currentBuyPositions + currentSellPositions;

    // Check if we have positions from previous session
    if(currentTotalPositions > 0 && !gridActive)
    {
        // Recover grid state from existing positions
        RecoverGridState(currentBuyPositions, currentSellPositions);
    }

    // Check total profit/loss
    double totalProfit = GetTotalProfit();
    double buyProfit = GetProfitByType(POSITION_TYPE_BUY);
    double sellProfit = GetProfitByType(POSITION_TYPE_SELL);

    // Check max loss limit
    if(totalProfit <= -Max_Loss_Limit && Max_Loss_Limit > 0)
    {
        Print("Max loss limit reached: $", totalProfit, ". Closing all positions.");
        CloseAllPositions();
        gridActive = false;
        return;
    }

    // Check if grid is active
    if(gridActive)
    {
        // Check if profit target reached
        if(totalProfit >= Total_Profit_Target)
        {
            Print("Profit target reached: $", totalProfit, ". Closing all positions.");
            CloseAllPositions();
            gridActive = false;
            return;
        }

        // DIRECTIONAL CLOSE LOGIC
        if(!losingSideClosed)
        {
            double priceMovePips = (currentPrice - gridBasePrice) / (_Point * 10);

            // Price moved UP - SELL positions are losing
            if(priceMovePips >= Close_Losing_Side_Pips)
            {
                if(Close_Losing_On_Profit && buyProfit > 0)
                {
                    Print("Price moved UP ", priceMovePips, " pips. BUY in profit. Closing SELL positions.");
                    ClosePositionsByType(POSITION_TYPE_SELL);
                    losingSideClosed = true;
                    winningSide = POSITION_TYPE_BUY;
                }
                else if(!Close_Losing_On_Profit)
                {
                    Print("Price moved UP ", priceMovePips, " pips. Closing SELL positions.");
                    ClosePositionsByType(POSITION_TYPE_SELL);
                    losingSideClosed = true;
                    winningSide = POSITION_TYPE_BUY;
                }
            }
            // Price moved DOWN - BUY positions are losing
            else if(priceMovePips <= -Close_Losing_Side_Pips)
            {
                if(Close_Losing_On_Profit && sellProfit > 0)
                {
                    Print("Price moved DOWN ", MathAbs(priceMovePips), " pips. SELL in profit. Closing BUY positions.");
                    ClosePositionsByType(POSITION_TYPE_BUY);
                    losingSideClosed = true;
                    winningSide = POSITION_TYPE_SELL;
                }
                else if(!Close_Losing_On_Profit)
                {
                    Print("Price moved DOWN ", MathAbs(priceMovePips), " pips. Closing BUY positions.");
                    ClosePositionsByType(POSITION_TYPE_BUY);
                    losingSideClosed = true;
                    winningSide = POSITION_TYPE_SELL;
                }
            }
        }

        // Continue opening grid positions if not all opened
        if(buyPositionsOpened < Grid_Positions_Per_Side || sellPositionsOpened < Grid_Positions_Per_Side)
        {
            if(Open_All_At_Once)
            {
                // Open remaining positions (only if losing side not closed)
                if(!losingSideClosed || winningSide == POSITION_TYPE_BUY)
                {
                    while(buyPositionsOpened < Grid_Positions_Per_Side)
                    {
                        OpenGridPosition(POSITION_TYPE_BUY, buyPositionsOpened);
                    }
                }
                if(!losingSideClosed || winningSide == POSITION_TYPE_SELL)
                {
                    while(sellPositionsOpened < Grid_Positions_Per_Side)
                    {
                        OpenGridPosition(POSITION_TYPE_SELL, sellPositionsOpened);
                    }
                }
            }
            else
            {
                // Check if we should open next position
                if(ShouldOpenNextPosition(currentPrice))
                {
                    OpenNextGridPosition();
                }
            }
        }
    }
    else
    {
        // No active grid, check for entry signal
        if(currentTotalPositions == 0)
        {
            int signal = GetEntrySignal();

            if(signal != 0)
            {
                Print("Entry signal detected. Starting HEDGING grid at price: ", currentPrice);
                StartHedgingGrid();
            }
        }
    }

    // Update chart comment
    if(Show_Comments)
    {
        UpdateChartComment(totalProfit, buyProfit, sellProfit, currentBuyPositions, currentSellPositions);
    }
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
//| Get Entry Signal (EMA + RSI)                                     |
//+------------------------------------------------------------------+
int GetEntrySignal()
{
    // Returns: 1 = good entry point, 0 = no signal
    // For hedging, we just need a good entry point to start the grid

    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double emaFast = emaFastBuffer[0];
    double emaSlow = emaSlowBuffer[0];
    double rsi = rsiBuffer[0];

    // Entry signal: Price is near EMA and RSI is in neutral zone
    bool nearEMA = (MathAbs(currentPrice - emaFast) < (Grid_Spacing_Pips * _Point * 10));
    bool neutralRSI = (rsi > 40 && rsi < 60);

    // Alternative: Strong trend with RSI not extreme
    bool strongUptrend = (currentPrice > emaFast && emaFast > emaSlow && rsi > 50 && rsi < RSI_Overbought);
    bool strongDowntrend = (currentPrice < emaFast && emaFast < emaSlow && rsi < 50 && rsi > RSI_Oversold);

    if(nearEMA && neutralRSI) return 1;
    if(strongUptrend || strongDowntrend) return 1;

    return 0;
}

//+------------------------------------------------------------------+
//| Start New Hedging Grid (Buy + Sell)                              |
//+------------------------------------------------------------------+
void StartHedgingGrid()
{
    gridActive = true;
    gridBasePrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    buyPositionsOpened = 0;
    sellPositionsOpened = 0;
    losingSideClosed = false;

    Print("Starting HEDGING grid at base price: ", gridBasePrice);
    Print("Will open ", Grid_Positions_Per_Side, " BUY and ", Grid_Positions_Per_Side, " SELL positions");

    if(Open_All_At_Once)
    {
        // Open all positions at once
        for(int i = 0; i < Grid_Positions_Per_Side; i++)
        {
            OpenGridPosition(POSITION_TYPE_BUY, i);
        }
        for(int i = 0; i < Grid_Positions_Per_Side; i++)
        {
            OpenGridPosition(POSITION_TYPE_SELL, i);
        }
    }
    else
    {
        // Open first buy and sell positions
        OpenGridPosition(POSITION_TYPE_BUY, 0);
        OpenGridPosition(POSITION_TYPE_SELL, 0);
    }
}

//+------------------------------------------------------------------+
//| Open Grid Position                                                |
//+------------------------------------------------------------------+
void OpenGridPosition(ENUM_POSITION_TYPE posType, int index)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};

    double lot = Grid_Lot_Size;
    double pipSize = _Point * 10; // 1 pip = 10 points
    double entryPrice;

    // Calculate entry price based on grid spacing
    if(posType == POSITION_TYPE_BUY)
    {
        // Buy positions below current price
        entryPrice = gridBasePrice - (index * Grid_Spacing_Pips * pipSize);
    }
    else // SELL
    {
        // Sell positions above current price
        entryPrice = gridBasePrice + (index * Grid_Spacing_Pips * pipSize);
    }

    // Normalize price
    int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
    entryPrice = NormalizeDouble(entryPrice, digits);

    // Set up order
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = lot;
    request.type = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
    request.price = (posType == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
    request.deviation = Slippage;
    request.magic = Magic_Number;
    request.comment = (posType == POSITION_TYPE_BUY) ? "BUY_" + IntegerToString(index + 1) : "SELL_" + IntegerToString(index + 1);

    // No SL/TP - managed by total profit

    if(!OrderSend(request, result))
    {
        Print("Grid position ", (posType == POSITION_TYPE_BUY ? "BUY" : "SELL"), " ", index + 1, " failed: ", GetLastError());
    }
    else
    {
        if(posType == POSITION_TYPE_BUY)
        {
            buyPositionsOpened++;
            Print("BUY position ", index + 1, " opened. Total BUY: ", buyPositionsOpened, "/", Grid_Positions_Per_Side);
        }
        else
        {
            sellPositionsOpened++;
            Print("SELL position ", index + 1, " opened. Total SELL: ", sellPositionsOpened, "/", Grid_Positions_Per_Side);
        }
    }
}

//+------------------------------------------------------------------+
//| Open Next Grid Position                                          |
//+------------------------------------------------------------------+
void OpenNextGridPosition()
{
    // Alternate between buy and sell
    if(buyPositionsOpened <= sellPositionsOpened && buyPositionsOpened < Grid_Positions_Per_Side)
    {
        OpenGridPosition(POSITION_TYPE_BUY, buyPositionsOpened);
    }
    else if(sellPositionsOpened < Grid_Positions_Per_Side)
    {
        OpenGridPosition(POSITION_TYPE_SELL, sellPositionsOpened);
    }
}

//+------------------------------------------------------------------+
//| Check if Next Position Should Be Opened                          |
//+------------------------------------------------------------------+
bool ShouldOpenNextPosition(double currentPrice)
{
    if(buyPositionsOpened >= Grid_Positions_Per_Side && sellPositionsOpened >= Grid_Positions_Per_Side)
        return false;

    double pipSize = _Point * 10;

    // Check if price reached next buy level
    if(buyPositionsOpened < Grid_Positions_Per_Side)
    {
        double buyTarget = gridBasePrice - (buyPositionsOpened * Grid_Spacing_Pips * pipSize);
        if(currentPrice <= buyTarget)
            return true;
    }

    // Check if price reached next sell level
    if(sellPositionsOpened < Grid_Positions_Per_Side)
    {
        double sellTarget = gridBasePrice + (sellPositionsOpened * Grid_Spacing_Pips * pipSize);
        if(currentPrice >= sellTarget)
            return true;
    }

    return false;
}

//+------------------------------------------------------------------+
//| Get Total Profit of All EA Positions                             |
//+------------------------------------------------------------------+
double GetTotalProfit()
{
    double totalProfit = 0;

    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                totalProfit += PositionGetDouble(POSITION_PROFIT);
            }
        }
    }

    return totalProfit;
}

//+------------------------------------------------------------------+
//| Get Profit by Position Type                                      |
//+------------------------------------------------------------------+
double GetProfitByType(ENUM_POSITION_TYPE type)
{
    double profit = 0;

    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number &&
               PositionGetInteger(POSITION_TYPE) == type)
            {
                profit += PositionGetDouble(POSITION_PROFIT);
            }
        }
    }

    return profit;
}

//+------------------------------------------------------------------+
//| Count Positions by Type                                          |
//+------------------------------------------------------------------+
int CountPositionsByType(ENUM_POSITION_TYPE type)
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
//| Count All EA Positions                                            |
//+------------------------------------------------------------------+
int CountEAPositions()
{
    return CountPositionsByType(POSITION_TYPE_BUY) + CountPositionsByType(POSITION_TYPE_SELL);
}

//+------------------------------------------------------------------+
//| Close All EA Positions                                           |
//+------------------------------------------------------------------+
void CloseAllPositions()
{
    int closed = 0;

    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByTicket(PositionGetTicket(i)))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
               PositionGetInteger(POSITION_MAGIC) == Magic_Number)
            {
                MqlTradeRequest request = {};
                MqlTradeResult result = {};

                request.action = TRADE_ACTION_DEAL;
                request.symbol = _Symbol;
                request.volume = PositionGetDouble(POSITION_VOLUME);
                request.type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ?
                              ORDER_TYPE_SELL : ORDER_TYPE_BUY;
                request.position = PositionGetInteger(POSITION_TICKET);
                request.price = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ?
                               SymbolInfoDouble(_Symbol, SYMBOL_BID) :
                               SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                request.deviation = Slippage;
                request.magic = Magic_Number;

                if(OrderSend(request, result))
                {
                    closed++;
                }
            }
        }
    }

    Print("Closed ", closed, " positions");
}

//+------------------------------------------------------------------+
//| Close Positions by Type                                           |
//+------------------------------------------------------------------+
void ClosePositionsByType(ENUM_POSITION_TYPE type)
{
    int closed = 0;

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
                request.deviation = Slippage;
                request.magic = Magic_Number;

                if(OrderSend(request, result))
                {
                    closed++;
                }
            }
        }
    }

    Print("Closed ", closed, " ", (type == POSITION_TYPE_BUY ? "BUY" : "SELL"), " positions");
}

//+------------------------------------------------------------------+
//| Recover Grid State from Existing Positions                       |
//+------------------------------------------------------------------+
void RecoverGridState(int buyCount, int sellCount)
{
    if(buyCount > 0 || sellCount > 0)
    {
        gridActive = true;
        buyPositionsOpened = buyCount;
        sellPositionsOpened = sellCount;

        // Determine if losing side was already closed
        if(buyCount > 0 && sellCount == 0)
        {
            losingSideClosed = true;
            winningSide = POSITION_TYPE_BUY;
            Print("Recovered: Only BUY positions remain. SELL side was closed.");
        }
        else if(sellCount > 0 && buyCount == 0)
        {
            losingSideClosed = true;
            winningSide = POSITION_TYPE_SELL;
            Print("Recovered: Only SELL positions remain. BUY side was closed.");
        }
        else
        {
            losingSideClosed = false;
            Print("Recovered grid state: ", buyCount, " BUY, ", sellCount, " SELL positions");
        }
    }
}

//+------------------------------------------------------------------+
//| Update Chart Comment                                             |
//+------------------------------------------------------------------+
void UpdateChartComment(double totalProfit, double buyProfit, double sellProfit, int buyCount, int sellCount)
{
    string statusStr = gridActive ? "ACTIVE" : "WAITING";
    int totalPositions = buyCount + sellCount;
    int maxPositions = Grid_Positions_Per_Side * 2;

    double priceMovePips = 0;
    if(gridActive)
    {
        double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
        priceMovePips = (currentPrice - gridBasePrice) / (_Point * 10);
    }

    string comment = "=== Hedging Grid EA v3.0 ===\n";
    comment += "Status: " + statusStr + "\n";
    comment += "Base Price: " + DoubleToString(gridBasePrice, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)) + "\n";
    comment += "Price Move: " + DoubleToString(priceMovePips, 1) + " pips\n";
    comment += "------------------------\n";
    comment += "BUY Positions: " + IntegerToString(buyCount) + "/" + IntegerToString(Grid_Positions_Per_Side) + "\n";
    comment += "BUY Profit: $" + DoubleToString(buyProfit, 2) + "\n";
    comment += "------------------------\n";
    comment += "SELL Positions: " + IntegerToString(sellCount) + "/" + IntegerToString(Grid_Positions_Per_Side) + "\n";
    comment += "SELL Profit: $" + DoubleToString(sellProfit, 2) + "\n";
    comment += "------------------------\n";
    comment += "Total Positions: " + IntegerToString(totalPositions) + "/" + IntegerToString(maxPositions) + "\n";
    comment += "Total Profit: $" + DoubleToString(totalProfit, 2) + "\n";
    comment += "Profit Target: $" + DoubleToString(Total_Profit_Target, 2) + "\n";
    comment += "Max Loss: $" + DoubleToString(Max_Loss_Limit, 2) + "\n";

    Comment(comment);
}
//+------------------------------------------------------------------+
