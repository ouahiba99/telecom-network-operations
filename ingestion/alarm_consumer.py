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
    "KAFKA_ALARM_TOPIC",
    "network.alarms",
)

KAFKA_GROUP_ID = os.getenv(
    "KAFKA_ALARM_GROUP_ID",
    "telecom-alarm-consumer",
)


DB_CONFIG = {
    "host": os.getenv(
        "POSTGRES_HOST",
        "127.0.0.1",
    ),
    "port": os.getenv(
        "POSTGRES_PORT",
        "5433",
    ),
    "dbname": os.getenv(
        "POSTGRES_DB",
        "telecom_network",
    ),
    "user": os.getenv(
        "POSTGRES_USER",
        "telecom",
    ),
    "password": os.getenv(
        "POSTGRES_PASSWORD",
        "telecom",
    ),
}


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(
            value.decode("utf-8")
        ),
    )


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def insert_alarm(cursor, alarm):
    query = """
        INSERT INTO network_alarms (
            timestamp,
            cell_db_id,
            radio,
            mcc,
            mnc,
            area,
            cell_id,
            alarm_type,
            severity,
            metric,
            metric_value,
            threshold_value,
            message,
            status
        )
        VALUES (
            %(timestamp)s,
            %(cell_db_id)s,
            %(radio)s,
            %(mcc)s,
            %(mnc)s,
            %(area)s,
            %(cell_id)s,
            %(alarm_type)s,
            %(severity)s,
            %(metric)s,
            %(metric_value)s,
            %(threshold_value)s,
            %(message)s,
            %(status)s
        )
    """

    cursor.execute(query, alarm)


def main():
    print(f"Kafka broker: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Kafka topic: {KAFKA_TOPIC}")
    print(f"Kafka group: {KAFKA_GROUP_ID}")
    print(
        f"PostgreSQL: "
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}"
    )

    consumer = create_consumer()
    connection = get_connection()

    try:
        cursor = connection.cursor()

        for message in consumer:
            alarm = message.value

            try:
                insert_alarm(cursor, alarm)
                connection.commit()

                consumer.commit()

                print(
                    f"[{alarm.get('severity', 'UNKNOWN'):8}] "
                    f"cell={alarm.get('cell_id')} | "
                    f"type={alarm.get('alarm_type')} | "
                    f"metric={alarm.get('metric')} | "
                    f"value={alarm.get('metric_value')}"
                )

            except Exception as exc:
                connection.rollback()
                print(
                    f"Failed to insert alarm: {exc}"
                )

    except KeyboardInterrupt:
        print("\nStopping alarm consumer...")

    finally:
        try:
            cursor.close()
        except Exception:
            pass

        try:
            connection.close()
        except Exception:
            pass

        consumer.close()


if __name__ == "__main__":
    main()
