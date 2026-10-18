"""ANOMALY / FRAUD DETECTION - FinPilot AI."""

from typing import Any, Dict, List
from modules.fraud.storage import (
    clear_fraud_history,
    get_all_flagged_for_contract,
    get_fraud_history,
    save_batch,
)


def get_flagged_transactions() -> dict:
    """Return the scored transactions from SQLite storage.

    Returns:
        {
          "total_scanned": int,
          "transactions": [
            {
              "id": str,
              "amount": int | float,
              "customer": str,
              "risk_score": float,
              "status": str,
            }, ...
          ],
        }
    """
    return get_all_flagged_for_contract()


def score_transactions_lazy(data: Any) -> list:
    """Lazily import pandas and fraud_detector to score transactions.

    Raises RuntimeError with friendly message if packages are not installed.
    """
    try:
        import pandas  # noqa: F401
        from modules.fraud.fraud_detector import score_transactions
    except ImportError as e:
        raise RuntimeError(
            "Fraud model packages are not installed. Run pip install -r backend/requirements.txt."
        ) from e

    return score_transactions(data)
