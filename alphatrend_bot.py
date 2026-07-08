import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import os
from datetime import datetime

# --- 1. BINANCE DEMO (FUTURES) SETUP ---
# Railway ke Variables se keys le raha hai
API_KEY = os.environ.get('BINANCE_API_KEY')
SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY')

# Futures Demo ke liye specific configuration
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
    },
})

# IMPORTANT: Demo Trading ke liye url ko manually 'test' par point karein
exchange.set_sandbox_mode(True) 
exchange.urls['api'] = exchange.urls['test'] 
exchange.has['fetchCurrencies'] = False

# --- 2. BOT SETTINGS ---
SYMBOL = 'BTC/USDT'
TIMEFRAME = '1h'
COEFF = 4.0
AP = 14
TRADE_SIZE = 0.01

current_position = None  

# --- 3. ALPHATREND CALCULATION ---
def calculate_alphatrend(df, coeff, ap):
    df = df.copy()
    df['TR'] = ta.true_range(df['High'], df['Low'], df['Close'])
    df['ATR'] = ta.sma(df['TR'], length=ap)
    df['upT'] = df['Low'] - df['ATR'] * coeff
    df['downT'] = df['High'] + df['ATR'] * coeff
    df['mfi'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=ap)
    
    alphatrend = [0.0] * len(df)
    for i in range(1, len(df)):
        if df['mfi'].iloc[i] >= 50:
            alphatrend[i] = df['upT'].iloc[i] if df['upT'].iloc[i] > alphatrend[i-1] else alphatrend[i-1]
        else:
            alphatrend[i] = df['downT'].iloc[i] if df['downT'].iloc[i] < alphatrend[i-1] else alphatrend[i-1]
    df['AlphaTrend'] = alphatrend
    return df

# --- 4. CORE LIVE LOGIC ---
def run_bot():
    global current_position
    try:
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=50)
        df = pd.DataFrame(bars, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df = calculate_alphatrend(df, coeff=COEFF, ap=AP)
        
        at_curr = df['AlphaTrend'].iloc[-1]
        at_prev = df['AlphaTrend'].iloc[-2]
        close_curr = df['Close'].iloc[-1]
        close_prev = df['Close'].iloc[-2]

        if close_prev < at_prev and close_curr > at_curr:
            if current_position != "LONG":
                print(f"🟢 BULLISH: Price {close_curr} > AT {at_curr}")
                exchange.create_market_buy_order(SYMBOL, TRADE_SIZE)
                current_position = "LONG"
                
        elif close_prev > at_prev and close_curr < at_curr:
            if current_position != "SHORT":
                print(f"🔴 BEARISH: Price {close_curr} < AT {at_curr}")
                exchange.create_market_sell_order(SYMBOL, TRADE_SIZE)
                current_position = "SHORT"
        else:
            print(f"⏸️ Monitoring... Price: {close_curr} | State: {current_position}")
    except Exception as e:
        print(f"❌ Logic Error: {e}")

if __name__ == '__main__':
    print("🚀 Initializing Bot...")
    try:
        # Markets load karein
        exchange.load_markets()
        print("✅ Connected Successfully to Futures Demo!")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        # Yahan exit mat karo, shayad retry mein chal jaye
    
    while True:
        run_bot()
        time.sleep(60) # 1 minute wait
