import os
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from api.main import (
    AlarmActionRequest,
    acknowledge_alarm,
    resolve_alarm,
    latest_alarms,
    cell_alarms,
    alarm_summary,
    format_alarm_row,
    get_alarm,
)


class TestAlarmLifecycleUnit(unittest.TestCase):
    """
    Unit tests for Alarm Lifecycle Management.
    Does not require a live Kafka broker or database.
    """

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.mock_alarm_row = (
            101,  # 0: id
            self.now,  # 1: timestamp
            12345,  # 2: cell_id
            "LTE",  # 3: radio
            "HIGH_LATENCY",  # 4: alarm_type
            "CRITICAL",  # 5: severity
            "latency_ms",  # 6: metric
            150.0,  # 7: metric_value
            120.0,  # 8: threshold_value
            "High latency observed",  # 9: message
            "OPEN",  # 10: status
            self.now,  # 11: created_at
            None,  # 12: acknowledged_at
            None,  # 13: acknowledged_by
            None,  # 14: resolved_at
            None,  # 15: resolved_by
            16,  # 16: wilaya_code
            "Algiers",  # 17: wilaya_name
            "Alger",  # 18: wilaya_name_fr
            "MATCHED",  # 19: geo_match_status
        )

    # -------------------------------------------------------------------------
    # 1. OPEN -> ACKNOWLEDGED
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_01_open_to_acknowledged(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # First fetchone returns existing OPEN alarm row
        # Second fetchone returns updated row with ACKNOWLEDGED status
        ack_time = self.now + timedelta(minutes=2)
        ack_row = list(self.mock_alarm_row)
        ack_row[10] = "ACKNOWLEDGED"
        ack_row[12] = ack_time
        ack_row[13] = "operator_1"

        mock_cursor.fetchone.side_effect = [
            (101, "OPEN"),  # check existing
            tuple(ack_row),  # return updated
        ]

        payload = AlarmActionRequest(username="operator_1")
        result = acknowledge_alarm(101, payload)

        self.assertEqual(result["id"], 101)
        self.assertEqual(result["status"], "ACKNOWLEDGED")
        self.assertEqual(result["acknowledged_by"], "operator_1")
        self.assertEqual(result["acknowledged_at"], ack_time)
        mock_conn.commit.assert_called_once()

    # -------------------------------------------------------------------------
    # 2. ACKNOWLEDGED -> RESOLVED
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_02_acknowledged_to_resolved(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        res_time = self.now + timedelta(minutes=10)
        res_row = list(self.mock_alarm_row)
        res_row[10] = "RESOLVED"
        res_row[12] = self.now + timedelta(minutes=2)
        res_row[13] = "operator_1"
        res_row[14] = res_time
        res_row[15] = "engineer_2"

        mock_cursor.fetchone.side_effect = [
            (101, "ACKNOWLEDGED"),  # check existing
            tuple(res_row),  # return updated
        ]

        payload = AlarmActionRequest(username="engineer_2")
        result = resolve_alarm(101, payload)

        self.assertEqual(result["id"], 101)
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["resolved_by"], "engineer_2")
        self.assertEqual(result["resolved_at"], res_time)
        mock_conn.commit.assert_called_once()

    # -------------------------------------------------------------------------
    # 3. OPEN -> RESOLVED
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_03_open_to_resolved(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        res_time = self.now + timedelta(minutes=5)
        res_row = list(self.mock_alarm_row)
        res_row[10] = "RESOLVED"
        res_row[14] = res_time
        res_row[15] = "auto_healer"

        mock_cursor.fetchone.side_effect = [
            (101, "OPEN"),  # check existing
            tuple(res_row),  # return updated
        ]

        payload = AlarmActionRequest(username="auto_healer")
        result = resolve_alarm(101, payload)

        self.assertEqual(result["id"], 101)
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["resolved_by"], "auto_healer")
        mock_conn.commit.assert_called_once()

    # -------------------------------------------------------------------------
    # 4. RESOLVED -> ACKNOWLEDGED rejected
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_04_resolved_to_acknowledged_rejected(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (101, "RESOLVED")

        payload = AlarmActionRequest(username="operator_1")
        with self.assertRaises(HTTPException) as ctx:
            acknowledge_alarm(101, payload)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("resolved", ctx.exception.detail.lower())

    # -------------------------------------------------------------------------
    # 5. RESOLVED -> OPEN rejected / ACKNOWLEDGED -> OPEN rejected
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_05_resolved_or_ack_to_open_rejected(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # If already acknowledged, trying to acknowledge again gives 409
        mock_cursor.fetchone.return_value = (101, "ACKNOWLEDGED")
        payload = AlarmActionRequest(username="operator_1")
        with self.assertRaises(HTTPException) as ctx:
            acknowledge_alarm(101, payload)
        self.assertEqual(ctx.exception.status_code, 409)

        # If already resolved, trying to resolve again gives 409
        mock_cursor.fetchone.return_value = (101, "RESOLVED")
        with self.assertRaises(HTTPException) as ctx:
            resolve_alarm(101, payload)
        self.assertEqual(ctx.exception.status_code, 409)

    # -------------------------------------------------------------------------
    # 6. Nonexistent alarm returns 404
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_06_nonexistent_alarm_returns_404(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.return_value = None

        payload = AlarmActionRequest(username="operator_1")
        with self.assertRaises(HTTPException) as ctx_ack:
            acknowledge_alarm(999999, payload)
        self.assertEqual(ctx_ack.exception.status_code, 404)

        with self.assertRaises(HTTPException) as ctx_res:
            resolve_alarm(999999, payload)
        self.assertEqual(ctx_res.exception.status_code, 404)

    # -------------------------------------------------------------------------
    # 7. Invalid username/request rejected (422)
    # -------------------------------------------------------------------------
    def test_07_invalid_username_rejected(self):
        # Empty string
        with self.assertRaises(ValidationError):
            AlarmActionRequest(username="")

        # Whitespace only
        with self.assertRaises(ValidationError):
            AlarmActionRequest(username="   ")

        # None / missing
        with self.assertRaises(ValidationError):
            AlarmActionRequest.model_validate({})

    # -------------------------------------------------------------------------
    # 8. MTTA calculation
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_08_mtta_calculation(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock database aggregation output with MTTA = 180 seconds (3.0 minutes)
        mock_cursor.fetchone.return_value = (
            50,    # total_alarms
            10,    # critical_alarms
            35,    # major_alarms
            5,     # minor_alarms
            20,    # open_alarms
            15,    # acknowledged_alarms
            15,    # resolved_alarms
            8,     # affected_cells
            180.0, # avg_mtta_seconds
            3.0,   # avg_mtta_minutes
            720.0, # avg_mttr_seconds
            12.0,  # avg_mttr_minutes
        )

        summary = alarm_summary()

        self.assertEqual(summary["total_alarms"], 50)
        self.assertEqual(summary["total"], 50)
        self.assertEqual(summary["open"], 20)
        self.assertEqual(summary["acknowledged"], 15)
        self.assertEqual(summary["resolved"], 15)
        self.assertEqual(summary["average_mtta_seconds"], 180.0)
        self.assertEqual(summary["average_mtta_minutes"], 3.0)

    # -------------------------------------------------------------------------
    # 9. MTTR calculation
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_09_mttr_calculation(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (
            100,    # total_alarms
            20,     # critical_alarms
            70,     # major_alarms
            10,     # minor_alarms
            30,     # open_alarms
            30,     # acknowledged_alarms
            40,     # resolved_alarms
            15,     # affected_cells
            240.0,  # avg_mtta_seconds
            4.0,    # avg_mtta_minutes
            900.0,  # avg_mttr_seconds (15.0 minutes)
            15.0,   # avg_mttr_minutes
        )

        summary = alarm_summary()

        self.assertEqual(summary["average_mttr_seconds"], 900.0)
        self.assertEqual(summary["average_mttr_minutes"], 15.0)

    # -------------------------------------------------------------------------
    # 10. Existing alarm endpoints still work and return all required fields
    # -------------------------------------------------------------------------
    @patch("api.main.get_connection")
    def test_10_existing_alarm_endpoints(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [self.mock_alarm_row]

        # Test latest_alarms
        latest = latest_alarms(limit=10)
        self.assertEqual(len(latest), 1)
        item = latest[0]

        # Verify all requested lifecycle and provenance fields exist
        required_fields = [
            "id",
            "timestamp",
            "cell_id",
            "alarm_type",
            "severity",
            "metric",
            "metric_value",
            "threshold_value",
            "message",
            "status",
            "created_at",
            "acknowledged_at",
            "acknowledged_by",
            "resolved_at",
            "resolved_by",
            "wilaya_name_fr",
        ]
        for field in required_fields:
            self.assertIn(field, item, f"Missing required field: {field}")

        # Test cell_alarms
        cell_res = cell_alarms(cell_id=12345, limit=5)
        self.assertEqual(len(cell_res), 1)
        for field in required_fields:
            self.assertIn(field, cell_res[0], f"Missing required field: {field}")


if __name__ == "__main__":
    unittest.main()
