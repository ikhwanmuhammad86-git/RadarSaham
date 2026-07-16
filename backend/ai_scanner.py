from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf


MINIMUM_DATA_ROWS = 60
DEFAULT_PERIOD = "1y"
SESSION_RESULT_KEY = "hasil_ai_scanner"
SESSION_FAILED_KEY = "gagal_ai_scanner"


def normalize_market_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    Merapikan struktur data dari Yahoo Finance.

    yfinance kadang menghasilkan MultiIndex pada nama kolom.
    Fungsi ini memastikan kolom menjadi Open, High, Low,
    Close, Volume, dan seterusnya.
    """
    if data.empty:
        return data

    result = data.copy()

    if isinstance(result.columns, pd.MultiIndex):
        result.columns = result.columns.get_level_values(0)

    required_columns = {
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    }

    missing_columns = required_columns.difference(result.columns)

    if missing_columns:
        raise ValueError(
            "Kolom Yahoo Finance tidak lengkap: "
            + ", ".join(sorted(missing_columns))
        )

    numeric_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    result = result.dropna(
        subset=[
            "High",
            "Low",
            "Close",
            "Volume",
        ]
    )

    return result


def download_stock_data(
    kode: str,
    periode: str,
) -> pd.DataFrame:
    """
    Mengambil data historis satu saham BEI dari Yahoo Finance.
    """
    kode = str(kode).strip().upper()

    if not kode:
        raise ValueError("Kode saham kosong.")

    symbol = f"{kode}.JK"

    data = yf.download(
        symbol,
        period=periode,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    return normalize_market_data(data)


def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    Menghitung indikator teknikal yang dipakai AI Scanner.
    """
    result = data.copy()

    # Moving Average
    result["MA20"] = (
        result["Close"]
        .rolling(window=20)
        .mean()
    )

    result["MA50"] = (
        result["Close"]
        .rolling(window=50)
        .mean()
    )

    # Rata-rata volume
    result["Volume_MA20"] = (
        result["Volume"]
        .rolling(window=20)
        .mean()
    )

    # RSI 14
    delta = result["Close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    average_loss = loss.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    relative_strength = (
        average_gain /
        average_loss.replace(0, pd.NA)
    )

    result["RSI"] = (
        100 -
        (100 / (1 + relative_strength))
    )

    # MACD
    ema12 = result["Close"].ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = result["Close"].ewm(
        span=26,
        adjust=False,
    ).mean()

    result["MACD_Value"] = ema12 - ema26

    result["MACD_Signal"] = (
        result["MACD_Value"]
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    result["MACD_Histogram"] = (
        result["MACD_Value"] -
        result["MACD_Signal"]
    )

    # True Range dan ATR
    previous_close = result["Close"].shift(1)

    true_range = pd.concat(
        [
            result["High"] - result["Low"],
            (result["High"] - previous_close).abs(),
            (result["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["ATR14"] = (
        true_range
        .rolling(window=14)
        .mean()
    )

    return result


def get_recommendation(
    score: int,
    risk_reward: float,
) -> tuple[str, str]:
    """
    Menentukan rekomendasi berdasarkan skor dan risk/reward.
    """
    if score >= 85 and risk_reward >= 2:
        return (
            "🔥 STRONG BUY",
            "Trend, momentum, volume, dan risk/reward sangat mendukung.",
        )

    if score >= 70:
        return (
            "🟢 BUY",
            "Setup teknikal cukup menarik untuk dipertimbangkan.",
        )

    if score >= 55:
        return (
            "🟡 HOLD / WATCHLIST",
            "Setup belum cukup kuat. Tunggu konfirmasi berikutnya.",
        )

    if score >= 40:
        return (
            "🟠 REDUCE",
            "Momentum relatif lemah dan risiko perlu diperhatikan.",
        )

    return (
        "🔴 SELL / AVOID",
        "Risiko lebih besar dibandingkan kualitas setup saat ini.",
    )


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Mengubah nilai menjadi float secara aman.
    """
    try:
        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def analisis_ai_saham(
    kode: str,
    periode: str = DEFAULT_PERIOD,
) -> dict[str, Any] | None:
    """
    Menganalisis satu saham dan mengembalikan satu baris hasil scanner.
    """
    kode = str(kode).strip().upper()

    data = download_stock_data(
        kode=kode,
        periode=periode,
    )

    if data.empty or len(data) < MINIMUM_DATA_ROWS:
        return None

    data = calculate_indicators(data)

    valid_data = data.dropna(
        subset=[
            "Close",
            "MA20",
            "MA50",
            "Volume_MA20",
            "RSI",
            "MACD_Value",
            "MACD_Signal",
            "ATR14",
        ]
    )

    if len(valid_data) < 2:
        return None

    latest = valid_data.iloc[-1]
    previous = valid_data.iloc[-2]

    close = safe_float(latest["Close"])
    previous_close = safe_float(previous["Close"])

    ma20 = safe_float(latest["MA20"])
    ma50 = safe_float(latest["MA50"])

    previous_ma20 = safe_float(previous["MA20"])
    previous_ma50 = safe_float(previous["MA50"])

    volume = safe_float(latest["Volume"])
    average_volume = safe_float(latest["Volume_MA20"])

    rsi = safe_float(latest["RSI"])

    macd_value = safe_float(latest["MACD_Value"])
    macd_signal = safe_float(latest["MACD_Signal"])

    previous_macd = safe_float(
        previous["MACD_Value"]
    )

    previous_macd_signal = safe_float(
        previous["MACD_Signal"]
    )

    atr = safe_float(latest["ATR14"])

    high_20 = safe_float(
        data["High"]
        .tail(20)
        .max()
    )

    low_20 = safe_float(
        data["Low"]
        .tail(20)
        .min()
    )

    previous_resistance = safe_float(
        data["High"]
        .shift(1)
        .tail(20)
        .max()
    )

    support = low_20
    resistance = high_20

    trend_bullish = ma20 > ma50

    golden_cross = (
        ma20 > ma50 and
        previous_ma20 <= previous_ma50
    )

    death_cross = (
        ma20 < ma50 and
        previous_ma20 >= previous_ma50
    )

    macd_bullish = macd_value > macd_signal

    macd_bullish_cross = (
        macd_value > macd_signal and
        previous_macd <= previous_macd_signal
    )

    macd_bearish_cross = (
        macd_value < macd_signal and
        previous_macd >= previous_macd_signal
    )

    volume_spike = (
        average_volume > 0 and
        volume >= average_volume * 1.5
    )

    breakout = (
        previous_resistance > 0 and
        close > previous_resistance and
        volume > average_volume
    )

    price_above_ma20 = close > ma20
    positive_daily_move = close > previous_close

    # =========================
    # SISTEM PENILAIAN
    # Total maksimal: 100
    # =========================

    score_trend = 0
    score_momentum = 0
    score_volume = 0
    score_position = 0
    score_breakout = 0

    # Trend maksimal 30
    if ma20 > ma50:
        score_trend += 20

    if close > ma20:
        score_trend += 5

    if golden_cross:
        score_trend += 5

    # Momentum maksimal 25
    if 45 <= rsi <= 65:
        score_momentum += 10
    elif 35 <= rsi < 45:
        score_momentum += 7
    elif 65 < rsi <= 75:
        score_momentum += 5
    elif rsi < 35:
        score_momentum += 4

    if macd_bullish:
        score_momentum += 10

    if macd_bullish_cross:
        score_momentum += 5

    # Volume maksimal 20
    if average_volume > 0:
        volume_ratio = volume / average_volume
    else:
        volume_ratio = 0

    if volume_ratio >= 1.5:
        score_volume = 20
    elif volume_ratio >= 1.1:
        score_volume = 15
    elif volume_ratio >= 0.8:
        score_volume = 10
    else:
        score_volume = 5

    # Posisi terhadap support maksimal 15
    if support > 0:
        distance_from_support = (
            (close - support) /
            support
        ) * 100
    else:
        distance_from_support = 0

    if 0 <= distance_from_support <= 5:
        score_position = 15
    elif distance_from_support <= 10:
        score_position = 10
    elif distance_from_support <= 20:
        score_position = 5

    # Breakout maksimal 10
    if breakout:
        score_breakout = 10
    elif positive_daily_move:
        score_breakout = 5

    total_score = int(
        min(
            100,
            score_trend
            + score_momentum
            + score_volume
            + score_position
            + score_breakout,
        )
    )

    # =========================
    # RISK MANAGEMENT
    # =========================

    entry_price = close

    if atr > 0:
        atr_stop = entry_price - (atr * 1.5)
    else:
        atr_stop = support

    if support > 0 and support < entry_price:
        stop_loss = max(
            support * 0.98,
            atr_stop,
        )
    else:
        stop_loss = atr_stop

    if stop_loss >= entry_price:
        stop_loss = entry_price * 0.97

    risk = entry_price - stop_loss

    if resistance > entry_price:
        target_1 = resistance
    else:
        target_1 = entry_price + (risk * 1.5)

    target_2 = entry_price + (risk * 2)

    reward = target_1 - entry_price

    if risk > 0:
        risk_reward = max(
            0,
            reward / risk,
        )
    else:
        risk_reward = 0

    recommendation, recommendation_note = (
        get_recommendation(
            score=total_score,
            risk_reward=risk_reward,
        )
    )

    if death_cross:
        trend_label = "Bearish"
    elif trend_bullish:
        trend_label = "Bullish"
    else:
        trend_label = "Bearish"

    if macd_bullish_cross:
        macd_label = "Bullish Cross"
    elif macd_bearish_cross:
        macd_label = "Bearish Cross"
    elif macd_bullish:
        macd_label = "Bullish"
    else:
        macd_label = "Bearish"

    return {
        "Kode": kode,
        "Harga": round(entry_price, 0),
        "Support": round(support, 0),
        "Resistance": round(resistance, 0),
        "Stop Loss": round(stop_loss, 0),
        "Target 1": round(target_1, 0),
        "Target 2": round(target_2, 0),
        "Risk Reward": round(risk_reward, 2),
        "AI Score": total_score,
        "Trend": trend_label,
        "MA20": round(ma20, 2),
        "MA50": round(ma50, 2),
        "RSI": round(rsi, 2),
        "MACD": macd_label,
        "Golden Cross": golden_cross,
        "Death Cross": death_cross,
        "Breakout": breakout,
        "Volume Spike": volume_spike,
        "Volume Ratio": round(volume_ratio, 2),
        "ATR": round(atr, 2),
        "Rekomendasi": recommendation,
        "Catatan": recommendation_note,
    }


def prepare_master_dataframe(
    master_data: list[dict[str, Any]],
) -> pd.DataFrame:
    """
    Membersihkan data master saham dari API.
    """
    master_df = pd.DataFrame(master_data)

    if master_df.empty:
        return master_df

    if "kode" not in master_df.columns:
        raise ValueError(
            "Respons endpoint master tidak memiliki kolom 'kode'."
        )

    master_df["kode"] = (
        master_df["kode"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    master_df = master_df[
        master_df["kode"].ne("")
    ]

    master_df = (
        master_df
        .drop_duplicates(subset=["kode"])
        .sort_values("kode")
        .reset_index(drop=True)
    )

    return master_df


def run_scanner(
    scan_df: pd.DataFrame,
    periode: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Menjalankan scanner dan memperbarui komponen progress Streamlit.
    """
    total = len(scan_df)

    result_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, str]] = []

    progress = st.progress(0)
    status = st.empty()

    column_success, column_failed, column_processed = (
        st.columns(3)
    )

    success_box = column_success.empty()
    failed_box = column_failed.empty()
    processed_box = column_processed.empty()

    success_count = 0
    failed_count = 0

    for index, row in enumerate(
        scan_df.itertuples(index=False),
        start=1,
    ):
        kode = str(row.kode).strip().upper()

        status.info(
            f"Menganalisis {kode} — {index} dari {total}"
        )

        try:
            result = analisis_ai_saham(
                kode=kode,
                periode=periode,
            )

            if result is None:
                failed_rows.append(
                    {
                        "Kode": kode,
                        "Alasan": (
                            "Data kosong atau jumlah data "
                            "belum mencukupi."
                        ),
                    }
                )

                failed_count += 1

            else:
                result_rows.append(result)
                success_count += 1

        except Exception as error:
            failed_rows.append(
                {
                    "Kode": kode,
                    "Alasan": str(error),
                }
            )

            failed_count += 1

        success_box.metric(
            "Berhasil",
            success_count,
        )

        failed_box.metric(
            "Gagal",
            failed_count,
        )

        processed_box.metric(
            "Diproses",
            f"{index}/{total}",
        )

        progress.progress(index / total)

    progress.empty()
    status.success("AI Scanner selesai.")

    result_df = pd.DataFrame(result_rows)
    failed_df = pd.DataFrame(failed_rows)

    if not result_df.empty:
        result_df = (
            result_df
            .sort_values(
                by=[
                    "AI Score",
                    "Risk Reward",
                ],
                ascending=[
                    False,
                    False,
                ],
            )
            .reset_index(drop=True)
        )

        result_df.index = result_df.index + 1
        result_df.index.name = "Rank"

    return result_df, failed_df


def create_excel_result(
    result_df: pd.DataFrame,
    failed_df: pd.DataFrame,
) -> bytes:
    """
    Membuat file Excel hasil scanner di memory.
    """
    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        result_df.reset_index().to_excel(
            writer,
            index=False,
            sheet_name="AI Scanner",
        )

        if not failed_df.empty:
            failed_df.to_excel(
                writer,
                index=False,
                sheet_name="Gagal",
            )

    return output.getvalue()


def render_scanner_results() -> None:
    """
    Menampilkan hasil scanner yang disimpan dalam session state.
    """
    if SESSION_RESULT_KEY not in st.session_state:
        return

    result_df = st.session_state[
        SESSION_RESULT_KEY
    ].copy()

    failed_df = st.session_state.get(
        SESSION_FAILED_KEY,
        pd.DataFrame(),
    )

    if result_df.empty:
        return

    st.divider()
    st.subheader("🏆 Ranking AI Scanner")

    column_score, column_recommendation, column_trend = (
        st.columns(3)
    )

    minimum_score = column_score.slider(
        "Minimal AI Score",
        min_value=0,
        max_value=100,
        value=0,
        key="scanner_minimum_score",
    )

    recommendation_options = sorted(
        result_df["Rekomendasi"]
        .dropna()
        .unique()
        .tolist()
    )

    recommendation_filter = (
        column_recommendation.multiselect(
            "Rekomendasi",
            options=recommendation_options,
            key="scanner_recommendation_filter",
        )
    )

    bullish_only = column_trend.checkbox(
        "Trend Bullish saja",
        key="scanner_bullish_only",
    )

    additional_filters = st.multiselect(
        "Filter sinyal tambahan",
        options=[
            "Golden Cross",
            "Breakout",
            "Volume Spike",
            "MACD Bullish",
            "RSI Oversold",
        ],
        key="scanner_additional_filters",
    )

    filtered_df = result_df[
        result_df["AI Score"] >= minimum_score
    ].copy()

    if recommendation_filter:
        filtered_df = filtered_df[
            filtered_df["Rekomendasi"].isin(
                recommendation_filter
            )
        ]

    if bullish_only:
        filtered_df = filtered_df[
            filtered_df["Trend"] == "Bullish"
        ]

    if "Golden Cross" in additional_filters:
        filtered_df = filtered_df[
            filtered_df["Golden Cross"]
        ]

    if "Breakout" in additional_filters:
        filtered_df = filtered_df[
            filtered_df["Breakout"]
        ]

    if "Volume Spike" in additional_filters:
        filtered_df = filtered_df[
            filtered_df["Volume Spike"]
        ]

    if "MACD Bullish" in additional_filters:
        filtered_df = filtered_df[
            filtered_df["MACD"].isin(
                [
                    "Bullish",
                    "Bullish Cross",
                ]
            )
        ]

    if "RSI Oversold" in additional_filters:
        filtered_df = filtered_df[
            filtered_df["RSI"] <= 30
        ]

    st.write(
        f"Ditemukan **{len(filtered_df)}** saham."
    )

    main_columns = [
        "Kode",
        "Harga",
        "AI Score",
        "Trend",
        "RSI",
        "MACD",
        "Golden Cross",
        "Breakout",
        "Volume Spike",
        "Risk Reward",
        "Rekomendasi",
    ]

    available_columns = [
        column
        for column in main_columns
        if column in filtered_df.columns
    ]

    st.dataframe(
        filtered_df[available_columns],
        use_container_width=True,
        height=600,
    )

    if not filtered_df.empty:
        top20 = (
            filtered_df
            .head(20)
            .reset_index()
        )

        figure = px.bar(
            top20,
            x="Kode",
            y="AI Score",
            text="AI Score",
            hover_data=[
                "Harga",
                "Trend",
                "RSI",
                "MACD",
                "Risk Reward",
                "Rekomendasi",
            ],
            title="Top 20 Saham Berdasarkan AI Score",
        )

        figure.update_traces(
            textposition="outside"
        )

        figure.update_layout(
            yaxis_range=[0, 110]
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    excel_data = create_excel_result(
        result_df=filtered_df,
        failed_df=failed_df,
    )

    st.download_button(
        label="📥 Download Hasil AI Scanner",
        data=excel_data,
        file_name="hasil_ai_scanner.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key="download_ai_scanner",
    )

    if not failed_df.empty:
        with st.expander(
            f"Lihat {len(failed_df)} saham yang gagal diproses"
        ):
            st.dataframe(
                failed_df,
                use_container_width=True,
            )


def render_ai_scanner_page(
    get_data_function,
) -> None:
    """
    Fungsi utama yang dipanggil oleh dashboard.py.

    Parameter:
        get_data_function:
            Fungsi dari dashboard untuk mengambil data API.
    """
    st.subheader("🤖 RadarSaham AI Scanner")

    st.caption(
        "Pemindaian saham menggunakan MA20/MA50, RSI, MACD, "
        "volume, support/resistance, ATR, breakout, "
        "risk/reward, dan AI Score."
    )

    master_data = get_data_function(
        "/stocks/master"
    )

    if not master_data:
        st.error(
            "Master saham kosong atau API tidak terhubung."
        )
        return

    try:
        master_df = prepare_master_dataframe(
            master_data
        )

    except ValueError as error:
        st.error(str(error))
        return

    if master_df.empty:
        st.warning(
            "Tidak ada kode saham yang dapat dipindai."
        )
        return

    st.metric(
        "Jumlah Master Saham",
        len(master_df),
    )

    column_period, column_mode, column_limit = (
        st.columns(3)
    )

    periode = column_period.selectbox(
        "Periode Analisis",
        options=[
            "6mo",
            "1y",
            "2y",
        ],
        index=1,
        key="ai_scanner_period",
    )

    scan_all = column_mode.checkbox(
        "Scan seluruh master",
        value=False,
        key="ai_scanner_scan_all",
    )

    maximum_limit = len(master_df)

    scan_limit = column_limit.number_input(
        "Jumlah saham",
        min_value=1,
        max_value=maximum_limit,
        value=min(20, maximum_limit),
        step=1,
        disabled=scan_all,
        key="ai_scanner_limit",
    )

    if scan_all:
        selected_df = master_df.copy()

        st.warning(
            f"Mode penuh akan menganalisis "
            f"{len(selected_df)} saham."
        )

    else:
        selected_df = master_df.head(
            int(scan_limit)
        )

    st.write(
        f"Akan dipindai: **{len(selected_df)} saham**"
    )

    start_scan = st.button(
        "🚀 Mulai AI Scanner",
        type="primary",
        key="start_ai_scanner",
    )

    if start_scan:
        result_df, failed_df = run_scanner(
            scan_df=selected_df,
            periode=periode,
        )

        st.session_state[
            SESSION_RESULT_KEY
        ] = result_df

        st.session_state[
            SESSION_FAILED_KEY
        ] = failed_df

        if result_df.empty:
            st.error(
                "Tidak ada saham yang berhasil dianalisis."
            )

        else:
            st.success(
                f"{len(result_df)} saham berhasil dianalisis."
            )

    render_scanner_results()