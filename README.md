# BTC Trading Dashboard

BTC Trading Dashboard is a Streamlit application that provides insights into Bitcoin trading signals, market data, and sends notifications via Telegram.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Scheduler](#scheduler)
- [License](#license)

## Introduction

This project aims to provide a comprehensive dashboard for monitoring Bitcoin trading signals and market data. The dashboard takes into account the Mayer Multiple as well as the Bitcoin Fear and Greed Index. It also includes functionality to send trading signals to a Telegram bot.

### Mayer Multiple

The Mayer Multiple is a ratio that compares the current price of Bitcoin to its 200-day moving average. It is used to identify potential buying or selling opportunities based on historical trends. A Mayer Multiple above 2.4 indicates that Bitcoin is potentially overbought, while a value below 0.8 suggests it might be oversold. In this dashboard, lines are drawn for buy and sell signals based on other thresholds.

### Bitcoin Fear and Greed Index

The Bitcoin Fear and Greed Index is a sentiment analysis tool that aggregates various data sources to gauge the overall market sentiment towards Bitcoin. The index ranges from 0 to 100, with lower values indicating fear and higher values indicating greed. This metric helps to understand the emotional state of the market.

## Features

- Display Bitcoin trading signals.
- Show historical market data.
- Fear and Greed Index integration.
- Mayer Multiple analysis.
- Send daily updates to Telegram.

## Installation

To get started with this project, follow these steps:

1. Clone the repository:
```sh
git clone https://github.com/yourusername/btc-trading-dashboard.git
cd btc-trading-dashboard
```

2. Create and activate a virtual environment:
```sh
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install the dependencies:
```sh
pip install -r requirements.txt
```

## Configuration
### Streamlit page configuration
```sh
PAGE_CONFIG = {
    "page_title": "Strategy Dashboard",
    "page_icon": "🧊",
    "layout": "centered",
    "initial_sidebar_state": "expanded",
    "menu_items": {
        "About": "# Investment Dashboard"
    }
}

# Time periods configuration
TIME_PERIODS = {
    "DAYS_PERIODE" : 2000,
}

# Indicators for the strategy (do usually not change)
INDICATORS = {
    "UPPER_MM_QUANTIL" : 0.90,
    "LOWER_MM_QUANTIL" : 0.10,
    "UPPER_FEAR_AND_GREED" : 76,
    "LOWER_FEAR_AND_GREED" : 25,  
    "BIGGER_SMA": 200,
    "SMALLER_SMA" : 100
}

# Ticker symbols
TICKER_SYMBOLS = {
    "BTC": "BTC-USD"
}

TELEGRAM = {
    "SEND_MESSAGE" : True
}

# Days for metrics
DAYS_FOR_METRICS = 1

# Function to set up Streamlit page configuration
def setup_page_config():
    import streamlit as st
    st.set_page_config(**PAGE_CONFIG)

# Function to create the URL to retrieve Fear and Greed data
def create_fear_and_greed_index_url(days):
    return f"https://api.alternative.me/fng/?limit={days}"
```

You will also need to add your Telegram bot and chat IDs to the environment variables:
```sh
export BOT_ID='your-telegram-bot-id'
export CHAT_ID='your-telegram-chat-id'
```


## Usage
```sh
streamlit run main.py
```

## Sheduler
```sh
name: Run scheduler script

on:
  push:
    branches:
      - main  # Trigger on push to main branch
  schedule:
    - cron: '0 7 * * *'  # Run daily at 08:00 AM Zurich time (07:00 AM UTC)
    - cron: '0 16 * * *'  # Run daily at 05:00 PM Zurich time (04:00 PM UTC)
  workflow_dispatch:  # Allow manual triggering of the workflow

jobs:
  run-script:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'  # Specify Python version 3.9

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run scheduler script
        env:
          BOT_ID: ${{ secrets.BOT_ID }}
          CHAT_ID: ${{ secrets.CHAT_ID }}
        run: |
          python scheduler.py

  cleanup:
    runs-on: ubuntu-latest
    needs: run-script

    steps:
      - name: Checkout repository
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Cleanup old workflow runs
        env:
          PERSONAL_ACCESS_TOKEN: ${{ secrets.PERSONAL_ACCESS_TOKEN }}  # Use the new secret name
        run: |
          python cleanup_old_runs.py
```
## License
This project is licensed under the MIT License. See the LICENSE file for details.
