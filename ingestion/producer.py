import json
import os
import random
import time

from dotenv import load_dotenv
from kafka import KafkaProducer

from simulator.kpi_generator import generate_kpi, load_cells


load_dotenv()


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "127.0.0.1:9092",
)

KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "network.kpis",
)


def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda key: str(key).encode("utf-8"),
    )


def main():
    cells = load_cells(limit=500)

    if not cells:
        raise RuntimeError("No cells found in PostgreSQL.")

    print(f"Loaded {len(cells)} real cells.")
    print(f"Kafka broker: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Kafka topic: {KAFKA_TOPIC}")

    producer = create_producer()

    try:
        while True:
            random.shuffle(cells)

            for cell in cells:
                kpi = generate_kpi(cell)

                future = producer.send(
                    KAFKA_TOPIC,
                    key=kpi["cell_id"],
                    value=kpi,
                )

                metadata = future.get(timeout=10)

                print(
                    f"Sent KPI | "
                    f"cell={kpi['cell_id']} | "
                    f"radio={kpi['radio']} | "
                    f"condition={kpi.get('condition', 'UNKNOWN')} | "
                    f"latency={kpi['latency_ms']} ms | "
                    f"partition={metadata.partition} | "
                    f"offset={metadata.offset}"
                )

                time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopping producer...")

    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
