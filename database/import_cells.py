import os

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

CSV_PATH = "data/cell_towers.csv"

COLUMNS = [
    "radio",
    "mcc",
    "net",
    "area",
    "cell",
    "unit",
    "lon",
    "lat",
    "range",
    "samples",
    "changeable",
    "created",
    "updated",
    "averageSignal",
]


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "telecom_network"),
        user=os.getenv("POSTGRES_USER", "telecom"),
        password=os.getenv("POSTGRES_PASSWORD", "telecom"),
    )


def load_data():
    df = pd.read_csv(
        CSV_PATH,
        header=None,
        names=COLUMNS,
    )

    return df


def main():
    print("Loading OpenCelliD data...")

    df = load_data()

    print(f"Rows loaded from CSV: {len(df):,}")

    records = [
        (
            row.radio,
            int(row.mcc),
            int(row.net) if pd.notna(row.net) else None,
            int(row.area) if pd.notna(row.area) else None,
            int(row.cell),
            int(row.unit) if pd.notna(row.unit) else None,
            float(row.lon) if pd.notna(row.lon) else None,
            float(row.lat) if pd.notna(row.lat) else None,
            int(row.range) if pd.notna(row.range) else None,
            int(row.samples) if pd.notna(row.samples) else None,
            bool(row.changeable) if pd.notna(row.changeable) else None,
            pd.to_datetime(row.created, unit="s", utc=True)
            if pd.notna(row.created)
            else None,
            pd.to_datetime(row.updated, unit="s", utc=True)
            if pd.notna(row.updated)
            else None,
            int(row.averageSignal)
            if pd.notna(row.averageSignal)
            else None,
        )
        for row in df.itertuples(index=False)
    ]

    sql = """
        INSERT INTO cells (
            radio,
            mcc,
            mnc,
            area,
            cell_id,
            unit,
            longitude,
            latitude,
            range_m,
            samples,
            changeable,
            created_at,
            updated_at,
            average_signal
        )
        VALUES %s
        ON CONFLICT (radio, mcc, mnc, area, cell_id)
        DO NOTHING;
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            execute_values(cursor, sql, records, page_size=1000)

        conn.commit()

        print(f"Inserted records: {len(records):,}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
