import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

def fetch_btc_volume_data():
    symbol = "BTCUSDT"
    interval = "1h"
    limit = 1000 # Roughly 41 days of data
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code}")
        return None
    
    data = response.json()
    
    # Klines format: [open_time, open, high, low, close, volume, close_time, quote_asset_volume, ...]
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume', 
        'close_time', 'quote_asset_volume', 'number_of_trades', 
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # Convert timestamps to PHT
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    utc = pytz.utc
    pht = pytz.timezone('Asia/Manila')
    df['open_time_pht'] = df['open_time'].dt.tz_localize(utc).dt.tz_convert(pht)
    
    # Extract hour
    df['hour'] = df['open_time_pht'].dt.hour
    
    # Use quote_asset_volume (USDT value) for better institutional insight
    df['quote_asset_volume'] = df['quote_asset_volume'].astype(float)
    
    # Group by hour and calculate mean volume
    hourly_vol = df.groupby('hour')['quote_asset_volume'].mean().sort_index()
    
    return hourly_vol

if __name__ == "__main__":
    vol_data = fetch_btc_volume_data()
    if vol_data is not None:
        print("Hour | Avg Quote Volume (USDT)")
        print("-" * 30)
        for hour, vol in vol_data.items():
            print(f"{hour:02d}:00 | {vol:,.2f}")
            
        # Find peaks
        max_vol_hour = vol_data.idxmax()
        max_vol_value = vol_data.max()
        print(f"\nPeak Volume Hour: {max_vol_hour:02d}:00 PHT")
        print(f"Peak Volume Value: {max_vol_value:,.2f} USDT")
