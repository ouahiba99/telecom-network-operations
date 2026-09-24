import json
import os
import random
import time
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv

load_dotenv()


# =========================================================
# PostgreSQL
# =========================================================

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

            return cursor.fetchall()

    finally:
        conn.close()


# =========================================================
# Persistent network conditions
# =========================================================

CELL_STATES = {}

STATE_DURATIONS = {
    "NORMAL": (20, 60),
    "CONGESTED": (20, 50),
    "DEGRADED": (15, 40),
    "OUTAGE": (10, 25),
}


def choose_initial_state(cell_id=None):
    """
    Assign an initial condition to each simulated cell.

    A few real cell IDs are reserved for deterministic demo
    scenarios so the monitoring system always has visible
    incidents.

    Remaining cells use a realistic probabilistic distribution.
    """

    demo_states = {
        18322: "NORMAL",
        6142: "CONGESTED",
        10086: "DEGRADED",
        35832: "OUTAGE",
    }

    if cell_id in demo_states:
        return demo_states[cell_id]

    roll = random.random()

    if roll < 0.75:
        return "NORMAL"

    if roll < 0.90:
        return "CONGESTED"

    if roll < 0.98:
        return "DEGRADED"

    return "OUTAGE"

def get_cell_state(cell_db_id, cell_id):
    """
    Keep a cell in the same network condition for multiple
    KPI cycles so that Grafana shows realistic trends.
    """

    state = CELL_STATES.get(cell_db_id)

    if state is None:
        condition = choose_initial_state(cell_id)

        min_duration, max_duration = STATE_DURATIONS[condition]

        CELL_STATES[cell_db_id] = {
            "condition": condition,
            "remaining": random.randint(
                min_duration,
                max_duration,
            ),
        }

        return condition

    state["remaining"] -= 1

    if state["remaining"] <= 0:
        previous = state["condition"]

        if previous == "NORMAL":
            condition = random.choices(
                ["NORMAL", "CONGESTED", "DEGRADED"],
                weights=[70, 22, 8],
                k=1,
            )[0]

        elif previous == "CONGESTED":
            condition = random.choices(
                ["NORMAL", "CONGESTED", "DEGRADED"],
                weights=[55, 30, 15],
                k=1,
            )[0]

        elif previous == "DEGRADED":
            condition = random.choices(
                ["NORMAL", "CONGESTED", "DEGRADED", "OUTAGE"],
                weights=[50, 20, 25, 5],
                k=1,
            )[0]

        else:
            condition = random.choices(
                ["NORMAL", "DEGRADED", "OUTAGE"],
                weights=[65, 25, 10],
                k=1,
            )[0]

        min_duration, max_duration = STATE_DURATIONS[condition]

        state["condition"] = condition
        state["remaining"] = random.randint(
            min_duration,
            max_duration,
        )

    return state["condition"]


# =========================================================
# KPI profiles
# =========================================================

def generate_normal_kpis():
    """
    Healthy network behavior.
    """

    active_users = random.randint(100, 1200)
    prb = random.uniform(20, 65)

    return {
        "availability": random.uniform(99.5, 100.0),
        "latency_ms": random.uniform(20, 50),
        "packet_loss_pct": random.uniform(0.0, 0.5),
        "throughput_mbps": random.uniform(120, 300),
        "prb_utilization_pct": prb,
        "rrc_success_rate": random.uniform(98.0, 100.0),
        "handover_success_rate": random.uniform(97.0, 100.0),
        "call_drop_rate": random.uniform(0.0, 0.8),
        "active_users": active_users,
    }


def generate_congested_kpis():
    """
    High traffic / capacity pressure.

    Congestion causes:
      users ↑
      PRB ↑
      latency ↑
      packet loss ↑
      throughput ↓
      accessibility and retainability ↓
    """

    active_users = random.randint(1400, 3000)
    prb = random.uniform(80, 96)

    return {
        "availability": random.uniform(98.5, 99.7),
        "latency_ms": random.uniform(70, 130),
        "packet_loss_pct": random.uniform(1.0, 3.5),
        "throughput_mbps": random.uniform(45, 150),
        "prb_utilization_pct": prb,
        "rrc_success_rate": random.uniform(93.0, 98.0),
        "handover_success_rate": random.uniform(92.0, 98.0),
        "call_drop_rate": random.uniform(1.0, 3.0),
        "active_users": active_users,
    }


def generate_degraded_kpis():
    """
    Service degradation.

    Multiple network-quality indicators deteriorate together.
    """

    active_users = random.randint(500, 2200)
    prb = random.uniform(65, 92)

    return {
        "availability": random.uniform(94.0, 98.8),
        "latency_ms": random.uniform(100, 220),
        "packet_loss_pct": random.uniform(2.0, 7.0),
        "throughput_mbps": random.uniform(15, 100),
        "prb_utilization_pct": prb,
        "rrc_success_rate": random.uniform(85.0, 95.0),
        "handover_success_rate": random.uniform(82.0, 94.0),
        "call_drop_rate": random.uniform(3.0, 8.0),
        "active_users": active_users,
    }


def generate_outage_kpis():
    """
    Severe cell failure / service outage.
    """

    active_users = random.randint(0, 500)

    return {
        "availability": random.uniform(70.0, 94.0),
        "latency_ms": random.uniform(180, 500),
        "packet_loss_pct": random.uniform(5.0, 20.0),
        "throughput_mbps": random.uniform(0, 25),
        "prb_utilization_pct": random.uniform(5, 60),
        "rrc_success_rate": random.uniform(40.0, 82.0),
        "handover_success_rate": random.uniform(35.0, 80.0),
        "call_drop_rate": random.uniform(8.0, 25.0),
        "active_users": active_users,
    }


# =========================================================
# Main KPI generator
# =========================================================

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

    condition = get_cell_state(db_id, cell_id)

    generators = {
        "NORMAL": generate_normal_kpis,
        "CONGESTED": generate_congested_kpis,
        "DEGRADED": generate_degraded_kpis,
        "OUTAGE": generate_outage_kpis,
    }

    metrics = generators[condition]()

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

        # Used by the alarm engine.
        # It is intentionally not stored in network_kpis.
        "condition": condition,

        "availability": round(
            metrics["availability"],
            2,
        ),

        "latency_ms": round(
            metrics["latency_ms"],
            2,
        ),

        "packet_loss_pct": round(
            metrics["packet_loss_pct"],
            2,
        ),

        "throughput_mbps": round(
            metrics["throughput_mbps"],
            2,
        ),

        "prb_utilization_pct": round(
            metrics["prb_utilization_pct"],
            2,
        ),

        "rrc_success_rate": round(
            metrics["rrc_success_rate"],
            2,
        ),

        "handover_success_rate": round(
            metrics["handover_success_rate"],
            2,
        ),

        "call_drop_rate": round(
            metrics["call_drop_rate"],
            2,
        ),

        "active_users": metrics["active_users"],
    }


# =========================================================
# Local simulator test
# =========================================================

if __name__ == "__main__":
    cells = load_cells(limit=20)

    if not cells:
        raise RuntimeError("No cells found in PostgreSQL.")

    print(
        f"Loaded {len(cells)} real cells from PostgreSQL"
    )

    try:
        while True:
            cell = random.choice(cells)

            kpi = generate_kpi(cell)

            print(
                f"[{kpi['condition']:9}] "
                f"cell={kpi['cell_id']} | "
                f"availability={kpi['availability']:6.2f}% | "
                f"latency={kpi['latency_ms']:6.2f} ms | "
                f"loss={kpi['packet_loss_pct']:5.2f}% | "
                f"PRB={kpi['prb_utilization_pct']:5.2f}% | "
                f"throughput={kpi['throughput_mbps']:6.2f} Mbps | "
                f"RRC={kpi['rrc_success_rate']:5.2f}% | "
                f"HO={kpi['handover_success_rate']:5.2f}% | "
                f"drop={kpi['call_drop_rate']:5.2f}% | "
                f"users={kpi['active_users']}"
            )

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopping simulator...")
