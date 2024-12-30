import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
from datetime import datetime
import logging
import time


# Define Telegram bot details
TELEGRAM_API_URL = "https://api.telegram.org/bot8018141731:AAEzdGmFO4DRoSZN-Jkqt2bCysOc2KfPN9E/sendMessage"
CHAT_ID = "-4600339839"

# Chartlink screener URL
CHARTLINK_SCREENER_URL = "https://chartink.com/screener/weekly-scan-nitin-2"

# To keep track of previously added stocks
previous_stocks = set()

# Set up logging
logging.basicConfig(filename="C:/Users/HP/Desktop/BOT/stock_monitor.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_telegram_message(message):
    """Sends a message to the Telegram chat."""
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    try:
        response = requests.post(TELEGRAM_API_URL, data=payload)
        response.raise_for_status()  # Raise an exception for 4xx/5xx errors
    except requests.exceptions.RequestException as e:
        current_time = datetime.now().strftime("%d-%b-%Y at %I:%M%p")
        print(f"{current_time} - Failed to send message: {e}")
        logging.error(f"Failed to send message: {e}")

def get_all_stocks():
    """Scrapes the Chartlink screener page for all stock nsecodes."""
    with requests.Session() as s:
        try:
            response = s.get(CHARTLINK_SCREENER_URL)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get CSRF token
            csrf = soup.select_one("[name='csrf-token']")['content']
            s.headers['x-csrf-token'] = csrf
            
            # Prepare POST request payload
            process_url = 'https://chartink.com/screener/process'
            payload = {
                "scan_clause": '( {cash} ( ( {cash} ( ( {cash} ( weekly macd line( 21 , 3 , 9 ) >= weekly macd signal( 21 , 3 , 9 ) and weekly ha-close  > weekly "wma( ( ( 2 * wma( (weekly close), 15) ) - wma((weekly close), 30) ), 5)" and 1 week ago  ha-close  <= 1 week ago  "wma( ( ( 2 * wma( (weekly close), 15) ) - wma((weekly close), 30) ), 5)" and 1 week ago ha-close  < weekly "wma( ( ( 2 * wma( (1 week ago min( 12 , weekly ha-close  )), 15) ) - wma((1 week ago min( 12 , weekly ha-close  )), 30) ), 5)" ) ) or( {cash} ( weekly ha-close  >= weekly "wma( ( ( 2 * wma( (weekly ha-close ), 22) ) - wma((weekly ha-close ), 44) ), 6)" and 1 week ago ha-close  < weekly "wma( ( ( 2 * wma( (1 week ago min( 12 , weekly ha-close  )), 15) ) - wma((1 week ago min( 12 , weekly ha-close  )), 30) ), 5)" and weekly macd line( 11 , 3 , 9 ) > weekly macd signal( 11 , 3 , 9 ) and 1 week ago  macd line( 11 , 3 , 9 ) <= 1 week ago  macd signal( 11 , 3 , 9 ) and 1 week ago max( 7 , 1 week ago macd histogram( 21 , 3 , 9 ) ) < 0 ) ) ) ) and weekly rsi( 9 ) >= 40 and weekly wma( weekly rsi( 9 ) , 11 ) < weekly rsi( 9 ) and latest close > 50 and 1 day ago volume > 50000 and market cap > 1000 and weekly macd histogram( 21 , 3 , 9 ) > 0 and weekly ha-close  > weekly ha-open  and 1 week ago ha-close  > 1 week ago ha-open  and latest close > latest open and weekly min( 10 , weekly macd histogram( 21 , 3 , 9 ) ) < -20 and weekly volume > weekly sma( weekly close , 7 ) ) )'
            }

            # Sending POST request to process the screener
            r = s.post(process_url, data=payload)
            r.raise_for_status()

            # Parse the JSON response
            stock_data = r.json().get('data', [])
            
            if stock_data:
                df = pd.DataFrame(stock_data)
                
                # Sort by 'close' and clean up DataFrame
                df.sort_values(by=['close'], inplace=True)
                df.drop(['sr'], axis=1, errors='ignore', inplace=True)
                df.reset_index(drop=True, inplace=True)
                
                current_time = datetime.now().strftime("%d-%b-%Y at %I:%M%p")
                print(f'{current_time} - Number of stocks found: {len(df)}')
                logging.info(f'Number of stocks found: {len(df)}')

                return df
            else:
                current_time = datetime.now().strftime("%d-%b-%Y at %I:%M%p")
                print(f'{current_time} - No stock data found.')
                logging.warning('No stock data found.')
                return None
        except requests.exceptions.RequestException as e:
            current_time = datetime.now().strftime("%d-%b-%Y at %I:%M%p")
            print(f"{current_time} - Error in HTTP request: {e}")
            logging.error(f"Error in HTTP request: {e}")
            return None

def monitor_stocks():
    global previous_stocks

    while True:
        all_stocks = get_all_stocks()
        if all_stocks is not None:
            added_stocks = all_stocks[~all_stocks['nsecode'].isin(previous_stocks)]

            if not added_stocks.empty:
                current_time = datetime.now().strftime("%d-%b-%Y at %I:%M%p")
                print(f"{current_time} - New stocks found: \n{added_stocks}")
                logging.info(f"New stocks found: \n{added_stocks}")

                for _, stock in added_stocks.iterrows():
                    nse_code = stock['nsecode']
                    price = stock['close']
                    message = f"New stock found:-\nWhen: {current_time}\n\n '{nse_code}' - {price}"
                    send_telegram_message(message)
                    print(f"{current_time} - Alert sent for: {nse_code} at {price}")
                    logging.info(f"Alert sent for: {nse_code} at {price}")

            # Update the list of previously seen stocks
            previous_stocks = set(all_stocks['nsecode'])

        time.sleep(10)
        
    print(f"{current_time} - STOPED")
    
# Start monitoring
try:
    monitor_stocks()
except KeyboardInterrupt:
    current_time = datetime.now().strftime("%d-%b-%Y at %I:%M%p")
    print(f"{current_time} - Monitoring stopped manually.")
    logging.info("Monitoring stopped manually.")
