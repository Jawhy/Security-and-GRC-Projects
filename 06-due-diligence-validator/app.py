import json
import os
import csv
import io
import datetime
import streamlit as st

st.set_page_config(
    page_title="Supplier Due Diligence Validator",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main { background-color: #0d1117; }
  .block-container { padding-top: 2rem; }
  .kpi-card {
    background:#161b22; border:1px solid #21262d;
    border-radius:10px; padding:20px; text-align:center;
  }
  .kpi-num  { font-size:2rem; font-weight:700; }
  .kpi-label{ font-size:.85rem; color:#8b949e; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────

MANDATORY_FIELDS = [
    "vendor_name","service_type","data_classification",
    "encryption_at_rest","encryption_in_transit","mfa_enforced",
    "incident_response_plan","bcdr_tested","penetration_test_date",
    "subprocessors_disclosed","data_residency",
    "vulnerability_management","access_control_policy","contact_name",
]

RED_RISKS = {
    "encryption_at_rest":      {"fail_values":["no","false",False],"message":"No encryption at rest","ref":"ISO 27001 A.8.24"},
    "encryption_in_transit":   {"fail_values":["no","false",False],"message":"No encryption in transit","ref":"ISO 27001 A.8.24"},
    "mfa_enforced":            {"fail_values":["no","false",False],"message":"MFA not enforced","ref":"ISO 27001 A.5.17"},
    "incident_response_plan":  {"fail_values":["no","false",False],"message":"No incident response plan","ref":"ISO 27001 A.5.26"},
    "bcdr_tested":             {"fail_values":["no","false",False],"message":"BCP/DR not tested","ref":"ISO 27001 A.5.30"},
    "subprocessors_disclosed": {"fail_values":["no","false",False],"message":"Subprocessors not disclosed","ref":"ISO 27001 A.5.19 / UK GDPR Art.28"},
    "vulnerability_management":{"fail_values":["no","false",False],"message":"No vulnerability management process","ref":"ISO 27001 A.8.8"},
    "access_control_policy":   {"fail_values":["no","false",False],"message":"No access control policy","ref":"ISO 27001 A.5.15"},
}

HIGH_RISK_JURISDICTIONS = [
    "china","prc","mainland china","hong kong",
    "russia","russian federation","ru",
    "iran","ir","north korea","dprk","kp",
    "belarus","by",
]

STATUS_ICONS     = {"Approved":"✅","Conditional":"⚠️","Reject":"❌"}
STATUS_COLORS    = {"Approved":"#2ecc71","Conditional":"#f1c40f","Reject":"#e74c3c"}


# ─── Validation Logic ─────────────────────────────────────────────────────────

def check_missing(q):
    missing = []
    for f in MANDATORY_FIELDS:
        if f not in q:
            missing.append(f)
        else:
            val = q[f]
            if val is None or val == "" or val == []:
                missing.append(f)
    return missing

def check_red(q):
    flags = []
    for field, rule in RED_RISKS.items():
        val = q.get(field)
        if isinstance(val, str): val = val.lower()
        if val in rule["fail_values"]:
            flags.append({"field":field,"message":rule["message"],"ref":rule["ref"]})
    return flags

def check_amber(q):
    flags  = []
    mat    = q.get("outsourcing_type","non-material").lower()
    is_mat = mat in ["material","critical"]

    pt = q.get("penetration_test_date","")
    if pt:
        try:
            age = (datetime.date.today() - datetime.date.fromisoformat(pt)).days
            if age > 365:
                flags.append({"field":"penetration_test_date",
                              "message":f"Pen test is {age} days old (>12 months)",
                              "ref":"ISO 27001 A.8.8 / FCA SS2/21",
                              "escalate_to_red":is_mat})
        except Exception:
            flags.append({"field":"penetration_test_date","message":"Invalid pen test date",
                          "ref":"—","escalate_to_red":False})
    else:
        flags.append({"field":"penetration_test_date","message":"No pen test date provided",
                      "ref":"ISO 27001 A.8.8","escalate_to_red":is_mat})

    if not q.get("certifications"):
        flags.append({"field":"certifications","message":"No certifications held — limited independent assurance",
                      "ref":"ISO 27001 A.5.19","escalate_to_red":False})

    residency = q.get("data_residency","").lower()
    for jr in HIGH_RISK_JURISDICTIONS:
        if jr in residency:
            flags.append({"field":"data_residency",
                          "message":f"Data residency in high-risk jurisdiction: {q.get('data_residency')}",
                          "ref":"UK GDPR Art.44 / FCA SS2/21","escalate_to_red":is_mat})
            break
    return flags

def determine_status(missing, red, amber):
    if missing or red:              return "Reject"
    if any(a.get("escalate_to_red") for a in amber): return "Reject"
    if amber:                       return "Conditional"
    return "Approved"

def build_rationale(missing, red, amber, status):
    if status == "Reject":
        reasons = []
        if missing:  reasons.append(f"{len(missing)} mandatory field(s) missing")
        if red:      reasons.append(f"{len(red)} critical control failure(s)")
        escalated = [a for a in amber if a.get("escalate_to_red")]
        if escalated: reasons.append(f"{len(escalated)} amber risk(s) escalated due to materiality")
        return "Rejected because: " + "; ".join(reasons)
    elif status == "Conditional":
        return f"Conditional because: {len(amber)} amber risk(s) require remediation"
    return "Approved: all mandatory controls satisfied"

def validate(q):
    missing  = check_missing(q)
    red      = check_red(q)
    amber    = check_amber(q)
    status   = determine_status(missing, red, amber)
    return {
        "vendor_name":    q.get("vendor_name","Unknown"),
        "service_type":   q.get("service_type","—"),
        "contact":        q.get("contact_name","—"),
        "data_class":     q.get("data_classification","—"),
        "data_residency": q.get("data_residency","—"),
        "outsourcing":    q.get("outsourcing_type","non-material").title(),
        "certifications": q.get("certifications",[]),
        "missing_fields": missing,
        "red_risks":      red,
        "amber_risks":    amber,
        "status":         status,
        "rationale":      build_rationale(missing, red, amber, status),
    }


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def sidebar_form():
    st.sidebar.markdown("## ➕ Add Supplier")
    with st.sidebar.form("q_form", clear_on_submit=True):
        name       = st.text_input("Vendor Name")
        service    = st.text_input("Service Type")
        contact    = st.text_input("Contact Name")
        data_class = st.selectbox("Data Classification",
            ["Public","Internal","Confidential","Highly Confidential"])
        residency  = st.text_input("Data Residency (e.g. United Kingdom)")
        out_type   = st.selectbox("Outsourcing Type",
            ["non-material","material","critical"])
        enc_rest   = st.selectbox("Encryption at Rest",    ["yes","no"])
        enc_trans  = st.selectbox("Encryption in Transit", ["yes","no"])
        mfa        = st.selectbox("MFA Enforced",          ["yes","no"])
        irp        = st.selectbox("Incident Response Plan",["yes","no"])
        bcdr       = st.selectbox("BCP/DR Tested",         ["yes","no"])
        sub        = st.selectbox("Subprocessors Disclosed",["yes","no"])
        vuln       = st.selectbox("Vulnerability Management",["yes","no"])
        acp        = st.selectbox("Access Control Policy", ["yes","no"])
        pt_date    = st.date_input("Last Pen Test Date",
                       value=datetime.date.today()-datetime.timedelta(days=180))
        certs      = st.multiselect("Certifications",
            ["ISO 27001","SOC 2 Type II","PCI DSS","GDPR","ISO 42001","Cyber Essentials Plus"])
        submitted  = st.form_submit_button("Validate Supplier")

    if submitted and name:
        st.session_state.questionnaires.append({
            "vendor_name":name,"service_type":service,"contact_name":contact,
            "data_classification":data_class,"data_residency":residency,
            "outsourcing_type":out_type,
            "encryption_at_rest":enc_rest,"encryption_in_transit":enc_trans,
            "mfa_enforced":mfa,"incident_response_plan":irp,"bcdr_tested":bcdr,
            "subprocessors_disclosed":sub,"vulnerability_management":vuln,
            "access_control_policy":acp,"penetration_test_date":str(pt_date),
            "certifications":certs,
        })
        st.sidebar.success(f"✓ {name} added")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if "questionnaires" not in st.session_state:
        sample = os.path.join(os.path.dirname(__file__),"sample_data","questionnaires.json")
        if os.path.exists(sample):
            with open(sample,encoding="utf-8") as f:
                st.session_state.questionnaires = json.load(f)
        else:
            st.session_state.questionnaires = []

    sidebar_form()

    st.markdown("# 🛡️ Supplier Due Diligence Validator")
    st.markdown(
        "<div style='color:#8b949e;font-size:.9rem;margin-bottom:24px'>"
        f"Assessment Date: {datetime.date.today().strftime('%d %B %Y')} &nbsp;·&nbsp; "
        "ISO 27001:2022 &nbsp;·&nbsp; FCA SS2/21 &nbsp;·&nbsp; "
        "EBA GL/2019/02 &nbsp;·&nbsp; UK GDPR Art.28</div>",
        unsafe_allow_html=True
    )

    if not st.session_state.questionnaires:
        st.info("No suppliers loaded. Add one via the sidebar or upload a questionnaires.json file.")
        return

    results = [validate(q) for q in st.session_state.questionnaires]
    sorted_r = sorted(results, key=lambda x: ["Reject","Conditional","Approved"].index(x["status"]))

    # KPIs
    st.markdown("### Assessment Dashboard")
    k1,k2,k3,k4,k5 = st.columns(5)
    for col, val, color, label in [
        (k1, len(results),                                           "#58a6ff","Total Suppliers"),
        (k2, sum(1 for r in results if r["status"]=="Reject"),       "#e74c3c","❌ Reject"),
        (k3, sum(1 for r in results if r["status"]=="Conditional"),  "#f1c40f","⚠️ Conditional"),
        (k4, sum(1 for r in results if r["status"]=="Approved"),     "#2ecc71","✅ Approved"),
        (k5, sum(len(r["red_risks"]) for r in results),              "#e74c3c","🔴 Total Red Risks"),
    ]:
        col.markdown(
            f'<div class="kpi-card"><div class="kpi-num" style="color:{color}">{val}</div>'
            f'<div class="kpi-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Validation Results","🔍 Supplier Detail","📄 Export"])

    # ── Tab 1 ──
    with tab1:
        st.markdown("#### Supplier Validation Summary")
        sf = st.multiselect("Filter by Status",["Reject","Conditional","Approved"],
                            default=["Reject","Conditional","Approved"])
        for r in [x for x in sorted_r if x["status"] in sf]:
            color = STATUS_COLORS[r["status"]]
            with st.expander(
                f"{STATUS_ICONS[r['status']]}  {r['vendor_name']}  —  {r['service_type']}  |  "
                f"{r['status']}  |  🔴 {len(r['red_risks'])}  "
                f"⚠️ {len(r['amber_risks'])}  Missing: {len(r['missing_fields'])}"
            ):
                ca, cb = st.columns(2)
                with ca:
                    st.markdown("**Supplier Overview**")
                    st.markdown(f"- **Contact:** {r['contact']}")
                    st.markdown(f"- **Outsourcing Type:** {r['outsourcing']}")
                    st.markdown(f"- **Data Classification:** {r['data_class']}")
                    st.markdown(f"- **Data Residency:** {r['data_residency']}")
                    certs = ", ".join(r["certifications"]) if r["certifications"] else "None"
                    st.markdown(f"- **Certifications:** {certs}")
                with cb:
                    st.markdown("**Assurance Status**")
                    st.markdown(
                        f"<div style='font-size:1.4rem;color:{color}'>"
                        f"{STATUS_ICONS[r['status']]} {r['status']}</div>"
                        f"<div style='color:#8b949e;font-size:.85rem;margin-top:8px'>"
                        f"{r['rationale']}</div>",
                        unsafe_allow_html=True
                    )

                if r["missing_fields"]:
                    st.error(f"**Missing Mandatory Fields ({len(r['missing_fields'])}):**")
                    for f in r["missing_fields"]:
                        st.markdown(f"- {f.replace('_',' ').title()}")

                if r["red_risks"]:
                    st.error(f"**🔴 Red Risks ({len(r['red_risks'])}):**")
                    for rk in r["red_risks"]:
                        st.markdown(f"- {rk['message']} — `{rk['ref']}`")

                escalated = [a for a in r["amber_risks"] if a.get("escalate_to_red")]
                standard  = [a for a in r["amber_risks"] if not a.get("escalate_to_red")]

                if escalated:
                    st.error(f"**🔴 Amber Escalated to Red (Material/Critical) ({len(escalated)}):**")
                    for a in escalated:
                        st.markdown(f"- {a['message']} — `{a['ref']}`")

                if standard:
                    st.warning(f"**⚠️ Amber Risks ({len(standard)}):**")
                    for a in standard:
                        st.markdown(f"- {a['message']} — `{a['ref']}`")

                if not r["missing_fields"] and not r["red_risks"] and not r["amber_risks"]:
                    st.success("✅ All mandatory controls satisfied — no risks identified")

    # ── Tab 2 ──
    with tab2:
        names    = [r["vendor_name"] for r in results]
        selected = st.selectbox("Select Supplier", names)
        r = next(x for x in results if x["vendor_name"]==selected)

        c1,c2,c3 = st.columns(3)
        c1.metric("Red Risks",     len(r["red_risks"]))
        c2.metric("Amber Risks",   len(r["amber_risks"]))
        c3.metric("Missing Fields",len(r["missing_fields"]))

        color = STATUS_COLORS[r["status"]]
        st.markdown(
            f"<div style='font-size:1.8rem;color:{color};margin:16px 0'>"
            f"{STATUS_ICONS[r['status']]} {r['status']}</div>"
            f"<div style='color:#8b949e;margin-bottom:16px'>{r['rationale']}</div>",
            unsafe_allow_html=True
        )
        st.markdown(f"**Service:** {r['service_type']}  |  **Contact:** {r['contact']}  |  **Outsourcing:** {r['outsourcing']}")
        st.markdown(f"**Data Classification:** {r['data_class']}  |  **Data Residency:** {r['data_residency']}")

        if r["certifications"]:
            st.success(f"✓ Certifications: {', '.join(r['certifications'])}")
        else:
            st.warning("No certifications held — limited independent assurance")

        if r["red_risks"]:
            st.markdown("#### 🔴 Red Risks")
            for rk in r["red_risks"]:
                st.error(f"{rk['message']} — `{rk['ref']}`")

        escalated = [a for a in r["amber_risks"] if a.get("escalate_to_red")]
        standard  = [a for a in r["amber_risks"] if not a.get("escalate_to_red")]
        if escalated:
            st.markdown("#### 🔴 Escalated Amber Risks")
            for a in escalated:
                st.error(f"{a['message']} — `{a['ref']}`")
        if standard:
            st.markdown("#### ⚠️ Amber Risks")
            for a in standard:
                st.warning(f"{a['message']} — `{a['ref']}`")

        if r["missing_fields"]:
            st.markdown("#### Missing Fields")
            for f in r["missing_fields"]:
                st.markdown(f"- {f.replace('_',' ').title()}")

    # ── Tab 3 ──
    with tab3:
        st.markdown("#### Export Reports")
        today = datetime.date.today().strftime("%d %B %Y")

        # Markdown
        lines = [
            "# Supplier Due Diligence Validation Report",
            f"**Date:** {today}  ",
            "**Framework:** ISO 27001:2022 · FCA SS2/21 · EBA GL/2019/02 · UK GDPR Art.28",
            "","---","",
            "| Status | Count |","|---|---|",
        ]
        for s in ["Reject","Conditional","Approved"]:
            lines.append(f"| {STATUS_ICONS[s]} {s} | {sum(1 for r in results if r['status']==s)} |")
        lines += ["","---",""]
        for r in sorted_r:
            lines += [
                f"### {STATUS_ICONS[r['status']]} {r['vendor_name']}",
                f"**Status:** {r['status']}  |  **Rationale:** {r['rationale']}  ",
                f"**Service:** {r['service_type']}  |  **Contact:** {r['contact']}  ","",
            ]
            if r["red_risks"]:
                lines.append("**Red Risks:**")
                lines += [f"- {rk['message']} ({rk['ref']})" for rk in r["red_risks"]]
                lines.append("")
            if r["amber_risks"]:
                lines.append("**Amber Risks:**")
                lines += [f"- {a['message']} ({a['ref']})" for a in r["amber_risks"]]
                lines.append("")
            if r["missing_fields"]:
                lines.append("**Missing Fields:**")
                lines += [f"- {f.replace('_',' ').title()}" for f in r["missing_fields"]]
            lines += ["","---",""]
        lines.append("*Generated by Supplier Due Diligence Validator — Ajibola Yusuff*")

        st.download_button(
            "⬇ Download Validation Report (Markdown)",
            data="\n".join(lines),
            file_name=f"validation_report_{datetime.date.today()}.md",
            mime="text/markdown"
        )

        # CSV
        csv_buf = io.StringIO()
        writer  = csv.DictWriter(csv_buf, fieldnames=[
            "vendor","service","outsourcing","data_class","residency",
            "red_count","amber_count","missing_count","status","rationale"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "vendor":r["vendor_name"],"service":r["service_type"],
                "outsourcing":r["outsourcing"],"data_class":r["data_class"],
                "residency":r["data_residency"],"red_count":len(r["red_risks"]),
                "amber_count":len(r["amber_risks"]),"missing_count":len(r["missing_fields"]),
                "status":r["status"],"rationale":r["rationale"],
            })
        st.download_button(
            "⬇ Download Summary (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"validation_summary_{datetime.date.today()}.csv",
            mime="text/csv"
        )

        st.download_button(
            "⬇ Download Questionnaire Data (JSON)",
            data=json.dumps(st.session_state.questionnaires, indent=2),
            file_name=f"questionnaires_{datetime.date.today()}.json",
            mime="application/json"
        )

        st.markdown("---")
        st.markdown("#### Upload Existing Data")
        uploaded = st.file_uploader("Upload questionnaires.json", type=["json"])
        if uploaded:
            try:
                data = json.load(uploaded)
                st.session_state.questionnaires = data
                st.success(f"✓ {len(data)} questionnaires loaded. Refresh to see results.")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

        st.markdown("---")
        if st.button("🗑 Clear All Suppliers"):
            st.session_state.questionnaires = []
            st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='color:#8b949e;font-size:.8rem'>"
        "Supplier Due Diligence Validator &nbsp;·&nbsp; Ajibola Yusuff &nbsp;·&nbsp; "
        "ISO 27001 | ISO 42001 | CompTIA Security+"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()