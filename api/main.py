import os

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

load_dotenv()

app = FastAPI(
    title="Telecom Network Operations API",
    version="1.1.0",
    description="API for telecom network KPI, alarm, and geographic monitoring",
)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5433"),
        dbname=os.getenv("POSTGRES_DB", "telecom_network"),
        user=os.getenv("POSTGRES_USER", "telecom"),
        password=os.getenv("POSTGRES_PASSWORD", "telecom"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/kpis/latest")
def latest_kpis(
    limit: int = Query(default=20, ge=1, le=100)
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    k.timestamp,
                    k.cell_id,
                    k.radio,
                    k.latency_ms,
                    k.packet_loss_pct,
                    k.throughput_mbps,
                    k.active_users,
                    c.wilaya_code,
                    c.wilaya_name,
                    c.wilaya_name_fr,
                    c.geo_match_status
                FROM network_kpis k
                LEFT JOIN cells c
                    ON k.cell_db_id = c.id
                ORDER BY k.timestamp DESC
                LIMIT %s;
                """,
                (limit,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "timestamp": row[0],
                    "cell_id": row[1],
                    "radio": row[2],
                    "latency_ms": row[3],
                    "packet_loss_pct": row[4],
                    "throughput_mbps": row[5],
                    "active_users": row[6],
                    "wilaya_code": row[7],
                    "wilaya_name": row[8],
                    "wilaya_name_fr": row[9],
                    "geo_match_status": row[10],
                }
                for row in rows
            ]

    finally:
        connection.close()


@app.get("/kpis/cell/{cell_id}")
def cell_kpis(
    cell_id: int,
    limit: int = Query(default=20, ge=1, le=100),
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    k.timestamp,
                    k.cell_id,
                    k.radio,
                    k.latency_ms,
                    k.packet_loss_pct,
                    k.throughput_mbps,
                    k.active_users,
                    c.wilaya_code,
                    c.wilaya_name,
                    c.wilaya_name_fr,
                    c.geo_match_status
                FROM network_kpis k
                LEFT JOIN cells c
                    ON k.cell_db_id = c.id
                WHERE k.cell_id = %s
                ORDER BY k.timestamp DESC
                LIMIT %s;
                """,
                (cell_id, limit),
            )

            rows = cursor.fetchall()

            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail=f"No KPI data found for cell {cell_id}",
                )

            return [
                {
                    "timestamp": row[0],
                    "cell_id": row[1],
                    "radio": row[2],
                    "latency_ms": row[3],
                    "packet_loss_pct": row[4],
                    "throughput_mbps": row[5],
                    "active_users": row[6],
                    "wilaya_code": row[7],
                    "wilaya_name": row[8],
                    "wilaya_name_fr": row[9],
                    "geo_match_status": row[10],
                }
                for row in rows
            ]

    finally:
        connection.close()


@app.get("/kpis/summary")
def kpi_summary():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_measurements,
                    ROUND(AVG(latency_ms)::numeric, 2)
                        AS avg_latency_ms,
                    ROUND(AVG(packet_loss_pct)::numeric, 2)
                        AS avg_packet_loss_pct,
                    ROUND(AVG(throughput_mbps)::numeric, 2)
                        AS avg_throughput_mbps,
                    ROUND(AVG(active_users)::numeric, 2)
                        AS avg_active_users
                FROM network_kpis;
                """
            )

            row = cursor.fetchone()

            return {
                "total_measurements": row[0],
                "avg_latency_ms": (
                    float(row[1])
                    if row[1] is not None
                    else None
                ),
                "avg_packet_loss_pct": (
                    float(row[2])
                    if row[2] is not None
                    else None
                ),
                "avg_throughput_mbps": (
                    float(row[3])
                    if row[3] is not None
                    else None
                ),
                "avg_active_users": (
                    float(row[4])
                    if row[4] is not None
                    else None
                ),
            }

    finally:
        connection.close()


@app.get("/alarms/latest")
def latest_alarms(
    limit: int = Query(default=20, ge=1, le=100)
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.timestamp,
                    a.cell_id,
                    a.radio,
                    a.alarm_type,
                    a.severity,
                    a.metric,
                    a.metric_value,
                    a.threshold_value,
                    a.message,
                    a.status,
                    c.wilaya_code,
                    c.wilaya_name,
                    c.wilaya_name_fr,
                    c.geo_match_status
                FROM network_alarms a
                LEFT JOIN cells c
                    ON a.cell_db_id = c.id
                ORDER BY a.timestamp DESC
                LIMIT %s;
                """,
                (limit,),
            )

            rows = cursor.fetchall()

            return [
                {
                    "timestamp": row[0],
                    "cell_id": row[1],
                    "radio": row[2],
                    "alarm_type": row[3],
                    "severity": row[4],
                    "metric": row[5],
                    "metric_value": row[6],
                    "threshold_value": row[7],
                    "message": row[8],
                    "status": row[9],
                    "wilaya_code": row[10],
                    "wilaya_name": row[11],
                    "wilaya_name_fr": row[12],
                    "geo_match_status": row[13],
                }
                for row in rows
            ]

    finally:
        connection.close()


@app.get("/alarms/cell/{cell_id}")
def cell_alarms(
    cell_id: int,
    limit: int = Query(default=20, ge=1, le=100),
):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.timestamp,
                    a.cell_id,
                    a.radio,
                    a.alarm_type,
                    a.severity,
                    a.metric,
                    a.metric_value,
                    a.threshold_value,
                    a.message,
                    a.status,
                    c.wilaya_code,
                    c.wilaya_name,
                    c.wilaya_name_fr,
                    c.geo_match_status
                FROM network_alarms a
                LEFT JOIN cells c
                    ON a.cell_db_id = c.id
                WHERE a.cell_id = %s
                ORDER BY a.timestamp DESC
                LIMIT %s;
                """,
                (cell_id, limit),
            )

            rows = cursor.fetchall()

            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail=f"No alarms found for cell {cell_id}",
                )

            return [
                {
                    "timestamp": row[0],
                    "cell_id": row[1],
                    "radio": row[2],
                    "alarm_type": row[3],
                    "severity": row[4],
                    "metric": row[5],
                    "metric_value": row[6],
                    "threshold_value": row[7],
                    "message": row[8],
                    "status": row[9],
                    "wilaya_code": row[10],
                    "wilaya_name": row[11],
                    "wilaya_name_fr": row[12],
                    "geo_match_status": row[13],
                }
                for row in rows
            ]

    finally:
        connection.close()


@app.get("/alarms/summary")
def alarm_summary():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_alarms,
                    COUNT(*) FILTER (
                        WHERE severity = 'CRITICAL'
                    ) AS critical_alarms,
                    COUNT(*) FILTER (
                        WHERE severity = 'MAJOR'
                    ) AS major_alarms,
                    COUNT(*) FILTER (
                        WHERE severity = 'MINOR'
                    ) AS minor_alarms,
                    COUNT(*) FILTER (
                        WHERE status = 'OPEN'
                    ) AS open_alarms,
                    COUNT(DISTINCT cell_id) AS affected_cells
                FROM network_alarms;
                """
            )

            row = cursor.fetchone()

            return {
                "total_alarms": row[0],
                "critical_alarms": row[1],
                "major_alarms": row[2],
                "minor_alarms": row[3],
                "open_alarms": row[4],
                "affected_cells": row[5],
            }

    finally:
        connection.close()


@app.get("/geography/wilayas")
def wilaya_summary():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    wilaya_code,
                    wilaya_name,
                    wilaya_name_fr,
                    COUNT(*) AS cell_count,
                    COUNT(*) FILTER (
                        WHERE geo_match_status = 'MATCHED'
                    ) AS matched_cells,
                    COUNT(*) FILTER (
                        WHERE geo_match_status = 'BOUNDARY_REVIEW'
                    ) AS boundary_review_cells
                FROM cells
                GROUP BY
                    wilaya_code,
                    wilaya_name,
                    wilaya_name_fr
                ORDER BY cell_count DESC;
                """
            )

            rows = cursor.fetchall()

            return [
                {
                    "wilaya_code": row[0],
                    "wilaya_name": row[1],
                    "wilaya_name_fr": row[2],
                    "cell_count": row[3],
                    "matched_cells": row[4],
                    "boundary_review_cells": row[5],
                }
                for row in rows
            ]

    finally:
        connection.close()


@app.get("/geography/summary")
def geography_summary():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_cells,
                    COUNT(*) FILTER (
                        WHERE geo_match_status = 'MATCHED'
                    ) AS matched_cells,
                    COUNT(*) FILTER (
                        WHERE geo_match_status = 'BOUNDARY_REVIEW'
                    ) AS boundary_review_cells,
                    COUNT(DISTINCT wilaya_code) AS wilayas_with_cells
                FROM cells;
                """
            )

            row = cursor.fetchone()

            return {
                "total_cells": row[0],
                "matched_cells": row[1],
                "boundary_review_cells": row[2],
                "wilayas_with_cells": row[3],
            }

    finally:
        connection.close()