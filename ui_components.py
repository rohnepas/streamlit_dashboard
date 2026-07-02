import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

from data_processing import fetch_onchain_data
from helpers import fetch_and_process_data
from strategy import get_signal_status, months_since_last_halving
from config import BITCOIN_HALVINGS, STRATEGY_CONFIG

# Farbrollen aus der dataviz-Skill-Referenzpalette (references/palette.md).
# Fixe, validierte Werte statt frei erfundener Hex-Codes.
INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
GOOD = "#0ca30c"       # Status: Kaufzone, aktiv
CRITICAL = "#d03b3b"   # Status: Verkaufszone, aktiv
CAT_BLUE = "#2a78d6"   # Kategorial Slot 1, Identitaet (F&G, MVRV-Z, Mayer Multiple)
CAT_YELLOW = "#eda100" # Kategorial Slot 3, 200-Tage MA
CAT_VIOLET = "#4a3aa7" # Kategorial Slot 5, CVDD
SEQ_BLUE_LIGHT = "#cde2fb"  # Sequential Blue, Stufe 100, Meter-Track

FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def show_app_header(last_date):
    """Zeigt App Header mit einer kurzen Erklärung, die auch Neulinge verstehen."""
    st.title("BTC Strategy Dashboard")
    st.caption(
        "Dieses Dashboard beobachtet acht verschiedene Signale für Bitcoin: vier sprechen "
        "für einen Kauf, vier für einen Verkauf. Jedes Signal wird für sich allein bewertet, "
        "die Signale hängen nicht voneinander ab und werden nicht zu einer Gesamtempfehlung "
        f"verrechnet. Was jedes Signal bedeutet, steht auf seiner Kachel. Letzte Daten: {last_date}."
    )


def show_current_price(df_merged):
    """Zeigt den aktuellen Bitcoin-Kurs in USD mit Veränderung zum Vortag."""
    price = df_merged['close'].iloc[-1]
    delta_str = None
    if len(df_merged) >= 2:
        prev = df_merged['close'].iloc[-2]
        if prev:
            pct = (price - prev) / prev * 100
            delta_str = f"{pct:+.1f}% seit Vortag"
    st.metric("Bitcoin-Kurs (USD)", f"${price:,.0f}", delta=delta_str)


def _show_signal_tile(active, name, value_str, buy_side, gap=None):
    """Zeigt eine Signal-Kachel als native Streamlit-Card (kein HTML/CSS).
    height='stretch' statt fester Pixelhöhe: Kacheln derselben Zeile werden gleich
    hoch (so hoch wie die höchste), aber Inhalt wird nie abgeschnitten. Eine feste
    Höhe hat auf dem Handy zu internem Scrollen in der Kachel geführt.
    Statt einer immer sichtbaren Beschreibung zeigt die Kachel eine Statuszeile,
    was 'aktiv'/'inaktiv' hier konkret bedeutet. Die volle Erklärung steht im
    gemeinsamen Erklärungs-Abschnitt unter dem Kachel-Raster.
    """
    with st.container(border=True, height="stretch"):
        header_col, badge_col = st.columns([0.62, 0.38], vertical_alignment="center")
        header_col.markdown(f"**{name}**")
        with badge_col:
            if active:
                st.badge("Aktiv", icon=":material/check_circle:", color="green" if buy_side else "red")
            else:
                st.badge("Inaktiv", icon=":material/radio_button_unchecked:", color="gray")

        st.markdown(value_str)

        if active:
            st.caption(":material/check: Bedingung ist aktuell erfüllt.")
        elif gap:
            st.caption(f"Noch nötig: {gap}")


def _signal_grid(tiles, buy_side):
    """Rendert Signal-Kacheln als Raster (3 Kacheln -> eine Reihe, 4 Kacheln -> 2x2)."""
    if len(tiles) == 3:
        row = st.columns(3)
        for col, tile in zip(row, tiles):
            with col:
                _show_signal_tile(buy_side=buy_side, **tile)
        return
    row1 = st.columns(2)
    for col, tile in zip(row1, tiles[:2]):
        with col:
            _show_signal_tile(buy_side=buy_side, **tile)
    row2 = st.columns(2)
    for col, tile in zip(row2, tiles[2:]):
        with col:
            _show_signal_tile(buy_side=buy_side, **tile)


def show_signal_dashboard(signal_status):
    """Zeigt 4 Kauf- und 4 Verkaufssignale als Kachel-Raster in 2 Spalten"""
    buy = signal_status['buy']
    sell = signal_status['sell']

    col_buy, col_sell = st.columns(2, gap="large")

    with col_buy:
        st.markdown("##### :material/trending_up: Kauf-Signale")

        sig = buy['mm_q10']
        q10_str = f"{sig['threshold']:.2f}" if sig['threshold'] is not None else "N/A"
        sig_cvdd = buy['cvdd']
        cvdd_str = (f"Preis: \\${sig_cvdd['value']:,.0f} | CVDD: \\${sig_cvdd['threshold']:,.0f} (inoffizielle Quelle)"
                    if sig_cvdd['threshold'] is not None else "CVDD: Daten nicht verfügbar")

        _signal_grid([
            dict(active=sig['active'], name="MM < Q10", value_str=f"MM: {sig['value']:.2f} | Q10: {q10_str}",
                 gap=sig['gap']),
            dict(active=buy['fg_fear']['active'], name=f"F&G < {buy['fg_fear']['threshold']}",
                 value_str=f"F&G: {int(buy['fg_fear']['value'])} | Schwelle: {buy['fg_fear']['threshold']}",
                 gap=buy['fg_fear']['gap']),
            dict(active=buy['cycle_bear']['active'], name=f"Zyklus > {buy['cycle_bear']['threshold']} Mo.",
                 value_str=f"Seit Halving: {buy['cycle_bear']['value']:.1f} Mo. | Schwelle: {buy['cycle_bear']['threshold']}",
                 gap=buy['cycle_bear']['gap']),
            dict(active=sig_cvdd['active'], name="Preis nahe CVDD", value_str=cvdd_str,
                 gap=sig_cvdd['gap']),
        ], buy_side=True)

    with col_sell:
        st.markdown("##### :material/trending_down: Verkauf-Signale")

        sig = sell['mm_q90']
        q90_str = f"{sig['threshold']:.2f}" if sig['threshold'] is not None else "N/A"
        sig_mvrv = sell['mvrv']
        mvrv_str = f"MVRV-Z: {sig_mvrv['value']:.2f}" if sig_mvrv['value'] is not None else "MVRV-Z: Daten nicht verfügbar"

        _signal_grid([
            dict(active=sig['active'], name="MM > Q90", value_str=f"MM: {sig['value']:.2f} | Q90: {q90_str}",
                 gap=sig['gap']),
            dict(active=sell['fg_greed']['active'], name=f"F&G > {sell['fg_greed']['threshold']}",
                 value_str=f"F&G: {int(sell['fg_greed']['value'])} | Schwelle: {sell['fg_greed']['threshold']}",
                 gap=sell['fg_greed']['gap']),
            dict(active=sell['cycle_bull']['active'], name=f"Zyklus < {sell['cycle_bull']['threshold']} Mo.",
                 value_str=f"Seit Halving: {sell['cycle_bull']['value']:.1f} Mo. | Schwelle: {sell['cycle_bull']['threshold']}",
                 gap=sell['cycle_bull']['gap']),
            dict(active=sig_mvrv['active'], name=f"MVRV-Z >= {sig_mvrv['threshold']}", value_str=mvrv_str,
                 gap=sig_mvrv['gap']),
        ], buy_side=False)

    with st.expander(":material/help: Was bedeuten die Signale?"):
        st.markdown("**Kauf-Signale**")
        st.markdown(
            "**MM < Q10.** Der Mayer Multiple (MM) zeigt, wie teuer Bitcoin gerade im Vergleich zu "
            "seinem eigenen Durchschnitt der letzten 200 Tage ist. Berechnung: aktueller Preis geteilt "
            "durch diesen Durchschnittspreis. Ein Wert von 1 heisst, der Preis entspricht genau dem "
            "Durchschnitt. Das Signal schlägt an, wenn der Wert tiefer ist als in 90% der bisherigen "
            "Zeit, Bitcoin also im Vergleich zu seinem eigenen Trend besonders günstig ist. Weil sich "
            "der 200-Tage-Durchschnitt nur langsam bewegt, reagiert der Mayer Multiple stark auf "
            "schnelle Kursbewegungen: Ein rascher Preisabfall kann dieses Signal schnell auslösen, "
            "auch wenn sich am langfristigen Trend sonst wenig geändert hat."
        )
        st.markdown(
            "**F&G < 25.** Der Fear & Greed Index misst die Stimmung im Markt von 0 (extreme Angst) "
            "bis 100 (extreme Gier). Das Signal schlägt an, wenn der Wert unter 25 fällt. Historisch "
            "waren solche Angstphasen oft gute Zeitpunkte zum Kaufen. Der Index setzt sich aus "
            "mehreren Bausteinen zusammen:"
        )
        st.markdown(
            "- Schwankungen und Kurseinbrüche (25%)\n"
            "- Handelsvolumen und Markttempo (25%)\n"
            "- Aktivität auf Social Media, z.B. Twitter (15%)\n"
            "- Umfragen unter Anlegern (15%, aktuell pausiert)\n"
            "- Bitcoin-Anteil am gesamten Kryptomarkt (10%)\n"
            "- Google-Suchtrends rund um Bitcoin (10%)"
        )
        st.markdown(
            "**Zyklus > 18 Mo.** Etwa alle vier Jahre halbiert sich die Belohnung für neu erzeugte "
            "Bitcoin, das nennt man Halving. Dieses Signal zählt einfach die Monate seit dem letzten "
            "Halving. Nach 18 Monaten sind die grossen Kursanstiege historisch meist vorbei, danach "
            "gilt es als ruhigere Phase mit günstigeren Einstiegen."
        )
        st.markdown(
            "**Preis nahe CVDD.** CVDD ist ein Bodenwert, der aus der Vergangenheit berechnet wird. "
            "Grundidee: Man schaut in der gesamten Bitcoin-Geschichte, wann besonders viele alte, "
            "lange gehaltene Bitcoin auf einmal verkauft wurden. Das war historisch oft nahe am "
            "tiefsten Punkt eines Kursrückgangs, weil dort selbst geduldige Langzeit-Besitzer "
            "aufgegeben haben. Aus diesen vergangenen Tiefpunkten ergibt sich ein Preisniveau, das "
            "sich mit der Zeit langsam nach oben verschiebt. Nähert sich der aktuelle Kurs diesem "
            "Niveau, war das in der Vergangenheit meist ein Bereich, in dem der grösste Ausverkauf "
            "schon vorbei war, nicht der Punkt, an dem er erst beginnt. Achtung: Der Wert kommt von "
            "axeladlerjr.com, einer privaten Seite ohne offizielle Schnittstelle, und konnte nicht "
            "gegen die Original-Studie geprüft "
            "werden. Dieses Signal bleibt auch nach dem Start der Bitcoin-ETFs (Januar 2024) "
            "verlässlich, weil eine Kapitulation von Langzeit-Besitzern weiterhin echte Bewegungen "
            "auf der Blockchain hinterlässt, anders als bei Signalen zur Markteuphorie wie MVRV-Z."
        )
        st.markdown("**Verkauf-Signale**")
        st.markdown(
            "**MM > Q90.** Gleiche Berechnung wie beim Kaufsignal MM < Q10, nur umgekehrt: Das Signal "
            "schlägt an, wenn der Mayer Multiple höher ist als in 90% der bisherigen Zeit, Bitcoin "
            "also im Vergleich zu seinem eigenen Trend besonders teuer ist. Auch hier gilt: Ein "
            "rascher Preisanstieg kann dieses Signal schnell auslösen, weil der 200-Tage-Durchschnitt "
            "nicht so schnell mitzieht."
        )
        st.markdown(
            "**F&G > 75.** Gleicher Index wie beim Kaufsignal, nur umgekehrt: Das Signal schlägt an, "
            "wenn der Wert über 75 steigt. Historisch waren solche Gierphasen oft riskante Zeitpunkte "
            "zum Verkaufen."
        )
        st.markdown(
            "**Zyklus < 18 Mo.** Gleiche Zählung wie beim Kaufsignal, nur umgekehrt: Das Signal ist "
            "aktiv, solange seit dem letzten Halving weniger als 18 Monate vergangen sind. Das ist "
            "historisch die Phase mit den grössten Kursanstiegen, aber auch dem grössten "
            "Rückschlagrisiko."
        )
        st.markdown(
            "**MVRV-Z >= 5.** Dieser Wert zeigt, wie viel Gewinn Bitcoin-Besitzer im Durchschnitt "
            "gerade auf dem Papier halten, verglichen mit ihrem Einstiegspreis. Ist der Wert sehr "
            "hoch, sitzen viele auf grossen Gewinnen. Das erhöht die Versuchung zu verkaufen, was den "
            "Kurs unter Druck bringen kann. Das Signal schlägt an, wenn dieser Wert 5 oder höher ist, "
            "historisch ein Zeichen für übertriebene Gewinne kurz vor einem Rückgang. Wichtiger "
            "Hinweis seit 2024: Seit dem Start der Bitcoin-ETFs im Januar 2024 findet ein wachsender "
            "Teil des Handels ausserhalb der Blockchain statt, in ETFs und Derivaten. Das schwächt "
            "genau dieses Signal, weil weniger davon auf der Blockchain sichtbar wird. In diesem "
            "Zyklus erreichte MVRV-Z bisher nur rund 3.5 statt wie früher 6 oder 7. Das Signal kann "
            "also stumm bleiben, selbst wenn der Markt bereits stark überhitzt ist."
        )


def show_halving_cycle():
    """Zeigt Halving-Zyklus"""
    today = datetime.now()
    months = months_since_last_halving(today)

    if months is None:
        return

    last_halving_num = None
    last_halving_date = None
    for num, data in BITCOIN_HALVINGS.items():
        h_date = datetime.strptime(data["date"], "%Y-%m-%d")
        if h_date <= today:
            if last_halving_date is None or h_date > last_halving_date:
                last_halving_num = num
                last_halving_date = h_date

    months_until_next = max(0, 48 - months)

    st.markdown("#### Halving-Zyklus")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Seit letztem Halving", f"{months:.0f} Monate")
        st.caption(f"Halving #{last_halving_num} am {last_halving_date.strftime('%d.%m.%Y')}")

    with col2:
        st.metric("Bis nächstes Halving", f"~{months_until_next:.0f} Monate")
        st.caption("Geschätzt ~April 2028")

    cycle_progress = min(months / 48, 1.0)
    st.progress(cycle_progress)
    st.caption(f"Zyklus-Fortschritt: {months:.0f}/48 Monate")


def _base_layout(title, height=420):
    # Grosszuegiger oberer Rand (t=120): auf schmalen Bildschirmen (Handy) bricht die
    # Legende auf mehrere Zeilen um. Mit zu wenig Platz ueberlappt sie den Titel.
    return dict(
        title=dict(text=title, font=dict(size=16, color=INK, family=FONT_FAMILY)),
        template="plotly_white",
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=SECONDARY_INK, family=FONT_FAMILY, size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, l=10, r=10, b=110),
        height=height,
        hovermode="x unified",
    )


def _add_halving_markers(fig, df_merged):
    """Fügt Halving-Linien und die Linie 18 Monate danach hinzu, beide mit Beschriftung."""
    for num, data in BITCOIN_HALVINGS.items():
        h_date = pd.to_datetime(data["date"])
        if df_merged.index.min() <= h_date <= df_merged.index.max():
            h_date_str = h_date.strftime('%Y-%m-%d')
            fig.add_vline(x=h_date_str, line=dict(color=MUTED, width=1, dash="dot"))
            fig.add_annotation(x=h_date_str, y=1.0, yref="paper", text=f"Halving {num}",
                                showarrow=False, yshift=10, font=dict(size=10, color=MUTED))

        h_plus_18 = h_date + relativedelta(months=18)
        if df_merged.index.min() <= h_plus_18 <= df_merged.index.max():
            h_plus_18_str = h_plus_18.strftime('%Y-%m-%d')
            fig.add_vline(x=h_plus_18_str, line=dict(color=MUTED, width=1, dash="dot"))
            fig.add_annotation(x=h_plus_18_str, y=0.93, yref="paper", text="+18 Mo. nach Halving",
                                showarrow=False, yshift=10, font=dict(size=9, color=MUTED))


def create_price_chart(df_merged, cvdd_current=None):
    """Chart 1: BTC Preis (Log) mit Q10/Q90-Kauf-/Verkaufszonen und CVDD."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['close'], name='BTC Preis',
                              line=dict(color=INK, width=2),
                              hovertemplate='%{x|%d.%m.%Y}<br>$%{y:,.0f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['200_days_sma_for_mm'], name='200-Tage MA',
                              line=dict(color=CAT_YELLOW, width=2, dash='dot'),
                              hovertemplate='$%{y:,.0f}<extra></extra>'))

    if 'q90_price_level' in df_merged.columns:
        fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['q90_price_level'], name='MM Q90 Preis (Verkauf)',
                                  line=dict(color=CRITICAL, width=2, dash='dash'),
                                  hovertemplate='$%{y:,.0f}<extra></extra>'))
    if 'q10_price_level' in df_merged.columns:
        fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['q10_price_level'], name='MM Q10 Preis (Kauf)',
                                  line=dict(color=GOOD, width=2, dash='dash'),
                                  hovertemplate='$%{y:,.0f}<extra></extra>'))

    if cvdd_current is not None:
        # Als echte Linie (Trace) statt Annotation: Text-Annotationen auf einer
        # log-skalierten Y-Achse werden von Plotly/Kaleido in dieser Version nicht
        # zuverlässig gerendert (isoliert getestet und bestätigt). Eine Linie mit
        # Legenden-Eintrag ist ausserdem konsistent mit allen anderen Kurven im Chart.
        fig.add_trace(go.Scatter(
            x=[df_merged.index.min().strftime('%Y-%m-%d'), df_merged.index.max().strftime('%Y-%m-%d')],
            y=[cvdd_current, cvdd_current], name='CVDD (inoffizielle Quelle)',
            line=dict(color=CAT_VIOLET, width=2, dash='dashdot'),
            hovertemplate='$%{y:,.0f}<extra></extra>'))

    price_ticks = [1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]
    price_labels = ['$1K', '$2K', '$5K', '$10K', '$20K', '$50K', '$100K', '$200K', '$500K']
    fig.update_yaxes(type='log', title='Preis', gridcolor=GRID, zeroline=False,
                      tickvals=price_ticks, ticktext=price_labels)
    fig.update_xaxes(gridcolor=GRID, dtick="M12", tickformat="%Y")
    fig.update_layout(**_base_layout('BTC Preis (Log) mit Kauf- und Verkaufszonen', height=540))

    _add_halving_markers(fig, df_merged)
    return fig


def create_mayer_multiple_chart(df_merged):
    """Chart 2: Mayer Multiple mit rollierendem Q10/Q90."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['mayer_multiple'], name='Mayer Multiple',
                              line=dict(color=CAT_BLUE, width=2), hovertemplate='%{y:.2f}<extra></extra>'))
    if 'q90_expanding' in df_merged.columns:
        fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['q90_expanding'], name='Q90 (Verkauf)',
                                  line=dict(color=CRITICAL, width=2, dash='dash'), hovertemplate='%{y:.2f}<extra></extra>'))
    if 'q10_expanding' in df_merged.columns:
        fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['q10_expanding'], name='Q10 (Kauf)',
                                  line=dict(color=GOOD, width=2, dash='dash'), hovertemplate='%{y:.2f}<extra></extra>'))

    fig.add_hline(y=1.0, line=dict(color=MUTED, width=1),
                  annotation_text='MM = 1 (Preis entspricht 200-Tage-Durchschnitt)',
                  annotation_position='bottom left', annotation_font=dict(color=MUTED, size=9))
    fig.update_yaxes(range=[0, 4], title='Mayer Multiple', gridcolor=GRID, zeroline=False)
    fig.update_xaxes(gridcolor=GRID, dtick="M12", tickformat="%Y")
    fig.update_layout(**_base_layout('Mayer Multiple mit Q10 / Q90 (rolling)', height=440))

    _add_halving_markers(fig, df_merged)
    return fig


def create_fear_greed_chart(df_merged):
    """Chart 3: Fear & Greed Index mit Kauf-/Verkaufsschwellen."""
    buy_fg = STRATEGY_CONFIG['BUY_FG_THRESHOLD']
    sell_fg = STRATEGY_CONFIG['SELL_FG_THRESHOLD']

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_merged.index, y=df_merged['value'], name='Fear & Greed',
                              line=dict(color=CAT_BLUE, width=2), fill='tozeroy',
                              fillcolor='rgba(42,120,214,0.1)', hovertemplate='%{y:.0f}<extra></extra>'))

    label_bg = 'rgba(252,252,251,0.85)'
    fig.add_hline(y=buy_fg, line=dict(color=GOOD, width=1.5, dash='dash'),
                  annotation_text=f'Kauf < {buy_fg}', annotation_font=dict(color=GOOD, size=11),
                  annotation_position='top left', annotation_bgcolor=label_bg)
    fig.add_hline(y=sell_fg, line=dict(color=CRITICAL, width=1.5, dash='dash'),
                  annotation_text=f'Verkauf > {sell_fg}', annotation_font=dict(color=CRITICAL, size=11),
                  annotation_position='top left', annotation_bgcolor=label_bg)

    fig.update_yaxes(range=[0, 100], title='Index', gridcolor=GRID, zeroline=False)
    fig.update_xaxes(gridcolor=GRID, dtick="M12", tickformat="%Y")
    fig.update_layout(**_base_layout('Fear & Greed Index', height=300))
    fig.update_layout(showlegend=False)  # nur eine Kurve, Titel sagt bereits was geplottet ist

    _add_halving_markers(fig, df_merged)
    return fig


def create_mvrv_meter(mvrv_current):
    """Chart 4: MVRV-Z als Meter (aktueller Wert gegen Verkaufsschwelle) statt Zeitreihe.
    Es liegt ohnehin keine brauchbare Historie vor (siehe fetch_onchain_data)."""
    threshold = STRATEGY_CONFIG['MVRV_SELL_THRESHOLD']
    gauge_max = max(threshold * 1.6, (mvrv_current or 0) * 1.2, 8)

    fig = go.Figure()

    # Track (unfilled), hellere Stufe derselben Rampe
    fig.add_shape(type='rect', x0=0, x1=gauge_max, y0=0.3, y1=0.7,
                  fillcolor=SEQ_BLUE_LIGHT, line=dict(width=0), layer='below')

    if mvrv_current is not None:
        fig.add_shape(type='rect', x0=0, x1=mvrv_current, y0=0.3, y1=0.7,
                      fillcolor=CAT_BLUE, line=dict(width=0))
        fig.add_annotation(x=mvrv_current, y=0.85, text=f'<b>{mvrv_current:.2f}</b>',
                            showarrow=False, font=dict(size=20, color=INK, family=FONT_FAMILY))
    else:
        fig.add_annotation(x=gauge_max / 2, y=0.5, text='Daten nicht verfügbar',
                            showarrow=False, font=dict(size=13, color=MUTED, family=FONT_FAMILY))

    fig.add_shape(type='line', x0=threshold, x1=threshold, y0=0.1, y1=0.9,
                  line=dict(color=CRITICAL, width=3))
    fig.add_annotation(x=threshold, y=0.05, text=f'Verkaufszone ≥ {threshold}',
                        showarrow=False, font=dict(size=11, color=CRITICAL, family=FONT_FAMILY))

    fig.update_xaxes(range=[0, gauge_max], showgrid=False, zeroline=False, title='MVRV-Z Score')
    fig.update_yaxes(range=[0, 1], showticklabels=False, showgrid=False, zeroline=False)
    fig.update_layout(**_base_layout('MVRV-Z Score, aktueller Wert (On-Chain)', height=190))
    fig.update_layout(showlegend=False)
    return fig


def loadUiComponents():
    """Hauptfunktion zum Laden aller UI-Komponenten"""
    # Marktdaten laden
    data_merged, message, df_merged = fetch_and_process_data()
    if not data_merged:
        st.error(message)
        return

    # On-Chain Daten laden (CVDD, MVRV-Z, Markt-/realisierte Kapitalisierung)
    cvdd_current, mvrv_current, market_cap_current, realized_cap_current = fetch_onchain_data()

    # App Header
    last_date = df_merged.index[-1].strftime('%d.%m.%Y')
    show_app_header(last_date)

    # Aktueller Bitcoin-Kurs
    show_current_price(df_merged)

    st.divider()

    # 1. Signal-Dashboard (4+4 Signale)
    st.markdown("### :material/insights: Signal-Übersicht")
    signal_status = get_signal_status(df_merged, cvdd_current, mvrv_current,
                                       market_cap_current, realized_cap_current)
    show_signal_dashboard(signal_status)

    st.divider()

    # 2. Halving-Zyklus
    show_halving_cycle()

    st.divider()

    # 3. Charts, standardmaessig eingeklappt: auf dem Handy belegen die vier Charts
    # sonst enorm viel Scrollweg, auf dem Desktop kostet das Aufklappen einen Klick.
    with st.expander(":material/monitoring: Charts anzeigen", expanded=False):
        st.plotly_chart(create_price_chart(df_merged, cvdd_current), width='stretch')
        st.plotly_chart(create_mayer_multiple_chart(df_merged), width='stretch')
        st.plotly_chart(create_fear_greed_chart(df_merged), width='stretch')
        st.plotly_chart(create_mvrv_meter(mvrv_current), width='stretch')
