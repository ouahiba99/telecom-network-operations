import os

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

load_dotenv()

app = FastAPI(
    title="Telecom Network Operations API",
    version="1.2.0",
    description="API for telecom network KPI, alarm, and geographic monitoring",
)


class AlarmActionRequest(BaseModel):
    username: str = Field(..., description="Operator username taking action on the alarm")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("username cannot be empty")
        return v.strip()


def format_alarm_row(row):
    return {
        "id": row[0],
        "timestamp": row[1],
        "cell_id": row[2],
        "radio": row[3],
        "alarm_type": row[4],
        "severity": row[5],
        "metric": row[6],
        "metric_value": row[7],
        "threshold_value": row[8],
        "message": row[9],
        "status": row[10],
        "created_at": row[11],
        "acknowledged_at": row[12],
        "acknowledged_by": row[13],
        "resolved_at": row[14],
        "resolved_by": row[15],
        "wilaya_code": row[16] if len(row) > 16 else None,
        "wilaya_name": row[17] if len(row) > 17 else None,
        "wilaya_name_fr": row[18] if len(row) > 18 else None,
        "geo_match_status": row[19] if len(row) > 19 else None,
    }


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
                    a.id,
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
                    a.created_at,
                    a.acknowledged_at,
                    a.acknowledged_by,
                    a.resolved_at,
                    a.resolved_by,
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
            return [format_alarm_row(row) for row in rows]

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
                    a.id,
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
                    a.created_at,
                    a.acknowledged_at,
                    a.acknowledged_by,
                    a.resolved_at,
                    a.resolved_by,
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

            return [format_alarm_row(row) for row in rows]

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
                    COUNT(*) FILTER (
                        WHERE status = 'ACKNOWLEDGED'
                    ) AS acknowledged_alarms,
                    COUNT(*) FILTER (
                        WHERE status = 'RESOLVED'
                    ) AS resolved_alarms,
                    COUNT(DISTINCT cell_id) AS affected_cells,
                    ROUND(
                        AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at)))
                        FILTER (WHERE acknowledged_at IS NOT NULL AND created_at IS NOT NULL)::numeric,
                        2
                    ) AS avg_mtta_seconds,
                    ROUND(
                        (AVG(EXTRACT(EPOCH FROM (acknowledged_at - created_at)))
                        FILTER (WHERE acknowledged_at IS NOT NULL AND created_at IS NOT NULL) / 60.0)::numeric,
                        2
                    ) AS avg_mtta_minutes,
                    ROUND(
                        AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)))
                        FILTER (WHERE resolved_at IS NOT NULL AND created_at IS NOT NULL)::numeric,
                        2
                    ) AS avg_mttr_seconds,
                    ROUND(
                        (AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)))
                        FILTER (WHERE resolved_at IS NOT NULL AND created_at IS NOT NULL) / 60.0)::numeric,
                        2
                    ) AS avg_mttr_minutes
                FROM network_alarms;
                """
            )

            row = cursor.fetchone()

            total_alarms = row[0]
            critical_alarms = row[1]
            major_alarms = row[2]
            minor_alarms = row[3]
            open_alarms = row[4]
            acknowledged_alarms = row[5]
            resolved_alarms = row[6]
            affected_cells = row[7]

            avg_mtta_sec = float(row[8]) if row[8] is not None else None
            avg_mtta_min = float(row[9]) if row[9] is not None else None
            avg_mttr_sec = float(row[10]) if row[10] is not None else None
            avg_mttr_min = float(row[11]) if row[11] is not None else None

            return {
                "total_alarms": total_alarms,
                "critical_alarms": critical_alarms,
                "major_alarms": major_alarms,
                "minor_alarms": minor_alarms,
                "open_alarms": open_alarms,
                "acknowledged_alarms": acknowledged_alarms,
                "resolved_alarms": resolved_alarms,
                "affected_cells": affected_cells,
                "total": total_alarms,
                "open": open_alarms,
                "acknowledged": acknowledged_alarms,
                "resolved": resolved_alarms,
                "critical": critical_alarms,
                "major": major_alarms,
                "minor": minor_alarms,
                "average_mtta_seconds": avg_mtta_sec,
                "average_mtta_minutes": avg_mtta_min,
                "average_mttr_seconds": avg_mttr_sec,
                "average_mttr_minutes": avg_mttr_min,
            }

    finally:
        connection.close()


@app.get("/alarms/{alarm_id}")
def get_alarm(alarm_id: int):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    a.id,
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
                    a.created_at,
                    a.acknowledged_at,
                    a.acknowledged_by,
                    a.resolved_at,
                    a.resolved_by,
                    c.wilaya_code,
                    c.wilaya_name,
                    c.wilaya_name_fr,
                    c.geo_match_status
                FROM network_alarms a
                LEFT JOIN cells c
                    ON a.cell_db_id = c.id
                WHERE a.id = %s;
                """,
                (alarm_id,),
            )

            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Alarm {alarm_id} not found",
                )

            return format_alarm_row(row)

    finally:
        connection.close()


@app.patch("/alarms/{alarm_id}/acknowledge")
def acknowledge_alarm(alarm_id: int, payload: AlarmActionRequest):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status
                FROM network_alarms
                WHERE id = %s;
                """,
                (alarm_id,),
            )

            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Alarm {alarm_id} not found",
                )

            current_status = row[1]

            if current_status == "ACKNOWLEDGED":
                raise HTTPException(
                    status_code=409,
                    detail=f"Alarm {alarm_id} is already acknowledged",
                )

            if current_status == "RESOLVED":
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot acknowledge resolved alarm {alarm_id}",
                )

            if current_status != "OPEN":
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot acknowledge alarm with status '{current_status}'",
                )

            cursor.execute(
                """
                UPDATE network_alarms
                SET
                    status = 'ACKNOWLEDGED',
                    acknowledged_at = CURRENT_TIMESTAMP,
                    acknowledged_by = %s
                WHERE id = %s;
                """,
                (payload.username, alarm_id),
            )
            connection.commit()

            cursor.execute(
                """
                SELECT
                    a.id,
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
                    a.created_at,
                    a.acknowledged_at,
                    a.acknowledged_by,
                    a.resolved_at,
                    a.resolved_by,
                    c.wilaya_code,
                    c.wilaya_name,
                    c.wilaya_name_fr,
                    c.geo_match_status
                FROM network_alarms a
                LEFT JOIN cells c
                    ON a.cell_db_id = c.id
                WHERE a.id = %s;
                """,
                (alarm_id,),
            )
            updated_row = cursor.fetchone()
            return format_alarm_row(updated_row)

    finally:
        connection.close()


@app.patch("/alarms/{alarm_id}/resolve")
def resolve_alarm(alarm_id: int, payload: AlarmActionRequest):
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    status
                FROM network_alarms
                WHERE id = %s;
                """,
                (alarm_id,),
            )

            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Alarm {alarm_id} not found",
                )

            current_status = row[1]

            if current_status == "RESOLVED":
                raise HTTPException(
                    status_code=409,
                    detail=f"Alarm {alarm_id} is already resolved",
                )

            if current_status not in ("OPEN", "ACKNOWLEDGED"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot resolve alarm with status '{current_status}'",
                )

            cursor.execute(
                """
                UPDATE network_alarms
                SET
                    status = 'RESOLVED',
                    resolved_at = CURRENT_TIMESTAMP,
                    resolved_by = %s
                WHERE id = %s;
                """,
                (payload.username, alarm_id),
            )
            connection.commit()

            cursor.execute(
                """
                SELECT
                    a.id,
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
                    a.created_at,
                    a.acknowledged_at,
                    a.acknowledged_by,
                    a.resolved_at,
                    a.resolved_by,
                    c.wilaya_code,
                    c.wilaya_name,
                    c.wilaya_name_fr,
                    c.geo_match_status
                FROM network_alarms a
                LEFT JOIN cells c
                    ON a.cell_db_id = c.id
                WHERE a.id = %s;
                """,
                (alarm_id,),
            )
            updated_row = cursor.fetchone()
            return format_alarm_row(updated_row)

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