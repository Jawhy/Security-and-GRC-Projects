# Risk Appetite & Metrics Dashboard

🔗 **[Live Demo](#)** ← update after deployment

A financial-sector aligned risk appetite monitoring and committee reporting tool built in Python and Streamlit.

This project simulates the compliance metrics workflow used in banking and regulated environments — tracking key risk indicators against defined appetite and tolerance thresholds, detecting trends, flagging breaches, and generating committee-ready outputs.

---

## Overview

This tool tracks compliance risk appetite metrics and produces:

- RAG Status per metric: Red / Amber / Green
- Appetite and tolerance threshold comparison
- Trend detection — improving vs worsening per metric
- Period-on-period change indicators
- Breach alerts with owner and remediation action
- AI-powered committee briefing (Groq / Llama 3)
- AI chat assistant for metric guidance and analysis
- Markdown and CSV report export
- JSON upload and download for metric sets
- Live metric entry and update via sidebar form

---

## Regulatory & Framework Alignment

| Framework | Application Within Tool |
|-----------|-------------------------|
| ISO/IEC 27001:2022 | Control metrics — vulnerabilities, audit findings, policy exceptions |
| FCA SYSC | Regulatory breach tracking and operational risk oversight |
| ISO/IEC 42001:2023 | AI model incident monitoring and governance metrics |
| UK GDPR | Data subject complaint tracking and DPO oversight |
| NIST CSF | Vulnerability management and security posture metrics |

---

## RAG Methodology

### Risk Score Logic
```
Green  = Current value within appetite threshold
Amber  = Current value between appetite and tolerance
Red    = Current value has breached tolerance threshold
```

### Threshold Direction

| Metric Type | Example | Logic |
|-------------|---------|-------|
| Lower is better | Regulatory Breaches | Red if current > tolerance |
| Higher is better | BCP Tests Completed | Red if current < tolerance |

### Metrics Tracked

| Metric | Owner | Framework |
|--------|-------|-----------|
| Regulatory Breach Count | Chief Compliance Officer | FCA SYSC 6.1 |
| Third-Party High Risk Vendors | Head of TPRM | FCA SS2/21 |
| Overdue Risk Reviews | Chief Risk Officer | ISO 27001 A.6.1 |
| Critical Vulnerabilities Open | CISO | ISO 27001 A.8.8 |
| Data Subject Complaints | DPO | UK GDPR Art.57 |
| AI Model Incidents | Chief Risk Officer | ISO 42001 |
| BCP Tests Completed | COO | ISO 27001 A.5.30 |
| Security Awareness Completion | CISO | ISO 27001 A.6.3 |
| Audit Findings Open | Head of Internal Audit | ISO 27001 A.9 |
| Policy Exceptions Active | Chief Compliance Officer | ISO 27001 A.5.1 |

---

## AI Features

### Committee Briefing Generator
One-click AI-generated executive summary of the current risk appetite position — ready to paste into a board or committee report.

### AI Chat Assistant
Ask the assistant questions about the metrics, RAG status, remediation actions, or how to use the tool. The assistant has full context of the current dataset and the tool's methodology.

Powered by **Groq API (Llama 3)** — fast, free tier available.

---

## Project Structure

```
05-risk-appetite-dashboard/
├── app.py
├── README.md
├── requirements.txt
└── sample_data/
    └── metrics.json  (optional — use sidebar or upload)
```

---

## How to Run

1. Activate virtual environment:
```
source ~/GRC-Projects/venv/bin/activate
```

2. Navigate to project:
```
cd ~/GRC-Projects/05-risk-appetite-dashboard
```

3. Add your Groq API key:
```
echo 'GROQ_API_KEY=your_key_here' > .env
```

4. Run Streamlit app:
```
streamlit run app.py
```

---

## Deployment

Deploy via Streamlit Community Cloud:
- Main file: `app.py`
- Add `GROQ_API_KEY` in Streamlit Cloud → Settings → Secrets

---

## Author

Ajibola Yusuff
Governance, Risk & Compliance | ISO 27001 | ISO 42001 | CompTIA Security+
Third-Party Risk Management | AI Vendor Risk | Identity Security