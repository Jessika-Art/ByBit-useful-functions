
import pandas as pd
from pybit import HTTP  # version: pybit==1.3.6 USE THIS VERSION
from datetime import datetime
import time



''' HOW TO:
1 Get last price.
2 Get historical data from now to going back.
3 Open a position.
4 Get opened positions
5 Set Stop Loss
6 Simple execution '''


''' SET MAIN VARIABLES '''
TESTNET = 'https://api-testnet.bybit.com'
MAINNET = 'https://api.bybit.com'
KEY = ''        # Api key
SECRET = ''     # Secret key
SYMBOL = 'ETHUSDT'
T_FRAME = 5     # 5 min timeframe
QUANTITY = 0.40 # ETH in this case



''' FOR GRABBING DATA GOING BACK TO THE PAST '''
def TIMESTAMP():
    today_now = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    dt = datetime.strptime(today_now, '%Y-%m-%d %H:%M:%S')
    in_secods_now = int(dt.timestamp())
    
    # EXPLANATION:
    # ByBit works with seconds, not with human datetime,
    # so grab the today's date and time and convert it
    # in seconds, we'll put this function
    # in the "from_time" variable when we ask data from ByBit.
    return in_secods_now
    


''' GET LAST CANDLE PRICE '''
def get_symbol_price(SYMBOL): # return close price only
    session = HTTP(TESTNET, api_key=KEY, api_secret=SECRET)
    prices = session.query_kline(
        symbol = SYMBOL,
        interval = T_FRAME, # 5 min
        limit = 200,        # 200 is max
        from_time = (TIMESTAMP() - (200 * T_FRAME)*60))
        # "from_time" is equal to the function previously created
        # which gives us the datetime now in seconds "TIMESTAMP()"
        # minus the "limit" which is 200 candles times the "T_FRAME"
        # which is 5 min times 60 which are the seconds in a minute.

    df = pd.DataFrame(prices['result']) # you can avoid Pandas and return a normal dictionary if you like more.
    df = df['close'].iloc[-1]   # get the last candle which will be used to place an order.
                                # or you can also set the "limit" as 1 instead 200 to get the last candle.

    return(df) # you can also return open, high or low



''' GET HISTORICAL CANDLES '''
def get_futures_klines(SYMBOL): # return Date Open High Low Close Volume
    session = HTTP(TESTNET, api_key=KEY, api_secret=SECRET)
    the_request = session.query_kline(
        symbol = SYMBOL,
        interval = T_FRAME,
        limit = 200,
        from_time = (TIMESTAMP() - (200 * T_FRAME)*60))

    result = the_request['result'] # keep only the results
    df = pd.DataFrame(result) # put them into a dataframe
    df = df.drop(['id','symbol','period','interval','start_at','turnover'],axis=1)  # cut off the useless data
    
    df = df[['open_time','open','high','low','close','volume']].astype(float)       # keep only those
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)

    return(df)


''' DEFINE A SIMPLE OPEN A POSITION '''
def open_position(SYMBOL, SIDE, QUANTITY):                  # keep as arguments the 3 important variables we want to play
    session = HTTP(TESTNET, api_key=KEY, api_secret=SECRET) # standard rquest
    print(f'Open:: {SYMBOL} with Qty:: {str(QUANTITY)}')    # OUTPUT: Open:: ETHUSDT with Qty:: 0.80pr 
    DATA = get_symbol_price(SYMBOL)                         # grab last 200 candles

    if (SIDE == 'long'):
        BEST_PRICE = str(round(DATA*(1-0.01),2)) # open a "Buy" position at 1% less of the actual price to avoid the spred between Bid Ask 😉
        params = session.place_active_order(
            symbol = SYMBOL,
            side = "Buy",
            order_type = "Market",
            qty = QUANTITY,
            price = BEST_PRICE,
            time_in_force = "GoodTillCancel",
            reduce_only = False, # if True the position will be closed instead opened
            close_on_trigger = False)

        response = (params)
        return response  
       
    if (SIDE == 'short'):
        BEST_PRICE = str(round(DATA*(1+0.01),2)) # open a "Sell" position at 1% more of the actual price to avoid the spred between Ask Bid 😉
        params = session.place_active_order(
            symbol = SYMBOL,
            side = "Sell",
            order_type = "Market",
            qty = QUANTITY,
            price = BEST_PRICE,
            time_in_force = "GoodTillCancel",
            reduce_only = False, # if True the position will be closed instead opened
            close_on_trigger = False)

        response = (params)
        return response  

# CALL THIS FUNCTION: open_position(SYMBOL, "long", 0.20)


''' GET ALL OPENED POSITIONS '''
def get_opened_positions(SYMBOL):
    session = HTTP(TESTNET, api_key=KEY, api_secret=SECRET)
    status = session.my_position(symbol=SYMBOL)
    positions = pd.DataFrame(status['result'])
    
    quantity = positions[positions['symbol']==SYMBOL]['size'].astype(float).tolist()[0:]
    laverage = positions[positions['symbol']==SYMBOL]['leverage']
    entryprice = positions[positions['symbol']==SYMBOL]['entry_price']
    profit = positions['unrealised_pnl']
    # Request Balance
    request_balance = session.get_wallet_balance(coin='USDT') # 'USDT' if you're trading with USDT
    balance = round(float(request_balance['result']['USDT']['wallet_balance']), 2)
        

    # When we request 'opened positions' data, ByBit will gives a nested dictionary,
    # index 0 for Buy position and index 1 for Sell position.
    # Since we transformend the request from a dict to a dataframe we can check
    # the size in each index to say if there is any position open.
    # If the quantity (size) is more than 0, well a position is currently open.

    if quantity[0] > 0: # if the quantity of the index 0 which refers to the 'Buy' position is more than 0, a positon is openend.
        quantity = quantity[0]
        pos = "long"
        
    elif quantity[1] > 0:
        quantity = quantity[1]
        pos = "short"
        
    else:
        pos = ""
    
    return([pos, quantity, profit, laverage, balance, entryprice, 0])


''' STOP LOSS FOR BUY POSITION '''
def STOP_IF_LONG(symbol):
    position = get_opened_positions(symbol)         # check if a position is open
    if position[0] == 'long':                       # index [0] refers to "pos" variable inside the "get_opened_positions(symbol)" which could be "long" or "short"
        stop_percent = 0.01                         # will used as 1%
        entry_price = position[5][0]                # get the entry price
        stop_price = entry_price*(1-stop_percent)   # set the stop loss to the 1% of the total order. if I Buy 1000, lose max 10.
        STOP = stop_price
    return round(STOP, 3)                           # IMPORTANT IS TO ROUND THE RETURN PRICE, OTHERWISE WILL NOT WORKS.


''' STOP LOSS FOR SELL POSITION '''
def STOP_IF_SHORT(symbol):
    position = get_opened_positions(symbol)
    if position[0] == 'short':
        stop_percent = 0.01
        # position = get_opened_positions(symbol)
        entry_price = position[5][1]
        stop_price = entry_price*(1+stop_percent)
        STOP = stop_price
    return round(STOP, 3)



''' SIMPLE EXECUTION '''
# Let's say you have created a strategy which return a signal buy or signal sell as a string.
def main():
    signal = ''
    try:
            
        if signal == 'long': # if your startegy told you that the signal is now for a Buy position.
            # open position long
            open_position(SYMBOL,'long', QUANTITY)

            # then set stop loss
            session_SLL = HTTP(TESTNET, api_key=KEY, api_secret=SECRET)
            session_SLL.set_trading_stop(
            symbol=SYMBOL,
            side="Buy",
            stop_loss=STOP_IF_LONG(SYMBOL))

        elif signal == 'short':
            # open position short
            open_position(SYMBOL,'short', QUANTITY)

            # then set stop loss
            session_SLS = HTTP(TESTNET, api_key=KEY, api_secret=SECRET)
            session_SLS.set_trading_stop(
            symbol=SYMBOL,
            side="Sell",
            stop_loss=STOP_IF_SHORT(SYMBOL))

        else: 
            None
      
    except :
        print('\n\nSomething did not work. Going on...')







