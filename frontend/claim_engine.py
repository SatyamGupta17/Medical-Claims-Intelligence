"""Claim extraction, validation, risk scoring, and workflow helpers."""

from __future__ import annotations

import json
import os
import re
import uuid
import csv
from io import StringIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


CLAIMS_FILE = Path(__file__).resolve().parent / "claims.json"
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

STATUSES = ["Needs review", "Ready to submit", "Submitted", "Paid", "Denied"]
STATUS_COLORS = {
    "Needs review": "#d97706",
    "Ready to submit": "#0f766e",
    "Submitted": "#2563eb",
    "Paid": "#15803d",
    "Denied": "#b91c1c",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def auto_route(claim: dict[str, Any]) -> tuple[str, str]:
    """Route claims using deterministic controls before human review."""
    if claim.get("status") in {"Paid", "Denied", "Submitted"}:
        return claim["status"], "Existing downstream status preserved"
    if any(issue.get("severity") == "High" for issue in claim.get("validation", [])):
        return "Needs review", "High-severity edit requires correction"
    if not claim.get("validation"):
        return "Ready to submit", "All required edits passed"
    return "Needs review", "Medium-severity edit requires coding review"


def deterministic_explanation(claim: dict[str, Any]) -> str:
    issues = claim.get("validation", [])
    if not issues:
        return "The claim passed the configured completeness and format checks. Release it to the submission batch after payer eligibility is confirmed."
    issue_text = "; ".join(issue["message"] for issue in issues[:3])
    return f"The claim is held because {issue_text}. Correct the flagged fields, then re-run validation before submission."


def generate_ai_explanation(claim: dict[str, Any]) -> tuple[str, str]:
    """Use Groq when configured, with an auditable local fallback."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return deterministic_explanation(claim), "rules-engine"
    try:
        from groq import Groq

        prompt = {
            "claim_id": claim["id"],
            "risk_score": claim["risk_score"],
            "risk_band": claim["risk_band"],
            "fields": {key: claim.get(key) for key in ("payer", "provider", "diagnosis", "procedure", "amount", "place_of_service")},
            "validation_edits": claim.get("validation", []),
        }
        response = Groq(api_key=api_key).chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            temperature=0.1,
            max_tokens=220,
            messages=[
                {"role": "system", "content": "You are a medical billing operations agent. Explain only the supplied claim evidence. Give one concise reason and one recommended action. Do not invent payer policy or clinical facts."},
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        text = response.choices[0].message.content.strip()
        if text:
            return text, "groq"
    except Exception:
        pass
    return deterministic_explanation(claim), "rules-engine"


def _value(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else default


def _money(value: str) -> float:
    try:
        return float(re.sub(r"[^0-9.]", "", value))
    except (TypeError, ValueError):
        return 0.0


def normalize_document_text(text: str, filename: str = "") -> str:
    """Convert JSON/CSV claim records into the labeled text extractor format."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(text)
            if isinstance(payload, dict):
                return "\n".join(f"{key.replace('_', ' ')}: {value}" for key, value in payload.items())
        except json.JSONDecodeError:
            pass
    if suffix == ".csv":
        rows = list(csv.DictReader(StringIO(text)))
        if rows:
            return "\n".join(f"{key.replace('_', ' ')}: {value}" for key, value in rows[0].items() if value is not None)
    return text


def extract_claim(text: str, filename: str) -> dict[str, Any]:
    """Extract common claim fields from labeled synthetic documents."""
    text = normalize_document_text(text, filename)
    service_date = _value(r"(?:date of service|service date|dos)\s*[:#-]?\s*([0-9/\-]+)", text)
    claim_id = _value(r"(?:claim id|claim number|control number)\s*[:#-]?\s*([A-Z0-9\-]+)", text, f"CLM-{uuid.uuid4().hex[:8].upper()}")
    patient_id = _value(r"patient id\s*[:#-]?\s*([^\n\r]+)", text, "Not provided")
    patient = _value(r"(?:patient name|member name|patient(?!\s+id))\s*[:#-]?\s*([^\n\r]+)", text, "Unknown patient")
    patient_dob = _value(r"(?:patient dob|date of birth|dob)\s*[:#-]?\s*([0-9/\-]+)", text, "Not provided")
    member_id = _value(r"(?:member id|subscriber id|policy number)\s*[:#-]?\s*([A-Z0-9\-]+)", text, "Not provided")
    payer = _value(r"(?:payer|insurance|health plan)\s*[:#-]?\s*([^\n\r]+)", text, "Unknown payer")
    provider = _value(r"(?:provider name|rendering provider|provider(?!\s+npi))\s*[:#-]?\s*([^\n\r]+)", text, "Unknown provider")
    npi = _value(r"(?:provider npi|npi)\s*[:#-]?\s*([0-9]+)", text, "")
    diagnosis = _value(r"(?:diagnosis codes?|icd(?:-10)?(?: codes?)?)\s*[:#-]?\s*([^\n\r]+)", text, "Not provided")
    procedure = _value(r"(?:procedure codes?|cpt(?: codes?)?|hcpcs(?: codes?)?)\s*[:#-]?\s*([^\n\r]+)", text, "Not provided")
    amount = _money(_value(r"(?:billed amount|charge|total charge|amount)\s*[:#-]?\s*([$0-9,.]+)", text, "0"))
    allowed_amount = _money(_value(r"allowed amount\s*[:#-]?\s*([$0-9,.]+)", text, "0"))
    paid_amount = _money(_value(r"paid amount\s*[:#-]?\s*([$0-9,.]+)", text, "0"))
    place = _value(r"(?:place of service|pos)\s*[:#-]?\s*([0-9]{2})", text, "11")

    claim = {
        "id": claim_id,
        "patient_id": patient_id,
        "patient": patient,
        "patient_dob": patient_dob,
        "member_id": member_id,
        "payer": payer,
        "provider": provider,
        "npi": npi,
        "service_date": service_date or "Not provided",
        "diagnosis": diagnosis,
        "procedure": procedure,
        "amount": amount,
        "allowed_amount": allowed_amount,
        "paid_amount": paid_amount,
        "place_of_service": place,
        "source_file": filename,
        "status": "Needs review",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "notes": [],
        "workflow_history": [],
    }
    claim["validation"] = validate_claim(claim)
    claim["risk_score"] = calculate_risk(claim)
    claim["risk_band"] = risk_band(claim["risk_score"])
    claim["recommendation"] = recommendation(claim)
    claim["status"], route_reason = auto_route(claim)
    claim["workflow_history"].append({"status": claim["status"], "reason": route_reason, "at": claim["created_at"]})
    claim["ai_explanation"], claim["ai_source"] = generate_ai_explanation(claim)
    return claim


def validate_claim(claim: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    required = {
        "patient": "Patient name is missing",
        "member_id": "Member ID is missing",
        "payer": "Payer is missing",
        "provider": "Rendering provider is missing",
        "service_date": "Date of service is missing",
        "diagnosis": "Diagnosis code is missing",
        "procedure": "Procedure code is missing",
    }
    for field, message in required.items():
        if not claim.get(field) or claim.get(field) in {"Not provided", "Unknown patient", "Unknown payer", "Unknown provider"}:
            issues.append({"severity": "High", "code": "MISSING_FIELD", "message": message, "action": f"Add {field.replace('_', ' ')} before submission"})

    if claim.get("npi") and not re.fullmatch(r"\d{10}", str(claim["npi"])):
        issues.append({"severity": "High", "code": "INVALID_NPI", "message": "NPI must contain exactly 10 digits", "action": "Verify the rendering provider NPI"})
    if float(claim.get("amount", 0)) <= 0:
        issues.append({"severity": "High", "code": "INVALID_CHARGE", "message": "Billed amount must be greater than zero", "action": "Correct the charge amount"})
    allowed = float(claim.get("allowed_amount", 0))
    paid = float(claim.get("paid_amount", 0))
    billed = float(claim.get("amount", 0))
    if allowed and allowed > billed:
        issues.append({"severity": "Medium", "code": "ALLOWED_EXCEEDS_BILLED", "message": "Allowed amount exceeds billed amount", "action": "Reconcile billed and allowed amounts"})
    if paid and allowed and paid > allowed:
        issues.append({"severity": "High", "code": "PAID_EXCEEDS_ALLOWED", "message": "Paid amount exceeds allowed amount", "action": "Reconcile remittance and payment amounts"})
    if claim.get("service_date") and claim.get("service_date") != "Not provided":
        if not re.fullmatch(r"\d{1,4}[\-/]\d{1,2}[\-/]\d{1,4}", str(claim["service_date"])):
            issues.append({"severity": "Medium", "code": "DATE_FORMAT", "message": "Date format could not be normalized", "action": "Confirm the date of service"})
    if claim.get("procedure") == "Not provided" or claim.get("diagnosis") == "Not provided":
        issues.append({"severity": "High", "code": "CODE_PAIR", "message": "Diagnosis and procedure codes are required for medical necessity review", "action": "Add valid ICD-10 and CPT/HCPCS codes"})
    if claim.get("place_of_service") not in {"11", "12", "21", "22", "23", "24", "31", "32", "49", "81"}:
        issues.append({"severity": "Medium", "code": "POS_CODE", "message": "Place of service code is not in the supported set", "action": "Verify the POS code against payer policy"})
    return issues


def calculate_risk(claim: dict[str, Any]) -> int:
    points = {"High": 28, "Medium": 12, "Low": 3}
    score = sum(points.get(issue["severity"], 0) for issue in claim.get("validation", []))
    if float(claim.get("amount", 0)) >= 5000:
        score += 12
    if not claim.get("npi"):
        score += 10
    return min(99, max(4, score))


def risk_band(score: int) -> str:
    if score >= 60:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def recommendation(claim: dict[str, Any]) -> str:
    issues = claim.get("validation", [])
    if not issues:
        return "Approve for submission. Run a final payer eligibility check before batching."
    if any(issue["severity"] == "High" for issue in issues):
        return "Hold claim. Correct high-severity data issues and re-run validation before submission."
    return "Route to coding review. Confirm payer-specific edits, then release to the ready queue."


def seed_claims() -> list[dict[str, Any]]:
    samples = [
        "Claim ID: CLM-24081\nPatient: Maya Patel\nMember ID: HZP-902144\nPayer: Horizon Health\nProvider: Northstar Family Clinic\nNPI: 1245789630\nDate of Service: 08/28/2026\nDiagnosis: J06.9\nProcedure: 99213\nBilled Amount: $185.00\nPlace of Service: 11",
        "Claim ID: CLM-24082\nPatient: Oliver Chen\nMember ID: AET-551028\nPayer: Aetna\nProvider: Harborview Ortho\nNPI: 1245789630\nDate of Service: 08/29/2026\nDiagnosis: M25.561\nProcedure: 99214\nBilled Amount: $640.00\nPlace of Service: 22",
        "Claim ID: CLM-24083\nPatient: Sofia Rivera\nMember ID: Not provided\nPayer: Meridian Health\nProvider: Westside Imaging\nDate of Service: 08/30/2026\nDiagnosis: R10.9\nProcedure: 74177\nBilled Amount: $6,450.00\nPlace of Service: 22",
        "Claim ID: CLM-24084\nPatient: Ethan Williams\nMember ID: UHC-771240\nPayer: United Healthcare\nProvider: Lakeside Pediatrics\nNPI: 1245789630\nDate of Service: 09/01/2026\nDiagnosis: Z00.129\nProcedure: 99393\nBilled Amount: $240.00\nPlace of Service: 11",
    ]
    claims = [extract_claim(text, "synthetic_batch.txt") for text in samples]
    claims[0]["status"] = "Ready to submit"
    claims[1]["status"] = "Submitted"
    claims[2]["status"] = "Needs review"
    claims[3]["status"] = "Paid"
    return claims


def load_claims() -> list[dict[str, Any]]:
    if not CLAIMS_FILE.exists():
        claims = seed_claims()
        save_claims(claims)
        return claims
    try:
        return json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return seed_claims()


def save_claims(claims: list[dict[str, Any]]) -> None:
    CLAIMS_FILE.write_text(json.dumps(claims, indent=2), encoding="utf-8")


def update_claim(claims: list[dict[str, Any]], claim_id: str, **updates: Any) -> list[dict[str, Any]]:
    for claim in claims:
        if claim["id"] == claim_id:
            previous_status = claim.get("status")
            claim.update(updates)
            claim["updated_at"] = now_iso()
            claim["validation"] = validate_claim(claim)
            claim["risk_score"] = calculate_risk(claim)
            claim["risk_band"] = risk_band(claim["risk_score"])
            claim["recommendation"] = recommendation(claim)
            if claim.get("status") != previous_status:
                claim.setdefault("workflow_history", []).append({"status": claim["status"], "reason": "Operator action", "at": claim["updated_at"]})
            claim["ai_explanation"], claim["ai_source"] = generate_ai_explanation(claim)
            break
    save_claims(claims)
    return claims
