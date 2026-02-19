# Compliance Risk Register Dashboard

🔗 **[Live Demo](https://compliancedashboard.streamlit.app/)** 

A financial-sector aligned compliance risk register analysis and reporting tool built in Python and Streamlit.

This project simulates the governance reporting workflow used in banking and regulated environments — ingesting a risk register CSV, calculating risk scores, flagging overdue reviews, and generating committee-ready outputs.

---

## Overview

This tool processes compliance risk registers and produces:

- Risk scoring via Likelihood × Impact matrix (1–25 scale)
- Risk Tier Classification: Low / Medium / High / Critical
- Overdue and due-soon review alerts
- Top 5 critical risks summary
- Interactive risk heatmap, distribution chart, and category breakdown
- Committee-ready Markdown report export
- CSV risk register export
- Live risk entry via sidebar form
- CSV upload for existing risk registers

---

## Regulatory & Framework Alignment

| Framework | Application Within Tool |
|-----------|-------------------------|
| ISO/IEC 27001:2022 | Control domain references per risk entry |
| NIST CSF | Risk categorisation and control mapping |
| FCA SYSC | Operational and compliance risk oversight |
| UK GDPR | Data privacy risk identification and tracking |
| ISO/IEC 42001:2023 | AI governance risk category support |

---

## Risk Scoring Methodology

### Risk Score
```
Risk Score = Likelihood (1–5) × Impact (1–5)
Maximum Score = 25
```

### Risk Tier Thresholds

| Score | Tier |
|-------|------|
| 20–25 | Critical |
| 12–19 | High |
| 6–11  | Medium |
| 1–5   | Low |

---

## CSV Format

The tool accepts any CSV with these column headers:

| Column | Description |
|--------|-------------|
| risk_id | Unique risk identifier (e.g. R001) |
| risk_title | Short risk description |
| category | Risk category |
| risk_owner | Accountable owner |
| likelihood | Score 1–5 |
| impact | Score 1–5 |
| existing_controls | Controls currently in place |
| remediation_action | Planned remediation steps |
| review_date | Format: YYYY-MM-DD |
| status | Open / In Progress / Closed |
| framework_ref | Applicable framework reference |

---

## Project Structure

```
03-compliance-risk-dashboard/
├── main.py
├── app.py
├── README.md
├── requirements.txt
└── sample_data/
    └── risk_register.csv
```

---

## How to Run

1. Activate virtual environment:
```
source ~/GRC-Projects/venv/bin/activate
```

2. Navigate to project:
```
cd ~/GRC-Projects/03-compliance-risk-dashboard
```

3. Run CLI tool:
```
python3 main.py
```

4. Run Streamlit dashboard:
```
streamlit run app.py
```

---

## Sample Dataset

The included sample register contains 10 risks across categories including:
- Cyber Security
- Third-Party Risk
- Regulatory Compliance
- AI Governance
- Data Privacy
- Operational Resilience
- Cloud Security

Produces a mix of Critical, High, Medium, and Low rated risks with overdue review alerts.

---

## Author

Ajibola Yusuff
Governance, Risk & Compliance | ISO 27001 | ISO 42001 | CompTIA Security+
Third-Party Risk Management | AI Vendor Risk | Identity Security
