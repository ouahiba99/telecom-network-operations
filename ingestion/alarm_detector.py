import json
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer


KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
KPI_TOPIC = "network.kpis"
ALARM_TOPIC = "network.alarms"

# Operational thresholds
THRESHOLDS = {
    "availability": 98.0,
    "latency_ms": 150.0,
    "packet_loss_pct": 3.0,
    "prb_utilization_pct": 90.0,
    "rrc_success_rate": 93.0,
    "handover_success_rate": 92.0,
    "call_drop_rate": 3.0,
}


def create_consumer():
    return KafkaConsumer(
        KPI_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="telecom-alarm-detector",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        key_serializer=lambda key: str(key).encode("utf-8"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def build_alarm(
    kpi,
    alarm_type,
    severity,
    metric,
    metric_value,
    threshold_value,
    message,
):
    return {
        "timestamp": kpi.get(
            "timestamp",
            datetime.now(timezone.utc).isoformat(),
        ),
        "cell_db_id": kpi["cell_db_id"],
        "radio": kpi["radio"],
        "mcc": kpi["mcc"],
        "mnc": kpi.get("mnc"),
        "area": kpi.get("area"),
        "cell_id": kpi["cell_id"],
        "alarm_type": alarm_type,
        "severity": severity,
        "metric": metric,
        "metric_value": metric_value,
        "threshold_value": threshold_value,
        "message": message,
        "status": "OPEN",
    }


def detect_alarms(kpi):
    alarms = []

    availability = kpi["availability"]
    latency = kpi["latency_ms"]
    packet_loss = kpi["packet_loss_pct"]
    prb = kpi["prb_utilization_pct"]
    rrc = kpi["rrc_success_rate"]
    handover = kpi["handover_success_rate"]
    call_drop = kpi["call_drop_rate"]

    # Availability
    if availability < 90:
        alarms.append(
            build_alarm(
                kpi,
                "CELL_OUTAGE",
                "CRITICAL",
                "availability",
                availability,
                90.0,
                f"Cell availability critically low: {availability:.2f}%",
            )
        )
    elif availability < THRESHOLDS["availability"]:
        severity = "MAJOR" if availability >= 95 else "CRITICAL"

        alarms.append(
            build_alarm(
                kpi,
                "LOW_AVAILABILITY",
                severity,
                "availability",
                availability,
                THRESHOLDS["availability"],
                f"Low cell availability: {availability:.2f}%",
            )
        )

    # Latency
    if latency > THRESHOLDS["latency_ms"]:
        severity = "MAJOR" if latency <= 300 else "CRITICAL"

        alarms.append(
            build_alarm(
                kpi,
                "HIGH_LATENCY",
                severity,
                "latency_ms",
                latency,
                THRESHOLDS["latency_ms"],
                f"High network latency: {latency:.2f} ms",
            )
        )

    # Packet loss
    if packet_loss > 10:
        alarms.append(
            build_alarm(
                kpi,
                "HIGH_PACKET_LOSS",
                "CRITICAL",
                "packet_loss_pct",
                packet_loss,
                10.0,
                f"Critical packet loss detected: {packet_loss:.2f}%",
            )
        )
    elif packet_loss > THRESHOLDS["packet_loss_pct"]:
        alarms.append(
            build_alarm(
                kpi,
                "HIGH_PACKET_LOSS",
                "MAJOR",
                "packet_loss_pct",
                packet_loss,
                THRESHOLDS["packet_loss_pct"],
                f"High packet loss: {packet_loss:.2f}%",
            )
        )

    # PRB utilization
    if prb > THRESHOLDS["prb_utilization_pct"]:
        severity = "MAJOR" if prb <= 97 else "CRITICAL"

        alarms.append(
            build_alarm(
                kpi,
                "HIGH_PRB_UTILIZATION",
                severity,
                "prb_utilization_pct",
                prb,
                THRESHOLDS["prb_utilization_pct"],
                f"High PRB utilization: {prb:.2f}%",
            )
        )

    # RRC success
    if rrc < THRESHOLDS["rrc_success_rate"]:
        severity = "MAJOR" if rrc >= 85 else "CRITICAL"

        alarms.append(
            build_alarm(
                kpi,
                "LOW_RRC_SUCCESS",
                severity,
                "rrc_success_rate",
                rrc,
                THRESHOLDS["rrc_success_rate"],
                f"Low RRC success rate: {rrc:.2f}%",
            )
        )

    # Handover success
    if handover < THRESHOLDS["handover_success_rate"]:
        severity = "MAJOR" if handover >= 80 else "CRITICAL"

        alarms.append(
            build_alarm(
                kpi,
                "LOW_HANDOVER_SUCCESS",
                severity,
                "handover_success_rate",
                handover,
                THRESHOLDS["handover_success_rate"],
                f"Low handover success rate: {handover:.2f}%",
            )
        )

    # Call drop
    if call_drop > 10:
        alarms.append(
            build_alarm(
                kpi,
                "HIGH_CALL_DROP",
                "CRITICAL",
                "call_drop_rate",
                call_drop,
                10.0,
                f"Critical call drop rate: {call_drop:.2f}%",
            )
        )
    elif call_drop > THRESHOLDS["call_drop_rate"]:
        alarms.append(
            build_alarm(
                kpi,
                "HIGH_CALL_DROP",
                "MAJOR",
                "call_drop_rate",
                call_drop,
                THRESHOLDS["call_drop_rate"],
                f"High call drop rate: {call_drop:.2f}%",
            )
        )

    return alarms


def main():
    consumer = create_consumer()
    producer = create_producer()

    print("Alarm detector started.")
    print(f"Listening to Kafka topic: {KPI_TOPIC}")
    print(f"Publishing alarms to: {ALARM_TOPIC}")

    try:
        for message in consumer:
            kpi = message.value
            alarms = detect_alarms(kpi)

            for alarm in alarms:
                producer.send(
                    ALARM_TOPIC,
                    key=str(alarm["cell_id"]),
                    value=alarm,
                )

                print(
                    f"[{alarm['severity']:<8}] "
                    f"cell={alarm['cell_id']} | "
                    f"type={alarm['alarm_type']} | "
                    f"metric={alarm['metric']} | "
                    f"value={alarm['metric_value']:.2f}"
                )

            producer.flush()

    except KeyboardInterrupt:
        print("\nStopping alarm detector...")

    finally:
        consumer.close()
        producer.close()


if __name__ == "__main__":
    main()
