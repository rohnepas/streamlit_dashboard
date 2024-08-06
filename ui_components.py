import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from data_processing import calculate_sell_and_buy_history, classify_fear_and_greed
from config import INDICATORS, DAYS_FOR_METRICS

def loadUiComponents():
    from main import fetch_and_process_data_dashboard
    data_merged, message, df_merged = fetch_and_process_data_dashboard()
    if data_merged:
        st.success(message)
        show_metrics(df_merged, DAYS_FOR_METRICS)
        plot_data(df_merged)
        show_sell_and_buy_history(df_merged)
    else:
        st.warning(message)
        

def show_sell_and_buy_history(df_merged):
    st.subheader("Historical buy and sell signals :sunglasses:")
    success, message, signals_df = calculate_sell_and_buy_history(df_merged)
    
    if success: 
        st.dataframe(signals_df)
    else:
        st.warning("historical signals can not be displayed")
    


def plot_data(df_merged):
    """
    This function visualizes various financial indicators for Bitcoin (BTC) market analysis in a comprehensive multi-part figure. 
    It consists of three subplots:
    1. The primary chart displays BTC closing prices, Simple Moving Averages (SMAs), and Bollinger Bands, highlighting market trends and volatility.
    2. The second chart focuses on the Mayer Multiple, plotting it against specific quantiles to identify overbought or oversold conditions.
    3. The third chart presents the Fear and Greed Index, offering insights into market sentiment.
    
    The method employs pandas DataFrame operations for calculations and matplotlib for plotting.

    Parameters:
    df_merged (DataFrame): A pandas DataFrame containing columns for BTC closing prices, Mayer Multiple, and Fear and Greed Index values.

    Returns:
    None: This function renders the plots directly without returning any value.
    """
    
    
    # Create the figure and subplots with three rows
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 18), gridspec_kw={"height_ratios": [3, 1, 2]})

    # Plot BTC close, SMA100, SMA200, and Bollinger Bands in the main chart
    ax1.plot(df_merged["close"], label="close")
    ax1.plot(df_merged[f"{INDICATORS.get("SMALLER_SMA")}_day_ma"], label=f"{INDICATORS.get("SMALLER_SMA")}_SMA")
    ax1.plot(df_merged[f"{INDICATORS.get("BIGGER_SMA")}_day_ma"], label=f"{INDICATORS.get("BIGGER_SMA")}_SMA")
    ax1.legend()
    ax1.set_title("BTC Closing Prices, SMAs and Bollinger Bands")

    # Calculating the quantiles for Mayer Multiple
    lower_quantile = df_merged["mayer_multiple"].quantile(INDICATORS.get("LOWER_MM_QUANTIL"))
    upper_quantile = df_merged["mayer_multiple"].quantile(INDICATORS.get("UPPER_MM_QUANTIL"))
        
     # Plot Mayer Multiple in the second subchart
    ax2.plot(df_merged["mayer_multiple"], label="Mayer Multiple", color="orange")
    ax2.axhline(y=lower_quantile, color="blue", linestyle="--", label=f"{INDICATORS.get("LOWER_MM_QUANTIL")} quantil")
    ax2.axhline(y=upper_quantile, color="purple", linestyle="--", label=f"{INDICATORS.get("UPPER_MM_QUANTIL")} quantil")

    # Fill between Mayer Multiple and lower/upper quantile lines
    ax2.fill_between(df_merged.index, df_merged["mayer_multiple"], lower_quantile, 
                    where=(df_merged["mayer_multiple"] < lower_quantile), 
                    color="red", alpha=0.5, interpolate=True)

    ax2.fill_between(df_merged.index, df_merged["mayer_multiple"], upper_quantile, 
                    where=(df_merged["mayer_multiple"] > upper_quantile), 
                    color="green", alpha=0.5, interpolate=True)

    ax2.legend()
    ax2.set_title("Mayer Multiple")

    # Plot Fear and Greed Index in the third subchart
    ax3.plot(df_merged["value"], label="Fear and Greed", color="orange")
    ax3.axhline(y=INDICATORS.get("LOWER_FEAR_AND_GREED"), color="blue", linestyle="--", label=f"{classify_fear_and_greed(INDICATORS.get("LOWER_FEAR_AND_GREED"))} ({INDICATORS.get("LOWER_FEAR_AND_GREED")})")
    ax3.axhline(y=INDICATORS.get("UPPER_FEAR_AND_GREED"), color="purple", linestyle="--", label=f"{classify_fear_and_greed(INDICATORS.get("UPPER_FEAR_AND_GREED"))} ({INDICATORS.get("UPPER_FEAR_AND_GREED")})")
    ax3.legend()
    ax3.set_title("Fear and Greed Index")

    success, message, signals_df = calculate_sell_and_buy_history(df_merged)

    marker_size = 80

    if success and signals_df is not None:
        for idx, row in signals_df.iterrows():
            # Extracting values for each subplot
            close_value = df_merged.at[idx, 'close']
            mayer_value = df_merged.at[idx, 'mayer_multiple']
            fear_and_greed_value = df_merged.at[idx, 'value']

            # Plot buy signals
            if row['signal'] == 'buy':
                ax1.scatter(idx, close_value, color='green', marker='^', s=marker_size, zorder=3)
                ax2.scatter(idx, mayer_value, color='green', marker='^', s=marker_size, zorder=3)
                ax3.scatter(idx, fear_and_greed_value, color='green', marker='^', s=marker_size, zorder=3)

            # Plot sell signals
            elif row['signal'] == 'sell':
                ax1.scatter(idx, close_value, color='red', marker='v', s=marker_size, zorder=3)
                ax2.scatter(idx, mayer_value, color='red', marker='v', s=marker_size, zorder=3)
                ax3.scatter(idx, fear_and_greed_value, color='red', marker='v', s=marker_size, zorder=3)

    # Adding buy and sell signal legends separately
    ax1.scatter([], [], color='green', marker='^', label='Buy Signal', s=60)
    ax1.scatter([], [], color='red', marker='v', label='Sell Signal', s=60)
    
    # Update legends for all subplots
    ax1.legend()
    ax2.legend()
    ax3.legend()


    st.pyplot(fig)

def show_metrics(df, days):
    st.divider()
    display_recommentation(df["signal"].iloc[-1])
    with st.container():
        col1, col2, col3 = st.columns(3)

        # Check if enough data is available
        if days < len(df):
            # Calculations for BTC closing price
            today_price = df["close"].iloc[-1]
            historical_price = df["close"].iloc[-1 - days]
            difference = today_price - historical_price
            percent_change = (difference / historical_price) * 100

            with col1:
                st.metric(label=f"{days}-Day BTC Closing Price", value=f"{today_price:.2f}", delta=f"{difference:.2f} ({percent_change:.2f}%)")

            # Calculations for Mayer Multiple
            last_mayer = df["mayer_multiple"].iloc[-1]
            historical_mayer = df["mayer_multiple"].iloc[-1 - days]
            difference_mayer = last_mayer - historical_mayer
            percent_change_mayer = (difference_mayer / historical_mayer) * 100

            with col2:
                st.metric(label=f"{days}-Day Mayer Multiple", value=f"{last_mayer:.2f}", delta=f"{difference_mayer:.2f} ({percent_change_mayer:.2f}%)")

            # Calculations for Fear and Greed Index
            last_value = df["value"].iloc[-1]
            historical_value = df["value"].iloc[-1 - days]
            difference_fear_greed = last_value - historical_value
            percent_change_fear_greed = (difference_fear_greed / historical_value) * 100

            with col3:
                st.metric(label=f"{days}-Day Fear and Greed", value=f"{last_value:.2f}", delta=f"{difference_fear_greed:.2f} ({percent_change_fear_greed:.2f}%)")
        else:
            st.error("Not enough data available for the specified period.")
    
    
    
    st.markdown("""
        <span style="color:green; font-weight:bold">Buy</span> if Mayer Multiple is below 10 % quantile and Fear and Greed has the classification of "Extreme Fear". 
        <span style="color:red; font-weight:bold">Sell</span> if Mayer Multiple is above 90 % quantile and Fear and Greed has the classification of "Extreme Greed".<br>
        <span> The timeframe between the year 2000 (or before) and today is relevant for the strategy.</span>
        """, unsafe_allow_html=True)
    st.divider()

def display_recommentation(signal):
    if signal == "buy":
        st.markdown("<h1 style='color:green;'>Buy</h1>", unsafe_allow_html=True)
    elif signal == "sell":
        st.markdown("<h1 style='color:red;'>Sell</h1>", unsafe_allow_html=True)
    elif signal == "hold":
        st.markdown("<h1 style='color:blue;'>Hold</h1>", unsafe_allow_html=True)

