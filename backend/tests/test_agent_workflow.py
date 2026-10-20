"""Comprehensive verification test suite for FinPilot AI Agent Layer.
Verifies all 14 backend checkpoints from Section 6 of ANTIGRAVITY_BRIEF_AGENT.md.
Uses standard library unittest / assertions (no pytest required).
"""

import os
import re
import shutil
import smtplib
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient

from app.main import app
from modules import agent
from modules.agent import emailer, reports, store
from modules.fraud import storage as fraud_storage

client = TestClient(app)

TEST_CSV_PATH = BASE_DIR / "data" / "fraud_test" / "Fraud _Detection_Dataset.csv"


def approx(val, target, tol=0.01):
    return abs(val - target) <= tol * max(abs(target), 1.0) or abs(val - target) < 0.1


def get_token(role="owner"):
    email = "owner@aaravretail.com" if role == "owner" else "analyst@aaravretail.com"
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "demo1234"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_01_pip_check_and_dependencies():
    print("Testing 01: pip check and dependencies...")
    res = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    assert res.returncode == 0, f"pip check failed: {res.stdout}\n{res.stderr}"

    req_file = BASE_DIR / "requirements.txt"
    assert req_file.exists()
    content = req_file.read_text(encoding="utf-8")
    assert "langgraph==1.2.16" in content

    forbidden = ["langchain", "openai", "anthropic", "cohere", "llama", "transformers", "ollama", "groq"]
    for pkg in forbidden:
        assert pkg not in content.lower(), f"Forbidden package '{pkg}' found in requirements.txt!"
    print("  -> PASS")


def test_02_fraud_upload_and_agent_trigger():
    print("Testing 02: Fraud upload and agent trigger...")
    token = get_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    client.delete("/api/v1/fraud/history", headers={"Authorization": f"Bearer {get_token('owner')}"})

    assert TEST_CSV_PATH.exists(), f"Missing test CSV at {TEST_CSV_PATH}"
    with open(TEST_CSV_PATH, "rb") as f:
        resp = client.post(
            "/api/v1/fraud/upload",
            files={"file": ("Fraud__Detection_Dataset.csv", f, "text/csv")},
            headers=headers,
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    batch = data["batch"]
    assert batch["total"] == 304

    notifs_resp = client.get("/api/v1/agent/notifications", headers=headers)
    assert notifs_resp.status_code == 200
    notifs = notifs_resp.json()["notifications"]
    types = [n["type"] for n in notifs]
    assert "fraud_alert" in types
    assert "forecast_drop" in types

    unread_resp = client.get("/api/v1/agent/notifications/unread-count", headers=headers)
    assert unread_resp.status_code == 200
    assert unread_resp.json()["count"] >= 2

    actions_resp = client.get("/api/v1/agent/actions", headers=headers)
    assert actions_resp.status_code == 200
    actions = actions_resp.json()["actions"]
    fraud_actions = [a for a in actions if a.get("type") == "fraud_report" and a.get("batch_id") == batch["id"]]
    assert len(fraud_actions) == 1
    action = fraud_actions[0]
    assert action["status"] == "pending_approval"

    rep_resp = client.get(f"/api/v1/agent/reports/{action['report_id']}", headers=headers)
    assert rep_resp.status_code == 200
    rep = rep_resp.json()["report"]
    assert rep["status"] == "draft"

    # Test error resilience
    with patch("modules.agent.on_fraud_upload", side_effect=RuntimeError("Simulated agent failure")):
        with open(TEST_CSV_PATH, "rb") as f:
            resp_err = client.post(
                "/api/v1/fraud/upload",
                files={"file": ("resilience_test.csv", f, "text/csv")},
                headers=headers,
            )
        assert resp_err.status_code == 200, "Upload failed when agent threw error!"
    print("  -> PASS")


def test_03_fraud_report_checkpoints():
    print("Testing 03: Fraud report checkpoints...")
    token = get_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    rep_list = client.get("/api/v1/agent/reports?kind=fraud", headers=headers).json()["reports"]
    assert len(rep_list) > 0
    full_rep = client.get(f"/api/v1/agent/reports/{rep_list[0]['id']}", headers=headers).json()["report"]

    summary = full_rep["summary"]
    html = full_rep["html"]
    subject = full_rep["subject"]

    assert subject.startswith("[FinPilot] 42 suspicious transactions need review"), f"Got subject: {subject}"
    assert "42 of 304 transactions flagged (13.8%)" in html
    assert "₹12,38,394.68" in html
    assert approx(summary["amount_at_risk"], 1238394.68)
    assert summary["highest_risk_score"] == 100
    assert summary["transactions_at_100"] == 39
    assert summary["customers_involved"] == 24

    expected_reasons = {
        "Transactions made within a very short time gap": 42,
        "Location changed": 42,
        "Flagged as anomaly by the AI model": 42,
        "Amount is much higher than the customer's average": 41,
        "High transaction frequency": 41,
        "Device changed": 36,
    }
    for reason, count in expected_reasons.items():
        assert summary["reason_counts"].get(reason) == count, f"Reason '{reason}' mismatch: {summary['reason_counts']}"

    assert len(summary["customers_to_watch"]) == 12
    watch_cids = {c["customer_id"] for c in summary["customers_to_watch"]}
    for expected_cid in ["C019", "C004", "C001", "C025", "C029"]:
        assert expected_cid in watch_cids

    top10 = summary["top_10"]
    assert len(top10) == 10
    assert top10[0]["transaction_id"] == "TX0275"
    assert top10[0]["customer_id"] == "C029"
    assert approx(top10[0]["amount"], 65970.02)
    assert top10[0]["risk_score"] == 100
    assert top10[1]["transaction_id"] == "TX0290"
    assert top10[2]["transaction_id"] == "TX0284"

    next_steps = summary["next_steps"]
    assert any("39 transactions scored 100" in s for s in next_steps)
    assert any("Review accounts flagged more than once" in s for s in next_steps)
    print("  -> PASS")


def test_04_second_upload_repeat_offender():
    print("Testing 04: Second upload repeat offender...")
    token = get_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    with open(TEST_CSV_PATH, "rb") as f:
        resp = client.post(
            "/api/v1/fraud/upload",
            files={"file": ("second_batch.csv", f, "text/csv")},
            headers=headers,
        )
    assert resp.status_code == 200

    actions = client.get("/api/v1/agent/actions", headers=headers).json()["actions"]
    fraud_actions = [a for a in actions if a.get("type") == "fraud_report"]
    assert len(fraud_actions) >= 2

    notifs = client.get("/api/v1/agent/notifications", headers=headers).json()["notifications"]
    repeat_notifs = [n for n in notifs if n["type"] == "repeat_offender"]
    assert len(repeat_notifs) >= 1
    r_notif = repeat_notifs[0]
    assert "24" in r_notif["message"]

    rep_id = fraud_actions[len(fraud_actions) - 1]["report_id"]
    rep2 = client.get(f"/api/v1/agent/reports/{rep_id}", headers=headers).json()["report"]
    assert len(rep2["summary"]["customers_to_watch"]) == 24
    print("  -> PASS")


def test_05_csv_edge_cases():
    print("Testing 05: CSV edge cases (no ID columns, 0 suspicious rows)...")
    token = get_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    no_id_csv = (
        "amount,transaction_frequency,average_amount,time_interval_minutes,location_change,device_change\n"
        "999999,10,100,1,1,1\n"
    )
    resp1 = client.post(
        "/api/v1/fraud/upload",
        files={"file": ("no_ids.csv", no_id_csv.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert resp1.status_code == 200

    clean_csv = (
        "amount,transaction_frequency,average_amount,time_interval_minutes,location_change,device_change\n"
        "10,1,10,1000,0,0\n"
    )
    resp2 = client.post(
        "/api/v1/fraud/upload",
        files={"file": ("clean.csv", clean_csv.encode("utf-8"), "text/csv")},
        headers=headers,
    )
    assert resp2.status_code == 200

    notifs = client.get("/api/v1/agent/notifications", headers=headers).json()["notifications"]
    clean_notifs = [n for n in notifs if n["type"] == "info" and "clean.csv" in n["title"]]
    assert len(clean_notifs) >= 1
    print("  -> PASS")


def test_06_approve_flow_dry_run():
    print("Testing 06: Approve flow in dry-run mode...")
    owner_token = get_token("owner")
    analyst_token = get_token("analyst")

    client.put(
        "/api/v1/agent/settings",
        json={"owner_email": "testowner@finpilot.ai"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    actions = client.get("/api/v1/agent/actions", headers={"Authorization": f"Bearer {analyst_token}"}).json()["actions"]
    pending = [a for a in actions if a["status"] == "pending_approval" and a.get("report_id")]
    assert len(pending) > 0
    target_action = pending[0]

    approve_resp = client.post(
        "/api/v1/agent/actions/approve",
        json={"action_id": target_action["id"]},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert approve_resp.status_code == 200, approve_resp.text
    app_data = approve_resp.json()
    assert app_data["status"] == "executed"
    assert app_data["email"]["mode"] == "dry_run"
    assert app_data["email"]["sent_to"] == "testowner@finpilot.ai"

    outbox_dir = BASE_DIR / "data" / "outbox"
    assert outbox_dir.exists()
    eml_files = list(outbox_dir.glob("*.eml"))
    assert len(eml_files) > 0

    rep = client.get(f"/api/v1/agent/reports/{target_action['report_id']}", headers={"Authorization": f"Bearer {analyst_token}"}).json()["report"]
    assert rep["status"] == "dry_run_saved"

    audit = client.get("/api/v1/agent/audit?event=agent_action_approved_and_executed", headers={"Authorization": f"Bearer {analyst_token}"}).json()["entries"]
    assert any(e["action_id"] == target_action["id"] for e in audit)

    again_resp = client.post(
        "/api/v1/agent/actions/approve",
        json={"action_id": target_action["id"]},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert again_resp.status_code == 400
    print("  -> PASS")


def test_07_approve_empty_owner_email_and_reject():
    print("Testing 07: Approve with empty owner email & reject...")
    owner_token = get_token("owner")
    analyst_token = get_token("analyst")

    client.put(
        "/api/v1/agent/settings",
        json={"owner_email": ""},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    actions = client.get("/api/v1/agent/actions", headers={"Authorization": f"Bearer {analyst_token}"}).json()["actions"]
    pending = [a for a in actions if a["status"] == "pending_approval" and a.get("report_id")]
    assert len(pending) > 0
    target_action = pending[0]

    resp = client.post(
        "/api/v1/agent/actions/approve",
        json={"action_id": target_action["id"]},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 400
    assert "Set the owner's email in Settings first." in resp.json()["detail"]

    reject_resp = client.post(
        "/api/v1/agent/actions/reject",
        json={"action_id": target_action["id"], "reason": "Testing manual rejection"},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert reject_resp.status_code == 200
    rej_data = reject_resp.json()
    assert rej_data["status"] == "rejected"

    audit = client.get("/api/v1/agent/audit?event=action_rejected", headers={"Authorization": f"Bearer {analyst_token}"}).json()["entries"]
    assert any(e["action_id"] == target_action["id"] for e in audit)
    print("  -> PASS")


def test_08_smtp_behavior_with_mocks():
    print("Testing 08: SMTP behavior with mocks...")
    owner_token = get_token("owner")
    analyst_token = get_token("analyst")

    client.put(
        "/api/v1/agent/settings",
        json={"owner_email": "owner@aaravretail.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    gen_resp = client.post(
        "/api/v1/agent/reports/generate",
        json={"kind": "sales"},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    action_id = gen_resp.json()["action"]["id"]

    with patch.dict(os.environ, {"EMAIL_MODE": "smtp", "SMTP_HOST": "smtp.gmail.com", "SMTP_USER": "test@gmail.com", "SMTP_PASSWORD": "pwd"}):
        with patch("smtplib.SMTP") as mock_smtp:
            instance = mock_smtp.return_value.__enter__.return_value
            instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")

            resp_auth = client.post(
                "/api/v1/agent/actions/approve",
                json={"action_id": action_id},
                headers={"Authorization": f"Bearer {analyst_token}"},
            )
            assert resp_auth.status_code == 502
            assert "The mail server rejected the login" in resp_auth.json()["detail"]

            act = store.get_action_by_id(action_id)
            assert act["status"] == "failed"

            instance.login.side_effect = None
            instance.send_message.side_effect = smtplib.SMTPConnectError(421, b"Cannot connect")
            resp_conn = client.post(
                "/api/v1/agent/actions/approve",
                json={"action_id": action_id},
                headers={"Authorization": f"Bearer {analyst_token}"},
            )
            assert resp_conn.status_code == 502
            assert "Could not reach the mail server" in resp_conn.json()["detail"]
            assert store.get_action_by_id(action_id)["status"] == "failed"

            instance.send_message.side_effect = None
            resp_retry = client.post(
                "/api/v1/agent/actions/approve",
                json={"action_id": action_id},
                headers={"Authorization": f"Bearer {analyst_token}"},
            )
            assert resp_retry.status_code == 200
            assert store.get_action_by_id(action_id)["status"] == "executed"
    print("  -> PASS")


def test_09_security_guards():
    print("Testing 09: Security guards (HTML XSS, Header injection, CSV injection)...")
    assert reports.sanitize_csv_cell("=1+1") == "'=1+1"
    assert reports.sanitize_csv_cell("+cmd") == "'+cmd"
    assert reports.sanitize_csv_cell("@SUM(A1)") == "'@SUM(A1)"
    assert reports.sanitize_csv_cell("Normal text") == "Normal text"

    assert reports.sanitize_header_value("Subject\r\nBcc: evil@hacker.com") == "Subject Bcc: evil@hacker.com"
    long_hdr = "A" * 500
    assert len(reports.sanitize_header_value(long_hdr)) == 200

    malicious_batch = {
        "id": 999,
        "filename": "<script>alert('xss')</script>\r\nname.csv",
        "total_transactions": 1,
        "transactions": [
            {
                "transaction_id": "<img src=x onerror=alert(1)>",
                "customer_id": "<script>evil()</script>",
                "amount": 100.0,
                "risk_score": 90,
                "status": "SUSPICIOUS",
                "is_anomaly": True,
                "reasons": ["<script>bad()</script>"],
            }
        ],
    }
    rep = reports.build_fraud_report(malicious_batch)
    assert "<script>" not in rep["html"]
    assert "&lt;script&gt;" in rep["html"]
    assert "\r" not in rep["subject"]
    assert "\n" not in rep["subject"]
    print("  -> PASS")


def test_10_permissions_and_settings():
    print("Testing 10: Permissions and settings...")
    resp_no_auth = client.get("/api/v1/agent/settings")
    assert resp_no_auth.status_code == 401

    analyst_token = get_token("analyst")
    resp_analyst_put = client.put(
        "/api/v1/agent/settings",
        json={"owner_email": "analyst_trying@finpilot.ai"},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp_analyst_put.status_code == 403

    owner_token = get_token("owner")
    resp_owner_put = client.put(
        "/api/v1/agent/settings",
        json={"owner_email": "owner_valid@finpilot.ai", "reminder_enabled": True, "reminder_hours": 6},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_owner_put.status_code == 200
    assert resp_owner_put.json()["owner_email"] == "owner_valid@finpilot.ai"
    assert resp_owner_put.json()["reminder_hours"] == 6

    resp_invalid_email = client.put(
        "/api/v1/agent/settings",
        json={"owner_email": "not-an-email"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_invalid_email.status_code == 400

    # Rate limiting on test email
    resp_test_1 = client.post("/api/v1/agent/settings/test-email", headers={"Authorization": f"Bearer {owner_token}"})
    assert resp_test_1.status_code in (200, 429)
    if resp_test_1.status_code == 200:
        resp_test_2 = client.post("/api/v1/agent/settings/test-email", headers={"Authorization": f"Bearer {owner_token}"})
        assert resp_test_2.status_code == 429
    print("  -> PASS")


def test_11_sales_report_checkpoints():
    print("Testing 11: Sales report checkpoints...")
    rep = reports.build_sales_report()
    summary = rep["summary"]
    html = rep["html"]
    subject = rep["subject"]

    assert subject == "[FinPilot] Sales outlook: forecast for week ending 6th Jan 2019"

    assert approx(summary["last_week_total"], 15401.63)
    assert approx(summary["prev_week_total"], 19328.14)
    assert approx(summary["last_week_change_pct"], -20.3, tol=0.05)
    assert approx(summary["next_week_total"], 12903.14)
    assert approx(summary["next_week_change_pct"], -16.2, tol=0.05)
    assert approx(summary["next_4_weeks_total"], 40840.46)

    groups = {g["category"]: g for g in summary["groups"]}
    assert approx(groups["Furniture"]["last_week"], 5431.05)
    assert approx(groups["Furniture"]["prev_week"], 6509.81)
    assert approx(groups["Furniture"]["forecast"], 4383.99)

    assert approx(groups["Office Supplies"]["last_week"], 5636.91)
    assert approx(groups["Office Supplies"]["prev_week"], 10317.32)
    assert approx(groups["Office Supplies"]["forecast"], 4225.05)

    assert approx(groups["Technology"]["last_week"], 4333.67)
    assert approx(groups["Technology"]["prev_week"], 2501.01)
    assert approx(groups["Technology"]["forecast"], 4294.10)

    top5_subs = [x["sub_category"] for x in summary["top_5"]]
    assert top5_subs == ["Chairs", "Copiers", "Phones", "Storage", "Accessories"]
    assert approx(summary["top_5"][0]["forecast"], 1749.51)
    assert approx(summary["top_5"][1]["forecast"], 1316.96)
    assert approx(summary["top_5"][2]["forecast"], 1249.15)
    assert approx(summary["top_5"][3]["forecast"], 1093.68)
    assert approx(summary["top_5"][4]["forecast"], 1068.68)

    fall_subs = [x["sub_category"] for x in summary["biggest_falls"]]
    assert fall_subs == ["Chairs", "Storage", "Copiers"]
    assert approx(summary["biggest_falls"][0]["change"], -2517.17)
    assert approx(summary["biggest_falls"][1]["change"], -2200.37)
    assert approx(summary["biggest_falls"][2]["change"], -1562.99)

    rise_subs = [x["sub_category"] for x in summary["biggest_rises"]]
    assert rise_subs == ["Accessories", "Tables", "Appliances"]
    assert approx(summary["biggest_rises"][0]["change"], 877.95)
    assert approx(summary["biggest_rises"][1]["change"], 659.51)
    assert approx(summary["biggest_rises"][2]["change"], 602.91)

    watch_items = [x["sub_category"] for x in summary["watch_list"]]
    assert watch_items == ["Appliances", "Chairs", "Paper", "Storage", "Tables"]

    assert summary["wide_range_count"] == 12
    assert summary["total_subcategories"] == 17
    assert "12 of 17 sub-categories have a range at least twice" in html

    assert "combined total range" not in html.lower()
    assert "total range" not in html.lower()
    print("  -> PASS")


def test_12_forecast_drop_idempotency():
    print("Testing 12: Forecast drop idempotency...")
    token = get_token("analyst")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/v1/agent/run-checks", headers=headers)
    assert resp.status_code == 200

    notifs = client.get("/api/v1/agent/notifications", headers=headers).json()["notifications"]
    drop_notifs = [n for n in notifs if n["type"] == "forecast_drop"]
    assert len(drop_notifs) == 1, f"Expected exactly 1 forecast_drop notification, got {len(drop_notifs)}"
    print("  -> PASS")


def test_13_overdue_handling():
    print("Testing 13: Overdue action handling & reminders...")
    analyst_token = get_token("analyst")
    owner_token = get_token("owner")

    five_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    test_action = {
        "id": "od_test",
        "title": "Overdue Test Action",
        "body": "Testing overdue waiting badge and reminder",
        "status": "pending_approval",
        "created_at": five_hours_ago,
    }
    store.save_action(test_action)

    client.put(
        "/api/v1/agent/settings",
        json={"reminder_enabled": False},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    actions = client.get("/api/v1/agent/actions", headers={"Authorization": f"Bearer {analyst_token}"}).json()["actions"]
    found = [a for a in actions if a["id"] == "od_test"]
    assert len(found) == 1
    assert found[0]["waiting_hours"] >= 5
    assert found[0]["is_overdue"] is True

    client.get("/api/v1/agent/notifications", headers={"Authorization": f"Bearer {analyst_token}"})
    notifs = client.get("/api/v1/agent/notifications", headers={"Authorization": f"Bearer {analyst_token}"}).json()["notifications"]
    reminders = [n for n in notifs if n["type"] == "reminder" and n.get("action_id") == "od_test"]
    assert len(reminders) == 1

    client.put(
        "/api/v1/agent/settings",
        json={"reminder_enabled": True, "owner_email": "owner@aaravretail.com"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    store.update_action("od_test", {"status": "rejected"})
    print("  -> PASS")


def test_14_contract_compatibility_and_history_clear():
    print("Testing 14: Contract compatibility & history clear...")
    analyst_token = get_token("analyst")
    headers = {"Authorization": f"Bearer {analyst_token}"}

    actions = client.get("/api/v1/agent/actions", headers=headers).json()["actions"]
    for a in actions:
        assert "id" in a
        assert "title" in a
        assert "body" in a
        assert "status" in a

    from modules.fraud import get_flagged_transactions
    flagged = get_flagged_transactions()
    assert "transactions" in flagged
    assert "total_scanned" in flagged

    resp = client.get("/api/v1/fraud", headers=headers)
    assert resp.status_code == 200

    owner_token = get_token("owner")
    del_resp = client.delete("/api/v1/fraud/history", headers={"Authorization": f"Bearer {owner_token}"})
    assert del_resp.status_code == 200

    reports_after = client.get("/api/v1/agent/reports", headers=headers).json()["reports"]
    assert len(reports_after) > 0
    first_rep = client.get(f"/api/v1/agent/reports/{reports_after[0]['id']}", headers=headers).json()["report"]
    assert "html" in first_rep
    assert len(first_rep["html"]) > 100
    print("  -> PASS")


if __name__ == "__main__":
    tests = [
        test_01_pip_check_and_dependencies,
        test_02_fraud_upload_and_agent_trigger,
        test_03_fraud_report_checkpoints,
        test_04_second_upload_repeat_offender,
        test_05_csv_edge_cases,
        test_06_approve_flow_dry_run,
        test_07_approve_empty_owner_email_and_reject,
        test_08_smtp_behavior_with_mocks,
        test_09_security_guards,
        test_10_permissions_and_settings,
        test_11_sales_report_checkpoints,
        test_12_forecast_drop_idempotency,
        test_13_overdue_handling,
        test_14_contract_compatibility_and_history_clear,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAILED: {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n==========================================")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests.")
    print(f"==========================================")
    if failed > 0:
        sys.exit(1)
