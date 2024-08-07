from config import setup_page_config, INDICATORS
from ui_components import loadUiComponents
import streamlit as st
from data_processing import calculate_sell_and_buy_history
from helpers import fetch_and_process_data

def main():
    setup_page_config()  # Configure the Streamlit page
    loadUiComponents()  # Load UI components

def fetch_and_process_data_dashboard():
    return fetch_and_process_data()

def create_buy_and_sell_history(df_merged):
    df_sell_and_buy_history = calculate_sell_and_buy_history(df_merged)
    st.dataframe(df_sell_and_buy_history)
    return df_sell_and_buy_history

if __name__ == "__main__":
    main()  # Run the main function
