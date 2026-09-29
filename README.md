# 📡 Telecom Network Operations & NOC Monitoring Platform

> Real-time telecom monitoring platform for KPI streaming, alarm detection, API access, and NOC observability.

## Overview

This project simulates and monitors cellular network performance through a complete event-driven pipeline:

```text
Cellular Data
     ↓
KPI Simulation
     ↓
Apache Kafka
     ↓
PostgreSQL
     ↓
Alarm Detection
     ↓
FastAPI
     ↓
Grafana NOC Dashboards
```

The platform generates correlated network conditions, stores KPI measurements, detects degradation, and exposes operational insights through APIs and dashboards.

## Key Features

* Real-time cellular KPI simulation
* Correlated network states:

  * `NORMAL`
  * `CONGESTED`
  * `DEGRADED`
  * `OUTAGE`
* Apache Kafka event streaming
* PostgreSQL KPI and alarm storage
* Rule-based alarm detection
* FastAPI monitoring API
* Grafana NOC dashboards
* Docker Compose infrastructure
* Cell-level health and performance monitoring

## Architecture

```text
OpenCelliD-style Cell Data
          ↓
      PostgreSQL
          ↓
    KPI Simulator
          ↓
      Kafka
   ┌──────┴──────┐
   ↓             ↓
KPI Consumer   Alarm Detector
   ↓             ↓
network_kpis  network.alarms
                 ↓
          Alarm Consumer
                 ↓
          network_alarms
                 ↓
        FastAPI + Grafana
```

## Monitored KPIs

* Availability
* Latency
* Packet loss
* Throughput
* PRB utilization
* RRC success rate
* Handover success rate
* Call drop rate
* Active users

## Alarm Detection

KPI events are consumed from:

```text
network.kpis
```

and evaluated against configurable thresholds:

| KPI              |  Threshold |
| ---------------- | ---------: |
| Availability     |    `< 98%` |
| Latency          | `> 150 ms` |
| Packet Loss      |     `> 3%` |
| PRB Utilization  |    `> 90%` |
| RRC Success      |    `< 93%` |
| Handover Success |    `< 92%` |
| Call Drop Rate   |     `> 3%` |

Detected alarms are published to:

```text
network.alarms
```

Supported alarm types include:

```text
CELL_OUTAGE
LOW_AVAILABILITY
HIGH_LATENCY
HIGH_PACKET_LOSS
HIGH_PRB_UTILIZATION
LOW_RRC_SUCCESS
LOW_HANDOVER_SUCCESS
HIGH_CALL_DROP
```

Severity levels:

```text
CRITICAL
MAJOR
MINOR
```

## PostgreSQL Tables

### `cells`

Stores cellular site information, including:

```text
radio, mcc, mnc, area, cell_id,
longitude, latitude, range,
samples, average_signal
```

### `network_kpis`

Stores streamed KPI measurements:

```text
timestamp, cell_id, radio, area,
availability, latency_ms,
packet_loss_pct, throughput_mbps,
prb_utilization_pct,
rrc_success_rate,
handover_success_rate,
call_drop_rate,
active_users
```

### `network_alarms`

Stores detected alarms:

```text
timestamp, cell_id, alarm_type,
severity, metric, metric_value,
threshold_value, message, status
```

## FastAPI Endpoints

Start the API:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Available endpoints:

```http
GET /health
GET /kpis/latest?limit=20
GET /kpis/cell/{cell_id}?limit=20
GET /kpis/summary
GET /alarms/latest?limit=20
GET /alarms/cell/{cell_id}?limit=20
GET /alarms/summary
```

API documentation:

```text
http://localhost:8000/docs
```

## Grafana Dashboards

The project includes dashboards for:

* Telecom NOC overview
* RAN performance
* Cell health
* Alarm signals
* Traffic and capacity

Grafana:

```text
http://localhost:3000
```

## Project Structure

```text
telecom-network-operations/
├── api/
│   └── main.py
├── database/
│   └── schema.sql
├── grafana/
│   ├── dashboards/
│   ├── provisioning/
│   └── build_dashboards.py
├── ingestion/
│   ├── producer.py
│   ├── consumer.py
│   ├── alarm_detector.py
│   └── alarm_consumer.py
├── simulator/
│   └── kpi_generator.py
├── data/
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Installation

```bash
git clone https://github.com/ouahiba99/telecom-network-operations.git
cd telecom-network-operations

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
docker compose up -d
```

Check running services:

```bash
docker compose ps
```

## Run the Platform

Run each component in a separate terminal:

```bash
python -m ingestion.producer
```

```bash
python -m ingestion.consumer
```

```bash
python -m ingestion.alarm_detector
```

```bash
python -m ingestion.alarm_consumer
```

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Infrastructure services:

```text
telecom-postgres
telecom-kafka
telecom-grafana
```

Stop the infrastructure:

```bash
docker compose down
```

## Technology Stack

* Python
* Apache Kafka
* PostgreSQL
* FastAPI
* Grafana
* Docker and Docker Compose
* OpenCelliD-style cellular data
* psycopg2

## Engineering Concepts

* Event-driven architecture
* Real-time streaming pipelines
* Kafka producers and consumers
* Telecom KPI monitoring
* Rule-based anomaly detection
* Alarm management
* PostgreSQL data modeling and indexing
* REST API development
* NOC observability
* Containerized infrastructure

## Project Status

The current implementation includes:

* ✅ Cellular data ingestion
* ✅ Correlated KPI simulation
* ✅ Kafka KPI streaming
* ✅ KPI persistence
* ✅ Alarm detection
* ✅ Kafka alarm streaming
* ✅ Alarm persistence
* ✅ FastAPI monitoring endpoints
* ✅ Grafana NOC dashboards
* ✅ Dockerized infrastructure

## Author

**Ouahiba Ahmid**

Telecom & ICT Engineer · DataOps & Cloud Consultant