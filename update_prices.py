import json
import urllib.request
from datetime import datetime
import ssl

def fetch_yahoo_price(ticker):
    """Fetches the latest regular market price from Yahoo Finance API."""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    # Ignore SSL certificate errors just in case
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode())
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price)
    except Exception as e:
        print(f"Failed to fetch {ticker}: {e}")
        return None

def update_carbon_data():
    json_path = 'carbon_prices.json'
    
    # 1. Read existing data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    # 2. Fetch live EU Carbon price in EUR (CO2.MI) and the EUR/USD exchange rate
    eua_eur_price = fetch_yahoo_price('CO2.MI')
    eur_usd_rate = fetch_yahoo_price('EURUSD=X')
    
    if eua_eur_price and eur_usd_rate:
        live_eu_usd = round(eua_eur_price * eur_usd_rate, 2)
        print(f"Successfully fetched Live EU ETS: ${live_eu_usd}")
        
        # 3. Update the EU ETS price in our JSON array
        for item in data['prices']:
            if item['name'] == 'EU ETS':
                item['price'] = live_eu_usd
                break
                
        # Update timestamp to include hours and save the Exchange Rate!
        data['last_updated'] = datetime.now().strftime('%b %d, %Y (%H:%M UTC)')
        data['exchange_rate'] = f"1 EUR = {eur_usd_rate:.4f} USD"
        
        # 4. Save the updated data back to the file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

if __name__ == "__main__":
    update_carbon_data()
