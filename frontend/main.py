from __future__ import annotations

import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

from claim_engine import (
    STATUS_COLORS,
    STATUSES,
    api_claims,
    api_enabled,
    api_update_claim_status,
    api_upload_claim,
    extract_claim,
    load_claims,
    save_claims,
    update_claim,
)
from app.extractor import extract_text

st.set_page_config(page_title="ClaimPilot | Revenue Operations", page_icon="CP", layout="wide", initial_sidebar_state="expanded")

_widget_key_counts: dict[str, int] = {}


def widget_key(name: str) -> str:
    """Return a stable key and avoid collisions if a view is rendered twice."""
    count = _widget_key_counts.get(name, 0)
    _widget_key_counts[name] = count + 1
    suffix = "" if count == 0 else f"_{count}"
    return f"{name}{suffix}"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#17211f; --muted:#68736f; --line:#dce5e0; --mint:#dff3e9; --teal:#087f73; --orange:#e8793b; --paper:#f6f8f5; }
html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); }
[data-testid="stAppViewContainer"] { background:var(--paper); }
[data-testid="stSidebar"] { background:#173b36; border-right:0; }
[data-testid="stSidebar"] * { color:#eff8f2; }
[data-testid="stSidebar"] .stButton button { background:transparent; border:1px solid rgba(255,255,255,.18); color:#eff8f2; }
h1,h2,h3 { font-family:'Space Grotesk', sans-serif; letter-spacing:0; }
h1 { font-size:2.35rem; margin-bottom:.15rem; } h2 { font-size:1.45rem; }
.block-container { max-width:1500px; padding:2.4rem 3.4rem 4rem; }
.hero { display:flex; justify-content:space-between; align-items:flex-end; border-bottom:1px solid var(--line); padding-bottom:1.4rem; margin-bottom:1.3rem; }
.eyebrow { color:var(--teal); font-size:.72rem; text-transform:uppercase; letter-spacing:.14em; font-weight:700; }
.subtitle { color:var(--muted); margin-top:.2rem; }
.kpi { background:white; border:1px solid var(--line); border-radius:8px; padding:1.05rem 1.1rem; min-height:108px; }
.kpi-label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; }
.kpi-value { font-family:'Space Grotesk'; font-size:2rem; font-weight:700; margin-top:.45rem; }
.kpi-note { color:var(--teal); font-size:.76rem; margin-top:.25rem; }
.section { margin:1.6rem 0 .8rem; }
.panel { background:white; border:1px solid var(--line); border-radius:8px; padding:1.2rem; }
.status { display:inline-block; border-radius:20px; padding:.23rem .58rem; font-size:.72rem; font-weight:700; }
.risk-high { color:#a33124; background:#fde7e4; } .risk-medium { color:#a35a10; background:#fff0dc; } .risk-low { color:#16734f; background:#e3f5e8; }
.queue-card { border:1px solid var(--line); border-radius:8px; padding:1rem; background:#fff; margin-bottom:.6rem; }
.claim-id { font-family:'Space Grotesk'; font-weight:700; font-size:1.02rem; }
.small { color:var(--muted); font-size:.82rem; }
div[data-testid="stMetric"] { background:white; border:1px solid var(--line); padding:1rem; border-radius:8px; }
button[kind="primary"] { background:#087f73; border-color:#087f73; }
[data-testid="stFileUploader"] { background:#f0f8f3; border:1px dashed #8abca9; border-radius:8px; padding:.35rem; }
</style>
""", unsafe_allow_html=True)


def money(value: float) -> str:
    return f"${value:,.0f}"


def badge(label: str, css: str = "") -> str:
    return f'<span class="status {css}">{label}</span>'


def render_sidebar(claims: list[dict[str, Any]]) -> None:
    with st.sidebar:
        st.markdown("<div style='font-family:Space Grotesk;font-size:1.45rem;font-weight:700'>ClaimPilot</div><div style='opacity:.7;font-size:.8rem;margin-top:.2rem'>Revenue operations command center</div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("**Workspace**")
        st.caption("Northstar Billing Group")
        st.caption("Last synced just now")
        st.divider()
        st.markdown("**Quick actions**")
        st.caption("Use Reports to download operational exports.")
        st.divider()
        st.markdown("**Control room**")
        st.caption(f"{len(claims)} claims in register")
        st.caption(f"{sum(1 for c in claims if c['risk_band'] == 'High')} high-risk items")
        st.caption("Synthetic data mode")


def render_kpis(claims: list[dict[str, Any]]) -> None:
    total = len(claims)
    billed = sum(float(c.get("amount", 0)) for c in claims)
    high = sum(1 for c in claims if c.get("risk_band") == "High")
    ready = sum(1 for c in claims if c.get("status") == "Ready to submit")
    paid = sum(1 for c in claims if c.get("status") == "Paid")
    cols = st.columns(5)
    items = [("Claims in queue", total, "12% vs last week"), ("Billed value", money(billed), "Across active register"), ("High-risk claims", high, "Needs intervention"), ("Ready to submit", ready, "Awaiting batch"), ("Clean claim rate", f"{paid / total * 100:.0f}%" if total else "0%", "Paid / total")]
    for col, (label, value, note) in zip(cols, items):
        with col:
            st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)


def render_overview(claims: list[dict[str, Any]]) -> None:
    render_kpis(claims)
    st.markdown('<div class="section"><div class="eyebrow">Operations pulse</div><h2>What needs attention today</h2></div>', unsafe_allow_html=True)
    left, right = st.columns([1.55, 1])
    with left:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.8rem">Claim flow</div>', unsafe_allow_html=True)
        counts = {status: sum(1 for c in claims if c.get("status") == status) for status in STATUSES}
        for status, count in counts.items():
            pct = int(count / max(len(claims), 1) * 100)
            color = STATUS_COLORS[status]
            st.markdown(f'<div style="display:flex;justify-content:space-between;margin:.65rem 0 .25rem;font-size:.82rem"><span>{status}</span><strong>{count}</strong></div><div style="height:8px;background:#edf1ee;border-radius:8px"><div style="width:{pct}%;height:8px;background:{color};border-radius:8px"></div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.8rem">Denial risk mix</div>', unsafe_allow_html=True)
        for band, css in [("High", "risk-high"), ("Medium", "risk-medium"), ("Low", "risk-low")]:
            count = sum(1 for c in claims if c.get("risk_band") == band)
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:.7rem 0;border-bottom:1px solid #edf1ee"><span>{badge(band, css)}</span><strong>{count} claims</strong></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section"><div class="eyebrow">Priority queue</div><h2>Claims with the most exposure</h2></div>', unsafe_allow_html=True)
    for claim in sorted(claims, key=lambda item: item.get("risk_score", 0), reverse=True)[:5]:
        issues = claim.get("validation") or []
        issue = issues[0].get("message", "No open issues") if issues else "No open issues"
        st.markdown(f'<div class="queue-card"><div style="display:flex;justify-content:space-between"><span class="claim-id">{claim["id"]} · {claim["patient"]}</span><span>{badge(claim["risk_band"], "risk-" + claim["risk_band"].lower())}</span></div><div class="small" style="margin-top:.35rem">{claim["payer"]} · {claim["procedure"]} · {money(float(claim["amount"]))} · {claim["status"]}</div><div style="margin-top:.6rem;font-size:.82rem">{issue}</div></div>', unsafe_allow_html=True)


def render_extraction_pipeline() -> None:
    st.markdown('<div class="section"><div class="eyebrow">Claim intake</div><h2>Extraction pipeline</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    for number, title in [
        ("01", "OCR / text extraction"),
        ("02", "Structured field mapping"),
        ("03", "Coding and completeness edits"),
        ("04", "Risk and next-best action"),
    ]:
        st.markdown(f'<div style="display:flex;gap:.75rem;padding:.7rem 0;border-bottom:1px solid #edf1ee"><span style="font-family:Space Grotesk;color:#087f73;font-weight:700">{number}</span><span>{title}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def parse_upload(uploaded_file: Any) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    content = uploaded_file.getvalue()
    if suffix == ".pdf": 
        try:
            return extract_text(content)
        except ValueError as error:
            raise RuntimeError(str(error)) from error
    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX support requires python-docx. Install the project requirements and retry.") from exc
        document = Document(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    if suffix in {".txt", ".csv", ".json"}:
        return content.decode("utf-8", errors="ignore")
    return content.decode("utf-8", errors="ignore")


def render_extraction_result(claim: dict[str, Any]) -> None:
    """Show the result of the most recent intake run without hiding the details."""
    st.markdown('<div class="section"><div class="eyebrow">Latest result</div><h2>Extraction and validation complete</h2></div>', unsafe_allow_html=True)
    with st.container(key="extraction_header"):
        header_cols = st.columns(4)
        header_cols[0].metric("Claim ID", claim["id"])
        header_cols[1].metric("Fields mapped", "10 / 10" if claim.get("patient") != "Unknown patient" else "Needs review")
        header_cols[2].metric("Risk score", f"{claim['risk_score']} / 99")
        header_cols[3].metric("Workflow", claim["status"])
    details, review = st.columns([1.15, 1])
    with details:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.7rem">Structured claim data</div>', unsafe_allow_html=True)
        fields = [
            ("Patient", claim.get("patient", "Not provided")),
            ("Patient ID", claim.get("patient_id", "Not provided")),
            ("Date of birth", claim.get("patient_dob", "Not provided")),
            ("Member ID", claim.get("member_id", "Not provided")),
            ("Payer", claim.get("payer", "Not provided")),
            ("Provider", claim.get("provider", "Not provided")),
            ("NPI", claim.get("npi") or "Missing"),
            ("Service date", claim.get("service_date", "Not provided")),
            ("Diagnosis", claim.get("diagnosis", "Not provided")),
            ("Procedure", claim.get("procedure", "Not provided")),
            ("Place of service", claim.get("place_of_service", "Not provided")),
            ("Billed amount", money(float(claim.get("amount", 0)))),
            ("Allowed amount", money(float(claim.get("allowed_amount", 0)))),
            ("Paid amount", money(float(claim.get("paid_amount", 0)))),
        ]
        for label, value in fields:
            st.markdown(f'<div style="display:flex;justify-content:space-between;gap:1rem;padding:.42rem 0;border-bottom:1px solid #edf1ee;font-size:.82rem"><span class="small">{label}</span><strong style="text-align:right">{value}</strong></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with review:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.7rem">Validation and routing</div>', unsafe_allow_html=True)
        st.progress(claim["risk_score"] / 99)
        st.markdown(f'<div style="margin-bottom:.7rem">{badge(claim["risk_band"] + " risk", "risk-" + claim["risk_band"].lower())} &nbsp; {badge(claim["status"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#f4f8f5;border-left:3px solid #087f73;padding:.7rem;font-size:.82rem;margin-bottom:.8rem">{claim.get("ai_explanation", claim["recommendation"])}</div>', unsafe_allow_html=True)
        if claim.get("validation"):
            st.markdown('<div style="font-weight:700">Detected issues</div>', unsafe_allow_html=True)
            for issue in claim["validation"]:
                css = "risk-high" if issue["severity"] == "High" else "risk-medium"
                st.markdown(f'<div style="padding:.55rem 0;border-bottom:1px solid #edf1ee;font-size:.8rem"><div>{badge(issue["severity"], css)} <strong>{issue["code"]}</strong></div><div>{issue["message"]}</div><div class="small">Next: {issue["action"]}</div></div>', unsafe_allow_html=True)
        else:
            st.success("All configured validation checks passed.")
        workflow_history = claim.get("workflow_history") or []
        route_reason = workflow_history[-1].get("reason", "Automatic routing") if workflow_history else "Automatic routing"
        st.caption(f"Explanation source: {claim.get('ai_source', 'rules-engine')} · Route reason: {route_reason}")
        st.markdown('</div>', unsafe_allow_html=True)


def render_upload(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    st.markdown('<div class="section"><div class="eyebrow">Intake</div><h2>Upload and structure a claim</h2><div class="subtitle">Drop a synthetic UB-04, CMS-1500, remittance, or labeled text document. ClaimPilot extracts fields and runs edits immediately.</div></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Claim document", type=["pdf", "txt", "csv", "json", "docx"], label_visibility="collapsed", key=widget_key("claim_document_uploader"))
    if uploaded:
        st.caption(f"{uploaded.name} · {uploaded.size / 1024:.1f} KB")
        with st.status("Processing claim document", expanded=True) as processing:
            try:
                processing.write("Reading uploaded document")
                if api_enabled():
                    claim = api_upload_claim(uploaded.name, uploaded.getvalue())
                else:
                    text = parse_upload(uploaded)
                    if not text.strip():
                        raise RuntimeError("The uploaded document contains no readable text.")
                    processing.write("Mapping document fields into claim structure")
                    claim = extract_claim(text, uploaded.name)
                processing.write("Running completeness, coding, and financial edits")
                processing.write(f"Calculated {claim['risk_band'].lower()} risk score: {claim['risk_score']} / 99")
                processing.write(f"Automatically routed to: {claim['status']}")
            except RuntimeError as error:
                processing.update(label="Claim processing stopped", state="error")
                st.error(str(error))
            else:
                processing.update(label="Claim processed successfully", state="complete")
                token = f"{uploaded.name}:{uploaded.size}"
                if not api_enabled() and st.session_state.get("last_processed_upload") != token:
                    claims.insert(0, claim)
                    save_claims(claims)
                    st.session_state.last_processed_upload = token
                st.session_state.selected_claim = claim["id"]
                st.session_state.last_intake_claim = claim
                st.success(f"{claim['id']} extracted, validated, scored, and routed")
    if st.session_state.get("last_intake_claim"):
        render_extraction_result(st.session_state.last_intake_claim)
    st.markdown('<div class="panel" style="margin-top:1rem"><div style="font-weight:700">Synthetic document format</div><div class="small" style="margin-top:.5rem">Use labels such as Patient, Member ID, Payer, Provider, NPI, Date of Service, Diagnosis, Procedure, Billed Amount, and Place of Service.</div></div>', unsafe_allow_html=True)
    # with right:
    #     render_extraction_pipeline()
    return claims


def render_claims_table(claims: list[dict[str, Any]]) -> None:
    st.markdown('<div class="section"><div class="eyebrow">Work queue</div><h2>Claims register</h2></div>', unsafe_allow_html=True)
    query = st.text_input("Search claims", placeholder="Search by claim ID, patient, payer, or provider", label_visibility="collapsed")
    status_filter = st.multiselect("Filter by status", STATUSES, default=[], label_visibility="collapsed")
    filtered = [c for c in claims if (not query or query.lower() in json.dumps(c).lower()) and (not status_filter or c.get("status") in status_filter)]
    rows = [{"Claim": c["id"], "Patient": c["patient"], "Payer": c["payer"], "Amount": money(float(c["amount"])), "Risk": f"{c['risk_band']} ({c['risk_score']})", "Status": c["status"], "Top edit": (c.get("validation") or [{}])[0].get("message", "Clean")} for c in filtered]
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True, height=310)
    if not filtered:
        st.info("No claims match the current filters.")
    else:
        selected = st.selectbox("Open claim", [c["id"] for c in filtered], key=widget_key("claim_selector"))
        st.session_state.selected_claim = selected


def render_claim_detail(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claim_id = st.session_state.get("selected_claim") or (claims[0]["id"] if claims else None)
    claim = next((c for c in claims if c["id"] == claim_id), None)
    if not claim:
        return claims
    st.markdown('<div class="section"><div class="eyebrow">Claim intelligence</div><h2>Review and route</h2></div>', unsafe_allow_html=True)
    header, action = st.columns([2, 1])
    with header:
        st.markdown(f'<div class="panel"><div class="claim-id">{claim["id"]} · {claim["patient"]}</div><div class="small" style="margin-top:.4rem">{claim["payer"]} · source {claim["source_file"]}</div><div style="margin-top:.8rem">{badge(claim["status"])} &nbsp; {badge(claim["risk_band"] + " risk", "risk-" + claim["risk_band"].lower())}</div></div>', unsafe_allow_html=True)
    with action:
        new_status = st.selectbox("Route claim", STATUSES, index=STATUSES.index(claim["status"]), key=widget_key("route_claim_status"))
        if st.button("Save workflow state", type="primary", width='stretch', key=widget_key("save_workflow_state")):
            if api_enabled():
                updated_claim = api_update_claim_status(claim["id"], new_status)
                claim.clear()
                claim.update(updated_claim)
            else:
                update_claim(claims, claim["id"], status=new_status)
            st.success("Workflow state saved")
            st.rerun()
    detail, issues = st.columns([1.15, 1])
    with detail:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.8rem">Extracted fields</div>', unsafe_allow_html=True)
        fields = [("Patient", claim["patient"]), ("Member ID", claim["member_id"]), ("Provider", claim["provider"]), ("NPI", claim["npi"] or "Missing"), ("Date of service", claim["service_date"]), ("Diagnosis", claim["diagnosis"]), ("Procedure", claim["procedure"]), ("Place of service", claim["place_of_service"]), ("Billed amount", money(float(claim["amount"]))) ]
        for label, value in fields:
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:.48rem 0;border-bottom:1px solid #edf1ee;font-size:.84rem"><span class="small">{label}</span><strong>{value}</strong></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with issues:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.8rem">AI review and recommended action</div>', unsafe_allow_html=True)
        st.metric("Claim risk score", f"{claim['risk_score']} / 99")
        st.progress(claim["risk_score"] / 99)
        st.caption(f"Explanation source: {claim.get('ai_source', 'rules-engine')}")
        st.markdown(f'<div style="background:#f4f8f5;border-left:3px solid #087f73;padding:.75rem;font-size:.84rem">{claim.get("ai_explanation", claim["recommendation"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="background:#f4f8f5;border-left:3px solid #087f73;padding:.75rem;font-size:.84rem">{claim["recommendation"]}</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:700;margin-top:1rem">Detected edits</div>', unsafe_allow_html=True)
        if claim["validation"]:
            for issue in claim["validation"]:
                css = "risk-high" if issue["severity"] == "High" else "risk-medium"
                st.markdown(f'<div style="padding:.55rem 0;border-bottom:1px solid #edf1ee;font-size:.82rem"><div>{badge(issue["severity"], css)} <strong>{issue["code"]}</strong></div><div style="margin-top:.2rem">{issue["message"]}</div><div class="small">Action: {issue["action"]}</div></div>', unsafe_allow_html=True)
        else:
            st.success("No validation edits detected. Claim is clean.")
        history = claim.get("workflow_history", [])
        if history:
            st.markdown('<div style="font-weight:700;margin-top:1rem">Workflow history</div>', unsafe_allow_html=True)
            for event in reversed(history[-4:]):
                st.caption(f"{event['status']} · {event['reason']} · {event['at'][:16].replace('T', ' ')}")
        st.markdown('</div>', unsafe_allow_html=True)
    return claims


def render_analytics(claims: list[dict[str, Any]]) -> None:
    st.markdown('<div class="section"><div class="eyebrow">Revenue cycle</div><h2>Operational analytics</h2><div class="subtitle">A compact view of throughput, exposure, and avoidable friction.</div></div>', unsafe_allow_html=True)
    df = pd.DataFrame(claims)
    if df.empty:
        st.info("Add claims to populate analytics.")
        return
    metrics = st.columns(4)
    metrics[0].metric("Total billed", money(df["amount"].sum()))
    metrics[1].metric("Avg. claim value", money(df["amount"].mean()))
    metrics[2].metric("Average risk", f"{df['risk_score'].mean():.0f} / 99")
    metrics[3].metric("Open edits", sum(len(c.get("validation", [])) for c in claims))
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.6rem">Billed value by payer</div>', unsafe_allow_html=True)
        st.bar_chart(df.groupby("payer")["amount"].sum(), color="#087f73")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div style="font-weight:700;margin-bottom:.6rem">Risk by workflow status</div>', unsafe_allow_html=True)
        chart = df.groupby("status")["risk_score"].mean().sort_values(ascending=False)
        st.bar_chart(chart, color="#e8793b")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section"><div class="eyebrow">Denial prevention</div><h2>Top edit categories</h2></div>', unsafe_allow_html=True)
    issue_rows = []
    for claim in claims:
        for issue in claim.get("validation", []):
            issue_rows.append({"Edit": issue["code"], "Severity": issue["severity"], "Claim": claim["id"], "Payer": claim["payer"]})
    st.dataframe(pd.DataFrame(issue_rows) if issue_rows else pd.DataFrame([{"Edit": "None", "Severity": "-", "Claim": "-", "Payer": "-"}]), width='stretch', hide_index=True)


def render_reports(claims: list[dict[str, Any]]) -> None:
    st.markdown('<div class="section"><div class="eyebrow">Reporting</div><h2>Operational reports</h2><div class="subtitle">Generate a snapshot for billing leadership, coding review, or payer operations.</div></div>', unsafe_allow_html=True)
    report_type = st.selectbox("Report type", ["Daily queue brief", "Denial prevention report", "Payer exposure report"], key=widget_key("report_type"))
    if report_type == "Daily queue brief":
        content = f"Daily Queue Brief - {datetime.now().strftime('%Y-%m-%d')}\nClaims in register: {len(claims)}\nHigh risk: {sum(c['risk_band'] == 'High' for c in claims)}\nReady to submit: {sum(c['status'] == 'Ready to submit' for c in claims)}\nBilled value: {money(sum(float(c['amount']) for c in claims))}"
    elif report_type == "Denial prevention report":
        issues = [issue["code"] for c in claims for issue in c.get("validation", [])]
        content = "Denial Prevention Report\n\n" + "\n".join(f"{code}: {issues.count(code)}" for code in sorted(set(issues)))
    else:
        grouped = pd.DataFrame(claims).groupby("payer")["amount"].sum() if claims else pd.Series(dtype=float)
        content = "Payer Exposure Report\n\n" + "\n".join(f"{payer}: {money(amount)}" for payer, amount in grouped.items())
    st.text_area("Report preview", content, height=220)
    st.download_button("Download report", content, "claimpilot-report.txt", "text/plain", type="primary", key=widget_key("download_operational_report"))


if api_enabled():
    try:
        claims = api_claims()
    except requests.RequestException as error:
        st.error(f"Could not connect to the ClaimPilot API: {error}")
        claims = []
else:
    claims = load_claims()
render_sidebar(claims)

st.markdown('<div class="hero"><div><div class="eyebrow">Northstar Billing Group / Operations</div><h1>ClaimPilot</h1><div class="subtitle">Make every claim explainable before it becomes expensive.</div></div><div style="text-align:right"><div class="small">Tuesday, September 17, 2026</div><div style="font-size:.82rem;color:#087f73;font-weight:700;margin-top:.3rem">● SYSTEMS NOMINAL</div></div></div>', unsafe_allow_html=True)

tab_overview, tab_intake, tab_queue, tab_analytics, tab_reports = st.tabs(["Overview", "Intake & extract", "Claim queue", "Revenue cycle", "Reports"])
with tab_overview:
    render_overview(claims)
with tab_intake:
    claims = render_upload(claims)
with tab_queue:
    render_claims_table(claims)
    render_claim_detail(claims)
with tab_analytics:
    render_analytics(claims)
with tab_reports:
    render_reports(claims)
