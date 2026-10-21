import json
import os
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "finpilot.db"
ACTIONS_FILE = DATA_DIR / "agent_actions.json"
AUDIT_FILE = DATA_DIR / "audit_log.jsonl"

_actions_lock = threading.Lock()
_audit_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -----------------------------------------------------------------------------
# SQLite Agent Tables (finpilot.db)
# -----------------------------------------------------------------------------

def _get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_agent_db() -> None:
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read INTEGER NOT NULL DEFAULT 0,
                action_id TEXT,
                report_id TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notif_created ON notifications(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notif_read ON notifications(read);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                subject TEXT NOT NULL,
                html TEXT NOT NULL,
                text TEXT NOT NULL,
                attachment_csv TEXT,
                summary_json TEXT,
                batch_id INTEGER,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                sent_to TEXT,
                sent_at TEXT,
                error TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_batch ON reports(batch_id);")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.commit()


# -----------------------------------------------------------------------------
# Notifications CRUD
# -----------------------------------------------------------------------------

def create_notification(
    notif_type: str,
    title: str,
    message: str,
    action_id: Optional[str] = None,
    report_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    init_agent_db()
    if created_at is None:
        created_at = _now_iso()

    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notifications (type, title, message, created_at, read, action_id, report_id)
            VALUES (?, ?, ?, ?, 0, ?, ?);
            """,
            (notif_type, title, message, created_at, action_id, report_id),
        )
        notif_id = cursor.lastrowid
        conn.commit()

    return {
        "id": notif_id,
        "type": notif_type,
        "title": title,
        "message": message,
        "created_at": created_at,
        "read": False,
        "action_id": action_id,
        "report_id": report_id,
    }


def has_notification(notif_type: str, title: str) -> bool:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM notifications WHERE type = ? AND title = ? LIMIT 1;",
            (notif_type, title),
        )
        return cursor.fetchone() is not None


def get_notifications(unread_only: bool = False, limit: int = 200) -> List[Dict[str, Any]]:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        if unread_only:
            cursor.execute(
                "SELECT * FROM notifications WHERE read = 0 ORDER BY id DESC LIMIT ?;",
                (limit,),
            )
        else:
            cursor.execute(
                "SELECT * FROM notifications ORDER BY id DESC LIMIT ?;",
                (limit,),
            )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "type": r["type"],
                "title": r["title"],
                "message": r["message"],
                "created_at": r["created_at"],
                "read": bool(r["read"]),
                "action_id": r["action_id"],
                "report_id": r["report_id"],
            }
            for r in rows
        ]


def get_unread_notification_count() -> int:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notifications WHERE read = 0;")
        return cursor.fetchone()[0]


def mark_notifications_read(ids: Optional[List[int]] = None, all_unread: bool = False) -> int:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        if all_unread:
            cursor.execute("UPDATE notifications SET read = 1 WHERE read = 0;")
            updated = cursor.rowcount
        elif ids:
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(
                f"UPDATE notifications SET read = 1 WHERE id IN ({placeholders});",
                ids,
            )
            updated = cursor.rowcount
        else:
            updated = 0
        conn.commit()
    return updated


# -----------------------------------------------------------------------------
# Reports CRUD
# -----------------------------------------------------------------------------

def save_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    init_agent_db()
    summary_json = json.dumps(report_data.get("summary", {}), ensure_ascii=False)
    created_at = report_data.get("created_at") or _now_iso()

    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (
                id, kind, subject, html, text, attachment_csv, summary_json,
                batch_id, created_at, status, sent_to, sent_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                report_data["id"],
                report_data["kind"],
                report_data["subject"],
                report_data["html"],
                report_data["text"],
                report_data.get("attachment_csv"),
                summary_json,
                report_data.get("batch_id"),
                created_at,
                report_data.get("status", "draft"),
                report_data.get("sent_to"),
                report_data.get("sent_at"),
                report_data.get("error"),
            ),
        )
        conn.commit()
    return report_data


def get_report_by_id(report_id: str) -> Optional[Dict[str, Any]]:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = ?;", (report_id,))
        r = cursor.fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "kind": r["kind"],
            "subject": r["subject"],
            "html": r["html"],
            "text": r["text"],
            "attachment_csv": r["attachment_csv"],
            "summary": json.loads(r["summary_json"]) if r["summary_json"] else {},
            "batch_id": r["batch_id"],
            "created_at": r["created_at"],
            "status": r["status"],
            "sent_to": r["sent_to"],
            "sent_at": r["sent_at"],
            "error": r["error"],
        }


def get_reports_list(kind: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        # Note: Heavy HTML field is omitted from listing per Section 3.7
        if kind:
            cursor.execute(
                """
                SELECT id, kind, subject, text, summary_json, batch_id,
                       created_at, status, sent_to, sent_at, error
                FROM reports WHERE kind = ? ORDER BY created_at DESC LIMIT ?;
                """,
                (kind, limit),
            )
        else:
            cursor.execute(
                """
                SELECT id, kind, subject, text, summary_json, batch_id,
                       created_at, status, sent_to, sent_at, error
                FROM reports ORDER BY created_at DESC LIMIT ?;
                """,
                (limit,),
            )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "kind": r["kind"],
                "subject": r["subject"],
                "text": r["text"],
                "summary": json.loads(r["summary_json"]) if r["summary_json"] else {},
                "batch_id": r["batch_id"],
                "created_at": r["created_at"],
                "status": r["status"],
                "sent_to": r["sent_to"],
                "sent_at": r["sent_at"],
                "error": r["error"],
            }
            for r in rows
        ]


def update_report(report_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    init_agent_db()
    allowed_cols = {"status", "sent_to", "sent_at", "error", "html", "text", "subject"}
    set_clauses = []
    values = []
    for k, v in updates.items():
        if k in allowed_cols:
            set_clauses.append(f"{k} = ?")
            values.append(v)
    if not set_clauses:
        return get_report_by_id(report_id)

    values.append(report_id)
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE reports SET {', '.join(set_clauses)} WHERE id = ?;",
            values,
        )
        conn.commit()
    return get_report_by_id(report_id)


# -----------------------------------------------------------------------------
# Settings CRUD
# -----------------------------------------------------------------------------

def get_settings() -> Dict[str, Any]:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM agent_settings;")
        rows = dict(cursor.fetchall())

    env_owner = os.getenv("OWNER_EMAIL", "").strip()
    stored_owner = rows.get("owner_email")
    if stored_owner is not None:
        owner_email = stored_owner
    else:
        owner_email = env_owner or "sreenikhilchowdary@gmail.com"

    reminder_enabled = rows.get("reminder_enabled", "false").lower() == "true"
    try:
        reminder_hours = int(rows.get("reminder_hours", "4"))
    except ValueError:
        reminder_hours = 4

    email_mode = os.getenv("EMAIL_MODE", "dry_run").strip().lower()
    if email_mode not in ("dry_run", "smtp"):
        email_mode = "dry_run"

    configured = bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))

    return {
        "owner_email": owner_email,
        "reminder_enabled": reminder_enabled,
        "reminder_hours": reminder_hours,
        "email": {
            "mode": email_mode,
            "configured": configured,
        },
    }


def update_settings(
    owner_email: Optional[str] = None,
    reminder_enabled: Optional[bool] = None,
    reminder_hours: Optional[int] = None,
) -> Dict[str, Any]:
    init_agent_db()
    with _get_db() as conn:
        cursor = conn.cursor()
        if owner_email is not None:
            cursor.execute(
                "INSERT INTO agent_settings (key, value) VALUES ('owner_email', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                (owner_email.strip(),),
            )
        if reminder_enabled is not None:
            cursor.execute(
                "INSERT INTO agent_settings (key, value) VALUES ('reminder_enabled', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                ("true" if reminder_enabled else "false",),
            )
        if reminder_hours is not None:
            cursor.execute(
                "INSERT INTO agent_settings (key, value) VALUES ('reminder_hours', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
                (str(max(1, int(reminder_hours))),),
            )
        conn.commit()

    return get_settings()


# -----------------------------------------------------------------------------
# Actions JSON File Storage (Thread-safe with atomic replace)
# -----------------------------------------------------------------------------

def _load_actions_unlocked() -> List[Dict[str, Any]]:
    if not ACTIONS_FILE.exists():
        return []
    try:
        with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_actions_unlocked(actions: List[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=DATA_DIR, prefix="actions_", suffix=".tmp")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(actions, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, ACTIONS_FILE)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def get_actions() -> List[Dict[str, Any]]:
    with _actions_lock:
        return _load_actions_unlocked()


def get_action_by_id(action_id: str) -> Optional[Dict[str, Any]]:
    with _actions_lock:
        actions = _load_actions_unlocked()
        for a in actions:
            if a["id"] == action_id:
                return dict(a)
    return None


def save_action(action: Dict[str, Any]) -> Dict[str, Any]:
    with _actions_lock:
        actions = _load_actions_unlocked()
        # Update existing or append
        updated = False
        for i, a in enumerate(actions):
            if a["id"] == action["id"]:
                actions[i] = action
                updated = True
                break
        if not updated:
            actions.append(action)
        _save_actions_unlocked(actions)
    return action


def update_action(action_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with _actions_lock:
        actions = _load_actions_unlocked()
        target = None
        for a in actions:
            if a["id"] == action_id:
                a.update(updates)
                target = dict(a)
                break
        if target:
            _save_actions_unlocked(actions)
        return target


def has_action_for_type_batch(action_type: str, batch_id: int) -> bool:
    with _actions_lock:
        actions = _load_actions_unlocked()
        for a in actions:
            if a.get("type") == action_type and a.get("batch_id") == batch_id:
                return True
    return False


# -----------------------------------------------------------------------------
# Audit Log JSONL Storage
# -----------------------------------------------------------------------------

def write_audit_entry(
    event: str,
    actor: str,
    details: Optional[Any] = None,
    action_id: Optional[str] = None,
    report_id: Optional[str] = None,
) -> Dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": _now_iso(),
        "actor": actor,
        "event": event,
        "action_id": action_id,
        "report_id": report_id,
        "details": details if details is not None else {},
    }
    with _audit_lock:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def get_audit_log(limit: int = 100, event: Optional[str] = None) -> List[Dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return []

    entries = []
    with _audit_lock:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if event and data.get("event") != event:
                        continue
                    entries.append(data)
                except Exception:
                    continue

    entries.reverse()  # Newest first
    return entries[:limit]
