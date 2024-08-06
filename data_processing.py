import requests
import pandas as pd
import yfinance as yf

from config import TICKER_SYMBOLS, INDICATORS, TIME_PERIODS, create_fear_and_greed_index_url


def process_fear_and_greed_data():
    """
    Retrieves and processes the Fear and Greed Index data.
    This function does not take any parameters. It uses the global variable TIME_PERIODS to determine the number of days for which the Fear and Greed Index data is to be fetched.
    Operations performed:
    - Constructs the API URL using the create_fear_and_greed_index_url function with the specified time period.
    - Sends an HTTP request to the constructed URL to fetch the Fear and Greed Index data.
    - Parses the JSON response and converts it into a Pandas DataFrame.
    - Converts the "timestamp" column from integer to datetime format and renames it to "date" for consistency.
    Returns:
    Tuple: A tuple containing a boolean, a message, and a DataFrame. 
    - The boolean is True if data fetching is successful, False otherwise.
    - The message is a success message if data is fetched successfully, or an error message detailing the encountered request exception.
    - The DataFrame contains the processed Fear and Greed Index data if successful; otherwise, it"s None.
    """
    url = create_fear_and_greed_index_url(TIME_PERIODS.get("DAYS_PERIODE"))
    try:   
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code

        # Parse the JSON data
        data_json = response.json()
        df_fear_and_greed = pd.DataFrame(data_json["data"])

        # Ensure the "timestamp" column is integer before converting to datetime
        df_fear_and_greed["timestamp"] = pd.to_datetime(df_fear_and_greed["timestamp"].astype(int), unit="s")
        df_fear_and_greed.rename(columns={"timestamp": "date"}, inplace=True)

        return True, "Fear and greed data successfully fetched!", df_fear_and_greed

    except requests.RequestException as e:
        # log(f"Failed to fetch Fear and Greed data: {e}", "ERROR")
        return False, "Error fetching fear and greed data!", None


def process_historical_data():
    """
    Retrieves historical Bitcoin price data.
    This function does not take any parameters. It uses predefined global variables:
    - TICKER_SYMBOLS: A dictionary that contains ticker symbols, with "BTC" for Bitcoin.
    - TIME_PERIODS: A dictionary that contains time periods, with "DAYS_PERIODE" indicating the number of days for which historical data is fetched.
    The method performs the following operations:
    - Retrieves the ticker symbol for Bitcoin from the TICKER_SYMBOLS dictionary.
    - Uses the yfinance library to fetch historical price data for Bitcoin based on the specified time period from TIME_PERIODS.
    Returns:
    Tuple: A tuple containing a boolean, a message, and a DataFrame. 
    - The boolean is True if data fetching is successful, False otherwise.
    - The message is a success message if data is fetched successfully, or an error message detailing the exception encountered.
    - The DataFrame contains historical Bitcoin prices if successful; otherwise, it"s None.
    """
    try:

        # Define the ticker symbol
        tickerSymbol = TICKER_SYMBOLS.get("BTC")

        # Get data on this ticker
        tickerData = yf.Ticker(tickerSymbol)

        df_historical_btc = tickerData.history(period=f"{TIME_PERIODS.get('DAYS_PERIODE')}d")

        return True, "Historical btc prices successfully fetched!", df_historical_btc

    except Exception as e:
        return False, f"Error fetching historical data: {e}", None


def process_and_merge_data(df_historical_btc, df_fear_and_greed, lower_mm_quantil, upper_mm_quantil, lower_fear_and_greed, upper_fear_and_greed, bigger_sma, smaller_sma):
    """
    Processes and merges two dataframes: historical Bitcoin prices and Fear and Greed Index data.
    Parameters:
    df_historical_btc (DataFrame): A Pandas DataFrame containing historical Bitcoin prices with columns such as "close", "high", "low", etc.
    df_fear_and_greed (DataFrame): A Pandas DataFrame containing Fear and Greed Index data.
    lower_mm_quantil (float): The lower quantile value for calculating the Mayer Multiple range.
    upper_mm_quantil (float): The upper quantile value for calculating the Mayer Multiple range.
    lower_fear_and_greed (int): The lower threshold value for the Fear and Greed Index.
    upper_fear_and_greed (int): The upper threshold value for the Fear and Greed Index.
    The function performs several data processing steps:
    - Resets indices, converts date columns to proper format, and cleans up the dataframes.
    - Computes rolling averages and Mayer Multiple for Bitcoin prices.
    - Merges the processed dataframes on the "date" column.
    - Calculates quantiles for Mayer Multiple and adds them as new columns.
    - Applies a custom logic to determine "buy", "sell", or "hold" signals based on Mayer Multiple and Fear and Greed Index values.
    Returns:
    DataFrame: A merged and processed DataFrame with added indicators and trading signals.
    """

    # Reset the index to turn date into a regular column
    df_historical_btc = df_historical_btc.reset_index()

    #Lower case for backtesting
    df_historical_btc.columns = [c.lower() for c in df_historical_btc.columns]

    # Convert the timezone-aware datetime to timezone-naive
    df_historical_btc["date"] = df_historical_btc["date"].dt.tz_localize(None)

    # Delete unused columns
    df_historical_btc = df_historical_btc.drop(["dividends", "stock splits"], axis=1)

    # Add smaller SMA - see config.py
    df_historical_btc[f"{bigger_sma}_day_ma"] = df_historical_btc["close"].rolling(window=bigger_sma).mean()

    # Add bigger SMA - see config.py
    df_historical_btc[f"{smaller_sma}_day_ma"] = df_historical_btc["close"].rolling(window=smaller_sma).mean()

    # Add 200 days SMA for calculating Mayer Multiple
    df_historical_btc["200_days_sma_for_mm"] = df_historical_btc["close"].rolling(window=200).mean()

    # Add Mayer Multiple
    df_historical_btc["mayer_multiple"] = df_historical_btc["close"] / df_historical_btc["200_days_sma_for_mm"]

    # Remove rows where 200_day_MA is NaN
    df_historical_btc.dropna(subset=["200_days_sma_for_mm"], inplace=True)

    # --- Processing / expanding fear and greed dataframe --- # 

    # Delete unused columns
    df_fear_and_greed = df_fear_and_greed.drop(["time_until_update"], axis=1)

    # Convert "Value" to numeric, coercing errors to NaN
    df_fear_and_greed["value"] = pd.to_numeric(df_fear_and_greed["value"], errors="coerce")

    df_merged = pd.merge(df_historical_btc, df_fear_and_greed, left_on="date", right_on="date", how="left")

    # Calculation of the quantiles for Mayer Multiple
    lower_quantile = df_historical_btc["mayer_multiple"].quantile(lower_mm_quantil)
    upper_quantile = df_historical_btc["mayer_multiple"].quantile(upper_mm_quantil)

    # Adding the quantiles as new columns in the DataFrame
    df_merged[f"{lower_mm_quantil}_quantile"] = lower_quantile
    df_merged[f"{upper_mm_quantil}_quantile"] = upper_quantile

    # Definition of a function for the signal logic
    def determine_signal(row):
        # Dynamically construct the key strings
        lower_quantile_key = f"{lower_mm_quantil}_quantile"
        upper_quantile_key = f"{upper_mm_quantil}_quantile"

        if row["mayer_multiple"] < row[lower_quantile_key] and row["value"] <= lower_fear_and_greed:
            return "buy"
        elif (row["mayer_multiple"] > row[upper_quantile_key] and 
            row["value"] >= upper_fear_and_greed):
            return "sell"
        else:
            return "hold"

    # Applying the function to each line
    df_merged["signal"] = df_merged.apply(determine_signal, axis=1)

    df_merged.set_index("date", inplace=True)

    return df_merged


def calculate_sell_and_buy_history(df_merged):
    """
    Filters and processes the merged DataFrame to create a history of buy and sell trades.
    Parameters:
    df_merged (DataFrame): A Pandas DataFrame containing merged historical price data and Fear and Greed Index data with trading signals.
    This function:
    - Filters the DataFrame to keep only rows with 'buy' or 'sell' signals.
    - Iterates through these filtered rows to create a chronological history of trades.
    - Removes unnecessary columns from the final trade history DataFrame.
    Returns:
    Tuple: A tuple containing a boolean, a message, and a DataFrame. 
    - The boolean is True if trades were identified, False if no trades were triggered with the given parameters.
    - The message provides information about the presence or absence of trades.
    - The DataFrame contains the history of trades if any were identified; otherwise, it's None.
    """

    filtered_df = df_merged[df_merged["signal"].isin(["buy", "sell"])]

    # Initialize the status variable and a list to store the rows
    status = "sell"  # Start with "Sell" so that we look for the first "Buy"
    rows_to_add = []

    # Iterate through the filtered DataFrame and apply the logic
    for index, row in filtered_df.iterrows():
        if status == "sell" and row["signal"] == "buy":
            # Change status to "Buy" and add the row to the list
            status = "buy"
            rows_to_add.append(row)
        elif status == "buy" and row["signal"] == "sell":
            # Change status to "Sell" and add the row to the list
            status = "sell"
            rows_to_add.append(row)

    # Convert the list of rows into a DataFrame
    sell_and_buy_history = pd.DataFrame(rows_to_add)

    if sell_and_buy_history.empty:
        return False, "No trades were triggered with the given parameters", None
    else:
        # Remove unnecessary columns
        sell_and_buy_history = sell_and_buy_history.drop(["open", "high", "low", "200_days_sma_for_mm", f"{INDICATORS.get('BIGGER_SMA')}_day_ma", f"{INDICATORS.get('SMALLER_SMA')}_day_ma", "value"], axis=1)
        return True, "Trades were identified in the given time frame", sell_and_buy_history


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