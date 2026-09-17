from fastapi import APIRouter, HTTPException
import os
import json
from typing import List

router = APIRouter()

@router.get("/debug/upload-status")
def upload_status():
    uploads_dir = "uploads"
    if not os.path.isdir(uploads_dir):
        raise HTTPException(status_code=404, detail="uploads directory not found")

    files = []
    for fname in os.listdir(uploads_dir):
        path = os.path.join(uploads_dir, fname)
        if os.path.isfile(path):
            try:
                files.append({"name": fname, "size": os.path.getsize(path)})
            except Exception:
                files.append({"name": fname, "size": None})

    debug_path = os.path.join(uploads_dir, ".last_upload.json")
    last = None
    if os.path.exists(debug_path):
        try:
            with open(debug_path, "r", encoding="utf-8") as f:
                last = json.load(f)
        except Exception:
            last = None

    return {"uploads": files, "last_upload": last}


@router.get("/debug/qdrant")
def qdrant_status():
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if not url:
        return {"error": "QDRANT_URL not set"}
    import requests
    endpoint = url.rstrip("/") + "/collections"
    headers = {}
    if api_key:
        headers["api-key"] = api_key
    try:
        r = requests.get(endpoint, headers=headers, timeout=10)
        return {"status_code": r.status_code, "text": r.text}
    except Exception as exc:
        return {"error": str(exc)}
