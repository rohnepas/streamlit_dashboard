# BTC Strategy Dashboard

A Streamlit dashboard that gives an at-a-glance overview of Bitcoin market conditions using a fixed set of independent buy and sell signals. It does not make decisions or give financial advice. It shows each signal's condition, its current value, and how far the market would have to move to trigger it. The UI language is German.

## The 4+4 signal system

Four independent buy signals and four independent sell signals. There is no combined score and no automatic recommendation, each signal is shown on its own tile.

**Buy signals**

| Signal | Condition |
|---|---|
| MM < Q10 | Mayer Multiple below its rolling 10% quantile |
| F&G < 25 | Fear & Greed Index in extreme fear |
| Cycle > 18 mo. | More than 18 months since the last halving (accumulation phase) |
| Price near CVDD | BTC price at or below the CVDD floor value |

**Sell signals**

| Signal | Condition |
|---|---|
| MM > Q90 | Mayer Multiple above its rolling 90% quantile |
| F&G > 75 | Fear & Greed Index in extreme greed |
| MVRV-Z >= 5 | On-chain unrealized profits at historic top levels |
| Cycle < 18 mo. | Less than 18 months since the last halving (typical top window) |

Each inactive tile also shows the required move to trigger, for example "price must fall another 13% (to $53,000)". For MVRV-Z the price target is derived from current market cap and realized cap.

The dashboard also shows halving cycle progress and four interactive Plotly charts: BTC price (log scale) with buy/sell zones, Mayer Multiple with rolling quantiles, Fear & Greed history, and the current MVRV-Z value as a meter.

## Data sources

| Data | Source | Notes |
|---|---|---|
| BTC price history | Yahoo Finance (yfinance) | |
| Fear & Greed Index | api.alternative.me | |
| MVRV-Z, market cap, realized cap | bitcoin-data.com | Free tier, 10 requests/hour, cached 24h |
| CVDD | axeladlerjr.com | Unofficial source, scraped from public page, clearly marked in the UI. bitcoin-data.com's CVDD endpoint was found to deviate strongly from independent sources and is not used. |

All on-chain values are cached for 24 hours server-side, so page reloads do not trigger new API requests.

## Installation

```sh
git clone https://github.com/rohnepas/streamlit_dashboard.git
cd streamlit_dashboard
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

## Usage

```sh
streamlit run main.py
```

All thresholds live in `config.py` under `STRATEGY_CONFIG`.

## Telegram notifications (optional)

`scheduler.py` sends the current signal to a Telegram chat. It runs twice daily via GitHub Actions (`.github/workflows/scheduler.yml`) using repository secrets, no credentials are stored in the code.

For local use, copy `.env.example` to `.env` and fill in your own values:

```
BOT_ID=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
```

Create a bot via [@BotFather](https://t.me/botfather) on Telegram. The `.env` file is gitignored.

## Project structure

```
main.py              entry point
ui_components.py     all UI, tiles and Plotly charts
strategy.py          signal logic and price target derivations
data_processing.py   data fetching, merging, on-chain sources
helpers.py           thin wrapper around data fetching
config.py            all configuration and thresholds
scheduler.py         Telegram notification job (GitHub Actions)
telegrambot.py       Telegram API wrapper
cleanup_old_runs.py  deletes old workflow runs (GitHub Actions)
```

## Disclaimer

This tool is a personal market overview. It is not financial advice. The signals are based on historical patterns that may not repeat, and one data source (CVDD) is unofficial and unverified.

## License

MIT, see [LICENSE](LICENSE).
