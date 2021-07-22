
class order_class:
    def __init__(self,order):
        if('guid' in order.keys()):
            self.broker = 'zerodha'
            self.order = order
            self.variety = self.order['variety']
            self.ordertype = self.order['order_type']
            self.producttype = self.order['product']
            self.price = self.order['price']
            self.triggerprice = self.order['trigger_price']
            self.quantity = self.order['quantity']
            self.disclosedquantity = self.order['disclosed_quantity']
            self.tradingsymbol = self.order['tradingsymbol']
            self.transactiontype = self.order['transaction_type']
            self.exchange = self.order['exchange']
            self.instrument_token = self.order['instrument_token']
            self.ordertag = self.order['tag']
            self.cancelled_quantity = self.order['cancelled_quantity']
            self.average_price = self.order['average_price']
            self.filled_quantity = self.order['filled_quantity']
            self.order_id = self.order['order_id']
            self.status = self.order['status']
            self.pending_quantity = self.order['pending_quantity']
            self.exchange_update_timestamp = self.order['exchange_update_timestamp']
            self.exchange_timestamp = self.order['exchange_timestamp']
            self.order_timestamp = self.order['order_timestamp']
            self.exchange_order_id = self.order['exchange_order_id']
            self.parent_order_id = self.order['parent_order_id']
            self.validity = self.order['validity']
            self.placed_by = self.order['placed_by']
            self.status_message = self.order['status_message']
            self.status_message_raw = self.order['status_message_raw']
            self.market_protection = self.order['market_protection']
            self.meta = self.order['meta']
            self.guid = self.order['guid']
        if('text' in order.keys()):
            self.broker = 'angel'
            self.order = order
            self.variety = self.order['variety']
            self.ordertype = self.order['ordertype']
            self.producttype = self.order['producttype']
            self.price = self.order['price']
            self.triggerprice = self.order['triggerprice']
            self.quantity = self.order['quantity']
            self.disclosedquantity = self.order['disclosedquantity']
            self.tradingsymbol = self.order['tradingsymbol']
            self.transactiontype = self.order['transactiontype']
            self.exchange = self.order['exchange']
            self.instrument_token = self.order['symboltoken']
            self.ordertag = self.order['ordertag']
            self.cancelled_quantity = self.order['cancelsize']
            self.average_price = self.order['averageprice']
            self.filled_quantity = self.order['filledshares']
            self.order_id = self.order['orderid']
            self.status = self.order['status']
            self.pending_quantity = self.order['unfilledshares']
            self.exchange_update_timestamp = self.order['updatetime']
            self.exchange_timestamp = self.order['exchtime']
            self.order_timestamp = self.order['exchorderupdatetime']
            self.exchange_order_id = self.order['fillid']
            self.parent_order_id = self.order['parentorderid']
            self.validity = self.order['duration']
            self.filltime = self.order['filltime']
            self.squareoff = self.order['squareoff']
            self.stoploss = self.order['stoploss']
            self.trailingstoploss = self.order['trailingstoploss']
            self.instrumenttype = self.order['instrumenttype']
            self.strikeprice = self.order['strikeprice']
            self.optiontype = self.order['optiontype']
            self.expirydate = self.order['expirydate']
            self.lotsize = self.order['lotsize']
            self.text = self.order['text']
            self.orderstatus = self.order['orderstatus']

class position_class:
    def __init__(self,position):
        if('overnight_quantity' in position.keys()):
            self.broker = 'zerodha'
            self.position = position       
            self.tradingsymbol = self.position['tradingsymbol']
            self.exchange = self.position['exchange']
            self.instrument_token = self.position['instrument_token']
            self.buy_price = self.position['buy_price']
            self.sell_price = self.position['sell_price']
            self.pnl = self.position['pnl']
            self.value = self.position['value']
            self.buy_quantity = self.position['buy_quantity']
            self.sell_quantity = self.position['sell_quantity']
            self.multiplier = self.position['multiplier']
            self.quantity = self.position['quantity']
            self.product = self.position['product']
            self.buy_value = self.position['buy_value']
            self.sell_value = self.position['sell_value']
            self.realised = self.position['realised']
            self.unrealised = self.position['unrealised']
            self.close_price = self.position['close_price']
            self.ltp = self.position['last_price']
            self.overnight_quantity = self.position['overnight_quantity']
            self.average_price = self.position['average_price']
            self.m2m = self.position['m2m']
            self.buy_m2m = self.position['buy_m2m']
            self.sell_m2m = self.position['sell_m2m']
            self.day_buy_quantity = self.position['day_buy_quantity']
            self.day_buy_price = self.position['day_buy_price']
            self.day_buy_value = self.position['day_buy_value']
            self.day_sell_quantity = self.position['day_sell_quantity']
            self.day_sell_price = self.position['day_sell_price']
            self.day_sell_value = self.position['day_sell_value']
        if('cfbuyqty' in position.keys()):
            self.broker = 'angel'
            self.position = position
            self.tradingsymbol = self.position['tradingsymbol']
            self.exchange = self.position['exchange']
            self.instrument_token = self.position['symboltoken']
            self.buy_price = self.position['buyavgprice']
            self.sell_price = self.position['sellavgprice']            
            self.pnl = self.position['pnl']
            self.value = self.position['netvalue']
            self.buy_quantity = self.position['buyqty']
            self.sell_quantity = self.position['sellqty']
            self.multiplier = self.position['multiplier']
            self.quantity = self.position['netqty']
            self.product = self.position['producttype']
            self.buy_value = self.position['totalbuyvalue']
            self.sell_value = self.position['totalsellvalue']
            self.realised = self.position['realised']
            self.unrealised = self.position['unrealised']
            self.close_price = self.position['close']
            self.ltp = self.position['ltp']
            self.symbolgroup = self.position['symbolgroup']
            self.strikeprice = self.position['strikeprice']
            self.expirydate = self.position['expirydate']
            self.lotsize = self.position['lotsize']
            self.cfbuyqty = self.position['cfbuyqty']
            self.cfsellqty = self.position['cfsellqty']
            self.cfbuyamount = self.position['cfbuyamount']
            self.cfsellamount = self.position['cfsellamount']
            self.avgnetprice = self.position['avgnetprice']
            self.cfbuyavgprice = self.position['cfbuyavgprice']
            self.cfsellavgprice = self.position['cfsellavgprice']
            self.totalbuyavgprice = self.position['totalbuyavgprice']
            self.totalsellavgprice = self.position['totalsellavgprice']
            self.netprice = self.position['netprice']
            self.buyamount = self.position['buyamount']
            self.sellamount = self.position['sellamount']
            self.symbolname = self.position['symbolname']
            self.instrumenttype = self.position['instrumenttype']
            self.optiontype = self.position['optiontype']
            self.priceden = self.position['priceden']
            self.pricenum = self.position['pricenum']            
            self.genden = self.position['genden']
            self.gennum = self.position['gennum']            
            self.precision = self.position['precision']
            self.boardlotsize = self.position['boardlotsize']

class holding_class:
    def __init__(self,holding):
        if('day_change_percentage' in holding.keys()):
            self.broker = 'zerodha'
            self.holding = holding 
            self.tradingsymbol = self.holding['tradingsymbol']
            self.exchange = self.holding['exchange']
            self.isin = self.holding['isin']
            self.instrument_token = self.holding['instrument_token']
            self.close_price = self.holding['close_price']
            self.ltp = self.holding['last_price']
            self.product = self.holding['product']
            self.t1_quantity = self.holding['t1_quantity']
            self.realised_quantity = self.holding['realised_quantity']
            self.quantity = self.holding['quantity']
            self.authorised_quantity = self.holding['authorised_quantity']
            self.pnl = self.holding['pnl']
            self.collateral_quantity = self.holding['collateral_quantity']
            self.collateral_type = self.holding['collateral_type']
            self.price = self.holding['price']
            self.used_quantity = self.holding['used_quantity']
            self.authorised_date = self.holding['authorised_date']
            self.opening_quantity = self.holding['opening_quantity']
            self.discrepancy = self.holding['discrepancy']
            self.average_price = self.holding['average_price']
            self.day_change = self.holding['day_change']
            self.day_change_percentage = self.holding['day_change_percentage']
        if('haircut' in holding.keys()):
            self.broker = 'angel'
            self.holding = holding 
            self.tradingsymbol = self.holding['tradingsymbol']
            self.exchange = self.holding['exchange']
            self.isin = self.holding['isin']
            self.instrument_token = self.holding['symboltoken']
            self.close_price = self.holding['close']
            self.ltp = self.holding['ltp']
            self.product = self.holding['product']
            self.t1_quantity = self.holding['t1quantity']
            self.realised_quantity = self.holding['realisedquantity']
            self.quantity = self.holding['quantity']
            self.authorised_quantity = self.holding['authorisedquantity']
            self.pnl = self.holding['profitandloss']
            self.collateral_quantity = self.holding['collateralquantity']
            self.collateral_type = self.holding['collateraltype']
            self.price = self.holding['averageprice']
            self.haircut = self.holding['haircut']
            
class zerodha_quote_class:
    def __init__(self,quote):
        self.broker = 'zerodha'
        self.quote = quote
        self.instrument_token = quote['instrument_token']
        self.timestamp = quote['timestamp']
        self.last_trade_time = quote['last_trade_time']
        self.last_price = quote['last_price']
        self.last_quantity = quote['last_quantity']
        self.buy_quantity = quote['buy_quantity']
        self.sell_quantity = quote['sell_quantity']
        self.volume = quote['volume']
        self.average_price = quote['average_price']
        self.oi = quote['oi']
        self.oi_day_high = quote['oi_day_high']
        self.oi_day_low = quote['oi_day_low']
        self.net_change = quote['net_change']
        self.lower_circuit_limit = quote['lower_circuit_limit']
        self.upper_circuit_limit = quote['upper_circuit_limit']
        self.ohlc = quote['ohlc']
        self.depth = quote['depth']
        self.depth_buy = quote['depth']['buy']
        self.depth_sell = quote['depth']['sell']
        self.open = quote['ohlc']['open']
        self.high = quote['ohlc']['high']
        self.low = quote['ohlc']['low']
        self.close = quote['ohlc']['close']
        counter1 = 1
        for one_depth in quote['depth']['buy']:
            locals()['self.buy_depth_qty_'+str(counter1)] = one_depth['quantity']
            locals()['self.buy_depth_price_'+str(counter1)] = one_depth['price']
            locals()['self.buy_depth_orders_'+str(counter1)] = one_depth['orders']
            counter1+=1
        counter1 = 1
        for one_depth in quote['depth']['sell']:
            locals()['self.sell_depth_qty_'+str(counter1)] = one_depth['quantity']
            locals()['self.sell_depth_price_'+str(counter1)] = one_depth['price']
            locals()['self.sell_depth_orders_'+str(counter1)] = one_depth['orders']
            counter1+=1
        
class gtt_condition:
#     {'exchange': 'NSE',
#    'last_price': 203.9,
#    'tradingsymbol': 'DATAMATICS',
#    'trigger_values': [203]},
    def __init__(self,condition):
        self.condition = condition
        self.exchange = condition['exchange']
        self.last_price = condition['last_price']
        self.tradingsymbol = condition['tradingsymbol']
        self.trigger_value_list = condition['trigger_values']
        len_counter = 0
        for one in condition['trigger_values']:
            len_counter+=1
        if(len_counter==2):
           self.trigger_value_1 = condition['trigger_values'][0]
           self.trigger_value_2 = condition['trigger_values'][1]
        else:
           self.trigger_value_1 = condition['trigger_values'][0]
           self.trigger_value_2 = 0.0
           
class gtt_orders:
    def __init__(self,orders):
        self.orders = orders
        self.exchange_1 = orders[0]['exchange']
        self.tradingsymbol_1 = orders[0]['tradingsymbol']
        self.product_1 = orders[0]['product']
        self.order_type_1 = orders[0]['order_type']
        self.transaction_type_1 = orders[0]['transaction_type']
        self.quantity_1 = orders[0]['quantity']
        self.price_1 = orders[0]['price']
        self.result_1 = orders[0]['result']
        len_counter = 0
        for one in orders:
            len_counter+=1
        if(len_counter==2):
            self.exchange_2 = orders[1]['exchange']
            self.tradingsymbol_2 = orders[1]['tradingsymbol']
            self.product_2 = orders[1]['product']
            self.order_type_2 = orders[1]['order_type']
            self.transaction_type_2 = orders[1]['transaction_type']
            self.quantity_2 = orders[1]['quantity']
            self.price_2 = orders[1]['price']
            self.result_2 = orders[1]['result']

          
class zerodha_gtt_status_class:
    def __init__(self,gtt):
        self.gtt = gtt
        self.broker = 'zerodha'
        self.id = gtt['id']
        self.user_id = gtt['user_id']
        self.parent_trigger = gtt['parent_trigger']
        self.type = gtt['type']
        self.created_at = gtt['created_at']
        self.updated_at = gtt['updated_at']
        self.expires_at = gtt['expires_at']
        self.status = gtt['status']
        self.condition = gtt_condition(gtt['condition'])
        self.orders = gtt_orders(gtt['orders'])
        
        
        
        
def flatten_json(y):
    out = {}
    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x
    flatten(y)
    return out

