import logging
import re
import requests
import pandas as pd
import yfinance as yf
import streamlit as st

from config import TICKER_SYMBOLS, INDICATORS, TIME_PERIODS, STRATEGY_CONFIG, BITCOIN_HALVINGS, create_fear_and_greed_index_url

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@st.cache_data(ttl=3600)  # Cache for 1 hour
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

@st.cache_data(ttl=3600)  # Cache for 1 hour
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

        # Use 'max' period to get all available data instead of specifying days
        # yfinance doesn't support very long periods like 2000d
        df_historical_btc = tickerData.history(period="max")

        if df_historical_btc.empty:
            logging.error("No historical BTC price data retrieved.")
            return False, "No historical BTC price data available!", None

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

        df_merged = pd.merge(df_historical_btc, df_fear_and_greed, left_on="date", right_on="date", how="inner")
        lower_quantile = df_historical_btc["mayer_multiple"].quantile(lower_mm_quantil)
        upper_quantile = df_historical_btc["mayer_multiple"].quantile(upper_mm_quantil)

        df_merged[f"{lower_mm_quantil}_quantile"] = lower_quantile
        df_merged[f"{upper_mm_quantil}_quantile"] = upper_quantile

        # Q90 expanding (Verkaufssignal: rollierendes 90%-Quantil)
        df_merged['q90_expanding'] = df_merged['mayer_multiple'].expanding(
            min_periods=STRATEGY_CONFIG['Q_MIN_PERIODS']
        ).quantile(0.9)

        # Q10 expanding (Kaufsignal: rollierendes 10%-Quantil)
        df_merged['q10_expanding'] = df_merged['mayer_multiple'].expanding(
            min_periods=STRATEGY_CONFIG['Q_MIN_PERIODS']
        ).quantile(0.1)

        # Preislevels für Chart-Visualisierung
        df_merged['q90_price_level'] = df_merged['200_days_sma_for_mm'] * df_merged['q90_expanding']
        df_merged['q10_price_level'] = df_merged['200_days_sma_for_mm'] * df_merged['q10_expanding']

        def months_since_halving_for_date(check_date):
            """Berechnet Monate seit letztem Halving für ein bestimmtes Datum"""
            check_date = pd.Timestamp(check_date)
            last_halving = None
            for halving_data in BITCOIN_HALVINGS.values():
                halving_date = pd.Timestamp(halving_data["date"])
                if halving_date <= check_date:
                    if last_halving is None or halving_date > last_halving:
                        last_halving = halving_date
            if last_halving is None:
                return None
            return (check_date - last_halving).days / 30.44

        def is_in_buy_block_window(check_date):
            """Prüft ob Datum in Bull-Phase (0-18 Mo. nach Halving) liegt"""
            months = months_since_halving_for_date(check_date)
            if months is None:
                return False  # Vor erstem Halving - erlauben
            buy_block_months = STRATEGY_CONFIG.get('BUY_BLOCK_MONTHS', 18)
            return months < buy_block_months

        def determine_signal(row):
            # 4+4 Strategie: Kauf wenn MM < Q10, Verkauf wenn MM > Q90 und FG > Schwelle
            q10 = row.get("q10_expanding")
            q90 = row.get("q90_expanding")
            if pd.notna(q10) and row["mayer_multiple"] < q10:
                if is_in_buy_block_window(row["date"]):
                    return "hold"
                return "buy"
            elif (pd.notna(q90) and
                  row["mayer_multiple"] > q90 and
                  row["value"] >= STRATEGY_CONFIG['SELL_FG_THRESHOLD']):
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

def calculate_sell_and_buy_history(df_merged, signal_column="signal"):
    """
    Filters and processes the merged DataFrame to create a history of buy and sell trades.

    WICHTIG: Verkauf nur wenn Position im Plus!
    Diese Funktion prüft, ob der Verkaufspreis > Kaufpreis ist.
    Falls nicht, wird das Verkaufssignal ignoriert und auf einen profitablen Verkauf gewartet.

    Args:
        df_merged: The merged DataFrame
        signal_column: Which signal column to use ('signal', 'signal_fixed', or 'signal_q90')
    Returns:
        Tuple: A tuple containing a boolean, a message, and a DataFrame.
    """
    try:
        logging.info(f"Calculating buy and sell history using {signal_column}.")
        filtered_df = df_merged[df_merged[signal_column].isin(["buy", "sell"])].copy()
        status = "sell"
        buy_price = None
        rows_to_add = []

        for index, row in filtered_df.iterrows():
            if status == "sell" and row[signal_column] == "buy":
                status = "buy"
                buy_price = row["close"]  # Kaufpreis merken
                row_copy = row.copy()
                row_copy['signal'] = row[signal_column]  # Normalize to 'signal'
                rows_to_add.append(row_copy)
            elif status == "buy" and row[signal_column] == "sell":
                # P&L Check: Nur verkaufen wenn Position im Plus!
                current_price = row["close"]
                if buy_price is not None and current_price > buy_price:
                    status = "sell"
                    buy_price = None  # Reset
                    row_copy = row.copy()
                    row_copy['signal'] = row[signal_column]
                    rows_to_add.append(row_copy)
                # Else: Verkaufssignal ignorieren, warte auf profitablen Verkauf

        sell_and_buy_history = pd.DataFrame(rows_to_add)

        if sell_and_buy_history.empty:
            logging.info("No trades were triggered with the given parameters.")
            return False, "No trades were triggered with the given parameters", None
        else:
            # Nur Spalten droppen die existieren
            cols_to_drop = ["open", "high", "low", "200_days_sma_for_mm",
                           f"{INDICATORS.get('BIGGER_SMA')}_day_ma",
                           f"{INDICATORS.get('SMALLER_SMA')}_day_ma", "value"]
            cols_to_drop = [c for c in cols_to_drop if c in sell_and_buy_history.columns]
            if cols_to_drop:
                sell_and_buy_history = sell_and_buy_history.drop(cols_to_drop, axis=1)
            logging.info("Trades were identified in the given time frame.")
            return True, "Trades were identified in the given time frame", sell_and_buy_history

    except Exception as e:
        logging.exception("Failed to calculate buy and sell history: %s", e)
        return False, "Error calculating buy and sell history", None

def fetch_cvdd_from_axeladlerjr():
    """
    Fetches CVDD from axeladlerjr.com (statisch im HTML, kein JavaScript noetig).

    Grund: bitcoin-data.com liefert fuer CVDD einen Wert, der um Faktor 3.3 von
    unabhaengigen Quellen abweicht (verifiziert gegen den echten BTC-Kurs am selben
    Tag). bitcoinmagazinepro.com (Original-Quelle der zugrunde liegenden Studie)
    gibt den Wert nur ueber ein JavaScript-Chart preis, nicht ohne echten Browser
    auslesbar, und die API dafuer ist kostenpflichtig.

    ACHTUNG: axeladlerjr.com ist eine private Seite, keine offizielle API. Der Wert
    konnte nicht direkt gegen bitcoinmagazinepro.com verifiziert werden. Aendert die
    Seite ihren Aufbau oder Wortlaut, kann diese Extraktion stillschweigend
    fehlschlagen. In dem Fall liefert die Funktion None, kein falscher Wert.

    Returns: cvdd_current, float oder None bei Fehler.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get('https://axeladlerjr.com/charts/bitcoin-cvdd/', headers=headers, timeout=15)
        resp.raise_for_status()
        plain_text = re.sub(r'<[^>]+>', '', resp.text)
        match = re.search(r'CVDD is\s*\$?([\d,]+)', plain_text)
        if match:
            return float(match.group(1).replace(',', ''))
        logging.warning("CVDD-Muster auf axeladlerjr.com nicht gefunden, Seite hat sich moeglicherweise geaendert.")
        return None
    except Exception as e:
        logging.warning("Failed to fetch CVDD from axeladlerjr.com: %s", e)
        return None


@st.cache_data(ttl=86400)  # 24h Cache, Daten aktualisieren sich ohnehin nur 1x/Tag
def fetch_onchain_data():
    """
    Fetches current on-chain data: CVDD (axeladlerjr.com, siehe Warnhinweis in
    fetch_cvdd_from_axeladlerjr), MVRV-Z, Marktkapitalisierung und realisierte
    Kapitalisierung (alle drei von bitcoin-data.com, gegen unabhaengige Quellen
    verifiziert und stimmen gut ueberein).

    Markt- und realisierte Kapitalisierung werden zusaetzlich geholt, damit
    strategy.py daraus den Zielpreis fuer das MVRV-Z Verkaufssignal herleiten kann
    (wie weit muesste der Preis steigen, damit MVRV-Z >= 5 wird).

    Returns: (cvdd_current, mvrv_current, market_cap_current, realized_cap_current),
    jeweils float oder None bei Fehler.
    """
    cvdd_current = fetch_cvdd_from_axeladlerjr()
    mvrv_current = None
    market_cap_current = None
    realized_cap_current = None

    try:
        mvrv_resp = requests.get("https://bitcoin-data.com/v1/mvrv-zscore/last", timeout=10)
        mvrv_resp.raise_for_status()
        mvrv_current = mvrv_resp.json().get('mvrvZscore')
    except Exception as e:
        logging.warning("Failed to fetch MVRV-Z data: %s", e)

    try:
        mc_resp = requests.get("https://bitcoin-data.com/v1/market-cap/last", timeout=10)
        mc_resp.raise_for_status()
        market_cap_current = mc_resp.json().get('marketCap')
    except Exception as e:
        logging.warning("Failed to fetch market cap data: %s", e)

    try:
        rc_resp = requests.get("https://bitcoin-data.com/v1/realized-cap/last", timeout=10)
        rc_resp.raise_for_status()
        realized_cap_current = rc_resp.json().get('realizedCap')
    except Exception as e:
        logging.warning("Failed to fetch realized cap data: %s", e)

    if mvrv_current is not None:
        mvrv_current = float(mvrv_current)
    if market_cap_current is not None:
        market_cap_current = float(market_cap_current)
    if realized_cap_current is not None:
        realized_cap_current = float(realized_cap_current)

    return cvdd_current, mvrv_current, market_cap_current, realized_cap_current


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
