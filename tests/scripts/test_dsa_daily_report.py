"""Tests for dsa_daily_report.py — report building and email integration."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.dsa_daily_report import (
    _already_sent_today,
    _mark_sent_today,
    build_report,
)
from src.common.dsa_utils import BREAK_EVEN_ROAS

TZ_LOCAL = timezone(timedelta(hours=3))


class TestBuildReport:
    def _make_order(self, price, landing="", tags="", source="web"):
        return {
            "order_number": 1001,
            "total_price": str(price),
            "landing_site": landing,
            "referring_site": "",
            "tags": tags,
            "source_name": source,
        }

    def test_report_with_dsa_orders(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        orders = [
            self._make_order(25.50, landing="/?gclid=x&gad_campaignid=23713866882"),
            self._make_order(15.00),
        ]
        dsa = [orders[0]]
        organic = [orders[1]]

        subject, body, alerts = build_report(1, orders, dsa, [], organic, now)

        assert "ROAS" in subject
        assert "1 DSA orders" in subject
        assert "DSA campaign:       1" in body
        assert "Organic/direct:     1" in body
        assert "EUR 25.50" in body

    def test_report_zero_orders_alert(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        subject, body, alerts = build_report(1, [], [], [], [], now)

        assert "0 DSA orders" in subject
        assert any("ZERO orders" in a for a in alerts)

    def test_report_break_even_shown(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        subject, body, alerts = build_report(1, [], [], [], [], now)

        assert "break-even" in body
        assert str(BREAK_EVEN_ROAS) in body

    def test_report_below_break_even_alert(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        # ROAS = 50/10 = 5x, which is below break-even (~18.87x)
        dsa = [self._make_order(50.00, landing="/?gclid=x&gad_campaignid=23713866882")]
        subject, body, alerts = build_report(1, dsa, dsa, [], [], now)

        assert any("below break-even" in a for a in alerts)

    def test_report_gclid_health_alert(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        # Order referred by Google but no gclid in landing
        order = self._make_order(10.00)
        order["referring_site"] = "https://www.google.com/search"
        subject, body, alerts = build_report(1, [order], [], [], [order], now)

        assert any("auto-tagging" in a for a in alerts)

    def test_report_proposed_actions_present(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        subject, body, alerts = build_report(1, [], [], [], [], now)

        assert "PROPOSED ACTIONS:" in body

    def test_report_alert_emoji_in_subject(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        subject, body, alerts = build_report(1, [], [], [], [], now)

        assert "!!!" in subject  # has alerts

    def test_report_no_alert_emoji_when_above_break_even(self):
        now = datetime(2026, 4, 5, 10, 0, tzinfo=timezone.utc)
        # ROAS = 200/10 = 20x, above break-even
        dsa = [self._make_order(200.00, landing="/?gclid=x&gad_campaignid=23713866882")]
        subject, body, alerts = build_report(1, dsa, dsa, [], [], now)

        assert "!!!" not in subject


class TestLockFile:
    def _today(self) -> datetime:
        return datetime(2026, 4, 8, 8, 0, tzinfo=TZ_LOCAL)

    def test_not_sent_when_no_lock_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.dsa_daily_report._lock_path", lambda: tmp_path / "dsa_report_sent.date")
        assert not _already_sent_today(self._today())

    def test_mark_then_detect_today(self, tmp_path, monkeypatch):
        lock = tmp_path / "dsa_report_sent.date"
        monkeypatch.setattr("scripts.dsa_daily_report._lock_path", lambda: lock)
        _mark_sent_today(self._today())
        assert _already_sent_today(self._today())

    def test_different_day_not_detected(self, tmp_path, monkeypatch):
        lock = tmp_path / "dsa_report_sent.date"
        monkeypatch.setattr("scripts.dsa_daily_report._lock_path", lambda: lock)
        yesterday = datetime(2026, 4, 7, 8, 0, tzinfo=TZ_LOCAL)
        _mark_sent_today(yesterday)
        assert not _already_sent_today(self._today())

    def test_lock_file_contains_date_string(self, tmp_path, monkeypatch):
        lock = tmp_path / "dsa_report_sent.date"
        monkeypatch.setattr("scripts.dsa_daily_report._lock_path", lambda: lock)
        _mark_sent_today(self._today())
        assert lock.read_text().strip() == "2026-04-08"


class TestSendAlert:
    @patch("src.common.mailer.smtplib.SMTP_SSL")
    @patch.dict("os.environ", {"GMAIL_ADDRESS": "test@gmail.com", "GMAIL_APP_PASSWORD": "pass123"})
    def test_send_alert_calls_smtp(self, mock_smtp_cls):
        from src.common.mailer import send_alert

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_alert(subject="Test Subject", body="Test body")

        mock_smtp_cls.assert_called_once_with("smtp.gmail.com", 465)
        mock_server.login.assert_called_once_with("test@gmail.com", "pass123")
