import os
import json
import csv
import io
import datetime

try:
    import streamlit as st
except ModuleNotFoundError:
    import sys
    import subprocess
    print("streamlit not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    import streamlit as st

try:
    import matplotlib.pyplot as plt
    plt.switch_backend("Agg")
except ModuleNotFoundError:
    try:
        try:
            import streamlit as st
        except ModuleNotFoundError:
            import sys
            print("streamlit is not installed. Please install it with 'pip install streamlit'.")
            sys.exit(1)
    except ModuleNotFoundError:
        import sys
        print("streamlit is not installed. Please install it with 'pip install streamlit'.")
        sys.exit(1)
    st.error("matplotlib is not installed. Please install it with 'pip install matplotlib'.")
    import sys
    sys.exit(1)

try:
    from groq import Groq
except ModuleNotFoundError:
    import sys
    import subprocess
    print("groq not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "groq"])
    from groq import Groq
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Risk Appetite & Metrics Dashboard",
    page_icon="🎯",
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
  .chat-msg-user { background:#1f2937; border-radius:8px; padding:10px 14px; margin:6px 0; }
  .chat-msg-ai   { background:#161b22; border:1px solid #21262d; border-radius:8px; padding:10px 14px; margin:6px 0; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────

RAG_COLORS       = {"Red":"#e74c3c","Amber":"#f1c40f","Green":"#2ecc71"}
RAG_ICONS        = {"Red":"🔴","Amber":"🟡","Green":"🟢"}
STYLE            = {"bg":"#0d1117","text":"#e6edf3","grid":"#21262d"}
HIGHER_IS_BETTER = ["BCP Tests Completed","Security Awareness Completion"]

FRAMEWORKS = {
    "Regulatory Breach Count":        "FCA SYSC 6.1 / ISO 27001 A.5.26",
    "Third-Party High Risk Vendors":  "FCA SS2/21 / ISO 27001 A.5.19",
    "Overdue Risk Reviews":           "ISO 27001 A.6.1 / FCA SYSC 4",
    "Critical Vulnerabilities Open":  "ISO 27001 A.8.8 / NIST CSF",
    "Data Subject Complaints":        "UK GDPR Art.57 / ICO",
    "AI Model Incidents":             "ISO 42001 / FCA AI Principles",
    "BCP Tests Completed":            "ISO 27001 A.5.30 / FCA SYSC 4",
    "Security Awareness Completion":  "ISO 27001 A.6.3",
    "Audit Findings Open":            "ISO 27001 A.9 / FCA SYSC",
    "Policy Exceptions Active":       "ISO 27001 A.5.1",
}

README_CONTEXT = """
This is the Risk Appetite & Metrics Dashboard — a compliance risk monitoring tool built for financial services.

It tracks key risk indicators against defined appetite and tolerance thresholds.
RAG status: Green = within appetite, Amber = between appetite and tolerance, Red = tolerance breached.
Metrics include: Regulatory Breaches, Third-Party Risk, Vulnerabilities, AI Incidents, BCP Tests, GDPR Complaints, Audit Findings, Policy Exceptions.
Frameworks: ISO 27001:2022, FCA SYSC, UK GDPR, ISO 42001:2023, NIST CSF.
Users can add/update metrics via the sidebar, upload JSON metric sets, and export Markdown/CSV reports.
The tool detects worsening vs improving trends and escalates breaches to committee attention.
"""

DEFAULT_METRICS = [
    {"metric":"Regulatory Breach Count",      "current":2, "appetite":1,"tolerance":3, "unit":"count","period":"Q1 2026","owner":"Chief Compliance Officer","action":"Review compliance calendar and close open items","history":[0,1,1,2]},
    {"metric":"Third-Party High Risk Vendors", "current":4, "appetite":3,"tolerance":5, "unit":"count","period":"Q1 2026","owner":"Head of TPRM","action":"Increase assessment frequency for critical suppliers","history":[2,3,3,4]},
    {"metric":"Overdue Risk Reviews",          "current":7, "appetite":5,"tolerance":8, "unit":"count","period":"Q1 2026","owner":"Chief Risk Officer","action":"Allocate additional review capacity in Q2","history":[3,4,6,7]},
    {"metric":"Critical Vulnerabilities Open", "current":12,"appetite":5,"tolerance":10,"unit":"count","period":"Q1 2026","owner":"CISO","action":"Prioritise patching sprint for critical CVEs","history":[8,9,10,12]},
    {"metric":"Data Subject Complaints",       "current":3, "appetite":2,"tolerance":5, "unit":"count","period":"Q1 2026","owner":"DPO","action":"Review complaint handling SLAs","history":[1,2,2,3]},
    {"metric":"AI Model Incidents",            "current":1, "appetite":0,"tolerance":2, "unit":"count","period":"Q1 2026","owner":"Chief Risk Officer","action":"Conduct post-incident review and update AI governance controls","history":[0,0,1,1]},
    {"metric":"BCP Tests Completed",           "current":3, "appetite":4,"tolerance":3, "unit":"count","period":"Q1 2026","owner":"COO","action":"Schedule outstanding BCP exercises before Q2 end","history":[2,3,3,3]},
    {"metric":"Security Awareness Completion", "current":82,"appetite":90,"tolerance":75,"unit":"%",    "period":"Q1 2026","owner":"CISO","action":"Issue reminder communications to outstanding staff","history":[70,75,80,82]},
    {"metric":"Audit Findings Open",           "current":6, "appetite":4,"tolerance":8, "unit":"count","period":"Q1 2026","owner":"Head of Internal Audit","action":"Agree remediation deadlines with finding owners","history":[3,4,5,6]},
    {"metric":"Policy Exceptions Active",      "current":2, "appetite":2,"tolerance":4, "unit":"count","period":"Q1 2026","owner":"Chief Compliance Officer","action":"Review and time-limit all active exceptions","history":[1,1,2,2]},
]

# ─── Core Logic ───────────────────────────────────────────────────────────────

def get_rag(metric, value, appetite, tolerance):
    if metric in HIGHER_IS_BETTER:
        if value >= appetite:    return "Green"
        elif value >= tolerance: return "Amber"
        else:                    return "Red"
    else:
        if value <= appetite:    return "Green"
        elif value <= tolerance: return "Amber"
        else:                    return "Red"

def assess_metric(m):
    rag = get_rag(m["metric"], m["current"], m["appetite"], m["tolerance"])
    hib = m["metric"] in HIGHER_IS_BETTER
    breach = (m["current"] < m["tolerance"]) if hib else (m["current"] > m["tolerance"])
    trend_dir = None
    hist = m.get("history", [])
    if hist:
        last = hist[-1]
        if hib:
            trend_dir = "improving" if m["current"] >= last else "worsening"
        else:
            trend_dir = "improving" if m["current"] <= last else "worsening"
    period_change = round(m["current"] - hist[-1], 2) if hist else None
    return {**m, "rag":rag, "breach":breach, "trend":trend_dir, "period_change":period_change}

def validate_thresholds(metric, appetite, tolerance):
    hib = metric in HIGHER_IS_BETTER
    if not hib and tolerance < appetite:
        return "Tolerance must be ≥ Appetite for 'lower is better' metrics."
    if hib and appetite < tolerance:
        return "For 'higher is better' metrics, Appetite must be ≥ Tolerance."
    return None

def build_metrics_context(results):
    lines = ["Current Risk Appetite Metrics:"]
    for r in results:
        change_str = ""
        if r.get("period_change") is not None:
            arrow = "▲" if r["period_change"] > 0 else "▼" if r["period_change"] < 0 else "→"
            change_str = f" ({arrow}{abs(r['period_change'])} vs last period)"
        lines.append(
            f"- {r['metric']}: {r['current']}{r['unit']}{change_str} | "
            f"Appetite: {r['appetite']} | Tolerance: {r['tolerance']} | "
            f"RAG: {r['rag']} | Trend: {r.get('trend','—')} | "
            f"Owner: {r.get('owner','—')} | Action: {r.get('action','—')}"
        )
    return "\n".join(lines)

# ─── Groq AI ──────────────────────────────────────────────────────────────────

def get_groq_client():
    key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY","")
    if not key:
        return None
    return Groq(api_key=key)

def ai_committee_briefing(results):
    client = get_groq_client()
    if not client:
        return "⚠ Groq API key not configured."
    metrics_ctx = build_metrics_context(results)
    prompt = f"""
{README_CONTEXT}

{metrics_ctx}

Write a concise, professional committee briefing paragraph (max 150 words) summarising the current risk appetite position.
Include: overall RAG summary, key breaches requiring escalation, notable trends, and recommended committee actions.
Write in formal financial services governance language suitable for a board or risk committee pack.
"""
    try:
        resp = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role":"user","content":prompt}],
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating briefing: {e}"

def ai_chat_response(user_msg, results, history):
    client = get_groq_client()
    if not client:
        return "⚠ Groq API key not configured. Add GROQ_API_KEY to your .env or Streamlit secrets."
    metrics_ctx = build_metrics_context(results)
    system = f"""
You are an expert GRC (Governance, Risk and Compliance) assistant embedded in the Risk Appetite & Metrics Dashboard.

{README_CONTEXT}

{metrics_ctx}

Help users understand:
- What each metric means and why it matters
- What RAG status means and what actions to take
- How to use the dashboard features
- Regulatory context (ISO 27001, FCA SYSC, UK GDPR, ISO 42001)
- Remediation advice for breached metrics

Be concise, professional, and practical. Use plain English.
"""
    messages = [{"role":"system","content":system}]
    for h in history[-6:]:
        messages.append({"role":"user","content":h["user"]})
        messages.append({"role":"assistant","content":h["assistant"]})
    messages.append({"role":"user","content":user_msg})
    try:
        resp = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            max_tokens=400,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# ─── Charts ───────────────────────────────────────────────────────────────────

def _apply_style():
    plt.rcParams.update({
        "text.color":STYLE["text"],"axes.labelcolor":STYLE["text"],
        "xtick.color":STYLE["text"],"ytick.color":STYLE["text"],
    })

def chart_rag_summary(results):
    _apply_style()
    counts   = {s: sum(1 for r in results if r["rag"]==s) for s in ["Red","Amber","Green"]}
    non_zero = [(s,c,RAG_COLORS[s]) for s,c in counts.items() if c > 0]
    fig, ax  = plt.subplots(figsize=(5,5), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    if non_zero:
        _, _, autotexts = ax.pie(
            [x[1] for x in non_zero], labels=[x[0] for x in non_zero],
            colors=[x[2] for x in non_zero], autopct="%1.0f%%", startangle=90,
            wedgeprops={"width":0.5,"edgecolor":STYLE["bg"],"linewidth":2},
            textprops={"color":STYLE["text"],"fontsize":11},
        )
        for at in autotexts: at.set_color(STYLE["bg"]); at.set_fontweight("bold")
    ax.set_title("RAG Status Distribution", color=STYLE["text"], fontsize=12, pad=15)
    fig.tight_layout(); return fig

def chart_metrics_bar(results):
    _apply_style()
    names   = [r["metric"].replace(" ","\n") for r in results]
    current = [r["current"] for r in results]
    app_val = [r["appetite"] for r in results]
    tol_val = [r["tolerance"] for r in results]
    colors  = [RAG_COLORS[r["rag"]] for r in results]
    x = list(range(len(results)))
    fig, ax = plt.subplots(figsize=(14,5), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    ax.bar(x, current, color=colors, alpha=0.8, width=0.5, label="Current Value")
    ax.plot(x, app_val, "o--", color="#2ecc71", linewidth=1.5, markersize=6, label="Appetite", alpha=0.8)
    ax.plot(x, tol_val, "s--", color="#e74c3c", linewidth=1.5, markersize=6, label="Tolerance", alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=7)
    ax.set_title("Metrics vs Risk Appetite & Tolerance Thresholds", color=STYLE["text"], fontsize=12, pad=12)
    ax.legend(facecolor=STYLE["bg"], labelcolor=STYLE["text"], framealpha=0.5)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(STYLE["grid"])
    ax.yaxis.grid(True, color=STYLE["grid"], linewidth=0.5); ax.set_axisbelow(True)
    fig.tight_layout(); return fig

def chart_trend(result):
    _apply_style()
    history = result.get("history", [])
    if len(history) < 2: return None
    x      = list(range(len(history)))
    labels = [f"T-{len(history)-1-i}" for i in range(len(history)-1)] + ["Current"]
    fig, ax = plt.subplots(figsize=(6,3), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    ax.plot(x, history, "o-", color=RAG_COLORS[result["rag"]], linewidth=2, markersize=8)
    ax.axhline(result["appetite"],  color="#2ecc71", linestyle="--", linewidth=1, alpha=0.7, label="Appetite")
    ax.axhline(result["tolerance"], color="#e74c3c", linestyle="--", linewidth=1, alpha=0.7, label="Tolerance")
    ax.fill_between(x, history, alpha=0.1, color=RAG_COLORS[result["rag"]])
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_title(f"Trend: {result['metric']}", color=STYLE["text"], fontsize=10, pad=10)
    ax.legend(facecolor=STYLE["bg"], labelcolor=STYLE["text"], framealpha=0.5, fontsize=8)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(STYLE["grid"])
    ax.yaxis.grid(True, color=STYLE["grid"], linewidth=0.3); ax.set_axisbelow(True)
    fig.tight_layout(); return fig

# ─── Sidebar ──────────────────────────────────────────────────────────────────

def sidebar_form():
    st.sidebar.markdown("## ➕ Add / Update Metric")
    with st.sidebar.form("metric_form", clear_on_submit=True):
        metric   = st.selectbox("Metric", list(FRAMEWORKS.keys()))
        current  = st.number_input("Current Value",     min_value=0, max_value=1000, value=0)
        appetite = st.number_input("Appetite Threshold", min_value=0, max_value=1000, value=5)
        tolerance= st.number_input("Tolerance Threshold",min_value=0, max_value=1000, value=10)
        unit     = st.selectbox("Unit", ["count","%","days","£k"])
        period   = st.text_input("Reporting Period", value="Q1 2026")
        owner    = st.text_input("Metric Owner")
        action   = st.text_area("Remediation Action", height=60)
        submitted= st.form_submit_button("Add / Update Metric")

    if submitted:
        err = validate_thresholds(metric, appetite, tolerance)
        if err:
            st.sidebar.error(err); return
        existing = next((m for m in st.session_state.metrics if m["metric"]==metric), None)
        if existing:
            history = list(existing.get("history", []))
            history.append(existing["current"])
            if len(history) > 6: history = history[-6:]
            st.session_state.metrics = [m for m in st.session_state.metrics if m["metric"]!=metric]
        else:
            history = [current]
        st.session_state.metrics.append({
            "metric":metric,"current":current,"appetite":appetite,
            "tolerance":tolerance,"unit":unit,"period":period,
            "owner":owner or "—","action":action or "—","history":history,
        })
        st.sidebar.success(f"✓ {metric} updated")

    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📂 Upload Metrics JSON")
    uploaded = st.sidebar.file_uploader("Upload metrics.json", type=["json"])
    if uploaded:
        try:
            data = json.load(uploaded)
            st.session_state.metrics = data
            st.sidebar.success(f"✓ {len(data)} metrics loaded")
        except Exception as e:
            st.sidebar.error(f"Invalid JSON: {e}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if "metrics"      not in st.session_state: st.session_state.metrics      = DEFAULT_METRICS
    if "chat_history" not in st.session_state: st.session_state.chat_history = []

    sidebar_form()

    st.markdown("# 🎯 Risk Appetite & Metrics Dashboard")
    st.markdown(
        "<div style='color:#8b949e;font-size:.9rem;margin-bottom:24px'>"
        f"Reporting Period: {datetime.date.today().strftime('%d %B %Y')} &nbsp;·&nbsp; "
        "ISO 27001:2022 &nbsp;·&nbsp; FCA SYSC &nbsp;·&nbsp; UK GDPR &nbsp;·&nbsp; ISO 42001:2023"
        "</div>", unsafe_allow_html=True
    )

    if not st.session_state.metrics:
        st.info("No metrics loaded. Add metrics via the sidebar."); return

    results  = [assess_metric(m) for m in st.session_state.metrics]
    breaches = [r for r in results if r["rag"]=="Red"]
    ambers   = [r for r in results if r["rag"]=="Amber"]
    greens   = [r for r in results if r["rag"]=="Green"]

    # KPIs
    st.markdown("### Risk Appetite Overview")
    k1,k2,k3,k4,k5 = st.columns(5)
    for col, val, color, label in [
        (k1, len(results),  "#58a6ff","Total Metrics"),
        (k2, len(breaches), "#e74c3c","🔴 Red — Breached"),
        (k3, len(ambers),   "#f1c40f","🟡 Amber — At Risk"),
        (k4, len(greens),   "#2ecc71","🟢 Green — Within Appetite"),
        (k5, sum(1 for r in results if r.get("trend")=="worsening"),"#e74c3c","📈 Worsening"),
    ]:
        col.markdown(
            f'<div class="kpi-card"><div class="kpi-num" style="color:{color}">{val}</div>'
            f'<div class="kpi-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Breach alerts
    if breaches:
        st.markdown("---")
        st.markdown("### 🔴 Risk Appetite Breaches — Escalation Required")
        for r in breaches:
            st.error(
                f"**{r['metric']}** — Current: {r['current']}{r['unit']}  |  "
                f"Tolerance: {r['tolerance']}{r['unit']}  |  "
                f"Owner: {r.get('owner','—')}  |  Action: {r.get('action','—')}"
            )
    if ambers:
        st.markdown("### 🟡 Amber — Approaching Tolerance")
        for r in ambers:
            st.warning(
                f"**{r['metric']}** — Current: {r['current']}{r['unit']}  |  "
                f"Appetite: {r['appetite']}{r['unit']}  |  Tolerance: {r['tolerance']}{r['unit']}  |  "
                f"Owner: {r.get('owner','—')}"
            )

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Charts","📋 Metrics Register","🔍 Metric Detail","🤖 AI Assistant","📄 Export"
    ])

    # Tab 1 — Charts
    with tab1:
        c1, c2 = st.columns([1,2])
        with c1: st.pyplot(chart_rag_summary(results))
        with c2: st.pyplot(chart_metrics_bar(results))

    # Tab 2 — Register
    with tab2:
        st.markdown("#### Compliance Risk Appetite Metrics")
        rf = st.multiselect("Filter by RAG",["Red","Amber","Green"],default=["Red","Amber","Green"])
        sorted_r = sorted(
            [r for r in results if r["rag"] in rf],
            key=lambda x: (["Red","Amber","Green"].index(x["rag"]),-abs(x["current"]-x["tolerance"]))
        )
        for r in sorted_r:
            color = RAG_COLORS[r["rag"]]
            trend_str = (" 📈 Worsening" if r["trend"]=="worsening"
                         else " 📉 Improving" if r["trend"]=="improving" else "")
            change = r.get("period_change")
            change_str = ""
            if change is not None:
                arrow = "▲" if change > 0 else "▼" if change < 0 else "→"
                change_str = f"  |  {arrow} {abs(change)} vs last period"

            with st.expander(
                f"{RAG_ICONS[r['rag']]}  {r['metric']}  |  "
                f"Current: {r['current']}{r['unit']}{change_str}  |  "
                f"{r['rag']}{trend_str}"
            ):
                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"**Current Value:** {r['current']} {r['unit']}")
                    st.markdown(f"**Appetite Threshold:** {r['appetite']} {r['unit']}")
                    st.markdown(f"**Tolerance Threshold:** {r['tolerance']} {r['unit']}")
                    st.markdown(f"**Reporting Period:** {r['period']}")
                    st.markdown(f"**Metric Owner:** {r.get('owner','—')}")
                    st.markdown(f"**Framework Ref:** `{FRAMEWORKS.get(r['metric'],'—')}`")
                with cb:
                    st.markdown(
                        f"<div style='font-size:1.4rem;color:{color}'>"
                        f"{RAG_ICONS[r['rag']]} {r['rag']}</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"**Remediation Action:** {r.get('action','—')}")
                    if r["breach"]:   st.error("⚠ Tolerance breached — escalation required")
                    if r["trend"]=="worsening": st.warning("📈 Trending in wrong direction")
                    elif r["trend"]=="improving": st.success("📉 Metric improving")
                fig = chart_trend(r)
                if fig: st.pyplot(fig)

    # Tab 3 — Detail
    with tab3:
        selected = st.selectbox("Select Metric", [r["metric"] for r in results])
        r = next(x for x in results if x["metric"]==selected)
        c1,c2,c3 = st.columns(3)
        c1.metric("Current Value", f"{r['current']} {r['unit']}")
        c2.metric("Appetite",      f"{r['appetite']} {r['unit']}")
        c3.metric("Tolerance",     f"{r['tolerance']} {r['unit']}")
        color = RAG_COLORS[r["rag"]]
        st.markdown(
            f"<div style='font-size:1.8rem;color:{color};margin:12px 0'>"
            f"{RAG_ICONS[r['rag']]} {r['rag']}</div>", unsafe_allow_html=True
        )
        change = r.get("period_change")
        if change is not None:
            arrow = "▲" if change > 0 else "▼" if change < 0 else "→"
            st.markdown(f"**Period Change:** {arrow} {abs(change)} {r['unit']} vs last period")
        st.markdown(f"**Metric Owner:** {r.get('owner','—')}")
        st.markdown(f"**Remediation Action:** {r.get('action','—')}")
        st.markdown(f"**Framework Ref:** `{FRAMEWORKS.get(r['metric'],'—')}`")
        st.markdown(f"**Reporting Period:** {r['period']}")
        if r["breach"]:            st.error("Tolerance breached — immediate escalation required")
        if r["trend"]=="worsening":st.warning("Metric trending in wrong direction")
        elif r["trend"]=="improving":st.success("Metric improving — continue monitoring")
        fig = chart_trend(r)
        if fig: st.pyplot(fig)

    # Tab 4 — AI Assistant
    with tab4:
        st.markdown("#### 🤖 AI Risk Appetite Assistant")
        st.markdown(
            "<div style='color:#8b949e;font-size:.85rem;margin-bottom:16px'>"
            "Powered by Groq / Llama 3 — Ask about metrics, RAG status, remediation, "
            "or how to use the dashboard.</div>",
            unsafe_allow_html=True
        )

        # Committee briefing
        st.markdown("##### AI Committee Briefing")
        if st.button("🗒 Generate Committee Briefing"):
            with st.spinner("Generating briefing..."):
                briefing = ai_committee_briefing(results)
            st.session_state.committee_briefing = briefing
        if "committee_briefing" in st.session_state:
            st.info(st.session_state.committee_briefing)
            st.download_button(
                "⬇ Download Briefing",
                data=st.session_state.committee_briefing,
                file_name=f"committee_briefing_{datetime.date.today()}.txt",
                mime="text/plain"
            )

        st.markdown("---")
        st.markdown("##### Chat with your Risk Appetite Data")

        # Display chat history
        for msg in st.session_state.chat_history:
            st.markdown(
                f'<div class="chat-msg-user">🧑 {msg["user"]}</div>',
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div class="chat-msg-ai">🤖 {msg["assistant"]}</div>',
                unsafe_allow_html=True
            )

        # Chat input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_input(
                "Ask a question...",
                placeholder="e.g. Why is Critical Vulnerabilities red? What should I do about BCP Tests?"
            )
            send = st.form_submit_button("Send")

        if send and user_input:
            with st.spinner("Thinking..."):
                response = ai_chat_response(
                    user_input, results, st.session_state.chat_history
                )
            st.session_state.chat_history.append({
                "user": user_input, "assistant": response
            })
            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑 Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()

    # Tab 5 — Export
    with tab5:
        st.markdown("#### Export Reports")
        today = datetime.date.today().strftime("%d %B %Y")
        lines = [
            "# Risk Appetite & Metrics Report",
            f"**Reporting Date:** {today}  ",
            "**Classification:** Internal — Risk Committee  ",
            "**Framework:** ISO 27001:2022 · FCA SYSC · UK GDPR · ISO 42001:2023",
            "","---","","## Executive Summary","",
            f"Total metrics tracked: **{len(results)}**","",
            "| RAG Status | Count |","|---|---|",
        ]
        for s in ["Red","Amber","Green"]:
            lines.append(f"| {RAG_ICONS[s]} {s} | {sum(1 for r in results if r['rag']==s)} |")
        if breaches:
            lines += ["","### ⚠ Appetite Breaches Requiring Escalation"]
            for r in breaches:
                lines.append(
                    f"- **{r['metric']}** — Current: {r['current']}{r['unit']} "
                    f"(Tolerance: {r['tolerance']}{r['unit']}) — "
                    f"Owner: {r.get('owner','—')} — Action: {r.get('action','—')}"
                )
        if "committee_briefing" in st.session_state:
            lines += ["","---","","## AI Committee Briefing","",
                      st.session_state.committee_briefing]
        lines += ["","---","","## Full Metrics Register",""]
        for r in sorted(results, key=lambda x: ["Red","Amber","Green"].index(x["rag"])):
            change = r.get("period_change")
            change_str = f" (▲{abs(change)} vs last)" if change and change > 0 else \
                         f" (▼{abs(change)} vs last)" if change and change < 0 else ""
            lines += [
                f"### {RAG_ICONS[r['rag']]} {r['metric']}",
                f"| Field | Value |","|---|---|",
                f"| Current Value | {r['current']}{r['unit']}{change_str} |",
                f"| Appetite | {r['appetite']}{r['unit']} |",
                f"| Tolerance | {r['tolerance']}{r['unit']} |",
                f"| RAG Status | {r['rag']} |",
                f"| Trend | {r.get('trend','—')} |",
                f"| Owner | {r.get('owner','—')} |",
                f"| Action | {r.get('action','—')} |",
                f"| Framework | {FRAMEWORKS.get(r['metric'],'—')} |",
                f"| Period | {r['period']} |","",
            ]
        lines.append("*Generated by Risk Appetite & Metrics Dashboard — Ajibola Yusuff*")

        st.download_button("⬇ Download Metrics Report (Markdown)",
            data="\n".join(lines),
            file_name=f"risk_appetite_report_{datetime.date.today()}.md",
            mime="text/markdown")

        csv_buf = io.StringIO()
        writer  = csv.DictWriter(csv_buf, fieldnames=[
            "metric","current","unit","appetite","tolerance",
            "rag","trend","period_change","owner","action","period","framework"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "metric":r["metric"],"current":r["current"],"unit":r["unit"],
                "appetite":r["appetite"],"tolerance":r["tolerance"],
                "rag":r["rag"],"trend":r.get("trend","—"),
                "period_change":r.get("period_change","—"),
                "owner":r.get("owner","—"),"action":r.get("action","—"),
                "period":r["period"],"framework":FRAMEWORKS.get(r["metric"],"—"),
            })
        st.download_button("⬇ Download Metrics (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"risk_appetite_{datetime.date.today()}.csv",
            mime="text/csv")

        st.download_button("⬇ Download Metrics (JSON)",
            data=json.dumps(st.session_state.metrics, indent=2),
            file_name=f"metrics_{datetime.date.today()}.json",
            mime="application/json")

        st.markdown("---")
        if st.button("🗑 Reset to Default Metrics"):
            st.session_state.metrics      = DEFAULT_METRICS
            st.session_state.chat_history = []
            st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='color:#8b949e;font-size:.8rem'>"
        "Risk Appetite & Metrics Dashboard &nbsp;·&nbsp; Ajibola Yusuff &nbsp;·&nbsp; "
        "ISO 27001 | ISO 42001 | CompTIA Security+"
        "</div>", unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()