import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "finpilot.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fraud_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                uploaded_by TEXT NOT NULL,
                total INTEGER NOT NULL,
                suspicious INTEGER NOT NULL,
                normal INTEGER NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fraud_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL REFERENCES fraud_batches(id) ON DELETE CASCADE,
                rank INTEGER NOT NULL,
                transaction_id TEXT,
                customer_id TEXT,
                amount REAL NOT NULL,
                risk_score REAL NOT NULL,
                status TEXT NOT NULL,
                ai_flagged INTEGER NOT NULL,
                ai_anomaly_score REAL NOT NULL,
                reasons TEXT NOT NULL,
                details TEXT NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fraud_tx_batch ON fraud_transactions(batch_id);")
        conn.commit()


def save_batch(
    filename: str,
    uploaded_by: str,
    sorted_transactions: List[Dict[str, Any]],
    uploaded_at: Optional[str] = None,
) -> Dict[str, Any]:
    init_db()
    if uploaded_at is None:
        uploaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    total = len(sorted_transactions)
    suspicious = sum(1 for t in sorted_transactions if t["status"] == "SUSPICIOUS")
    normal = total - suspicious

    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO fraud_batches (filename, uploaded_at, uploaded_by, total, suspicious, normal)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (filename, uploaded_at, uploaded_by, total, suspicious, normal),
        )
        batch_id = cursor.lastrowid

        rows = [
            (
                batch_id,
                t["rank"],
                t["transaction_id"],
                t["customer_id"],
                float(t["amount"]),
                float(t["risk_score"]),
                t["status"],
                1 if t["ai_flagged"] else 0,
                float(t["ai_anomaly_score"]),
                json.dumps(t.get("reasons", []), ensure_ascii=False),
                json.dumps(t.get("details", {}), ensure_ascii=False),
            )
            for t in sorted_transactions
        ]

        cursor.executemany(
            """
            INSERT INTO fraud_transactions (
                batch_id, rank, transaction_id, customer_id, amount,
                risk_score, status, ai_flagged, ai_anomaly_score, reasons, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows,
        )
        conn.commit()

    return {
        "id": batch_id,
        "filename": filename,
        "uploaded_at": uploaded_at,
        "uploaded_by": uploaded_by,
        "total": total,
        "suspicious": suspicious,
        "normal": normal,
        "transactions": sorted_transactions,
    }


def get_fraud_history() -> Dict[str, Any]:
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fraud_batches ORDER BY id DESC;")
        batch_rows = cursor.fetchall()

        batches: List[Dict[str, Any]] = []
        for b in batch_rows:
            batch_id = b["id"]
            cursor.execute(
                """
                SELECT rank, transaction_id, customer_id, amount, risk_score,
                       status, ai_flagged, ai_anomaly_score, reasons, details
                FROM fraud_transactions
                WHERE batch_id = ?
                ORDER BY rank ASC;
                """,
                (batch_id,),
            )
            tx_rows = cursor.fetchall()
            tx_list = [
                {
                    "rank": r["rank"],
                    "transaction_id": r["transaction_id"],
                    "customer_id": r["customer_id"],
                    "amount": r["amount"],
                    "risk_score": r["risk_score"],
                    "status": r["status"],
                    "ai_flagged": bool(r["ai_flagged"]),
                    "ai_anomaly_score": r["ai_anomaly_score"],
                    "reasons": json.loads(r["reasons"]) if r["reasons"] else [],
                    "details": json.loads(r["details"]) if r["details"] else {},
                }
                for r in tx_rows
            ]

            batches.append({
                "id": b["id"],
                "filename": b["filename"],
                "uploaded_at": b["uploaded_at"],
                "uploaded_by": b["uploaded_by"],
                "total": b["total"],
                "suspicious": b["suspicious"],
                "normal": b["normal"],
                "transactions": tx_list,
            })

    total_batches = len(batches)
    total_tx = sum(b["total"] for b in batches)
    total_suspicious = sum(b["suspicious"] for b in batches)

    return {
        "totals": {
            "batches": total_batches,
            "transactions": total_tx,
            "suspicious": total_suspicious,
        },
        "batches": batches,
    }


def clear_fraud_history() -> Dict[str, int]:
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fraud_batches;")
        n_batches = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM fraud_transactions;")
        n_transactions = cursor.fetchone()[0]

        cursor.execute("DELETE FROM fraud_transactions;")
        cursor.execute("DELETE FROM fraud_batches;")
        conn.commit()

    return {
        "deleted_batches": n_batches,
        "deleted_transactions": n_transactions,
    }


def get_all_flagged_for_contract() -> Dict[str, Any]:
    """Returns shape expected by get_flagged_transactions() and GET /api/v1/fraud.
    
    count: number of SUSPICIOUS transactions across all uploads
    total_scanned: total transactions across all uploads
    transactions: suspicious transactions converted to legacy shape
    """
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fraud_transactions;")
        total_scanned = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT transaction_id, amount, customer_id, risk_score
            FROM fraud_transactions
            WHERE status = 'SUSPICIOUS'
            ORDER BY id ASC;
            """
        )
        rows = cursor.fetchall()

        txns = [
            {
                "id": r["transaction_id"] or f"TXN-{idx + 1}",
                "amount": r["amount"],
                "customer": r["customer_id"] or "Unknown",
                "risk_score": round(r["risk_score"] / 100.0, 2),
                "status": "pending",
            }
            for idx, r in enumerate(rows)
        ]

    return {
        "total_scanned": total_scanned,
        "transactions": txns,
    }


def get_batch_by_id(batch_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fraud_batches WHERE id = ?;", (batch_id,))
        b = cursor.fetchone()
        if not b:
            return None

        cursor.execute(
            """
            SELECT rank, transaction_id, customer_id, amount, risk_score,
                   status, ai_flagged, ai_anomaly_score, reasons, details
            FROM fraud_transactions
            WHERE batch_id = ?
            ORDER BY rank ASC;
            """,
            (batch_id,),
        )
        tx_rows = cursor.fetchall()
        tx_list = [
            {
                "rank": r["rank"],
                "transaction_id": r["transaction_id"],
                "customer_id": r["customer_id"],
                "amount": r["amount"],
                "risk_score": r["risk_score"],
                "status": r["status"],
                "ai_flagged": bool(r["ai_flagged"]),
                "ai_anomaly_score": r["ai_anomaly_score"],
                "reasons": json.loads(r["reasons"]) if r["reasons"] else [],
                "details": json.loads(r["details"]) if r["details"] else {},
            }
            for r in tx_rows
        ]

        return {
            "id": b["id"],
            "filename": b["filename"],
            "uploaded_at": b["uploaded_at"],
            "uploaded_by": b["uploaded_by"],
            "total": b["total"],
            "suspicious": b["suspicious"],
            "normal": b["normal"],
            "transactions": tx_list,
        }


def get_latest_batch() -> Optional[Dict[str, Any]]:
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM fraud_batches ORDER BY id DESC LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            return None
        return get_batch_by_id(row["id"])


def get_customer_batch_counts() -> Dict[str, int]:
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT customer_id, COUNT(DISTINCT batch_id) as batch_count
            FROM fraud_transactions
            WHERE status = 'SUSPICIOUS' AND customer_id IS NOT NULL AND customer_id != ''
            GROUP BY customer_id;
            """
        )
        rows = cursor.fetchall()
        return {r["customer_id"]: r["batch_count"] for r in rows}


def get_all_batches_summary() -> List[Dict[str, Any]]:
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, uploaded_at, total, suspicious, normal FROM fraud_batches ORDER BY id DESC;")
        return [dict(r) for r in cursor.fetchall()]

