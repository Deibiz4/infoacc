import urllib.request
import json
import logging

def fetch_crypto_fear_and_greed():
    """Fetches Crypto Fear & Greed Index from Alternative.me API."""
    url = "https://api.alternative.me/fng/?limit=1"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                fng_data = data['data'][0]
                value = int(fng_data['value'])
                classification = fng_data['value_classification']
                
                # Classify colors
                if value >= 75:
                    color = "#10b981" # Extreme Greed (Emerald)
                elif value >= 55:
                    color = "#34d399" # Greed (Green)
                elif value >= 45:
                    color = "#f59e0b" # Neutral (Amber)
                elif value >= 25:
                    color = "#f97316" # Fear (Orange)
                else:
                    color = "#ef4444" # Extreme Fear (Red)
                    
                return {
                    "value": value,
                    "classification": classification,
                    "color": color,
                    "timestamp": fng_data.get("timestamp")
                }
    except Exception as e:
        logging.warning(f"Unable to fetch Crypto Fear & Greed index: {e}")
        
    # Fallback default
    return {
        "value": 50,
        "classification": "Neutral",
        "color": "#f59e0b",
        "timestamp": None
    }

def get_stock_sentiment(vix_value):
    """Calculates stock market sentiment based on VIX index."""
    try:
        vix = float(vix_value)
        if vix <= 13:
            return {"value": 85, "classification": "Extreme Greed", "color": "#10b981"}
        elif vix <= 16:
            return {"value": 65, "classification": "Greed", "color": "#34d399"}
        elif vix <= 20:
            return {"value": 50, "classification": "Neutral", "color": "#f59e0b"}
        elif vix <= 28:
            return {"value": 30, "classification": "Fear", "color": "#f97316"}
        else:
            return {"value": 15, "classification": "Extreme Fear", "color": "#ef4444"}
    except (ValueError, TypeError):
        return {"value": 50, "classification": "Neutral", "color": "#f59e0b"}

if __name__ == "__main__":
    print("Crypto F&G:", fetch_crypto_fear_and_greed())
    print("Stock Sentiment (VIX 14.5):", get_stock_sentiment(14.5))
