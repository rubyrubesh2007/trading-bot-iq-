from iqoptionapi.stable_api import IQ_Option
import numpy as np
import colorama
from colorama import Fore, Back, init
import asyncio
import talib
import threading
import time as t
import sys

init(autoreset=True)

#USER ACCOUNT CREDENTIALS AND LOG IN 
my_user = "iqtrader.evomatrix@gmail.com"    #YOUR IQOPTION USERNAME
my_pass = "P@$$w0rd@2007"         #YOUR IQOTION PASSWORD

# Global variables for trading signals
bollinger_signal = 0
macd_above_signal = False
ma_above_price = False
money = 1  # Initial amount for Option
goal = "EURUSD"  # Initial target instrument
expirations_mode = 1  # Option Expiration Time in Minutes (You can adjust this as needed)
size = 60
period = 14
last_trade_result = None
my_close = []
my_high = []
my_low = []
my_volume = []


Iq = IQ_Option(my_user, my_pass)
iqch1, iqch2 = Iq.connect()
if iqch1:
    print(Fore.GREEN + "Login successful.")
else:
    print(Fore.RED + "Login Failed.")
    sys.exit()

async def set_balance_type(Iq):
    print(Back.MAGENTA + Fore.BLACK + "[+] ACCOUNT TYPE: ")
    print("1.REAL \n2.PRACTICE")
    acc_type = input("ENTER A NUMBER : ")
    if acc_type == '1':
        Iq.change_balance("REAL")
    elif acc_type == '2':
        Iq.change_balance("PRACTICE")
    print(Fore.GREEN + "Trading Started, Please Wait...")

print(Back.MAGENTA + Fore.BLACK + "[+] Assets:")
print(Fore.RED + "AUDCAD,AUDJPY,AUDUSD,EURGBP,EURUSD,EURJPY,GBPJPY,GBPUSD,USDCAD,USDJPY")
print(Fore.RED + "add -OTC at end of Assets on market holidays type Asset in capital letters")
goal = input(Fore.BLUE + "Enter the ASSET:")
money = float(input(Fore.BLUE + "Enter the AMOUNT($):"))

balance = Iq.get_balance()
print(Back.MAGENTA + Fore.BLACK + "[+] Amount Balance:", balance)


#GET OHLC DATA FROM IQOPTION
Iq.start_candles_stream(goal,size,period)
cc=Iq.get_realtime_candles(goal,size)

#STORE OPEN AND CLOSE VALUES
my_open = []
my_close =[]

#WHEN TO PLACE BET BEFORE EXPIRY TIME (TIME IN SECONDS)
place_at  = 0
def get_purchase_time():
    remaning_time=Iq.get_remaning(expirations_mode)   
    purchase_time=remaning_time
    return purchase_time

def get_expiration_time():
    exp=Iq.get_server_timestamp()
    time_to_buy=(exp % size)
    return int(time_to_buy)

#THREAD TO RUN TIMER SIMULTANEOUSLY
def expiration_thread():
    global place_at
    while True:
        x=get_expiration_time()
        t.sleep(1)
        if x == place_at:
            place_option(Iq, my_close, my_high, my_low, my_volume, size, period)
threading.Thread(target=expiration_thread).start()

#SET VALUES TO PLACE BET(S)
def set_values( my_close, my_high, my_low, my_volume, size):
    cc = Iq.get_realtime_candles(goal, size)
    for k in list(cc.keys()):
        close = cc[k]['close']
        my_close.append(close)
        low = cc[k]['min']
        my_low.append(low)
        volume = cc[k]['volume']
        my_volume.append(volume)
        high = cc[k]['max']
        my_high.append(high)


#BET PLACEMENT CONDITIONS AND BET PLACEMENT
def place_option(Iq, my_close, my_high, my_low, my_volume, size, period):  
    
    global bollinger_signal
    global macd_above_signal
    global ma_above_price
    global last_trade_result  # Define last_trade_result in this scope
    
    set_values(my_close, my_high, my_low, my_volume, size)

    while True:
        set_values(my_close, my_high, my_low, my_volume, size)
        if len(my_close) < period:
            t.sleep(5)
            continue

        upper, middle, lower = talib.BBANDS(np.array(my_close), timeperiod=period)
        upper_val = upper[-1]
        middle_val = middle[-1]
        lower_val = lower[-1]

        macd, macd_signal, _ = talib.MACD(np.array(my_close), fastperiod=12, slowperiod=26, signalperiod=9)
        macd_val = macd[-1]
        macd_signal = macd_signal[-1]

        ma = talib.SMA(np.array(my_close), timeperiod=period)
        ma_val = ma[-1]

        line = "#" * 80
        print(line)
        print("\t\t\t\t", goal, "\t\t\t")
        print(line)

        # Bollinger Bands
        put = []
        call = []

        print(Back.CYAN+Fore.BLACK+"BOLLINGER BAND:")
        if my_close[-1] > upper[-1]:
            bollinger_signal = -1
        elif my_close[-1] < lower[-1]:
            bollinger_signal = 1
        else:
            bollinger_signal = 0

        if bollinger_signal == -1:
            print("Price above upper Bollinger Band. Placing ", Fore.RED + "'PUT⇩'", " Option.",
                  Fore.BLUE + "\nUp:", upper_val, Fore.BLUE + "mid:", middle_val, Fore.BLUE + "low:", lower_val)
            put.append(1)
        elif bollinger_signal == 1:
            print("Price below lower Bollinger Band. Placing ", Fore.GREEN + "'CALL⇑'", " Option.",
                  Fore.BLUE + "\nUp:", upper_val, Fore.BLUE + "mid:", middle_val, Fore.BLUE + "low:", lower_val)
            call.append(1)
        else:
            print("No Clear Trading Signal (Bollinger Bands)😕.", Fore.BLUE + "\nUp:", upper_val, Fore.BLUE + "mid:",
                  middle_val, Fore.BLUE + "low:", lower_val)

        # MACD
        print(Back.CYAN + Fore.BLACK + "MACD:")

        if macd_val > macd_signal and not macd_above_signal:
            print("MACD crossed above the signal line. Placing ", Fore.RED + "'PUT⇩'", " Option.",
                  Fore.BLUE + "macd val=", macd_val)
            macd_above_signal = True
            put.append(1)
        elif macd_val < macd_signal and macd_above_signal:
            print("MACD crossed below the signal line. Placing ", Fore.GREEN + "'CALL⇑'", " Option.",
                  Fore.BLUE + "macd val=", macd_val)
            macd_above_signal = False
            call.append(1)
        else:
            print("No Trading Signal (MACD)😕.", Fore.BLUE + "macd val=", macd_val)


        # Moving Average
        print(Back.CYAN + Fore.BLACK + "MA:")

        if my_close[-1] > ma_val and not ma_above_price:
            print("Price crossed above the Moving Average. Placing ", Fore.RED + "'PUT⇩'", " Option.", Fore.BLUE + "\nMA val=", ma_val)
            ma_above_price = True
            put.append(1)
        elif my_close[-1] < ma_val and ma_above_price:
            print("Price crossed below the Moving Average. Placing ", Fore.GREEN + "'CALL⇑'", " Option.", Fore.BLUE + "\nMA val=", ma_val)
            ma_above_price = False
            call.append(1)
        else:
            print("No Trading Signal (Moving Average)😕.", Fore.BLUE + "MA val=", ma_val)

        print(line)

        call_signal = len(call)
        put_signal = len(put)

        print("total call=", call_signal, "\ttotal put=", put_signal)

        # Calculate the average signal
        if call_signal < put_signal:
            if put_signal == 3:
                overall_signal = Fore.RED + "STRONG PUT⇩"
                print(Fore.BLUE + "Overall Signal:", overall_signal)
                check,id=Iq.buy(money,goal,"put",expirations_mode)
                if check:
                    print(Fore.GREEN + "PUT Option Placed Successfully.")

                else:
                    print(Fore.RED + "PUT option Failed.")
                print(line)
                
            elif put_signal == 2:
                overall_signal = Fore.LIGHTRED_EX + "PUT⇩"
                print(Fore.BLUE + "Overall Signal:", overall_signal)
                check,id=Iq.buy(money,goal,"put",expirations_mode)
                if check:
                    print(Fore.GREEN + "PUT Option Placed Successfully.")

                else:
                    print(Fore.RED + "PUT option Failed.")
                print(line)
                
            else:
                overall_signal = "NEUTRAL(PUT⇩😕)"
                print(Fore.BLUE + "Overall Signal:", overall_signal)

        elif call_signal > put_signal:
            if call_signal == 3:
                overall_signal = Fore.GREEN + "STRONG CALL⇑"
                print(Fore.BLUE + "Overall Signal:", overall_signal)
                check,id=Iq.buy(money,goal,"call",expirations_mode)
                if check:
                    print(Fore.GREEN + "CALL Option Placed Successfully.")

                else:
                    print(Fore.RED + "CALL option Failed.")

                print(line)
                
            elif call_signal == 2:
                overall_signal = Fore.LIGHTGREEN_EX + "CALL⇑"
                print(Fore.BLUE + "Overall Signal:", overall_signal)
                check,id=Iq.buy(money,goal,"call",expirations_mode)
                if check:
                    print(Fore.GREEN + "CALL Option Placed Successfully.")

                else:
                    print(Fore.RED + "CALL option Failed.")
                
                print(line)
                
            else:
                overall_signal = "NEUTRAL(CALL⇑😕)"
                print(Fore.BLUE + "Overall Signal:", overall_signal)

        else:
            overall_signal = "NEUTRAL(NO SIGNALS😕)"
            print(Fore.BLUE + "Overall Signal:", overall_signal)

        print(Back.MAGENTA + Fore.BLACK + f"Last Trade Result: {last_trade_result}")

        print(line)

        t.sleep(60)

            
#--END
