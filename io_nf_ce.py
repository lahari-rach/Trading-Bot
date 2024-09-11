#!/bin/python3
from kiteconnect import KiteConnect
import pandas as pd
from pytz import timezone
import datetime
import time
from datetime import timedelta
from datetime import datetime
import zrd_login
import numpy as np
import threading
import math
import csv
import os
import ast
import logging
import calendar
import tkinter as tk
import gc
#import everything from tkinter module
from tkinter import *
from tkinter import ttk
from tkinter import messagebox as mb
from tti.indicators import StochasticMomentumIndex
import talib
#from talib import RSI
import pandas_ta as ta
#import boto3
global dict_inputs
global dict_runtime_inputs
global dict_runtime_inputs_default
global dict_data
global firsttime
global first_thread
global last_candle_time
global single_trade_flag
global idle_state
global trading_symbol
global ta_delta_flag

global band1_counter_status
global band1_counter
global band2_counter_status
global band2_counter
global get_index_flag  

dict_inputs = {'ReportFile': ' ', 'OptExpiry': ' ','Iterations': ' ',
                   'EntryStartTime': ' ', 'EntryEndTime': ' ', 'ExitTime': ' ','PMHigh':' ','PMLow':'','PMClose':' '}

dict_runtime_inputs_default = {"OptMode": " ", "OptStopLoss": " ", "OptTarget": " ",
        "OptTrailing": " ", "OptSLInc": " ", "OptSLReset": " ", "OptSLRP": " ","Opt_target_set":" ","OptBuffer":" ",
                           "IndexMode": " ", "IndexStopLoss": " ", "IndexTarget": " ",
                           "IndexTrailing": " ", "IndexSLInc": " ", "IndexSLReset": " ",
                           "IndexSLRP": " ","Index_target_set":" ", "CapitalBased": " ", "Capital": " ","OptQuantityLots":" ","IndexBuffer":" ","OptBuyDepth":" ","LiveTrade":" ","PaDelta": " ","CprTaDelta": " ", "TaDelta": " ", "PaTf":" ","TradeTf":" ","auto_entry": " ", "auto_exit": " "}

dict_data = {'date':'','time':'','high':'','low':'','resistance':'','support':''}

kite = zrd_login.kite

logging.basicConfig(filename='IO_NF_CE_Log',
                            filemode='w',
                            format='%(message)s',
                            level=logging.INFO)

file = open('IO_NF_CE_Inputs.txt', 'r')
contents = file.read()
dict_inputs = ast.literal_eval(contents)
file.close()
#print(dict_inputs)
#logging.info(dict_inputs)

# Reading run time inputs
ce_input = open('IO_NF_CE_Runtime_Inputs.txt', 'r')
contents = ce_input.read()
dict_runtime_inputs_default = ast.literal_eval(contents)
ce_input.close()

dict_runtime_inputs = dict_runtime_inputs_default.copy()

#print(dict_runtime_inputs)
#logging.info(dict_runtime_inputs)

script_name = 'NIFTY 50'
trading_symbol = 'NIFTY 50'
traded_scripts = []

lock = threading.Lock()

place_order_in_process = 0
place_order_max_lots = 35
lot_size = 50
firsttime = True
first_thread = True
last_candle_time = 0
idle_state = 0
ta_delta_flag = True

band1_counter_status = False
band1_counter = 0
band2_counter_status = False
band2_counter = 0
get_index_flag = False


def check_single_trade_flag():
    global single_trade_flag

    # Checking single trade flag
    single_trade_flag_file = open('Single_Trade_Flag.txt', 'r')
    single_trade_flag = single_trade_flag_file.read(1)
    single_trade_flag_file.close()

def set_single_trade_flag():
    logging.info('setting single_trade_flag')
    single_trade_flag_file = open('Single_Trade_Flag.txt', 'w')
    single_trade_flag_file.write('3')
    single_trade_flag_file.close()
    logging.info('single trade flag file is set')

def reset_single_trade_flag():
    logging.info('resetting single_trade_flag')
    single_trade_flag_file = open('Single_Trade_Flag.txt', 'w')
    single_trade_flag_file.write('0')
    single_trade_flag_file.close()
    logging.info('single trade flag file is reset')



def get_nifty_ltp(n):

    if (n == "1"):
        print('n = 1')
        ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
        nifty_ltp1 = ohlc['NSE:{}'.format(trading_symbol)]['last_price']
        return nifty_ltp1
    elif (n == "2"):
        print('n = 2')
        ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
        nifty_ltp2 = ohlc['NSE:{}'.format(trading_symbol)]['last_price']
        return nifty_ltp2

def cpr():
    global dict_inputs
    global pdh,pdl,pivot,tc,bc
    global trading_symbol
    global fivemin_r1,fivemin_r2,fivemin_r3,fivemin_s1,fivemin_s2,fivemin_s3

    curRow = 1
    prevRow = 0
    # current date
    cpr_curr_date_time = datetime.now(timezone('Asia/Kolkata'))
    cpr_curr_date = cpr_curr_date_time.strftime("%Y-%m-%d")
    # logging.info("curr_date: %s", curr_date)

    cpr_index_data = zrd_login.get_data(name = trading_symbol, segment='NSE:', delta=dict_runtime_inputs["CprTaDelta"], interval='15minute', continuous=False,
                              oi=False)

    logging.info(cpr_index_data)

    indexCurRow = 0
    cpr_index_dataLen = len(cpr_index_data)
    pdh = 0
    pdl = 0
    pdc = 0

    while (indexCurRow < cpr_index_dataLen):
        
        cpr_index_data_str = cpr_index_data.astype(str)
        cpr_indexCurrCandle = cpr_index_data_str.iloc[indexCurRow]
        cpr_curr_candle_date = cpr_indexCurrCandle['date']
        cpr_candle_split = cpr_curr_candle_date.split()
        cpr_candle_date = cpr_candle_split[0]
        cpr_candle_time = cpr_candle_split[1]
        cpr_candle_time_split = cpr_candle_time.split(':')
        cpr_candle_hour = cpr_candle_time_split[0]
        cpr_candle_minute = cpr_candle_time_split[1]
        cpr_candle_time =  cpr_candle_hour + cpr_candle_minute
        cpr_candle_total_minutes = (int(cpr_candle_hour) * 60) + int(cpr_candle_minute)

        if (cpr_curr_date != cpr_candle_date):

            if(pdh == 0):
                pdh = float(cpr_indexCurrCandle['high'])
            elif(pdh < float(cpr_indexCurrCandle['high'])):
                pdh = float(cpr_indexCurrCandle['high'])
            
            if(pdl == 0):
                pdl = float(cpr_indexCurrCandle['low'])
            elif(pdl > float(cpr_indexCurrCandle['low'])):
                pdl = float(cpr_indexCurrCandle['low'])

            if(cpr_candle_total_minutes == 915):
                logging.info("15:15 candle")
                pdc = float(cpr_indexCurrCandle['close'])

            indexCurRow = indexCurRow + 1
        else:
            logging.info("reached current day")
            break;

    logging.info("pdh : %s",pdh)
    logging.info("pdl : %s",pdl)
    logging.info("pdc : %s",pdc)




    # CPR Calculation

    pivot=round(((pdh+pdl+pdc)/3),2)
    bcraw=round(((pdh+pdl)/2.0),2)
    tcraw=round(((pivot-bcraw)+pivot),2)
    if(tcraw>bcraw):
        tc=tcraw
        bc=bcraw
    else:
        tc=bcraw
        bc=tcraw
    logging.info('\ncurrent day tc:%s\n',tc)
    logging.info('current day pivot:%s\n',pivot)
    logging.info('current day bc:%s\n',bc)

    fivemin_r1 = round((2 * pivot) - pdl)
    fivemin_s1 = round((2 * pivot) - pdh)

    fivemin_r2 = round(pivot + (pdh - pdl))
    fivemin_s2 = round( pivot - (pdh - pdl))

    fivemin_r3 = round(pivot + 2 * (pdh - pdl))
    fivemin_s3 = round(pivot - 2 * (pdh - pdl))

    logging.info('Five min pivot:%s\n',pivot)
    logging.info('Five min r1 :%s\n',fivemin_r1)
    logging.info('Five min r2 :%s\n',fivemin_r2)
    logging.info('Five min r3 :%s\n',fivemin_r3)
    logging.info('Five min s1 :%s\n',fivemin_s1)
    logging.info('Five min s2 :%s\n',fivemin_s2)
    logging.info('Five min s3 :%s\n',fivemin_s3)
def month_cpr():
    global trading_symbol
    global day_pivot, day_s1, day_s2, day_s3, day_r1, day_r2, day_r3
    global dict_inputs
    curRow = 1
    prevRow = 0
    # CPR Calculation

    logging.info('\nprevious month high:%s\n',dict_inputs['PMHigh'])
    logging.info('previous month low:%s\n',dict_inputs['PMLow'])
    logging.info('previous month close:%s\n',dict_inputs['PMClose'])

    day_pivot=round(((float(dict_inputs['PMHigh']) + float(dict_inputs['PMLow'])+ float(dict_inputs['PMClose']))/3),2)
    day_r1 = round((2 * day_pivot) - dict_inputs['PMLow'])
    day_s1 = round((2 * day_pivot) - dict_inputs['PMHigh'])

    day_r2 = round( ( day_pivot - day_s1 ) + day_r1)
    day_s2 = round( day_pivot - ( day_r1 - day_s1 ))

    day_r3 = round( ( day_pivot - day_s2 ) +  day_r2)
    day_s3 = round( day_pivot - ( day_r2 - day_s2 ))


    logging.info('current month pivot:%s\n',day_pivot)
    logging.info('current month r1 :%s\n',day_r1)
    logging.info('current month r2 :%s\n',day_r2)
    logging.info('current month r3 :%s\n',day_r3)
    logging.info('current month s1 :%s\n',day_s1)
    logging.info('current month s2 :%s\n',day_s2)
    logging.info('current month s3 :%s\n',day_s3)

def check_day_pivot(search_index_close):

    global day_pivot, day_s1, day_s2, day_s3, day_r1, day_r2, day_r3
    global day_pivot_flag
    day_pivot_flag = False

    if ((search_index_close < (float(day_s3) - float(dict_inputs['ResDepth']))) or 
       (((float(day_s3) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close < (float(day_s2) - float(dict_inputs['ResDepth'])))) or 
       (((float(day_s2) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close< (float(day_s1) - float(dict_inputs['ResDepth'])))) or
       (((float(day_s1) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close < (float(day_pivot) - float(dict_inputs['ResDepth'])))) or
       (((float(day_pivot) + float(dict_inputs['SupDepth'])) < search_index_close) and (search_index_close < (float(day_r1) - float(dict_inputs['ResDepth']))))  or 
       (((float(day_r1) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close < (float(day_r2) - float(dict_inputs['ResDepth'])))) or 
       (((float(day_r2) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close < (float(day_r3) - float(dict_inputs['ResDepth']))))or 
       (search_index_close > (float(day_r3) + float(dict_inputs['SupDepth'])))):
        day_pivot_flag = True
    else:
        day_pivot_flag = False


def check_day_hilow(search_index_close):

    global day_high,day_low
    global day_hilow_flag
    day_hilow_flag = False
    logging.info('day_high = %s',day_high)
    logging.info('day_low = %s',day_low)

    if ((search_index_close < (float(day_low) - float(dict_inputs['ResDepth']) )) or 
       ((search_index_close > (float(day_low) + float(dict_inputs['SupDepth']))) and ((search_index_close < (float(day_high) - float(dict_inputs['ResDepth']) )))) or
       (search_index_close > (float(day_high) + float(dict_inputs['SupDepth'])))):
        day_hilow_flag = True
    else:
        day_hilow_flag = False

def check_pdhl(search_index_close):

    global pdhl_flag
    pdhl_flag = False

    if ((search_index_close < (float(pdl) - float(dict_inputs['ResDepth']) )) or 
       ((search_index_close > (float(pdl) + float(dict_inputs['SupDepth']))) and ((search_index_close < (float(pdh) - float(dict_inputs['ResDepth']) )))) or
       (search_index_close > (float(pdh) + float(dict_inputs['SupDepth'])))):
        pdhl_flag = True
    else:
        pdhl_flag = False


def check_cpr_pivot(search_index_close):
    global cpr_flag,fivemin_pivot_flag,pivot
    global fivemin_r1,fivemin_r2,fivemin_r3,fivemin_s1,fivemin_s2,fivemin_s3
    cpr_flag = False
    fivemin_pivot_flag = False

    if((search_index_close > (float(tc + float(dict_inputs['SupDepth'])))) or (search_index_close < (float(bc)) - float(dict_inputs['ResDepth']))):
        cpr_flag = True
    else:
        cpr_flag = False

    if ((search_index_close < (float(fivemin_s3) - float(dict_inputs['ResDepth']))) or
       (((float(fivemin_s3) + float(dict_inputs['SupDepth']) ) < search_index_close ) and (search_index_close < (float(fivemin_s2) - float(dict_inputs['ResDepth'])))) or
        (((float(fivemin_s2) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close< (float(fivemin_s1) - float(dict_inputs['ResDepth'])))) or
        (((float(fivemin_s1) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close < (float(pivot) - float(dict_inputs['ResDepth'])))) or
        (((float(pivot) + float(dict_inputs['SupDepth'])) < search_index_close) and (search_index_close < (float(fivemin_r1) - float(dict_inputs['ResDepth']))))  or
        (((float(fivemin_r1) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close < (float(fivemin_r2) - float(dict_inputs['ResDepth'])))) or
        (((float(fivemin_r2) + float(dict_inputs['SupDepth']) ) < search_index_close) and (search_index_close < (float(fivemin_r3) - float(dict_inputs['ResDepth'])))) or
        (search_index_close > (float(fivemin_r3) + float(dict_inputs['SupDepth'])))):

        fivemin_pivot_flag = True
    else:
        fivemin_pivot_flag = False


#Represent a node of doubly linked list
class NodeHist:
    def __init__(self,dict_large_tf_data):
        self.data = dict_large_tf_data;
        self.previous = None;
        self.next = None;

class DLLHist:
    #Represent the head and tail of the doubly linked list
    def __init__(self):
        self.head = None;
        self.tail = None;

    #addNode() will add a node to the list
    def addNode(self, dict_large_tf_data):
        #Create a new node
        newNode = NodeHist(dict_large_tf_data);

        #If list is empty
        if(self.head == None):
            #Both head and tail will point to newNode
            self.head = self.tail = newNode;
            #head's previous will point to None
            self.head.previous = None;
            #tail's next will point to None, as it is the last node of the list
            self.tail.next = None;
        else:
            #newNode will be added after tail such that tail's next will point to newNode
            self.tail.next = newNode;
            #newNode's previous will point to tail
            newNode.previous = self.tail;
            #newNode will become new tail
            self.tail = newNode;
            #As it is last node, tail's next will point to None
            self.tail.next = None;
    # marking resistance and support levels
    def large_tf_mark_resistance_support(self):
        global current
        global firsttime
        if (firsttime == True):
            current = self.head
            levelNode = current.next.next
            if(self.head == None):
                print("Mark: List is empty")
                return;
        else:
            levelNode = current

        while (levelNode.next.next.next != None):
            if ((levelNode.data['high'] > levelNode.previous.data['high'] ) and (levelNode.data['high'] > levelNode.previous.previous.data['high']) and (levelNode.data['high'] > levelNode.next.data['high'] ) and (levelNode.data['high'] > levelNode.next.next.data['high'])):
                levelNode.data['resistance'] = True
            else:
                levelNode.data['resistance'] = False

            if ((levelNode.data['low'] < levelNode.previous.data['low'] ) and (levelNode.data['low'] < levelNode.previous.previous.data['low']) and (levelNode.data['low'] < levelNode.next.data['low'] ) and (levelNode.data['low'] < levelNode.next.next.data['low'])):
                levelNode.data['support'] = True
            else:
                levelNode.data['support'] = False

            levelNode = levelNode.next
        current = levelNode

    # searching resistance levels
    def large_tf_find_resistance(self,curCandle):
        global large_tf_up_res
        global large_tf_down_res
        global search_index_close

        large_tf_up_res = large_tf_down_res = 0
        search_index_close = curCandle['close']

        if(self.head == None):
            print("find_resistance : List is empty");
            return;
        searchNode = self.tail

        # finding up_res
        curNode = searchNode
        print('\n')
        while (curNode.previous != None):
            if ((float(curNode.data['high']) > float(search_index_close))  and (curNode.data['resistance'] == True )):
                large_tf_up_res = curNode.data['high']
                print('large_tf_up_res: ',curNode.data)
                break

            curNode = curNode.previous

        # finding down_res
        curNode = searchNode
        while (curNode.previous != None):
            if ((float(curNode.data['high']) < float(search_index_close) ) and (curNode.data['resistance'] == True )):
                large_tf_down_res = curNode.data['high']
                print('large_tf_down_res: ',curNode.data)
                break

            curNode = curNode.previous

    # searching support levels
    def large_tf_find_support(self,curCandle):
        global large_tf_up_sup
        global large_tf_down_sup
        global search_index_close

        large_tf_up_sup = large_tf_down_sup = 0

        search_index_close = curCandle['close']

        if(self.head == None):
            print("find_support : List is empty");
            return;
        searchNode = self.tail

        # finding up_sup
        curNode = searchNode
        while (curNode.previous != None):
            if ((float(curNode.data['low']) > float(search_index_close)) and (curNode.data['support'] == True )):
                large_tf_up_sup = curNode.data['low']
                print('large_tf_up_sup: ',curNode.data)
                break

            curNode = curNode.previous

        # finding down_sup
        curNode = searchNode
        while (curNode.previous != None):
            if ((float(curNode.data['low']) < float(search_index_close)) and (curNode.data['support'] == True )):
                large_tf_down_sup = curNode.data['low']
                print('lage_tf_down_sup: ',curNode.data)
                break

            curNode = curNode.previous

    def check_large_tf_supres(self,search_index_close):
        global large_tf_down_res,large_tf_down_sup,large_tf_up_res,large_tf_up_sup
        global large_tf_supres_flag

        large_tf_down_res_flag = False
        large_tf_up_sup_flag = False
        large_tf_supres_flag = False
        large_tf_down_supres = 0
        large_tf_up_supres = 0

        if((float(large_tf_down_res) == 0) and (float(large_tf_down_sup) == 0)):
            large_tf_down_sup_flag = True
        else:

            if(((float(large_tf_down_res) > 1)) and (float(large_tf_down_sup) > 1)):

                if(float(large_tf_down_res) > float(large_tf_down_sup)):
                    large_tf_down_supres = float(large_tf_down_res)
                else:
                    large_tf_down_supres = float(large_tf_down_sup)
            else:

                if((float(large_tf_down_res) > 1)):
                    large_tf_down_supres = float(large_tf_down_res)
                elif((float(large_tf_down_sup) > 1)):
                    large_tf_down_supres = float(large_tf_down_sup)

            if(search_index_close > (float(large_tf_down_supres) + float(dict_inputs['SupDepth']))):
                large_tf_down_res_flag = True
            else:
                large_tf_down_res_flag = False


        if((float(large_tf_up_res) == 0) and (float(large_tf_up_sup) == 0)):
            large_tf_up_sup_flag = True
        else:

            if(((float(large_tf_up_res) > 1)) and (float(large_tf_up_sup) > 1)):

                if(float(large_tf_up_res) < float(large_tf_up_sup)):
                    large_tf_up_supres = float(large_tf_up_res)
                else:
                    large_tf_up_supres = float(large_tf_up_sup)
            else:

                if((float(large_tf_up_res) > 1)):
                    large_tf_up_supres = float(large_tf_up_res)
                elif((float(large_tf_up_sup) > 1)):
                    large_tf_up_supres = float(large_tf_up_sup)


            if(search_index_close < (float(large_tf_up_supres) - float(dict_inputs['ResDepth']))):
                large_tf_up_sup_flag = True
            else:
                large_tf_up_sup_flag = False

        if ((large_tf_down_res_flag == True) and (large_tf_up_sup_flag == True)):
            large_tf_supres_flag = True
        else:
            large_tf_supres_flag = False


    #display() will print out the nodes of the list
    def large_tf_display(self):
        #Node current will point to head
        large_tf_current = self.head
        if(self.head == None):
            logging.info("List is empty")
            return;
        while(large_tf_current != None):
            #Prints each node by incrementing pointer.
            logging.info('large_tf_current %s',large_tf_current.data)
            large_tf_current = large_tf_current.next

dLargeTfList = DLLHist()

# checking current candle time
def check_large_tf_current_candle_time():
    global large_tf_index_data
    global large_tf_candle_time_flag
    indexCurRow = -2
    large_tf_candle_time_flag = False

    #checking prev candle time and curr time
    large_tf_index_data_str = large_tf_index_data.astype(str)
    large_tf_indexLastCandle = large_tf_index_data_str.iloc[indexCurRow]
    large_tf_index_curr_candle_time = large_tf_indexLastCandle['date']
    logging.info('large_tf_current candle time:%s', large_tf_index_curr_candle_time)

    large_tf_candle_split = large_tf_index_curr_candle_time.split()
    large_tf_candle_date = large_tf_candle_split[0]
    large_tf_candle_time = large_tf_candle_split[1]

    # current date
    large_tf_curr_date_time = datetime.now(timezone('Asia/Kolkata'))
    large_tf_curr_date = large_tf_curr_date_time.strftime("%Y-%m-%d")
    # logging.info("curr_date: %s", curr_date)


    if (large_tf_curr_date == large_tf_candle_date):
        logging.info('large_tf_curr_date : %s and large_tf_candle_date : %s are same',large_tf_curr_date,large_tf_candle_date)
        # candle time
        large_tf_candle_time_split = large_tf_candle_time.split(':')
        large_tf_candle_hour = large_tf_candle_time_split[0]
        large_tf_candle_minute = large_tf_candle_time_split[1]
        #logging.info('candle_hour =%s', candle_hour)
        #logging.info('candle_minute =%s', candle_minute)
        large_tf_candle_total_minutes = (int(large_tf_candle_hour) * 60) + int(large_tf_candle_minute)
        #logging.info('candle_total_minutes = %s',candle_total_minutes)

        # current time
        large_tf_curr_time_hour = datetime.now(timezone('Asia/Kolkata')).strftime('%H')
        #logging.info('current_time_hour:%s', curr_time_hour)
        large_tf_curr_time_min = datetime.now(timezone('Asia/Kolkata')).strftime('%M')
        #logging.info('current_time_min:%s', curr_time_min)
        large_tf_curr_total_time_min = (int(large_tf_curr_time_hour) * 60) + int(large_tf_curr_time_min)
        large_tf_curr_total_time_seconds = large_tf_curr_total_time_min * 60
        large_tf_candle_total_seconds = large_tf_candle_total_minutes * 60
        time_diff = large_tf_curr_total_time_seconds - large_tf_candle_total_seconds

        allowed_time = ((int(dict_runtime_inputs['PaTf']) * 60 )  + (int(dict_runtime_inputs['PaTf']) * 40))

        logging.info('large_tf_curr_total_time_sec: %s large_tf_candle_total_sec %s',large_tf_curr_total_time_seconds,large_tf_candle_total_seconds)
        if (time_diff < allowed_time):
            logging.info('time_diff:%s less than allowed_time:%s',time_diff,allowed_time)
            large_tf_candle_time_flag = True
        else:
            logging.info('time_diff: %s higher than allowed_time:%s',time_diff,allowed_time)
            large_tf_candle_time_flag = False
    else:
        logging.info('curr_date : %s and candle_date : %s are not same',large_tf_curr_date,large_tf_candle_date)
        large_tf_candle_time_flag = False


# getting historical data
def large_tf_data():
    global dict_inputs
    global large_tf_index_data
    global large_tf_candle_time_flag
    global firsttime
    global first_thread
    global large_tf_up_res,large_tf_down_res,large_tf_up_sup,large_tf_down_sup
    global large_tf_supres_flag
    global search_index_close
    global day_high,day_low
    global last_candle_time


    search_index_close = 0
    indexPrevRow = 0
    indexCurRow = 0
    indexDataLen = 0
    candle_time_flag = False
    large_tf_up_res_flag = False
    large_tf_up_sup_flag = False
    large_tf_supres_flag = False
    #laha
    large_tf_candle_time_flag = False

    # current date
    large_tf_curr_date_time = datetime.now(timezone('Asia/Kolkata'))
    large_tf_curr_date = large_tf_curr_date_time.strftime("%Y-%m-%d")
    # logging.info("curr_date: %s", curr_date)


    large_tf_up_res = large_tf_down_res = large_tf_up_sup = large_tf_down_sup = 0

    dict_data = {'date':'','time':'','high':'','low':'','resistance':'','support':''}
    # current date

    if( int(dict_runtime_inputs["PaTf"]) == 1):
        pa_interval = 'minute'
        #print('pa_interval',pa_interval)
    else:
        pa_interval = dict_runtime_inputs["PaTf"]+'minute'
        #print('pa_interval',pa_interval)

    if(first_thread == True):
        logging.info('first_thread True')
        time_min =  datetime.now(timezone('Asia/Kolkata')).strftime('%M')
        logging.info('time_min %s',time_min)
        #print(time_min)
        
        if (int(dict_runtime_inputs["PaTf"]) == 30):
            if(int(time_min) <= 15):
                bal_min = 15 - int(time_min)
            elif(15 < int(time_min) <= 45):
                bal_min = 45 - int(time_min)
            elif(int(time_min) > 45):
                bal_min = 30 - ((int(time_min) - 45))
        else:

            remind = int(time_min) % (int(dict_runtime_inputs["PaTf"]))
            bal_min = (int(dict_runtime_inputs["PaTf"])) - remind

        
        delay = int(bal_min) * 60
        # Timer
        if(int(delay) != 0):
            logging.info('timer started with %s seconds',delay)
            timer = threading.Timer(delay, large_tf_data)
            timer.start()
        else:
            delay = (int(dict_runtime_inputs["PaTf"])) * 60
            logging.info('timer started with %s seconds',delay)
            timer = threading.Timer(delay, large_tf_data)
            timer.start()

        time.sleep(30)
        large_tf_index_data = zrd_login.get_data(name='NIFTY 50', segment='NSE:', delta=int(dict_runtime_inputs["PaDelta"]), interval=pa_interval, continuous=True,oi=False)

        first_thread = False
    else:
        logging.info('first_thread False')
        delay = (int(dict_runtime_inputs["PaTf"])) * 60
        logging.info('timer started with %s seconds',delay)
        timer = threading.Timer(delay, large_tf_data)
        timer.start()

        while True:
            time.sleep(30)
            large_tf_index_data = zrd_login.get_data(name='NIFTY 50', segment='NSE:', delta=int(dict_runtime_inputs["CprTaDelta"]), interval=pa_interval, continuous=True,oi=False)
            #laha
            check_large_tf_current_candle_time()
        
            if(large_tf_candle_time_flag == True):
                break
            time.sleep(30)

    #print(large_tf_index_data)

    indexCurRow = 0
    large_tf_indexDataLen = len(large_tf_index_data)
    if(firsttime == True):
        logging.info('first_time True')
        day_high = 0
        day_low = 0
        while (indexCurRow < large_tf_indexDataLen):
            large_tf_index_data_str = large_tf_index_data.astype(str)
            large_tf_indexCurrCandle = large_tf_index_data_str.iloc[indexCurRow]
            large_tf_curr_candle_date = large_tf_indexCurrCandle['date']
            large_tf_candle_split = large_tf_curr_candle_date.split()
            large_tf_candle_date = large_tf_candle_split[0]
            large_tf_candle_time = large_tf_candle_split[1]
            large_tf_candle_time_split = large_tf_candle_time.split(':')
            large_tf_candle_hour = large_tf_candle_time_split[0]
            large_tf_candle_minute = large_tf_candle_time_split[1]
            large_tf_candle_time =  large_tf_candle_hour + large_tf_candle_minute

            #Add nodes to the list
            large_tf_dict_data = {'date':'','time':'','high':'','low':'','resistance':'','support':''}
            large_tf_dict_data['date'] = large_tf_candle_date
            large_tf_dict_data['time'] = large_tf_candle_time
            large_tf_dict_data['high'] = large_tf_indexCurrCandle['high']
            large_tf_dict_data['low'] = large_tf_indexCurrCandle['low']
            large_tf_dict_data['resistance'] = False
            large_tf_dict_data['support'] = False
            #Add nodes to the list

            if ((large_tf_curr_date == large_tf_candle_date) and (indexCurRow == (large_tf_indexDataLen - 1))):
                logging.info('skip adding node')
            else:
                if (last_candle_time !=  large_tf_dict_data['time']):
                    logging.info('last_candle_time:%s current_candle_time:%s',last_candle_time,large_tf_dict_data['time'])
                    dLargeTfList.addNode(large_tf_dict_data);
                    last_candle_time =  large_tf_dict_data['time']

            #logging.info('large_tf_candle %s',large_tf_indexCurrCandle)
            if ((large_tf_curr_date == large_tf_candle_date) and (indexCurRow != (large_tf_indexDataLen - 1))):

                if(day_high == 0):
                    day_high = large_tf_indexCurrCandle['high']
                elif(day_high < large_tf_indexCurrCandle['high']):
                    day_high = large_tf_indexCurrCandle['high']
                if(day_low == 0):
                    day_low = large_tf_indexCurrCandle['low']
                elif(day_low > large_tf_indexCurrCandle['low']):
                    day_low = large_tf_indexCurrCandle['low']

            #Displays the nodes present in the list
            indexCurRow = indexCurRow + 1
    else:
        logging.info('first_time False')
        indexCurRow = -2
        large_tf_index_data_str = large_tf_index_data.astype(str)
        large_tf_indexCurrCandle = large_tf_index_data_str.iloc[indexCurRow]
        large_tf_curr_candle_date = large_tf_indexCurrCandle['date']
        large_tf_candle_split = large_tf_curr_candle_date.split()
        large_tf_candle_date = large_tf_candle_split[0]
        large_tf_candle_time = large_tf_candle_split[1]
        large_tf_candle_time_split = large_tf_candle_time.split(':')
        large_tf_candle_hour = large_tf_candle_time_split[0]
        large_tf_candle_minute = large_tf_candle_time_split[1]
        large_tf_candle_time =  large_tf_candle_hour + large_tf_candle_minute

        #Add nodes to the list
        large_tf_dict_data = {'date':'','time':'','high':'','low':'','resistance':'','support':''}
        large_tf_dict_data['date'] = large_tf_candle_date
        large_tf_dict_data['time'] = large_tf_candle_time
        large_tf_dict_data['high'] = large_tf_indexCurrCandle['high']
        large_tf_dict_data['low'] = large_tf_indexCurrCandle['low']
        large_tf_dict_data['resistance'] = False
        large_tf_dict_data['support'] = False
        #Add nodes to the list
        if (large_tf_curr_date == large_tf_candle_date):
            if (last_candle_time !=  large_tf_dict_data['time']):
                logging.info('last_candle_time:%s current_candle_time:%s',last_candle_time,large_tf_dict_data['time'])
                dLargeTfList.addNode(large_tf_dict_data);
                last_candle_time =  large_tf_dict_data['time']

        if(day_high == 0):
            day_high = large_tf_indexCurrCandle['high']
        elif(day_high < large_tf_indexCurrCandle['high']):
            day_high = large_tf_indexCurrCandle['high']
        if(day_low == 0):
            day_low = large_tf_indexCurrCandle['low']
        elif(day_low > large_tf_indexCurrCandle['low']):
            day_low = large_tf_indexCurrCandle['low']

    dLargeTfList.large_tf_mark_resistance_support();
    #laha
    dLargeTfList.large_tf_display();

    firsttime = False

# Basket orders
def basket_margin():
    global opt_trade_symbol
    global dict_inputs
    global dict_runtime_inputs
    global lot_size
    global margin_amount_required

    if(dict_runtime_inputs["CapitalBased"]=='False'):
        order_param_basket = [
        {
            "exchange": "NFO",
            "tradingsymbol": opt_trade_symbol,
            "transaction_type": "BUY",
            "variety": "regular",
            "product": "MIS",
            "order_type": "MARKET",
            "quantity": dict_runtime_inputs["OptQuantityLots"] * lot_size
        }]

        #margin_amount = kite.basket_order_margins(order_param_basket)
        ##logging.info("Required margin for basket order: {}".format(margin_amount))
        ##logging.info("\n")
        # Compact margin response
        margin_amount_comt = kite.basket_order_margins(order_param_basket, mode='compact')
        #logging.info("Required margin for basket order in compact form: {}".format(margin_amount_comt))
        #logging.info("\n")
        #margin_amount_required = margin_amount_comt['final']['total']
        margin_amount_required = margin_amount_comt['initial']['total']
        #logging.info('Required margin for basket order %s', round(margin_amount_required))
        #except Exception as e:

def reset():

    global script_name
    global traded_scripts
    global thirdwindow_enable
    global secondwindow_enable


    traded_scripts.remove(script_name)
    #logging.info('Removed script_name')
    thirdwindow_enable = False
    secondwindow_enable = True

def ce_firstwindow():


    #defining global for inputs,runtime inputs,auto_flag,hold_flag
    global dict_inputs
    global dict_runtime_inputs

    # create a tkinter main_root window
    main_root = Tk()
    
    # main_root window title and dimension
    main_root.title('NF CE TRADE')
    main_root.geometry('630x355+0+440')
    main_root['bg'] = '#C0C0C0'
    
    # Function for closing the main window
    def Close():
        main_root.destroy()
        gc.collect()

    
    # fun is called when radiobutton for hold flag is seleced
    def viewSelect():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["LiveTrade"] = vari.get()
        if dict_runtime_inputs["LiveTrade"] == 'True':
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    vari = StringVar()

    # setting the default value for the aut0_flag by using var
    vari.set(dict_runtime_inputs["LiveTrade"])
    #print(dict_runtime_inputs["LiveTrade"])

    # radio button for true
    R1 = Radiobutton(main_root, text="Live ",font=('Garamond', 15), variable=vari, value="True", command=viewSelect)

    # placing the radio button
    R1.place(x=50, y=170)

    # radio button for false
    R2 = Radiobutton(main_root, text="Paper ",font=('Garamond', 15), variable=vari, value="False", command=viewSelect)

    # placing the radio button
    R2.place(x=140, y=170)

    # function for viewing inputs widget
    def view_inputs():
        # defining global to all the variables required in this function
        global dict_inputs
        global r1, r2, r3, r4, r5, r6, r7, r8
    
        # to create view inputs (child) widget
        view_inputs_root = Toplevel(main_root)
    
        # input root window title and dimension
        view_inputs_root.title("NF CE View Input")
        view_inputs_root.geometry("540x450+150+100")
    
        # the label for ReportFile
        Label(view_inputs_root, text="ReportFile", font=('Garamond', 16)).place(x=50, y=10)
    
        # to display ReportFile value value in a box and then modify it
        r1 = tk.Entry(view_inputs_root, font=('Garamond', 16), bd=1)
        r1.insert(0, dict_inputs["ReportFile"])
        r1.place(x=250, y=10)
    
        # the label for FutExpiry
        #Label(view_inputs_root, text="FutExpiry", font=('Garamond', 16)).place(x=50, y=50)
    
        # to display FutExpiry value value in a box and then modify it
        #r2 = tk.Entry(view_inputs_root, font=('Garamond', 16), bd=1)
        #r2.insert(0, dict_inputs["FutExpiry"])
        #r2.place(x=250, y=50)
    
        # the label for OptExpiry
        Label(view_inputs_root, text="OptExpiry", font=('Garamond', 16)).place(x=50, y=50)
    
        # to display OptExpiry value value in a box and then modify it
        r3 = tk.Entry(view_inputs_root, font=('Garamond', 16), bd=1)
        r3.insert(0, dict_inputs["OptExpiry"])
        r3.place(x=250, y=50)
    
        # the label for EntryStartTime
        Label(view_inputs_root, text="EntryStartTime", font=('Garamond', 16)).place(x=50, y=100)
    
        # to display EntryStartTime value in a box and then modify it
        r5 = tk.Entry(view_inputs_root, font=('Garamond', 16), bd=1)
        r5.insert(0, dict_inputs["EntryStartTime"])
        r5.place(x=250, y=100)
    
        # the label for EntryEndTime
        Label(view_inputs_root, text="EntryEndTime", font=('Garamond', 16)).place(x=50, y=150)
    
        # to display EntryEndTime value in a box and then modify it
        r6 = tk.Entry(view_inputs_root, font=('Garamond', 16), bd=1)
        r6.insert(0, dict_inputs["EntryEndTime"])
        r6.place(x=250, y=150)
    
        # the label for ExitTime
        Label(view_inputs_root, text="ExitTime", font=('Garamond', 16)).place(x=50, y=200)
    
        # to display ExitTime value in a box and then modify it
        r7 = tk.Entry(view_inputs_root, font=('Garamond', 16), bd=1)
        r7.insert(0, dict_inputs["ExitTime"])
        r7.place(x=250, y=200)
    
        # function is called when modify is clicked
        def modify_inputs():
            # defining global to all the variables required in this function
            global dict_inputs
            global r1, r2, r3, r4, r5, r6, r7, r8
            # function to assign and display modified values
            dict_inputs["ReportFile"] = r1.get()
            #print("ReportFile : ", dict_inputs["ReportFile"])
    
            # function to assign and display modified values
            #dict_inputs["FutExpiry"] = r2.get()
            ##print("FutExpiry : ", dict_inputs["FutExpiry"])
    
            # function to assign and display modified values
            dict_inputs["OptExpiry"] = r3.get()
            #print("OptExpiry : ", dict_inputs["OptExpiry"])

            # function to assign and display modified values
            dict_inputs["EntryStartTime"] = r5.get()
            #print("EntryStartTime : ", dict_inputs["EntryStartTime"])
    
            # function to assign and display modified values
            dict_inputs["EntryEndTime"] = r6.get()
            #print("EntryEndTime : ", dict_inputs["EntryEndTime"])
    
            # function to assign and display modified values
            dict_inputs["ExitTime"] = r7.get()
            #print("ExitTime : ", dict_inputs["ExitTime"])
      

            var=StringVar()
            label = Message(view_inputs_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

            var.set("Inputs Modified")
            label.place(x=190,y=255)
    
        # function is called when close is clicked
        # this function will close the view_inputs_root widget
        def Close_modify_inputs():
            view_inputs_root.destroy()
            gc.collect()
    
        # creating button for modify in modify inputs window
        b1 = tk.Button(view_inputs_root, text='Modify',
                       command=lambda: modify_inputs(), width=10, heigh=3,bg="#3CB371", font=("Arial", 15))
    
        # placing the button in the window
        b1.place(x=110, y=320)
    
        # creating button for cancel in modify inputs window
        b2 = tk.Button(view_inputs_root, text='Close',
                command=lambda: Close_modify_inputs(), width=10, height=3,bg="RED", font=("Arial", 15))
    
        # placing the button in the window
        b2.place(x=320, y=320)
    
        # Call function to make the widget stay on top
        view_inputs_root.attributes('-topmost', True)
    
        # the widget will keep on displaying in loop
        view_inputs_root.mainloop()
    
    # function for viewing runtime inputs
    def view_runtime_input():
        # defining global to all the variables required in this function
        global dict_runtime_inputs
        global r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15, r16, r17
    
        # to create view_runtime_input(child) widget
        view_runtime_input_root = Toplevel(main_root)
    
        # runtime input root window title and dimension
        view_runtime_input_root.title(" NF CE View RunTime Input")
        view_runtime_input_root.geometry("760x515+100+100")
    
        # the label for OptMode
        Label(view_runtime_input_root, text="OptMode", font=('Garamond', 16)).place(x=50, y=10)
    
        # fun is called when radiobutton for hold flag is seleced
        def viewSelected():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["OptMode"] = var.get()
            if dict_runtime_inputs["OptMode"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var.set(dict_runtime_inputs["OptMode"])
        #print(dict_runtime_inputs["OptMode"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True", variable=var, value="True", command=viewSelected, font=('Garamond', 15))
    
        # placing the radio button
        R1.place(x=180, y=10)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False", variable=var, value="False", command=viewSelected ,font=('Garamond', 15))
    
        # placing the radio button
        R2.place(x=243, y=10)
    
        # the label for OptStopLoss
        Label(view_runtime_input_root, text="OptStopLoss", font=('Garamond', 16)).place(x=50, y=50)
    
        # creating a entry for OptStopLoss
        r1 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r1.insert(0, dict_runtime_inputs["OptStopLoss"])
        r1.place(x=190, y=50)
    
        # the label for OptTarget
        Label(view_runtime_input_root, text="OptTarget", font=('Garamond', 16)).place(x=50, y=100)
    
        #creating a entry for OptTarget value
        r2 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r2.insert(0, dict_runtime_inputs["OptTarget"])
        r2.place(x=190, y=100)
    
        # the label for OptTrailing
        Label(view_runtime_input_root, text="OptTrailing", font=('Garamond', 16)).place(x=50, y=150)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected1():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["OptTrailing"] = var1.get()
            if dict_runtime_inputs["OptTrailing"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var1 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var1.set(dict_runtime_inputs["OptTrailing"])
        #print(dict_runtime_inputs["OptTrailing"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var1, value="True", command=viewSelected1)
    
        # placing the radio button
        R1.place(x=180, y=150)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15) ,variable=var1, value="False", command=viewSelected1)
    
        # placing the radio button
        R2.place(x=243, y=150)
    
        # the label for OptSLInc
        Label(view_runtime_input_root, text="OptSLInc", font=('Garamond', 16)).place(x=50, y=200)
    
        # creating a combobox for OptSLInc
        n3 = tk.StringVar()
        r3 = ttk.Combobox(view_runtime_input_root, width=11, height=9, textvariable=n3, font=('Garamond', 16))
        r3['values'] = (' 1',' 2',' 3')
    
        r3.grid(column=1, row=5)
        r3.current()
        r3.insert(0, dict_runtime_inputs["OptSLInc"])
        r3.place(x=190, y=200)
    
        # the label for OptSLReset
        Label(view_runtime_input_root, text="OptSLReset", font=('Garamond', 16)).place(x=50, y=250)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected2():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["OptSLReset"] = var2.get()
            if dict_runtime_inputs["OptSLReset"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var2 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var2.set(dict_runtime_inputs["OptSLReset"])
        #print(dict_runtime_inputs["OptSLReset"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var2, value="True", command=viewSelected2)
    
        # placing the radio button
        R1.place(x=180, y=250)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var2, value="False", command=viewSelected2)
    
        # placing the radio button
        R2.place(x=243, y=250)
    
        # the label for OptSLRP
        Label(view_runtime_input_root, text="OptSLRP", font=('Garamond', 16)).place(x=50, y=300)
    
        # creating a entry for OptSLRP
        r4 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r4.insert(0, dict_runtime_inputs["OptSLRP"])
        r4.place(x=190, y=300)

        Label(view_runtime_input_root, text="Opt Target",font=('Garamond', 16)).place(x=50, y=350)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected12():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["Opt_target_set"] = var12.get()
            if dict_runtime_inputs["Opt_target_set"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var12 = StringVar()

        # setting the default value for the aut0_flag by using var
        var12.set(dict_runtime_inputs["Opt_target_set"])
        #print(dict_runtime_inputs["Opt_target_set"])

        # radio button for true
        X13 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var12, value="True", command=viewSelected12)

        # placing the radio button
        X13.place(x=180, y=350)

        # radio button for false
        X14 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var12, value="False", command=viewSelected12)

        # placing the radio button
        X14.place(x=243, y=350)
    
        # the label for IndexMode
        Label(view_runtime_input_root, text="IndexMode", font=('Garamond', 16)).place(x=430, y=10)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected3():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["IndexMode"] = var3.get()
            if dict_runtime_inputs["IndexMode"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var3 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var3.set(dict_runtime_inputs["IndexMode"])
        #print(dict_runtime_inputs["IndexMode"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var3, value="True", command=viewSelected3)
    
        # placing the radio button
        R1.place(x=575, y=10)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var3, value="False", command=viewSelected3)
    
        # placing the radio button
        R2.place(x=643, y=10)
    
        # the label for IndexStopLoss
        Label(view_runtime_input_root, text="IndexStopLoss", font=('Garamond', 16)).place(x=430, y=50)
    
        # creating a entry for IndexStopLoss
        r5 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r5.insert(0, dict_runtime_inputs["IndexStopLoss"])
        r5.place(x=590, y=50)
    
        # the label for IndexTarget
        Label(view_runtime_input_root, text="IndexTarget", font=('Garamond', 16)).place(x=430, y=100)
    
        # creating a entry for IndexTarget
        r6 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r6.insert(0, dict_runtime_inputs["IndexTarget"])
        r6.place(x=590, y=100)
    
        # the label for IndexTrailing
        Label(view_runtime_input_root, text="IndexTrailing", font=('Garamond', 16)).place(x=430, y=150)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected4():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["IndexTrailing"] = var4.get()
            if dict_runtime_inputs["IndexTrailing"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var4 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var4.set(dict_runtime_inputs["IndexTrailing"])
        #print(dict_runtime_inputs["IndexTrailing"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var4, value="True", command=viewSelected4)
    
        # placing the radio button
        R1.place(x=575, y=150)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var4, value="False", command=viewSelected4)
    
        # placing the radio button
        R2.place(x=643, y=150)
    
        # the label for IndexSLInc
        Label(view_runtime_input_root, text="IndexSLInc", font=('Garamond', 16)).place(x=430, y=200)
    
        # creating a entry for IndexSLInc
        r7 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r7.insert(0, dict_runtime_inputs["IndexSLInc"])
        r7.place(x=590, y=200)
    
        # the label for IndexSLReset
        Label(view_runtime_input_root, text="IndexSLReset", font=('Garamond', 16)).place(x=430, y=250)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected5():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["IndexSLReset"] = var5.get()
            if dict_runtime_inputs["IndexSLReset"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var5 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var5.set(dict_runtime_inputs["IndexSLReset"])
        #print(dict_runtime_inputs["IndexSLReset"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var5, value="True", command=viewSelected5)
    
        # placing the radio button
        R1.place(x=575, y=250)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var5, value="False", command=viewSelected5)
    
        # placing the radio button
        R2.place(x=643, y=250)
    
        # the label for IndexSLRP
        Label(view_runtime_input_root, text="IndexSLRP", font=('Garamond', 16)).place(x=430, y=300)
        # creating a entry for IndexSLRP
        r8 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r8.insert(0, dict_runtime_inputs["IndexSLRP"])
        r8.place(x=590, y=300)

        Label(view_runtime_input_root, text="Index Target",font=('Garamond', 16)).place(x=430, y=350)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected11():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["Index_target_set"] = var11.get()
            if dict_runtime_inputs["Index_target_set"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var11 = StringVar()

        # setting the default value for the aut0_flag by using var
        var11.set(dict_runtime_inputs["Index_target_set"])
        #print(dict_runtime_inputs["Index_target_set"])

        # radio button for true
        X11 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var11, value="True", command=viewSelected11)

        # placing the radio button
        X11.place(x=575, y=350)

        # radio button for false
        X12 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var11, value="False", command=viewSelected11)

        # placing the radio button
        X12.place(x=645, y=350)

        Label(view_runtime_input_root, text="Auto Exit",font=('Garamond', 16)).place(x=430, y=400)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected12():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["auto_exit"] = var12.get()
            if dict_runtime_inputs["auto_exit"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var12 = StringVar()

        # setting the default value for the aut0_flag by using var
        var12.set(dict_runtime_inputs["auto_exit"])
        #print(dict_runtime_inputs["Index_target_set"])

        # radio button for true
        X13 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var12, value="True", command=viewSelected12)

        # placing the radio button
        X13.place(x=575, y=400)

        # radio button for false
        X14 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var12, value="False", command=viewSelected12)

        # placing the radio button
        X14.place(x=645, y=400)

        Label(view_runtime_input_root, text="Auto Entry",font=('Garamond', 16)).place(x=50, y=400)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected13():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["auto_entry"] = var13.get()
            if dict_runtime_inputs["auto_entry"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var13 = StringVar()

        # setting the default value for the aut0_flag by using var
        var13.set(dict_runtime_inputs["auto_entry"])
        #print(dict_runtime_inputs["Index_target_set"])

        # radio button for true
        X15 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var13, value="True", command=viewSelected13)

        # placing the radio button
        X15.place(x=180, y=400)

        # radio button for false
        X16 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var13, value="False", command=viewSelected13)

        # placing the radio button
        X16.place(x=243, y=400)
        
        # function is called when modify is clicked
        def modify_runtime_inputs():
            global dict_runtime_inputs
            
            global r1, r2, r3, r4, r5, r6, r7, r8, r9, r10
    
            # function to assign and display modified values
            #print("OptMode : ", dict_runtime_inputs["OptMode"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptStopLoss"] = int(r1.get())
            #print("OptStopLoss : ", dict_runtime_inputs["OptStopLoss"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptTarget"] = int(r2.get())
            #print("OptTarget : ", dict_runtime_inputs["OptTarget"])
    
            # function to assign and display modified values
            #print("OptTrailing : ", dict_runtime_inputs["OptTrailing"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptSLInc"]= int(r3.get())
            #print("OptSLInc : ", dict_runtime_inputs["OptSLInc"])
    
            # function to assign and display modified values
            #print("OptSLReset : ", dict_runtime_inputs["OptSLReset"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptSLRP"] = int(r4.get())
            #print("OptSLRP : ", dict_runtime_inputs["OptSLRP"])

            # function to assign and display modified values
            #print("Opt Target set : ", dict_runtime_inputs["Opt_target_set"])
    
            # function to assign and display modified values
            #print("IndexMode : ", dict_runtime_inputs["IndexMode"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexStopLoss"] = int(r5.get())
            #print("IndexStopLoss : ", dict_runtime_inputs["IndexStopLoss"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexTarget"] = int(r6.get())
            #print("IndexTarget : ", dict_runtime_inputs["IndexTarget"])
    
            # function to assign and display modified values
            #print("IndexTrailing : ", dict_runtime_inputs["IndexTrailing"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexSLInc"] = int(r7.get())
            #print("IndexSLInc : ", dict_runtime_inputs["IndexSLInc"])
    
            # function to assign and display modified values
            #print("IndexSLReset : ", dict_runtime_inputs["IndexSLReset"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexSLRP"] = int(r8.get())
            #print("OptSLRP : ", dict_runtime_inputs["IndexSLRP"])

            # function to assign and display modified values
            #print("Index Target set : ", dict_runtime_inputs["Index_target_set"])

            var=StringVar()
            label = Message(view_runtime_input_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

            #var.set(IndexTarget_points)
            var.set("Runtimeinputs Modified")
            label.place(x=290,y=400)    
    
        # function is called when close is clicked
        # this function will close the view_inputss_root widget
        def Close_modify_runtime_inputs():
            view_runtime_input_root.destroy()
            gc.collect()
    
        # creating button for modify
        b1 = tk.Button(view_runtime_input_root, text='Modify',
                       command=lambda: modify_runtime_inputs(), width=14, heigh=3, font=("Arial", 15),bg="#3CB371")
        # placing the button
        b1.place(x=170, y=450)
        # creating button for cancel
        b2 = tk.Button(view_runtime_input_root, text='Close',
                       command=lambda: Close_modify_runtime_inputs(), width=14, height=3, font=("Arial", 15),bg="RED")
        # placing the button
        b2.place(x=470, y=450)
        # Call function to make the widget stay on top
        view_runtime_input_root.attributes('-topmost', True)
        # the widget will keep on displaying in loop
        view_runtime_input_root.mainloop()
    def Exit():
        #print("Exited code from firstwindow")
        os._exit(os.EX_OK)
    # Create a Button for Inputs
    b1 = tk.Button(main_root, text='Inputs',
                   command=lambda: view_inputs(), width=14, heigh=5, font=("Arial", 15))
    # placing the button
    b1.place(x=50, y=20)
    # Create a Button for runtime inputs
    b2 = tk.Button(main_root, text='RunTime Inputs',
                   command=lambda: view_runtime_input(), width=14, height=5, font=("Arial", 15))
    # placing the button
    b2.place(x=360, y=20)
    # Create a Button for runtime inputs
    b4 = tk.Button(main_root, text=' NF CE Proceed ',
                   command=lambda: Close(), width=14, height=5, font=("Arial", 15), bg="#3CB371")
    # placing the button
    b4.place(x=360, y=140)
    b5 = tk.Button(main_root, text='Exit',
                   command=lambda: Exit(), width=14, height=5, font=("Arial", 15), bg="#F70D1A")
    # placing the button
    b5.place(x=220, y=260)
    # Call function to make the window stay on top
    main_root.attributes('-topmost', True)
    
    # the widget will keep on displaying in loop
    main_root.mainloop()

def ce_secondwindow():

    #defining global for runtime inputs,auto_flag,hold_flag
    global dict_runtime_inputs
    global opt_trade_symbol
    global ltp
    global script_name
    global traded_scripts
    global opt_premium

    #logging.info("In second window loop")
    # create a tkinter main_root window
    main_root = Tk()
    #main_root.after(1000,lambda:main_root.destroy())
    def Close():
        logging.info("In second window destroy")
        main_root.destroy()
        gc.collect()
    # main_root window title and dimension
    main_root.title("NF CE Trade")
    main_root.geometry('630x355+0+440')
    main_root['bg'] = '#C0C0C0'
    logging.info("Second window is opened")
    
    # function for viewing runtime inputs
    def view_runtime_input():

        # defining global to all the variables required in this function
        global dict_runtime_inputs
        global dict_inputs
        global r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15, r16, r17
    
        # to create view_runtime_input(child) widget
        view_runtime_input_root = Toplevel(main_root)
    
        # runtime input root window title and dimension
        view_runtime_input_root.title(" NF CE View RunTime Input")
        view_runtime_input_root.geometry("760x515+100+100")
    
        # the label for OptMode
        Label(view_runtime_input_root, text="OptMode", font=('Garamond', 16)).place(x=50, y=10)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["OptMode"] = var.get()
            if dict_runtime_inputs["OptMode"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var.set(dict_runtime_inputs["OptMode"])
        #print(dict_runtime_inputs["OptMode"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True", variable=var, value="True", command=viewSelected, font=('Garamond', 15))
    
        # placing the radio button
        R1.place(x=180, y=10)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False", variable=var, value="False", command=viewSelected ,font=('Garamond', 15))
    
        # placing the radio button
        R2.place(x=243, y=10)
    
        # the label for OptStopLoss
        Label(view_runtime_input_root, text="OptStopLoss", font=('Garamond', 16)).place(x=50, y=50)
    
        # creating a entry for OptStopLoss
        r1 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r1.insert(0, dict_runtime_inputs["OptStopLoss"])
        r1.place(x=190, y=50)
    
        # the label for OptTarget
        Label(view_runtime_input_root, text="OptTarget", font=('Garamond', 16)).place(x=50, y=100)
    
        #creating a entry for OptTarget value
        r2 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r2.insert(0, dict_runtime_inputs["OptTarget"])
        r2.place(x=190, y=100)
    
        # the label for OptTrailing
        Label(view_runtime_input_root, text="OptTrailing", font=('Garamond', 16)).place(x=50, y=150)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected1():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["OptTrailing"] = var1.get()
            if dict_runtime_inputs["OptTrailing"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var1 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var1.set(dict_runtime_inputs["OptTrailing"])
        #print(dict_runtime_inputs["OptTrailing"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var1, value="True", command=viewSelected1)
    
        # placing the radio button
        R1.place(x=180, y=150)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15) ,variable=var1, value="False", command=viewSelected1)
    
        # placing the radio button
        R2.place(x=243, y=150)
    
        # the label for OptSLInc
        Label(view_runtime_input_root, text="OptSLInc", font=('Garamond', 16)).place(x=50, y=200)
    
        # creating a combobox for OptSLInc
        n3 = tk.StringVar()
        r3 = ttk.Combobox(view_runtime_input_root, width=11, height=9, textvariable=n3, font=('Garamond', 16))
        r3['values'] = (' 1',' 2',' 3')
    
        r3.grid(column=1, row=5)
        r3.current()
        r3.insert(0, dict_runtime_inputs["OptSLInc"])
        r3.place(x=190, y=200)
    
        # the label for OptSLReset
        Label(view_runtime_input_root, text="OptSLReset", font=('Garamond', 16)).place(x=50, y=250)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected2():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["OptSLReset"] = var2.get()
            if dict_runtime_inputs["OptSLReset"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var2 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var2.set(dict_runtime_inputs["OptSLReset"])
        #print(dict_runtime_inputs["OptSLReset"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var2, value="True", command=viewSelected2)
    
        # placing the radio button
        R1.place(x=180, y=250)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var2, value="False", command=viewSelected2)
    
        # placing the radio button
        R2.place(x=243, y=250)
    
        # the label for OptSLRP
        Label(view_runtime_input_root, text="OptSLRP", font=('Garamond', 16)).place(x=50, y=300)
    
        # creating a entry for OptSLRP
        r4 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r4.insert(0, dict_runtime_inputs["OptSLRP"])
        r4.place(x=190, y=300)
        
        Label(view_runtime_input_root, text="Opt Target",font=('Garamond', 16)).place(x=50, y=350)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected12():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["Opt_target_set"] = var12.get()
            if dict_runtime_inputs["Opt_target_set"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var12 = StringVar()

        # setting the default value for the aut0_flag by using var
        var12.set(dict_runtime_inputs["Opt_target_set"])
        #print(dict_runtime_inputs["Opt_target_set"])

        # radio button for true
        X13 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var12, value="True", command=viewSelected12)

        # placing the radio button
        X13.place(x=180, y=350)

        # radio button for false
        X14 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var12, value="False", command=viewSelected12)

        # placing the radio button
        X14.place(x=243, y=350)

        # the label for IndexMode
        Label(view_runtime_input_root, text="IndexMode", font=('Garamond', 16)).place(x=430, y=10)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected3():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["IndexMode"] = var3.get()
            if dict_runtime_inputs["IndexMode"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var3 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var3.set(dict_runtime_inputs["IndexMode"])
        #print(dict_runtime_inputs["IndexMode"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var3, value="True", command=viewSelected3)
    
        # placing the radio button
        R1.place(x=575, y=10)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var3, value="False", command=viewSelected3)
    
        # placing the radio button
        R2.place(x=643, y=10)
    
        # the label for IndexStopLoss
        Label(view_runtime_input_root, text="IndexStopLoss", font=('Garamond', 16)).place(x=430, y=50)
    
        # creating a entry for IndexStopLoss
        r5 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r5.insert(0, dict_runtime_inputs["IndexStopLoss"])
        r5.place(x=590, y=50)
    
        # the label for IndexTarget
        Label(view_runtime_input_root, text="IndexTarget", font=('Garamond', 16)).place(x=430, y=100)
    
        # creating a entry for IndexTarget
        r6 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r6.insert(0, dict_runtime_inputs["IndexTarget"])
        r6.place(x=590, y=100)
    
        # the label for IndexTrailing
        Label(view_runtime_input_root, text="IndexTrailing", font=('Garamond', 16)).place(x=430, y=150)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected4():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["IndexTrailing"] = var4.get()
            if dict_runtime_inputs["IndexTrailing"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var4 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var4.set(dict_runtime_inputs["IndexTrailing"])
        #print(dict_runtime_inputs["IndexTrailing"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var4, value="True", command=viewSelected4)
    
        # placing the radio button
        R1.place(x=575, y=150)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var4, value="False", command=viewSelected4)
    
        # placing the radio button
        R2.place(x=643, y=150)
    
        # the label for IndexSLInc
        Label(view_runtime_input_root, text="IndexSLInc", font=('Garamond', 16)).place(x=430, y=200)
    
        # creating a entry for IndexSLInc
        r7 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r7.insert(0, dict_runtime_inputs["IndexSLInc"])
        r7.place(x=590, y=200)
    
        # the label for IndexSLReset
        Label(view_runtime_input_root, text="IndexSLReset", font=('Garamond', 16)).place(x=430, y=250)
    
        # fun is called when radiobutton for hold flag is selected
        def viewSelected5():
            global dict_runtime_inputs
    
            # setting the flag value to auto_flag
            dict_runtime_inputs["IndexSLReset"] = var5.get()
            if dict_runtime_inputs["IndexSLReset"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)
    
        # creating the raio buttons for auto flag
        var5 = StringVar()
    
        # setting the default value for the aut0_flag by using var
        var5.set(dict_runtime_inputs["IndexSLReset"])
        #print(dict_runtime_inputs["IndexSLReset"])
    
        # radio button for true
        R1 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var5, value="True", command=viewSelected5)
    
        # placing the radio button
        R1.place(x=575, y=250)
    
        # radio button for false
        R2 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var5, value="False", command=viewSelected5)
    
        # placing the radio button
        R2.place(x=643, y=250)
    
        # the label for IndexSLRP
        Label(view_runtime_input_root, text="IndexSLRP", font=('Garamond', 16)).place(x=430, y=300)
        # creating a entry for IndexSLRP
        r8 = tk.Entry(view_runtime_input_root, font=('Garamond', 16), bd=1,width=12)
        r8.insert(0, dict_runtime_inputs["IndexSLRP"])
        r8.place(x=590, y=300)
        
        Label(view_runtime_input_root, text="Index Target",font=('Garamond', 16)).place(x=430, y=350)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected11():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["Index_target_set"] = var11.get()
            if dict_runtime_inputs["Index_target_set"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var11 = StringVar()

        # setting the default value for the aut0_flag by using var
        var11.set(dict_runtime_inputs["Index_target_set"])
        #print(dict_runtime_inputs["Index_target_set"])

        # radio button for true
        X11 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var11, value="True", command=viewSelected11)

        # placing the radio button
        X11.place(x=575, y=350)

        # radio button for false
        X12 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var11, value="False", command=viewSelected11)

        # placing the radio button
        X12.place(x=645, y=350)

        Label(view_runtime_input_root, text="Auto Exit",font=('Garamond', 16)).place(x=430, y=400)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected12():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["auto_exit"] = var12.get()
            if dict_runtime_inputs["auto_exit"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var12 = StringVar()

        # setting the default value for the aut0_flag by using var
        var12.set(dict_runtime_inputs["auto_exit"])
        #print(dict_runtime_inputs["Index_target_set"])

        # radio button for true
        X13 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var12, value="True", command=viewSelected12)

        # placing the radio button
        X13.place(x=575, y=400)

        # radio button for false
        X14 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var12, value="False", command=viewSelected12)

        # placing the radio button
        X14.place(x=645, y=400)

        Label(view_runtime_input_root, text="Auto Entry",font=('Garamond', 16)).place(x=50, y=400)

        # fun is called when radiobutton for hold flag is selected
        def viewSelected13():
            global dict_runtime_inputs

            # setting the flag value to auto_flag
            dict_runtime_inputs["auto_entry"] = var13.get()
            if dict_runtime_inputs["auto_entry"] == "True":
                output = "True"
            else:
                output = "False"
            #print(output)

        # creating the raio buttons for auto flag
        var13 = StringVar()

        # setting the default value for the aut0_flag by using var
        var13.set(dict_runtime_inputs["auto_entry"])
        #print(dict_runtime_inputs["Index_target_set"])

        # radio button for true
        X15 = Radiobutton(view_runtime_input_root, text="True",font=('Garamond', 15), variable=var13, value="True", command=viewSelected13)

        # placing the radio button
        X15.place(x=180, y=400)

        # radio button for false
        X16 = Radiobutton(view_runtime_input_root, text="False",font=('Garamond', 15), variable=var13, value="False", command=viewSelected13)

        # placing the radio button
        X16.place(x=243, y=400)


        # this function will close the view_inputs_root widget
        def Close_modify_runtime_inputs():
            view_runtime_input_root.destroy()
            gc.collect()
        # function is called when modify is clicked
        def modify_runtime_inputs():
            global dict_runtime_inputs
            global dict_inputs
            global r1, r2, r3, r4, r5, r6, r7, r8, r9,r10    

            # function to assign and display modified values
            #print("OptMode : ", dict_runtime_inputs["OptMode"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptStopLoss"] = int(r1.get())
            #print("OptStopLoss : ", dict_runtime_inputs["OptStopLoss"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptTarget"] = int(r2.get())
            #print("OptTarget : ", dict_runtime_inputs["OptTarget"])
    
            # function to assign and display modified values
            #print("OptTrailing : ", dict_runtime_inputs["OptTrailing"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptSLInc"]= int(r3.get())
            #print("OptSLInc : ", dict_runtime_inputs["OptSLInc"])
    
            # function to assign and display modified values
            #print("OptSLReset : ", dict_runtime_inputs["OptSLReset"])
    
            # function to assign and display modified values
            dict_runtime_inputs["OptSLRP"] = int(r4.get())
            #print("OptSLRP : ", dict_runtime_inputs["OptSLRP"])
    
            # function to assign and display modified values
            #print("Opt Target Set: ", dict_runtime_inputs["Opt_target_set"])

            # function to assign and display modified values
            #print("IndexMode : ", dict_runtime_inputs["IndexMode"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexStopLoss"] = int(r5.get())
            #print("IndexStopLoss : ", dict_runtime_inputs["IndexStopLoss"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexTarget"] = int(r6.get())
            #print("IndexTarget : ", dict_runtime_inputs["IndexTarget"])
    
            # function to assign and display modified values
            #print("IndexTrailing : ", dict_runtime_inputs["IndexTrailing"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexSLInc"] = int(r7.get())
            #print("IndexSLInc : ", dict_runtime_inputs["IndexSLInc"])
    
            # function to assign and display modified values
            #print("IndexSLReset : ", dict_runtime_inputs["IndexSLReset"])
    
            # function to assign and display modified values
            dict_runtime_inputs["IndexSLRP"] = int(r8.get())
            #print("IndexSLRP : ", dict_runtime_inputs["IndexSLRP"])

            # function to assign and display modified values
            #print("Index Target Set: ", dict_runtime_inputs["Index_target_set"])

    
            var=StringVar()
            label = Message(view_runtime_input_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

            #var.set(IndexTarget_points)
            var.set("Runtimeinputs Modified")
            label.place(x=290,y=400) 
        # creating button for modify
        b1 = tk.Button(view_runtime_input_root, text='Modify',
                       command=lambda: modify_runtime_inputs(), width=14, heigh=3, font=("Arial", 15),bg="#3CB371")
        # placing the button
        b1.place(x=170, y=450)
        # creating button for cancel
        b2 = tk.Button(view_runtime_input_root, text='Close',
                       command=lambda: Close_modify_runtime_inputs(), width=14, height=3, font=("Arial", 15),bg="RED")
        # placing the button
        b2.place(x=470, y=450)
        # Call function to make the widget stay on top
        view_runtime_input_root.attributes('-topmost', True)
    
        # the widget will keep on displaying in loop
        view_runtime_input_root.mainloop()
    #fun is called when ce_entry is clicked
    def ce_entry():

        # to display a message box for conformation
        '''res = mb.askquestion('NF CE Entry',
                             'Entry NF CE')
        if res == 'yes':

        '''
        logging.info("ce entered from entry button")
        init_ce_entry()
    def Exit():
        #print("Exited code from secondwindow")
        os._exit(os.EX_OK)
    
    # the label for CapitalBased
    Label(main_root, text="CapitalBased", font=('Garamond', 16)).place(x=30, y=20)

    # fun is called when radiobutton for hold flag is seleced
    def viewSelected6():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["CapitalBased"] = var6.get()
        if dict_runtime_inputs["CapitalBased"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var6 = StringVar()

    # setting the default value for the aut0_flag by using var
    var6.set(dict_runtime_inputs["CapitalBased"])
    #print(dict_runtime_inputs["CapitalBased"])

    # radio button for true
    R1 = Radiobutton(main_root, text="True",font=('Garamond', 15), variable=var6, value="True", command=viewSelected6)

    # placing the radio button
    R1.place(x=160, y=20)

    # radio button for false
    R2 = Radiobutton(main_root, text="False",font=('Garamond', 15), variable=var6, value="False", command=viewSelected6)

    # placing the radio button
    R2.place(x=235, y=20)
    
    #the label for Capital
    Label(main_root,text="Capital :",font=('Garamond', 16)).place(x=30, y=60)
    # creating a entry for Capital
    r1 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width=10)
    r1.insert(0, dict_runtime_inputs["Capital"])
    r1.place(x=150, y=60)

    def modify_capital():

        global dict_runtime_inputs
        if(dict_runtime_inputs["CapitalBased"] == "True"):
            dict_runtime_inputs["Capital"] = int(r1.get())

            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold"))

            var.set(dict_runtime_inputs["Capital"])
            var.set("Capital modified")
            label.place(x=380,y=10)
    # Create a Button for zero

    a3 = tk.Button(main_root, text='M',
                   command=lambda: modify_capital(), bg="#1E90FF",width=3, height=0, font=("Garamond", 10))
    a3.place(x=245,y=60)

    #the label for Capital
    Label(main_root,text="Lots :",font=('Garamond', 16)).place(x=30, y=100)
    # creating a entry for Capital
    r2 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width=10)
    r2.insert(0, dict_runtime_inputs["OptQuantityLots"])
    r2.place(x=150, y=100)

    def modify_lots():

        global dict_runtime_inputs
        if(dict_runtime_inputs["CapitalBased"] == "False"):
            dict_runtime_inputs["OptQuantityLots"] = int(r2.get())

            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold"))

            var.set(dict_runtime_inputs["OptQuantityLots"])
            var.set("Lots modified")
            label.place(x=380,y=10)
    # Create a Button for zero

    a4 = tk.Button(main_root, text='M',
                   command=lambda: modify_lots(), bg="#1E90FF",width=3, height=0, font=("Garamond", 10))
    a4.place(x=245,y=100)

    def save_config():
        global dict_runtime_inputs
        global dict_runtime_inputs_default

        dict_runtime_inputs_default["CapitalBased"] = dict_runtime_inputs["CapitalBased"]
        dict_runtime_inputs_default["Capital"] = dict_runtime_inputs["Capital"]
        dict_runtime_inputs_default["OptQuantityLots"] = dict_runtime_inputs["OptQuantityLots"]
        dict_runtime_inputs_default["OptBuyDepth"] = dict_runtime_inputs["OptBuyDepth"]
        dict_runtime_inputs_default["LiveTrade"] = dict_runtime_inputs["LiveTrade"]
        dict_runtime_inputs_default["auto_entry"] = dict_runtime_inputs["auto_entry"]
        dict_runtime_inputs_default["auto_exit"] = dict_runtime_inputs["auto_exit"]

        var = StringVar()
        label = Message(main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold"))

        var.set("Config Saved")
        label.place(x=380,y=10)

    a5 = tk.Button(main_root, text='Save Config',
                   command=lambda: save_config(), bg="Yellow",width=11, height=3, font=("Garamond", 10))
    a5.place(x=300,y=70)

    # the label for Strike Price in the main window
    Label(main_root, text='Buy Depth:',font=("Arial", 16)).place(x=30,y=220)
    # creating a entry box for strike ce
    e7 = Entry(main_root,font=("Arial", 16),width=10)
    e7.insert(0,dict_runtime_inputs["OptBuyDepth"])
    e7.place(x=150,y=220)

    def modify_buyDepth():
        global dict_runtime_inputs
        dict_runtime_inputs["OptBuyDepth"] = int(e7.get())

        var = StringVar()
        label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold"))

        var.set(dict_runtime_inputs["OptBuyDepth"])
        var.set("BuyDepth modified")
        label.place(x=380,y=10)
    # Create a Button for zero

    a4 = tk.Button(main_root, text='M',
                   command=lambda: modify_buyDepth(), bg="#1E90FF",width=3, height=0, font=("Garamond", 10))
    a4.place(x=245,y=220)

    # the label for Strike Price in the main window
    Label(main_root, text='Margin Req:',font=("Arial", 16)).place(x=25,y=260)
    # creating a entry box for strike ce
    e8 = Entry(main_root,font=("Arial", 16),width=10)
    e8.place(x=150,y=260)

    def margin_req():

        global margin_amount_required
        global dict_runtime_inputs
        basket_margin()
        #margin_amount_required = int(e6.get())
        e8.delete(0, END)
        if(dict_runtime_inputs["CapitalBased"] == 'False'):
            e8.insert(0,round(margin_amount_required))
            # creating the raio buttons for auto flag
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold") )
            var.set(margin_amount_required)
            # Create a Button for zero

    a5 = tk.Button(main_root, text='S',
                   command=lambda: margin_req(), bg="Yellow",width=3, height=0, font=("Garamond", 10))
    a5.place(x=245,y=260)


    #the label for Strike Price in the main window
    Label(main_root, text='Strike Price :',font=("Arial", 16)).place(x=30,y=140)
    # creating a entry box for strike price
    e1 = Entry(main_root,font=("Arial", 16),width=22)
    e1.insert(0,opt_trade_symbol)
    e1.place(x=170,y=140)
    
    # the label for Strike Price in the main window
    Label(main_root, text='NF Index :',font=("Arial", 16)).place(x=30,y=180)
    # creating a entry box for strike price
    e2 = Entry(main_root,font=("Arial", 16),width=6)
    #e1.insert(0,ltp)
    e2.place(x=130,y=180)

    # the label for Strike Price in the main window
    Label(main_root, text='Premium :',font=("Arial", 16)).place(x=230,y=180)
    # creating a entry box for strike price
    e3 = Entry(main_root,font=("Arial", 16),width=6)
    #e1.insert(0,ltp)
    e3.place(x=320,y=180)

    Label(main_root, text="Idx SL",font=('Garamond', 16)).place(x=30, y=300)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected111():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["IndexStopLoss"] = var111.get()
        #print(dict_runtime_inputs["IndexStopLoss"])
     # creating the raio buttons for auto flag
    var111 = StringVar()

    # setting the default value for the aut0_flag by using var
    var111.set(dict_runtime_inputs["IndexStopLoss"])

    #print(dict_runtime_inputs["IndexStopLoss"])

    # radio button for true
    X111 = Radiobutton(main_root, text="-10",font=('Garamond', 15), variable=var111, value="-10", command=viewSelected111)

    # placing the radio button
    X111.place(x=100, y=295)

    # radio button for false
    X112 = Radiobutton(main_root, text="-20",font=('Garamond', 15), variable=var111, value="-20", command=viewSelected111)

    # placing the radio button
    X112.place(x=150, y=295)

    # radio button for true
    X113 = Radiobutton(main_root, text="-30",font=('Garamond', 15), variable=var111, value="-30", command=viewSelected111)

    # placing the radio button
    X113.place(x=200, y=295)

    # radio button for true
    X114 = Radiobutton(main_root, text="-40",font=('Garamond', 15), variable=var111, value="-40", command=viewSelected111)

    # placing the radio button
    X114.place(x=250, y=295)

    # radio button for true
    X115 = Radiobutton(main_root, text="-50",font=('Garamond', 15), variable=var111, value="-50", command=viewSelected111)

    # placing the radio button
    X115.place(x=300, y=295)

    # radio button for false
    X116 = Radiobutton(main_root, text="-60",font=('Garamond', 15), variable=var111, value="-60", command=viewSelected111)

    # placing the radio button
    X116.place(x=100, y=325)

    # radio button for true
    X117 = Radiobutton(main_root, text="-70",font=('Garamond', 15), variable=var111, value="-70", command=viewSelected111)

    # placing the radio button
    X117.place(x=150, y=325)

    # radio button for true
    X118 = Radiobutton(main_root, text="-80",font=('Garamond', 15), variable=var111, value="-80", command=viewSelected111)

    # placing the radio button
    X118.place(x=200, y=325)

    # radio button for true
    X119 = Radiobutton(main_root, text="-90",font=('Garamond', 15), variable=var111, value="-90", command=viewSelected111)

    # placing the radio button
    X119.place(x=250, y=325)

    # radio button for true
    X120 = Radiobutton(main_root, text="-100",font=('Garamond', 15), variable=var111, value="-100", command=viewSelected111)

    # placing the radio button
    X120.place(x=300, y=325)

    
    # Create a Button for runtime inputs
    b1 = tk.Button(main_root, text='RunTime Inputs',
                   command=lambda: view_runtime_input(), width=15, height=4, font=("Arial", 15))
    
    # placing the button
    b1.place(x=400, y=40)

    # fun is called when radiobutton for hold flag is seleced
    def viewSelect():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["LiveTrade"] = vari.get()
        if dict_runtime_inputs["LiveTrade"] == 'True':
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    vari = StringVar()

    # setting the default value for the aut0_flag by using var
    vari.set(dict_runtime_inputs["LiveTrade"])
    #print(dict_runtime_inputs["LiveTrade"])

    # radio button for true
    R1 = Radiobutton(main_root, text="Live ",font=('Garamond', 15), variable=vari, value="True", command=viewSelect)

    # placing the radio button
    R1.place(x=400, y=130)

    # radio button for false
    R2 = Radiobutton(main_root, text="Paper ",font=('Garamond', 15), variable=vari, value="False", command=viewSelect)

    # placing the radio button
    R2.place(x=490, y=130)
    
    # Create a Button for ce entry
    b3 = tk.Button(main_root, text='NF CE Entry',
                   command=lambda: ce_entry(),  bg="#3CB371" ,width=14, heigh=4, font=("Arial", 15))
    
    # placing the ce entry button
    b3.place(x=400, y=170)
    b4 = tk.Button(main_root, text='Exit',
                   command=lambda: Exit(),  bg="RED" ,width=14, heigh=3, font=("Arial", 15))

    # placing the ce entry button
    b4.place(x=400, y=290)
    
    # Call function to make the window stay on top
    main_root.attributes('-topmost', True)
    #to update strike price and ltp
    def sw_update():

        e1.delete(0, END)
        e1.insert(0,opt_trade_symbol)
        e2.delete(0, END)
        e2.insert(0,round(ltp))
        e3.delete(0, END)
        e3.insert(0,(round(opt_premium,2)))

        if(script_name in traded_scripts):
            #main_root.after_cancel(sw_after)
            logging.info("In second window destroy")
            Close()
        sw_after = main_root.after(5000,sw_update)
    sw_update()
    # the widget will keep on displaying in loop
    main_root.mainloop()

def ce_thirdwindow():
    global profit
    global profit_perc
    global loss
    global loss_per
    global traded_index_points
    global index_ltp
    global IndexStopLoss_points
    global IndexTarget_points
    global profit_points
    global loss_points
    global script_name
    global traded_scripts
    global opt_ce_entry_trade_symbol
    global opt_ce_entry_avg_price
    global opt_ce_entry_qty_sum
    global opt_ce_entry_amount
    global dict_runtime_inputs
    global dict_runtime_inputs_default
    global y1,y2,x1, x2, x3, x4, x5, x6, x7, x8
    global r1,r2,r3,r4,r5,r6,r7,r8,r9,r10,r11,r12,r13,r14,r15,r1,r17,r18

    # create a tkinter main_root window
    main_root = Tk()
    # main_root window title and dimension
    main_root.title("NF CE Trade")
    main_root.geometry('1280x840+0+0')
    main_root['bg'] = '#C0C0C0'
    logging.info("Third window is opened")
    if (dict_runtime_inputs["LiveTrade"] == 'True'):
        Label(main_root, text="Live Trade", bg="WHITE",fg="RED", font=('Garamond', 22,'bold')).place(x=550, y=10)
    else:
        Label(main_root, text="Paper Trade", bg="WHITE",fg="GREEN",font=('Garamond', 22,'bold')).place(x=550, y=10)

    # function for viewing runtime inputs

    Label(main_root, text="Runtime Inputs", bg="#C0C0C0",font=('Garamond', 17,'bold')).place(x=880, y=0)
    Label(main_root, text="Option", bg="#C0C0C0",font=('Garamond', 16)).place(x=740, y=25)
    # the label for opt_mode_status

    # the label for opt_stoploss_perc
    Label(main_root, text="Opt SL %",bg="#C0C0C0",fg="#CC6600", font=('Garamond', 16)).place(x=620, y=330)

    # creating a entry for opt_stoploss_perc
    x1 = tk.Entry(main_root, font=('Garamond', 16), width=10,bd=1)
    x1.insert(0, dict_runtime_inputs["OptStopLoss"])
    x1.place(x=770, y=330)
    def modify_optstoploss():
        global dict_runtime_inputs
        global opt_stoploss_price
        global opt_ce_entry_avg_price
        OS = int(x1.get())
        if(OS <= 0):
            dict_runtime_inputs["OptStopLoss"] = int(x1.get())
            #print("OptStopLoss : ", dict_runtime_inputs["OptStopLoss"])
            opt_stoploss_price = opt_ce_entry_avg_price * (100 + (int(dict_runtime_inputs["OptStopLoss"]))) / 100
            r4.delete(0,END)
            r4.insert(0,dict_runtime_inputs["OptStopLoss"])
            r4.insert(5," %")
            r3.delete(0,END)
            r3.insert(0,round(opt_stoploss_price))
                    
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

            #var.set(IndexTarget_points)
            var.set("Opt SL modified")
            label.place(x=890,y=430)
    # Create a Button for zero

    a5 = tk.Button(main_root, text='M',
                   command=lambda: modify_optstoploss(), bg="RED",width=3, height=0, font=("Garamond", 10))
    a5.place(x=870,y=330)

    # the label for opt_target_perc
    Label(main_root, text="Opt TP %",bg="#C0C0C0", fg="#0020C2",font=('Garamond', 16)).place(x=620, y=290)

    # creating a entry for opt_target_perc value
    x2 = tk.Entry(main_root, font=('Garamond', 16),width = 10, bd=1)
    x2.insert(0, dict_runtime_inputs["OptTarget"])
    x2.place(x=770, y=290)
    def modify_opttarget():
        global dict_runtime_inputs
        global opt_target_price
        global opt_ce_entry_avg_price
        OT = int(x2.get())
        if(OT >= 0):
            dict_runtime_inputs["OptTarget"] = int(x2.get())
            #print("OptTarget : ", dict_runtime_inputs["OptTarget"])
            opt_target_price = opt_ce_entry_avg_price * (100 + int(dict_runtime_inputs["OptTarget"])) / 100
            r6.delete(0,END)
            r6.insert(0,dict_runtime_inputs["OptTarget"])
            r6.insert(5," %")
            r5.delete(0,END)
            r5.insert(0,round(opt_target_price))
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

            #var.set(IndexTarget_points)
            var.set("Opt TP modified")
            label.place(x=890,y=430)
            #label.after(100000, label.destroy())
    # Create a Button for zero

    a6 = tk.Button(main_root, text='M',
                   command=lambda: modify_opttarget(), bg="#3CB371",width=3, height=0, font=("Garamond", 10))
    a6.place(x=870,y=290)
    
    Label(main_root, text="Opt Target",bg="#C0C0C0", font=('Garamond', 16)).place(x=620, y=250)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected22():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["Opt_target_set"] = var22.get()
        if dict_runtime_inputs["Opt_target_set"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var22 = StringVar()

    # setting the default value for the aut0_flag by using var
    var22.set(dict_runtime_inputs["Opt_target_set"])
    #print(dict_runtime_inputs["Opt_target_set"])

    # radio button for true
    X13 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var22, value="True", command=viewSelected22)

    # placing the radio button
    X13.place(x=770, y=250)

    # radio button for false
    X14 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var22, value="False", command=viewSelected22)

    # placing the radio button
    X14.place(x=830, y=250)

    # the label for opt_trailing
    Label(main_root, text="OptTrailing",bg="#C0C0C0",font=('Garamond', 16)).place(x=620, y=65)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected11():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["OptTrailing"] = var11.get()
        if dict_runtime_inputs["OptTrailing"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var11 = StringVar()

    # setting the default value for the aut0_flag by using var
    var11.set(dict_runtime_inputs["OptTrailing"])
    #print(dict_runtime_inputs["OptTrailing"])

    # radio button for true
    X3 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var11, value="True", command=viewSelected11)

    # placing the radio button
    X3.place(x=770, y=65)

    # radio button for false
    X4 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var11, value="False", command=viewSelected11)

    # placing the radio button
    X4.place(x=830, y=65)

    # the label for opt_slinc
    Label(main_root, text="Opt Slinc",bg="#C0C0C0", font=('Garamond', 16)).place(x=620, y=100)

    # creating a combobox for opt_slinc
    x3 = tk.Entry(main_root,  width=10 ,font=('Garamond', 16), bd=1)
    x3.insert(0, dict_runtime_inputs["OptSLInc"])
    x3.place(x=770, y=100)

    def modify_optslinc():
        global dict_runtime_inputs

        dict_runtime_inputs["OptSLInc"] = int(x3.get())
        #print("OptSLInc : ", dict_runtime_inputs["OptSLInc"])
        var = StringVar() 
        label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )
        
        var.set(dict_runtime_inputs["OptSLInc"])
        var.set("OptSlInc modified")
        label.place(x=890,y=430)


    # Create a Button for zero

    a1 = tk.Button(main_root, text='M',
                   command=lambda: modify_optslinc(), bg="#FFEF53",width=3, height=0, font=("Garamond", 10))
    a1.place(x=870,y=100)
    # the label for opt_reset
    Label(main_root, text="Opt Reset",bg="#C0C0C0", font=('Garamond', 16)).place(x=620, y=160)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected12():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["OptSLReset"] = var12.get()
        if dict_runtime_inputs["OptSLReset"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var12 = StringVar()

    # setting the default value for the aut0_flag by using var
    var12.set(dict_runtime_inputs["OptSLReset"])
    #print(dict_runtime_inputs["OptSLReset"])

    # radio button for true
    X5 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var12, value="True", command=viewSelected12)

    # placing the radio button
    X5.place(x=770, y=160)

    # radio button for false
    X6 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var12, value="False", command=viewSelected12)

    # placing the radio button
    X6.place(x=830, y=160)

    # the label for opt_slrp
    Label(main_root, text="Opt Slrp",bg="#C0C0C0", font=('Garamond', 16)).place(x=620, y=195)

    # creating a entry for opt_slrp
    x4 = tk.Entry(main_root,  width=10,font=('Garamond', 16), bd=1)
    x4.insert(0, dict_runtime_inputs["OptSLRP"])
    x4.place(x=770, y=195)

    def modify_optslrp():
        global dict_runtime_inputs

        dict_runtime_inputs["OptSLRP"] = int(x4.get())
        #print("OptSLRP : ", dict_runtime_inputs["OptSLRP"])
        var = StringVar() 
        label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

        var.set(dict_runtime_inputs["OptSLRP"])
        var.set("OptSlrp modified")
        label.place(x=890,y=430)
    # Create a Button for zero

    a2 = tk.Button(main_root, text='M',
                 command=lambda: modify_optslrp(), bg="#1E90FF",width=3, height=0, font=("Garamond", 10))
    a2.place(x=870,y=195)

    # the label for index_mode_status
    Label(main_root, text="Index", bg="#C0C0C0",font=("Garamond", 16)).place(x=1090, y=25)
    # the label for index_stoploss
    Label(main_root, text="Index SL Pts",bg="#C0C0C0",fg="#E55451", font=('Garamond', 16)).place(x=950, y=330)

    # creating a entry for index_stoploss
    x5 = tk.Entry(main_root,  width = 10 ,font=('Garamond', 16), bd=1)
    x5.insert(0, round(IndexStopLoss_points))
    x5.place(x=1110, y=330)

    def modify_indexstoploss():

        global IndexStopLoss_points
        global traded_index_points
        global IndexStopLoss_real
        global dict_runtime_inputs
        IS = float(x5.get())
        if(IS <= traded_index_points):
            # function to assign and display modified values
            IndexStopLoss_points = float(x5.get())
            #print("IndexStopLoss : ", round(IndexStopLoss_points))
            r13.delete(0,END)
            r13.insert(0,round(IndexStopLoss_points))
            dict_runtime_inputs["IndexStopLoss"]= IndexStopLoss_points - traded_index_points
            r17.delete(0,END)
            r17.insert(0, round(dict_runtime_inputs["IndexStopLoss"]))
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )
            #var.set(IndexTarget_points)
            var.set("Index SL points modified")
            label.place(x=890,y=430)
    # Create a Button for zero

    a7 = tk.Button(main_root, text='M',
                   command=lambda: modify_indexstoploss(), bg="RED",width=3, height=0, font=("Garamond", 10))
    a7.place(x=1210,y=330)

    Label(main_root, text="Index Target",bg="#C0C0C0", font=('Garamond', 16)).place(x=950, y=250)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected11():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["Index_target_set"] = var11.get()
        if dict_runtime_inputs["Index_target_set"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var11 = StringVar()

    # setting the default value for the aut0_flag by using var
    var11.set(dict_runtime_inputs["Index_target_set"])
    #print(dict_runtime_inputs["Index_target_set"])

    # radio button for true
    X11 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var11, value="True", command=viewSelected11)

    # placing the radio button
    X11.place(x=1110, y=250)

    # radio button for false
    X12 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var11, value="False", command=viewSelected11)

    # placing the radio button
    X12.place(x=1175, y=250)

    # the label for index_target
    Label(main_root, text="Index TP Pts",bg="#C0C0C0",fg="#357EC7", font=('Garamond', 16)).place(x=950, y=290)

    # creating a entry for index_target
    x6 = tk.Entry(main_root, width = 10 ,font=('Garamond', 16), bd=1)
    x6.insert(0, round(IndexTarget_points))
    x6.place(x=1110, y=290)

    def modify_indextarget():

        global IndexTarget_points
        global traded_index_points
        global dict_runtime_inputs
        IT = float(x6.get())
        if(IT >= traded_index_points):

            # function to assign and display modified values
            IndexTarget_points = float(x6.get())
            #print("IndexTarget : ", round(IndexTarget_points))
            r14.delete(0,END)
            r14.insert(0,round(IndexTarget_points))
            dict_runtime_inputs["IndexTarget"]= IndexTarget_points - traded_index_points
            r18.delete(0,END)
            r18.insert(0, round(dict_runtime_inputs["IndexTarget"]))
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

            #var.set(IndexTarget_points)
            var.set("Index TP points modified")
            label.place(x=890,y=430)
    # Create a Button for zero

    a8 = tk.Button(main_root, text='M',
                   command=lambda: modify_indextarget(), bg="#3CB371",width=3, height=0, font=("Garamond", 10))
    a8.place(x=1210,y=290)

    Label(main_root, text="Idx SL",fg="RED",font=('Garamond', 16)).place(x=620, y=370)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected111():
        global dict_runtime_inputs
        global IndexStopLoss_points
        global traded_index_points,x5

        # setting the flag value to auto_flag
        dict_runtime_inputs["IndexStopLoss"] = var111.get()
        #r13.delete(0,END)

        IndexStopLoss_points = traded_index_points + int(dict_runtime_inputs["IndexStopLoss"])
        #r13.insert(0, round(IndexStopLoss_points))
        x5.delete(0,END)
        x5.insert(0, round(IndexStopLoss_points))
        #print(dict_runtime_inputs["IndexStopLoss"])
        #print("IndexStopLoss_points",IndexStopLoss_points)

        var = StringVar()
        label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

        #var.set(IndexTarget_points)
        var.set("Index SL modified")
        label.place(x=890,y=430)

     # creating the raio buttons for auto flag
    var111 = StringVar()

    # setting the default value for the aut0_flag by using var
    var111.set(dict_runtime_inputs["IndexStopLoss"])

    #print(dict_runtime_inputs["IndexStopLoss"])

    # radio button for true
    X111 = Radiobutton(main_root, text="-10",font=('Garamond', 15), variable=var111, value="-10", command=viewSelected111)

    # placing the radio button
    X111.place(x=680, y=370)

    # radio button for true
    X112 = Radiobutton(main_root, text="-20",font=('Garamond', 15), variable=var111, value="-20", command=viewSelected111)

    # placing the radio button
    X112.place(x=730, y=370)
    # radio button for true
    # radio button for true
    X113 = Radiobutton(main_root, text="-30",font=('Garamond', 15), variable=var111, value="-30", command=viewSelected111)

    # placing the radio button
    X113.place(x=780, y=370)
    # radio button for true
    X114 = Radiobutton(main_root, text="-40",font=('Garamond', 15), variable=var111, value="-40", command=viewSelected111)

    # placing the radio button
    X114.place(x=830, y=370)
    # radio button for true
    X115 = Radiobutton(main_root, text="-50",font=('Garamond', 15), variable=var111, value="-50", command=viewSelected111)

    # placing the radio button
    X115.place(x=880, y=370)

    # radio button for true
    X116 = Radiobutton(main_root, text="-60",font=('Garamond', 15), variable=var111, value="-60", command=viewSelected111)

    # placing the radio button
    X116.place(x=680, y=400)

    # radio button for true
    X117 = Radiobutton(main_root, text="-70",font=('Garamond', 15), variable=var111, value="-70", command=viewSelected111)

    # placing the radio button
    X117.place(x=730, y=400)

    # radio button for true
    X118 = Radiobutton(main_root, text="-80",font=('Garamond', 15), variable=var111, value="-80", command=viewSelected111)

    # placing the radio button
    X118.place(x=780, y=400)

    # radio button for true
    X119 = Radiobutton(main_root, text="-90",font=('Garamond', 15), variable=var111, value="-90", command=viewSelected111)

    # placing the radio button
    X119.place(x=830, y=400)

    # radio button for true
    X120 = Radiobutton(main_root, text="-100",font=('Garamond', 15), variable=var111, value="-100", command=viewSelected111)

    X120.place(x=880, y=400)

    Label(main_root, text="Idx TP",fg="GREEN",font=('Garamond', 16)).place(x=955, y=370)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected112():
        global dict_runtime_inputs
        global IndexTarget_points
        global traded_index_points,x6

        # setting the flag value to auto_flag
        dict_runtime_inputs["IndexTarget"] = var112.get()
        #r13.delete(0,END)

        IndexTarget_points = traded_index_points + int(dict_runtime_inputs["IndexTarget"])
        #r13.insert(0, round(IndexStopLoss_points))
        x6.delete(0,END)
        x6.insert(0, round(IndexTarget_points))
        #print(dict_runtime_inputs["IndexTarget"])
        #print("IndexTarget_points",IndexTarget_points)

        var = StringVar()
        label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

        #var.set(IndexTarget_points)
        var.set("Index TP modified")
        label.place(x=890,y=430)

     # creating the raio buttons for auto flag
    var112 = StringVar()

    # setting the default value for the aut0_flag by using var
    var112.set(dict_runtime_inputs["IndexTarget"])

    #print(dict_runtime_inputs["IndexTarget"])

    # radio button for true
    X120 = Radiobutton(main_root, text="50",font=('Garamond', 15), variable=var112, value="50", command=viewSelected112)

    X120.place(x=1035, y=370)

    # radio button for true
    X111 = Radiobutton(main_root, text="60",font=('Garamond', 15), variable=var112, value="60", command=viewSelected112)

    # placing the radio button
    X111.place(x=1075, y=370)

    # radio button for true
    X112 = Radiobutton(main_root, text="70",font=('Garamond', 15), variable=var112, value="70", command=viewSelected112)

    # placing the radio button
    X112.place(x=1120, y=370)
    # radio button for true
    # radio button for true
    X113 = Radiobutton(main_root, text="80",font=('Garamond', 15), variable=var112, value="80", command=viewSelected112)

    # placing the radio button
    X113.place(x=1165, y=370)
    # radio button for true
    X114 = Radiobutton(main_root, text="90",font=('Garamond', 15), variable=var112, value="90", command=viewSelected112)

    # placing the radio button
    X114.place(x=1210, y=370)
    # radio button for true
    X115 = Radiobutton(main_root, text="100",font=('Garamond', 15), variable=var112, value="100", command=viewSelected112)

    # placing the radio button
    X115.place(x=1025, y=400)

    # radio button for true
    X116 = Radiobutton(main_root, text="125",font=('Garamond', 15), variable=var112, value="125", command=viewSelected112)

    # placing the radio button
    X116.place(x=1075, y=400)

    # radio button for true
    X117 = Radiobutton(main_root, text="150",font=('Garamond', 15), variable=var112, value="150", command=viewSelected112)

    # placing the radio button
    X117.place(x=1125, y=400)

    # radio button for true
    X118 = Radiobutton(main_root, text="175",font=('Garamond', 15), variable=var112, value="175", command=viewSelected112)

    X118.place(x=1175, y=400)

    # radio button for true
    X119 = Radiobutton(main_root, text="200",font=('Garamond', 15), variable=var112, value="200", command=viewSelected112)

    X119.place(x=1225, y=400)
    # Create a Button for zero

    # the label for index_trailing
    Label(main_root, text="Index Trailing",bg="#C0C0C0", font=('Garamond', 16)).place(x=950, y=65)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected4():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["IndexTrailing"] = var4.get()
        if dict_runtime_inputs["IndexTrailing"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var4 = StringVar()

    # setting the default value for the aut0_flag by using var
    var4.set(dict_runtime_inputs["IndexTrailing"])
    #print(dict_runtime_inputs["IndexTrailing"])

    # radio button for true
    X9 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var4, value="True", command=viewSelected4)

    # placing the radio button
    X9.place(x=1110, y=65)

    # radio button for false
    X10 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var4, value="False", command=viewSelected4)

    # placing the radio button
    X10.place(x=1165, y=65)

    # the label for index_slinc
    Label(main_root, text="Index Slinc",bg="#C0C0C0", font=('Garamond', 16)).place(x=950, y=100)

    # creating a entry for index_slinc
    x7 = tk.Entry(main_root, width =10, font=('Garamond', 16), bd=1)
    x7.insert(0, dict_runtime_inputs["IndexSLInc"])
    x7.place(x=1110, y=100)

    def modify_indexslinc():

        global dict_runtime_inputs
        dict_runtime_inputs["IndexSLInc"] = int(x7.get())
        
        #print("IndexSLInc : ", dict_runtime_inputs["IndexSLInc"])
        var = StringVar()
        label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

        var.set(dict_runtime_inputs["IndexSLInc"])
        var.set("IndexSLInc modified")
        label.place(x=890,y=430)
    # Create a Button for zero

    a3 = tk.Button(main_root, text='M',
                   command=lambda: modify_indexslinc(), bg="#FFEF53",width=3, height=0, font=("Garamond", 10))
    a3.place(x=1210,y=100)


    # the label for index_slreset
    Label(main_root, text="Index slreset",bg="#C0C0C0", font=('Garamond', 16)).place(x=950, y=160)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected5():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["IndexSLReset"] = var5.get()
        if dict_runtime_inputs["IndexSLReset"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var5 = StringVar()

    # setting the default value for the aut0_flag by using var
    var5.set(dict_runtime_inputs["IndexSLReset"])
    #print(dict_runtime_inputs["IndexSLReset"])

    # radio button for true
    X11 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var5, value="True", command=viewSelected5)

    # placing the radio button
    X11.place(x=1110, y=160)

    # radio button for false
    X12 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var5, value="False", command=viewSelected5)

    # placing the radio button
    X12.place(x=1165, y=160)

    # the label for index_slrp
    Label(main_root, text="Index Slrp",bg="#C0C0C0", font=('Garamond', 16)).place(x=950, y=195)
    # creating a entry for index_slrp
    x8 = tk.Entry(main_root,width=10, font=('Garamond', 16), bd=1)
    x8.insert(0, dict_runtime_inputs["IndexSLRP"])
    x8.place(x=1110, y=195)
    
    def modify_indexslrp():
        
        global dict_runtime_inputs
        # function to assign and display modified values
        dict_runtime_inputs["IndexSLRP"] = int(x8.get())
        #print("IndexSLRP : ", dict_runtime_inputs["IndexSLRP"])

        # creating the raio buttons for auto flag
        var = StringVar()
        label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14,"bold") )

        var.set(dict_runtime_inputs["IndexSLRP"])
        var.set("IndexSLRP modified")
        label.place(x=890,y=430)
    # Create a Button for zero

    a4 = tk.Button(main_root, text='M',
                   command=lambda: modify_indexslrp(), bg="#1E90FF",width=3, height=0, font=("Garamond", 10))
    a4.place(x=1210,y=195)
    # Create a Button for zero

    #b1 = tk.Button(main_root, text='Opt Zero',
    #              command=lambda: Optzero(), bg="#3CB371",width=15, height=2, font=("Arial", 15))
    #b1.place(x=90,y=670)
    #b2 = tk.Button(main_root, text='Idx Zero',
    #               command=lambda: Idxzero(),  bg="#3CB371",width=15, height=2, font=("Arial", 15))
    #b2.place(x=380,y=670)

    # the label for opt_mode_status
    Label(main_root, text="Opt Mode", bg="#C0C0C0",font=('Garamond', 16)).place(x=110, y=50)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected2():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["OptMode"] = var2.get()
        if dict_runtime_inputs["OptMode"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var2 = StringVar()

    # setting the default value for the aut0_flag by using var
    var2.set(dict_runtime_inputs["OptMode"])
    #print(dict_runtime_inputs["OptMode"])

    # radio button for true2
    X1 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15) ,variable=var2, value="True", command=viewSelected2)

    # placing the radio button
    X1.place(x=240, y=50)

    # radio button for false
    X2 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15) ,variable=var2, value="False", command=viewSelected2)

    # placing the radio button
    X2.place(x=320, y=50)

    Label(main_root, text="Index Mode",bg="#C0C0C0", font=('Garamond', 16)).place(x=110, y=100)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected3():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["IndexMode"] = var3.get()
        if dict_runtime_inputs["IndexMode"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var3 = StringVar()

    # setting the default value for the aut0_flag by using var
    var3.set(dict_runtime_inputs["IndexMode"])
    #print(dict_runtime_inputs["IndexMode"])

    # radio button for true
    X7 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var3, value="True", command=viewSelected3)

    # placing the radio button
    X7.place(x=240, y=100)

    # radio button for false
    X8 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var3, value="False", command=viewSelected3)

    # placing the radio button
    X8.place(x=320, y=100)

    Label(main_root, text="Auto Entry",bg="#C0C0C0",font=('Garamond', 16)).place(x=110, y=150)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected12():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["auto_entry"] = var12.get()
        if dict_runtime_inputs["auto_entry"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var12 = StringVar()

    # setting the default value for the aut0_flag by using var
    var12.set(dict_runtime_inputs["auto_entry"])
    #print(dict_runtime_inputs["Index_target_set"])

    # radio button for true
    X13 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var12, value="True", command=viewSelected12)

    # placing the radio button
    X13.place(x=240, y=150)

    # radio button for false
    X14 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var12, value="False", command=viewSelected12)

    # placing the radio button
    X14.place(x=320, y=150)

    Label(main_root, text="Auto Exit",bg="#C0C0C0" ,font=('Garamond', 16)).place(x=110, y=200)

        # fun is called when radiobutton for hold flag is selected
    def viewSelected13():
        global dict_runtime_inputs

        # setting the flag value to auto_flag
        dict_runtime_inputs["auto_exit"] = var13.get()
        if dict_runtime_inputs["auto_exit"] == "True":
            output = "True"
        else:
            output = "False"
        #print(output)

    # creating the raio buttons for auto flag
    var13 = StringVar()

    # setting the default value for the aut0_flag by using var
    var13.set(dict_runtime_inputs["auto_exit"])
    #print(dict_runtime_inputs["Index_target_set"])

    # radio button for true
    X15 = Radiobutton(main_root, text="True",bg="#C0C0C0",font=('Garamond', 15), variable=var13, value="True", command=viewSelected13)

    # placing the radio button
    X15.place(x=240, y=200)

    # radio button for false
    X16 = Radiobutton(main_root, text="False",bg="#C0C0C0",font=('Garamond', 15), variable=var13, value="False", command=viewSelected13)

    # placing the radio button
    X16.place(x=320, y=200)

    Label(main_root, text="Buy Symbol", bg="#C0C0C0",font=('Garamond', 16)).place(x=110, y=250)

    # creating a entry for opt_ce_entry_amount
    r02 = tk.Entry(main_root,font=('Garamond', 16), bd=1,width =22)
    r02.insert(0, opt_ce_entry_trade_symbol)
    r02.place(x=240, y=250)

    # the label for opt_ce_entry_qty_sum
    Label(main_root, text="Buy Quantity", bg="#C0C0C0",font=('Garamond', 16)).place(x=110, y=300)

    # creating a entry for opt_ce_entry_qty_sum
    r01 = tk.Entry(main_root,font=('Garamond', 16), bd=1,width =11)
    r01.insert(0, round(opt_ce_entry_qty_sum))
    r01.place(x=240, y=300)

    Label(main_root, text="Buy Amount", bg="#C0C0C0",font=('Garamond', 16)).place(x=110, y=350)

    # creating a entry for opt_ce_entry_amount
    r02 = tk.Entry(main_root,font=('Garamond', 16), bd=1,width =11)
    r02.insert(0, round(opt_ce_entry_amount))
    r02.place(x=240, y=350)

    def ce_exit():
        # to display a message box for conformation
        '''res = mb.askquestion('NF CE Exit',
                             'Exit NF CE ')
        if res == 'yes':
        '''
        #logging.info("Third window is exited")
        init_ce_exit()


    def Close():
        logging.info("Third window is destroyed")
        main_root.destroy()
        gc.collect()


    # option #printing
    Label(main_root, text="Option", bg="#C0C0C0",font=('Garamond', 16)).place(x=150, y=450)

    # the label for opt_ce_entry_avg_price
    Label(main_root, text="Buy / Curr", bg="#C0C0C0",font=('Garamond', 16)).place(x=20, y=550)

    # creating a entry for opt_ce_entry_avg_price
    r1 = tk.Entry(main_root,font=('Garamond', 16), bd=1,width =7)
    r1.insert(0, round((opt_ce_entry_avg_price),1))
    r1.place(x=120, y=550)
    r2 = tk.Entry(main_root, font=('Garamond', 16),width =7)
    r2.insert(0,round((opt_curr_price),2))
    r2.place(x=190, y=550)


    # the label for opt_stoploss_perc
    Label(main_root, text="SL Prc / %", bg="#C0C0C0",fg="#CC6600",font=('Garamond', 16)).place(x=20, y=600)
    # creating a entry for opt_stoploss_price
    r3 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7,fg="RED")
    r3.insert(0,round(opt_stoploss_price))
    r3.place(x=120, y=600)
    # creating a entry for opt_stoploss_perc
    r4 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7 ,fg="RED")
    r4.insert(0,round(int(dict_runtime_inputs["OptStopLoss"])))
    r4.insert(5," %")
    r4.place(x=190, y=600)

    # the label for opt_target_perc
    Label(main_root, text="TP Prc / %", bg="#C0C0C0",fg="#0020C2",font=('Garamond', 16)).place(x=20, y=500)
    # creating a entry for opt_target_price
    r5 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7 ,fg="GREEN")
    r5.insert(0,round(opt_target_price))
    r5.place(x=120, y=500)
    # creating a entry for opt_target_perc
    r6 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7, fg="GREEN")
    r6.insert(0,round(int(dict_runtime_inputs["OptTarget"])))
    r6.insert(5," %")
    r6.place(x=190, y=500)

    # the label for profit
    Label(main_root, text="Profit",bg="#C0C0C0",fg="GREEN", font=('Garamond', 16)).place(x=940, y=600)

    # creating a entry for profit
    r7 = tk.Entry(main_root, fg='GREEN', font=('Garamond', 16), bd=1,width =11)
    r7.place(x=1090, y=600)

    # the label for profit_perc
    Label(main_root, text="Profit %",bg="#C0C0C0",fg="GREEN", font=('Garamond', 16)).place(x=940, y=550)

    # creating a entry for opt_profit_perc
    r8 = tk.Entry(main_root, fg='GREEN',font=('Garamond', 16), bd=1,width =11)
    r8.place(x=1090, y=550)

    # the label for loss
    Label(main_root, text="Loss",bg="#C0C0C0", fg='RED',font=('Garamond', 16)).place(x=630, y=600)

    # creating a entry for loss
    r9 = tk.Entry(main_root, fg='RED', font=('Garamond', 16), bd=1,width =11)
    r9.place(x=760, y=600)

    # the label for loss_perc
    Label(main_root, text="Loss %",bg="#C0C0C0",fg='RED', font=('Garamond', 16)).place(x=630, y=550)

    # creating a entry for loss_perc
    r10 = tk.Entry(main_root,fg='RED' , font=('Garamond', 16), bd=1,width =11)
    r10.place(x=760, y=550)

    # index #printing
    Label(main_root, text="Index",bg="#C0C0C0", font=('Garamond', 16)).place(x=410, y=450)

    # the label for traded_index_points
    Label(main_root, text="Traded / LTP", bg="#C0C0C0",font=('Garamond', 16)).place(x=290, y=550)

    # creating a entry for traded_index_points
    r11 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7)
    r11.insert(0, round((traded_index_points)))
    r11.place(x=410, y=550)
    r12 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7)
    r12.place(x=480, y=550)
    # the label for index_ltp

    # the label for IndexStopLoss_points
    Label(main_root, text="SL Pts/ %",bg="#C0C0C0",fg="#CD5C5C", font=('Garamond', 16)).place(x=295, y=600)

    # creating a entry for IndexStopLoss_points
    r13 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7 , fg="RED")
    r13.insert(0, round(IndexStopLoss_points))
    r13.place(x=410, y=600)
    #IndexStopLoss_real= traded_index_points + IndexStopLoss_points
    r17 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7 , fg="RED")
    r17.insert(0, int(dict_runtime_inputs["IndexStopLoss"]))
    r17.place(x=480, y=600)
    # the label for index_target_points
    Label(main_root, text="TP Pts/ %", bg="#C0C0C0" ,fg="#357EC7",font=('Garamond', 16)).place(x=295, y=500)

    # creating a entry for profit
    r14 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7 ,fg="GREEN")
    r14.insert(0, round(IndexTarget_points))
    r14.place(x=410, y=500)
    #IndexTarget_real= traded_index_points + IndexTarget_points
    r18 = tk.Entry(main_root, font=('Garamond', 16), bd=1,width =7 ,fg="GREEN")
    r18.insert(0, int(dict_runtime_inputs["IndexTarget"]))
    r18.place(x=480,y=500)
    # the label for profit_points
    # the label for profit_points
    Label(main_root, text="Profit Points", bg="#C0C0C0",fg="GREEN",font=('Garamond', 16)).place(x=940, y=500)

    # creating a entry for profit_points
    r15 = tk.Entry(main_root, fg="GREEN",font=('Garamond', 16), bd=1,width =11)
    r15.place(x=1090, y=500)

    # the label for loss_points
    Label(main_root, text="Loss Points", bg="#C0C0C0",fg="RED",font=('Garamond', 16)).place(x=630, y=500)

    # creating a entry for loss_points
    r16 = tk.Entry(main_root, fg="RED",font=('Garamond', 16), bd=1,width =11)
    r16.place(x=760, y=500)

    # the label for index_slrp
    Label(main_root, text="Idx Buffer",bg="#C0C0C0", font=('Garamond', 16)).place(x=296, y=640)
    # creating a entry for index_slrp
    y1 = tk.Entry(main_root,width=10, font=('Garamond', 16), bd=1)
    y1.insert(0, int(dict_runtime_inputs["IndexBuffer"]))
    y1.place(x=400, y=640)
    def modify_buffer():
        global IndexStopLoss_points
        global dict_runtime_inputs
        global traded_index_points
        global y1,r17,x5
        dict_runtime_inputs["IndexBuffer"] = int(y1.get())
        if (index_ltp >= traded_index_points + int(dict_runtime_inputs["IndexBuffer"])):

            IndexStopLoss_points = int(traded_index_points) + int(dict_runtime_inputs["IndexBuffer"])
            #print("IndexBuffer : ", dict_runtime_inputs["IndexBuffer"])
            dict_runtime_inputs["IndexStopLoss"] = IndexStopLoss_points - int(traded_index_points)
            #print("IndexStopLoss : ", dict_runtime_inputs["IndexStopLoss"])
            r17.delete(0,END)
            r17.insert(0,round(dict_runtime_inputs["IndexStopLoss"]))
            x5.delete(0,END)
            x5.insert(0, round(IndexStopLoss_points))

            # creating the raio buttons for auto flag
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold") )

            var.set(dict_runtime_inputs["IndexBuffer"])
            var.set("Trailing modified")
            label.place(x=50,y=640)
    # Create a Button for zero

    b1 = tk.Button(main_root, text='M',
                   command=lambda: modify_buffer(), bg="#1E90FF",width=4, height=1, font=("Garamond", 10))
    b1.place(x=495,y=640)

    Label(main_root, text="Trailing",fg="#1E90FF",font=('Garamond', 16)).place(x=296, y=670)

    # fun is called when radiobutton for hold flag is selected
    def viewSelected113():
        global dict_runtime_inputs
        global traded_index_points
        global x5,y1,r17
        global IndexStopLoss_points
        dict_runtime_inputs["IndexBuffer"] = var113.get()
        if (index_ltp >= traded_index_points + int(dict_runtime_inputs["IndexBuffer"])):

            IndexStopLoss_points = int(traded_index_points) + int(dict_runtime_inputs["IndexBuffer"])
            #print("IndexBuffer : ", dict_runtime_inputs["IndexBuffer"])
            dict_runtime_inputs["IndexStopLoss"] = IndexStopLoss_points - int(traded_index_points)
            #print("IndexStopLoss : ", dict_runtime_inputs["IndexStopLoss"])
            r17.delete(0,END)
            r17.insert(0,round(dict_runtime_inputs["IndexStopLoss"]))
            x5.delete(0,END)
            x5.insert(0, round(IndexStopLoss_points))
            y1.delete(0,END)
            y1.insert(0, int(dict_runtime_inputs["IndexBuffer"]))

            # creating the raio buttons for auto flag
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold") )

            var.set(dict_runtime_inputs["IndexBuffer"])
            var.set("IndexBuffer modified")
            label.place(x=50,y=640)

     # creating the raio buttons for auto flag
    var113 = StringVar()

    # setting the default value for the aut0_flag by using var
    var113.set(dict_runtime_inputs["IndexBuffer"])

    #print(dict_runtime_inputs["IndexBuffer"])
    
    # radio button for true
    X121 = Radiobutton(main_root, text="0",font=('Garamond', 15), variable=var113, value="0", command=viewSelected113)

    X121.place(x=400, y=670)
    # radio button for true
    X120 = Radiobutton(main_root, text="20",font=('Garamond', 15), variable=var113, value="20", command=viewSelected113)

    X120.place(x=435, y=670)

    # radio button for true
    X111 = Radiobutton(main_root, text="30",font=('Garamond', 15), variable=var113, value="30", command=viewSelected113)

    # placing the radio button
    X111.place(x=480, y=670)

    # radio button for true
    X122 = Radiobutton(main_root, text="40",font=('Garamond', 15), variable=var113, value="40", command=viewSelected113)

    # placing the radio button
    X122.place(x=525, y=670)

    # radio button for true
    X112 = Radiobutton(main_root, text="50",font=('Garamond', 15), variable=var113, value="50", command=viewSelected113)

    # placing the radio button
    X112.place(x=570, y=670)
    # radio button for true
    X123 = Radiobutton(main_root, text="60",font=('Garamond', 15), variable=var113, value="60", command=viewSelected113)

    # placing the radio button
    X123.place(x=615, y=670)
    # radio button for true
    # radio button for true
    X113 = Radiobutton(main_root, text="70",font=('Garamond', 15), variable=var113, value="70", command=viewSelected113)

    # placing the radio button
    X113.place(x=660, y=670)
    # radio button for true
    X114 = Radiobutton(main_root, text="80",font=('Garamond', 15), variable=var113, value="80", command=viewSelected113)

    # placing the radio button
    X114.place(x=380, y=700)
    # radio button for true
    X115 = Radiobutton(main_root, text="90",font=('Garamond', 15), variable=var113, value="90", command=viewSelected113)

    # placing the radio button
    X115.place(x=425, y=700)

    # radio button for true
    X116 = Radiobutton(main_root, text="100",font=('Garamond', 15), variable=var113, value="100", command=viewSelected113)

    # placing the radio button
    X116.place(x=470, y=700)

    # radio button for true
    X117 = Radiobutton(main_root, text="125",font=('Garamond', 15), variable=var113, value="125", command=viewSelected113)

    # placing the radio button
    X117.place(x=520, y=700)

    # radio button for true
    X118 = Radiobutton(main_root, text="150",font=('Garamond', 15), variable=var113, value="150", command=viewSelected113)

    X118.place(x=570, y=700)

    # radio button for true
    X119 = Radiobutton(main_root, text="175",font=('Garamond', 15), variable=var113, value="175", command=viewSelected113)

    X119.place(x=620, y=700)

    # radio button for true
    X130 = Radiobutton(main_root, text="200",font=('Garamond', 15), variable=var113, value="200", command=viewSelected113)

    X130.place(x=670, y=700)
    # the label for index_slrp
    Label(main_root, text="Opt Buffer",bg="#C0C0C0", font=('Garamond', 16)).place(x=20, y=680)
    # creating a entry for index_slrp
    y2 = tk.Entry(main_root,width=10, font=('Garamond', 16), bd=1)
    y2.insert(0, dict_runtime_inputs["OptBuffer"])
    y2.place(x=110, y=680)
    def modify_optbuffer():

        global dict_runtime_inputs
        global opt_stoploss_price
        global y2
        dict_runtime_inputs["OptBuffer"] = int(y2.get())
        if(opt_curr_price > opt_ce_entry_avg_price + int(dict_runtime_inputs["OptBuffer"])):
            dict_runtime_inputs["OptStopLoss"] = int(y2.get())
            opt_stoploss_price = opt_ce_entry_avg_price + ((opt_ce_entry_avg_price * int(dict_runtime_inputs["OptBuffer"]))/100)
            r3.delete(0,END)
            r3.insert(0,opt_stoploss_price)
            r4.delete(0,END)
            r4.insert(0,round(int(dict_runtime_inputs["OptStopLoss"])))
            r4.insert(5," %")
            var = StringVar()
            label = Message( main_root, textvariable=var, width=250, bg="WHITE" ,font=("Garamond", 14 ,"bold") )

            var.set(dict_runtime_inputs["OptBuffer"])
            var.set("OptBuffer modified")
            label.place(x=50,y=640)
    # Create a Button for zero

    b2 = tk.Button(main_root, text='M',
                   command=lambda: modify_optbuffer(), bg="#1E90FF",width=4, height=1, font=("Garamond", 10))
    b2.place(x=200,y=680)

    b3 = tk.Button(main_root, text='Reset',
                   command=lambda: reset(),bg="#1E90FF", width=15, height=2, font=("Arial", 15))
    # placing the button for mode flags
    b3.place(x=735, y=670)

    # creating button for mode flags
    b4 = tk.Button(main_root, text='NF CE Exit',
                   command=lambda: ce_exit(),bg="#FF0000", width=16, height=2, font=("Arial", 15))


    # placing the button for mode flags
    b4.place(x=1015, y=670)


    def update():
        global dict_runtime_inputs
        global dict_runtime_inputs_default
        global opt_ce_entry_avg_price
        global opt_curr_price
        global opt_target_price
        global opt_stoploss_price
        global profit
        global profit_perc
        global loss
        global loss_perc
        global traded_index_points
        global index_ltp
        global IndexStopLoss_points
        global IndexTarget_points
        global profit_points
        global loss_points
        global script_name
        global traded_scripts


        r2.delete(0, END)
        r2.insert(0, round((opt_curr_price),1))

        r3.delete(0, END)
        r3.insert(0, round(opt_stoploss_price,1))

        r4.delete(0, END)
        r4.insert(0, int(dict_runtime_inputs["OptStopLoss"]))
        r4.insert(5," %")

        r5.delete(0, END)
        r5.insert(0, round(opt_target_price,1))

        r6.delete(0, END)
        r6.insert(0, int(dict_runtime_inputs["OptTarget"]))
        r6.insert(5," %")

        r7.delete(0, END)
        r7.insert(0, round(profit))

        r8.delete(0, END)
        r8.insert(0, round(profit_perc))
        r8.insert(7," %")

        r9.delete(0, END)
        r9.insert(0, round(loss))

        r10.delete(0, END)
        r10.insert(0, round(loss_perc))
        r10.insert(7," %")

        r12.delete(0, END)
        r12.insert(0, round((index_ltp)))

        r13.delete(0, END)
        r13.insert(0, round(IndexStopLoss_points))

        r14.delete(0, END)
        r14.insert(0, round(IndexTarget_points))

        r15.delete(0, END)
        r15.insert(0, round(profit_points))

        r16.delete(0, END)
        r16.insert(0, round(loss_points))

        r17.delete(0, END)
        r17.insert(0, round(int(dict_runtime_inputs["IndexStopLoss"])))
        
        r18.delete(0, END)
        r18.insert(0, round(int(dict_runtime_inputs["IndexTarget"])))


        if len(traded_scripts) == 0:
            dict_runtime_inputs = dict_runtime_inputs_default.copy()
            Close()
        main_root.after(2000, update)
    update()

    # Call function to make the window stay on top
    main_root.attributes('-topmost', True)

    # the widget will keep on displaying in loop
    main_root.mainloop()


# placing option ce orders
def opt_ce_entry_place_mkt_order(symbl, place_order_qty):
    #logging.info("Im inside opt_ce_entry_place_mkt_order for:%s ", symbl)
    opt_ce_entry_order_id = 0
    try:
        opt_ce_entry_order_id = kite.place_order(tradingsymbol=symbl, variety=kite.VARIETY_REGULAR,
                                     exchange=kite.EXCHANGE_NFO,
                                     transaction_type=kite.TRANSACTION_TYPE_BUY,
                                     quantity=place_order_qty,
                                     order_type=kite.ORDER_TYPE_MARKET,
                                     product=kite.PRODUCT_MIS)

        #logging.info("option ce entry order placed. ID is:%s", opt_ce_entry_order_id)
        return opt_ce_entry_order_id
    except Exception as e:
        logging.info("exception occured:%s" + str(e))

# placing option ce_exit orders
def opt_ce_exit_place_mkt_order(symbl, place_order_qty):
    #logging.info("Im inside opt_ce_exit_place_mkt_order for:%s ", symbl)
    opt_ce_exit_order_id = 0
    try:
        opt_ce_exit_order_id = kite.place_order(tradingsymbol=symbl, variety=kite.VARIETY_REGULAR,
                                     exchange=kite.EXCHANGE_NFO,
                                     transaction_type=kite.TRANSACTION_TYPE_SELL,
                                     quantity=place_order_qty,
                                     order_type=kite.ORDER_TYPE_MARKET,
                                     product=kite.PRODUCT_MIS)

        #logging.info("option ce exit order placed. ID is:%s", opt_ce_exit_order_id)
        return opt_ce_exit_order_id
    except Exception as e:
        logging.info("exception occured:%s" + str(e))


# executing ce func
def opt_ce_entry():
    global opt_qty_to_ce_entry
    global opt_trade_symbol
    global opt_ce_entry_avg_price
    global opt_ce_entry_qty_sum
    global opt_ce_entry_amount
    global place_order_max_qty
    global opt_ce_entry_trade_symbol
    global traded_index_points
    global script_name
    global traded_scripts
    global dict_runtime_inputs
    global trading_symbol
    global band1_counter_status
    global band1_counter 

    #logging.info('In opt_ce_entry')
    opt_ce_entry_qty_sum = 0
    opt_ce_entry_price_sum = 0
    place_order_qty = opt_qty_to_ce_entry
    number_iteration = 0
    opt_ce_entry_order = {}
            
    if(dict_runtime_inputs["LiveTrade"] == 'True'):
         
        while (place_order_qty > place_order_max_qty):
            opt_ce_entry_order_id = opt_ce_entry_place_mkt_order(opt_trade_symbol, place_order_max_qty)
            time.sleep(3)
            received = kite.orders()
            for individual_order in received:
                if int(individual_order['order_id']) == int(opt_ce_entry_order_id):
                    if individual_order['status'] == 'COMPLETE':
                        opt_ce_entry_timestamp = individual_order['exchange_timestamp']
                        opt_ce_entry_trade_symbol = individual_order['tradingsymbol']
                        opt_ce_entry_order['order%s' %number_iteration] = {}
                        opt_ce_entry_order['order%s' %number_iteration]['order_id'] = individual_order['order_id']
                        opt_ce_entry_order['order%s' %number_iteration]['quantity'] = individual_order['quantity']
                        opt_ce_entry_order['order%s' %number_iteration]['price'] = individual_order['average_price']

                        place_order_qty = place_order_qty - place_order_max_qty
                        number_iteration = number_iteration + 1

        if (place_order_qty > 0):
            opt_ce_entry_order_id = opt_ce_entry_place_mkt_order(opt_trade_symbol, place_order_qty)
            time.sleep(3)
            received = kite.orders()
            for individual_order in received:
                if int(individual_order['order_id']) == int(opt_ce_entry_order_id):
                    if individual_order['status'] == 'COMPLETE':
                        opt_ce_entry_timestamp = individual_order['exchange_timestamp']
                        opt_ce_entry_trade_symbol = individual_order['tradingsymbol']
                        opt_ce_entry_order['order%s' %number_iteration] = {}
                        opt_ce_entry_order['order%s' %number_iteration]['order_id'] = individual_order['order_id']
                        opt_ce_entry_order['order%s' %number_iteration]['quantity'] = individual_order['quantity']
                        opt_ce_entry_order['order%s' %number_iteration]['price'] = individual_order['average_price']
                        number_iteration = number_iteration + 1
        #logging.info('opt_ce_entry_order : %s ' , opt_ce_entry_order)
        loop = 0

        while (loop < number_iteration):
            opt_ce_entry_qty_sum = opt_ce_entry_qty_sum + opt_ce_entry_order['order%s' %loop]['quantity']
            opt_ce_entry_price_sum = opt_ce_entry_price_sum + opt_ce_entry_order['order%s' %loop]['price']
            loop = loop + 1
        opt_ce_entry_avg_price = opt_ce_entry_price_sum / number_iteration

    else:
        opt_ce_entry_timestamp = datetime.now(timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S') 
        ohlc = kite.ohlc('NFO:{}'.format(opt_trade_symbol))
        opt_ce_entry_avg_price  = ohlc['NFO:{}'.format(opt_trade_symbol)]['last_price']
        opt_ce_entry_qty_sum = opt_qty_to_ce_entry
        opt_ce_entry_trade_symbol = opt_trade_symbol
        logging.info('Paper Trade')
        logging.info('opt_ce_entry_timestamp : %s',opt_ce_entry_timestamp)
        logging.info('opt_ce_entry_avg_price : %s',opt_ce_entry_avg_price)
        logging.info('opt_ce_entry_qty_sum : %s',opt_ce_entry_qty_sum)
        logging.info('opt_ce_entry_trade_symbol : %s',opt_ce_entry_trade_symbol)

    opt_ce_entry_amount =  round(opt_ce_entry_qty_sum * opt_ce_entry_avg_price)

    if (opt_ce_entry_qty_sum > 0):

        ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
        traded_index_points = ohlc['NSE:{}'.format(trading_symbol)]['last_price']
        #logging.info(' traded_index_points : %s',traded_index_points) 

    row = [opt_ce_entry_timestamp,  opt_ce_entry_trade_symbol, dict_runtime_inputs["LiveTrade"], 'CE_Entry',opt_ce_entry_qty_sum, round(opt_ce_entry_avg_price,2),   opt_ce_entry_amount, round(traded_index_points)]
    with open(dict_inputs["ReportFile"], 'a', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)
        f.close()

    #logging.info('\n')
    #logging.info('opt_ce_entry_qty :%s', opt_ce_entry_qty_sum)
    #logging.info('opt_ce_entry_avg_price :%s', round(opt_ce_entry_avg_price,2))
    #logging.info('\n')

    if (opt_ce_entry_qty_sum > 0):
        traded_scripts.append(script_name)
        logging.info('appended script_name')
        band1_counter_status = True
        band1_counter = 3
        set_single_trade_flag()
        logging.info('single trade flag is set')

    
# executin ce exit func
def opt_ce_exit():
    global opt_ce_entry_qty_sum
    global opt_ce_entry_amount
    global opt_trade_symbol
    global opt_ce_entry_trade_symbol
    global place_order_max_qty
    global script_name
    global traded_scripts
    global trading_symbol
    global thirdwindow_enable
    global secondwindow_enable
    global dict_runtime_inputs
    
    index_exit_points = 0

    #logging.info('In opt_ce_exit')

    opt_trade_symbol = opt_ce_entry_trade_symbol

    opt_ce_exit_qty = opt_ce_entry_qty_sum
    opt_ce_exit_avg_price = 0
    opt_ce_exit_amount = 0
    opt_ce_exit_qty_sum = 0
    opt_ce_exit_price_sum = 0
    number_iteration = 0
    opt_profit = 0
    opt_loss = 0
    opt_ce_exit_order = {}

    if(dict_runtime_inputs["LiveTrade"] == 'True'):
        while (opt_ce_exit_qty  > place_order_max_qty):
            opt_ce_exit_order_id = opt_ce_exit_place_mkt_order(opt_trade_symbol, place_order_max_qty)
            time.sleep(3)
            received = kite.orders()
            for individual_order in received:
                if int(individual_order['order_id']) == int(opt_ce_exit_order_id):
                    if individual_order['status'] == 'COMPLETE':
                        opt_ce_exit_timestamp = individual_order['exchange_timestamp']
                        opt_ce_exit_trade_symbol = individual_order['tradingsymbol']
                        opt_ce_exit_order['order%s' %number_iteration] = {}
                        opt_ce_exit_order['order%s' %number_iteration]['order_id'] = individual_order['order_id']
                        opt_ce_exit_order['order%s' %number_iteration]['quantity'] = individual_order['quantity']
                        opt_ce_exit_order['order%s' %number_iteration]['price'] = individual_order['average_price']

                        opt_ce_exit_qty = opt_ce_exit_qty - place_order_max_qty
                        number_iteration = number_iteration + 1

        if (opt_ce_exit_qty > 0):
            opt_ce_exit_order_id = opt_ce_exit_place_mkt_order(opt_trade_symbol, opt_ce_exit_qty)
            time.sleep(3)
            received = kite.orders()
            for individual_order in received:
                if int(individual_order['order_id']) == int(opt_ce_exit_order_id):
                    if individual_order['status'] == 'COMPLETE':
                        opt_ce_exit_timestamp = individual_order['exchange_timestamp']
                        opt_ce_exit_trade_symbol = individual_order['tradingsymbol']
                        opt_ce_exit_order['order%s' %number_iteration] = {}
                        opt_ce_exit_order['order%s' %number_iteration]['order_id'] = individual_order['order_id']
                        opt_ce_exit_order['order%s' %number_iteration]['quantity'] = individual_order['quantity']
                        opt_ce_exit_order['order%s' %number_iteration]['price'] = individual_order['average_price']
                        number_iteration = number_iteration + 1
                        opt_ce_exit_qty = 0

        #logging.info('opt_ce_exit_order : %s ' , opt_ce_exit_order)
        loop = 0
        while (loop < number_iteration):
            opt_ce_exit_qty_sum = opt_ce_exit_qty_sum + opt_ce_exit_order['order%s' %loop]['quantity']
            opt_ce_exit_price_sum = opt_ce_exit_price_sum + opt_ce_exit_order['order%s' %loop]['price']
            loop = loop + 1

        opt_ce_exit_avg_price = opt_ce_exit_price_sum / number_iteration

    else:

        opt_ce_exit_timestamp = datetime.now(timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')
        ohlc = kite.ohlc('NFO:{}'.format(opt_trade_symbol))
        opt_ce_exit_avg_price  = ohlc['NFO:{}'.format(opt_trade_symbol)]['last_price']
        opt_ce_exit_qty_sum = opt_ce_entry_qty_sum
        opt_ce_exit_trade_symbol = opt_trade_symbol
        opt_ce_exit_qty = 0


    opt_ce_exit_amount =  round(opt_ce_exit_qty_sum * opt_ce_exit_avg_price)
   
    ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
    index_exit_points = ohlc['NSE:{}'.format(trading_symbol)]['last_price']
    #logging.info('index_exit_points : %s',index_exit_points)
    index_profit_points = index_exit_points - traded_index_points

    if (opt_ce_exit_amount > opt_ce_entry_amount):
        opt_profit = round(opt_ce_exit_amount - opt_ce_entry_amount)
        if (opt_profit != 0):
            profit_percent = round((100 * opt_profit/opt_ce_entry_amount),1)
        else:
            profit_percent = 0
        #logging.info('\n')
        #logging.info('opt_ce_exit_qty :%s', opt_ce_exit_qty_sum)
        #logging.info('avg_ce_exit_price :%s', round(opt_ce_exit_avg_price,2))
        #logging.info('opt_profit  :%s', round(opt_profit))
        #logging.info('\n')

        row = [opt_ce_exit_timestamp,opt_ce_exit_trade_symbol, dict_runtime_inputs["LiveTrade"] , 'CE Exit', opt_ce_exit_qty_sum, round(opt_ce_exit_avg_price,2), opt_ce_exit_amount, round(index_exit_points), round(index_profit_points), opt_profit,profit_percent]
        with open(dict_inputs["ReportFile"], 'a', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
            f.close()
    else:
        opt_loss = round(opt_ce_exit_amount - opt_ce_entry_amount)
        if (opt_loss != 0):
            loss_percent = round((100 * opt_loss/opt_ce_entry_amount),1) 
        else:
            loss_percent = 0
        #logging.info('\n')
        #logging.info('opt_ce_exit_qty_sum :%s', opt_ce_exit_qty_sum)
        #logging.info('opt_ce_exit_avg_price :%s', round(opt_ce_exit_avg_price,2))
        #logging.info('opt_loss  :%s', round(opt_loss))
        #logging.info('\n')

        row = [opt_ce_exit_timestamp,opt_ce_exit_trade_symbol, dict_runtime_inputs["LiveTrade"], 'CE Exit', opt_ce_exit_qty_sum, round(opt_ce_exit_avg_price,2),     opt_ce_exit_amount, round(index_exit_points), round(index_profit_points), opt_loss, loss_percent]
        with open(dict_inputs["ReportFile"], 'a', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
            f.close()
    
    # Removing the script name
    if (opt_ce_exit_qty == 0):
        traded_scripts.remove(script_name)
        logging.info('Removed script_name')
        reset_single_trade_flag()
        thirdwindow_enable = False
        secondwindow_enable = True

# executing init_ce_entry func
def init_ce_entry():
    global trading_symbol
    global opt_qty_to_ce_entry
    global script_name
    global traded_scripts
    global traded_index_points
    global place_order_in_process
    global place_order_max_qty
    global lot_size
    global IndexMode
    global IndexTarget
    global IndexStopLoss
    global IndexTrailing
    global IndexSLInc
    global IndexSLReset
    global IndexSLRP
    global OptMode
    global OptTarget
    global OptStopLoss
    global OptTrailing
    global OptSLInc
    global OptSLReset
    global OptSLRP
    global stock_in_position

    place_order_in_process = 1
    stock_in_position = 0

    # Get current price
    ohlc = kite.ohlc('NFO:{}'.format(opt_trade_symbol))
    ltp_option = ohlc['NFO:{}'.format(opt_trade_symbol)]['last_price']
    curr_price = ltp_option

    # Calculating Quantity for ce
    if dict_runtime_inputs["CapitalBased"] == 'True':
        Capital_lots = round(int(dict_runtime_inputs["Capital"]) / (curr_price * lot_size))
        opt_qty_to_ce_entry = Capital_lots * lot_size
    else:
        opt_qty_to_ce_entry = int(dict_runtime_inputs["OptQuantityLots"]) * lot_size

    #logging.info('opt_qty_to_ce_entry:%s', opt_qty_to_ce_entry)

    place_order_max_qty = place_order_max_lots * lot_size

    # Calling ce func
    if script_name not in traded_scripts:
        lock.acquire()
        logging.info('acquired lock in entry')
        opt_ce_entry()
        lock.release()
        logging.info('released lock in entry')
        logging.info("In ce script name %s",traded_scripts)
        stock_in_position = 1

    place_order_in_process = 0

# executing init_ce_exit func
def init_ce_exit():
    global place_order_in_process
    global stock_in_position

    if (stock_in_position == 1):
        stock_in_position = 0
        place_order_in_process = 1
        # Acquiring lock to ce_exit the script
        lock.acquire()
        logging.info('acquired lock in exit')
        opt_ce_exit()
        lock.release()
        logging.info('released lock in exit')
    
        place_order_in_process = 0

# executing getStickPrice thread
def getStrickPrice():
    global script_name
    global traded_scripts
    global place_order_in_process
    global opt_ce_entry_qty_sum
    global opt_ce_entry_avg_price
    global opt_trade_symbol
    global opt_prev_price
    global opt_target_price
    global opt_stoploss_price
    global opt_prev_price
    global opt_ltp
    global trading_symbol
    global IndexStopLoss_points
    global IndexTarget_points
    global traded_index_points
    global ltp
    global dict_runtime_inputs
    global dict_inputs
    global opt_ce_entry_avg_price
    global opt_curr_price
    global opt_stoploss_price
    global opt_stoploss_perc
    global opt_target_price
    global opt_target_perc
    global opt_curr_price
    global profit
    global profit_perc
    global loss
    global loss_perc
    global traded_index_points
    global index_ltp
    global IndexStopLoss_points
    global IndexTarget_points
    global profit_points
    global loss_points
    global thirdwindow_enable 
    global secondwindow_enable
    global dict_runtime_inputs
    global opt_premium
    global idle_state
    global band1_counter_status
    global band1_counter
    global band2_counter_status
    global band2_counter


    opt_profit = 0
    profit_perc = 0
    profit_points = 0
    loss_points = 0
    loss_perc = 0
    opt_prev_price = 0
    index_prev_points = 0 
    opt_stoploss_price = 0
    IndexStopLoss_points = 0
    opt_target_price = 0
    IndexTarget_points = 0
    profit = 0
    loss = 0
    thirdwindow_enable = False
    secondwindow_enable = False
    logging.info('getStrickPrice() called')

    while True:
        opt_trade_symbol = ''

        band1_counter_status = False
        band1_counter = 0
        band2_counter_status = False
        band2_counter = 0

        if place_order_in_process == 0:

            logging.info("script name %s",traded_scripts)

            while len(traded_scripts) == 0:

                if(idle_state == 1):
                    logging.info('In getStickPrice, idle_state 1 :%s',idle_state)
                    # Timer
                    timer = threading.Timer(int(dict_runtime_inputs["TradeTf"]) * 60, getStrickPrice)
                    timer.start()
                    break
                time.sleep(5)

                trading_symbol = 'NIFTY 50'
                ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
                ltp = ohlc['NSE:{}'.format(trading_symbol)]['last_price']
                #logging.info('index ltp :%s', ltp)
                #option sell strike price calculation
                val = ltp + int(dict_runtime_inputs["OptBuyDepth"])
                val2 = math.fmod(val, 50)
                #logging.info('OptBuyDepth %s',(dict_runtime_inputs["OptBuyDepth"]))
                #logging.info('val : %s',val)
                #logging.info('val2 : %s',val2)
                x = val - val2
                opt_price2 = "{}".format("{:.0f}".format(x + 50))
                opt_current_trade_symbol = dict_inputs["OptExpiry"] + opt_price2 + "CE"
                if opt_trade_symbol != opt_current_trade_symbol:
                    opt_trade_symbol = opt_current_trade_symbol
                #logging.info('opt_trade_symbol : %s',opt_trade_symbol)

                opt_ohlc = kite.ohlc('NFO:{}'.format(opt_trade_symbol))
                opt_premium = opt_ohlc['NFO:{}'.format(opt_trade_symbol)]['last_price']
                #opt_premium = kite.ltp('NFO:BANKNIFTY2332339100CE')
                #logging.info('opt premium :%s', opt_premium)
                
                thirdwindow_enable = False
                secondwindow_enable = True
                
            if(idle_state == 1):
                logging.info('In getStickPrice, idle_state 2 :%s',idle_state)
                break
            #nifty in Position
            opt_prev_price = opt_ce_entry_avg_price
            opt_stoploss_price = opt_ce_entry_avg_price * (100 + float(dict_runtime_inputs["OptStopLoss"])) / 100
            opt_target_price = opt_ce_entry_avg_price * (100 + float(dict_runtime_inputs["OptTarget"])) / 100
            index_prev_points = traded_index_points
            IndexStopLoss_points = traded_index_points + float(dict_runtime_inputs["IndexStopLoss"])
            IndexTarget_points = traded_index_points + float(dict_runtime_inputs["IndexTarget"])
            
            while (script_name in traded_scripts):
                logging.info('in getStrikeprice second block')
                ohlc = kite.ohlc('NFO:{}'.format(opt_ce_entry_trade_symbol))
                opt_ltp = ohlc['NFO:{}'.format(opt_ce_entry_trade_symbol)]['last_price']
                opt_curr_price = opt_ltp
                opt_ce_entry_amount = opt_ce_entry_avg_price * opt_ce_entry_qty_sum
                logging.info('opt_ce_entry_avg_price : %s \n',round(opt_ce_entry_avg_price,2))
                opt_curr_amount = opt_curr_price * opt_ce_entry_qty_sum
                logging.info('opt_current_amount : %s \t\t opt_ce_entry_amount : %s\n\n',round(opt_curr_amount,2),round(opt_ce_entry_amount,2))
                 
                index_ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
                index_ltp = index_ohlc['NSE:{}'.format(trading_symbol)]['last_price']
                logging.info('index_ltp : %s', index_ltp)

 
                if (dict_runtime_inputs["OptMode"] == 'True'):

                    logging.info('I am inside OptMode')

                    if (opt_ltp <= opt_stoploss_price):
                        logging.info('opt_stoploss_price : %s is hit',round(opt_stoploss_price,2))
                        init_ce_exit()
                        break

                    if(dict_runtime_inputs['Opt_target_set'] == 'True'):
                        if (opt_ltp >= opt_target_price):
                            logging.info('opt_target_price : %s is hit',round(opt_target_price,2))
                            init_ce_exit()
                            break

                    if (dict_runtime_inputs["OptTrailing"] == "True"):
                        logging.info('In OptTrailing')
                        profit_perc = 0
                        if (opt_curr_price > opt_prev_price):
                            logging.info('RRB: opt_prev_price: %s opt_curr_price :%s',opt_prev_price,opt_curr_price)
                            profit_perc = (((opt_curr_price - opt_prev_price) * 100)/opt_prev_price)
                            logging.info('profit_perc:%s', round(profit_perc,2))

                            if (profit_perc > float(dict_runtime_inputs["OptSLInc"])):
                                logging.info('RRB: profit_perc : %s higher than OptSLInc :%s',profit_perc,dict_runtime_inputs["OptSLInc"])
                                opt_stoploss_price = opt_stoploss_price + ((profit_perc/100) * opt_ce_entry_avg_price)
                                dict_runtime_inputs["OptStopLoss"] = ((opt_stoploss_price - opt_ce_entry_avg_price)/opt_ce_entry_avg_price)*100
                                opt_prev_price = opt_curr_price
                                #dict_runtime_inputs["OptTrailing"] = "False"

                    if (dict_runtime_inputs["OptSLReset"] == "True"):
                        logging.info('OptSLReset True')
                        profit_perc = 0
                        if opt_curr_price > opt_ce_entry_avg_price:
                            profit_perc = (((opt_curr_price - opt_ce_entry_avg_price) * 100)/opt_ce_entry_avg_price)
                            if (profit_perc > float(dict_runtime_inputs["OptSLRP"])):
                                logging.info('profit_perc :%s, greater than OptSLRP : %s',profit_perc,dict_runtime_inputs["OptSLRP"])
                                opt_stoploss_price = opt_ce_entry_avg_price
                                dict_runtime_inputs["OptStopLoss"] = ((opt_stoploss_price - opt_ce_entry_avg_price)/opt_ce_entry_avg_price)*100
                                dict_runtime_inputs["OptTrailing"] = "True"
                                dict_runtime_inputs["OptSLReset"] = "False"
                                opt_prev_price = opt_ce_entry_avg_price +  ((float(dict_runtime_inputs["OptSLRP"]) * opt_ce_entry_avg_price) / 100)



                if (dict_runtime_inputs["IndexMode"] == 'True'):
                    
                    logging.info('I am inside IndexMode')


                    if index_ltp <= IndexStopLoss_points:
                        logging.info('IndexStopLoss_points : %s is hit',round(IndexStopLoss_points,2))
                        init_ce_exit()
                        break
                    if(dict_runtime_inputs['Index_target_set'] == 'True'):
                        if (index_ltp >= IndexTarget_points):
                            logging.info('IndexTarget_points : %s is hit',round(IndexTarget_points,2))
                            init_ce_exit()
                            break

                    if (dict_runtime_inputs["IndexTrailing"] == "True"):
                        logging.info('RRB: IndexTrailing True')
                        logging.info('RRB: index_prev_points : %s index_ltp: %s',index_prev_points,index_ltp)
                        index_profit_points = 0
                        if (index_ltp > index_prev_points):
                            index_profit_points = (index_ltp - index_prev_points)
                            logging.info('RRB: index_profit_points:%s', round(index_profit_points,2))
                            logging.info('RRB: IndexSLInc :%s', float(dict_runtime_inputs["IndexSLInc"]))

                            if (index_profit_points > float(dict_runtime_inputs["IndexSLInc"])):
                                IndexStopLoss_points = IndexStopLoss_points + (1.5 * (index_profit_points))
                                dict_runtime_inputs["IndexStopLoss"] = dict_runtime_inputs["IndexStopLoss"] + round(float((1.5 * (index_profit_points),1))) 
                                logging.info('RRB:IndexStopLoss_points:%s', IndexStopLoss_points)
                                index_prev_points = index_ltp
                                logging.info('RRB: index_prev_points:%s', round(index_prev_points,2))


                    if (dict_runtime_inputs["IndexSLReset"] == "True"):
                        logging.info('RRB: IndexSLReset True')
                        index_profit_points = 0

                        if (index_ltp > traded_index_points):
                            logging.info('RRB: index_ltp high than traded_index_points')
                            index_profit_points = index_ltp - traded_index_points
                            if (index_profit_points > float(dict_runtime_inputs["IndexSLRP"])):
                                band1_counter_status = False
                                band2_counter_status = True
                                band2_counter = 3
                                logging.info('band2_counter set in Index SLRP')
                                dict_runtime_inputs["IndexStopLoss"] = 0 
                                IndexStopLoss_points = traded_index_points
                                index_prev_points = traded_index_points + float(dict_runtime_inputs["IndexSLRP"])
                                dict_runtime_inputs["IndexTrailing"] = "True"
                                dict_runtime_inputs["IndexSLReset"] = "False"


                    if (index_ltp > traded_index_points):
                        profit_points = index_ltp - traded_index_points
                        loss_points = 0
                        logging.info('traded_index_points : %s \t\t\tindex_ltp : %s',round(traded_index_points,2),round(index_ltp,2))
                        logging.info('IndexStopLoss_points : %s \t\tIndexTarget_points : %s ',round(IndexStopLoss_points,2),round(IndexTarget_points,2))
                        logging.info('profit_points : %s\n\n', round(profit_points,2))
                    else:
                        loss_points = index_ltp - traded_index_points 
                        profit_points = 0
                        logging.info('traded_index_points : %s \t\t\tindex_ltp : %s',round(traded_index_points,2),round(index_ltp,2))
                        logging.info('IndexStopLoss_points : %s \t\tIndexTarget_points : %s',round(IndexStopLoss_points,2),round(IndexTarget_points,2))
                        logging.info('loss_points : %s\n\n', round(loss_points,2))


                if opt_curr_amount >= opt_ce_entry_amount:
                    profit = opt_curr_amount - opt_ce_entry_amount
                    profit_perc = ((profit * 100) / opt_ce_entry_amount)
                    loss = 0
                    loss_perc = 0
                    logging.info('buy_price : %s \t\t current_price : %s \t\t stoploss_price : %s \t\t profit : %s',round(opt_ce_entry_avg_price,2),round(opt_curr_price,2),round(opt_stoploss_price,2),round(profit,2))
                    logging.info('stoploss_perc : %s%% \t\t profit_perc : %s%%',round(int(dict_runtime_inputs["OptStopLoss"]),2),round(profit_perc,2))
                    logging.info('target : %s \t\t target_perc : %s%%\n\n',round(opt_target_price,2),round(int(dict_runtime_inputs["OptTarget"]),2))
                else:
                    loss = opt_curr_amount - opt_ce_entry_amount
                    loss_perc = ((loss * 100) / opt_ce_entry_amount)
                    profit = 0
                    profit_perc = 0
                    logging.info('buy_price : %s \t\t current_price : %s \t\t stoploss_price : %s \t\t loss : %s',round(opt_ce_entry_avg_price,2),round(opt_curr_price,2),round(opt_stoploss_price,2),round(loss,2))
                    logging.info('stoploss_perc : %s%% \t\t loss_perc : %s%%',round(int(dict_runtime_inputs["OptStopLoss"]),2),round(loss_perc,2))
                    logging.info('target : %s \t\t target_perc : %s%%\n\n',round(opt_target_price,2),round(int(dict_runtime_inputs["OptTarget"]),2))

                logging.info('secondwindow_enable = False from getStrikePrice')
                secondwindow_enable = False
                logging.info('thirdwindow_enable = True from getStrikePrice')
                thirdwindow_enable = True
                time.sleep(5)

def trade_popup_entry():
    global dict_runtime_inputs
    global user_entry_input
    user_entry_input = False

    # create a tkinter root window
    root = Tk()

    # root window title and dimension
    root.title("NF CE Trade Alert")
    root['bg'] = 'WHITE'
    root.geometry('360x160+20+530')


    # Function for closing window
    def Close():
        root.destroy()
        #gc.collect()

    def onClick1():
        global user_entry_input
        global dict_runtime_inputs
        user_entry_input = True
        dict_runtime_inputs["LiveTrade"] = 'True'
        print('user_entry_input from onClinck1:',user_entry_input)
        Close()

    def onClick2():
        global user_entry_input
        user_entry_input = False
        print('user_entry_input from onClinck2:',user_entry_input)
        Close()
    def onClick3():
        global user_entry_input
        global dict_runtime_inputs
        user_entry_input = True
        dict_runtime_inputs["LiveTrade"] = 'False'
        print('user_entry_input from onClinck1:',user_entry_input)
        Close()

    # Create a Button
    button1 = Button(root, fg='BLACK', text="Live", command=onClick1, height=6, width=10,bg="#3CB371", font=("Arial", 15))
    button2 = Button(root,bg="#FD6B6B", font=("Arial", 15) ,fg='BLACK', text="No", command=onClick2, height=6, width=10)
    button3 = Button(root, bg="Yellow", font=("Arial", 15) ,fg='BLACK', text="Paper ", command=onClick3, height=6, width=10)

    # Set the position of button on the top of window.
    button1.place(x=10, y=50)
    button2.place(x=130, y=50)
    button3.place(x=250, y=50)
    if(dict_runtime_inputs["CapitalBased"] == "True"):
        #the label for Capital
        Label(root,text="Capital",bg="WHITE",font=('Garamond', 16)).place(x=110, y=10)
        # creating a entry for Capital
        r1 = tk.Entry(root, font=('Garamond', 16), bd=1,width=8)
        r1.insert(0, dict_runtime_inputs["Capital"])
        r1.place(x=177, y=10)
    else:
        #the label for Capital
        Label(root,text="Lots",bg="WHITE",font=('Garamond', 16)).place(x=110, y=10)
        # creating a entry for Capital
        r2 = tk.Entry(root, font=('Garamond', 16), bd=1,width=6)
        r2.insert(0, dict_runtime_inputs["OptQuantityLots"])
        r2.place(x=170, y=10)

    #Automatically close the window after 3 minutes
    root.after(180000,lambda:root.destroy())

    # Call function to make the window stay on top
    root.attributes('-topmost',True)

    root.mainloop()

def trade_popup_exit():
    global dict_runtime_inputs
    global user_exit_input
    user_exit_input = False

    # create a tkinter root window
    root = Tk()

    # root window title and dimension
    root.title("NF CE Exit Alert")
    root['bg'] = 'WHITE'
    root.geometry('340x140+800+150')


    # Function for closing window
    def Close():
        root.destroy()
        #gc.collect()

    def onClick1():
        global user_exit_input
        user_exit_input = True
        print('user_exit_input from onClinck1:',user_exit_input)
        Close()

    def onClick2():
        global user_exit_input
        user_exit_input = False
        print('user_exit_input from onClinck2:',user_exit_input)
        Close()

    # Create a Button
    button1 = Button(root,bg="#3CB371", font=("Arial", 15), fg='BLACK', text="Yes ", command=onClick1, height=6, width=10)
    button2 = Button(root, bg="#FD6B6B", font=("Arial", 15), text="No ", command=onClick2, height=6, width=10)

    # Set the position of button on the top of window.
    button1.place(x=30,y=30)
    button2.place(x=200, y=30)
    
    #Automatically close the window after 3 minutes
    root.after(180000,lambda:root.destroy())

    # Call function to make the window stay on top
    root.attributes('-topmost',True)

    root.mainloop()

# checking current candle time
def check_current_candle_time():
    global index_data
    global candle_time_flag

    indexCurRow = -2
    candle_time_flag = False

    #checking prev candle time and curr time
    index_data_str = index_data.astype(str)
    indexLastCandle = index_data_str.iloc[indexCurRow]
    index_curr_candle_time = indexLastCandle['date']
    logging.info('current candle time:%s', index_curr_candle_time)

    candle_split = index_curr_candle_time.split()
    candle_date = candle_split[0]
    candle_time = candle_split[1]

    # current date
    curr_date_time = datetime.now(timezone('Asia/Kolkata'))
    curr_date = curr_date_time.strftime("%Y-%m-%d")
    # logging.info("curr_date: %s", curr_date)


    if (curr_date == candle_date):
        logging.info('curr_date : %s and candle_date : %s are same',curr_date,candle_date)
        # candle time
        candle_time_split = candle_time.split(':')
        candle_hour = candle_time_split[0]
        candle_minute = candle_time_split[1]
        #logging.info('candle_hour =%s', candle_hour)
        #logging.info('candle_minute =%s', candle_minute)
        candle_total_minutes = (int(candle_hour) * 60) + int(candle_minute)
        #logging.info('candle_total_minutes = %s',candle_total_minutes)

        # current time
        curr_time_hour = datetime.now(timezone('Asia/Kolkata')).strftime('%H')
        #logging.info('current_time_hour:%s', curr_time_hour)
        curr_time_min = datetime.now(timezone('Asia/Kolkata')).strftime('%M')
        #logging.info('current_time_min:%s', curr_time_min)

        curr_total_time_min = (int(curr_time_hour) * 60) + int(curr_time_min)
        curr_total_time_seconds = curr_total_time_min * 60
        candle_total_seconds = candle_total_minutes * 60
        time_diff = curr_total_time_seconds - candle_total_seconds

        aloowed_time = (int(dict_runtime_inputs['TradeTf']) * 60 )  + (int(dict_runtime_inputs['TradeTf']) * 40)
        logging.info('curr_total_time_sec: %s candle_total_sec %s',curr_total_time_seconds,candle_total_seconds)
        if (time_diff < (int(dict_runtime_inputs['TradeTf']) * 60 )  + (int(dict_runtime_inputs['TradeTf']) * 40)):
            logging.info('time_diff:%s lower than allowed_time:%s',time_diff, aloowed_time)
            candle_time_flag = True
        else:
            logging.info('time_diff:%s higher than allowed_time:%s',time_diff, aloowed_time)
            candle_time_flag = False
    else:
        logging.info('curr_date : %s and candle_date : %s are not same',curr_date,candle_date)
        candle_time_flag = False
# checking current candle time
def check_opt_current_candle_time():
    global opt_data
    global opt_candle_time_flag

    optCurRow = -2
    optcandle_time_flag = False

    #checking prev candle time and curr time
    opt_data_str = opt_data.astype(str)
    optLastCandle = opt_data_str.iloc[optCurRow]
    opt_curr_candle_time = optLastCandle['date']
    logging.info('opt current candle time:%s', opt_curr_candle_time)

    candle_split = opt_curr_candle_time.split()
    candle_date = candle_split[0]
    candle_time = candle_split[1]

    # current date
    curr_date_time = datetime.now(timezone('Asia/Kolkata'))
    curr_date = curr_date_time.strftime("%Y-%m-%d")
    # logging.info("curr_date: %s", curr_date)


    if (curr_date == candle_date):
        logging.info('opt_curr_date : %s and opt_candle_date : %s are same',curr_date,candle_date)
        # candle time
        candle_time_split = candle_time.split(':')
        candle_hour = candle_time_split[0]
        candle_minute = candle_time_split[1]
        #logging.info('candle_hour =%s', candle_hour)
        #logging.info('candle_minute =%s', candle_minute)
        candle_total_minutes = (int(candle_hour) * 60) + int(candle_minute)
        #logging.info('candle_total_minutes = %s',candle_total_minutes)

        # current time
        curr_time_hour = datetime.now(timezone('Asia/Kolkata')).strftime('%H')
        #logging.info('current_time_hour:%s', curr_time_hour)
        curr_time_min = datetime.now(timezone('Asia/Kolkata')).strftime('%M')
        #logging.info('current_time_min:%s', curr_time_min)

        curr_total_time_min = (int(curr_time_hour) * 60) + int(curr_time_min)
        curr_total_time_seconds = curr_total_time_min * 60
        candle_total_seconds = candle_total_minutes * 60
        time_diff = curr_total_time_seconds - candle_total_seconds

        aloowed_time = (int(dict_runtime_inputs['TradeTf']) * 60 )  + (int(dict_runtime_inputs['TradeTf']) * 40)
        logging.info('opt_curr_total_time_sec: %s opt_candle_total_sec %s',curr_total_time_seconds,candle_total_seconds)
        if (time_diff < (int(dict_runtime_inputs['TradeTf']) * 60 )  + (int(dict_runtime_inputs['TradeTf']) * 40)):
            logging.info('opt_time_diff:%s lower than allowed_time:%s',time_diff, aloowed_time)
            opt_candle_time_flag = True
        else:
            logging.info('opt_time_diff:%s higher than allowed_time:%s',time_diff, aloowed_time)
            opt_candle_time_flag = False
    else:
        logging.info('opt_curr_date : %s and opt_candle_date : %s are not same',curr_date,candle_date)
        opt_candle_time_flag = False


# checking current candle time
def check_FiveMinTf_current_candle_time():

    global FiveMinTf_data
    global FiveMinTf_candle_time_flag 

    FiveMinTfCurRow = -2
    FiveMinTf_candle_time_flag = False

    #checking prev candle time and curr time
    FiveMinTf_data_str = FiveMinTf_data.astype(str)
    FiveMinTfLastCandle = FiveMinTf_data_str.iloc[FiveMinTfCurRow]
    FiveMinTf_curr_candle_time = FiveMinTfLastCandle['date']
    logging.info('FiveMinTf candle time:%s', FiveMinTf_curr_candle_time)

    FiveMinTf_candle_split =  FiveMinTf_curr_candle_time.split()
    FiveMinTf_candle_date = FiveMinTf_candle_split[0]
    FiveMinTf_candle_time = FiveMinTf_candle_split[1]

    # current date
    curr_date_time = datetime.now(timezone('Asia/Kolkata'))
    curr_date = curr_date_time.strftime("%Y-%m-%d")
    # logging.info("curr_date: %s", curr_date)

    if (curr_date ==  FiveMinTf_candle_date):
        logging.info('curr_date : %s and FiveMinTf_candle_date : %s are same',curr_date,FiveMinTf_candle_date)
        # candle time
        FiveMinTf_candle_time_split = FiveMinTf_candle_time.split(':')
        FiveMinTf_candle_hour = FiveMinTf_candle_time_split[0]
        FiveMinTf_candle_minute = FiveMinTf_candle_time_split[1]
        #logging.info('candle_hour =%s', candle_hour)
        #logging.info('candle_minute =%s', candle_minute)
        FiveMinTf_candle_total_minutes = (int(FiveMinTf_candle_hour) * 60) + int(FiveMinTf_candle_minute)
        #logging.info('candle_total_minutes = %s',candle_total_minutes)

        # current time
        curr_time_hour = datetime.now(timezone('Asia/Kolkata')).strftime('%H')
        #logging.info('current_time_hour:%s', curr_time_hour)
        curr_time_min = datetime.now(timezone('Asia/Kolkata')).strftime('%M')
        #logging.info('current_time_min:%s', curr_time_min)

        curr_total_time_min = (int(curr_time_hour) * 60) + int(curr_time_min)
        curr_total_time_seconds = curr_total_time_min * 60
        FiveMinTf_candle_total_seconds = FiveMinTf_candle_total_minutes * 60
        time_diff = curr_total_time_seconds - FiveMinTf_candle_total_seconds

        aloowed_time = int(500)
        logging.info('curr_total_time_sec: %s FiveMinTf_candle_total_sec %s',curr_total_time_seconds,FiveMinTf_candle_total_seconds)
        if (time_diff < (int(500))):
            logging.info('time_diff:%s lower than allowed_time:%s',time_diff, aloowed_time)
            FiveMinTf_candle_time_flag = True
        else:
            logging.info('time_diff:%s higher than allowed_time:%s',time_diff, aloowed_time)
            FiveMinTf_candle_time_flag = False
    else:
        logging.info('curr_date : %s and FiveMinTf_candle_date : %s are not same',curr_date,FiveMinTf_candle_date)
        FiveMinTf_candle_time_flag = False


def FiveMinTf20Ema():
    
    global FiveMinTf_data
    global FiveMinTf_candle_time_flag
    global FiveMinTfLastCandle
    global idle_state
    global single_trade_flag

    #laha
    FiveMinTf_candle_time_flag = False
    trade_interval = '5minute'

    # Timer
    time.sleep(30)
    timer = threading.Timer(int(300), FiveMinTf20Ema)
    timer.start()
    
    if(idle_state == 1) or (single_trade_flag == '3'):
        logging.info('In FiveMinTf20Ema, idle_state :%s',idle_state)
        return 0

    while True:
        FiveMinTf_data = zrd_login.get_data(name='NIFTY 50', segment='NSE:', delta=int(dict_runtime_inputs["TaDelta"]), interval=trade_interval, continuous=True,oi=False)
        #laha
        check_FiveMinTf_current_candle_time()
        if(FiveMinTf_candle_time_flag == True):
            break
        time.sleep(30)

    FiveMinTfCurRow = 1
    FiveMinTfDataLen = len(FiveMinTf_data)

    while FiveMinTfCurRow <= FiveMinTfDataLen:

        FiveMinTf_data['EMA20'] = talib.EMA(FiveMinTf_data['close'], timeperiod=20)

        FiveMinTfCurRow = FiveMinTfCurRow + 1

    logging.info(FiveMinTf_data)
    #print(FiveMinTf_data)

    FiveMinTfCurRow = -2
    FiveMinTfLastCandle = FiveMinTf_data.iloc[FiveMinTfCurRow]

def hist_data():
    global dict_inputs
    global dict_runtime_inputs
    global index_data
    global candle_time_flag
    global opt_candle_time_flag
    global ce_entry_signal
    global ce_exit_signal
    global firsttime
    global bc,tc
    global pdl,pdh
    global large_tf_supres_flag
    global day_hilow_flag,day_pivot_flag,large_tf_supres_flag,pdhl_flag,cpr_flag
    global fivemin_r1,fivemin_r2,fivemin_r3,fivemin_s1,fivemin_s2,fivemin_s3,fivemin_pivot_flag,pivot
    global opt_trade_symbol
    global opt_data
    global FiveMinTfLastCandle
    global search_index_close
    global day_high,day_low
    global single_trade_flag
    global band1_counter_status
    global band1_counter
    global band2_counter_status
    global band2_counter
    global IndexStopLoss_points
    global IndexTarget_points
    global traded_index_points
    global trading_symbol
    global ta_delta_flag
    global get_index_flag

    logging.info('In hist_data')

    search_index_close = 0
    indexPrevRow = 0
    indexCurRow = 0
    indexDataLen = 0

    optPrevRow = 0
    optCurRow = 0
    optDataLen = 0
    loop_count = 3

    ce_entry_signal = False
    ce_exit_signal = False
    #laha
    candle_time_flag = False
    opt_candle_time_flag = False
    up_res_flag = False
    up_sup_flag = False
    day_pivot_flag = False
    large_tf_supres_flag = False
    day_hilow_flag = False
    pdhl_flag = False
    cpr_flag = False
    fivemin_pivot_flag = False
    FiveMinTf_SupRes_flag = False
    get_index_flag = False
    logging.info('get_index_flag is set to False')

    currTime = datetime.now(timezone('Asia/Kolkata')).strftime('%H%M')
    logging.info('currTime : %s',currTime)

    if(int(currTime) > 1200 and (ta_delta_flag == True)):
        dict_runtime_inputs["TaDelta"] = 0
        logging.info('Setting TaDelta to Zero')
        ta_delta_flag = False


    if( int(dict_runtime_inputs["TradeTf"]) == 1):
        trade_interval = 'minute'
        #print('trade_interval',trade_interval)
    else:
        trade_interval = dict_runtime_inputs["TradeTf"]+'minute'
        #print('trade_interval',trade_interval)
    while True:
        index_data = zrd_login.get_data(name='NIFTY 50', segment='NSE:', delta=int(dict_runtime_inputs["TaDelta"]), interval=trade_interval , continuous=True,oi=False)
        #laha
        check_current_candle_time()
        if(candle_time_flag == True):
            break
        time.sleep(10)

    indexCurRow = 1
    indexDataLen = len(index_data)

    p1 = StochasticMomentumIndex(index_data, period=14, smoothing_period=3, double_smoothing_period=3,
                                 fill_missing_values=True)
    index_data['SMI'] = p1._calculateTi()
    index_data['SMID'] = talib.EMA(index_data['SMI'], timeperiod=10)

    while indexCurRow <= indexDataLen:

        index_data['EMA8'] = talib.EMA(index_data['close'], timeperiod=8)

        index_data['EMA20'] = talib.EMA(index_data['close'], timeperiod=20)

        if script_name not in traded_scripts:
            index_data['CHOP'] = ta.chop(index_data['high'], index_data['low'], index_data['close'], length=14)

        indexCurRow = indexCurRow + 1
        indexPrevRow = indexPrevRow + 1

    logging.info(index_data)
    print(index_data)

    indexCurRow = -2
    indexPrevRow = -3
    indexLastCandle = index_data.iloc[indexCurRow]
    indexPreviousCandle = index_data.iloc[indexPrevRow]

    #script name not in traded scripts
    if script_name not in traded_scripts:
        logging.info('script_name not in traded_scripts')

        while True:
            opt_data = zrd_login.get_data(name=opt_trade_symbol, segment='NFO:', delta=int(dict_runtime_inputs["TaDelta"]), interval=trade_interval , continuous=True,oi=False)
            #laha
            check_opt_current_candle_time()
            if(opt_candle_time_flag == True):
                break
            time.sleep(10)

        optCurRow = 1
        optDataLen = len(opt_data)

        while optCurRow <= optDataLen:

            opt_data_kvo = ta.kvo(opt_data['high'],opt_data['low'],opt_data['close'],opt_data['volume'])

            optCurRow = optCurRow + 1
            optPrevRow = optPrevRow + 1

        opt_data['KVO'] = opt_data_kvo['KVO_34_55_13']
        opt_data['KS'] = opt_data_kvo['KVOs_34_55_13']
        logging.info(opt_data)
        #print(opt_data)

        optCurRow = -2
        optPrevRow = -3
        optLastCandle = opt_data.iloc[optCurRow]
        optPreviousCandle = opt_data.iloc[optPrevRow]

        search_index_close = indexLastCandle['close']

        if(indexLastCandle['close'] > indexLastCandle['open']):
            logging.info('Green Candle')

            dLargeTfList.large_tf_find_resistance(indexLastCandle);
            dLargeTfList.large_tf_find_support(indexLastCandle);

            if(indexLastCandle['close'] < FiveMinTfLastCandle['EMA20']):
                if(indexLastCandle['close'] < (FiveMinTfLastCandle['EMA20'] - float(dict_inputs['ResDepth']))):
                    FiveMinTf_SupRes_flag = True
                    print('FiveMinTf_SupRes_flag:',FiveMinTf_SupRes_flag)
                else:
                    FiveMinTf_SupRes_flag = False
                    print('FiveMinTf_SupRes_flag:',FiveMinTf_SupRes_flag)

            if(indexLastCandle['close'] > FiveMinTfLastCandle['EMA20']):
                if(indexLastCandle['close'] > (FiveMinTfLastCandle['EMA20'] + float(dict_inputs['SupDepth']))):
                    FiveMinTf_SupRes_flag = True
                    print('FiveMinTf_SupRes_flag:',FiveMinTf_SupRes_flag)
                else:
                    FiveMinTf_SupRes_flag = False
                    print('FiveMinTf_SupRes_flag:',FiveMinTf_SupRes_flag)


            print('\n')
            print('day_pivot_flag:',day_pivot_flag)
            check_day_pivot(float(search_index_close))
            print('day_pivot_flag:',day_pivot_flag)
            print('\n')

            print('large_tf_supres_flag:',large_tf_supres_flag)
            dLargeTfList.check_large_tf_supres(float(search_index_close))
            print('large_tf_supres_flag:',large_tf_supres_flag)
            print('\n')

            print('day_hilow_flag:',day_hilow_flag)
            check_day_hilow(float(search_index_close))
            print('day_hilow_flag:',day_hilow_flag)
            print('\n')

            print('pdhl_flag:',pdhl_flag)
            check_pdhl(float(search_index_close))
            print('pdhl_flag:',pdhl_flag)
            print('\n')

            print('cpr_flag:',cpr_flag)
            print('fivemin_pivot_flag:',fivemin_pivot_flag)
            check_cpr_pivot(float(search_index_close))
            print('cpr_flag:',cpr_flag)
            print('fivemin_pivot_flag:',fivemin_pivot_flag)

            
            print('\n')
            print('day_high : ',day_high)
            print('day_low : ',day_low)
            print('\n')

            print('\n')
            print('pdh : ',pdh)
            print('pdl : ',pdl)
            print('\n')
            print('tc : ',tc)
            print('bc : ',bc)
            print('\n')
            print('large_tf_up_res : ',large_tf_up_res)
            print('large_tf_up_sup : ',large_tf_up_sup)
            print('\n')
            print('search_index_close : ',search_index_close)
            print('\n')
            print('large_tf_down_res : ',large_tf_down_res)
            print('large_tf_down_sup : ',large_tf_down_sup)
            print('\n')

            logging.info('day_pivot_flag : %s',day_pivot_flag)
            logging.info('large_tf_supres_flag : %s',large_tf_supres_flag)
            logging.info('day_hilow_flag: %s',day_hilow_flag)
            logging.info('pdhl_flag : %s',pdhl_flag)
            logging.info('cpr_flag : %s',cpr_flag)
            logging.info('fivemin_pivot_flag : %s',fivemin_pivot_flag)


            # Nifty Entry conditions
            logging.info('indexLastCandle:%s', indexLastCandle)
            if (dict_inputs["EntryStartTime"] <= currTime <= dict_inputs["EntryEndTime"]):
                logging.info('currTime is higher than EntryStartTime and lower than EntryEndTime')
                if(FiveMinTf_SupRes_flag == True):
                    logging.info('FiveMinTf_SupRes_flag is True')
                    if((day_pivot_flag == True) and (large_tf_supres_flag == True) and (day_hilow_flag == True) and (pdhl_flag == True) and (cpr_flag == True) and (fivemin_pivot_flag == True)):
                        logging.info('Support Resistance flags True')
                        if (indexLastCandle['close'] > indexLastCandle['open']):
                            logging.info('close = %s higher than open = %s', indexLastCandle['close'], indexLastCandle['open'])
                            if (indexLastCandle['close'] > indexPreviousCandle['high']):
                                logging.info('last close = %s higher than previous high = %s', indexLastCandle['close'], indexPreviousCandle['high'])
                                if(indexLastCandle['high'] - indexPreviousCandle['low']  < 80):
                                    logging.info('current candle high - previous candle low  is less than 80')
                                    if((indexLastCandle['close'] - indexLastCandle['open']) < 60):
                                        logging.info('candle size is less than 60')
                                        if(((indexLastCandle['high'] - indexLastCandle['open']) * 2/3) < (indexLastCandle['close'] - indexLastCandle['open'])):
                                            logging.info('candle body higher than Wick')
                                            if(indexLastCandle['close'] > indexLastCandle['EMA8']):
                                                logging.info('close higher than EMA8')
                                                if(indexLastCandle['EMA8'] >= indexLastCandle['EMA20']):
                                                    logging.info('EMA8 higher than EMA20')
                                                    if(indexLastCandle['CHOP'] < 50):
                                                        logging.info('CHOP %s less than 50',indexLastCandle['CHOP'])
                                                        if(optLastCandle['KVO'] > optLastCandle['KS']):
                                                            logging.info('KVO = %s higher than KS = %s',optLastCandle['KVO'], optPreviousCandle['KS'])
                                                            if(indexLastCandle['SMI'] >= indexLastCandle['SMID']):
                                                                logging.info('SMI: %s is greater than SMID: %s',indexLastCandle['SMI'],indexLastCandle['SMID'])

                                                                # setting ce signal
                                                                get_index_flag = True
                                                                logging.info('get_index_flag is set to True')

                                                                nifty_ltp1 = get_nifty_ltp("1")
                                                                logging.info('nifty_ltp1 :%s',nifty_ltp1)
                                                                #while ((float(nifty_ltp1) <= indexLastCandle['high']) and (loop_count > 1) and  (get_index_flag == True)):
                                                                while ((float(nifty_ltp1) <= indexLastCandle['high']) and (get_index_flag == True)):
                                                                    logging.info('nifty_ltp1: get_index_flag is True')
                                                                    time.sleep(2)
                                                                    nifty_ltp1 = get_nifty_ltp("1")
                                                                    #loop_count = loop_count - 1
                                                                logging.info('nifty_ltp1 final:%s',nifty_ltp1)
                                                                time.sleep(5)
                                                                nifty_ltp2 = get_nifty_ltp("2")
                                                                logging.info('nifty_ltp2 :%s',nifty_ltp2)

                                                                #while (float(nifty_ltp2) <= float(nifty_ltp1) and (loop_count > 1)):
                                                                while (float(nifty_ltp2) <= float(nifty_ltp1) and (get_index_flag == True)):
                                                                    logging.info('nifty_ltp2: get_index_flag is True')
                                                                    time.sleep(2)
                                                                    nifty_ltp2 = get_nifty_ltp("2")
                                                                    #loop_count = loop_count - 1

                                                                logging.info('nifty_ltp2 final:%s',nifty_ltp2)
                                                                if(float(nifty_ltp2) > float(nifty_ltp1) > indexLastCandle['high']):

                                                                    # checking single trade flat status
                                                                    check_single_trade_flag()
                                                                    if (single_trade_flag == '0'):
                                                                        logging.info('single_trade_flag is zero')
                                                                        logging.info('All conditions satisfied, setting ce signal')
                                                                        ce_entry_signal = True
                                                                    else:
                                                                        logging.info('single_trade_flag is not zero and other trade is in progress')


    # BankNifty Exit Conditions
    else:
        if script_name in traded_scripts:
            logging.info('script_name in traded_scripts')

            #case1
            if(band1_counter_status == True):
                if(band1_counter > 0):
                    logging.info('band1_counter : %s',band1_counter)
                    band1_counter =  band1_counter - 1
                    #dict_runtime_inputs["IndexStopLoss"] = dict_runtime_inputs["IndexStopLoss"] + 10
                    #IndexStopLoss_points = traded_index_points + dict_runtime_inputs["IndexStopLoss"]

                if(band1_counter == 0):

                    index_ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
                    index_ltp = index_ohlc['NSE:{}'.format(trading_symbol)]['last_price']
                    index_profit_points = index_ltp - traded_index_points

                    if(index_profit_points < float(dict_runtime_inputs["IndexSLRP"])):
                        band1_counter_status = False
                        logging.info('ce_exit_signal is set')
                        ce_exit_signal = True
                        '''
                         dict_runtime_inputs["IndexTarget"] = dict_runtime_inputs["IndexSLRP"]
                         logging.info('IndexTarget is set to : %s',dict_runtime_inputs["IndexTarget"])
                         IndexTarget_points = traded_index_points + dict_runtime_inputs["IndexTarget"]
                         band1_counter_status = False
                        '''

            #case2
            if(band2_counter_status == True):
                if(band2_counter > 0):
                    logging.info('band2_counter : %s',band2_counter)
                    band2_counter =  band2_counter - 1

                if(band2_counter == 0):
                    index_ohlc = kite.ohlc('NSE:{}'.format(trading_symbol))
                    index_ltp = index_ohlc['NSE:{}'.format(trading_symbol)]['last_price']
                    index_profit_points = index_ltp - traded_index_points

                    if(index_profit_points < (2 * float(dict_runtime_inputs["IndexSLRP"]))):
                        band2_counter_status = False
                        logging.info('ce_exit_signal is set')
                        ce_exit_signal = True
                        
                        '''
                        dict_runtime_inputs["IndexTarget"] = (2 * int(dict_runtime_inputs["IndexSLRP"]))
                        logging.info('IndexTarget is set to : %s',dict_runtime_inputs["IndexTarget"])
                        IndexTarget_points = traded_index_points + dict_runtime_inputs["IndexTarget"]
                        band2_counter_status = False
                        '''

            #if((currTime > dict_inputs["ExitTime"]) or  (indexLastCandle['EMA8'] <= indexLastCandle['EMA20']) or (indexLastCandle['SMI'] <= indexLastCandle['SMID'])) :
            if((currTime > dict_inputs["ExitTime"]) or  (indexLastCandle['EMA8'] < indexLastCandle['EMA20'])):
                logging.info('ce_exit_signal is set')
                ce_exit_signal = True

# executing main thread
def mainTask():
    global dict_inputs
    global script_name
    global traded_scripts
    global ce_entry_signal
    global ce_exit_signal
    global user_entry_input
    global user_exit_input
    global dict_runtime_inputs
    global single_trade_flag 
    global idle_state

    ce_entry_signal = False
    ce_exit_signal = False
    user_entry_input = False
    user_exit_input = False

    message_entry = 'NF CE Buy Entry'
    message_exit = 'NF CE Buy Exit'
    message_entry_auto = 'NF CE Buy Entry Auto'
    message_exit_auto = 'NF CE Buy Exit Auto'
    # Timer
    timer = threading.Timer(int(dict_runtime_inputs["TradeTf"]) * 60, mainTask)
    timer.start()

    #checking for automode flag set
    # Get historical data
    logging.info("Inside mainTask")
    check_single_trade_flag()
    if (single_trade_flag == '0' or single_trade_flag == '3'):
        logging.info('single trade flag %s',single_trade_flag)
        idle_state = 0
        logging.info('In mainTask, idle_state :%s',idle_state)
        hist_data()
    else:
        logging.info("Inside return 0 condition")
        idle_state = 1
        logging.info('In mainTask, idle_state :%s',idle_state)
        return 0
    #checking for hold flag set
    logging.info("Continue condition ")
    if len(traded_scripts) == 0:
        if (ce_entry_signal == True):
            #checking for number of Iterations
            logging.info('current number of iteration = %s',int(dict_inputs["Iterations"]))
            if (int(dict_inputs["Iterations"]) > 0):
                if (dict_runtime_inputs["auto_entry"] == "False"):
                    #sns.publish(TopicArn=topic_arn,Message=message_entry)
                    trade_popup_entry()
                    print('user_entry_input:',user_entry_input)
                    logging.info('user_entry_input = %s',user_entry_input)
                elif(dict_runtime_inputs["auto_entry"] == "True"):
                    #sns.publish(TopicArn=topic_arn,Message=message_entry_auto)
                    user_entry_input = True

                if(user_entry_input == True):
                    #initiating CE func
                    init_ce_entry()
                    dict_inputs["Iterations"] = int(dict_inputs["Iterations"]) - 1
                    time.sleep(2)

    # Nifty in Position
    if (script_name in traded_scripts):
        if(ce_exit_signal == True):
            if (dict_runtime_inputs["auto_exit"] == "False"):
                logging.info('1:auto_exit == false:%s',dict_runtime_inputs["auto_exit"])
                #sns.publish(TopicArn=topic_arn,Message=message_exit)
                trade_popup_exit()
                logging.info('2:auto_exit == false:%s',dict_runtime_inputs["auto_exit"])
                print('user_exit_input:',user_exit_input)
                logging.info('user_exit_input = %s',user_exit_input)
            elif(dict_runtime_inputs["auto_exit"] == "True"):
                #sns.publish(TopicArn=topic_arn,Message=message_exit_auto)
                user_exit_input = True
                
            
            if(user_exit_input == True):
                logging.info('user_exit_input = %s',user_exit_input)
                init_ce_exit()


# Main
if __name__ == '__main__':
    global thirdwindow_enable
    global secondwindow_enable 

    gc_status = gc.isenabled()
    if((gc_status) == True):
        logging.info("gc enabled")
        gc.disable()
        logging.info("gc disabled")

    currTime = datetime.now(timezone('Asia/Kolkata')).strftime('%H%M')
    #logging.info('current time:%s', currTime)
    while(dict_inputs["EntryStartTime"] > currTime):
        time.sleep(60)
        currTime = datetime.now(timezone('Asia/Kolkata')).strftime('%H%M')
        #logging.info('current time:%s is less than EntryStartTime:%s\n',currTime,dict_inputs["EntryStartTime"])

    month_cpr()
    cpr()
    large_tf_data()
    # GUI Starting
    #ce_firstwindow()

    t1 = threading.Thread(target=getStrickPrice)
    # starting thread 1
    t1.start()
    time.sleep(3)

# Timer for last candle
while True:
    time_min =  datetime.now(timezone('Asia/Kolkata')).strftime('%M')
    #print('time_min\n',time_min)

    if((int(time_min) % 2) == 0):
        logging.info('Start Threading Timer for mainTask\n')

        timer = threading.Timer(5, mainTask)
        timer.start()
        break

# Timer for 5 min candle
while True:
    time_min =  datetime.now(timezone('Asia/Kolkata')).strftime('%M')
    #print('time_min\n',time_min)
    if((int(time_min) % 5) == 0):
        logging.info('Start Threading Timer for FiveMinTf20Ema\n')
        timer = threading.Timer(5, FiveMinTf20Ema)
        timer.start()
        break


# Report header
if not os.path.exists(dict_inputs["ReportFile"]):
    header = ['Trigger Date','Instrument','Live/Paper', 'Buy/Sell', 'Qty', 'Opt Price','Amount','Index Entry/Exit','Index P&L', 'Opt P&L','Opt P&L %']
    with open(dict_inputs["ReportFile"], 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        f.close()

while True:
    if ((len(traded_scripts) == 0) and (secondwindow_enable == True)):
        logging.info('Starting second window from __main__')
        ce_secondwindow()

    if ((script_name in traded_scripts) and (thirdwindow_enable == True )):
        # Third Screen
        logging.info('Starting third window from __main__')
        ce_thirdwindow()
