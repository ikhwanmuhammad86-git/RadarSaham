import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from io import BytesIO

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
        "Alert Trading"
    ]
)


if menu == "Semua Saham":
    data = get_data("/stocks-db")
    df = pd.DataFrame(data)

    st.subheader("Daftar Saham")
    st.dataframe(df)


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
    )

    if st.button("Cari"):
        if kode:
            data = get_data(f"/stocks/{kode.upper()}")
            st.json(data)
        else:
            st.warning("Masukkan kode saham terlebih dahulu.")


elif menu == "Filter Broker Score":
    st.subheader("Filter Broker Score")

    min_score = st.slider(
        "Minimal Broker Score",
        min_value=0,
        max_value=100,
        value=80
    )

    data = get_data("/stocks/top-broker")
    df = pd.DataFrame(data)

    if df.empty:
        st.warning("Belum ada data.")
    else:
        df = df[df["broker_score"].fillna(0) >= min_score]
        st.dataframe(df)


elif menu == "Grafik Broker Score":
    data = get_data("/stocks/top-broker")
    df = pd.DataFrame(data)

    st.subheader("📊 Grafik Broker Score")

    if df.empty:
        st.warning("Belum ada data broker score.")
    else:
        fig = px.bar(
            df,
            x="kode",
            y="broker_score",
            text="broker_score",
            title="Broker Score per Saham"
        )

        fig.update_traces(textposition="outside")
        fig.update_layout(yaxis_range=[0, 110])

        st.plotly_chart(fig, use_container_width=True)


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