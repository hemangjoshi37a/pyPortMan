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
        
        
        
