# Security Incident & Vulnerability Tracker

🔗 **[Live Demo](#)** ← update after deployment

A financial and enterprise-grade security operations tool built in Python and Streamlit.

This project simulates the incident response and vulnerability management workflows used in SOC environments — tracking security incidents against SLA thresholds, managing vulnerability registers by CVSS severity, and generating committee-ready security briefings powered by AI.

---

## Overview

This tool provides a full security operations dashboard producing:

- Incident register with automatic SLA breach detection and countdown
- Vulnerability register sorted by CVSS score
- Real-time KPI dashboard — open incidents, critical items, SLA breaches
- SLA policy enforcement — Critical 4h · High 24h · Medium 72h · Low 168h
- Incident and vulnerability dossier drawer — click any record for full detail
- AI-powered security briefing generator (Groq / Llama 3)
- AI chat analyst with full incident and vulnerability context
- Markdown and CSV export for committee reporting
- Sidebar forms for live incident and vulnerability logging

---

## Regulatory & Framework Alignment

| Framework | Application Within Tool |
|-----------|-------------------------|
| ISO/IEC 27001:2022 | Control references per incident and vulnerability (A.5.26, A.8.8, A.5.15) |
| NIST CSF | Incident response and recovery alignment (RS.RP, PR.IP, PR.AC) |
| CIS Controls | Vulnerability management and patching (Controls 5, 7) |
| UK GDPR Art.33 | Data breach incident tracking and ICO notification assessment |
| OWASP Top 10 | Web application vulnerability classification |
| PCI DSS | Payment system vulnerability and TLS compliance tracking |

---

## SLA Methodology

| Severity | SLA Threshold | Breach Action |
|----------|--------------|---------------|
| Critical | 4 hours | Immediate escalation |
| High | 24 hours | Senior analyst review |
| Medium | 72 hours | Team lead notification |
| Low | 168 hours | Standard review cycle |

SLA status is calculated automatically from the incident logged date against the current time. Breached items are flagged in red on the Command Center and Incidents pages.

---

## AI Features

### Security Briefing Generator
One-click AI-generated security operations briefing covering open critical items, SLA breaches, top vulnerabilities by CVSS, and recommended priorities. Suitable for SOC team or committee reporting.

### AI Chat Analyst
Full conversational analyst with complete incident and vulnerability context loaded. Ask about SLA status, remediation priorities, CVE details, or framework guidance.

Powered by **Groq API (Llama 3)**.

---

## Project Structure

```
02-security-incident-tracker/
├── app.py
├── README.md
├── requirements.txt
├── logo.png
└── .gitignore
```

---

## How to Run

1. Activate virtual environment:
```
source ~/GRC-Projects/venv/bin/activate
```

2. Navigate to project:
```
cd ~/GRC-Projects/02-security-incident-tracker
```

3. Add Groq API key:
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

## Intended Use Case

This project demonstrates capability in:

- Security Operations Centre (SOC) workflows
- Incident response and SLA management
- Vulnerability management and CVSS prioritisation
- Security governance and committee reporting
- AI-assisted security analysis

---

## Author

Ajibola Yusuff · SentinelLabs
Governance, Risk & Compliance | ISO 27001 | ISO 42001 | CompTIA Security+ | SC-900
Third-Party Risk Management | AI Vendor Risk | Identity Security
