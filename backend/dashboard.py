import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import yfinance as yf

from io import BytesIO
from plotly.subplots import make_subplots
import plotly.graph_objects as go

from ai_scanner import render_ai_scanner_page
from candlestick import render_candlestick_page

API_URL = "http://127.0.0.1:8000"

st.title("📈 RadarSaham Dashboard")


def get_data(endpoint):
    try:
        response = requests.get(f"{API_URL}{endpoint}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API error: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Koneksi ke API gagal: {e}")
        return []

if st.button("🔄 Update Semua Harga"):
    hasil = get_data("/stocks/update-all")

    if isinstance(hasil, dict):
        st.success(f"Berhasil update {hasil.get('jumlah_update', 0)} saham")
        st.dataframe(pd.DataFrame(hasil.get("data", [])))


menu = st.sidebar.selectbox(
    "Pilih Menu",
    [
        "Semua Saham",
        "Top Broker",
        "Top Buy",
        "Ranking",
        "Cari Saham",
        "Filter Broker Score",
        "Grafik Broker Score",
        "Grafik Smart Ranking",
        "Pie Signal",
        "Grafik Foreign Flow",
        "Export Excel",
        "Top 10 Smart Score",
        "Alert Trading",
        "Candlestick Chart",
        "Import Broker Summary",
        "📋 Master Saham",
        "🤖 RadarSaham AI Scanner",
        "Auto Ranking Yahoo"
    ]
)

if menu == "Semua Saham":

    response = requests.get(f"{API_URL}/stocks-db")
    data = response.json()

    df = pd.DataFrame(data)

    st.subheader("Daftar Saham")

    # ===== FILTER =====
    min_foreign = st.number_input(
        "Minimal Foreign Flow",
        value=0
    )

    min_broker = st.slider(
        "Minimal Broker Score",
        min_value=0,
        max_value=100,
        value=0
    )

    buy_only = st.checkbox(
        "Tampilkan BUY saja"
    )

    # ===== PROSES FILTER =====
    df = df[
        (df["foreign_flow"] >= min_foreign) &
        (df["broker_score"] >= min_broker)
    ]

    if buy_only:
        df = df[
            df["signal"] == "BUY"
        ]

    st.dataframe(df, use_container_width=True)

elif menu == "Top Broker":
    data = get_data("/stocks/top-broker")
    df = pd.DataFrame(data)

    st.subheader("Top Broker Score")
    st.dataframe(df)


elif menu == "Top Buy":
    data = get_data("/stocks/top-buy")
    df = pd.DataFrame(data)

    st.subheader("Top Buy")
    st.dataframe(df)


elif menu == "Ranking":
    data = get_data("/stocks/ranking")
    df = pd.DataFrame(data)

    st.subheader("Ranking Saham")
    st.dataframe(df)


elif menu == "Cari Saham":
    st.subheader("Cari Saham")

    kode = st.text_input(
        "Masukkan kode saham",
        placeholder="Contoh: BBCA"
    ).upper()

    if st.button("Cari"):
        if not kode:
            st.warning("Masukkan kode saham terlebih dahulu.")
        else:
            data = get_data(f"/stocks/{kode}")

            if isinstance(data, dict) and data.get("message") != "Saham tidak ditemukan":
                st.success("Data ditemukan di database.")
                st.json(data)

            else:
                st.warning("Data tidak ada di database. Mengambil dari Yahoo Finance...")

                symbol = f"{kode}.JK"

                saham = yf.Ticker(symbol)
                info = saham.history(period="1mo")

                if info.empty:
                    st.error(f"Data {kode} tidak ditemukan di Yahoo Finance.")
                else:
                    harga_terakhir = float(info["Close"].iloc[-1])

                    st.success(f"Data {kode} ditemukan dari Yahoo Finance.")
                    st.metric("Harga Terakhir", f"{harga_terakhir:,.0f}")

                    st.dataframe(info.tail())

                    fig = px.line(
                        info.reset_index(),
                        x="Date",
                        y="Close",
                        title=f"Pergerakan Harga {kode} 1 Bulan"
                    )

                    st.plotly_chart(fig, use_container_width=True)

elif menu == "Filter Broker Score":

    st.subheader("🔍 Filter Broker Score")

    data = get_data("/stocks-db")
    df = pd.DataFrame(data)

    if df.empty:
        st.warning("Belum ada data saham.")

    elif "broker_score" not in df.columns:
        st.error("Kolom broker_score tidak ditemukan dalam data.")

    else:
        min_score = st.slider(
            "Minimal Broker Score",
            min_value=0,
            max_value=100,
            value=70
        )

        hasil_filter = df[
            df["broker_score"] >= min_score
        ].copy()

        hasil_filter = hasil_filter.sort_values(
            by="broker_score",
            ascending=False
        )

        if hasil_filter.empty:
            st.warning(
                f"Tidak ada saham dengan Broker Score minimal {min_score}."
            )
        else:
            st.success(
                f"Ditemukan {len(hasil_filter)} saham dengan "
                f"Broker Score minimal {min_score}."
            )

            kolom_tampil = [
                kolom for kolom in [
                    "kode",
                    "nama",
                    "harga",
                    "broker_score",
                    "foreign_flow",
                    "signal",
                    "smart_score"
                ]
                if kolom in hasil_filter.columns
            ]

            st.dataframe(
                hasil_filter[kolom_tampil],
                use_container_width=True
            )
elif menu == "Grafik Broker Score":

    st.subheader("📊 Grafik Broker Score")

    data = get_data("/stocks-db")
    df = pd.DataFrame(data)

    if df.empty:
        st.warning("Belum ada data saham.")

    elif (
        "kode" not in df.columns or
        "broker_score" not in df.columns
    ):
        st.error(
            "Kolom kode atau broker_score tidak ditemukan."
        )

    else:
        df = df.dropna(
            subset=["kode", "broker_score"]
        )

        jumlah_data = len(df)

        if jumlah_data == 0:
            st.warning(
                "Tidak ada data Broker Score yang dapat ditampilkan."
            )

        else:
            if jumlah_data == 1:
                jumlah_saham = 1
            else:
                jumlah_saham = st.slider(
                    "Jumlah saham yang ditampilkan",
                    min_value=1,
                    max_value=jumlah_data,
                    value=min(10, jumlah_data)
                )

            grafik_df = (
                df.sort_values(
                    by="broker_score",
                    ascending=False
                )
                .head(jumlah_saham)
            )

            fig = px.bar(
                grafik_df,
                x="kode",
                y="broker_score",
                text="broker_score",
                title=f"Top {jumlah_saham} Broker Score"
            )

            fig.update_traces(
                textposition="outside"
            )

            fig.update_layout(
                yaxis_title="Broker Score",
                xaxis_title="Kode Saham",
                yaxis_range=[0, 110]
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            kolom_tampil = [
                kolom for kolom in [
                    "kode",
                    "nama",
                    "broker_score",
                    "signal"
                ]
                if kolom in grafik_df.columns
            ]

            st.dataframe(
                grafik_df[kolom_tampil],
                use_container_width=True
            )

elif menu == "Grafik Smart Ranking":
    data = get_data("/stocks/smart-ranking")
    df = pd.DataFrame(data)

    st.subheader("⭐ Grafik Smart Ranking")

    if df.empty:
        st.warning("Belum ada data smart ranking.")
    else:
        fig = px.bar(
            df,
            x="kode",
            y="smart_score",
            text="smart_score",
            title="Smart Score per Saham"
        )

        fig.update_traces(textposition="outside")
        fig.update_layout(yaxis_range=[0, 110])

        st.plotly_chart(fig, use_container_width=True)


elif menu == "Pie Signal":
    data = get_data("/stocks-db")
    df = pd.DataFrame(data)

    st.subheader("🥧 Komposisi Signal Saham")

    if df.empty:
        st.warning("Belum ada data saham.")
    else:
        signal_count = df["signal"].value_counts().reset_index()
        signal_count.columns = ["signal", "jumlah"]

        fig = px.pie(
            signal_count,
            names="signal",
            values="jumlah",
            title="Komposisi BUY / HOLD / SELL"
        )

        st.plotly_chart(fig, use_container_width=True)

elif menu == "Import Broker Summary":

    st.subheader("📤 Import Broker Summary")

    st.info(
        "Upload file Excel atau CSV yang berisi data Broker Summary."
    )

    uploaded_file = st.file_uploader(
        "Pilih file Broker Summary",
        type=["xlsx", "xls", "csv"]
    )

    if uploaded_file is not None:

        try:
            nama_file = uploaded_file.name.lower()

            if nama_file.endswith(".csv"):
                broker_df = pd.read_csv(uploaded_file)
            else:
                broker_df = pd.read_excel(uploaded_file)

            if broker_df.empty:
                st.warning("File yang diupload tidak memiliki data.")

            else:
                broker_df.columns = (
                    broker_df.columns
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .str.replace(" ", "_")
                )

                st.success("File berhasil dibaca.")

                st.write("### Preview Data")

                st.dataframe(
                    broker_df.head(20),
                    use_container_width=True
                )

                st.write(
                    f"Jumlah baris: **{len(broker_df)}**"
                )

                st.write(
                    f"Jumlah kolom: **{len(broker_df.columns)}**"
                )

                st.write(
                    "**Daftar kolom:** "
                    + ", ".join(broker_df.columns)
                )

                kolom_wajib = ["kode"]

                kolom_tidak_ada = [
                    kolom for kolom in kolom_wajib
                    if kolom not in broker_df.columns
                ]

                if kolom_tidak_ada:
                    st.warning(
                        "Kolom wajib belum ditemukan: "
                        + ", ".join(kolom_tidak_ada)
                    )

                else:
                    broker_df["kode"] = (
                        broker_df["kode"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                    )

                    st.success(
                        "Format dasar Broker Summary sudah valid."
                    )

                    output = BytesIO()

                    with pd.ExcelWriter(
                        output,
                        engine="openpyxl"
                    ) as writer:
                        broker_df.to_excel(
                            writer,
                            index=False,
                            sheet_name="Broker Summary"
                        )

                    st.download_button(
                        label="Download Hasil Bersih",
                        data=output.getvalue(),
                        file_name="broker_summary_bersih.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-"
                            "officedocument.spreadsheetml.sheet"
                        )
                    )

        except Exception as error:
            st.error(
                f"Gagal membaca file Broker Summary: {error}"
            )

elif menu == "Grafik Foreign Flow":
    data = get_data("/stocks-db")
    df = pd.DataFrame(data)

    st.subheader("📈 Grafik Foreign Flow")

    if df.empty:
        st.warning("Belum ada data foreign flow.")
    else:
        fig = px.bar(
            df,
            x="kode",
            y="foreign_flow",
            text="foreign_flow",
            title="Foreign Flow per Saham"
        )

        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)


elif menu == "Export Excel":
    data = get_data("/stocks/smart-ranking")
    df = pd.DataFrame(data)

    st.subheader("📥 Export Smart Ranking ke Excel")

    if df.empty:
        st.warning("Belum ada data untuk diexport.")
    else:
        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(
                writer,
                index=False,
                sheet_name="Smart Ranking"
            )

        st.download_button(
            label="Download Excel",
            data=output.getvalue(),
            file_name="smart_ranking.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


elif menu == "Top 10 Smart Score":
    data = get_data("/stocks/smart-ranking")
    df = pd.DataFrame(data)

    st.subheader("🏆 Top 10 Smart Score")

    if df.empty:
        st.warning("Belum ada data.")
    else:
        top10 = df.head(10).copy()

        top10["support"] = top10["low_price"]
        top10["resistance"] = top10["high_price"]

        top10 = top10.reset_index(drop=True)
        top10.index = top10.index + 1
        top10.index.name = "Rank"

        st.dataframe(
            top10[
                [
                    "kode",
                    "nama",
                    "harga",
                    "support",
                    "resistance",
                    "smart_score"
                ]
            ]
        )

        fig = px.bar(
            top10,
            x="kode",
            y="smart_score",
            text="smart_score",
            title="🏆 Top 10 Smart Score"
        )

        fig.update_traces(textposition="outside")

        st.plotly_chart(fig, use_container_width=True)


elif menu == "Alert Trading":
    data = get_data("/stocks/smart-ranking")
    df = pd.DataFrame(data)

    st.subheader("🚨 Alert Trading")

    if df.empty:
        st.warning("Belum ada data saham.")
    else:
        for _, row in df.iterrows():
            kode = row.get("kode")
            harga = row.get("harga")
            support = row.get("low_price")
            resistance = row.get("high_price")
            smart_score = row.get("smart_score", 0)

            st.markdown(f"## {kode}")

            if smart_score >= 85:
                st.success(f"🔥 STRONG BUY | Smart Score: {smart_score}")

            if support is not None and harga is not None:
                if harga <= support * 1.02:
                    st.info(
                        f"🟢 BUY ZONE | Harga {harga} dekat support {support}"
                    )

                if harga < support:
                    st.error(
                        f"⚠️ CUT LOSS ALERT! Harga {harga} turun di bawah support {support}"
                    )

            if resistance is not None and harga is not None:
                if harga >= resistance * 0.98:
                    st.warning(
                        f"🔴 TAKE PROFIT ZONE | Harga {harga} dekat resistance {resistance}"
                    )

                if harga > resistance:
                    st.success(
                        f"🚀 BREAKOUT! Harga {harga} berhasil menembus resistance {resistance}"
                    )

            st.write(
                f"Harga: {harga} | Support: {support} | Resistance: {resistance}"
            )

            if (
                harga is not None
                and support is not None
                and resistance is not None
            ):
                stop_loss = support * 0.98
                target_profit = resistance

                risk = harga - stop_loss
                reward = target_profit - harga

                if risk > 0:
                    risk_reward = reward / risk
                else:
                    risk_reward = 0

                st.write(f"Stop Loss: {stop_loss:.0f}")
                st.write(f"Target Profit: {target_profit:.0f}")
                st.write(f"Risk Reward: 1 : {risk_reward:.2f}")

                if risk_reward >= 2:
                    st.success("✅ Risk Reward Sangat Menarik")
                elif risk_reward >= 1:
                    st.info("ℹ️ Risk Reward Cukup Baik")
                else:
                    st.warning("⚠️ Risk Reward Kurang Menarik")

            st.divider()
    
elif menu == "Candlestick Chart":
    render_candlestick_page()
    
elif menu == "📋 Master Saham":

    st.subheader("📋 Master Saham BEI")

    data = get_data("/stocks/master")
    df_master = pd.DataFrame(data)

    if df_master.empty:
        st.warning(
            "Master saham masih kosong. "
            "Silakan import file Excel melalui endpoint backend."
        )

    else:
        st.metric(
            "Jumlah Saham",
            len(df_master)
        )

        keyword = st.text_input(
            "Cari kode atau nama perusahaan",
            placeholder="Contoh: BBCA atau Bank Central Asia"
        ).strip()

        hasil_master = df_master.copy()

        if keyword:
            hasil_master = hasil_master[
                hasil_master["kode"]
                .astype(str)
                .str.contains(
                    keyword,
                    case=False,
                    na=False
                )
                |
                hasil_master["nama"]
                .astype(str)
                .str.contains(
                    keyword,
                    case=False,
                    na=False
                )
            ]

        hasil_master = hasil_master.sort_values(
            by="kode",
            ascending=True
        ).reset_index(drop=True)

        hasil_master.index = hasil_master.index + 1
        hasil_master.index.name = "No"

        st.write(
            f"Ditemukan **{len(hasil_master)}** saham."
        )

        st.dataframe(
            hasil_master,
            use_container_width=True,
            height=600
        )

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:
            hasil_master.reset_index().to_excel(
                writer,
                index=False,
                sheet_name="Master Saham"
            )

        st.download_button(
            label="📥 Download Master Saham",
            data=output.getvalue(),
            file_name="master_saham_bei.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )

elif menu == "🤖 RadarSaham AI Scanner":
    render_ai_scanner_page(get_data)

elif menu == "Auto Ranking Yahoo":

    st.subheader("🤖 Auto Ranking Saham dari Yahoo Finance")

    master_saham = get_data("/stocks/master")

    daftar_saham = [
        item["kode"]
        for item in master_saham
        if isinstance(item, dict) and item.get("kode")
    ]

    if not daftar_saham:
        st.warning("Master saham belum tersedia.")
        st.stop()

    hasil_ranking = []

    if st.button("Mulai Auto Ranking"):

        progress = st.progress(0)
        status = st.empty()

        for index, kode in enumerate(daftar_saham):
            status.write(f"Sedang menganalisis {kode}...")

            symbol = f"{kode}.JK"

            try:
                data = yf.download(
                    symbol,
                    period="6mo",
                    auto_adjust=False,
                    progress=False
                )

                if data.empty:
                    progress.progress((index + 1) / len(daftar_saham))
                    continue

                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)

                data = data.reset_index()

                if len(data) < 50:
                    progress.progress((index + 1) / len(daftar_saham))
                    continue

                data["MA20"] = data["Close"].rolling(window=20).mean()
                data["MA50"] = data["Close"].rolling(window=50).mean()

                delta = data["Close"].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)

                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()

                rs = avg_gain / avg_loss.replace(0, pd.NA)
                data["RSI14"] = 100 - (100 / (1 + rs))

                ema12 = data["Close"].ewm(
                    span=12,
                    adjust=False
                ).mean()

                ema26 = data["Close"].ewm(
                    span=26,
                    adjust=False
                ).mean()

                data["MACD"] = ema12 - ema26
                data["Signal_Line"] = data["MACD"].ewm(
                    span=9,
                    adjust=False
                ).mean()

                close_terakhir = float(data["Close"].iloc[-1])
                volume_terakhir = float(data["Volume"].iloc[-1])
                volume_rata20 = float(data["Volume"].tail(20).mean())

                ma20 = data["MA20"].iloc[-1]
                ma50 = data["MA50"].iloc[-1]
                rsi = data["RSI14"].iloc[-1]
                macd = data["MACD"].iloc[-1]
                signal = data["Signal_Line"].iloc[-1]

                support = float(data["Low"].tail(20).min())
                resistance = float(data["High"].tail(20).max())

                if support > 0:
                    jarak_support = (
                        (close_terakhir - support) / support
                    ) * 100
                else:
                    jarak_support = 0

                if close_terakhir > 0:
                    jarak_resistance = (
                        (resistance - close_terakhir) /
                        close_terakhir
                    ) * 100
                else:
                    jarak_resistance = 0

                if pd.notna(ma20) and pd.notna(ma50) and ma20 > ma50:
                    skor_trend = 25
                else:
                    skor_trend = 10

                if volume_terakhir > volume_rata20:
                    skor_volume = 20
                else:
                    skor_volume = 10

                if 0 <= jarak_support <= 5:
                    skor_support = 20
                elif 5 < jarak_support <= 10:
                    skor_support = 10
                else:
                    skor_support = 5

                if jarak_resistance >= 10:
                    skor_resistance = 15
                elif jarak_resistance >= 5:
                    skor_resistance = 10
                else:
                    skor_resistance = 5

                if pd.notna(rsi):
                    if 40 <= rsi <= 65:
                        skor_rsi = 10
                    elif 30 <= rsi < 40:
                        skor_rsi = 7
                    elif 65 < rsi <= 75:
                        skor_rsi = 5
                    else:
                        skor_rsi = 2
                else:
                    skor_rsi = 0

                if pd.notna(macd) and pd.notna(signal) and macd > signal:
                    skor_macd = 10
                else:
                    skor_macd = 5

                total_skor = (
                    skor_trend +
                    skor_volume +
                    skor_support +
                    skor_resistance +
                    skor_rsi +
                    skor_macd
                )

                risiko = close_terakhir - support
                reward = resistance - close_terakhir

                if risiko > 0:
                    risk_reward = reward / risiko
                else:
                    risk_reward = 0

                if total_skor >= 85 and risk_reward >= 2:
                    rekomendasi = "🔥 STRONG BUY"
                elif total_skor >= 70:
                    rekomendasi = "🟢 BUY"
                elif total_skor >= 55:
                    rekomendasi = "🟡 HOLD / WATCHLIST"
                elif total_skor >= 40:
                    rekomendasi = "🟠 REDUCE"
                else:
                    rekomendasi = "🔴 SELL / AVOID"

                hasil_ranking.append(
                    {
                        "kode": kode,
                        "harga": round(close_terakhir, 0),
                        "support": round(support, 0),
                        "resistance": round(resistance, 0),
                        "RSI": round(float(rsi), 2)
                        if pd.notna(rsi)
                        else None,
                        "MACD": round(float(macd), 2),
                        "risk_reward": round(risk_reward, 2),
                        "total_skor": total_skor,
                        "rekomendasi": rekomendasi
                    }
                )

            except Exception as error:
                st.warning(
                    f"Gagal menganalisis {kode}: {error}"
                )

            progress.progress(
                (index + 1) / len(daftar_saham)
            )

        status.empty()

        df_ranking = pd.DataFrame(hasil_ranking)

        if df_ranking.empty:
            st.warning(
                "Tidak ada data saham yang berhasil dianalisis."
            )
        else:
            df_ranking = df_ranking.sort_values(
                by="total_skor",
                ascending=False
            ).reset_index(drop=True)

            df_ranking.index = df_ranking.index + 1
            df_ranking.index.name = "Rank"

            st.success("Auto Ranking selesai.")

            st.dataframe(
                df_ranking,
                use_container_width=True
            )

            fig = px.bar(
                df_ranking.reset_index(),
                x="kode",
                y="total_skor",
                text="total_skor",
                title="Ranking Saham Berdasarkan Total Skor"
            )

            fig.update_traces(
                textposition="outside"
            )

            fig.update_layout(
                yaxis_range=[0, 100]
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )