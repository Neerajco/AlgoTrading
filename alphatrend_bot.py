import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
import os  # Yeh module zaroori hai
from datetime import datetime

# --- 1. BINANCE DEMO (FUTURES) SETUP ---
# Ab keys environment variables se fetch hongi
API_KEY = os.environ.get('BINANCE_API_KEY')
SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY')

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
})

exchange.set_sandbox_mode(True)
exchange.options['defaultType'] = 'future'
exchange.has['fetchCurrencies'] = False


# --- 2. BOT SETTINGS ---
SYMBOL = 'BTC/USDT'
TIMEFRAME = '1h'
COEFF = 4.0
AP = 14
TRADE_SIZE = 0.01  # Minimum size for BTC on futures

current_position = None  

# --- 3. ALPHATREND INDICATOR CALCULATION ---
def calculate_alphatrend(df, coeff, ap):
    df = df.copy()
    df['TR'] = ta.true_range(df['High'], df['Low'], df['Close'])
    df['ATR'] = ta.sma(df['TR'], length=ap)
    
    df['upT'] = df['Low'] - df['ATR'] * coeff
    df['downT'] = df['High'] + df['ATR'] * coeff

    df['mfi'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=ap)
    df['condition'] = df['mfi'] >= 50

    alphatrend = np.zeros(len(df))
    for i in range(1, len(df)):
        prev_at = alphatrend[i-1]
        if pd.isna(df['ATR'].iloc[i]):
            continue
        if df['condition'].iloc[i]:
            alphatrend[i] = prev_at if df['upT'].iloc[i] < prev_at else df['upT'].iloc[i]
        else:
            alphatrend[i] = prev_at if df['downT'].iloc[i] > prev_at else df['downT'].iloc[i]
            
    df['AlphaTrend'] = alphatrend
    df['AlphaTrend_2'] = df['AlphaTrend'].shift(2) 
    return df

# --- 4. CORE LIVE LOGIC ---
def run_bot():
    global current_position
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scanning Futures Demo Market for {SYMBOL}...")

    # Fetch live OHLCV data
    bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=100)
    df = pd.DataFrame(bars, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
    # Calculate AlphaTrend
    df = calculate_alphatrend(df, coeff=COEFF, ap=AP)
    
    at_last = df['AlphaTrend'].iloc[-2]
    at2_last = df['AlphaTrend_2'].iloc[-2]
    at_prev = df['AlphaTrend'].iloc[-3]
    at2_prev = df['AlphaTrend_2'].iloc[-3]
    
    current_price = df['Close'].iloc[-1]
    print(f"Live Price: ${current_price:.2f} | AT1: {at_last:.2f} | AT2: {at2_last:.2f}")

    # Check Futures Balance (Yeh ab bina SAPI crash ke chalega)
    try:
        balance = exchange.fetch_balance()
        usdt_balance = balance['total'].get('USDT', 0)
        print(f"Demo Wallet Balance: ${usdt_balance:.2f} USDT")
    except Exception as e:
        print("Balance Check Skipped (Demo API behavior)")

    # TRADING SIGNALS AND EXECUTION
    # 🟢 Bullish Cross (LONG)
    if (at_last > at2_last) and (at_prev <= at2_prev):
        if current_position != "LONG":
            print("🟢 BULLISH CROSS DETECTED! Placing Market BUY (LONG) Order...")
            order = exchange.create_market_buy_order(SYMBOL, TRADE_SIZE)
            print(f"✅ LONG Order Filled. Order ID: {order['id']}")
            current_position = "LONG"
            
    # 🔴 Bearish Cross (SHORT)
    elif (at_last < at2_last) and (at_prev >= at2_prev):
        if current_position != "SHORT":
            print("🔴 BEARISH CROSS DETECTED! Placing Market SELL (SHORT) Order...")
            order = exchange.create_market_sell_order(SYMBOL, TRADE_SIZE)
            print(f"✅ SHORT Order Filled. Order ID: {order['id']}")
            current_position = "SHORT"
            
    else:
        print(f"⏸️ No crossover found. Monitoring... Current State: {current_position}")

# --- 5. MAIN LIVE LOOP ---
if __name__ == '__main__':
    print("🚀 LIVE FUTURES DEMO BOT INITIALIZED...")
    print("Connecting to Binance Futures API...")
    try:
        # Ab yeh safely load hoga bina kisi crash ke
        exchange.load_markets() 
        print("✅ Connected Successfully to Futures Demo Environment!\n")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        exit()
        
    while True:
        try:
            run_bot()
            time.sleep(300) # Wait 5 minutes
        except Exception as e:
            print(f"❌ Error occurred in main loop: {e}")
            time.sleep(60)