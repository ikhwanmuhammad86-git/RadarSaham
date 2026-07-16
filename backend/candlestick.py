import streamlit as st
import yfinance as yf
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from technical import (
    calculate_ma,
    calculate_rsi,
    calculate_macd,
    calculate_vwap,
    calculate_ema
)

def render_candlestick_page():

    st.subheader("📈 Candlestick Chart")

    kode = st.text_input(
        "Kode Saham",
        value="BBCA",
        key="cs_kode"
    ).upper().strip()

    timeframe_options = {
        "1 Jam": {
            "period": "1mo",
            "interval": "1h"
        },
        "1 Hari": {
            "period": "6mo",
            "interval": "1d"
        },
        "1 Minggu": {
            "period": "2y",
            "interval": "1wk"
        },
        "1 Bulan": {
            "period": "1mo",
            "interval": "1d"
        },
        "3 Bulan": {
            "period": "3mo",
            "interval": "1d"
        },
        "6 Bulan": {
            "period": "6mo",
            "interval": "1d"
        },
        "1 Tahun": {
            "period": "1y",
            "interval": "1d"
        }
    }

    pilihan_timeframe = st.selectbox(
        "Timeframe Analisis",
        list(timeframe_options.keys()),
        index=1,
        key="cs_timeframe"
    )

    period = timeframe_options[pilihan_timeframe]["period"]
    interval = timeframe_options[pilihan_timeframe]["interval"]

    st.caption(
        f"Periode data: {period} | "
        f"Interval candle: {interval}"
    )

    if st.button(
        "Tampilkan Grafik",
        key="cs_button",
        type="primary",
        use_container_width=True
    ):

        if not kode:
            st.warning("Masukkan kode saham terlebih dahulu.")
            return

        symbol = f"{kode}.JK"

        try:
            with st.spinner(
                f"Mengambil data {kode} dari Yahoo Finance..."
            ):
                data = yf.download(
                    symbol,
                    period=period,
                    interval=interval,
                    auto_adjust=False,
                    progress=False,
                    threads=False
                )

        except Exception as error:
            st.error(
                f"Gagal mengambil data {kode}: {error}"
            )
            return

        if data.empty:
            st.error(
                f"Data {kode} untuk timeframe "
                f"{pilihan_timeframe} tidak ditemukan."
            )
            return

        # Merapikan MultiIndex dari yfinance
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data = data.reset_index()

        # ==================================
        # MENENTUKAN KOLOM WAKTU
        # ==================================

        if "Datetime" in data.columns:
            time_column = "Datetime"

        elif "Date" in data.columns:
            time_column = "Date"

        else:
            st.error(
                "Kolom waktu Date atau Datetime tidak ditemukan."
            )
            return

        # Menghapus timezone agar aman untuk Plotly
        if pd.api.types.is_datetime64_any_dtype(
            data[time_column]
        ):
            try:
                data[time_column] = (
                    data[time_column]
                    .dt.tz_localize(None)
                )
            except TypeError:
                pass

        # Mengubah kolom numerik menjadi angka
        numeric_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]

        for column in numeric_columns:
            if column in data.columns:
                data[column] = pd.to_numeric(
                    data[column],
                    errors="coerce"
                )

        # Menghapus baris harga yang tidak valid
        data = data.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close"
            ]
        ).copy()

        if data.empty:
            st.error(
                "Data harga tidak valid setelah proses pembersihan."
            )
            return

        # ==================================
        # INDIKATOR TEKNIKAL
        # ==================================

        data = calculate_ma(data)
        data = calculate_rsi(data)
        data = calculate_macd(data)
        data = calculate_vwap(data)
        data = calculate_ema(data)

        # ==================================
        # SUPPORT & RESISTANCE
        # ==================================

        jumlah_candle_sr = min(20, len(data))

        support = (
            data["Low"]
            .tail(jumlah_candle_sr)
            .min()
        )

        resistance = (
            data["High"]
            .tail(jumlah_candle_sr)
            .max()
        )

        st.success(
            f"Data {kode} berhasil diambil: "
            f"{len(data)} candle."
        )

        # ==================================
        # PREVIEW DATA
        # ==================================

        preview_columns = [
        time_column,
        "Close",
        "VWAP",
        "MA20",
        "MA50",
        "EMA20",
        "EMA50",
        "EMA200",
        "RSI14",
        "MACD",
        "Signal_Line",
        "Volume"
    ]

        preview_columns = [
            column
            for column in preview_columns
            if column in data.columns
        ]

        st.write("Preview Data")

        st.dataframe(
            data[preview_columns].tail(10),
            use_container_width=True,
            hide_index=True
        )

        # ==================================
        # MEMBUAT GRAFIK
        # ==================================

        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[
                0.50,
                0.20,
                0.15,
                0.15
            ],
            subplot_titles=[
                "Candlestick dan Moving Average",
                "Volume",
                "RSI",
                "MACD"
            ]
        )

        # MA20
        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["MA20"],
                mode="lines",
                name="MA20",
                line=dict(
                    color="blue",
                    width=2
                )
            ),
            row=1,
            col=1
        )

        # MA50
        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["MA50"],
                mode="lines",
                name="MA50",
                line=dict(
                    color="red",
                    width=2
                )
            ),
            row=1,
            col=1
        )

        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["VWAP"],
                mode="lines",
                name="VWAP",
                line=dict(
                color="gold",
                width=3,
                dash="dot"
                )
            ),
            row=1,
            col=1
        )

        # EMA20
        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["EMA20"],
                mode="lines",
                name="EMA20",
                line=dict(
                    color="orange",
                    width=2
                )
            ),
            row=1,
            col=1
        )

        # EMA50
        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["EMA50"],
                mode="lines",
                name="EMA50",
                line=dict(
                    color="purple",
                    width=2
                )
            ),
            row=1,
            col=1
        )

        # EMA200
        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["EMA200"],
                mode="lines",
                name="EMA200",
                line=dict(
                    color="black",
                    width=3
                )
            ),
            row=1,
            col=1
        )

        # Support
        fig.add_hline(
            y=float(support),
            line_dash="dash",
            annotation_text=(
                f"Support {support:,.0f}"
            ),
            annotation_position="bottom left",
            row=1,
            col=1
        )

        # Resistance
        fig.add_hline(
            y=float(resistance),
            line_dash="dash",
            annotation_text=(
                f"Resistance {resistance:,.0f}"
            ),
            annotation_position="top left",
            row=1,
            col=1
        )

        # Volume
        fig.add_trace(
            go.Bar(
                x=data[time_column],
                y=data["Volume"],
                name="Volume"
            ),
            row=2,
            col=1
        )

        # RSI
        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["RSI14"],
                mode="lines",
                name="RSI 14"
            ),
            row=3,
            col=1
        )

        fig.add_hline(
            y=70,
            line_dash="dash",
            annotation_text="Overbought",
            row=3,
            col=1
        )

        fig.add_hline(
            y=30,
            line_dash="dash",
            annotation_text="Oversold",
            row=3,
            col=1
        )

        # MACD
        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["MACD"],
                mode="lines",
                name="MACD"
            ),
            row=4,
            col=1
        )

        fig.add_trace(
            go.Scatter(
                x=data[time_column],
                y=data["Signal_Line"],
                mode="lines",
                name="Signal MACD"
            ),
            row=4,
            col=1
        )

        fig.add_trace(
            go.Bar(
                x=data[time_column],
                y=data["MACD_Histogram"],
                name="MACD Histogram"
            ),
            row=4,
            col=1
        )

        fig.add_hline(
            y=0,
            line_dash="dot",
            row=4,
            col=1
        )

        # ==================================
        # JUDUL SUMBU
        # ==================================

        fig.update_yaxes(
            title_text="Harga",
            row=1,
            col=1
        )

        fig.update_yaxes(
            title_text="Volume",
            row=2,
            col=1
        )

        fig.update_yaxes(
            title_text="RSI",
            range=[0, 100],
            row=3,
            col=1
        )

        fig.update_yaxes(
            title_text="MACD",
            row=4,
            col=1
        )

        # Menonaktifkan range slider
        fig.update_xaxes(
            rangeslider_visible=False,
            row=1,
            col=1
        )

        fig.update_layout(
            title=(
                f"{kode} | {pilihan_timeframe}\n"
                "Candlestick • MA • EMA • VWAP • RSI • MACD"
            ),
            height=1200,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            ),
            margin=dict(
                l=30,
                r=30,
                t=120,
                b=30
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        # ==================================
        # INFORMASI SUPPORT & RESISTANCE
        # ==================================

        col1, col2, col3 = st.columns(3)

        harga_terakhir = float(
            data["Close"].iloc[-1]
        )

        col1.metric(
            "Harga Terakhir",
            f"Rp {harga_terakhir:,.0f}"
        )

        col2.success(
            f"Support\n\nRp {support:,.0f}"
        )

        col3.warning(
            f"Resistance\n\nRp {resistance:,.0f}"
        )