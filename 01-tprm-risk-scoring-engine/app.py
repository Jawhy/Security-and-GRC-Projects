import json
import os
import datetime
import io
import base64

import streamlit as st  # type: ignore
import importlib

# Import matplotlib dynamically to avoid static analysis/lint errors when the
# package is not installed in the environment (CI / lint). Use importlib so
# linters don't try to resolve matplotlib.pyplot at analysis time.
matplotlib = None
plt = None
try:
    matplotlib = importlib.import_module("matplotlib")
    matplotlib.use("Agg")
    plt = importlib.import_module("matplotlib.pyplot")
except Exception:
    # matplotlib may not be available; fallback to None and handle gracefully
    matplotlib = None
    plt = None

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TPRM Risk Scoring Engine",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ──────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  .main { background-color: #0d1117; }
  .block-container { padding-top: 2rem; }
  .kpi-card {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 10px; padding: 20px; text-align: center;
  }
  .kpi-num  { font-size: 2rem; font-weight: 700; }
  .kpi-label{ font-size: .85rem; color: #8b949e; margin-top: 4px; }
  .badge {
    display: inline-block; padding: 3px 12px;
    border-radius: 12px; font-size: .8rem; font-weight: 700;
  }
  .badge-critical{ background:#e74c3c22;color:#e74c3c;border:1px solid #e74c3c }
  .badge-high    { background:#e67e2222;color:#e67e22;border:1px solid #e67e22 }
  .badge-medium  { background:#f1c40f22;color:#f1c40f;border:1px solid #f1c40f }
  .badge-low     { background:#2ecc7122;color:#2ecc71;border:1px solid #2ecc71 }
  .flag-box {
    background:#161b22; border-radius:8px;
    padding:14px 16px; margin:8px 0;
  }
  h1 { color: #58a6ff !important; }
  .stTabs [data-baseweb="tab"] { font-size: .9rem; }
</style>
""", unsafe_allow_html=True)

# ─── Scoring Tables ───────────────────────────────────────────────────────────

DATA_SENSITIVITY = {
    "public":              {"score": 0,  "label": "Public"},
    "internal":            {"score": 10, "label": "Internal"},
    "confidential":        {"score": 20, "label": "Confidential"},
    "highly_confidential": {"score": 30, "label": "Highly Confidential"},
}
HOSTING_LOCATION = {
    "uk":        {"score": 5,  "label": "United Kingdom",        "gdpr_risk": False},
    "eu":        {"score": 5,  "label": "European Union",        "gdpr_risk": False},
    "us":        {"score": 10, "label": "United States",         "gdpr_risk": True},
    "other":     {"score": 15, "label": "Other Jurisdiction",    "gdpr_risk": True},
    "high_risk": {"score": 20, "label": "High-Risk Jurisdiction","gdpr_risk": True},
}
AI_USAGE = {
    "none":        {"score": 0,  "label": "No AI Usage"},
    "internal":    {"score": 5,  "label": "Internal AI Tools"},
    "third_party": {"score": 10, "label": "Third-Party AI"},
    "autonomous":  {"score": 15, "label": "Autonomous AI Decision-Making"},
}
SUBCONTRACTORS = {
    "none":   {"score": 0,  "label": "None"},
    "low":    {"score": 5,  "label": "1–2 Subcontractors"},
    "medium": {"score": 10, "label": "3–5 Subcontractors"},
    "high":   {"score": 15, "label": "5+ Subcontractors"},
}
SERVICE_CRITICALITY = {
    "low":      {"score": 5,  "label": "Low"},
    "medium":   {"score": 10, "label": "Medium"},
    "high":     {"score": 15, "label": "High"},
    "critical": {"score": 20, "label": "Critical"},
}
CERTIFICATIONS = {
    "iso_27001":        {"reduction": 10, "label": "ISO 27001:2022"},
    "soc2_type2":       {"reduction": 8,  "label": "SOC 2 Type II"},
    "pci_dss":          {"reduction": 7,  "label": "PCI DSS"},
    "gdpr":             {"reduction": 5,  "label": "GDPR Compliance"},
    "iso_42001":        {"reduction": 5,  "label": "ISO 42001 (AI Governance)"},
    "cyber_essentials": {"reduction": 3,  "label": "Cyber Essentials Plus"},
}
OUTSOURCING_LABELS = {
    "non-material": "Non-Material",
    "material":     "Material",
    "critical":     "Critical / Material",
}
CONTROL_DOMAIN_MAP = {
    "data_sensitivity":    {"domain": "Information Classification",     "ref": "ISO 27001 A.5.12 / A.8.10"},
    "hosting_location":    {"domain": "Cross-Border Transfer Controls", "ref": "UK GDPR Art.44 / A.5.19"},
    "ai_usage":            {"domain": "AI Governance & Oversight",      "ref": "ISO 42001 / FCA AI Principles"},
    "subcontractors":      {"domain": "Supplier Relationship Mgmt",     "ref": "ISO 27001 A.5.19–A.5.22"},
    "service_criticality": {"domain": "Business Continuity / DR",       "ref": "ISO 27001 A.5.29–A.5.30"},
}
EVIDENCE_MAP = {
    "iso_27001":  ["ISO 27001 certificate + Statement of Applicability (SoA)", "Most recent internal audit report"],
    "soc2_type2": ["SOC 2 Type II report (confirm scope + coverage period)", "Bridge letter if report > 6 months old"],
    "pci_dss":    ["PCI DSS Attestation of Compliance (AoC)", "Cardholder data environment scope diagram"],
    "gdpr":       ["Data Processing Agreement (DPA)", "Record of Processing Activities (RoPA) extract"],
    "iso_42001":  ["ISO 42001 certificate", "AI governance documentation (model cards, oversight, change management)"],
}
BASE_EVIDENCE = [
    "Completed Third-Party Security Questionnaire",
    "Business Continuity and Disaster Recovery test results (within 12 months)",
    "Penetration test summary (within 12 months)",
    "Subprocessor / fourth-party list",
    "Data flow and hosting architecture diagram",
]
AI_DUE_DILIGENCE = [
    "Training data provenance documented and approved?",
    "Prompt injection and adversarial attack controls in place?",
    "Model update and change management process defined?",
    "Human oversight mechanism for automated decisions?",
    "AI system logs retained for audit purposes?",
    "Data retention, deletion and minimisation controls?",
    "Subprocessors used for AI training or inference disclosed?",
    "Bias and fairness evaluation results available?",
]
MAX_INHERENT = 90
TIER_COLORS = {"LOW":"#2ecc71","MEDIUM":"#f1c40f","HIGH":"#e67e22","CRITICAL":"#e74c3c"}
TIER_ICONS  = {"LOW":"🟢","MEDIUM":"🟡","HIGH":"🟠","CRITICAL":"🔴"}

# ─── Core Logic ───────────────────────────────────────────────────────────────

def get_risk_tier(score):
    if score <= 25:   return "LOW"
    elif score <= 50: return "MEDIUM"
    elif score <= 75: return "HIGH"
    else:             return "CRITICAL"

def calculate_scores(vendor):
    raw = (
        DATA_SENSITIVITY.get(vendor.get("data_sensitivity",""),{}).get("score",0) +
        HOSTING_LOCATION.get(vendor.get("hosting_location",""),{}).get("score",0) +
        AI_USAGE.get(vendor.get("ai_usage",""),{}).get("score",0) +
        SUBCONTRACTORS.get(vendor.get("subcontractors",""),{}).get("score",0) +
        SERVICE_CRITICALITY.get(vendor.get("service_criticality",""),{}).get("score",0)
    )
    inherent  = round((raw / MAX_INHERENT) * 100)
    reduction = sum(CERTIFICATIONS[c]["reduction"] for c in vendor.get("certifications",[]) if c in CERTIFICATIONS)
    return inherent, max(0, inherent - reduction)

def get_evidence_required(vendor):
    ev = list(BASE_EVIDENCE)
    for c in vendor.get("certifications",[]):
        ev.extend(EVIDENCE_MAP.get(c,[]))
    if vendor.get("ai_usage") in ["third_party","autonomous"]:
        ev.append("AI governance pack (model cards, DPIA, evaluation results)")
    if HOSTING_LOCATION.get(vendor.get("hosting_location",""),{}).get("gdpr_risk"):
        ev.append("Standard Contractual Clauses (SCCs) / adequacy evidence + Transfer Impact Assessment (TIA)")
    if vendor.get("subcontractors") in ["medium","high"]:
        ev.append("Fourth-party risk management policy")
    seen, out = set(), []
    for i in ev:
        if i not in seen: seen.add(i); out.append(i)
    return out

def get_control_domains(vendor):
    domains = []
    checks = [
        ("data_sensitivity",    DATA_SENSITIVITY,    20),
        ("hosting_location",    HOSTING_LOCATION,    10),
        ("ai_usage",            AI_USAGE,            10),
        ("subcontractors",      SUBCONTRACTORS,      10),
        ("service_criticality", SERVICE_CRITICALITY, 15),
    ]
    for field, table, threshold in checks:
        if table.get(vendor.get(field,""),{}).get("score",0) >= threshold:
            domains.append(CONTROL_DOMAIN_MAP[field])
    return domains

def days_until(date_str):
    try:
        return (datetime.date.fromisoformat(date_str) - datetime.date.today()).days
    except Exception:
        return None

def assess_vendor(vendor):
    inherent, residual = calculate_scores(vendor)
    certs    = vendor.get("certifications",[])
    ai_flag  = vendor.get("ai_usage") in ["third_party","autonomous"] and "iso_42001" not in certs
    gdpr_flag= HOSTING_LOCATION.get(vendor.get("hosting_location",""),{}).get("gdpr_risk",False)
    days     = days_until(vendor.get("review_date",""))
    return {
        "name":             vendor.get("vendor_name","Unknown"),
        "service":          vendor.get("service_type","—"),
        "inherent_score":   inherent,
        "inherent_tier":    get_risk_tier(inherent),
        "residual_score":   residual,
        "residual_tier":    get_risk_tier(residual),
        "ai_flag":          ai_flag,
        "gdpr_flag":        gdpr_flag,
        "critical_jurisdiction": vendor.get("service_criticality")=="critical" and vendor.get("hosting_location")=="high_risk",
        "certifications":   certs,
        "data_sensitivity": DATA_SENSITIVITY.get(vendor.get("data_sensitivity",""),{}).get("label","—"),
        "hosting":          HOSTING_LOCATION.get(vendor.get("hosting_location",""),{}).get("label","—"),
        "ai_usage_label":   AI_USAGE.get(vendor.get("ai_usage",""),{}).get("label","—"),
        "subcontractors":   SUBCONTRACTORS.get(vendor.get("subcontractors",""),{}).get("label","—"),
        "criticality":      SERVICE_CRITICALITY.get(vendor.get("service_criticality",""),{}).get("label","—"),
        "outsourcing_type": OUTSOURCING_LABELS.get(vendor.get("outsourcing_type",""),vendor.get("outsourcing_type","—")),
        "risk_owner":       vendor.get("risk_owner","—"),
        "review_date":      vendor.get("review_date","—"),
        "review_days":      days,
        "review_overdue":   days is not None and days < 0,
        "review_due_soon":  days is not None and 0 <= days <= 30,
        "status":           vendor.get("status","—"),
        "evidence_required":get_evidence_required(vendor),
        "control_domains":  get_control_domains(vendor),
    }

# ─── Chart Helpers ────────────────────────────────────────────────────────────

STYLE = {"bg":"#0d1117","text":"#e6edf3","grid":"#21262d"}

def _apply_style():
    plt.rcParams.update({"text.color":STYLE["text"],"axes.labelcolor":STYLE["text"],
                          "xtick.color":STYLE["text"],"ytick.color":STYLE["text"]})

def chart_donut(results):
    _apply_style()
    tiers = ["CRITICAL","HIGH","MEDIUM","LOW"]
    data  = [(t, sum(1 for r in results if r["residual_tier"]==t), TIER_COLORS[t]) for t in tiers]
    data  = [(t,c,col) for t,c,col in data if c > 0]
    if not data: return None
    fig, ax = plt.subplots(figsize=(5,5), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    _, texts, autotexts = ax.pie(
        [d[1] for d in data], labels=[d[0] for d in data],
        colors=[d[2] for d in data], autopct="%1.0f%%", startangle=90,
        wedgeprops={"width":0.5,"edgecolor":STYLE["bg"],"linewidth":2},
        textprops={"color":STYLE["text"],"fontsize":11},
    )
    for at in autotexts: at.set_color(STYLE["bg"]); at.set_fontweight("bold")
    ax.set_title("Residual Risk Distribution", color=STYLE["text"], fontsize=13, pad=15)
    return fig

def chart_bars(results):
    _apply_style()
    fig, ax = plt.subplots(figsize=(10,5), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    x     = list(range(len(results)))
    names = [r["name"].replace(" ","\n") for r in results]
    ax.bar([i-0.2 for i in x], [r["inherent_score"] for r in results],
           width=0.35, label="Inherent", color="#5b8dd9", alpha=0.85)
    ax.bar([i+0.2 for i in x], [r["residual_score"] for r in results],
           width=0.35, label="Residual",
           color=[TIER_COLORS[r["residual_tier"]] for r in results], alpha=0.9)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("Risk Score (0–100)"); ax.set_ylim(0,115)
    ax.axhline(75, color=TIER_COLORS["CRITICAL"], linestyle="--", linewidth=0.8, alpha=0.5, label="Critical threshold")
    ax.axhline(50, color=TIER_COLORS["HIGH"],     linestyle="--", linewidth=0.8, alpha=0.5, label="High threshold")
    ax.legend(facecolor=STYLE["bg"], labelcolor=STYLE["text"], framealpha=0.5)
    ax.set_title("Inherent vs Residual Risk by Vendor", color=STYLE["text"], fontsize=13, pad=12)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(STYLE["grid"])
    ax.yaxis.grid(True, color=STYLE["grid"], linewidth=0.5); ax.set_axisbelow(True)
    fig.tight_layout(); return fig

def chart_heatmap(results, vendors):
    _apply_style()
    keys   = ["data_sensitivity","hosting_location","ai_usage","subcontractors","service_criticality"]
    tables = [DATA_SENSITIVITY,HOSTING_LOCATION,AI_USAGE,SUBCONTRACTORS,SERVICE_CRITICALITY]
    labels = ["Data\nSensitivity","Hosting\nLocation","AI\nUsage","Subcontractors","Service\nCriticality"]
    names  = [v.get("vendor_name","?") for v in vendors]
    matrix = []
    for v in vendors:
        row = []
        for k, tbl in zip(keys, tables):
            s   = tbl.get(v.get(k,""),{}).get("score",0)
            mx  = max(t["score"] for t in tbl.values()) or 1
            row.append(s/mx)
        matrix.append(row)
    fig, ax = plt.subplots(figsize=(9,4), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    im = ax.imshow(matrix, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, fontsize=9)
    ax.set_yticks(range(len(names)));  ax.set_yticklabels(names, fontsize=9)
    for i in range(len(names)):
        for j in range(len(labels)):
            val = matrix[i][j]
            ax.text(j,i,f"{val:.0%}",ha="center",va="center",fontsize=8,fontweight="bold",
                    color="black" if 0.3 < val < 0.8 else STYLE["text"])
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.ax.yaxis.set_tick_params(color=STYLE["text"])
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=STYLE["text"])
    ax.set_title("Risk Factor Heatmap (Normalised per Factor)", color=STYLE["text"], fontsize=12, pad=12)
    fig.tight_layout(); return fig

def badge_html(tier):
    return f'<span class="badge badge-{tier.lower()}">{TIER_ICONS[tier]} {tier}</span>'

# ─── Sidebar — Vendor Input Form ──────────────────────────────────────────────

def sidebar_form():
    st.sidebar.markdown("## ➕ Add a Vendor")
    with st.sidebar.form("vendor_form", clear_on_submit=True):
        name     = st.text_input("Vendor Name")
        service  = st.text_input("Service Type")
        ds       = st.selectbox("Data Sensitivity",  list(DATA_SENSITIVITY.keys()),
                                format_func=lambda k: DATA_SENSITIVITY[k]["label"])
        hl       = st.selectbox("Hosting Location",  list(HOSTING_LOCATION.keys()),
                                format_func=lambda k: HOSTING_LOCATION[k]["label"])
        ai       = st.selectbox("AI Usage",          list(AI_USAGE.keys()),
                                format_func=lambda k: AI_USAGE[k]["label"])
        sub      = st.selectbox("Subcontractors",    list(SUBCONTRACTORS.keys()),
                                format_func=lambda k: SUBCONTRACTORS[k]["label"])
        crit     = st.selectbox("Service Criticality",list(SERVICE_CRITICALITY.keys()),
                                format_func=lambda k: SERVICE_CRITICALITY[k]["label"])
        out_type = st.selectbox("Outsourcing Type",  list(OUTSOURCING_LABELS.keys()),
                                format_func=lambda k: OUTSOURCING_LABELS[k])
        certs    = st.multiselect("Certifications Held",list(CERTIFICATIONS.keys()),
                                  format_func=lambda k: CERTIFICATIONS[k]["label"])
        owner    = st.text_input("Risk Owner")
        rev_date = st.date_input("Next Review Date", value=datetime.date.today() + datetime.timedelta(days=90))
        status   = st.selectbox("Status", ["Open","In Remediation","Accepted","Closed"])
        submitted= st.form_submit_button("Add Vendor")

    if submitted and name:
        vendor = {
            "vendor_name":        name,
            "service_type":       service,
            "data_sensitivity":   ds,
            "hosting_location":   hl,
            "ai_usage":           ai,
            "subcontractors":     sub,
            "service_criticality":crit,
            "outsourcing_type":   out_type,
            "certifications":     certs,
            "risk_owner":         owner,
            "review_date":        str(rev_date),
            "status":             status,
        }
        st.session_state.vendors.append(vendor)
        st.sidebar.success(f"✓ {name} added")

# ─── Main App ─────────────────────────────────────────────────────────────────

def main():
    # Initialise session state
    if "vendors" not in st.session_state:
        # Load sample data if available
        sample = os.path.join(os.path.dirname(__file__), "sample_data", "vendors.json")
        if os.path.exists(sample):
            with open(sample, encoding="utf-8") as f:
                st.session_state.vendors = json.load(f)
        else:
            st.session_state.vendors = []

    sidebar_form()

    # Header
    st.markdown("# 🔐 TPRM Risk Scoring Engine")
    st.markdown(
        "<div style='color:#8b949e;font-size:.9rem;margin-bottom:24px'>"
        f"Assessment Date: {datetime.date.today().strftime('%d %B %Y')} &nbsp;·&nbsp; "
        "ISO 27001:2022 &nbsp;·&nbsp; ISO 42001:2023 &nbsp;·&nbsp; "
        "FCA SS2/21 &nbsp;·&nbsp; EBA GL/2019/02 &nbsp;·&nbsp; UK GDPR"
        "</div>",
        unsafe_allow_html=True
    )

    if not st.session_state.vendors:
        st.info("No vendors loaded. Add a vendor using the sidebar, or add a sample_data/vendors.json file.")
        return

    vendors = st.session_state.vendors
    results = [assess_vendor(v) for v in vendors]
    sorted_results = sorted(results, key=lambda x: x["residual_score"], reverse=True)

    # ── KPI Dashboard ──
    st.markdown("### Portfolio KPI Dashboard")
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    kpis = [
        (k1, len(results),                                               "#58a6ff", "Total Vendors"),
        (k2, sum(1 for r in results if r["residual_tier"]=="CRITICAL"),  "#e74c3c", "Critical"),
        (k3, sum(1 for r in results if r["residual_tier"]=="HIGH"),      "#e67e22", "High Risk"),
        (k4, sum(1 for r in results if r["review_overdue"]),             "#f1c40f", "Overdue Reviews"),
        (k5, sum(1 for r in results if r["ai_flag"]),                    "#f1c40f", "AI Flags 🤖"),
        (k6, sum(1 for r in results if r["gdpr_flag"]),                  "#e74c3c", "GDPR Flags 🌍"),
    ]
    for col, val, color, label in kpis:
        col.markdown(
            f'<div class="kpi-card"><div class="kpi-num" style="color:{color}">{val}</div>'
            f'<div class="kpi-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Charts", "📋 Risk Register", "🔍 Vendor Detail", "📄 Export"])

    # ── Tab 1: Charts ──
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            fig = chart_donut(results)
            if fig: st.pyplot(fig)
        with c2:
            fig = chart_bars(results)
            if fig: st.pyplot(fig)
        fig = chart_heatmap(results, vendors)
        if fig: st.pyplot(fig)

    # ── Tab 2: Risk Register ──
    with tab2:
        st.markdown("#### Third-Party Vendor Risk Register")

        # Filters
        fc1, fc2 = st.columns(2)
        tier_filter   = fc1.multiselect("Filter by Risk Tier", ["CRITICAL","HIGH","MEDIUM","LOW"],
                                         default=["CRITICAL","HIGH","MEDIUM","LOW"])
        status_filter = fc2.multiselect("Filter by Status", ["Open","In Remediation","Accepted","Closed"],
                                         default=["Open","In Remediation","Accepted","Closed"])

        filtered = [r for r in sorted_results
                    if r["residual_tier"] in tier_filter and r["status"] in status_filter]

        for r in filtered:
            rd_str = r["review_date"]
            if r["review_overdue"]:   rd_str += " ⚠ OVERDUE"
            elif r["review_due_soon"]:rd_str += f" ⚠ ({r['review_days']}d)"
            flags = ("🤖 " if r["ai_flag"] else "") + ("🌍 " if r["gdpr_flag"] else "") + ("🔴" if r["critical_jurisdiction"] else "")

            with st.expander(
                f"{TIER_ICONS[r['residual_tier']]}  {r['name']}  —  "
                f"Residual: {r['residual_score']}  |  {r['residual_tier']}  |  {r['status']}  {flags}"
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Risk Factor Breakdown**")
                    st.table({
                        "Factor": ["Data Sensitivity","Hosting Location","AI Usage","Subcontractors","Criticality","Outsourcing"],
                        "Value":  [r["data_sensitivity"],r["hosting"],r["ai_usage_label"],
                                   r["subcontractors"],r["criticality"],r["outsourcing_type"]],
                    })
                with col_b:
                    st.markdown("**Risk Scores**")
                    st.markdown(
                        f"Inherent: **{r['inherent_score']}/100** &nbsp; {badge_html(r['inherent_tier'])}<br>"
                        f"Residual: **{r['residual_score']}/100** &nbsp; {badge_html(r['residual_tier'])}",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**Risk Owner:** {r['risk_owner']}")
                    st.markdown(f"**Review Date:** {rd_str}")

                if r["ai_flag"]:
                    st.warning("⚠ AI VENDOR FLAG — ISO 42001 certification absent")
                    with st.expander("AI Enhanced Due Diligence Checklist"):
                        for q in AI_DUE_DILIGENCE:
                            st.markdown(f"- ☐ {q}")
                if r["gdpr_flag"]:
                    st.error("⚠ GDPR Cross-Border Transfer Flag — Validate SCCs / adequacy decision")
                if r["critical_jurisdiction"]:
                    st.error("🔴 Critical service in high-risk jurisdiction — Escalate to Risk Committee")

                if r["control_domains"]:
                    st.markdown("**Control Domains Impacted**")
                    for d in r["control_domains"]:
                        st.markdown(f"- {d['domain']} — `{d['ref']}`")

                st.markdown("**Evidence Required**")
                for i, e in enumerate(r["evidence_required"], 1):
                    st.markdown(f"{i}. {e}")

        # Overdue alerts
        overdue  = [r for r in results if r["review_overdue"]]
        due_soon = [r for r in results if r["review_due_soon"]]
        if overdue or due_soon:
            st.markdown("---")
            st.markdown("#### ⚠ Review Schedule Alerts")
            for r in overdue:
                st.error(f"**{r['name']}** — review overdue by {abs(r['review_days'])} days")
            for r in due_soon:
                st.warning(f"**{r['name']}** — review due in {r['review_days']} days")

    # ── Tab 3: Vendor Detail ──
    with tab3:
        vendor_names = [r["name"] for r in results]
        selected = st.selectbox("Select Vendor", vendor_names)
        r = next(x for x in results if x["name"] == selected)

        col1, col2, col3 = st.columns(3)
        col1.metric("Inherent Risk", f"{r['inherent_score']}/100", r["inherent_tier"])
        col2.metric("Residual Risk", f"{r['residual_score']}/100", r["residual_tier"])
        col3.metric("Risk Owner", r["risk_owner"])

        st.markdown(f"**Service:** {r['service']}  |  **Outsourcing:** {r['outsourcing_type']}  |  **Status:** {r['status']}")
        st.markdown(f"**Review Date:** {r['review_date']}")

        if r["certifications"]:
            cert_labels = [CERTIFICATIONS[c]["label"] for c in r["certifications"] if c in CERTIFICATIONS]
            st.success(f"✓ Certifications: {', '.join(cert_labels)}")
        else:
            st.error("✗ No certifications held — no residual risk reduction applied")

        if r["ai_flag"]:   st.warning("⚠ AI Governance Flag — ISO 42001 certification absent")
        if r["gdpr_flag"]: st.error("⚠ GDPR Cross-Border Transfer Flag")
        if r["critical_jurisdiction"]: st.error("🔴 Critical service in high-risk jurisdiction")

        st.markdown("**Evidence Required for Assurance Review**")
        for i, e in enumerate(r["evidence_required"], 1):
            st.markdown(f"{i}. {e}")

    # ── Tab 4: Export ──
    with tab4:
        st.markdown("#### Export Reports")

        today = datetime.date.today().strftime("%d %B %Y")

        # Markdown committee report
        lines = [
            "# TPRM Committee Pack",
            f"**Assessment Date:** {today}  ",
            "**Classification:** Internal — Risk Committee  ",
            "**Framework:** ISO 27001:2022 · ISO 42001:2023 · FCA SS2/21 · EBA GL/2019/02 · UK GDPR",
            "","---","","## Executive Summary","",
            f"Third-party risk assessment of **{len(results)} vendors**.", "",
            "| Tier | Count |","|---|---|",
        ]
        for t in ["CRITICAL","HIGH","MEDIUM","LOW"]:
            lines.append(f"| {t} | {sum(1 for r in results if r['residual_tier']==t)} |")
        lines += ["","---","","## Vendor Risk Register",""]
        for r in sorted_results:
            lines += [
                f"### {TIER_ICONS[r['residual_tier']]} {r['name']}",
                f"**Residual Risk:** {r['residual_score']}/100 — {r['residual_tier']}  ",
                f"**Inherent Risk:** {r['inherent_score']}/100  ",
                f"**Risk Owner:** {r['risk_owner']}  ",
                f"**Review Date:** {r['review_date']}  ",
                f"**Status:** {r['status']}  ","",
            ]
            if r["ai_flag"]:   lines.append("⚠ AI Governance Flag — ISO 42001 absent")
            if r["gdpr_flag"]: lines.append("⚠ GDPR Cross-Border Transfer Flag")
            lines += ["","**Evidence Required:**"]
            lines += [f"- {e}" for e in r["evidence_required"]]
            lines += ["","---",""]
        lines += ["*Generated by TPRM Risk Scoring Engine — Ajibola Yusuff*"]
        md_content = "\n".join(lines)

        st.download_button(
            label="⬇ Download Committee Pack (Markdown)",
            data=md_content,
            file_name=f"tprm_committee_pack_{datetime.date.today()}.md",
            mime="text/markdown"
        )

        # JSON export
        st.download_button(
            label="⬇ Download Vendor Data (JSON)",
            data=json.dumps(vendors, indent=2),
            file_name=f"tprm_vendors_{datetime.date.today()}.json",
            mime="application/json"
        )

        st.markdown("---")
        st.markdown("#### Upload Existing Vendor Data")
        uploaded = st.file_uploader("Upload vendors.json", type=["json"])
        if uploaded:
            try:
                data = json.load(uploaded)
                st.session_state.vendors = data
                st.success(f"✓ {len(data)} vendors loaded successfully. Refresh the page to see results.")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

        st.markdown("---")
        st.markdown("#### Clear All Vendors")
        if st.button("🗑 Clear All Vendors"):
            st.session_state.vendors = []
            st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='color:#8b949e;font-size:.8rem'>"
        "TPRM Risk Scoring Engine &nbsp;·&nbsp; Ajibola Yusuff &nbsp;·&nbsp; "
        "ISO 27001 | ISO 42001 | CompTIA Security+"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()