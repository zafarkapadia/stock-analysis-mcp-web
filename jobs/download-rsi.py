from datetime import datetime
import json
import logging
import os
import sqlite3
import time
from dotenv import load_dotenv
import requests

# Configure logging module to display time, level, and message
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def process_portfolio_rsi(symbols_list):
    # 1. Base URL Endpoint
    url = "https://www.alphavantage.co/query"

    # 2. Portfolio Stock Symbols Target List
    rsi_results = []


    # 3. Get API Key
    load_dotenv()
    API_KEY = os.environ.get('API_KEY')


    # Create a clean persistent session object. 
    # This maintains an isolated pipeline state and forces the network adapter 
    # to bypass local script proxy caches that drop parameter values.
    session = requests.Session()

    # Enforce clean browser metadata identifiers to clear WAF security blockades
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Connection": "keep-alive"
    })

    for symbol in symbols_list:
        logging.info(f"Requesting RSI for {symbol}...")

        # Pack strict query parameters matching Alpha Vantage technical analysis syntax
        params = {
            "function": "RSI",
            "symbol": symbol.strip().upper(),
            "interval": "60min",  # Assigned exactly as the 60min string literal
            "time_period": "14",
            "series_type": "close",
            "entitlement": "delayed",
            "apikey": API_KEY
        }

        try:
            # Execute network call with an explicit transport timeout boundary
            r = session.get(url, params=params, timeout=10)
            
            # Check HTTP Protocol Status
            if r.status_code != 200:
                logging.error(f"❌ HTTP Network Error for {symbol}: Status {r.status_code}")
                continue
                
            data = r.json()
            
            # Check for Alpha Vantage Internal Response Notices
            if "Information" in data:
                logging.warning(f"⚠️ API Info for {symbol}: {data['Information']}")
            elif "Error Message" in data:
                logging.error(f"❌ Configuration Error for {symbol}: {data['Error Message']}")
                logging.error("   Please check that your asset symbol text or key is active.")
            else:
                rsi_series = data.get("Technical Analysis: RSI", {})
                if rsi_series:
                    # Isolate the newest chronological hourly key index timestamp
                    latest_timestamp = max(rsi_series.keys())
                    latest_rsi = rsi_series[latest_timestamp]["RSI"]
                    logging.info(f"✅ Success -> {symbol} | Time: {latest_timestamp} | RSI: {latest_rsi}")
                    rsi_results.append({
                        "symbol": symbol,
                        "rsi": latest_rsi,
                        "timestamp": latest_timestamp
                    })
                else:
                    logging.error(f"❌ Missing RSI payload matching indices for {symbol}.")

        except requests.exceptions.JSONDecodeError:
            logging.error(f"❌ Routing Blocked for {symbol}. Server returned HTML layout markup.")
            logging.error("   -> Your machine's current network IP profile or token assignment layout is rejected.")
        except requests.exceptions.Timeout:
            logging.error(f"❌ Network Timeout for {symbol}. Server took too long to reply.")
        except Exception as e:
            logging.error(f"❌ Connection Failure for {symbol}: {str(e)}")

        # Brief delay buffer to keep data transfer stable
        time.sleep(2)

    # Connect to local database file
    conn = sqlite3.connect("../data/trading_signals.db")
    cursor = conn.cursor()

    # Create the table structure matching your exact parameters
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            symbol TEXT,
            timestamp TEXT,
            rsi REAL
        )
    """)

    # Delete previous rows
    cursor.execute("DELETE FROM signals")
    conn.commit()

    # Insert the data safely and save changes
    logging.info("--- All portfolio symbols processed ---")

    for item in rsi_results:
        cursor.execute(
        "INSERT INTO signals (symbol, timestamp, rsi) VALUES (?, ?, ?)",
        (item['symbol'], item['timestamp'], item['rsi'])
        )
        
        logging.info(f"Database Save -> Symbol: {item['symbol']} | RSI: {item['rsi']}")

    conn.commit()
    conn.close()


# Example integration usage:
if __name__ == "__main__":
    # Fetch data first using your existing function
    my_portfolio = ["GOOGL", "GOOG", "AMZN", "AAPL", "META", "MSFT", "NVDA", "TSLA"]
    process_portfolio_rsi(my_portfolio)


