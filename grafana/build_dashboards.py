import json
from pathlib import Path


OUT = Path("grafana/dashboards")
OUT.mkdir(parents=True, exist_ok=True)

FOLDER_UID = "telecom-noc-folder"


def datasource():
    return {"type": "postgres", "uid": "telecom-postgres"}


def stat_panel(
    panel_id,
    title,
    x,
    y,
    w,
    sql,
    unit="short",
    decimals=2,
):
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": 5},
        "datasource": datasource(),
        "targets": [
            {
                "refId": "A",
                "datasource": datasource(),
                "format": "table",
                "rawQuery": True,
                "rawSql": sql,
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": decimals,
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {
                "calcs": ["mean"],
                "fields": "",
                "values": False,
            },
            "orientation": "auto",
            "textMode": "auto",
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "center",
        },
    }


def timeseries_panel(
    panel_id,
    title,
    x,
    y,
    w,
    sql,
    unit="short",
    decimals=2,
):
    return {
        "id": panel_id,
        "type": "timeseries",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": 8},
        "datasource": datasource(),
        "targets": [
            {
                "refId": "A",
                "datasource": datasource(),
                "format": "time_series",
                "rawQuery": True,
                "rawSql": sql,
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "decimals": decimals,
            },
            "overrides": [],
        },
        "options": {
            "legend": {
                "displayMode": "table",
                "placement": "bottom",
                "calcs": ["mean", "max"],
            },
            "tooltip": {
                "mode": "multi",
                "sort": "desc",
            },
        },
    }


def table_panel(panel_id, title, x, y, w, sql):
    return {
        "id": panel_id,
        "type": "table",
        "title": title,
        "gridPos": {"x": x, "y": y, "w": w, "h": 9},
        "datasource": datasource(),
        "targets": [
            {
                "refId": "A",
                "datasource": datasource(),
                "format": "table",
                "rawQuery": True,
                "rawSql": sql,
            }
        ],
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "auto",
                    "cellOptions": {
                        "type": "auto",
                    },
                    "inspect": False,
                }
            },
            "overrides": [],
        },
        "options": {
            "cellHeight": "sm",
            "footer": {
                "show": False,
            },
            "showHeader": True,
            "sortBy": [],
        },
    }


def base_dashboard(uid, title, tags):
    return {
        "annotations": {
            "list": [
                {
                    "builtIn": 1,
                    "datasource": {
                        "type": "grafana",
                        "uid": "-- Grafana --",
                    },
                    "enable": True,
                    "hide": True,
                    "iconColor": "rgba(255, 96, 96, 1)",
                    "name": "Annotations & Alerts",
                    "type": "dashboard",
                }
            ]
        },
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "links": [],
        "panels": [],
        "refresh": "10s",
        "schemaVersion": 39,
        "style": "dark",
        "tags": tags,
        "templating": {"list": []},
        "time": {
            "from": "now-30m",
            "to": "now",
        },
        "timepicker": {
            "refresh_intervals": ["5s", "10s", "30s", "1m", "5m"],
            "time_options": [
                "5m",
                "15m",
                "30m",
                "1h",
                "6h",
                "12h",
                "24h",
            ],
        },
        "timezone": "browser",
        "title": title,
        "uid": uid,
        "version": 1,
        "weekStart": "",
        "folderUid": FOLDER_UID,
    }


def write_dashboard(filename, dashboard):
    path = OUT / filename
    with path.open("w") as f:
        json.dump(dashboard, f, indent=2)
    print(f"Created {path}")


# ============================================================
# 01 — NOC OVERVIEW
# ============================================================

d = base_dashboard(
    "telecom-noc",
    "01 — Telecom NOC Overview",
    ["telecom", "noc", "operations", "overview"],
)

d["panels"] = [
    stat_panel(
        1,
        "Network Availability",
        0,
        0,
        4,
        """
        SELECT COALESCE(AVG(availability), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    stat_panel(
        2,
        "Cells Monitored",
        4,
        0,
        4,
        """
        SELECT COUNT(*) AS value
        FROM cells;
        """,
        "short",
        0,
    ),
    stat_panel(
        3,
        "Active Users",
        8,
        0,
        4,
        """
        SELECT COALESCE(AVG(active_users), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "short",
        0,
    ),
    stat_panel(
        4,
        "Degraded Cells",
        12,
        0,
        4,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                cell_db_id,
                availability,
                latency_ms,
                packet_loss_pct,
                prb_utilization_pct,
                call_drop_rate,
                rrc_success_rate,
                handover_success_rate
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE availability < 98
           OR latency_ms > 80
           OR packet_loss_pct > 2
           OR prb_utilization_pct > 90
           OR call_drop_rate > 2
           OR rrc_success_rate < 95
           OR handover_success_rate < 94;
        """,
        "short",
        0,
    ),
    stat_panel(
        5,
        "Critical Signals",
        16,
        0,
        4,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                cell_db_id,
                availability,
                latency_ms,
                packet_loss_pct,
                prb_utilization_pct,
                call_drop_rate,
                rrc_success_rate,
                handover_success_rate
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE availability < 95
           OR latency_ms > 120
           OR packet_loss_pct > 5
           OR prb_utilization_pct > 95
           OR call_drop_rate > 5
           OR rrc_success_rate < 90
           OR handover_success_rate < 90;
        """,
        "short",
        0,
    ),
    stat_panel(
        6,
        "Avg Latency",
        20,
        0,
        4,
        """
        SELECT COALESCE(AVG(latency_ms), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "ms",
    ),
    timeseries_panel(
        7,
        "Network Latency",
        0,
        5,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(latency_ms) AS "Latency"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "ms",
    ),
    timeseries_panel(
        8,
        "Network Availability",
        12,
        5,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(availability) AS "Availability"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        9,
        "Packet Loss",
        0,
        13,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(packet_loss_pct) AS "Packet Loss"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        10,
        "Throughput",
        12,
        13,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(throughput_mbps) AS "Throughput"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "Mbps",
    ),
    table_panel(
        11,
        "Top Degraded Cells",
        0,
        21,
        24,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT
            cell_id AS "Cell",
            radio AS "Radio",
            ROUND(availability::numeric, 2) AS "Availability %",
            ROUND(latency_ms::numeric, 2) AS "Latency ms",
            ROUND(packet_loss_pct::numeric, 2) AS "Packet Loss %",
            ROUND(prb_utilization_pct::numeric, 2) AS "PRB %",
            ROUND(rrc_success_rate::numeric, 2) AS "RRC %",
            ROUND(handover_success_rate::numeric, 2) AS "HO %",
            ROUND(call_drop_rate::numeric, 2) AS "Drop %",
            CASE
                WHEN availability < 95
                  OR latency_ms > 120
                  OR packet_loss_pct > 5
                  OR prb_utilization_pct > 95
                  OR call_drop_rate > 5
                THEN 'CRITICAL'
                WHEN availability < 98
                  OR latency_ms > 80
                  OR packet_loss_pct > 2
                  OR prb_utilization_pct > 90
                  OR call_drop_rate > 2
                THEN 'WARNING'
                ELSE 'HEALTHY'
            END AS "Status"
        FROM latest
        WHERE availability < 98
           OR latency_ms > 80
           OR packet_loss_pct > 2
           OR prb_utilization_pct > 90
           OR call_drop_rate > 2
           OR rrc_success_rate < 95
           OR handover_success_rate < 94
        ORDER BY
            CASE
                WHEN availability < 95
                  OR latency_ms > 120
                  OR packet_loss_pct > 5
                  OR prb_utilization_pct > 95
                  OR call_drop_rate > 5
                THEN 1
                ELSE 2
            END,
            latency_ms DESC
        LIMIT 15;
        """,
    ),
]

write_dashboard("telecom-noc.json", d)


# ============================================================
# 02 — RAN PERFORMANCE
# ============================================================

d = base_dashboard(
    "telecom-ran-performance",
    "02 — RAN Performance",
    ["telecom", "ran", "accessibility", "mobility", "retainability"],
)

d["panels"] = [
    stat_panel(
        1,
        "RRC Success",
        0,
        0,
        6,
        """
        SELECT COALESCE(AVG(rrc_success_rate), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    stat_panel(
        2,
        "Handover Success",
        6,
        0,
        6,
        """
        SELECT COALESCE(AVG(handover_success_rate), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    stat_panel(
        3,
        "Call Drop Rate",
        12,
        0,
        6,
        """
        SELECT COALESCE(AVG(call_drop_rate), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    stat_panel(
        4,
        "Packet Loss",
        18,
        0,
        6,
        """
        SELECT COALESCE(AVG(packet_loss_pct), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    timeseries_panel(
        5,
        "RRC Success Rate",
        0,
        5,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(rrc_success_rate) AS "RRC Success"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        6,
        "Handover Success Rate",
        12,
        5,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(handover_success_rate) AS "Handover Success"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        7,
        "Call Drop Rate",
        0,
        13,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(call_drop_rate) AS "Call Drop Rate"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        8,
        "Latency",
        12,
        13,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(latency_ms) AS "Latency"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "ms",
    ),
    timeseries_panel(
        9,
        "Packet Loss",
        0,
        21,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(packet_loss_pct) AS "Packet Loss"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        10,
        "Throughput",
        12,
        21,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(throughput_mbps) AS "Throughput"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "Mbps",
    ),
    table_panel(
        11,
        "RAN Cells Requiring Attention",
        0,
        29,
        24,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT
            cell_id AS "Cell",
            radio AS "Radio",
            ROUND(rrc_success_rate::numeric, 2) AS "RRC %",
            ROUND(handover_success_rate::numeric, 2) AS "HO %",
            ROUND(call_drop_rate::numeric, 2) AS "Drop %",
            ROUND(latency_ms::numeric, 2) AS "Latency ms",
            ROUND(packet_loss_pct::numeric, 2) AS "Loss %",
            CASE
                WHEN rrc_success_rate < 90
                  OR handover_success_rate < 90
                  OR call_drop_rate > 5
                THEN 'CRITICAL'
                WHEN rrc_success_rate < 95
                  OR handover_success_rate < 94
                  OR call_drop_rate > 2
                THEN 'WARNING'
                ELSE 'HEALTHY'
            END AS "Status"
        FROM latest
        WHERE rrc_success_rate < 95
           OR handover_success_rate < 94
           OR call_drop_rate > 2
        ORDER BY rrc_success_rate ASC
        LIMIT 20;
        """,
    ),
]

write_dashboard("telecom-ran-performance.json", d)


# ============================================================
# 03 — CELL HEALTH
# ============================================================

d = base_dashboard(
    "telecom-cell-health",
    "03 — Cell Health",
    ["telecom", "cells", "health", "degradation"],
)

d["panels"] = [
    stat_panel(
        1,
        "Healthy Cells",
        0,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE availability >= 98
          AND latency_ms <= 80
          AND packet_loss_pct <= 2
          AND prb_utilization_pct <= 90
          AND call_drop_rate <= 2
          AND rrc_success_rate >= 95
          AND handover_success_rate >= 94;
        """,
        "short",
        0,
    ),
    stat_panel(
        2,
        "Warning Cells",
        6,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE (
            availability < 98
            OR latency_ms > 80
            OR packet_loss_pct > 2
            OR prb_utilization_pct > 90
            OR call_drop_rate > 2
            OR rrc_success_rate < 95
            OR handover_success_rate < 94
        )
        AND NOT (
            availability < 95
            OR latency_ms > 120
            OR packet_loss_pct > 5
            OR prb_utilization_pct > 95
            OR call_drop_rate > 5
            OR rrc_success_rate < 90
            OR handover_success_rate < 90
        );
        """,
        "short",
        0,
    ),
    stat_panel(
        3,
        "Critical Cells",
        12,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE availability < 95
           OR latency_ms > 120
           OR packet_loss_pct > 5
           OR prb_utilization_pct > 95
           OR call_drop_rate > 5
           OR rrc_success_rate < 90
           OR handover_success_rate < 90;
        """,
        "short",
        0,
    ),
    stat_panel(
        4,
        "Avg PRB Utilization",
        18,
        0,
        6,
        """
        SELECT COALESCE(AVG(prb_utilization_pct), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    table_panel(
        5,
        "Current Cell Health Matrix",
        0,
        5,
        24,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT
            cell_id AS "Cell",
            radio AS "Radio",
            ROUND(latitude::numeric, 5) AS "Latitude",
            ROUND(longitude::numeric, 5) AS "Longitude",
            ROUND(availability::numeric, 2) AS "Availability %",
            ROUND(latency_ms::numeric, 2) AS "Latency ms",
            ROUND(packet_loss_pct::numeric, 2) AS "Loss %",
            ROUND(throughput_mbps::numeric, 2) AS "Mbps",
            ROUND(prb_utilization_pct::numeric, 2) AS "PRB %",
            active_users AS "Users",
            ROUND(rrc_success_rate::numeric, 2) AS "RRC %",
            ROUND(handover_success_rate::numeric, 2) AS "HO %",
            ROUND(call_drop_rate::numeric, 2) AS "Drop %",
            CASE
                WHEN availability < 95
                  OR latency_ms > 120
                  OR packet_loss_pct > 5
                  OR prb_utilization_pct > 95
                  OR call_drop_rate > 5
                  OR rrc_success_rate < 90
                  OR handover_success_rate < 90
                THEN 'CRITICAL'
                WHEN availability < 98
                  OR latency_ms > 80
                  OR packet_loss_pct > 2
                  OR prb_utilization_pct > 90
                  OR call_drop_rate > 2
                  OR rrc_success_rate < 95
                  OR handover_success_rate < 94
                THEN 'WARNING'
                ELSE 'HEALTHY'
            END AS "Status"
        FROM latest
        ORDER BY
            CASE
                WHEN availability < 95
                  OR latency_ms > 120
                  OR packet_loss_pct > 5
                  OR prb_utilization_pct > 95
                  OR call_drop_rate > 5
                  OR rrc_success_rate < 90
                  OR handover_success_rate < 90
                THEN 1
                WHEN availability < 98
                  OR latency_ms > 80
                  OR packet_loss_pct > 2
                  OR prb_utilization_pct > 90
                  OR call_drop_rate > 2
                  OR rrc_success_rate < 95
                  OR handover_success_rate < 94
                THEN 2
                ELSE 3
            END,
            latency_ms DESC;
        """,
    ),
    timeseries_panel(
        6,
        "Cell Availability",
        0,
        14,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(availability) AS "Availability"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        7,
        "PRB Utilization",
        12,
        14,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(prb_utilization_pct) AS "PRB Utilization"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        8,
        "Active Users per Cell — Network Average",
        0,
        22,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(active_users) AS "Active Users"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "short",
        0,
    ),
    timeseries_panel(
        9,
        "Throughput per Cell — Network Average",
        12,
        22,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(throughput_mbps) AS "Throughput"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "Mbps",
    ),
]

write_dashboard("telecom-cell-health.json", d)


# ============================================================
# 04 — ALARM SIGNALS
# ============================================================

d = base_dashboard(
    "telecom-alarm-signals",
    "04 — Alarm Signals",
    ["telecom", "alarms", "incidents", "thresholds"],
)

d["panels"] = [
    stat_panel(
        1,
        "Critical Signals",
        0,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE availability < 95
           OR latency_ms > 120
           OR packet_loss_pct > 5
           OR prb_utilization_pct > 95
           OR call_drop_rate > 5
           OR rrc_success_rate < 90
           OR handover_success_rate < 90;
        """,
        "short",
        0,
    ),
    stat_panel(
        2,
        "Warning Signals",
        6,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE (
            availability < 98
            OR latency_ms > 80
            OR packet_loss_pct > 2
            OR prb_utilization_pct > 90
            OR call_drop_rate > 2
            OR rrc_success_rate < 95
            OR handover_success_rate < 94
        )
        AND NOT (
            availability < 95
            OR latency_ms > 120
            OR packet_loss_pct > 5
            OR prb_utilization_pct > 95
            OR call_drop_rate > 5
            OR rrc_success_rate < 90
            OR handover_success_rate < 90
        );
        """,
        "short",
        0,
    ),
    stat_panel(
        3,
        "Cells Affected",
        12,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE availability < 98
           OR latency_ms > 80
           OR packet_loss_pct > 2
           OR prb_utilization_pct > 90
           OR call_drop_rate > 2
           OR rrc_success_rate < 95
           OR handover_success_rate < 94;
        """,
        "short",
        0,
    ),
    stat_panel(
        4,
        "Network Availability",
        18,
        0,
        6,
        """
        SELECT COALESCE(AVG(availability), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    table_panel(
        5,
        "Current Network Alert Signals",
        0,
        5,
        24,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        ),
        signals AS (
            SELECT cell_id, radio, timestamp,
                   'AVAILABILITY' AS alarm,
                   ROUND(availability::numeric, 2) AS value,
                   '%' AS unit,
                   CASE WHEN availability < 95 THEN 'CRITICAL' ELSE 'WARNING' END AS severity
            FROM latest
            WHERE availability < 98

            UNION ALL

            SELECT cell_id, radio, timestamp,
                   'HIGH LATENCY',
                   ROUND(latency_ms::numeric, 2),
                   'ms',
                   CASE WHEN latency_ms > 120 THEN 'CRITICAL' ELSE 'WARNING' END
            FROM latest
            WHERE latency_ms > 80

            UNION ALL

            SELECT cell_id, radio, timestamp,
                   'PACKET LOSS',
                   ROUND(packet_loss_pct::numeric, 2),
                   '%',
                   CASE WHEN packet_loss_pct > 5 THEN 'CRITICAL' ELSE 'WARNING' END
            FROM latest
            WHERE packet_loss_pct > 2

            UNION ALL

            SELECT cell_id, radio, timestamp,
                   'HIGH PRB UTILIZATION',
                   ROUND(prb_utilization_pct::numeric, 2),
                   '%',
                   CASE WHEN prb_utilization_pct > 95 THEN 'CRITICAL' ELSE 'WARNING' END
            FROM latest
            WHERE prb_utilization_pct > 90

            UNION ALL

            SELECT cell_id, radio, timestamp,
                   'CALL DROP RATE',
                   ROUND(call_drop_rate::numeric, 2),
                   '%',
                   CASE WHEN call_drop_rate > 5 THEN 'CRITICAL' ELSE 'WARNING' END
            FROM latest
            WHERE call_drop_rate > 2

            UNION ALL

            SELECT cell_id, radio, timestamp,
                   'RRC SUCCESS',
                   ROUND(rrc_success_rate::numeric, 2),
                   '%',
                   CASE WHEN rrc_success_rate < 90 THEN 'CRITICAL' ELSE 'WARNING' END
            FROM latest
            WHERE rrc_success_rate < 95

            UNION ALL

            SELECT cell_id, radio, timestamp,
                   'HANDOVER SUCCESS',
                   ROUND(handover_success_rate::numeric, 2),
                   '%',
                   CASE WHEN handover_success_rate < 90 THEN 'CRITICAL' ELSE 'WARNING' END
            FROM latest
            WHERE handover_success_rate < 94
        )
        SELECT
            timestamp AS "Last Seen",
            cell_id AS "Cell",
            radio AS "Radio",
            severity AS "Severity",
            alarm AS "Alarm",
            value AS "Value",
            unit AS "Unit"
        FROM signals
        ORDER BY
            CASE severity
                WHEN 'CRITICAL' THEN 1
                ELSE 2
            END,
            timestamp DESC
        LIMIT 50;
        """,
    ),
    timeseries_panel(
        6,
        "Latency — Alarm Context",
        0,
        14,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(latency_ms) AS "Latency",
            80 AS "Warning Threshold",
            120 AS "Critical Threshold"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "ms",
    ),
    timeseries_panel(
        7,
        "PRB Utilization — Congestion Context",
        12,
        14,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(prb_utilization_pct) AS "PRB",
            90 AS "Warning Threshold",
            95 AS "Critical Threshold"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        8,
        "Packet Loss — Alarm Context",
        0,
        22,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(packet_loss_pct) AS "Packet Loss",
            2 AS "Warning Threshold",
            5 AS "Critical Threshold"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        9,
        "Call Drop Rate — Alarm Context",
        12,
        22,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(call_drop_rate) AS "Call Drop",
            2 AS "Warning Threshold",
            5 AS "Critical Threshold"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
]

write_dashboard("telecom-alarm-signals.json", d)


# ============================================================
# 05 — TRAFFIC & CAPACITY
# ============================================================

d = base_dashboard(
    "telecom-traffic-capacity",
    "05 — Traffic & Capacity",
    ["telecom", "traffic", "capacity", "congestion"],
)

d["panels"] = [
    stat_panel(
        1,
        "Active Users",
        0,
        0,
        6,
        """
        SELECT COALESCE(AVG(active_users), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "short",
        0,
    ),
    stat_panel(
        2,
        "PRB Utilization",
        6,
        0,
        6,
        """
        SELECT COALESCE(AVG(prb_utilization_pct), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "percent",
    ),
    stat_panel(
        3,
        "Throughput",
        12,
        0,
        6,
        """
        SELECT COALESCE(AVG(throughput_mbps), 0) AS value
        FROM network_kpis
        WHERE $__timeFilter(timestamp);
        """,
        "Mbps",
    ),
    stat_panel(
        4,
        "Congested Cells",
        18,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT COUNT(*) AS value
        FROM latest
        WHERE prb_utilization_pct > 90;
        """,
        "short",
        0,
    ),
    timeseries_panel(
        5,
        "Active Users",
        0,
        5,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(active_users) AS "Active Users"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "short",
        0,
    ),
    timeseries_panel(
        6,
        "PRB Utilization",
        12,
        5,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(prb_utilization_pct) AS "PRB Utilization",
            90 AS "Congestion Threshold"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "percent",
    ),
    timeseries_panel(
        7,
        "Network Throughput",
        0,
        13,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(throughput_mbps) AS "Throughput"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "Mbps",
    ),
    timeseries_panel(
        8,
        "Latency vs Utilization",
        12,
        13,
        12,
        """
        SELECT
            date_trunc('minute', timestamp) AS time,
            AVG(latency_ms) AS "Latency ms",
            AVG(prb_utilization_pct) AS "PRB %"
        FROM network_kpis
        WHERE $__timeFilter(timestamp)
        GROUP BY 1
        ORDER BY 1;
        """,
        "short",
        2,
    ),
    table_panel(
        9,
        "Top Congested Cells",
        0,
        21,
        24,
        """
        WITH latest AS (
            SELECT DISTINCT ON (cell_db_id)
                *
            FROM network_kpis
            ORDER BY cell_db_id, timestamp DESC
        )
        SELECT
            cell_id AS "Cell",
            radio AS "Radio",
            ROUND(prb_utilization_pct::numeric, 2) AS "PRB %",
            active_users AS "Active Users",
            ROUND(throughput_mbps::numeric, 2) AS "Throughput Mbps",
            ROUND(latency_ms::numeric, 2) AS "Latency ms",
            ROUND(packet_loss_pct::numeric, 2) AS "Packet Loss %",
            ROUND(availability::numeric, 2) AS "Availability %",
            CASE
                WHEN prb_utilization_pct > 95 THEN 'CRITICAL'
                WHEN prb_utilization_pct > 90 THEN 'WARNING'
                ELSE 'NORMAL'
            END AS "Capacity Status"
        FROM latest
        WHERE prb_utilization_pct > 80
        ORDER BY prb_utilization_pct DESC
        LIMIT 20;
        """,
    ),
]

write_dashboard("telecom-traffic-capacity.json", d)


print()
print("All telecom NOC dashboards generated successfully.")
# ============================================================
# 06 — REGIONAL NETWORK INTELLIGENCE
# ============================================================

d = base_dashboard(
    "telecom-regional-intelligence",
    "06 — Regional Network Intelligence",
    ["telecom", "regional", "wilaya", "geography", "operations"],
)

d["templating"] = {
    "list": [
        {
            "name": "wilaya",
            "label": "Wilaya",
            "type": "query",
            "datasource": datasource(),
            "query": """
                SELECT 'All' AS wilaya
                UNION ALL
                SELECT DISTINCT wilaya_normalized
                FROM cells
                WHERE geo_match_status = 'MATCHED'
                  AND wilaya_normalized IS NOT NULL
                ORDER BY 1;
            """,
            "includeAll": False,
            "multi": False,
            "current": {
                "selected": True,
                "text": "All",
                "value": "All",
            },
        }
    ]
}

d["panels"] = [

    # --------------------------------------------------------
    # 1 — CELLS IN SCOPE
    # --------------------------------------------------------

    stat_panel(
        1,
        "Cells in Scope",
        0,
        0,
        6,
        """
        SELECT COUNT(*) AS value
        FROM cells
        WHERE '${wilaya}' = 'All'
           OR wilaya_normalized = '${wilaya}';
        """,
        "short",
        0,
    ),

    # --------------------------------------------------------
    # 2 — WILAYAS WITH CELLS
    # --------------------------------------------------------

    stat_panel(
        2,
        "Wilayas with Cells",
        6,
        0,
        6,
        """
        SELECT COUNT(DISTINCT wilaya_normalized) AS value
        FROM cells
        WHERE geo_match_status = 'MATCHED'
          AND wilaya_normalized IS NOT NULL
          AND (
              '${wilaya}' = 'All'
              OR wilaya_normalized = '${wilaya}'
          );
        """,
        "short",
        0,
    ),

    # --------------------------------------------------------
    # 3 — BOUNDARY REVIEW
    # --------------------------------------------------------

    stat_panel(
        3,
        "Boundary Review",
        12,
        0,
        6,
        """
        SELECT COUNT(*) AS value
        FROM cells
        WHERE geo_match_status = 'BOUNDARY_REVIEW'
          AND (
              '${wilaya}' = 'All'
              OR wilaya_name_fr = '${wilaya}'
          );
        """,
        "short",
        0,
    ),

    # --------------------------------------------------------
    # 4 — REGIONAL AVAILABILITY
    # --------------------------------------------------------

    stat_panel(
        4,
        "Regional Availability",
        18,
        0,
        6,
        """
        WITH latest AS (
            SELECT DISTINCT ON (k.cell_db_id)
                k.cell_db_id,
                k.availability
            FROM network_kpis k
            JOIN cells c
              ON c.id = k.cell_db_id
            WHERE '${wilaya}' = 'All'
               OR c.wilaya_normalized = '${wilaya}'
            ORDER BY k.cell_db_id, k.timestamp DESC
        )
        SELECT COALESCE(AVG(availability), 0) AS value
        FROM latest;
        """,
        "percent",
        2,
    ),

    # --------------------------------------------------------
    # 5 — CELLS BY WILAYA
    # --------------------------------------------------------

    table_panel(
        5,
        "Cells by Wilaya",
        0,
        5,
        12,
        """
        SELECT
            COALESCE(wilaya_normalized, 'Boundary Review') AS "Wilaya",
            COUNT(*) AS "Cells",
            COUNT(*) FILTER (
                WHERE geo_match_status = 'MATCHED'
            ) AS "Matched",
            COUNT(*) FILTER (
                WHERE geo_match_status = 'BOUNDARY_REVIEW'
            ) AS "Boundary Review"
        FROM cells
        WHERE '${wilaya}' = 'All'
           OR wilaya_normalized = '${wilaya}'
        GROUP BY wilaya_normalized
        ORDER BY COUNT(*) DESC;
        """,
    ),

    # --------------------------------------------------------
    # 6 — REGIONAL NETWORK HEALTH
    # --------------------------------------------------------

    table_panel(
        6,
        "Regional Network Health",
        12,
        5,
        12,
        """
        WITH latest AS (
            SELECT DISTINCT ON (k.cell_db_id)
                k.cell_db_id,
                k.availability,
                k.latency_ms,
                k.packet_loss_pct,
                k.throughput_mbps,
                k.prb_utilization_pct,
                k.rrc_success_rate,
                k.handover_success_rate,
                k.call_drop_rate
            FROM network_kpis k
            JOIN cells c
              ON c.id = k.cell_db_id
            WHERE '${wilaya}' = 'All'
               OR c.wilaya_normalized = '${wilaya}'
            ORDER BY k.cell_db_id, k.timestamp DESC
        )
        SELECT
            COUNT(*) AS "Cells",
            ROUND(AVG(availability)::numeric, 2) AS "Availability %",
            ROUND(AVG(latency_ms)::numeric, 2) AS "Latency ms",
            ROUND(AVG(packet_loss_pct)::numeric, 2) AS "Packet Loss %",
            ROUND(AVG(throughput_mbps)::numeric, 2) AS "Throughput Mbps",
            ROUND(AVG(prb_utilization_pct)::numeric, 2) AS "PRB %",
            ROUND(AVG(rrc_success_rate)::numeric, 2) AS "RRC %",
            ROUND(AVG(handover_success_rate)::numeric, 2) AS "HO %",
            ROUND(AVG(call_drop_rate)::numeric, 2) AS "Drop %"
        FROM latest;
        """,
    ),

    # --------------------------------------------------------
    # 7 — LATENCY BY WILAYA
    # --------------------------------------------------------

    timeseries_panel(
        7,
        "Latency by Wilaya",
        0,
        14,
        12,
        """
        SELECT
            date_trunc('minute', k.timestamp) AS time,
            c.wilaya_normalized AS "Wilaya",
            AVG(k.latency_ms) AS "Latency"
        FROM network_kpis k
        JOIN cells c
          ON c.id = k.cell_db_id
        WHERE $__timeFilter(k.timestamp)
          AND c.geo_match_status = 'MATCHED'
          AND (
              '${wilaya}' = 'All'
              OR c.wilaya_normalized = '${wilaya}'
          )
        GROUP BY 1, 2
        ORDER BY 1;
        """,
        "ms",
        2,
    ),

    # --------------------------------------------------------
    # 8 — PACKET LOSS BY WILAYA
    # --------------------------------------------------------

    timeseries_panel(
        8,
        "Packet Loss by Wilaya",
        12,
        14,
        12,
        """
        SELECT
            date_trunc('minute', k.timestamp) AS time,
            c.wilaya_normalized AS "Wilaya",
            AVG(k.packet_loss_pct) AS "Packet Loss"
        FROM network_kpis k
        JOIN cells c
          ON c.id = k.cell_db_id
        WHERE $__timeFilter(k.timestamp)
          AND c.geo_match_status = 'MATCHED'
          AND (
              '${wilaya}' = 'All'
              OR c.wilaya_normalized = '${wilaya}'
          )
        GROUP BY 1, 2
        ORDER BY 1;
        """,
        "percent",
        2,
    ),

    # --------------------------------------------------------
    # 9 — TRAFFIC & CAPACITY BY WILAYA
    # --------------------------------------------------------

    table_panel(
        9,
        "Traffic & Capacity by Wilaya",
        0,
        22,
        24,
        """
        WITH latest AS (
            SELECT DISTINCT ON (k.cell_db_id)
                k.cell_db_id,
                k.active_users,
                k.throughput_mbps,
                k.prb_utilization_pct,
                k.latency_ms
            FROM network_kpis k
            JOIN cells c
              ON c.id = k.cell_db_id
            WHERE '${wilaya}' = 'All'
               OR c.wilaya_normalized = '${wilaya}'
            ORDER BY k.cell_db_id, k.timestamp DESC
        )
        SELECT
            c.wilaya_normalized AS "Wilaya",
            COUNT(*) AS "Cells",
            ROUND(AVG(latest.active_users)::numeric, 0) AS "Active Users",
            ROUND(AVG(latest.throughput_mbps)::numeric, 2) AS "Throughput Mbps",
            ROUND(AVG(latest.prb_utilization_pct)::numeric, 2) AS "PRB %",
            ROUND(AVG(latest.latency_ms)::numeric, 2) AS "Latency ms"
        FROM latest
        JOIN cells c
          ON c.id = latest.cell_db_id
        GROUP BY c.wilaya_normalized
        ORDER BY AVG(latest.prb_utilization_pct) DESC;
        """,
    ),

    # --------------------------------------------------------
    # 10 — CRITICAL & MAJOR ALARMS BY WILAYA
    # --------------------------------------------------------

    table_panel(
        10,
        "Critical & Major Alarms by Wilaya",
        0,
        31,
        12,
        """
        SELECT
            COALESCE(c.wilaya_normalized, 'Boundary Review') AS "Wilaya",
            COUNT(*) FILTER (
                WHERE a.severity = 'CRITICAL'
            ) AS "Critical",
            COUNT(*) FILTER (
                WHERE a.severity IN ('MAJOR', 'WARNING')
            ) AS "Major / Warning",
            COUNT(*) AS "Total"
        FROM network_alarms a
        LEFT JOIN cells c
          ON c.id = a.cell_db_id
        WHERE a.timestamp >= NOW() - INTERVAL '24 hours'
          AND (
              '${wilaya}' = 'All'
              OR c.wilaya_normalized = '${wilaya}'
          )
        GROUP BY c.wilaya_normalized
        ORDER BY COUNT(*) DESC;
        """,
    ),

    # --------------------------------------------------------
    # 11 — REGIONAL ALARM BREAKDOWN
    # --------------------------------------------------------

    table_panel(
        11,
        "Regional Alarm Breakdown",
        12,
        31,
        12,
        """
        SELECT
            COALESCE(c.wilaya_normalized, 'Boundary Review') AS "Wilaya",
            a.alarm_type AS "Alarm Type",
            a.severity AS "Severity",
            COUNT(*) AS "Count"
        FROM network_alarms a
        LEFT JOIN cells c
          ON c.id = a.cell_db_id
        WHERE a.timestamp >= NOW() - INTERVAL '24 hours'
          AND (
              '${wilaya}' = 'All'
              OR c.wilaya_normalized = '${wilaya}'
          )
        GROUP BY
            c.wilaya_normalized,
            a.alarm_type,
            a.severity
        ORDER BY COUNT(*) DESC
        LIMIT 30;
        """,
    ),

    # --------------------------------------------------------
    # 12 — GEOGRAPHIC DATA QUALITY
    # --------------------------------------------------------

    table_panel(
        12,
        "Geographic Data Quality",
        0,
        40,
        12,
        """
        SELECT
            geo_match_status AS "Status",
            COUNT(*) AS "Cells",
            ROUND(
                COUNT(*) * 100.0 /
                NULLIF((SELECT COUNT(*) FROM cells), 0),
                2
            ) AS "Coverage %"
        FROM cells
        GROUP BY geo_match_status
        ORDER BY COUNT(*) DESC;
        """,
    ),

    # --------------------------------------------------------
    # 13 — REGIONAL CELL HEALTH DETAIL
    # --------------------------------------------------------

    table_panel(
        13,
        "Regional Cell Health Detail",
        12,
        40,
        12,
        """
        WITH latest AS (
            SELECT DISTINCT ON (k.cell_db_id)
                k.*
            FROM network_kpis k
            JOIN cells c
              ON c.id = k.cell_db_id
            WHERE '${wilaya}' = 'All'
               OR c.wilaya_normalized = '${wilaya}'
            ORDER BY k.cell_db_id, k.timestamp DESC
        )
        SELECT
            latest.cell_id AS "Cell",
            c.wilaya_normalized AS "Wilaya",
            latest.radio AS "Radio",
            ROUND(latest.availability::numeric, 2) AS "Availability %",
            ROUND(latest.latency_ms::numeric, 2) AS "Latency ms",
            ROUND(latest.packet_loss_pct::numeric, 2) AS "Loss %",
            ROUND(latest.prb_utilization_pct::numeric, 2) AS "PRB %",
            ROUND(latest.rrc_success_rate::numeric, 2) AS "RRC %",
            ROUND(latest.handover_success_rate::numeric, 2) AS "HO %",
            ROUND(latest.call_drop_rate::numeric, 2) AS "Drop %",
            CASE
                WHEN latest.availability < 95
                  OR latest.latency_ms > 120
                  OR latest.packet_loss_pct > 5
                  OR latest.prb_utilization_pct > 95
                  OR latest.call_drop_rate > 5
                  OR latest.rrc_success_rate < 90
                  OR latest.handover_success_rate < 90
                THEN 'CRITICAL'
                WHEN latest.availability < 98
                  OR latest.latency_ms > 80
                  OR latest.packet_loss_pct > 2
                  OR latest.prb_utilization_pct > 90
                  OR latest.call_drop_rate > 2
                  OR latest.rrc_success_rate < 95
                  OR latest.handover_success_rate < 94
                THEN 'WARNING'
                ELSE 'HEALTHY'
            END AS "Status"
        FROM latest
        JOIN cells c
          ON c.id = latest.cell_db_id
        ORDER BY
            CASE
                WHEN latest.availability < 95
                  OR latest.latency_ms > 120
                  OR latest.packet_loss_pct > 5
                  OR latest.prb_utilization_pct > 95
                  OR latest.call_drop_rate > 5
                  OR latest.rrc_success_rate < 90
                  OR latest.handover_success_rate < 90
                THEN 1
                WHEN latest.availability < 98
                  OR latest.latency_ms > 80
                  OR latest.packet_loss_pct > 2
                  OR latest.prb_utilization_pct > 90
                  OR latest.call_drop_rate > 2
                  OR latest.rrc_success_rate < 95
                  OR latest.handover_success_rate < 94
                THEN 2
                ELSE 3
            END,
            latest.latency_ms DESC
        LIMIT 50;
        """,
    ),

    # --------------------------------------------------------
    # 14 — NATIONAL CELL MAP
    # --------------------------------------------------------

    {
        "id": 14,
        "type": "geomap",
        "title": "Algeria Network Cell Map",
        "description": "Geographic view of network cells with latest KPI health state.",
        "gridPos": {
            "x": 0,
            "y": 54,
            "w": 24,
            "h": 16,
        },
        "datasource": datasource(),

        "targets": [
            {
                "refId": "A",
                "datasource": datasource(),
                "format": "table",
                "rawQuery": True,

                "rawSql": """
                    WITH latest AS (
                        SELECT DISTINCT ON (k.cell_db_id)
                            k.cell_db_id,
                            k.timestamp,
                            k.cell_id,
                            k.radio,
                            k.availability,
                            k.latency_ms,
                            k.packet_loss_pct,
                            k.throughput_mbps,
                            k.prb_utilization_pct,
                            k.rrc_success_rate,
                            k.handover_success_rate,
                            k.call_drop_rate,
                            k.active_users
                        FROM network_kpis k
                        ORDER BY
                            k.cell_db_id,
                            k.timestamp DESC
                    ),

                    network_state AS (
                        SELECT
                            c.id,
                            c.latitude,
                            c.longitude,
                            c.cell_id,
                            c.radio,
                            c.wilaya_normalized,

                            latest.timestamp,
                            latest.availability,
                            latest.latency_ms,
                            latest.packet_loss_pct,
                            latest.throughput_mbps,
                            latest.prb_utilization_pct,
                            latest.rrc_success_rate,
                            latest.handover_success_rate,
                            latest.call_drop_rate,
                            latest.active_users,

                            CASE
                                WHEN latest.cell_db_id IS NULL
                                    THEN 'NO KPI DATA'

                                WHEN latest.availability < 95
                                  OR latest.latency_ms > 120
                                  OR latest.packet_loss_pct > 5
                                  OR latest.prb_utilization_pct > 95
                                  OR latest.call_drop_rate > 5
                                  OR latest.rrc_success_rate < 90
                                  OR latest.handover_success_rate < 90
                                    THEN 'CRITICAL'

                                WHEN latest.availability < 98
                                  OR latest.latency_ms > 80
                                  OR latest.packet_loss_pct > 2
                                  OR latest.prb_utilization_pct > 90
                                  OR latest.call_drop_rate > 2
                                  OR latest.rrc_success_rate < 95
                                  OR latest.handover_success_rate < 94
                                    THEN 'WARNING'

                                ELSE 'HEALTHY'
                            END AS status

                        FROM cells c

                        LEFT JOIN latest
                            ON latest.cell_db_id = c.id

                        WHERE c.latitude IS NOT NULL
                          AND c.longitude IS NOT NULL
                          AND (
                              '${wilaya}' = 'All'
                              OR c.wilaya_normalized = '${wilaya}'
                          )
                    )

                    SELECT
                        latitude,
                        longitude,

                        cell_id AS "Cell",
                        radio AS "Radio",
                        wilaya_normalized AS "Wilaya",

                        ROUND(availability::numeric, 2)
                            AS "Availability %",
                        ROUND(latency_ms::numeric, 2)
                            AS "Latency ms",
                        ROUND(packet_loss_pct::numeric, 2)
                            AS "Packet Loss %",
                        ROUND(throughput_mbps::numeric, 2)
                            AS "Throughput Mbps",
                        ROUND(prb_utilization_pct::numeric, 2)
                            AS "PRB %",
                        ROUND(rrc_success_rate::numeric, 2)
                            AS "RRC %",
                        ROUND(handover_success_rate::numeric, 2)
                            AS "HO %",
                        ROUND(call_drop_rate::numeric, 2)
                            AS "Drop %",
                        active_users AS "Active Users",
                        timestamp AS "Last Seen",

                        status AS "Status",

                        CASE status
                            WHEN 'HEALTHY' THEN 1
                            WHEN 'WARNING' THEN 2
                            WHEN 'CRITICAL' THEN 3
                            WHEN 'NO KPI DATA' THEN 0
                            ELSE 0
                        END AS "Health Code"

                    FROM network_state

                    ORDER BY
                        wilaya_normalized,
                        cell_id;
                """,
            }
        ],

        "options": {
            "view": {
                "id": "fit",
                "lat": 28.0339,
                "lon": 1.6596,
                "zoom": 5,
                "allLayers": True,
                "lastOnly": False,
            },

            "controls": {
                "showZoom": True,
                "mouseWheelZoom": True,
                "showAttribution": True,
                "showScale": True,
                "showMeasure": False,
                "showDebug": False,
            },

            "tooltip": {
                "mode": "details",
            },

            "basemap": {
                "config": {},
                "name": "Layer 0",
                "type": "default",
            },

            "layers": [
                {
                    "config": {
                        "showLegend": True,

                        "style": {
                            "color": {
                                "field": "Health Code",
                            },

                            "opacity": 0.85,

                            "size": {
                                "field": "PRB %",
                                "min": 5,
                                "max": 15,
                            },

                            "symbol": {
                                "fixed": "img/icons/marker/circle.svg",
                                "mode": "fixed",
                            },

                            "rotation": {
                                "fixed": 0,
                                "min": -360,
                                "max": 360,
                                "mode": "mod",
                            },

                            "textConfig": {
                                "fontSize": 11,
                                "offsetX": 0,
                                "offsetY": 0,
                                "textAlign": "center",
                                "textBaseline": "middle",
                            },
                        },
                    },

                    "filterData": {
                        "id": "byRefId",
                        "options": "A",
                    },

                    "location": {
                        "latitude": "latitude",
                        "longitude": "longitude",
                        "mode": "coords",
                    },

                    "name": "Network Cells",

                    "tooltip": True,

                    "type": "markers",
                },
            ],
        },

        "fieldConfig": {
            "defaults": {
                "color": {
                    "mode": "thresholds",
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {
                            "color": "gray",
                            "value": None,
                        },
                        {
                            "color": "green",
                            "value": 1,
                        },
                        {
                            "color": "yellow",
                            "value": 2,
                        },
                        {
                            "color": "red",
                            "value": 3,
                        },
                    ],
                },
            },

            "overrides": [],
        },
    },
]

write_dashboard(
    "telecom-regional-intelligence.json",
    d,
)


print()
print("All telecom NOC dashboards generated successfully.")