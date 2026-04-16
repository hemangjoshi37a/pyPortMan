from jugaad_trader import Zerodha
import qgrid
from smartapi import SmartConnect
from rich import  print
from smartapi import SmartWebSocket
import ipywidgets
import json
import pandas as pd
import datetime
import threading
import math
import ast 
import http.client
import mimetypes
import telepot
conn = http.client.HTTPSConnection("apiconnect.angelbroking.com")
import time
from dateutil import parser, tz
from tqdm import tqdm
import nsepython
import pyotp
from client_enums import *
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


class one_client_class:
    def __init__(self,ac_broker,ac_name,ac_id,ac_pass,ac_pin,api_key='api_key',
                 totp_key='totp_key',totp_enabled='totp_enabled'
                ):
        '''one_client_class(ac_broker,ac_name,ac_id,ac_pass,ac_pin,api_key='api_key',
                            totp_key='totp_key',totp_enabled='totp_enabled')'''
        self.ac_name = ac_name
        self.ac_id = ac_id
        self.ac_pass = ac_pass
        self.ac_pin = ac_pin
        self.ac_broker = ac_broker
        self.api_key = api_key
        self.totp_key = totp_key
        self.totp_enabled = totp_enabled
        self.funds_equity = 0.00
        self.funds_commodity = 0.00
        
        self.pending_orders_list = []
        self.orders_list = []
        self.holdings_list = []
        self.positions_list = []
        self.gtt_list = []
        self.stock_status = stock_status
        
        self.zerodha_user = ''
        self.zerodha_user_data = ''
        
        self.angel_user = ''
        self.angel_user_data = {}
        self.angel_request_headers = ''
        self.angel_refreshToken = ''
        self.angel_feedToken = ''
            
        orders_list_type = type(self.pending_orders_list)
        holdings_list_type = type(self.holdings_list)
        positions_list_type = type(self.positions_list)

    def do_login(self):
        login_try_counter = 0
        try:
            if(self.ac_broker=='zerodha'):
                self.do_login_zerodha()
                return self.zerodha_user
            elif(self.ac_broker=='angel'):
                self.do_login_angel()
                return self.angel_user
        except Exception as excp:
            if(login_try_counter>=3):
                print('Login Tries exceeded...')
                return
            print(f'Error in login : {excp}')
            time.sleep(1)
#             self.do_login()
            login_try_counter+=1
                
    def get_orders_list(self) -> list:
        got_orders_list = []
        self.pending_orders_list = []
        if(self.ac_broker=='zerodha'):
            got_orders_list = self.zerodha_user.orders()
        elif(self.ac_broker=='angel'):
            got_orders_list = self.angel_user.orderBook()['data']
        if(got_orders_list==None):
            return got_orders_list  
        if(len(got_orders_list)==0):
            return got_orders_list
        for one_order in got_orders_list:
            self.orders_list.append(order_class(one_order))
        return self.orders_list

    def get_pending_orders(self) -> list:
        got_orders_list = []
        self.pending_orders_list = []
        if(self.ac_broker=='zerodha'):
            got_orders_list = self.zerodha_user.orders()
        elif(self.ac_broker=='angel'):
            got_orders_list = self.angel_user.orderBook()['data']
        if(got_orders_list==None):
            return got_orders_list  
        if(len(got_orders_list)==0):
            return got_orders_list
        for one_order in got_orders_list:
            if(one_order['status']=='OPEN' or one_order['status']=='open'):
                self.pending_orders_list.append(order_class(one_order))
                
        return self.pending_orders_list
    
    
    def get_holdings_list(self) -> list:
        got_holding_list = []
        self.holdings_list = []
        if(self.ac_broker=='zerodha'):
            got_holding_list = self.zerodha_user.holdings()
        elif(self.ac_broker=='angel'):
            got_holding_list = self.angel_user.holding()['data']
            if(got_holding_list==None):
                return []
        if(len(got_holding_list)==0):
            return got_holding_list
        for one_holding in got_holding_list:
            self.holdings_list.append(holding_class(one_holding))
        return self.holdings_list    
    
    def get_positions_list(self) -> list:
        got_positions_list = []
        self.positions_list = []
        if(self.ac_broker=='zerodha'):
            got_positions_list = self.zerodha_user.positions()['net']
        elif(self.ac_broker=='angel'):
            got_positions_list = self.angel_user.position()['data']
            if(got_positions_list==None):
                return []
        if(len(got_positions_list)==0 ):
            return got_positions_list
        for one_position in got_positions_list:
            self.positions_list.append(position_class(one_position))
        return self.positions_list
    
    
    def get_gtt_list(self) -> list:
        got_gtt_list = []
        self.gtt_list = []
        if(self.ac_broker=='zerodha'):
            got_gtt_list = self.zerodha_user.get_gtts()
        elif(self.ac_broker=='angel'):
            pass
        for one_gtt in got_gtt_list:
            self.gtt_list.append(zerodha_gtt_status_class(one_gtt))
        return self.gtt_list
        
        
    def check_funds(self):
        if(self.ac_broker=='zerodha'):
            self.funds_equity = math.floor(self.zerodha_user.margins()['equity']['available']['live_balance'])
            self.funds_commodity = math.floor(self.zerodha_user.margins()['commodity']['available']['live_balance'])
        elif(self.ac_broker=='angel'):
            self.funds_equity = math.floor(float(self.angel_user.rmsLimit()['data']['availablecash']))
            self.funds_commodity = math.floor(float(self.angel_user.rmsLimit()['data']['availablecash']))
        
    def do_login_zerodha(self):
        if(self.totp_enabled==1):
            this_totp_class = pyotp.TOTP(self.totp_key)
            this_totp_pin = this_totp_class.now()
#             print(self.totp_key)
#             print(this_totp_pin)
            self.zerodha_user = Zerodha(user_id=self.ac_id,
                                       password=self.ac_pass,
                                       twofa=int(this_totp_pin))  
        else:
            self.zerodha_user = Zerodha(user_id=self.ac_id,
                                       password=self.ac_pass,
                                       twofa=int(self.ac_pin))
        self.zerodha_user.login()
        self.zerodha_user_data = self.zerodha_user.profile()
        str1 = 'LOGIN ZERODHA : '
        print(str1 + self.zerodha_user.profile()['user_name'])
        return self.zerodha_user
                    
    def do_login_angel(self):
        self.angel_user = SmartConnect(api_key=self.api_key)
        self.angel_user_data =self.angel_user.generateSession(self.ac_id,self.ac_pass)
        self.angel_refreshToken = self.angel_user_data['data']['refreshToken']
        self.angel_feedToken=self.angel_user.getfeedToken()
        userProfile= self.angel_user.getProfile(self.angel_refreshToken)
        print (f"LOGIN ANGEL : {userProfile['data']['name']}")
        self.angel_request_headers = {
              'Authorization': f'''Bearer {self.angel_user.access_token}''',
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'X-UserType': 'USER',
              'X-SourceID': 'WEB',
              'X-ClientLocalIP': self.angel_user.clientLocalIP,
              'X-ClientPublicIP': self.angel_user.clientPublicIP,
              'X-MACAddress': self.angel_user.clientMacAddress,
              'X-PrivateKey': self.api_key
            }
        return self.angel_user

    def place_order(self, symbol, quantity, transaction_type, order_type,
                    price=None, trigger_price=None, product='CNC',
                    exchange='NSE', validity='DAY'):
        """
        Place regular market/limit orders for both Zerodha and Angel brokers.

        Args:
            symbol (str): Trading symbol (e.g., 'RELIANCE')
            quantity (int): Order quantity
            transaction_type (str): 'BUY' or 'SELL'
            order_type (str): 'MARKET' or 'LIMIT'
            price (float, optional): Limit price (required for LIMIT orders)
            trigger_price (float, optional): Trigger price for SL/SL-M orders
            product (str): Product type - 'CNC', 'MIS', 'NRML', 'BO', 'CO'
            exchange (str): Exchange - 'NSE', 'BSE', 'MCX', 'NFO'
            validity (str): Order validity - 'DAY', 'IOC'

        Returns:
            dict: Order response from broker
        """
        try:
            if self.ac_broker == 'zerodha':
                return self._place_order_zerodha(
                    symbol, quantity, transaction_type, order_type,
                    price, trigger_price, product, exchange, validity
                )
            elif self.ac_broker == 'angel':
                return self._place_order_angel(
                    symbol, quantity, transaction_type, order_type,
                    price, trigger_price, product, exchange, validity
                )
        except Exception as excp:
            print(f'Error placing order: {excp}')
            return None

    def _place_order_zerodha(self, symbol, quantity, transaction_type, order_type,
                             price, trigger_price, product, exchange, validity):
        """Place order for Zerodha broker."""
        order_params = {
            'tradingsymbol': symbol,
            'exchange': exchange,
            'quantity': quantity,
            'transaction_type': transaction_type,
            'order_type': order_type,
            'product': product,
            'validity': validity
        }

        if order_type in ['LIMIT', 'SL'] and price is not None:
            order_params['price'] = price

        if order_type in ['SL', 'SL-M'] and trigger_price is not None:
            order_params['trigger_price'] = trigger_price

        order_id = self.zerodha_user.place_order(order_params)
        print(f'Zerodha Order Placed: {order_id}')
        return {'order_id': order_id, 'status': 'success'}

    def _place_order_angel(self, symbol, quantity, transaction_type, order_type,
                           price, trigger_price, product, exchange, validity):
        """Place order for Angel broker."""
        # Get instrument token for Angel
        instrument_token = self._get_angel_instrument_token(symbol, exchange)

        order_params = {
            'variety': 'NORMAL',
            'tradingsymbol': symbol,
            'symboltoken': instrument_token,
            'transactiontype': transaction_type,
            'exchange': exchange,
            'ordertype': order_type,
            'producttype': product,
            'duration': validity,
            'price': price if price else 0,
            'squareoff': '0',
            'stoploss': '0',
            'quantity': quantity
        }

        if trigger_price:
            order_params['triggerprice'] = trigger_price

        order_id = self.angel_user.placeOrder(order_params)
        print(f'Angel Order Placed: {order_id}')
        return {'order_id': order_id, 'status': 'success'}

    def place_gtt_order(self, symbol, trigger_price, target_price,
                       quantity, transaction_type, stop_loss=None):
        """
        Create GTT (Good Till Triggered) orders with stop-loss (Zerodha only).

        Args:
            symbol (str): Trading symbol
            trigger_price (float): Price to trigger the order
            target_price (float): Target price for sell order
            quantity (int): Order quantity
            transaction_type (str): 'BUY' or 'SELL'
            stop_loss (float, optional): Stop-loss price

        Returns:
            dict: GTT order response
        """
        if self.ac_broker != 'zerodha':
            print('GTT orders are only supported for Zerodha broker')
            return None

        try:
            gtt_params = {
                'tradingsymbol': symbol,
                'exchange': 'NSE',
                'trigger_values': [trigger_price],
                'last_price': trigger_price,
                'orders': [{
                    'exchange': 'NSE',
                    'tradingsymbol': symbol,
                    'transaction_type': transaction_type,
                    'quantity': quantity,
                    'order_type': 'LIMIT',
                    'product': 'CNC',
                    'price': target_price
                }]
            }

            gtt_id = self.zerodha_user.place_gtt(gtt_params)
            print(f'GTT Order Placed: {gtt_id}')
            return {'gtt_id': gtt_id, 'status': 'success'}

        except Exception as excp:
            print(f'Error placing GTT order: {excp}')
            return None

    def cancel_order(self, order_id):
        """
        Cancel a pending order.

        Args:
            order_id (str): Order ID to cancel

        Returns:
            dict: Cancellation response
        """
        try:
            if self.ac_broker == 'zerodha':
                result = self.zerodha_user.cancel_order(order_id)
                print(f'Zerodha Order Cancelled: {order_id}')
                return {'order_id': order_id, 'status': 'cancelled', 'result': result}
            elif self.ac_broker == 'angel':
                result = self.angel_user.cancelOrder(order_id)
                print(f'Angel Order Cancelled: {order_id}')
                return {'order_id': order_id, 'status': 'cancelled', 'result': result}
        except Exception as excp:
            print(f'Error cancelling order: {excp}')
            return None

    def modify_order(self, order_id, price=None, quantity=None,
                     trigger_price=None):
        """
        Modify an existing order.

        Args:
            order_id (str): Order ID to modify
            price (float, optional): New price
            quantity (int, optional): New quantity
            trigger_price (float, optional): New trigger price

        Returns:
            dict: Modification response
        """
        try:
            if self.ac_broker == 'zerodha':
                modify_params = {'order_id': order_id}
                if price is not None:
                    modify_params['price'] = price
                if quantity is not None:
                    modify_params['quantity'] = quantity
                if trigger_price is not None:
                    modify_params['trigger_price'] = trigger_price

                result = self.zerodha_user.modify_order(order_id, modify_params)
                print(f'Zerodha Order Modified: {order_id}')
                return {'order_id': order_id, 'status': 'modified', 'result': result}

            elif self.ac_broker == 'angel':
                modify_params = {
                    'variety': 'NORMAL',
                    'orderid': order_id
                }
                if price is not None:
                    modify_params['price'] = price
                if quantity is not None:
                    modify_params['quantity'] = quantity
                if trigger_price is not None:
                    modify_params['triggerprice'] = trigger_price

                result = self.angel_user.modifyOrder(modify_params)
                print(f'Angel Order Modified: {order_id}')
                return {'order_id': order_id, 'status': 'modified', 'result': result}

        except Exception as excp:
            print(f'Error modifying order: {excp}')
            return None

    def cancel_all_orders(self):
        """
        Cancel all pending orders for an account.

        Returns:
            list: List of cancellation results
        """
        results = []
        pending_orders = self.get_pending_orders()

        for order in pending_orders:
            cancel_result = self.cancel_order(order.order_id)
            results.append({
                'order_id': order.order_id,
                'symbol': order.tradingsymbol,
                'result': cancel_result
            })

        print(f'Cancelled {len(results)} orders')
        return results

    def cancel_gtt(self, gtt_id):
        """
        Cancel a specific GTT order (Zerodha only).

        Args:
            gtt_id (str): GTT order ID to cancel

        Returns:
            dict: Cancellation response
        """
        if self.ac_broker != 'zerodha':
            print('GTT orders are only supported for Zerodha broker')
            return None

        try:
            result = self.zerodha_user.delete_gtt(gtt_id)
            print(f'GTT Order Cancelled: {gtt_id}')
            return {'gtt_id': gtt_id, 'status': 'cancelled', 'result': result}
        except Exception as excp:
            print(f'Error cancelling GTT order: {excp}')
            return None

    def _get_angel_instrument_token(self, symbol, exchange='NSE'):
        """
        Get instrument token for Angel broker (helper function).

        Args:
            symbol (str): Trading symbol
            exchange (str): Exchange

        Returns:
            str: Instrument token
        """
        # This is a placeholder - you may need to implement proper token lookup
        # based on Angel's instrument list or use their search API
        try:
            search_params = {
                'exchange': exchange,
                'searchtext': symbol
            }
            result = self.angel_user.searchscrip(search_params)
            if result and 'data' in result and len(result['data']) > 0:
                return result['data'][0]['symboltoken']
        except Exception as excp:
            print(f'Error getting instrument token: {excp}')
        return None

    # ==================== Market Data Functions ====================

    def get_quote(self, symbol, exchange='NSE'):
        """
        Get real-time quote for a stock.

        Args:
            symbol (str): Trading symbol
            exchange (str): Exchange - 'NSE', 'BSE', 'MCX', 'NFO'

        Returns:
            dict: Quote data or None
        """
        try:
            if self.ac_broker == 'zerodha':
                instrument_token = self._get_zerodha_instrument_token(symbol, exchange)
                if instrument_token:
                    quote = self.zerodha_user.quote([instrument_token])
                    if quote and len(quote) > 0:
                        return zerodha_quote_class(quote[instrument_token])
            elif self.ac_broker == 'angel':
                instrument_token = self._get_angel_instrument_token(symbol, exchange)
                if instrument_token:
                    quote_params = {
                        'exchange': exchange,
                        'symboltoken': instrument_token,
                        'interval': '1'
                    }
                    quote = self.angel_user.getLTP(quote_params)
                    if quote and 'data' in quote:
                        return quote['data']
        except Exception as excp:
            print(f'Error getting quote: {excp}')
        return None

    def get_quotes(self, symbols_list, exchange='NSE'):
        """
        Get quotes for multiple stocks.

        Args:
            symbols_list (list): List of trading symbols
            exchange (str): Exchange - 'NSE', 'BSE', 'MCX', 'NFO'

        Returns:
            dict: Dictionary of quotes keyed by symbol
        """
        quotes = {}
        try:
            if self.ac_broker == 'zerodha':
                instrument_tokens = []
                for symbol in symbols_list:
                    token = self._get_zerodha_instrument_token(symbol, exchange)
                    if token:
                        instrument_tokens.append(token)

                if instrument_tokens:
                    quote_data = self.zerodha_user.quote(instrument_tokens)
                    for i, symbol in enumerate(symbols_list):
                        if i < len(instrument_tokens):
                            quotes[symbol] = quote_data.get(instrument_tokens[i])

            elif self.ac_broker == 'angel':
                for symbol in symbols_list:
                    quote = self.get_quote(symbol, exchange)
                    if quote:
                        quotes[symbol] = quote

        except Exception as excp:
            print(f'Error getting quotes: {excp}')
        return quotes

    def get_historical_data(self, symbol, from_date, to_date, interval='day', exchange='NSE'):
        """
        Get historical OHLCV data.

        Args:
            symbol (str): Trading symbol
            from_date (str/datetime): Start date (YYYY-MM-DD or datetime object)
            to_date (str/datetime): End date (YYYY-MM-DD or datetime object)
            interval (str): Interval - 'minute', 'day', 'week', 'month'
            exchange (str): Exchange - 'NSE', 'BSE', 'MCX', 'NFO'

        Returns:
            pandas.DataFrame: Historical data with OHLCV columns
        """
        try:
            # Convert dates to proper format
            if isinstance(from_date, str):
                from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
            if isinstance(to_date, str):
                to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')

            if self.ac_broker == 'zerodha':
                instrument_token = self._get_zerodha_instrument_token(symbol, exchange)
                if instrument_token:
                    data = self.zerodha_user.historical_data(
                        instrument_token,
                        from_date,
                        to_date,
                        interval
                    )
                    return pd.DataFrame(data)

            elif self.ac_broker == 'angel':
                instrument_token = self._get_angel_instrument_token(symbol, exchange)
                if instrument_token:
                    params = {
                        'exchange': exchange,
                        'symboltoken': instrument_token,
                        'interval': interval,
                        'fromdate': from_date.strftime('%Y-%m-%d %H:%M'),
                        'todate': to_date.strftime('%Y-%m-%d %H:%M')
                    }
                    data = self.angel_user.getCandleData(params)
                    if data and 'data' in data:
                        df = pd.DataFrame(data['data'])
                        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        return df

        except Exception as excp:
            print(f'Error getting historical data: {excp}')
        return pd.DataFrame()

    def get_intraday_data(self, symbol, interval='minute', days=1, exchange='NSE'):
        """
        Get intraday candle data.

        Args:
            symbol (str): Trading symbol
            interval (str): Interval - 'minute', '5minute', '15minute', '30minute', 'hour'
            days (int): Number of days of data
            exchange (str): Exchange - 'NSE', 'BSE', 'MCX', 'NFO'

        Returns:
            pandas.DataFrame: Intraday data with OHLCV columns
        """
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=days)
        return self.get_historical_data(symbol, from_date, to_date, interval, exchange)

    def _get_zerodha_instrument_token(self, symbol, exchange='NSE'):
        """
        Get instrument token for Zerodha broker (helper function).

        Args:
            symbol (str): Trading symbol
            exchange (str): Exchange

        Returns:
            str: Instrument token
        """
        try:
            instruments = self.zerodha_user.instruments(exchange)
            for inst in instruments:
                if inst['tradingsymbol'] == symbol:
                    return inst['instrument_token']
        except Exception as excp:
            print(f'Error getting Zerodha instrument token: {excp}')
        return None

    # ==================== Portfolio Analysis Functions ====================

    def calculate_portfolio_pnl(self):
        """
        Calculate total P&L across holdings and positions.

        Returns:
            dict: Dictionary with total P&L breakdown
        """
        total_pnl = {
            'holdings_pnl': 0.0,
            'positions_pnl': 0.0,
            'total_pnl': 0.0,
            'holdings_count': 0,
            'positions_count': 0
        }

        try:
            # Calculate holdings P&L
            holdings = self.get_holdings_list()
            for holding in holdings:
                total_pnl['holdings_pnl'] += holding.pnl
                total_pnl['holdings_count'] += 1

            # Calculate positions P&L
            positions = self.get_positions_list()
            for position in positions:
                total_pnl['positions_pnl'] += position.pnl
                total_pnl['positions_count'] += 1

            total_pnl['total_pnl'] = total_pnl['holdings_pnl'] + total_pnl['positions_pnl']

        except Exception as excp:
            print(f'Error calculating portfolio P&L: {excp}')

        return total_pnl

    def get_portfolio_summary(self):
        """
        Return consolidated portfolio summary.

        Returns:
            dict: Portfolio summary with key metrics
        """
        summary = {
            'account_name': self.ac_name,
            'broker': self.ac_broker,
            'funds_equity': self.funds_equity,
            'funds_commodity': self.funds_commodity,
            'total_funds': self.funds_equity + self.funds_commodity,
            'holdings_count': 0,
            'holdings_value': 0.0,
            'positions_count': 0,
            'positions_value': 0.0,
            'total_pnl': 0.0,
            'pending_orders': 0
        }

        try:
            # Holdings summary
            holdings = self.get_holdings_list()
            for holding in holdings:
                summary['holdings_count'] += 1
                summary['holdings_value'] += holding.quantity * holding.ltp
                summary['total_pnl'] += holding.pnl

            # Positions summary
            positions = self.get_positions_list()
            for position in positions:
                summary['positions_count'] += 1
                summary['positions_value'] += position.value
                summary['total_pnl'] += position.pnl

            # Pending orders
            pending_orders = self.get_pending_orders()
            summary['pending_orders'] = len(pending_orders)

        except Exception as excp:
            print(f'Error getting portfolio summary: {excp}')

        return summary

    def get_sector_allocation(self):
        """
        Get portfolio allocation by sector.

        Returns:
            dict: Dictionary with sector-wise allocation
        """
        sector_allocation = {}

        try:
            holdings = self.get_holdings_list()

            for holding in holdings:
                # Get sector information (this may require additional API calls or data)
                # For now, using a placeholder - you may need to integrate with sector data
                sector = self._get_sector_for_symbol(holding.tradingsymbol)

                if sector not in sector_allocation:
                    sector_allocation[sector] = {
                        'count': 0,
                        'value': 0.0,
                        'pnl': 0.0
                    }

                sector_allocation[sector]['count'] += 1
                sector_allocation[sector]['value'] += holding.quantity * holding.ltp
                sector_allocation[sector]['pnl'] += holding.pnl

        except Exception as excp:
            print(f'Error getting sector allocation: {excp}')

        return sector_allocation

    def _get_sector_for_symbol(self, symbol):
        """
        Get sector for a given symbol (helper function).

        Args:
            symbol (str): Trading symbol

        Returns:
            str: Sector name
        """
        # This is a placeholder - you may need to implement proper sector lookup
        # using NSE data or maintain a sector mapping
        sector_map = {
            'RELIANCE': 'Energy',
            'TCS': 'IT',
            'INFY': 'IT',
            'HDFCBANK': 'Banking',
            'ICICIBANK': 'Banking',
            'SBIN': 'Banking',
            'TATAMOTORS': 'Auto',
            'MARUTI': 'Auto',
            'BAJFINANCE': 'Finance',
            'HDFC': 'Finance',
            'ITC': 'FMCG',
            'HINDUNILVR': 'FMCG',
            'NESTLEIND': 'FMCG',
            'LT': 'Infrastructure',
            'BHARTIARTL': 'Telecom',
            'WIPRO': 'IT',
            'AXISBANK': 'Banking',
            'KOTAKBANK': 'Banking',
            'TATASTEEL': 'Metals',
            'JSWSTEEL': 'Metals',
            'SUNPHARMA': 'Pharma',
            'DRREDDY': 'Pharma',
            'CIPLA': 'Pharma',
            'TITAN': 'Consumer',
            'ADANIENT': 'Conglomerate',
            'ADANIPORTS': 'Infrastructure',
            'POWERGRID': 'Power',
            'NTPC': 'Power',
            'ONGC': 'Energy',
            'COALINDIA': 'Energy',
            'BPCL': 'Energy',
            'HINDALCO': 'Metals',
            'ULTRACEMCO': 'Cement',
            'GRASIM': 'Cement',
            'ASIANPAINT': 'Consumer',
            'BRITANNIA': 'FMCG',
            'DABUR': 'FMCG',
            'GODREJCP': 'Consumer',
            'HCLTECH': 'IT',
            'TECHM': 'IT',
            'M&M': 'Auto',
            'EICHERMOT': 'Auto',
            'BAJAJ-AUTO': 'Auto',
            'HEROMOTOCO': 'Auto',
            'APOLLOHOSP': 'Healthcare',
            'DIVISLAB': 'Pharma',
            'LUPIN': 'Pharma',
            'AUROPHARMA': 'Pharma',
            'TATACONSUM': 'Consumer',
            'MARICO': 'FMCG',
            'GAIL': 'Energy',
            'IOC': 'Energy',
            'BPCL': 'Energy',
            'HINDPETRO': 'Energy',
            'MUTHOOTFIN': 'Finance',
            'MANAPPURAM': 'Finance',
            'CHOLAHOLDING': 'Finance',
            'BAJAJFINSV': 'Finance',
            'PNB': 'Banking',
            'BANKBARODA': 'Banking',
            'INDUSINDBK': 'Banking',
            'FEDERALBNK': 'Banking',
            'IDFCFIRSTB': 'Banking',
            'BANDHANBNK': 'Banking',
            'RBLBANK': 'Banking',
            'YESBANK': 'Banking',
            'MAHABANK': 'Banking',
            'CENTRALBK': 'Banking',
            'IOB': 'Banking',
            'UCOBANK': 'Banking',
            'ANDHRABANK': 'Banking',
            'CORPBANK': 'Banking',
            'VIJAYABANK': 'Banking',
            'DENABANK': 'Banking',
            'J&KBANK': 'Banking',
            'SOUTHIND': 'Banking',
            'KARURVYSYA': 'Banking',
            'LAKSHVIL': 'Banking',
            'DCBBANK': 'Banking',
            'CUB': 'Banking',
            'NKGSB': 'Banking',
            'SURYODAY': 'Banking',
            'JANASESH': 'Banking',
            'KSBK': 'Banking',
            'ESAF': 'Banking',
            'UJJIVAN': 'Banking',
            'FSS': 'Banking',
            'IDFC': 'Banking',
            'RELCAPITAL': 'Finance',
            'RELINFRA': 'Infrastructure',
            'ADANIPOWER': 'Power',
            'TATAPOWER': 'Power',
            'JSWENERGY': 'Power',
            'TORNTPOWER': 'Power',
            'CESC': 'Power',
            'NTPC': 'Power',
            'POWERGRID': 'Power',
            'NHPC': 'Power',
            'SJVN': 'Power',
            'THDC': 'Power',
            'SJVN': 'Power',
            'NHPC': 'Power',
            'NLCINDIA': 'Power',
            'MSEZ': 'Power',
            'ADANIGREEN': 'Power',
            'ADANISOLAR': 'Power',
            'TATACOMM': 'Telecom',
            'IDEA': 'Telecom',
            'VODAFONE': 'Telecom',
            'MTNL': 'Telecom',
            'BSNL': 'Telecom',
            'TATATELE': 'Telecom',
            'TEJASNET': 'Telecom',
            'HFCL': 'Telecom',
            'ITI': 'Telecom',
            'STL': 'Telecom',
            'TATACOMM': 'Telecom',
            'TATASTEEL': 'Metals',
            'JSWSTEEL': 'Metals',
            'HINDALCO': 'Metals',
            'VEDL': 'Metals',
            'NMDC': 'Metals',
            'MOIL': 'Metals',
            'SAIL': 'Metals',
            'RASHTRIYA': 'Metals',
            'COALINDIA': 'Metals',
            'NLCINDIA': 'Metals',
            'ADANIENT': 'Metals',
            'ADANIPORTS': 'Metals',
            'ADANIGREEN': 'Metals',
            'ADANISOLAR': 'Metals',
            'ADANITRANS': 'Metals',
            'ADANIPOWER': 'Metals',
            'ADANIGAS': 'Metals',
            'ADANIOIL': 'Metals',
            'ADANIPORTS': 'Metals',
            'ADANIGREEN': 'Metals',
            'ADANISOLAR': 'Metals',
            'ADANITRANS': 'Metals',
            'ADANIPOWER': 'Metals',
            'ADANIGAS': 'Metals',
            'ADANIOIL': 'Metals',
        }

        return sector_map.get(symbol, 'Others')

            
class my_clients_group:

    def __init__(self,user_df):
        self.user_df = user_df

    def do_login_df(self):
        self.user_list = []
        for index,one_zerodha_user_row in self.user_df.iterrows():
            this_name = one_zerodha_user_row['ac_name']
            this_uid = one_zerodha_user_row['ac_id']
            this_pass = one_zerodha_user_row['ac_pass']
            this_pin = one_zerodha_user_row['ac_pin']
            this_broker = one_zerodha_user_row['ac_broker']
            this_api_key = one_zerodha_user_row['api_key']
            this_totp_key = one_zerodha_user_row['totp_key']
            this_totp_enabled = one_zerodha_user_row['totp_enabled']

            globals()[str(this_name)] = one_client_class(this_broker,
                                                      this_name,
                                                      this_uid,
                                                      this_pass,
                                                      this_pin,
                                                   this_api_key,
                                                      this_totp_key,
                                                   this_totp_enabled, )
            globals()[str(this_name)].do_login()
            self.user_list.append(globals()[str(this_name)])

    # ==================== Multi-Account Group Functions ====================

    def get_consolidated_holdings(self):
        """
        Get holdings across all accounts.

        Returns:
            dict: Consolidated holdings with account-wise breakdown
        """
        consolidated = {
            'total_holdings': [],
            'by_account': {},
            'summary': {
                'total_value': 0.0,
                'total_pnl': 0.0,
                'total_count': 0,
                'unique_symbols': set()
            }
        }

        try:
            for client in self.user_list:
                client.check_funds()
                holdings = client.get_holdings_list()

                account_holdings = {
                    'account_name': client.ac_name,
                    'broker': client.ac_broker,
                    'funds': client.funds_equity,
                    'holdings': []
                }

                for holding in holdings:
                    holding_data = {
                        'account': client.ac_name,
                        'symbol': holding.tradingsymbol,
                        'quantity': holding.quantity,
                        'average_price': holding.average_price,
                        'ltp': holding.ltp,
                        'value': holding.quantity * holding.ltp,
                        'pnl': holding.pnl,
                        'day_change': holding.day_change if hasattr(holding, 'day_change') else 0
                    }

                    account_holdings['holdings'].append(holding_data)
                    consolidated['total_holdings'].append(holding_data)

                    # Update summary
                    consolidated['summary']['total_value'] += holding_data['value']
                    consolidated['summary']['total_pnl'] += holding_data['pnl']
                    consolidated['summary']['total_count'] += 1
                    consolidated['summary']['unique_symbols'].add(holding.tradingsymbol)

                consolidated['by_account'][client.ac_name] = account_holdings

            # Convert set to list for JSON serialization
            consolidated['summary']['unique_symbols'] = list(consolidated['summary']['unique_symbols'])

        except Exception as excp:
            print(f'Error getting consolidated holdings: {excp}')

        return consolidated

    def get_consolidated_positions(self):
        """
        Get positions across all accounts.

        Returns:
            dict: Consolidated positions with account-wise breakdown
        """
        consolidated = {
            'total_positions': [],
            'by_account': {},
            'summary': {
                'total_value': 0.0,
                'total_pnl': 0.0,
                'total_count': 0,
                'unique_symbols': set()
            }
        }

        try:
            for client in self.user_list:
                positions = client.get_positions_list()

                account_positions = {
                    'account_name': client.ac_name,
                    'broker': client.ac_broker,
                    'positions': []
                }

                for position in positions:
                    position_data = {
                        'account': client.ac_name,
                        'symbol': position.tradingsymbol,
                        'exchange': position.exchange,
                        'quantity': position.quantity,
                        'buy_price': position.buy_price,
                        'sell_price': position.sell_price,
                        'ltp': position.ltp,
                        'value': position.value,
                        'pnl': position.pnl,
                        'product': position.product
                    }

                    account_positions['positions'].append(position_data)
                    consolidated['total_positions'].append(position_data)

                    # Update summary
                    consolidated['summary']['total_value'] += position_data['value']
                    consolidated['summary']['total_pnl'] += position_data['pnl']
                    consolidated['summary']['total_count'] += 1
                    consolidated['summary']['unique_symbols'].add(position.tradingsymbol)

                consolidated['by_account'][client.ac_name] = account_positions

            # Convert set to list for JSON serialization
            consolidated['summary']['unique_symbols'] = list(consolidated['summary']['unique_symbols'])

        except Exception as excp:
            print(f'Error getting consolidated positions: {excp}')

        return consolidated

    def get_total_funds(self):
        """
        Get total available funds across all accounts.

        Returns:
            dict: Total funds breakdown by account and broker
        """
        total_funds = {
            'total_equity': 0.0,
            'total_commodity': 0.0,
            'grand_total': 0.0,
            'by_account': {},
            'by_broker': {
                'zerodha': {'equity': 0.0, 'commodity': 0.0, 'count': 0},
                'angel': {'equity': 0.0, 'commodity': 0.0, 'count': 0}
            }
        }

        try:
            for client in self.user_list:
                client.check_funds()

                account_funds = {
                    'account_name': client.ac_name,
                    'broker': client.ac_broker,
                    'equity': client.funds_equity,
                    'commodity': client.funds_commodity,
                    'total': client.funds_equity + client.funds_commodity
                }

                total_funds['by_account'][client.ac_name] = account_funds

                # Update totals
                total_funds['total_equity'] += client.funds_equity
                total_funds['total_commodity'] += client.funds_commodity

                # Update broker-wise totals
                if client.ac_broker in total_funds['by_broker']:
                    total_funds['by_broker'][client.ac_broker]['equity'] += client.funds_equity
                    total_funds['by_broker'][client.ac_broker]['commodity'] += client.funds_commodity
                    total_funds['by_broker'][client.ac_broker]['count'] += 1

            total_funds['grand_total'] = total_funds['total_equity'] + total_funds['total_commodity']

        except Exception as excp:
            print(f'Error getting total funds: {excp}')

        return total_funds

    def place_order_all_accounts(self, symbol, quantity, transaction_type, order_type,
                                  price=None, trigger_price=None, product='CNC',
                                  exchange='NSE', validity='DAY'):
        """
        Place same order across all accounts.

        Args:
            symbol (str): Trading symbol
            quantity (int): Order quantity
            transaction_type (str): 'BUY' or 'SELL'
            order_type (str): 'MARKET' or 'LIMIT'
            price (float, optional): Limit price
            trigger_price (float, optional): Trigger price
            product (str): Product type - 'CNC', 'MIS', 'NRML'
            exchange (str): Exchange - 'NSE', 'BSE', 'MCX', 'NFO'
            validity (str): Order validity - 'DAY', 'IOC'

        Returns:
            dict: Order results for each account
        """
        results = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'by_account': {}
        }

        try:
            for client in self.user_list:
                order_result = client.place_order(
                    symbol=symbol,
                    quantity=quantity,
                    transaction_type=transaction_type,
                    order_type=order_type,
                    price=price,
                    trigger_price=trigger_price,
                    product=product,
                    exchange=exchange,
                    validity=validity
                )

                results['by_account'][client.ac_name] = {
                    'broker': client.ac_broker,
                    'result': order_result,
                    'status': 'success' if order_result and order_result.get('status') == 'success' else 'failed'
                }

                results['total_orders'] += 1
                if order_result and order_result.get('status') == 'success':
                    results['successful_orders'] += 1
                else:
                    results['failed_orders'] += 1

        except Exception as excp:
            print(f'Error placing order across all accounts: {excp}')

        return results

    def get_consolidated_pnl(self):
        """
        Get consolidated P&L across all accounts.

        Returns:
            dict: Consolidated P&L breakdown
        """
        consolidated_pnl = {
            'total_pnl': 0.0,
            'holdings_pnl': 0.0,
            'positions_pnl': 0.0,
            'by_account': {},
            'by_symbol': {}
        }

        try:
            for client in self.user_list:
                pnl = client.calculate_portfolio_pnl()

                consolidated_pnl['by_account'][client.ac_name] = {
                    'broker': client.ac_broker,
                    'holdings_pnl': pnl['holdings_pnl'],
                    'positions_pnl': pnl['positions_pnl'],
                    'total_pnl': pnl['total_pnl']
                }

                consolidated_pnl['holdings_pnl'] += pnl['holdings_pnl']
                consolidated_pnl['positions_pnl'] += pnl['positions_pnl']
                consolidated_pnl['total_pnl'] += pnl['total_pnl']

        except Exception as excp:
            print(f'Error getting consolidated P&L: {excp}')

        return consolidated_pnl

    def cancel_all_orders_all_accounts(self):
        """
        Cancel all pending orders across all accounts.

        Returns:
            dict: Cancellation results for each account
        """
        results = {
            'total_cancelled': 0,
            'by_account': {}
        }

        try:
            for client in self.user_list:
                cancel_results = client.cancel_all_orders()

                results['by_account'][client.ac_name] = {
                    'broker': client.ac_broker,
                    'cancelled_count': len(cancel_results),
                    'results': cancel_results
                }

                results['total_cancelled'] += len(cancel_results)

        except Exception as excp:
            print(f'Error cancelling orders across all accounts: {excp}')

        return results

    def get_consolidated_portfolio_summary(self):
        """
        Get consolidated portfolio summary across all accounts.

        Returns:
            dict: Consolidated portfolio summary
        """
        summary = {
            'total_accounts': len(self.user_list),
            'total_funds': 0.0,
            'total_holdings_value': 0.0,
            'total_positions_value': 0.0,
            'total_pnl': 0.0,
            'total_holdings_count': 0,
            'total_positions_count': 0,
            'by_account': {}
        }

        try:
            for client in self.user_list:
                client_summary = client.get_portfolio_summary()

                summary['by_account'][client.ac_name] = client_summary

                summary['total_funds'] += client_summary['total_funds']
                summary['total_holdings_value'] += client_summary['holdings_value']
                summary['total_positions_value'] += client_summary['positions_value']
                summary['total_pnl'] += client_summary['total_pnl']
                summary['total_holdings_count'] += client_summary['holdings_count']
                summary['total_positions_count'] += client_summary['positions_count']

        except Exception as excp:
            print(f'Error getting consolidated portfolio summary: {excp}')

        return summary
            
class stock_status:
    def __init__(self,one_stock_data=object):
        self.symbol = one_stock_data['symbol']
        self.percent = one_stock_data['percent']
        self.buy_price = one_stock_data['buy']
        self.sl_price = one_stock_data['sl']
        self.target_price = one_stock_data['target']
        self.entry_open = one_stock_data['entry_open']
        self.required_qty = 0
        self.available_qty = 0
        self.holding_qty = 0
        self.position_qty = 0
        
        
        
