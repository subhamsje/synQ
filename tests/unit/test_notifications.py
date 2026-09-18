import pytest
from backend.persistence.db import db
from backend.persistence.seed_data import seed_operational_memory
from backend.notifications.reporter import OperationsReporter


@pytest.fixture(scope="module", autouse=True)
def ensure_db_seeded():
    seed_operational_memory(db)


def test_daily_operations_report_format():
    reporter = OperationsReporter()
    report = reporter.generate_daily_operations_report("19 September 2026")

    assert "FLTX DAILY OPERATIONS REPORT" in report
    assert "Warehouse 01 — Austin Hub" in report
    assert "19 September 2026" in report

    # Required sections
    assert "SYSTEM HEALTH" in report
    assert "Fleet availability" in report
    assert "System uptime" in report
    assert "Safety events             0" in report

    assert "FLEET PERFORMANCE" in report
    assert "Total robots              12" in report
    assert "Missions completed" in report
    assert "Total distance" in report

    assert "AUTONOMY EVENTS" in report
    assert "Obstacle avoidance" in report
    assert "CBS conflicts resolved" in report

    assert "ATTENTION REQUIRED" in report
    assert "AMR-07" in report
    assert "Battery health declining" in report

    assert "FLTX RECOMMENDATION" in report
    assert "Schedule AMR-07 for battery inspection" in report


def test_whatsapp_tiered_alerts():
    reporter = OperationsReporter()

    # Daily summary
    daily_msg = reporter.generate_whatsapp_message(severity="DAILY_SUMMARY")
    assert daily_msg["channel"] == "WHATSAPP"
    assert "*synQ — Daily Operations*" in daily_msg["formatted_message"]
    assert "Fleet: 12/12 online" in daily_msg["formatted_message"]

    # Critical alert
    crit_msg = reporter.generate_whatsapp_message(
        severity="CRITICAL",
        robot_id="AMR-04",
        reason="Localization failure",
        mission_id="TASK-9281"
    )
    assert "*[FLTX CRITICAL]*" in crit_msg["formatted_message"]
    assert "AMR-04 stopped unexpectedly" in crit_msg["formatted_message"]
    assert "TASK-9281" in crit_msg["formatted_message"]

    # Warning alert
    warn_msg = reporter.generate_whatsapp_message(severity="WARNING", robot_id="AMR-07")
    assert "*[FLTX WARNING]*" in warn_msg["formatted_message"]
    assert "AMR-07 battery health declining" in warn_msg["formatted_message"]


def test_email_digest_structure():
    reporter = OperationsReporter()
    email_data = reporter.generate_email_digest()
    assert email_data["channel"] == "EMAIL"
    assert "Daily Operations Brief" in email_data["subject"]
    assert "FLTX — Daily Operations Brief" in email_data["html"]
