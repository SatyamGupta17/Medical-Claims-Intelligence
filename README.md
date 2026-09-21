# ClaimPilot

ClaimPilot is a Streamlit-based medical billing operations console for synthetic claims. It extracts claim fields from uploaded documents, validates completeness and format, scores denial risk, explains issues, routes claims through a workflow, tracks the register, analyzes revenue-cycle metrics, and generates operational reports.

> This project is a synthetic-data prototype. It is not a HIPAA-compliant production system and must not be used with real PHI until authentication, authorization, encryption, audit controls, secure infrastructure, and compliance requirements are implemented.

## Features

- Upload synthetic `TXT`, `CSV`, `JSON`, `PDF`, and `DOCX` claim documents
- Extract patient, payer, provider, NPI, service date, diagnosis, procedure, POS, and charge fields
- Validate required fields, NPI format, charge amount, date format, code pairing, and POS values
- Identify high- and medium-severity denial risks
- Calculate a claim risk score and risk band
- Generate an AI explanation with Groq when `GROQ_API_KEY` is configured
- Fall back to an auditable local rules-engine explanation when no LLM is available
- Automatically route claims:
  - High-severity edit -> `Needs review`
  - Medium-severity edit -> `Needs review`
  - No edits -> `Ready to submit`
- Track workflow history and operator status changes
- Search and filter the claims register
- View billed value, risk, status, payer, and edit analytics
- Download claim-register JSON and operational text reports
- Persist claims locally in `frontend/claims.json`

## Requirements

- Windows PowerShell
- Python 3.11 recommended
- A virtual environment
- Internet access for installing packages and optional Groq calls

## Setup on Windows

Open PowerShell in the repository root:

```powershell
cd "D:\Tech stack\Document-rag"
```

Create a virtual environment if one does not already exist:

```powershell
py -3.11 -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Verify the document parsers:

```powershell
python -c "import docx, fitz; print('document parsers available')"
```

## Configure AI explanations

AI explanations are optional. Without a Groq key, ClaimPilot uses the local rules engine.

Create or update `.env` in the repository root:

```dotenv
GROQ_API_KEY=your_rotated_groq_key
GROQ_MODEL=openai/gpt-oss-120b
```

Never commit `.env`. It is ignored by `.gitignore`. Rotate any credentials that have previously been exposed in this repository.

## Run ClaimPilot

The main product is the Streamlit frontend. The FastAPI service is used for the claims API and does not include the legacy document-RAG workflow.

From the repository root:

```powershell
.\venv\Scripts\streamlit.exe run frontend\app.py --server.port 8501
```

Or activate the environment first and run:

```powershell
.\venv\Scripts\Activate.ps1
cd frontend
streamlit run app.py --server.port 8501
```

Open the application at:

```text
http://localhost:8501
```

To run on another port:

```powershell
.\venv\Scripts\streamlit.exe run frontend\app.py --server.port 8502
```

## Deploy with Docker Compose

Docker deployment runs two services:

- `api`: FastAPI claims backend on port `8000`
- `frontend`: Streamlit operations console on port `8501`

The Compose setup persists `frontend/claims.json`, `uploads/`, and `data/` on the host. The deployment image uses `requirements-deploy.txt`, which contains the production claims workflow dependencies for the claim intake and analytics app.

### Prerequisites

- Docker Desktop with Compose enabled
- A rotated Groq key, if AI explanations are required

### Start the deployment

From the repository root:

```powershell
docker compose build
docker compose up -d
```

Check service status:

```powershell
docker compose ps
```

Check the backend:

```powershell
curl.exe http://127.0.0.1:8000/api/health
```

Open the frontend:

```text
http://localhost:8501
```

View logs:

```powershell
docker compose logs -f api
docker compose logs -f frontend
```

Stop the deployment:

```powershell
docker compose down
```

After code or dependency changes, rebuild:

```powershell
docker compose down
docker compose build --no-cache
docker compose up -d
```

The Compose deployment is suitable for a private internal demo or development environment. For public production deployment, place TLS and authentication in front of both services, store `.env` in a secret manager, restrict exposed ports, use a managed database/object store instead of local JSON/files, and configure backups and monitoring.

## Free deployment

The easiest free setup is:

- Streamlit Community Cloud for the frontend
- Render free web service for the optional FastAPI backend
- Local rules-engine explanations, or a Groq key added as a deployment secret

### Deploy the frontend to Streamlit Community Cloud

1. Push this repository to GitHub. Confirm `.env` is not committed.
2. Open [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Select the repository and branch.
4. Set the main file path to `frontend/app.py`.
5. In **Advanced settings**, select Python 3.11 if available.
6. Add the contents of `requirements-deploy.txt` to the app's dependency configuration, or rename/copy it to `requirements.txt` in the deployed branch.
7. In **Advanced settings -> Secrets**, add the Render URL and optional Groq settings as valid TOML:

```toml
CLAIMPILOT_API_URL = "https://your-render-service.onrender.com"
GROQ_API_KEY = "your_rotated_groq_key"
GROQ_MODEL = "openai/gpt-oss-120b"
```

  `CLAIMPILOT_API_URL` must not include a trailing `/api`. Add `GROQ_API_KEY` and `GROQ_MODEL` only if AI explanations are required.
8. Deploy and open the generated `streamlit.app` URL.

The frontend processes uploaded claims locally, so it does not require the Render API for the core intake, extraction, validation, risk, dashboard, and report workflow.

### Deploy the backend to Render free

The repository includes [render.yaml](render.yaml).

1. Push the repository to GitHub.
2. Open [dashboard.render.com](https://dashboard.render.com) and create a new **Blueprint**.
3. Connect the GitHub repository.
4. Render detects `render.yaml` and creates `claimpilot-api`.
5. Add `GROQ_API_KEY` in the service environment settings if AI explanations are required.
6. Deploy and wait for the health check to pass.
7. Test the generated URL:

```text
https://your-render-service.onrender.com/api/health
```

Render free services sleep when idle and have ephemeral local storage. Therefore, uploaded files and `frontend/claims.json` must be treated as temporary. Do not use this free setup for real PHI or durable production records.

### Free deployment limitations

- Streamlit Community Cloud and Render free instances can sleep.
- Local JSON and uploaded files are not durable across redeploys or instance replacement.
- There is no built-in authentication in this prototype.
- Public deployment requires access control before handling any sensitive data.
- Use synthetic claims only on free hosting.

## Use the application

1. Open the `Overview` tab to see queue volume, billed value, risk mix, and priority claims.
2. Open `Intake & extract`.
3. Upload a synthetic claim file.
4. Select `Extract and validate`.
5. Open `Claim queue` to inspect extracted fields, edits, risk score, AI/rules explanation, and workflow history.
6. Use `Revenue cycle` for payer and risk analytics.
7. Use `Reports` to preview and download an operational report.
8. To restore the seeded sample register, remove `frontend/claims.json` and restart the app.

## Supported document format

The extractor works best with labeled synthetic documents. For example:

```text
Claim Number: CLM-2026-0001
Patient Name: John Carter
Member ID: MCR10001
Payer: Medicare
Provider NPI: 1234567890
Provider Name: City Medical Center
Date of Service: 2026-08-15
Place of Service: 11
Diagnosis Codes: E11.9, I10
Procedure Codes: 99213
Billed Amount: 150.00
```

The parser accepts common label variants such as `Claim ID`, `Patient`, `NPI`, `DOS`, `Diagnosis`, `Procedure`, `Charge`, and `POS`.

## Generate the provided sample files

`script.py` creates six synthetic text claims and a ZIP archive. It was written with `/mnt/data` paths, so it is intended for a notebook or Linux environment and is not required to run ClaimPilot on Windows.

For Windows, use the application’s built-in seeded claims or place your own `.txt` files in the upload workflow. If you adapt `script.py` for Windows, change its paths to something like:

```python
base = Path("data/medical_claim_samples")
zip_path = Path("data/medical_claim_samples.zip")
```

## FastAPI backend

The FastAPI backend exposes the ClaimPilot claims API. Start it from the repository root in a second terminal:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Health check:

```text
http://127.0.0.1:8000/
```

ClaimPilot API endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service health and claim count |
| `POST` | `/api/claims/upload` | Upload, extract, validate, score, and route a claim |
| `GET` | `/api/claims` | List claims with optional `status` and `risk_band` filters |
| `GET` | `/api/claims/{claim_id}` | Retrieve one claim |
| `PATCH` | `/api/claims/{claim_id}/status` | Record a workflow status change |
| `GET` | `/api/metrics` | Return revenue-cycle metrics |
| `GET` | `/api/reports/operational` | Return a priority operational report |

Example upload from PowerShell:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/claims/upload" -F "file=@data\medical_claim_samples\true_claim_low_priority.txt"
```

Example status update:

```powershell
curl.exe -X PATCH "http://127.0.0.1:8000/api/claims/CLM-2026-0001/status" -H "Content-Type: application/json" -d "{\"status\":\"Submitted\"}"
```

The Streamlit console can run without this backend because it uses the same local claim engine directly. PDF extraction uses PyMuPDF, and DOCX extraction uses `python-docx`.

## Project structure

```text
Document-rag/
├── app/
│   ├── main.py              # FastAPI claims service
│   ├── extractor.py         # PDF text extraction
│   └── api/
│       └── debug.py         # Optional debug endpoints
├── frontend/
│   ├── app.py               # ClaimPilot Streamlit application
│   ├── claim_engine.py      # Extraction, validation, risk, AI, routing
│   └── claims.json          # Local claim register, created automatically
├── uploads/                 # Uploaded source documents
├── data/                    # Optional local sample data
├── requirements.txt
├── script.py                # Optional synthetic sample generator
└── .env                     # Local secrets, never commit
```

## Troubleshooting

### `streamlit` cannot find `app.py`

Run from the repository root with the full path:

```powershell
.\venv\Scripts\streamlit.exe run frontend\app.py --server.port 8501
```

Or change into `frontend` before using `streamlit run app.py`.

### Port 8501 is already in use

Use another port:

```powershell
.\venv\Scripts\streamlit.exe run frontend\app.py --server.port 8502
```

### `ModuleNotFoundError: docx` or `fitz`

Install the project requirements using the same interpreter that launches Streamlit:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Then verify:

```powershell
.\venv\Scripts\python.exe -c "import docx, fitz; print('document parsers available')"
```

### Groq is unavailable

The app intentionally falls back to the local rules engine. Check `.env`, rotate the key if necessary, and restart Streamlit after changing environment variables.

### Reset local claim data

Use the sidebar’s `Reset demo claims` button, or remove the generated register and restart:

```powershell
Remove-Item frontend\claims.json
```

## Validation commands

Run syntax checks:

```powershell
.\venv\Scripts\python.exe -m py_compile frontend\app.py frontend\claim_engine.py
```

Run the FastAPI service only when you need the legacy document Q&A endpoints. The primary application is the Streamlit ClaimPilot console.
