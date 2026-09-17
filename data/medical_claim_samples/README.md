# Medical claim samples

These are synthetic test documents for ClaimPilot. They contain no real patient information.

| File | Format | Expected use |
|---|---|---|
| `claim_clean.txt` | TXT | Complete claim; should route to `Ready to submit` |
| `claim_pending.csv` | CSV | Complete claim with pending payment values |
| `claim_review.json` | JSON | Higher-value claim for review workflow |
| `claim_invalid.txt` | TXT | Invalid NPI, missing diagnosis, invalid POS, and amount mismatch |
| `claim_clean.docx` | DOCX | Same clean claim in Word format |
| `claim_review.pdf` | PDF | Same review claim in PDF format |

## Test in the Streamlit UI

1. Start ClaimPilot from the repository root:

   ```powershell
   .\venv\Scripts\streamlit.exe run frontend\app.py --server.port 8501
   ```

2. Open `http://localhost:8501`.
3. Open **Intake & extract**.
4. Upload any sample above.
5. Select **Extract and validate**.
6. Open **Claim queue** to inspect extracted fields, edits, risk, explanation, and routing.

## Test through the FastAPI backend

Start the backend in another terminal:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Upload a sample:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/claims/upload" -F "file=@data\medical_claim_samples\claim_clean.txt"
```

Replace the filename to test the CSV, JSON, DOCX, PDF, or invalid claim sample.
