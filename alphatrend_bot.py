import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import os
import requests
from datetime import datetime

# --- 1. CONFIGURATION (Variables from Railway) ---
API_KEY = os.environ.get('BINANCE_API_KEY')
SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
    'options': {'defaultType': 'future', 'adjustForTimeDifference': True},
})

exchange.set_sandbox_mode(True) 
exchange.urls['api'] = exchange.urls['test'] 
exchange.has['fetchCurrencies'] = False

# --- 2. TELEGRAM FUNCTION ---
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}"
        requests.get(url)
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

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
        df = pd.DataFrame(exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=50), 
                          columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df = calculate_alphatrend(df, coeff=COEFF, ap=AP)
        
        at_curr = df['AlphaTrend'].iloc[-1]
        at_prev = df['AlphaTrend'].iloc[-2]
        close_curr = df['Close'].iloc[-1]
        close_prev = df['Close'].iloc[-2]

        if close_prev < at_prev and close_curr > at_curr:
            if current_position != "LONG":
                msg = f"🟢 BULLISH: Price {close_curr} > AT {at_curr}"
                print(msg)
                exchange.create_market_buy_order('BTC/USDT', 0.01)
                send_telegram(msg)
                current_position = "LONG"
        elif close_prev > at_prev and close_curr < at_curr:
            if current_position != "SHORT":
                msg = f"🔴 BEARISH: Price {close_curr} < AT {at_curr}"
                print(msg)
                exchange.create_market_sell_order('BTC/USDT', 0.01)
                send_telegram(msg)
                current_position = "SHORT"
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    exchange.load_markets()
    while True:
        run_bot()
        time.sleep(60)
