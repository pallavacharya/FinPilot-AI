"""ANOMALY / FRAUD DETECTION  -  owner: Kritagy Kaushik

Replace the body of get_flagged_transactions() with your Isolation Forest +
XGBoost output. Keep the function name and return keys EXACTLY as below.
The agent module (Akshi) will also import this function, so keep it stable.
"""

# --- sample data (delete once the real model is connected) ---
_SAMPLE = [
    {"id": "TXN-88213", "amount": 42500, "customer": "R. Bansal", "risk_score": 0.94, "status": "pending"},
    {"id": "TXN-88240", "amount": 118200, "customer": "K. Iyer", "risk_score": 0.89, "status": "pending"},
    {"id": "TXN-88190", "amount": 9800, "customer": "S. Fernandes", "risk_score": 0.61, "status": "reviewed"},
    {"id": "TXN-88177", "amount": 15300, "customer": "A. Verma", "risk_score": 0.58, "status": "reviewed"},
    {"id": "TXN-88155", "amount": 3200, "customer": "M. Gupta", "risk_score": 0.22, "status": "cleared"},
    {"id": "TXN-88130", "amount": 2750, "customer": "T. Rao", "risk_score": 0.14, "status": "cleared"},
]


def get_flagged_transactions() -> dict:
    """Return the scored transactions.

    Returns:
        {
          "total_scanned": int,           # how many transactions were scored in total
          "transactions": [
            {
              "id": str,                  # unique transaction id
              "amount": int | float,      # in rupees
              "customer": str,
              "risk_score": float,        # 0.0 - 1.0  (>=0.8 shows red, >=0.4 amber, else green)
              "status": str,              # "pending" | "reviewed" | "cleared"
            }, ...
          ],
        }
    """
    return {"total_scanned": 12847, "transactions": [dict(t) for t in _SAMPLE]}
