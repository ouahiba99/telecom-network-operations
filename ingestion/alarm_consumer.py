import json

import psycopg2
from kafka import KafkaConsumer


KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
KAFKA_TOPIC = "network.alarms"
KAFKA_GROUP_ID = "telecom-alarm-consumer"

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "dbname": "telecom_network",
    "user": "telecom",
    "password": "telecom",
}


def create_consumer():
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
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
    consumer = create_consumer()
    connection = get_connection()
    cursor = connection.cursor()

    print("Alarm consumer started.")
    print(f"Listening to Kafka topic: {KAFKA_TOPIC}")
    print("Writing alarms to PostgreSQL: network_alarms")

    try:
        for message in consumer:
            alarm = message.value

            required_fields = [
                "timestamp",
                "cell_db_id",
                "radio",
                "mcc",
                "cell_id",
                "alarm_type",
                "severity",
                "metric",
                "metric_value",
                "threshold_value",
                "message",
                "status",
            ]

            missing = [
                field
                for field in required_fields
                if field not in alarm
            ]

            if missing:
                print(
                    f"Skipping invalid alarm | "
                    f"missing fields: {missing}"
                )
                continue

            try:
                insert_alarm(cursor, alarm)
                connection.commit()

                consumer.commit()

                print(
                    f"Stored alarm | "
                    f"cell={alarm['cell_id']} | "
                    f"type={alarm['alarm_type']} | "
                    f"severity={alarm['severity']} | "
                    f"metric={alarm['metric']} | "
                    f"value={alarm['metric_value']:.2f}"
                )

            except Exception as exc:
                connection.rollback()

                print(
                    f"Database error | "
                    f"cell={alarm.get('cell_id')} | "
                    f"type={alarm.get('alarm_type')} | "
                    f"error={exc}"
                )

    except KeyboardInterrupt:
        print("\nStopping alarm consumer...")

    finally:
        cursor.close()
        connection.close()
        consumer.close()


if __name__ == "__main__":
    main()
