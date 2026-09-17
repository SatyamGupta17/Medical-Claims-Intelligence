from pathlib import Path
import zipfile

base = Path("/mnt/data/medical_claim_samples")
base.mkdir(parents=True, exist_ok=True)

claims = {
    "true_claim_low_priority.txt": """Claim Number: CLM-2026-0001
Patient ID: P10001
Patient Name: John Carter
Patient DOB: 1985-04-12
Payer: Medicare
Member ID: MCR10001
Provider NPI: 1234567890
Provider Name: City Medical Center
Date of Service: 2026-08-15
Place of Service: 11
Diagnosis Codes: E11.9, I10
Procedure Codes: 99213
Billed Amount: 150.00
Allowed Amount: 120.00
Paid Amount: 120.00
Claim Status: Clean
Priority: Low
""",
    "true_claim_medium_priority.txt": """Claim Number: CLM-2026-0002
Patient ID: P10002
Patient Name: Sarah Miller
Patient DOB: 1978-09-21
Payer: Aetna
Member ID: AET20002
Provider NPI: 2345678901
Provider Name: Northside Family Clinic
Date of Service: 2026-08-02
Place of Service: 11
Diagnosis Codes: J06.9
Procedure Codes: 99214
Billed Amount: 250.00
Allowed Amount: 190.00
Paid Amount: 150.00
Claim Status: Pending
Priority: Medium
""",
    "true_claim_high_priority.txt": """Claim Number: CLM-2026-0003
Patient ID: P10003
Patient Name: Robert Wilson
Patient DOB: 1969-03-03
Payer: UnitedHealthcare
Member ID: UHC30003
Provider NPI: 3456789012
Provider Name: Metro Health Associates
Date of Service: 2026-07-20
Place of Service: 22
Diagnosis Codes: M54.5, G89.29
Procedure Codes: 97110, 97140
Billed Amount: 1200.00
Allowed Amount: 850.00
Paid Amount: 500.00
Claim Status: Pending Review
Priority: High
""",
    "false_claim_high_priority_missing_diagnosis.txt": """Claim Number: CLM-2026-0004
Patient ID: P10004
Patient Name: Emily Davis
Patient DOB: 1990-11-11
Payer: Aetna
Member ID: AET40004
Provider NPI: 12345
Provider Name: Westside Medical Group
Date of Service: 2026-08-10
Place of Service: 99
Diagnosis Codes:
Procedure Codes: 99214
Billed Amount: 2500.00
Allowed Amount: 1200.00
Paid Amount: 1500.00
Claim Status: Error
Priority: High
""",
    "false_claim_high_priority_invalid_npi.txt": """Claim Number: CLM-2026-0005
Patient ID: P10005
Patient Name: Michael Brown
Patient DOB: 1975-05-18
Payer: Medicare
Member ID: MCR50005
Provider NPI: 987654
Provider Name: Central Care Hospital
Date of Service: 2026-08-12
Place of Service: 21
Diagnosis Codes: I10
Procedure Codes: 99223
Billed Amount: 1800.00
Allowed Amount: 1400.00
Paid Amount: 900.00
Claim Status: Rejected
Priority: High
""",
    "false_claim_medium_priority_amount_mismatch.txt": """Claim Number: CLM-2026-0006
Patient ID: P10006
Patient Name: Lisa Anderson
Patient DOB: 1988-06-27
Payer: BlueCross
Member ID: BC60006
Provider NPI: 4567890123
Provider Name: Lakeside Health Clinic
Date of Service: 2026-08-05
Place of Service: 11
Diagnosis Codes: E78.5
Procedure Codes: 99213
Billed Amount: 500.00
Allowed Amount: 600.00
Paid Amount: 650.00
Claim Status: Error
Priority: Medium
""",
}

for filename, content in claims.items():
    (base / filename).write_text(content, encoding="utf-8")

zip_path = Path("/mnt/data/medical_claim_samples.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(base.glob("*.txt")):
        z.write(path, arcname=path.name)

print(f"Created {len(claims)} synthetic claim files.")
print(zip_path)
