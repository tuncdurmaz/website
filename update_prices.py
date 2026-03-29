import json
import urllib.request
from datetime import datetime
import ssl
import re

def fetch_yahoo_price(ticker):
    """Fetches the latest EU ETS price and Forex rates from Yahoo Finance."""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode())
            return float(data['chart']['result'][0]['meta']['regularMarketPrice'])
    except Exception as e:
        print(f"Failed to fetch {ticker}: {e}")
        return None

def scrape_carboncredits_com():
    """Scrapes regional prices from carboncredits.com using robust regex."""
    url = "https://carboncredits.com/carbon-prices-today/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    prices = {}
    try:
        # Fetch the HTML of the website
        html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
        
        # Regex mappings for specific markets
        # This tells the scraper to look for the market name and grab the $XX.XX amount that follows it
        mappings = {
            'UK ETS': r'(?:UK ETS|UK Carbon|UKA)[\s\S]{1,100}?\$([0-9]{1,3}\.[0-9]{2})',
            'California CaT': r'(?:California|CCA)[\s\S]{1,100}?\$([0-9]{1,3}\.[0-9]{2})',
            'New Zealand': r'(?:New Zealand|NZU)[\s\S]{1,100}?\$([0-9]{1,3}\.[0-9]{2})',
            'China ETS': r'(?:China|CEA)[\s\S]{1,100}?\$([0-9]{1,3}\.[0-9]{2})',
            'South Korea': r'(?:South Korea|KAU)[\s\S]{1,100}?\$([0-9]{1,3}\.[0-9]{2})'
        }
        
        # Strip all HTML tags to make text scanning highly reliable
        clean_text = re.sub(r'<[^>]+>', ' ', html)
        
        for market, pattern in mappings.items():
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                prices[market] = float(match.group(1))
                print(f"Scraped {market}: ${prices[market]}")
                
    except Exception as e:
        print(f"Failed to scrape CarbonCredits.com: {e}")
    
    return prices

def update_carbon_data():
    json_path = 'carbon_prices.json'
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    # 1. Fetch EU ETS (The Gold Standard method)
    eua_eur_price = fetch_yahoo_price('CO2.MI')
    eur_usd_rate = fetch_yahoo_price('EURUSD=X')
    
    updates_made = False

    if eua_eur_price and eur_usd_rate:
        live_eu_usd = round(eua_eur_price * eur_usd_rate, 2)
        print(f"Successfully fetched Live EU ETS: ${live_eu_usd}")
        for item in data['prices']:
            if item['name'] == 'EU ETS':
                item['price'] = live_eu_usd
                updates_made = True
                break
        # Format the exchange rate footprint for the frontend
        data['exchange_rate'] = f"1 EUR = {eur_usd_rate:.4f} USD"

    # 2. Scrape the remaining 5 markets from CarbonCredits.com
    scraped_prices = scrape_carboncredits_com()
    
    for market, scraped_price in scraped_prices.items():
        for item in data['prices']:
            if item['name'] == market:
                # Sanity Check: Protects your site from website layout changes. 
                # If the scraper grabs an accidental number (like a year "$2024.00") it ignores it.
                if 2.00 <= scraped_price <= 250.00: 
                    item['price'] = scraped_price
                    updates_made = True
                break

    # 3. Only save to the file if we actually got fresh data!
    if updates_made:
        data['last_updated'] = datetime.now().strftime('%B %d, %Y (%H:%M UTC)')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print("carbon_prices.json fully updated successfully.")
    else:
        print("No new data retrieved. JSON file left unchanged.")

if __name__ == "__main__":
    update_carbon_data()
