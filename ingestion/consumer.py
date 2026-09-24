import json
import os

import psycopg2
from dotenv import load_dotenv
from kafka import KafkaConsumer

load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "127.0.0.1:9092",
)

KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "network.kpis",
)

KAFKA_GROUP_ID = os.getenv(
    "KAFKA_GROUP_ID",
    "telecom-kpi-consumer",
)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "telecom_network"),
        user=os.getenv("POSTGRES_USER", "telecom"),
        password=os.getenv("POSTGRES_PASSWORD", "telecom"),
    )


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def insert_kpi(cursor, kpi):
    cursor.execute(
        """
        INSERT INTO network_kpis (
            timestamp,
            cell_db_id,
            radio,
            mcc,
            mnc,
            area,
            cell_id,
            longitude,
            latitude,
            availability,
            latency_ms,
            packet_loss_pct,
            throughput_mbps,
            prb_utilization_pct,
            rrc_success_rate,
            handover_success_rate,
            call_drop_rate,
            active_users
        )
        VALUES (
            %(timestamp)s,
            %(cell_db_id)s,
            %(radio)s,
            %(mcc)s,
            %(mnc)s,
            %(area)s,
            %(cell_id)s,
            %(longitude)s,
            %(latitude)s,
            %(availability)s,
            %(latency_ms)s,
            %(packet_loss_pct)s,
            %(throughput_mbps)s,
            %(prb_utilization_pct)s,
            %(rrc_success_rate)s,
            %(handover_success_rate)s,
            %(call_drop_rate)s,
            %(active_users)s
        );
        """,
        kpi,
    )


def main():
    consumer = create_consumer()
    connection = get_db_connection()

    print(f"Listening to Kafka topic: {KAFKA_TOPIC}")
    print(f"Consumer group: {KAFKA_GROUP_ID}")

    try:
        with connection.cursor() as cursor:
            for message in consumer:
                kpi = message.value

                try:
                    required_fields = [
                        "timestamp",
                        "cell_db_id",
                        "radio",
                        "mcc",
                        "cell_id",
                        "availability",
                        "latency_ms",
                        "packet_loss_pct",
                        "throughput_mbps",
                        "prb_utilization_pct",
                        "rrc_success_rate",
                        "handover_success_rate",
                        "call_drop_rate",
                        "active_users",
                    ]

                    missing_fields = [
                        field for field in required_fields
                        if field not in kpi
                    ]

                    if missing_fields:
                        raise ValueError(
                            f"Missing fields: {missing_fields}"
                        )

                    insert_kpi(cursor, kpi)
                    connection.commit()
                    consumer.commit()

                    print(
                        f"Stored KPI | "
                        f"cell={kpi['cell_id']} | "
                        f"latency={kpi['latency_ms']} ms | "
                        f"partition={message.partition} | "
                        f"offset={message.offset}"
                    )

                except Exception as exc:
                    connection.rollback()

                    print(
                        f"Failed to process message "
                        f"partition={message.partition} "
                        f"offset={message.offset}: {exc}"
                    )

    except KeyboardInterrupt:
        print("\nStopping consumer...")

    finally:
        consumer.close()
        connection.close()


if __name__ == "__main__":
    main()
