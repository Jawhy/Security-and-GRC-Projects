# TPRM Risk Scoring Engine

🔗 **[[Live Demo](https://tprmdemo.streamlit.app/)]



A financial-sector aligned Third-Party Risk Management (TPRM) assessment tool built in Python.

This project simulates a structured supplier assurance workflow used in banking, fintech, and regulated technology environments.

It generates inherent and residual risk ratings, control domain mappings, enhanced AI governance due diligence, and committee-ready management reporting outputs.

---

## Overview

This tool performs structured third-party risk assessments across multiple weighted factors and produces:

- Inherent and Residual Risk Scores (0–100)
- Risk Tier Classification: Low / Medium / High / Critical
- ISO 27001:2022 control domain impact mapping
- ISO 42001:2023 AI governance risk gap detection
- GDPR cross-border data transfer risk flags
- Critical outsourcing escalation triggers
- Evidence request lists for assurance reviews
- Risk owner tracking and review schedule alerts
- Exported committee-ready Markdown reporting

---

## Regulatory & Framework Alignment

| Framework | Application Within Tool |
|-----------|-------------------------|
| ISO/IEC 27001:2022 | Information classification, supplier management, BCP/DR control mapping |
| ISO/IEC 42001:2023 | AI governance oversight and enhanced due diligence |
| FCA SS2/21 | Outsourcing and third-party risk oversight |
| EBA GL/2019/02 | ICT & security risk management in financial services |
| UK GDPR (Art. 44) | Cross-border transfer safeguard validation |

---

## Risk Scoring Methodology

### Inherent Risk

Inherent risk is calculated across five weighted domains:

| Factor | Max Score | Framework Reference |
|--------|-----------|---------------------|
| Data Sensitivity | 30 | ISO 27001 A.5.12 / A.8.10 |
| Hosting Location | 20 | UK GDPR Art.44 / FCA SS2/21 |
| AI Usage | 15 | ISO 42001 |
| Subcontractor Exposure | 15 | ISO 27001 A.5.19–A.5.22 |
| Service Criticality | 20 | EBA GL/2019/02 |

Total maximum inherent score: **90** → Normalised to 100.

### Residual Risk

Residual risk is derived by applying control strength reductions based on verified certifications, including:

- ISO 27001
- SOC 2 Type II
- PCI DSS
- ISO 42001 (AI Governance)
- GDPR compliance
- Cyber Essentials Plus

### Risk Tier Thresholds

| Score | Tier |
|-------|------|
| 0–25 | Low |
| 26–50 | Medium |
| 51–75 | High |
| 76–100 | Critical |

---

## Governance Outputs

The engine produces:

- Vendor-level assurance breakdown
- Portfolio-level risk distribution
- Overdue review alerts
- Enhanced AI vendor due diligence checklist
- Escalation flags for material outsourcing risks
- Committee-ready Markdown report export

Generated report path:
```
reports/committee_pack.md
```

---

## Project Structure

```
01-tprm-risk-scoring-engine/
├── main.py
├── README.md
├── requirements.txt
├── sample_data/
│   └── vendors.json
└── reports/
    └── committee_pack.md  (auto-generated)
```

---

## How to Run

1. Activate virtual environment:
```
source ~/GRC-Projects/venv/bin/activate
```

2. Navigate to project directory:
```
cd ~/GRC-Projects/01-tprm-risk-scoring-engine
```

3. Install dependency:
```
pip install -r requirements.txt
```

4. Execute tool:
```
python3 main.py
```

5. View generated committee report:
```
cat reports/committee_pack.md
```

---

## Author

Ajibola Yusuff
Governance, Risk & Compliance | ISO 27001 | ISO 42001 | CompTIA Security+
Third-Party Risk Management | AI Vendor Risk | Identity Security
