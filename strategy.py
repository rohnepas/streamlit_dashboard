"""
strategy.py - Signal-Logik für BTC Dashboard (4+4 Strategie)

8 unabhängige Signale (4 Kauf, 4 Verkauf). Kein automatischer Entscheid, nur eine Übersicht.

KAUF-Signale:
- MM < Q10:        Mayer Multiple unter rollendem 10%-Quantil
- F&G < 25:        Extreme Angst (Fear & Greed < 25)
- Zyklus > 18 Mo.: Bärphase / Akkumulationsphase aktiv
- CVDD:            Preis nahe dem Coindays Destroyed Value Floor

VERKAUF-Signale:
- MM > Q90:        Mayer Multiple über rollendem 90%-Quantil
- F&G > 75:        Extreme Gier (Fear & Greed > 75)
- MVRV-Z >= 5:     On-Chain Überhitzung
- Zyklus < 18 Mo.: Bullenmarkt-Phase aktiv

CVDD kommt von axeladlerjr.com, keine offizielle API. Siehe Warnhinweis in
data_processing.fetch_cvdd_from_axeladlerjr.
"""

import pandas as pd
from datetime import datetime
from config import STRATEGY_CONFIG, BITCOIN_HALVINGS


def calculate_q90_expanding(df):
    """Berechnet rollierenden Q90 für Mayer Multiple."""
    min_periods = STRATEGY_CONFIG['Q_MIN_PERIODS']
    return df['mayer_multiple'].expanding(min_periods=min_periods).quantile(0.9)


def get_halving_info(current_date=None):
    """
    Liefert Halving-Zyklus-Information.

    Returns:
        dict mit keys: months_since_halving, last_halving_date, in_typical_top_window, halving_hint
    """
    months = months_since_last_halving(current_date)

    if months is None:
        return {
            'months_since_halving': 0,
            'last_halving_date': None,
            'in_typical_top_window': False,
            'halving_hint': 'Kein Halving-Datum verfügbar'
        }

    if current_date is None:
        current_date = pd.Timestamp.now()
    else:
        current_date = pd.Timestamp(current_date)

    last_halving_date = None
    for halving_data in BITCOIN_HALVINGS.values():
        halving_date = pd.Timestamp(halving_data["date"])
        if halving_date <= current_date:
            if last_halving_date is None or halving_date > last_halving_date:
                last_halving_date = halving_date

    in_typical_top_window = 12 <= months <= 24

    buy_block = STRATEGY_CONFIG['BUY_BLOCK_MONTHS']
    if months < buy_block:
        halving_hint = f'{months:.1f} Mo. seit Halving, Bullenmarkt-Phase (Verkaufsignale beachten)'
    else:
        halving_hint = f'{months:.1f} Mo. seit Halving, Akkumulationsphase (Kaufsignale beachten)'

    return {
        'months_since_halving': months,
        'last_halving_date': last_halving_date,
        'in_typical_top_window': in_typical_top_window,
        'halving_hint': halving_hint
    }


def _price_gap_str(target_price, current_price, direction):
    """Formatiert die nötige Preisbewegung bis zu einem Ziel-Preislevel.
    direction: 'down' (Ziel muss fallen, Kaufsignal) oder 'up' (Ziel muss steigen, Verkaufssignal)
    """
    if target_price is None or current_price is None or current_price == 0:
        return None
    pct = (target_price - current_price) / current_price * 100
    if direction == 'down':
        if pct >= 0:
            return "Signal aktiv"
        return f"Preis muss noch {abs(pct):.1f}% fallen (auf \\${target_price:,.0f})"
    else:
        if pct <= 0:
            return "Signal aktiv"
        return f"Preis muss noch {pct:.1f}% steigen (auf \\${target_price:,.0f})"


def _points_gap_str(current_value, threshold, direction, unit=""):
    """Formatiert die nötige Punkte-Bewegung bis zu einem Schwellwert.
    direction: 'down' (Wert muss fallen) oder 'up' (Wert muss steigen)
    """
    if current_value is None or threshold is None:
        return None
    if direction == 'down':
        gap = current_value - threshold
        if gap <= 0:
            return "Signal aktiv"
        return f"muss noch {gap:.1f}{unit} fallen"
    else:
        gap = threshold - current_value
        if gap <= 0:
            return "Signal aktiv"
        return f"muss noch {gap:.1f}{unit} steigen"


def _mvrv_target_price(current_price, mvrv_current, market_cap_current, realized_cap_current, threshold):
    """Leitet den Zielpreis her, ab dem MVRV-Z die Verkaufsschwelle erreichen wuerde.

    MVRV-Z = (Marktkapitalisierung - realisierte Kapitalisierung) / Volatilitaetsfaktor.
    Aus dem heutigen Z-Wert und den heutigen Kapitalisierungen laesst sich der
    Volatilitaetsfaktor exakt zurueckrechnen. Realisierte Kapitalisierung und dieser
    Faktor bewegen sich nur sehr langsam (ueber Monate), daher werden sie fuer die
    Zielpreis-Frage als kurzfristig konstant behandelt, dieselbe Annahme wie bei
    CVDD und Mayer Multiple.
    """
    if None in (current_price, mvrv_current, market_cap_current, realized_cap_current):
        return None
    if abs(mvrv_current) < 0.01 or market_cap_current == 0:
        return None
    volatility_factor = (market_cap_current - realized_cap_current) / mvrv_current
    target_market_cap = threshold * volatility_factor + realized_cap_current
    return target_market_cap * current_price / market_cap_current


def get_signal_status(df_merged, cvdd_current=None, mvrv_current=None,
                       market_cap_current=None, realized_cap_current=None):
    """
    Berechnet den Status aller 8 Signale (4 Kauf, 4 Verkauf).

    Args:
        df_merged: DataFrame mit allen Indikatoren
        cvdd_current: Aktueller CVDD-Wert (float oder None)
        mvrv_current: Aktueller MVRV-Z-Score (float oder None)
        market_cap_current: Aktuelle Marktkapitalisierung in USD (float oder None)
        realized_cap_current: Aktuelle realisierte Kapitalisierung in USD (float oder None)

    Returns:
        dict mit 'buy' und 'sell' Signalen, jeweils mit active/value/threshold/gap
    """
    current = df_merged.iloc[-1]
    mm = current['mayer_multiple']
    fg = current['value']
    q10 = current.get('q10_expanding')
    q90 = current.get('q90_expanding')
    current_price = current['close']
    sma_200 = current['200_days_sma_for_mm']

    halving_info = get_halving_info()
    months_since = halving_info['months_since_halving']
    buy_block_months = STRATEGY_CONFIG['BUY_BLOCK_MONTHS']
    # Grobe Schätzung nächstes Halving: ~48 Monate nach dem letzten (4-Jahres-Zyklus)
    months_to_next_halving = max(0.0, 48 - months_since)

    # KAUF-Signale
    q10_valid = q10 is not None and not pd.isna(q10)
    mm_buy_active = q10_valid and mm < q10
    mm_buy_target_price = sma_200 * float(q10) if q10_valid else None

    fg_buy_active = fg < STRATEGY_CONFIG['BUY_FG_THRESHOLD']

    cycle_buy_active = months_since >= buy_block_months

    cvdd_tolerance = STRATEGY_CONFIG['CVDD_TOLERANCE_PCT']
    cvdd_target_price = cvdd_current * (1 + cvdd_tolerance) if cvdd_current is not None else None
    cvdd_buy_active = (
        cvdd_current is not None and
        current_price <= cvdd_target_price
    )

    # VERKAUF-Signale
    q90_valid = q90 is not None and not pd.isna(q90)
    mm_sell_active = q90_valid and mm > q90
    mm_sell_target_price = sma_200 * float(q90) if q90_valid else None

    fg_sell_active = fg > STRATEGY_CONFIG['SELL_FG_THRESHOLD']

    mvrv_sell_active = (
        mvrv_current is not None and
        mvrv_current >= STRATEGY_CONFIG['MVRV_SELL_THRESHOLD']
    )

    cycle_sell_active = months_since < buy_block_months

    return {
        'buy': {
            'mm_q10': {
                'active': mm_buy_active,
                'value': mm,
                'threshold': float(q10) if q10_valid else None,
                'label': 'MM < Q10',
                'gap': _price_gap_str(mm_buy_target_price, current_price, 'down')
            },
            'fg_fear': {
                'active': fg_buy_active,
                'value': fg,
                'threshold': STRATEGY_CONFIG['BUY_FG_THRESHOLD'],
                'label': f"F&G < {STRATEGY_CONFIG['BUY_FG_THRESHOLD']}",
                'gap': _points_gap_str(fg, STRATEGY_CONFIG['BUY_FG_THRESHOLD'], 'down', ' Pkt.')
            },
            'cycle_bear': {
                'active': cycle_buy_active,
                'value': months_since,
                'threshold': buy_block_months,
                'label': f'Zyklus > {buy_block_months} Mo.',
                'gap': "Signal aktiv" if cycle_buy_active else f"noch {buy_block_months - months_since:.1f} Mo. bis Akkumulationsphase"
            },
            'cvdd': {
                'active': cvdd_buy_active,
                'value': current_price,
                'threshold': cvdd_current,
                'label': 'Preis nahe CVDD',
                'gap': _price_gap_str(cvdd_target_price, current_price, 'down')
            }
        },
        'sell': {
            'mm_q90': {
                'active': mm_sell_active,
                'value': mm,
                'threshold': float(q90) if q90_valid else None,
                'label': 'MM > Q90',
                'gap': _price_gap_str(mm_sell_target_price, current_price, 'up')
            },
            'fg_greed': {
                'active': fg_sell_active,
                'value': fg,
                'threshold': STRATEGY_CONFIG['SELL_FG_THRESHOLD'],
                'label': f"F&G > {STRATEGY_CONFIG['SELL_FG_THRESHOLD']}",
                'gap': _points_gap_str(fg, STRATEGY_CONFIG['SELL_FG_THRESHOLD'], 'up', ' Pkt.')
            },
            'mvrv': {
                'active': mvrv_sell_active,
                'value': mvrv_current,
                'threshold': STRATEGY_CONFIG['MVRV_SELL_THRESHOLD'],
                'label': f"MVRV-Z >= {STRATEGY_CONFIG['MVRV_SELL_THRESHOLD']}",
                'gap': _price_gap_str(
                    _mvrv_target_price(current_price, mvrv_current, market_cap_current,
                                        realized_cap_current, STRATEGY_CONFIG['MVRV_SELL_THRESHOLD']),
                    current_price, 'up'
                ) or _points_gap_str(mvrv_current, STRATEGY_CONFIG['MVRV_SELL_THRESHOLD'], 'up')
            },
            'cycle_bull': {
                'active': cycle_sell_active,
                'value': months_since,
                'threshold': buy_block_months,
                'label': f'Zyklus < {buy_block_months} Mo.',
                'gap': "Signal aktiv" if cycle_sell_active else f"noch ~{months_to_next_halving:.1f} Mo. bis nächstes Halving"
            }
        },
        'current_price': current_price,
        'months_since_halving': months_since,
        'halving_hint': halving_info['halving_hint']
    }


def calculate_price_levels(df_merged):
    """
    Berechnet wichtige Preislevels für Charts und Anzeige.

    Returns:
        dict mit aktuellen Preislevels
    """
    current = df_merged.iloc[-1]
    sma_200 = current['200_days_sma_for_mm']
    q90 = current.get('q90_expanding')
    q10 = current.get('q10_expanding')

    q90_val = float(q90) if q90 is not None and not pd.isna(q90) else None
    q10_val = float(q10) if q10 is not None and not pd.isna(q10) else None

    return {
        'current_price': current['close'],
        'current_200_sma': sma_200,
        'q90_price': sma_200 * q90_val if q90_val else None,
        'q10_price': sma_200 * q10_val if q10_val else None,
        'current_mm': current['mayer_multiple'],
        'current_fg': current['value'],
        'current_q90': q90_val,
        'current_q10': q10_val
    }


def months_since_last_halving(current_date=None):
    """
    Berechnet Monate seit dem letzten Bitcoin Halving.

    Returns:
        float: Monate seit letztem Halving, oder None falls kein Halving vor current_date
    """
    if current_date is None:
        current_date = pd.Timestamp.now()
    else:
        current_date = pd.Timestamp(current_date)

    last_halving_date = None
    for halving_num, halving_data in BITCOIN_HALVINGS.items():
        halving_date = pd.Timestamp(halving_data["date"])
        if halving_date <= current_date:
            if last_halving_date is None or halving_date > last_halving_date:
                last_halving_date = halving_date

    if last_halving_date is None:
        return None

    days_since = (current_date - last_halving_date).days
    return days_since / 30.44
