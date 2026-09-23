import json
import random
import time
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "telecom_network"),
        user=os.getenv("POSTGRES_USER", "telecom"),
        password=os.getenv("POSTGRES_PASSWORD", "telecom"),
    )


def load_cells(limit=20):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    radio,
                    mcc,
                    mnc,
                    area,
                    cell_id,
                    longitude,
                    latitude
                FROM cells
                ORDER BY id
                LIMIT %s;
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return rows

    finally:
        conn.close()


def generate_kpi(cell):
    (
        db_id,
        radio,
        mcc,
        mnc,
        area,
        cell_id,
        longitude,
        latitude,
    ) = cell

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cell_db_id": db_id,
        "radio": radio,
        "mcc": mcc,
        "mnc": mnc,
        "area": area,
        "cell_id": cell_id,
        "longitude": longitude,
        "latitude": latitude,
        "availability": round(random.uniform(98.0, 100.0), 2),
        "latency_ms": round(random.uniform(20.0, 80.0), 2),
        "packet_loss_pct": round(random.uniform(0.0, 2.0), 2),
        "throughput_mbps": round(random.uniform(50.0, 300.0), 2),
        "prb_utilization_pct": round(random.uniform(20.0, 90.0), 2),
        "rrc_success_rate": round(random.uniform(95.0, 100.0), 2),
        "handover_success_rate": round(random.uniform(94.0, 100.0), 2),
        "call_drop_rate": round(random.uniform(0.0, 2.0), 2),
        "active_users": random.randint(100, 3000),
    }


if __name__ == "__main__":
    cells = load_cells(limit=20)

    print(f"Loaded {len(cells)} real cells from PostgreSQL")

    while True:
        cell = random.choice(cells)
        kpi = generate_kpi(cell)

        print(json.dumps(kpi, indent=2))

        time.sleep(2)
