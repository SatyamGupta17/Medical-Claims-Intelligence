from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from frontend.claim_engine import load_claims, save_claims, update_claim, extract_claim

app = FastAPI()


class ClaimStatusUpdate(BaseModel):
    status: str


def _claim_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        from app.extractor import extract_text

        return extract_text(content)
    if suffix == ".docx":
        from docx import Document

        document = Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return content.decode("utf-8", errors="ignore")


def _find_claim(claim_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    claims = load_claims()
    claim = next((item for item in claims if item["id"] == claim_id), None)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return claims, claim


# Home Route
@app.get("/")
def home():

    return {
        "message": "ClaimPilot API Running",
        "service": "claims-and-document-rag",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "claimpilot", "claims": len(load_claims())}


@app.post("/api/claims/upload")
async def upload_claim(file: UploadFile = File(...)):
    supported = {".txt", ".csv", ".json", ".pdf", ".docx"}
    filename = Path(file.filename or "claim.txt").name
    if Path(filename).suffix.lower() not in supported:
        raise HTTPException(status_code=400, detail="Supported claim files: TXT, CSV, JSON, PDF, DOCX")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded claim document is empty")
    try:
        claim = extract_claim(_claim_text(filename, content), filename)
    except ImportError as error:
        raise HTTPException(status_code=503, detail="The required document parser is not installed") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    claims = load_claims()
    claims.insert(0, claim)
    save_claims(claims)
    return {"claim": claim, "message": "Claim extracted, validated, scored, and routed"}


@app.get("/api/claims")
def list_claims(status: str | None = None, risk_band: str | None = None):
    claims = load_claims()
    if status:
        claims = [claim for claim in claims if claim.get("status") == status]
    if risk_band:
        claims = [claim for claim in claims if claim.get("risk_band") == risk_band]
    return {"count": len(claims), "claims": claims}


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: str):
    _, claim = _find_claim(claim_id)
    return claim


@app.patch("/api/claims/{claim_id}/status")
def set_claim_status(claim_id: str, update: ClaimStatusUpdate):
    if update.status not in {"Needs review", "Ready to submit", "Submitted", "Paid", "Denied"}:
        raise HTTPException(status_code=400, detail="Invalid workflow status")
    claims, _ = _find_claim(claim_id)
    update_claim(claims, claim_id, status=update.status)
    _, claim = _find_claim(claim_id)
    return claim


@app.get("/api/metrics")
def metrics():
    claims = load_claims()
    total = len(claims)
    return {
        "claim_count": total,
        "billed_value": sum(float(claim.get("amount", 0)) for claim in claims),
        "average_risk_score": round(sum(float(claim.get("risk_score", 0)) for claim in claims) / total, 2) if total else 0,
        "open_edits": sum(len(claim.get("validation", [])) for claim in claims),
        "by_status": {status: sum(1 for claim in claims if claim.get("status") == status) for status in ["Needs review", "Ready to submit", "Submitted", "Paid", "Denied"]},
        "by_risk_band": {band: sum(1 for claim in claims if claim.get("risk_band") == band) for band in ["High", "Medium", "Low"]},
    }


@app.get("/api/reports/operational")
def operational_report():
    claims = load_claims()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": metrics(),
        "priority_claims": sorted(claims, key=lambda claim: claim.get("risk_score", 0), reverse=True)[:10],
    }


