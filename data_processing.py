import logging
import requests
import pandas as pd
import yfinance as yf

from config import TICKER_SYMBOLS, INDICATORS, TIME_PERIODS, create_fear_and_greed_index_url

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_fear_and_greed_data():
    """
    Retrieves and processes the Fear and Greed Index data.
    Returns:
    Tuple: A tuple containing a boolean, a message, and a DataFrame.
    """
    url = create_fear_and_greed_index_url(TIME_PERIODS.get("DAYS_PERIODE"))
    try:
        logging.info("Fetching Fear and Greed Index data from URL: %s", url)
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

        logging.info("Parsing JSON response for Fear and Greed Index data.")
        data_json = response.json()
        df_fear_and_greed = pd.DataFrame(data_json["data"])

        df_fear_and_greed["timestamp"] = pd.to_datetime(df_fear_and_greed["timestamp"].astype(int), unit="s")
        df_fear_and_greed.rename(columns={"timestamp": "date"}, inplace=True)

        logging.info("Fear and Greed Index data successfully processed.")
        return True, "Fear and greed data successfully fetched!", df_fear_and_greed

    except requests.RequestException as e:
        logging.exception("Failed to fetch Fear and Greed data: %s", e)
        return False, "Error fetching fear and greed data!", None

def process_historical_data():
    """
    Retrieves historical Bitcoin price data.
    Returns:
    Tuple: A tuple containing a boolean, a message, and a DataFrame.
    """
    try:
        tickerSymbol = TICKER_SYMBOLS.get("BTC")
        logging.info("Fetching historical BTC price data for ticker symbol: %s", tickerSymbol)

        tickerData = yf.Ticker(tickerSymbol)
        df_historical_btc = tickerData.history(period=f"{TIME_PERIODS.get('DAYS_PERIODE')}d")

        logging.info("Historical BTC price data successfully fetched.")
        return True, "Historical BTC prices successfully fetched!", df_historical_btc

    except Exception as e:
        logging.exception("Failed to fetch historical BTC price data: %s", e)
        return False, f"Error fetching historical data: {e}", None

def process_and_merge_data(df_historical_btc, df_fear_and_greed, lower_mm_quantil, upper_mm_quantil, lower_fear_and_greed, upper_fear_and_greed, bigger_sma, smaller_sma):
    """
    Processes and merges two dataframes: historical Bitcoin prices and Fear and Greed Index data.
    Returns:
    DataFrame: A merged and processed DataFrame with added indicators and trading signals.
    """
    try:
        logging.info("Processing and merging historical BTC and Fear and Greed data.")

        df_historical_btc = df_historical_btc.reset_index()
        df_historical_btc.columns = [c.lower() for c in df_historical_btc.columns]
        df_historical_btc["date"] = df_historical_btc["date"].dt.tz_localize(None)
        df_historical_btc = df_historical_btc.drop(["dividends", "stock splits"], axis=1)

        df_historical_btc[f"{bigger_sma}_day_ma"] = df_historical_btc["close"].rolling(window=bigger_sma).mean()
        df_historical_btc[f"{smaller_sma}_day_ma"] = df_historical_btc["close"].rolling(window=smaller_sma).mean()
        df_historical_btc["200_days_sma_for_mm"] = df_historical_btc["close"].rolling(window=200).mean()
        df_historical_btc["mayer_multiple"] = df_historical_btc["close"] / df_historical_btc["200_days_sma_for_mm"]

        df_historical_btc.dropna(subset=["200_days_sma_for_mm"], inplace=True)
        df_fear_and_greed = df_fear_and_greed.drop(["time_until_update"], axis=1)
        df_fear_and_greed["value"] = pd.to_numeric(df_fear_and_greed["value"], errors="coerce")

        df_merged = pd.merge(df_historical_btc, df_fear_and_greed, left_on="date", right_on="date", how="left")
        lower_quantile = df_historical_btc["mayer_multiple"].quantile(lower_mm_quantil)
        upper_quantile = df_historical_btc["mayer_multiple"].quantile(upper_mm_quantil)

        df_merged[f"{lower_mm_quantil}_quantile"] = lower_quantile
        df_merged[f"{upper_mm_quantil}_quantile"] = upper_quantile

        def determine_signal(row):
            lower_quantile_key = f"{lower_mm_quantil}_quantile"
            upper_quantile_key = f"{upper_mm_quantil}_quantile"
            if row["mayer_multiple"] < row[lower_quantile_key] and row["value"] <= lower_fear_and_greed:
                return "buy"
            elif (row["mayer_multiple"] > row[upper_quantile_key] and row["value"] >= upper_fear_and_greed):
                return "sell"
            else:
                return "hold"

        df_merged["signal"] = df_merged.apply(determine_signal, axis=1)
        df_merged.set_index("date", inplace=True)

        logging.info("Data merged and processed successfully.")
        return df_merged

    except Exception as e:
        logging.exception("Failed to process and merge data: %s", e)
        return None

def calculate_sell_and_buy_history(df_merged):
    """
    Filters and processes the merged DataFrame to create a history of buy and sell trades.
    Returns:
    Tuple: A tuple containing a boolean, a message, and a DataFrame.
    """
    try:
        logging.info("Calculating buy and sell history.")
        filtered_df = df_merged[df_merged["signal"].isin(["buy", "sell"])]
        status = "sell"
        rows_to_add = []

        for index, row in filtered_df.iterrows():
            if status == "sell" and row["signal"] == "buy":
                status = "buy"
                rows_to_add.append(row)
            elif status == "buy" and row["signal"] == "sell":
                status = "sell"
                rows_to_add.append(row)

        sell_and_buy_history = pd.DataFrame(rows_to_add)

        if sell_and_buy_history.empty:
            logging.info("No trades were triggered with the given parameters.")
            return False, "No trades were triggered with the given parameters", None
        else:
            sell_and_buy_history = sell_and_buy_history.drop(
                ["open", "high", "low", "200_days_sma_for_mm", f"{INDICATORS.get('BIGGER_SMA')}_day_ma", f"{INDICATORS.get('SMALLER_SMA')}_day_ma", "value"], axis=1
            )
            logging.info("Trades were identified in the given time frame.")
            return True, "Trades were identified in the given time frame", sell_and_buy_history

    except Exception as e:
        logging.exception("Failed to calculate buy and sell history: %s", e)
        return False, "Error calculating buy and sell history", None

def classify_fear_and_greed(value):
    if 0 <= value <= 25:
        return "Extreme Fear"
    elif 26 <= value <= 46:
        return "Fear"
    elif 47 <= value <= 54:
        return "Neutral"
    elif 55 <= value <= 75:
        return "Greed"
    elif 76 <= value <= 100:
        return "Extreme Greed"
    else:
        return "Invalid Value"
