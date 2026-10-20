import csv
import html
import io
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DASHBOARD_URL_DEFAULT = "http://localhost:3000"


# -----------------------------------------------------------------------------
# Formatting Helpers (Pure Python, No Babel)
# -----------------------------------------------------------------------------

def format_ordinal_date(dt_or_str: Any) -> str:
    """Format date as '18th Oct 2026'."""
    if not dt_or_str:
        return ""
    if isinstance(dt_or_str, str):
        cleaned = dt_or_str.replace("Z", "+00:00")
        try:
            if "T" in cleaned:
                dt = datetime.fromisoformat(cleaned)
            else:
                dt = datetime.strptime(cleaned[:10], "%Y-%m-%d")
        except Exception:
            return dt_or_str
    elif isinstance(dt_or_str, datetime):
        dt = dt_or_str
    else:
        return str(dt_or_str)

    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    month_name = dt.strftime("%b")
    return f"{day}{suffix} {month_name} {dt.year}"


def format_inr(number: float) -> str:
    """Format rupees with Indian digit grouping: e.g. ₹12,38,394.68."""
    val = float(number or 0.0)
    s = f"{abs(val):.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        groups.append(last3)
        formatted = ",".join(groups)
    sign = "-" if val < 0 else ""
    return f"{sign}₹{formatted}.{decimal_part}"


def format_usd(number: float, with_sign: bool = False) -> str:
    """Format dollars with US grouping: e.g. $15,401.63 or +$659.51."""
    val = float(number or 0.0)
    sign = ""
    if val < 0:
        sign = "-"
    elif with_sign and val > 0:
        sign = "+"
    return f"{sign}${abs(val):,.2f}"


def format_pct(number: float, with_sign: bool = True) -> str:
    """Format percentage: e.g. -20.3% or +15.2%."""
    val = float(number or 0.0)
    sign = ""
    if val < 0:
        sign = ""
    elif with_sign and val > 0:
        sign = "+"
    return f"{sign}{val:.1f}%"


def sanitize_header_value(val: str, max_len: int = 200) -> str:
    """Strip CR/LF and cap length to prevent email header injection."""
    s = re.sub(r"[\r\n]+", " ", str(val)).strip()
    return s[:max_len]


def sanitize_csv_cell(val: Any) -> str:
    """Prefix formula characters (=, +, -, @) with a single quote."""
    s = str(val if val is not None else "")
    if s and s[0] in ("=", "+", "-", "@"):
        return "'" + s
    return s


# -----------------------------------------------------------------------------
# Base Email Template Frame (HTML + Text)
# -----------------------------------------------------------------------------

def _render_email_html(
    preheader: str,
    badge_title: str,
    report_title: str,
    meta_line: str,
    content_html: str,
    approval_line: str,
    footer_text: str,
    dashboard_url: str,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(report_title)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F3F5F8; font-family: Arial, Helvetica, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
  <!-- Hidden preheader -->
  <div style="display: none; max-height: 0px; overflow: hidden; font-size: 1px; line-height: 1px; color: #F3F5F8;">
    {html.escape(preheader)}
  </div>

  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #F3F5F8; width: 100%;">
    <tr>
      <td align="center" style="padding: 24px 12px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; width: 100%; background-color: #FFFFFF; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
          
          <!-- Header Band -->
          <tr>
            <td style="background-color: #10141B; padding: 18px 24px; border-bottom: 3px solid #3ECF8E;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td>
                    <span style="font-size: 19px; font-weight: bold; color: #FFFFFF; letter-spacing: -0.5px;">
                      FinPilot <span style="color: #3ECF8E;">AI</span>
                    </span>
                  </td>
                  <td align="right">
                    <span style="font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #8A93A6; background-color: #171C26; padding: 4px 10px; border-radius: 12px; border: 1px solid #2A3242;">
                      {html.escape(badge_title)}
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Report Title & Meta -->
          <tr>
            <td style="padding: 24px 24px 8px 24px; border-bottom: 1px solid #E3E7EE;">
              <h1 style="margin: 0 0 6px 0; font-size: 20px; font-weight: bold; color: #1A1F2B; line-height: 1.3;">
                {html.escape(report_title)}
              </h1>
              <div style="font-size: 12px; color: #5B6475; line-height: 1.4;">
                {html.escape(meta_line)}
              </div>
            </td>
          </tr>

          <!-- Main Content Section -->
          <tr>
            <td style="padding: 20px 24px;">
              {content_html}
            </td>
          </tr>

          <!-- Action Button -->
          <tr>
            <td style="padding: 0 24px 24px 24px;" align="center">
              <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="center" style="border-radius: 6px; background-color: #10141B;">
                    <a href="{html.escape(dashboard_url)}" target="_blank" style="font-size: 13px; font-weight: bold; color: #3ECF8E; text-decoration: none; padding: 12px 24px; display: inline-block; border: 1px solid #2A3242; border-radius: 6px;">
                      Open dashboard &rarr;
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Approval Status Strip -->
          <tr>
            <td style="background-color: #F8FAFC; padding: 12px 24px; border-top: 1px solid #E3E7EE; font-size: 11.5px; color: #5B6475; line-height: 1.4;">
              <strong>Audit:</strong> {html.escape(approval_line)}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #F3F5F8; padding: 16px 24px; font-size: 11px; color: #8A93A6; line-height: 1.5; border-top: 1px solid #E3E7EE;">
              {html.escape(footer_text)}
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# -----------------------------------------------------------------------------
# Template 1: Fraud Alert Report
# -----------------------------------------------------------------------------

def build_fraud_report(
    batch: Dict[str, Any],
    all_customer_batch_counts: Optional[Dict[str, int]] = None,
    dashboard_url: Optional[str] = None,
    report_id: Optional[str] = None,
    approval_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pure function generating subject, html, text, attachment_csv and summary.
    
    Order of transactions matches Fraud tab:
    1. SUSPICIOUS first, then NORMAL
    2. risk_score descending
    3. ties: ai_anomaly_score ascending, amount descending, orig_index ascending
    """
    if dashboard_url is None:
        dashboard_url = os.getenv("DASHBOARD_URL", DASHBOARD_URL_DEFAULT).strip()
    if not report_id:
        report_id = f"RPT-FRD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    filename = batch.get("filename", "transactions.csv")
    raw_date = batch.get("uploaded_at") or datetime.now(timezone.utc).isoformat()
    formatted_date = format_ordinal_date(raw_date)

    txs = batch.get("transactions", [])
    total_tx = len(txs)
    flagged_tx = [t for t in txs if t.get("status") == "SUSPICIOUS"]
    flagged_count = len(flagged_tx)
    normal_count = total_tx - flagged_count

    flag_rate_pct = (flagged_count / total_tx * 100.0) if total_tx > 0 else 0.0
    amount_at_risk = sum(float(t.get("amount", 0.0)) for t in flagged_tx)

    # Risk score statistics
    scores = [float(t.get("risk_score", 0.0)) for t in flagged_tx]
    max_risk = max(scores) if scores else 0.0
    max_risk_count = sum(1 for s in scores if s == 100.0)

    # Unique customers in flagged set
    flagged_cust_ids = [t["customer_id"] for t in flagged_tx if t.get("customer_id")]
    unique_cust_count = len(set(flagged_cust_ids))

    # Reasons counts
    reason_counts: Dict[str, int] = {}
    device_change_count = 0
    for t in flagged_tx:
        for r in t.get("reasons", []):
            reason_counts[r] = reason_counts.get(r, 0) + 1
            if "device" in r.lower():
                device_change_count += 1

    # Sorted reasons descending by frequency
    sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)

    # Repeat offenders analysis
    # Customer is repeat offender if:
    # 1. Flagged >= 2 times in THIS batch, OR
    # 2. Flagged in this batch AND in an earlier upload
    in_batch_counts: Dict[str, int] = {}
    in_batch_amt: Dict[str, float] = {}
    for t in flagged_tx:
        cid = t.get("customer_id")
        if cid:
            in_batch_counts[cid] = in_batch_counts.get(cid, 0) + 1
            in_batch_amt[cid] = in_batch_amt.get(cid, 0.0) + float(t.get("amount", 0.0))

    if all_customer_batch_counts is None:
        try:
            from modules.fraud.storage import get_customer_batch_counts
            all_customer_batch_counts = get_customer_batch_counts()
        except Exception:
            all_customer_batch_counts = {}

    customers_to_watch = []
    for cid, b_cnt in in_batch_counts.items():
        earlier_batches = max(0, all_customer_batch_counts.get(cid, 1) - 1)
        if b_cnt >= 2 or earlier_batches >= 1:
            customers_to_watch.append({
                "customer_id": cid,
                "batch_flags": b_cnt,
                "earlier_flags": earlier_batches,
                "amount_flagged": in_batch_amt[cid],
            })

    # Sort customers to watch by flags in this batch descending, then amount descending
    customers_to_watch.sort(key=lambda x: (x["batch_flags"], x["amount_flagged"]), reverse=True)

    # Top 10 riskiest transactions
    # Note: flagged_tx already has deterministic sorting from batch save
    top_10_tx = flagged_tx[:10]

    # Suggested next steps rules (at most 4 in priority)
    next_steps = []
    if max_risk_count > 0:
        next_steps.append(
            f"{max_risk_count} transaction{'s' if max_risk_count != 1 else ''} scored 100. "
            "Consider holding settlement until they are reviewed."
        )
    if customers_to_watch:
        top_watch_ids = [c["customer_id"] for c in customers_to_watch[:3]]
        next_steps.append(f"Review accounts flagged more than once: {', '.join(top_watch_ids)}.")
    if flagged_count > 0 and (device_change_count >= (flagged_count / 2.0)):
        next_steps.append("Most flagged transactions also involved a device change. Consider step-up verification.")
    if flag_rate_pct >= 10.0:
        next_steps.append(f"A flag rate of {flag_rate_pct:.1f}% is high. Check whether the file comes from a single source.")
    if not next_steps:
        next_steps.append("No urgent action. Review the listed transactions.")
    next_steps = next_steps[:4]

    # Subject line
    tx_word = "transaction" if flagged_count == 1 else "transactions"
    clean_filename = sanitize_header_value(filename, 50)
    subject = f"[FinPilot] {flagged_count} suspicious {tx_word} need review ({clean_filename}, {formatted_date})"

    # Approval line
    if approval_info and approval_info.get("approved_by"):
        appr_dt = format_ordinal_date(approval_info.get("approved_at", raw_date))
        approval_line = f"Approved by {approval_info['approved_by']} on {appr_dt}. Action {approval_info.get('action_id', 'manual')}."
    else:
        approval_line = f"Pending human approval before dispatch. Report ID {report_id}."

    # Preheader
    preheader = f"{flagged_count} of {total_tx} transactions flagged ({flag_rate_pct:.1f}%). Amount at risk: {format_inr(amount_at_risk)}."

    # Build Content HTML
    stat_boxes_html = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
      <tr>
        <td width="32%" style="background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px; vertical-align: top;">
          <div style="font-size: 10px; font-weight: bold; text-transform: uppercase; color: #5B6475; margin-bottom: 4px;">Amount at risk</div>
          <div style="font-size: 16px; font-weight: bold; color: #E5595F;">{format_inr(amount_at_risk)}</div>
          <div style="font-size: 11px; color: #8A93A6; margin-top: 2px;">in {flagged_count} flagged rows</div>
        </td>
        <td width="2%">&nbsp;</td>
        <td width="32%" style="background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px; vertical-align: top;">
          <div style="font-size: 10px; font-weight: bold; text-transform: uppercase; color: #5B6475; margin-bottom: 4px;">Highest risk score</div>
          <div style="font-size: 16px; font-weight: bold; color: #1A1F2B;">{max_risk:.0f} <span style="font-size: 11px; font-weight: normal; color: #5B6475;">({max_risk_count} at 100)</span></div>
          <div style="font-size: 11px; color: #8A93A6; margin-top: 2px;">scale 0 &ndash; 100</div>
        </td>
        <td width="2%">&nbsp;</td>
        <td width="32%" style="background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px; vertical-align: top;">
          <div style="font-size: 10px; font-weight: bold; text-transform: uppercase; color: #5B6475; margin-bottom: 4px;">Customers involved</div>
          <div style="font-size: 16px; font-weight: bold; color: #1A1F2B;">{unique_cust_count}</div>
          <div style="font-size: 11px; color: #8A93A6; margin-top: 2px;">distinct accounts</div>
        </td>
      </tr>
    </table>
    """

    # Reasons table
    reasons_rows_html = "".join([
        f"""<tr style="background-color: {'#FFFFFF' if i % 2 == 0 else '#F8FAFC'};">
          <td style="padding: 8px 10px; font-size: 12px; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{html.escape(r)}</td>
          <td align="right" style="padding: 8px 10px; font-size: 12px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{cnt}</td>
        </tr>"""
        for i, (r, cnt) in enumerate(sorted_reasons)
    ])
    reasons_table_html = f"""
    <div style="margin-bottom: 22px;">
      <h3 style="font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #1A1F2B; margin: 0 0 8px 0;">Why they were flagged</h3>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #E3E7EE; border-radius: 6px; overflow: hidden; border-collapse: collapse;">
        <thead>
          <tr style="background-color: #10141B; color: #FFFFFF;">
            <th align="left" style="padding: 8px 10px; font-size: 11px; text-transform: uppercase; font-weight: bold;">Detection Reason</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; text-transform: uppercase; font-weight: bold;">Count</th>
          </tr>
        </thead>
        <tbody>
          {reasons_rows_html if reasons_rows_html else '<tr><td colspan="2" style="padding: 10px; font-size: 12px; color: #5B6475;">No specific reasons reported.</td></tr>'}
        </tbody>
      </table>
    </div>
    """

    # Top 10 Table
    top_rows_html = "".join([
        f"""<tr style="background-color: {'#FFFFFF' if i % 2 == 0 else '#F8FAFC'};">
          <td style="padding: 7px 8px; font-size: 11.5px; color: #5B6475; border-bottom: 1px solid #E3E7EE;">#{t.get('rank', i+1)}</td>
          <td style="padding: 7px 8px; font-size: 11.5px; font-family: monospace; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{html.escape(str(t.get('transaction_id') or '—'))}</td>
          <td style="padding: 7px 8px; font-size: 11.5px; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{html.escape(str(t.get('customer_id') or '—'))}</td>
          <td align="right" style="padding: 7px 8px; font-size: 11.5px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{format_inr(t.get('amount', 0))}</td>
          <td align="center" style="padding: 7px 8px; font-size: 11px; font-weight: bold; color: #E5595F; border-bottom: 1px solid #E3E7EE;">{float(t.get('risk_score', 0)):.0f}</td>
          <td style="padding: 7px 8px; font-size: 11px; color: #5B6475; border-bottom: 1px solid #E3E7EE;">{html.escape(t.get('reasons', ['—'])[0] if t.get('reasons') else '—')}</td>
        </tr>"""
        for i, t in enumerate(top_10_tx)
    ])
    top_table_html = f"""
    <div style="margin-bottom: 22px;">
      <h3 style="font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #1A1F2B; margin: 0 0 8px 0;">Top 10 riskiest transactions</h3>
      <div style="overflow-x: auto;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #E3E7EE; border-radius: 6px; overflow: hidden; border-collapse: collapse; min-width: 520px;">
          <thead>
            <tr style="background-color: #10141B; color: #FFFFFF;">
              <th align="left" style="padding: 8px 8px; font-size: 11px; font-weight: bold;">Rank</th>
              <th align="left" style="padding: 8px 8px; font-size: 11px; font-weight: bold;">Tx ID</th>
              <th align="left" style="padding: 8px 8px; font-size: 11px; font-weight: bold;">Customer</th>
              <th align="right" style="padding: 8px 8px; font-size: 11px; font-weight: bold;">Amount</th>
              <th align="center" style="padding: 8px 8px; font-size: 11px; font-weight: bold;">Risk</th>
              <th align="left" style="padding: 8px 8px; font-size: 11px; font-weight: bold;">Main Reason</th>
            </tr>
          </thead>
          <tbody>
            {top_rows_html if top_rows_html else '<tr><td colspan="6" style="padding: 10px; font-size: 12px; color: #5B6475;">No flagged transactions.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
    """

    # Customers to watch
    watch_rows_html = "".join([
        f"""<tr style="background-color: {'#FFFFFF' if i % 2 == 0 else '#F8FAFC'};">
          <td style="padding: 7px 10px; font-size: 12px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{html.escape(c['customer_id'])}</td>
          <td align="center" style="padding: 7px 10px; font-size: 12px; color: #E5595F; font-weight: bold; border-bottom: 1px solid #E3E7EE;">{c['batch_flags']}</td>
          <td align="center" style="padding: 7px 10px; font-size: 12px; color: #5B6475; border-bottom: 1px solid #E3E7EE;">{c['earlier_flags']}</td>
          <td align="right" style="padding: 7px 10px; font-size: 12px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{format_inr(c['amount_flagged'])}</td>
        </tr>"""
        for i, c in enumerate(customers_to_watch)
    ])
    watch_html = f"""
    <div style="margin-bottom: 22px;">
      <h3 style="font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #1A1F2B; margin: 0 0 8px 0;">Customers to watch ({len(customers_to_watch)})</h3>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #E3E7EE; border-radius: 6px; overflow: hidden; border-collapse: collapse;">
        <thead>
          <tr style="background-color: #10141B; color: #FFFFFF;">
            <th align="left" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Customer</th>
            <th align="center" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Flags this upload</th>
            <th align="center" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Earlier uploads</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Flagged Amount</th>
          </tr>
        </thead>
        <tbody>
          {watch_rows_html if watch_rows_html else '<tr><td colspan="4" style="padding: 10px; font-size: 12px; color: #5B6475;">No repeat offenders identified in this upload.</td></tr>'}
        </tbody>
      </table>
    </div>
    """

    # Next steps
    next_steps_html = "".join([
        f"""<li style="margin-bottom: 6px; font-size: 12.5px; color: #1A1F2B; line-height: 1.45;">{html.escape(step)}</li>"""
        for step in next_steps
    ])
    steps_box_html = f"""
    <div style="background-color: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; padding: 14px 16px; margin-bottom: 24px;">
      <div style="font-size: 11.5px; font-weight: bold; text-transform: uppercase; color: #B45309; margin-bottom: 8px;">Suggested next steps</div>
      <ol style="margin: 0; padding-left: 20px;">
        {next_steps_html}
      </ol>
    </div>
    """

    content_html = f"""
    <div style="margin-bottom: 16px;">
      <h2 style="font-size: 16px; font-weight: bold; color: #1A1F2B; margin: 0 0 4px 0;">
        {flagged_count} of {total_tx} transactions flagged ({flag_rate_pct:.1f}%)
      </h2>
      <div style="font-size: 12.5px; color: #5B6475;">Source upload file: <strong>{html.escape(filename)}</strong></div>
    </div>
    {stat_boxes_html}
    {steps_box_html}
    {reasons_table_html}
    {top_table_html}
    {watch_html}
    """

    footer_text = (
        "Risk score = rule points (amount vs the customer's average, frequency, time gap, location change, device change) "
        "plus a flag from an Isolation Forest model. It supports a human decision and is not proof of fraud. "
        "Generated automatically by FinPilot's rule-based agent; no external AI service was used."
    )

    meta_line = f"Report generated {formatted_date} · ID: {report_id}"

    report_html = _render_email_html(
        preheader=preheader,
        badge_title="Fraud Alert Report",
        report_title=f"Fraud Alert: {flagged_count} Suspicious Transactions",
        meta_line=meta_line,
        content_html=content_html,
        approval_line=approval_line,
        footer_text=footer_text,
        dashboard_url=dashboard_url,
    )

    # Plain text version
    text_lines = [
        f"FinPilot AI - Fraud Alert Report",
        f"================================",
        f"Subject: {subject}",
        f"Generated: {formatted_date} | Report ID: {report_id}",
        "",
        f"SUMMARY:",
        f"- {flagged_count} of {total_tx} transactions flagged ({flag_rate_pct:.1f}%)",
        f"- Amount at risk: {format_inr(amount_at_risk)}",
        f"- Highest risk score: {max_risk:.0f} ({max_risk_count} at 100)",
        f"- Distinct customers involved: {unique_cust_count}",
        f"- File: {filename}",
        "",
        "SUGGESTED NEXT STEPS:",
    ]
    for i, s in enumerate(next_steps, start=1):
        text_lines.append(f"{i}. {s}")

    text_lines.extend(["", "WHY THEY WERE FLAGGED:"])
    for r, cnt in sorted_reasons:
        text_lines.append(f"- {r}: {cnt}")

    text_lines.extend(["", "TOP RISKIEST TRANSACTIONS:"])
    for t in top_10_tx:
        text_lines.append(
            f"#{t.get('rank')} {t.get('transaction_id')} | Customer: {t.get('customer_id')} | "
            f"Amount: {format_inr(t.get('amount', 0))} | Risk: {t.get('risk_score')} | Reason: {t.get('reasons', [''])[0]}"
        )

    if customers_to_watch:
        text_lines.extend(["", "CUSTOMERS TO WATCH:"])
        for c in customers_to_watch:
            text_lines.append(
                f"- {c['customer_id']}: {c['batch_flags']} flags this upload, "
                f"{c['earlier_flags']} earlier, {format_inr(c['amount_flagged'])} total"
            )

    text_lines.extend([
        "",
        f"Open dashboard: {dashboard_url}",
        "",
        f"Audit: {approval_line}",
        "",
        footer_text,
    ])
    report_text = "\n".join(text_lines)

    # CSV Attachment (Formula injection guarded)
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow([
        "rank", "transaction_id", "customer_id", "amount",
        "risk_score", "status", "ai_flagged", "ai_anomaly_score", "reasons"
    ])
    for t in flagged_tx:
        writer.writerow([
            sanitize_csv_cell(t.get("rank")),
            sanitize_csv_cell(t.get("transaction_id")),
            sanitize_csv_cell(t.get("customer_id")),
            sanitize_csv_cell(t.get("amount")),
            sanitize_csv_cell(t.get("risk_score")),
            sanitize_csv_cell(t.get("status")),
            sanitize_csv_cell(t.get("ai_flagged")),
            sanitize_csv_cell(t.get("ai_anomaly_score")),
            sanitize_csv_cell("; ".join(t.get("reasons", []))),
        ])
    attachment_csv = csv_buf.getvalue()

    summary_dict = {
        "batch_id": batch.get("id"),
        "filename": filename,
        "total_scanned": total_tx,
        "total_transactions": total_tx,
        "flagged_count": flagged_count,
        "suspicious_count": flagged_count,
        "flag_rate_pct": flag_rate_pct,
        "amount_at_risk": amount_at_risk,
        "max_risk": max_risk,
        "highest_risk_score": int(max_risk),
        "max_risk_count": max_risk_count,
        "transactions_at_100": max_risk_count,
        "unique_customers": unique_cust_count,
        "customers_involved": unique_cust_count,
        "repeat_customers_count": len(customers_to_watch),
        "customers_to_watch": customers_to_watch,
        "reason_counts": reason_counts,
        "top_10": top_10_tx,
        "next_steps": next_steps,
    }

    return {
        "id": report_id,
        "kind": "fraud",
        "batch_id": batch.get("id"),
        "subject": subject,
        "html": report_html,
        "text": report_text,
        "attachment_csv": attachment_csv,
        "summary": summary_dict,
        "created_at": raw_date,
        "status": "draft",
    }


# -----------------------------------------------------------------------------
# Template 2: Sales Outlook Report
# -----------------------------------------------------------------------------

def build_sales_report(
    forecasting_module: Any = None,
    dashboard_url: Optional[str] = None,
    report_id: Optional[str] = None,
    approval_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Pure function generating subject, html, text and summary for sales outlook."""
    if forecasting_module is None:
        import modules.forecasting as forecasting_module
    if dashboard_url is None:
        dashboard_url = os.getenv("DASHBOARD_URL", DASHBOARD_URL_DEFAULT).strip()
    if not report_id:
        report_id = f"RPT-SLS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    summary_info = forecasting_module.get_summary()
    next_week_items = forecasting_module.get_all_next_week()
    groups_dict = forecasting_module.get_groups()

    week_ending = summary_info.get("week_ending", "2019-01-06")
    formatted_week_ending = format_ordinal_date(week_ending)
    subject = f"[FinPilot] Sales outlook: forecast for week ending {formatted_week_ending}"

    # Map subcategory to group
    sub_to_group = {}
    for g, subs in groups_dict.items():
        for s in subs:
            sub_to_group[s] = g

    last_week_total = 0.0
    prev_week_total = 0.0
    group_stats: Dict[str, Dict[str, float]] = {g: {"last": 0.0, "prev": 0.0, "forecast": 0.0} for g in groups_dict}
    sub_diffs = []
    wide_range_items = []

    for it in next_week_items:
        sub = it["sub_category"]
        g = sub_to_group.get(sub, "Other")
        chart = forecasting_module.get_chart_data(sub)
        hist = chart["history"]
        w_last = float(hist[-1]["sales"])
        w_prev = float(hist[-2]["sales"])
        w_fc = float(it["predicted_sales"])

        last_week_total += w_last
        prev_week_total += w_prev
        if g in group_stats:
            group_stats[g]["last"] += w_last
            group_stats[g]["prev"] += w_prev
            group_stats[g]["forecast"] += w_fc

        diff = w_fc - w_last
        sub_diffs.append((sub, diff, w_fc, w_last))

        range_width = float(it["upper_estimate"]) - float(it["lower_estimate"])
        rel_width = (range_width / w_fc) if w_fc > 0 else 0.0
        if w_fc > 0 and range_width >= 2 * w_fc:
            wide_range_items.append((sub, rel_width, w_fc, range_width))

    # Overall changes
    last_vs_prev_pct = ((last_week_total - prev_week_total) / prev_week_total * 100.0) if prev_week_total > 0 else 0.0
    fc_next_total = float(summary_info.get("next_week_total", 0.0))
    fc_vs_last_pct = ((fc_next_total - last_week_total) / last_week_total * 100.0) if last_week_total > 0 else 0.0
    fc_4_weeks_total = float(summary_info.get("next_4_weeks_total", 0.0))

    # Sort sub-categories by predicted sales descending for Top 5
    top_5_items = sorted(next_week_items, key=lambda x: float(x["predicted_sales"]), reverse=True)[:5]

    # Biggest falls (3) & biggest rises (3)
    sub_diffs.sort(key=lambda x: x[1])
    biggest_falls = sub_diffs[:3]
    biggest_rises = sorted(sub_diffs[-3:], key=lambda x: x[1], reverse=True)

    # Watch list: 4-week average >= $500 and predicted <= 70% of 4-week average
    watch_list = []
    for it in next_week_items:
        sub = it["sub_category"]
        chart = forecasting_module.get_chart_data(sub)
        hist = chart["history"]
        last_4_actual = [float(h["sales"]) for h in hist[-4:]]
        avg_4 = sum(last_4_actual) / 4.0
        pred = float(it["predicted_sales"])
        pct = (pred / avg_4) if avg_4 > 0 else 1.0
        if avg_4 >= 500.0 and pct <= 0.70:
            watch_list.append({
                "sub_category": sub,
                "four_week_avg": avg_4,
                "predicted": pred,
                "drop_pct": (1.0 - pct) * 100.0,
            })
    watch_list.sort(key=lambda x: x["sub_category"])

    # Wide ranges: 3 widest relative ranges
    wide_range_items.sort(key=lambda x: x[1], reverse=True)
    top_3_wide = wide_range_items[:3]
    wide_count = len(wide_range_items)
    total_sub_count = len(next_week_items)

    # Metrics
    metrics = summary_info.get("metrics", {})
    wape = round(metrics.get("wape_pct", 70.0))
    baseline_wape = round(metrics.get("baseline_wape_pct", 97.0))
    accuracy_line = f"Backtest on the last 12 weeks: WAPE {wape}%, versus {baseline_wape}% for 'next week = last week'."

    # Preheader
    preheader = f"Sales outlook for week ending {formatted_week_ending}. Next week forecast: {format_usd(fc_next_total)} ({format_pct(fc_vs_last_pct)})."

    # Approval line
    if approval_info and approval_info.get("approved_by"):
        appr_dt = format_ordinal_date(approval_info.get("approved_at", datetime.now(timezone.utc).isoformat()))
        approval_line = f"Approved by {approval_info['approved_by']} on {appr_dt}. Action {approval_info.get('action_id', 'manual')}."
    else:
        approval_line = f"Pending human approval before dispatch. Report ID {report_id}."

    # HTML Stat Boxes
    stat_boxes_html = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
      <tr>
        <td width="32%" style="background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px; vertical-align: top;">
          <div style="font-size: 10px; font-weight: bold; text-transform: uppercase; color: #5B6475; margin-bottom: 4px;">Last actual week</div>
          <div style="font-size: 16px; font-weight: bold; color: #1A1F2B;">{format_usd(last_week_total)}</div>
          <div style="font-size: 11px; color: {'#E5595F' if last_vs_prev_pct < 0 else '#1F7A55'}; margin-top: 2px;">
            {format_pct(last_vs_prev_pct)} vs prev week
          </div>
        </td>
        <td width="2%">&nbsp;</td>
        <td width="32%" style="background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px; vertical-align: top;">
          <div style="font-size: 10px; font-weight: bold; text-transform: uppercase; color: #5B6475; margin-bottom: 4px;">Next week forecast</div>
          <div style="font-size: 16px; font-weight: bold; color: #1A1F2B;">{format_usd(fc_next_total)}</div>
          <div style="font-size: 11px; color: {'#E5595F' if fc_vs_last_pct < 0 else '#1F7A55'}; margin-top: 2px;">
            {format_pct(fc_vs_last_pct)} vs last actual
          </div>
        </td>
        <td width="2%">&nbsp;</td>
        <td width="32%" style="background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px; vertical-align: top;">
          <div style="font-size: 10px; font-weight: bold; text-transform: uppercase; color: #5B6475; margin-bottom: 4px;">Next 4 weeks</div>
          <div style="font-size: 16px; font-weight: bold; color: #1F7A55;">{format_usd(fc_4_weeks_total)}</div>
          <div style="font-size: 11px; color: #8A93A6; margin-top: 2px;">cumulative sales</div>
        </td>
      </tr>
    </table>
    """

    # Group table HTML
    group_rows_html = "".join([
        f"""<tr style="background-color: {'#FFFFFF' if i % 2 == 0 else '#F8FAFC'};">
          <td style="padding: 8px 10px; font-size: 12px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{html.escape(g)}</td>
          <td align="right" style="padding: 8px 10px; font-size: 12px; color: #5B6475; border-bottom: 1px solid #E3E7EE;">{format_usd(s['prev'])}</td>
          <td align="right" style="padding: 8px 10px; font-size: 12px; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{format_usd(s['last'])}</td>
          <td align="right" style="padding: 8px 10px; font-size: 12px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{format_usd(s['forecast'])}</td>
          <td align="right" style="padding: 8px 10px; font-size: 12px; font-weight: bold; color: {'#E5595F' if (s['forecast'] - s['last']) < 0 else '#1F7A55'}; border-bottom: 1px solid #E3E7EE;">
            {format_pct(((s['forecast'] - s['last']) / s['last'] * 100) if s['last'] > 0 else 0)}
          </td>
        </tr>"""
        for i, (g, s) in enumerate(group_stats.items())
    ])
    group_table_html = f"""
    <div style="margin-bottom: 22px;">
      <h3 style="font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #1A1F2B; margin: 0 0 8px 0;">Performance by group</h3>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #E3E7EE; border-radius: 6px; overflow: hidden; border-collapse: collapse;">
        <thead>
          <tr style="background-color: #10141B; color: #FFFFFF;">
            <th align="left" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Group</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Prev Week</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Last Actual</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Next Forecast</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Change</th>
          </tr>
        </thead>
        <tbody>
          {group_rows_html}
        </tbody>
      </table>
    </div>
    """

    # Top 5 subcategories
    top_5_rows_html = "".join([
        f"""<tr style="background-color: {'#FFFFFF' if i % 2 == 0 else '#F8FAFC'};">
          <td style="padding: 7px 10px; font-size: 12px; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">#{i+1} <strong>{html.escape(it['sub_category'])}</strong> ({html.escape(it['category'])})</td>
          <td align="right" style="padding: 7px 10px; font-size: 12px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{format_usd(it['predicted_sales'])}</td>
          <td align="right" style="padding: 7px 10px; font-size: 11.5px; color: #5B6475; border-bottom: 1px solid #E3E7EE;">{format_usd(it['lower_estimate'])} &ndash; {format_usd(it['upper_estimate'])}</td>
        </tr>"""
        for i, it in enumerate(top_5_items)
    ])
    top_5_html = f"""
    <div style="margin-bottom: 22px;">
      <h3 style="font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #1A1F2B; margin: 0 0 8px 0;">Top 5 sub-categories by forecast</h3>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #E3E7EE; border-radius: 6px; overflow: hidden; border-collapse: collapse;">
        <thead>
          <tr style="background-color: #10141B; color: #FFFFFF;">
            <th align="left" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Sub-category</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Predicted Sales</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Range (80% Interval)</th>
          </tr>
        </thead>
        <tbody>
          {top_5_rows_html}
        </tbody>
      </table>
    </div>
    """

    # Falls & Rises side-by-side
    falls_html = "".join([
        f"""<div style="font-size: 12px; padding: 4px 0; border-bottom: 1px dashed #E3E7EE; display: flex; justify-content: space-between;">
          <span style="font-weight: 500;">{html.escape(s)}</span>
          <span style="font-weight: bold; color: #E5595F;">{format_usd(d)}</span>
        </div>"""
        for s, d, fc, l in biggest_falls
    ])
    rises_html = "".join([
        f"""<div style="font-size: 12px; padding: 4px 0; border-bottom: 1px dashed #E3E7EE; display: flex; justify-content: space-between;">
          <span style="font-weight: 500;">{html.escape(s)}</span>
          <span style="font-weight: bold; color: #1F7A55;">{format_usd(d, with_sign=True)}</span>
        </div>"""
        for s, d, fc, l in biggest_rises
    ])
    movers_html = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 22px;">
      <tr>
        <td width="48%" style="vertical-align: top; background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px;">
          <div style="font-size: 11.5px; font-weight: bold; text-transform: uppercase; color: #E5595F; margin-bottom: 8px;">Biggest expected falls</div>
          {falls_html}
        </td>
        <td width="4%">&nbsp;</td>
        <td width="48%" style="vertical-align: top; background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 12px;">
          <div style="font-size: 11.5px; font-weight: bold; text-transform: uppercase; color: #1F7A55; margin-bottom: 8px;">Biggest expected rises</div>
          {rises_html}
        </td>
      </tr>
    </table>
    """

    # Watch list items
    watch_rows_html = "".join([
        f"""<tr style="background-color: {'#FFFFFF' if i % 2 == 0 else '#F8FAFC'};">
          <td style="padding: 7px 10px; font-size: 12px; font-weight: bold; color: #1A1F2B; border-bottom: 1px solid #E3E7EE;">{html.escape(w['sub_category'])}</td>
          <td align="right" style="padding: 7px 10px; font-size: 12px; color: #5B6475; border-bottom: 1px solid #E3E7EE;">{format_usd(w['four_week_avg'])}</td>
          <td align="right" style="padding: 7px 10px; font-size: 12px; color: #1A1F2B; font-weight: bold; border-bottom: 1px solid #E3E7EE;">{format_usd(w['predicted'])}</td>
          <td align="right" style="padding: 7px 10px; font-size: 12px; font-weight: bold; color: #E5595F; border-bottom: 1px solid #E3E7EE;">-{w['drop_pct']:.1f}%</td>
        </tr>"""
        for i, w in enumerate(watch_list)
    ])
    watch_html = f"""
    <div style="margin-bottom: 22px;">
      <h3 style="font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #1A1F2B; margin: 0 0 8px 0;">Watch list: Significant Drop Alert ({len(watch_list)})</h3>
      <div style="font-size: 11.5px; color: #5B6475; margin-bottom: 8px;">Sub-categories with predicted sales &le; 70% of their 4-week baseline average (&ge; $500).</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid #E3E7EE; border-radius: 6px; overflow: hidden; border-collapse: collapse;">
        <thead>
          <tr style="background-color: #10141B; color: #FFFFFF;">
            <th align="left" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Sub-category</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">4-Wk Avg</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Next Forecast</th>
            <th align="right" style="padding: 8px 10px; font-size: 11px; font-weight: bold;">Drop vs Avg</th>
          </tr>
        </thead>
        <tbody>
          {watch_rows_html if watch_rows_html else '<tr><td colspan="4" style="padding: 10px; font-size: 12px; color: #5B6475;">No items meet drop criteria.</td></tr>'}
        </tbody>
      </table>
    </div>
    """

    # Range note and accuracy note
    widest_names = ", ".join(w[0] for w in top_3_wide)
    range_and_accuracy_html = f"""
    <div style="background-color: #F8FAFC; border: 1px solid #E3E7EE; border-radius: 6px; padding: 14px 16px; margin-bottom: 24px;">
      <div style="font-size: 12px; color: #1A1F2B; margin-bottom: 8px;">
        <strong>Forecast range note:</strong> {wide_count} of {total_sub_count} sub-categories have a range at least twice the predicted value; treat single numbers with caution (widest ranges: {html.escape(widest_names)}).
      </div>
      <div style="font-size: 11.5px; color: #5B6475;">
        <strong>Accuracy:</strong> {html.escape(accuracy_line)}
      </div>
    </div>
    """

    content_html = f"""
    {stat_boxes_html}
    {group_table_html}
    {top_5_html}
    {movers_html}
    {watch_html}
    {range_and_accuracy_html}
    """

    footer_text = "Demo dataset: Superstore sales 2015-2018 (US$). Generated automatically by FinPilot's rule-based agent; no external AI service was used."
    meta_line = f"Forecast for week ending {formatted_week_ending} · ID: {report_id}"

    report_html = _render_email_html(
        preheader=preheader,
        badge_title="Sales Outlook Report",
        report_title=f"Sales Outlook: Week Ending {formatted_week_ending}",
        meta_line=meta_line,
        content_html=content_html,
        approval_line=approval_line,
        footer_text=footer_text,
        dashboard_url=dashboard_url,
    )

    # Plain text version
    text_lines = [
        f"FinPilot AI - Sales Outlook Report",
        f"==================================",
        f"Subject: {subject}",
        f"Forecast for week ending: {formatted_week_ending} | Report ID: {report_id}",
        "",
        "SUMMARY:",
        f"- Last actual week: {format_usd(last_week_total)} ({format_pct(last_vs_prev_pct)} vs prev week)",
        f"- Next week forecast: {format_usd(fc_next_total)} ({format_pct(fc_vs_last_pct)} vs last actual)",
        f"- Next 4 weeks forecast: {format_usd(fc_4_weeks_total)}",
        "",
        "PERFORMANCE BY GROUP:",
    ]
    for g, s in group_stats.items():
        chg = ((s['forecast'] - s['last']) / s['last'] * 100) if s['last'] > 0 else 0
        text_lines.append(f"- {g}: Last={format_usd(s['last'])}, Forecast={format_usd(s['forecast'])}, Change={format_pct(chg)}")

    text_lines.extend(["", "TOP 5 SUB-CATEGORIES:"])
    for i, it in enumerate(top_5_items, start=1):
        text_lines.append(f"{i}. {it['sub_category']}: {format_usd(it['predicted_sales'])} (range {format_usd(it['lower_estimate'])} - {format_usd(it['upper_estimate'])})")

    text_lines.extend(["", "BIGGEST FALLS:"])
    for s, d, fc, l in biggest_falls:
        text_lines.append(f"- {s}: {format_usd(d)}")

    text_lines.extend(["", "BIGGEST RISES:"])
    for s, d, fc, l in biggest_rises:
        text_lines.append(f"- {s}: {format_usd(d, with_sign=True)}")

    text_lines.extend(["", "WATCH LIST (SIGNIFICANT DROP):"])
    for w in watch_list:
        text_lines.append(f"- {w['sub_category']}: 4w_avg={format_usd(w['four_week_avg'])}, pred={format_usd(w['predicted'])} (-{w['drop_pct']:.1f}%)")

    text_lines.extend([
        "",
        f"Forecast range note: {wide_count} of {total_sub_count} sub-categories have a range at least twice the predicted value (widest: {widest_names}).",
        accuracy_line,
        "",
        f"Open dashboard: {dashboard_url}",
        "",
        f"Audit: {approval_line}",
        "",
        footer_text,
    ])
    report_text = "\n".join(text_lines)

    summary_dict = {
        "week_ending": week_ending,
        "next_week_ending": week_ending,
        "last_week_total": last_week_total,
        "prev_week_total": prev_week_total,
        "last_week_change_pct": last_vs_prev_pct,
        "next_week_total": fc_next_total,
        "next_week_change_pct": fc_vs_last_pct,
        "next_4_weeks_total": fc_4_weeks_total,
        "groups": [
            {
                "category": g,
                "last_week": stats["last"],
                "prev_week": stats["prev"],
                "forecast": stats["forecast"],
                "change": stats["forecast"] - stats["last"],
            }
            for g, stats in sorted(group_stats.items())
        ],
        "top_5": [
            {"sub_category": it["sub_category"], "forecast": float(it["predicted_sales"])}
            for it in top_5_items
        ],
        "biggest_falls": [
            {"sub_category": item[0], "change": item[1], "forecast": item[2], "last": item[3]}
            for item in biggest_falls
        ],
        "biggest_rises": [
            {"sub_category": item[0], "change": item[1], "forecast": item[2], "last": item[3]}
            for item in biggest_rises
        ],
        "watch_list": watch_list,
        "watch_list_count": len(watch_list),
        "wide_range_count": wide_count,
        "total_subcategories": total_sub_count,
    }

    return {
        "id": report_id,
        "kind": "sales",
        "batch_id": None,
        "subject": subject,
        "html": report_html,
        "text": report_text,
        "attachment_csv": None,
        "summary": summary_dict,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "draft",
    }


# -----------------------------------------------------------------------------
# Reminder Email Builder
# -----------------------------------------------------------------------------

def build_reminder_email(
    action: Dict[str, Any],
    owner_email: str,
    dashboard_url: Optional[str] = None,
) -> Dict[str, str]:
    """Short reminder email without transaction details."""
    if dashboard_url is None:
        dashboard_url = os.getenv("DASHBOARD_URL", DASHBOARD_URL_DEFAULT).strip()

    subject = "[FinPilot] Reminder: a fraud alert is still waiting for your approval"
    action_title = action.get("title", "Pending Alert")
    action_id = action.get("id", "")

    html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; background-color: #F3F5F8; padding: 24px;">
  <div style="max-width: 500px; margin: 0 auto; background: #FFFFFF; padding: 24px; border-radius: 8px; border: 1px solid #E3E7EE;">
    <h3 style="margin: 0 0 12px 0; color: #1A1F2B;">Action Required: Fraud Alert Approval</h3>
    <p style="font-size: 13.5px; color: #5B6475; line-height: 1.5; margin: 0 0 16px 0;">
      A fraud alert report is waiting for your review and approval.
    </p>
    <div style="background: #F8FAFC; border: 1px solid #E3E7EE; padding: 12px; border-radius: 6px; font-size: 13px; color: #1A1F2B; margin-bottom: 20px;">
      <strong>{html.escape(action_title)}</strong> (ID: {html.escape(action_id)})
    </div>
    <a href="{html.escape(dashboard_url)}" style="background: #10141B; color: #3ECF8E; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-size: 13px; font-weight: bold; display: inline-block;">
      Review in Dashboard &rarr;
    </a>
  </div>
</body>
</html>"""

    text_content = (
        f"FinPilot AI - Reminder\n"
        f"====================\n\n"
        f"A fraud alert is still waiting for your approval: {action_title} (ID: {action_id})\n\n"
        f"Please review and approve in your dashboard: {dashboard_url}\n"
    )

    return {
        "subject": subject,
        "html": html_content,
        "text": text_content,
    }
