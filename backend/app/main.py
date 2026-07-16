from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy import text
from app.database.connection import engine
from app.models import Stock
from io import BytesIO
import pandas as pd
import yfinance as yf

app = FastAPI(title="RadarSaham API")


# ==========================
# MASTER SAHAM
# ==========================

def buat_tabel_master_saham():
    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS master_stocks (
                    id SERIAL PRIMARY KEY,
                    kode VARCHAR(20) NOT NULL UNIQUE,
                    nama VARCHAR(255) NOT NULL
                )
            """)
        )
buat_tabel_master_saham()

@app.get("/stocks/master")
def get_master_saham():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT kode, nama
                FROM master_stocks
                ORDER BY kode
            """)
        )

        return [
            dict(row._mapping)
            for row in result
        ]


@app.post("/stocks/master/import")
async def import_master_saham(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Nama file tidak tersedia."
        )

    nama_file = file.filename.lower()
    isi_file = await file.read()

    try:
        if nama_file.endswith(".csv"):
            df = pd.read_csv(
                BytesIO(isi_file)
            )

        elif nama_file.endswith((".xlsx", ".xls")):
            df = pd.read_excel(
                BytesIO(isi_file)
            )

        else:
            raise HTTPException(
                status_code=400,
                detail="Gunakan file CSV, XLS, atau XLSX."
            )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file: {error}"
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="File tidak memiliki data."
        )

    # ==========================
    # NORMALISASI NAMA KOLOM
    # ==========================

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    # File BEI menggunakan kolom:
    # "Kode" dan "Nama Perusahaan"
    # Setelah dinormalisasi menjadi:
    # "kode" dan "nama_perusahaan"

    if "nama_perusahaan" in df.columns:
        df = df.rename(
            columns={
                "nama_perusahaan": "nama"
            }
        )

    # ==========================
    # VALIDASI KOLOM
    # ==========================

    if "kode" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "Kolom 'Kode' tidak ditemukan. "
                "Pastikan file memiliki kolom Kode."
            )
        )

    if "nama" not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=(
                "Kolom 'Nama Perusahaan' tidak ditemukan. "
                "Pastikan file memiliki kolom Nama Perusahaan."
            )
        )

    # ==========================
    # PEMBERSIHAN DATA
    # ==========================

    df = df[
        ["kode", "nama"]
    ].copy()

    df = df.dropna(
        subset=["kode", "nama"]
    )

    df["kode"] = (
        df["kode"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["nama"] = (
        df["nama"]
        .astype(str)
        .str.strip()
    )

    # Menghapus akhiran .JK jika sudah ada
    df["kode"] = (
        df["kode"]
        .str.replace(
            ".JK",
            "",
            regex=False
        )
    )

    # Hanya menyimpan kode yang tidak kosong
    df = df[
        (df["kode"] != "") &
        (df["nama"] != "")
    ]

    # Hapus kode saham duplikat
    df = df.drop_duplicates(
        subset=["kode"],
        keep="last"
    )

    jumlah_baru = 0
    jumlah_update = 0
    jumlah_gagal = 0

    # ==========================
    # SIMPAN KE DATABASE
    # ==========================

    with engine.begin() as conn:
        for _, row in df.iterrows():
            kode = row["kode"]
            nama = row["nama"]

            try:
                existing = conn.execute(
                    text("""
                        SELECT id
                        FROM master_stocks
                        WHERE kode = :kode
                    """),
                    {
                        "kode": kode
                    }
                ).fetchone()

                if existing:
                    conn.execute(
                        text("""
                            UPDATE master_stocks
                            SET nama = :nama
                            WHERE kode = :kode
                        """),
                        {
                            "kode": kode,
                            "nama": nama
                        }
                    )

                    jumlah_update += 1

                else:
                    conn.execute(
                        text("""
                            INSERT INTO master_stocks
                            (
                                kode,
                                nama
                            )
                            VALUES
                            (
                                :kode,
                                :nama
                            )
                        """),
                        {
                            "kode": kode,
                            "nama": nama
                        }
                    )

                    jumlah_baru += 1

            except Exception:
                jumlah_gagal += 1

    return {
        "message": "Import master saham selesai.",
        "jumlah_data_file": len(df),
        "jumlah_baru": jumlah_baru,
        "jumlah_update": jumlah_update,
        "jumlah_gagal": jumlah_gagal
    }
    
@app.get("/")
def root():
    return {"message": "Selamat datang di RadarSaham API"}


@app.get("/db-test")
def db_test():
    try:
        conn = engine.connect()
        conn.close()
        return {"database": "connected"}
    except Exception as e:
        return {"database": "failed", "error": str(e)}


@app.get("/stocks-db")
def get_stocks_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM stocks"))
        return [dict(row._mapping) for row in result]


@app.post("/stocks")
def add_stock(data: Stock):
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO stocks
                (
                    kode, nama, harga, akumulasi, signal,
                    volume, foreign_flow, broker_score,
                    low_price, high_price
                )
                VALUES
                (
                    :kode, :nama, :harga, :akumulasi, :signal,
                    :volume, :foreign_flow, :broker_score,
                    :low_price, :high_price
                )
            """),
            {
                "kode": data.kode.upper(),
                "nama": data.nama,
                "harga": data.harga,
                "akumulasi": data.akumulasi,
                "signal": data.signal.upper(),
                "volume": data.volume,
                "foreign_flow": data.foreign_flow,
                "broker_score": data.broker_score,
                "low_price": data.low_price,
                "high_price": data.high_price,
            },
        )
        conn.commit()

    return {"message": "Data berhasil ditambahkan"}


@app.put("/stocks/{kode}")
def update_stock(kode: str, data: Stock):
    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE stocks
                SET
                    nama = :nama,
                    harga = :harga,
                    akumulasi = :akumulasi,
                    signal = :signal,
                    volume = :volume,
                    foreign_flow = :foreign_flow,
                    broker_score = :broker_score,
                    low_price = :low_price,
                    high_price = :high_price
                WHERE kode = :kode
            """),
            {
                "kode": kode.upper(),
                "nama": data.nama,
                "harga": data.harga,
                "akumulasi": data.akumulasi,
                "signal": data.signal.upper(),
                "volume": data.volume,
                "foreign_flow": data.foreign_flow,
                "broker_score": data.broker_score,
                "low_price": data.low_price,
                "high_price": data.high_price,
            },
        )
        conn.commit()

    return {"message": f"Saham {kode.upper()} berhasil diperbarui"}


@app.delete("/stocks/{kode}")
def delete_stock(kode: str):
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM stocks WHERE kode = :kode"),
            {"kode": kode.upper()},
        )
        conn.commit()

    return {"message": f"Saham {kode.upper()} berhasil dihapus"}


@app.get("/stocks/buy")
def saham_buy():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM stocks WHERE signal='BUY'"))
        return [dict(row._mapping) for row in result]


@app.get("/stocks/hold")
def saham_hold():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM stocks WHERE signal='HOLD'"))
        return [dict(row._mapping) for row in result]


@app.get("/stocks/sell")
def saham_sell():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM stocks WHERE signal='SELL'"))
        return [dict(row._mapping) for row in result]


@app.get("/stocks/akumulasi/tinggi")
def akumulasi_tinggi():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM stocks WHERE akumulasi='tinggi'")
        )
        return [dict(row._mapping) for row in result]


@app.get("/stocks/top-buy")
def top_buy():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT *
                FROM stocks
                WHERE signal = 'BUY'
                AND akumulasi = 'tinggi'
            """)
        )
        return [dict(row._mapping) for row in result]


@app.get("/stocks/ranking")
def stock_ranking():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT *,
                    CASE
                        WHEN signal = 'BUY' AND akumulasi = 'tinggi' THEN 90
                        WHEN signal = 'BUY' AND akumulasi = 'sedang' THEN 75
                        WHEN signal = 'HOLD' AND akumulasi = 'tinggi' THEN 65
                        WHEN signal = 'HOLD' THEN 50
                        WHEN signal = 'SELL' THEN 20
                        ELSE 0
                    END AS score
                FROM stocks
                ORDER BY score DESC
            """)
        )
        return [dict(row._mapping) for row in result]


@app.get("/stocks/rekomendasi")
def rekomendasi():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT *,
                    CASE
                        WHEN signal='BUY' AND akumulasi='tinggi' THEN 90
                        WHEN signal='BUY' AND akumulasi='sedang' THEN 75
                        WHEN signal='HOLD' AND akumulasi='tinggi' THEN 65
                        WHEN signal='SELL' THEN 20
                        ELSE 0
                    END AS score
                FROM stocks
                WHERE signal='BUY'
                AND akumulasi='tinggi'
                ORDER BY harga ASC
            """)
        )
        return [dict(row._mapping) for row in result]


@app.get("/stocks/top-broker")
def top_broker():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT *
                FROM stocks
                ORDER BY broker_score DESC
                LIMIT 10
            """)
        )
        return [dict(row._mapping) for row in result]


@app.get("/stocks/smart-ranking")
def smart_ranking():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    id,
                    kode,
                    nama,
                    harga,
                    akumulasi,
                    signal,
                    volume,
                    foreign_flow,
                    broker_score,
                    low_price,
                    high_price,

                    ROUND(
                        (
                            COALESCE(broker_score, 0) * 0.4
                        ) +

                        (
                            CASE
                                WHEN foreign_flow >= 1000000000 THEN 100
                                WHEN foreign_flow >= 500000000 THEN 80
                                WHEN foreign_flow >= 100000000 THEN 60
                                WHEN foreign_flow > 0 THEN 40
                                ELSE 20
                            END
                        ) * 0.3 +

                        (
                            CASE
                                WHEN signal = 'BUY' THEN 100
                                WHEN signal = 'HOLD' THEN 60
                                WHEN signal = 'SELL' THEN 20
                                ELSE 0
                            END
                        ) * 0.2 +

                        (
                            CASE
                                WHEN akumulasi = 'tinggi' THEN 100
                                WHEN akumulasi = 'sedang' THEN 70
                                WHEN akumulasi = 'rendah' THEN 40
                                ELSE 0
                            END
                        ) * 0.1

                    ,2) AS smart_score

                FROM stocks
                ORDER BY smart_score DESC
            """)
        )

        return [dict(row._mapping) for row in result]


@app.get("/stocks/top10-smart")
def top10_smart():
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    id,
                    kode,
                    nama,
                    harga,
                    akumulasi,
                    signal,
                    volume,
                    foreign_flow,
                    broker_score,
                    low_price,
                    high_price,
                    COALESCE(broker_score, 0) AS smart_score
                FROM stocks
                ORDER BY broker_score DESC
                LIMIT 10
            """)
        )
        return [dict(row._mapping) for row in result]


@app.get("/stocks/update-all")
def update_semua_harga():
    updated = []

    with engine.connect() as conn:
        result = conn.execute(text("SELECT kode FROM stocks"))
        daftar_saham = result.fetchall()

        for row in daftar_saham:
            kode = row[0].upper()

            try:
                symbol = f"{kode}.JK"
                saham = yf.Ticker(symbol)
                data = saham.history(period="1d")

                if not data.empty:
                    harga = float(data["Close"].iloc[-1])

                    conn.execute(
                        text("""
                            UPDATE stocks
                            SET harga = :harga
                            WHERE kode = :kode
                        """),
                        {
                            "harga": harga,
                            "kode": kode,
                        },
                    )

                    updated.append(
                        {
                            "kode": kode,
                            "harga": harga,
                        }
                    )

            except Exception as e:
                print(f"Gagal update {kode}: {e}")

        conn.commit()

    return {
        "jumlah_update": len(updated),
        "data": updated,
    }


@app.get("/stocks/update/{kode}")
def update_harga_otomatis(kode: str):
    kode = kode.upper()
    symbol = f"{kode}.JK"

    try:
        saham = yf.Ticker(symbol)
        data = saham.history(period="1d")

        if data.empty:
            return {"error": f"Data {kode} tidak ditemukan"}

        harga = float(data["Close"].iloc[-1])

        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE stocks
                    SET harga = :harga
                    WHERE kode = :kode
                """),
                {
                    "harga": harga,
                    "kode": kode,
                },
            )
            conn.commit()

        return {
            "kode": kode,
            "harga_terbaru": harga,
            "status": "updated",
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/stocks/{kode}")
def get_stock(kode: str):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM stocks WHERE kode = :kode"),
            {"kode": kode.upper()},
        )

        stock = result.fetchone()

        if stock is None:
            return {"message": "Saham tidak ditemukan"}

        return dict(stock._mapping)
