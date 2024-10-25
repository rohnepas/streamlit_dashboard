import logging
from config import INDICATORS
from data_processing import process_fear_and_greed_data, process_historical_data, process_and_merge_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_and_process_data():
    """
    This function is responsible for fetching and processing Bitcoin (BTC) market data. It performs two main tasks:
    1. Fetching Fear and Greed Index Data.
    2. Fetching Historical BTC Data.
    If both data types are successfully fetched, the method merges and processes these datasets.
    Returns:
    - On successful fetching and processing: A tuple (True, combined success message, merged DataFrame)
    - On failure to retrieve data: A tuple (False, combined error message, None)
    """
    try:
        logging.info("Fetching Fear and Greed Index data.")
        fear_and_greed_fetched, fear_and_greed_message, df_fear_and_greed = process_fear_and_greed_data()
        logging.info(fear_and_greed_message)

        logging.info("Fetching Historical BTC data.")
        historical_data_fetched, historical_data_message, df_historical_btc = process_historical_data()
        logging.info(historical_data_message)

        if fear_and_greed_fetched and historical_data_fetched:
            logging.info("Merging and processing fetched data.")
            df_merged = process_and_merge_data(
                df_historical_btc, df_fear_and_greed,
                INDICATORS.get("LOWER_MM_QUANTIL"), INDICATORS.get("UPPER_MM_QUANTIL"),
                INDICATORS.get("LOWER_FEAR_AND_GREED"), INDICATORS.get("UPPER_FEAR_AND_GREED"),
                INDICATORS.get("BIGGER_SMA"), INDICATORS.get("SMALLER_SMA")
            )
            logging.info("Data processed successfully.")
            return True, "Data processed successfully", df_merged
        else:
            logging.error("Failed to process data due to unsuccessful fetch operations.")
            return False, "Data processing failed", None

    except Exception as e:
        logging.exception("An error occurred during data fetching and processing: %s", e)
        return False, "Data processing failed due to an error", None
