# TPRM Committee Pack
**Assessment Date:** 18 February 2026  
**Classification:** Internal — Risk Committee  
**Framework:** ISO 27001:2022 · ISO 42001:2023 · FCA SS2/21 · EBA GL/2019/02 · UK GDPR

---

## Executive Summary

This report covers the third-party risk assessment of **5 vendors**.

### Portfolio Risk Distribution

| Tier | Count |
|---|---|
| CRITICAL | 1 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 0 |

---

## Vendor Risk Register

### 🔴 InsightAI Analytics
**Service:** AI Decision Support  
**Risk Owner:** Chief Risk Officer  
**Outsourcing Type:** Critical / Material  
**Status:** In Remediation  
**Review Date:** 2026-02-15  

| Score Type | Score | Tier |
|---|---|---|
| Inherent Risk | 89/100 | CRITICAL |
| Residual Risk | 79/100 | CRITICAL |

**Flags:**
- ⚠ AI Governance Flag — ISO 42001 certification absent
- ⚠ GDPR Cross-Border Transfer Flag

**Control Domains Impacted:**
- Information Classification (ISO 27001 A.5.12 / A.8.10)
- Cross-Border Transfer Controls (UK GDPR Art.44 / ISO 27001 A.5.19)
- AI Governance & Oversight (ISO 42001 / FCA AI Principles)
- Supplier Relationship Mgmt (ISO 27001 A.5.19–A.5.22)
- Business Continuity / DR (ISO 27001 A.5.29–A.5.30)

**Evidence Required:**
- Completed Third-Party Security Questionnaire
- Business Continuity and Disaster Recovery test results (within 12 months)
- Penetration test summary (within 12 months)
- Subprocessor / fourth-party list
- Data flow and hosting architecture diagram
- ISO 27001 certificate + Statement of Applicability (SoA)
- Most recent internal audit report (or surveillance audit summary)
- AI governance pack (model cards, DPIA, evaluation results)
- Standard Contractual Clauses (SCCs) / adequacy evidence + Transfer Impact Assessment (TIA)
- Fourth-party risk management policy / subcontractor oversight evidence

---

### 🟠 DataArchive Co
**Service:** Long-Term Data Storage  
**Risk Owner:** Chief Data Officer  
**Outsourcing Type:** Material  
**Status:** Open  
**Review Date:** 2026-03-20  

| Score Type | Score | Tier |
|---|---|---|
| Inherent Risk | 61/100 | HIGH |
| Residual Risk | 61/100 | HIGH |

**Flags:**
- ⚠ GDPR Cross-Border Transfer Flag
- 🔴 Critical service in high-risk jurisdiction

**Control Domains Impacted:**
- Cross-Border Transfer Controls (UK GDPR Art.44 / ISO 27001 A.5.19)
- Business Continuity / DR (ISO 27001 A.5.29–A.5.30)

**Evidence Required:**
- Completed Third-Party Security Questionnaire
- Business Continuity and Disaster Recovery test results (within 12 months)
- Penetration test summary (within 12 months)
- Subprocessor / fourth-party list
- Data flow and hosting architecture diagram
- Standard Contractual Clauses (SCCs) / adequacy evidence + Transfer Impact Assessment (TIA)

---

### 🟠 AlphaCloud Hosting
**Service:** Cloud Infrastructure  
**Risk Owner:** Head of IT Operations  
**Outsourcing Type:** Material  
**Status:** Open  
**Review Date:** 2026-01-15  

| Score Type | Score | Tier |
|---|---|---|
| Inherent Risk | 78/100 | CRITICAL |
| Residual Risk | 60/100 | HIGH |

**Flags:**
- ⚠ GDPR Cross-Border Transfer Flag

**Control Domains Impacted:**
- Information Classification (ISO 27001 A.5.12 / A.8.10)
- Cross-Border Transfer Controls (UK GDPR Art.44 / ISO 27001 A.5.19)
- Supplier Relationship Mgmt (ISO 27001 A.5.19–A.5.22)
- Business Continuity / DR (ISO 27001 A.5.29–A.5.30)

**Evidence Required:**
- Completed Third-Party Security Questionnaire
- Business Continuity and Disaster Recovery test results (within 12 months)
- Penetration test summary (within 12 months)
- Subprocessor / fourth-party list
- Data flow and hosting architecture diagram
- ISO 27001 certificate + Statement of Applicability (SoA)
- Most recent internal audit report (or surveillance audit summary)
- SOC 2 Type II report (confirm scope + coverage period)
- Bridge letter if report is > 6 months old
- Standard Contractual Clauses (SCCs) / adequacy evidence + Transfer Impact Assessment (TIA)
- Fourth-party risk management policy / subcontractor oversight evidence

---

### 🟡 SecurePay Gateway
**Service:** Payment Processing  
**Risk Owner:** Head of Finance  
**Outsourcing Type:** Critical / Material  
**Status:** Open  
**Review Date:** 2026-06-01  

| Score Type | Score | Tier |
|---|---|---|
| Inherent Risk | 72/100 | HIGH |
| Residual Risk | 50/100 | MEDIUM |

**Control Domains Impacted:**
- Information Classification (ISO 27001 A.5.12 / A.8.10)
- Business Continuity / DR (ISO 27001 A.5.29–A.5.30)

**Evidence Required:**
- Completed Third-Party Security Questionnaire
- Business Continuity and Disaster Recovery test results (within 12 months)
- Penetration test summary (within 12 months)
- Subprocessor / fourth-party list
- Data flow and hosting architecture diagram
- ISO 27001 certificate + Statement of Applicability (SoA)
- Most recent internal audit report (or surveillance audit summary)
- PCI DSS Attestation of Compliance (AoC)
- Cardholder data environment scope diagram
- Data Processing Agreement (DPA)
- Record of Processing Activities (RoPA) extract (or equivalent evidence)

---

### 🟡 HRSoft Solutions
**Service:** HR SaaS Platform  
**Risk Owner:** HR Director  
**Outsourcing Type:** Non-Material  
**Status:** Accepted  
**Review Date:** 2026-05-10  

| Score Type | Score | Tier |
|---|---|---|
| Inherent Risk | 61/100 | HIGH |
| Residual Risk | 46/100 | MEDIUM |

**Control Domains Impacted:**
- Information Classification (ISO 27001 A.5.12 / A.8.10)
- AI Governance & Oversight (ISO 42001 / FCA AI Principles)
- Supplier Relationship Mgmt (ISO 27001 A.5.19–A.5.22)

**Evidence Required:**
- Completed Third-Party Security Questionnaire
- Business Continuity and Disaster Recovery test results (within 12 months)
- Penetration test summary (within 12 months)
- Subprocessor / fourth-party list
- Data flow and hosting architecture diagram
- ISO 27001 certificate + Statement of Applicability (SoA)
- Most recent internal audit report (or surveillance audit summary)
- ISO 42001 certificate
- AI governance documentation (model cards, oversight, change management)
- AI governance pack (model cards, DPIA, evaluation results)
- Fourth-party risk management policy / subcontractor oversight evidence

---

## Review Schedule Alerts

- ⚠ **AlphaCloud Hosting** — overdue by 34 days
- ⚠ **InsightAI Analytics** — overdue by 3 days
- ⚠ **DataArchive Co** — due in 30 days

---

## Methodology

Inherent risk scored across five weighted factors: Data Sensitivity, Hosting Location, AI Usage, Subcontractor Exposure, Service Criticality.
Residual risk adjusted by control strength reductions from verified vendor certifications.
Risk Tiers: Low (0–25) · Medium (26–50) · High (51–75) · Critical (76–100)

*Generated by TPRM Risk Scoring Engine*