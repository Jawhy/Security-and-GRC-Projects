import csv
import io
import os
import datetime
import streamlit as st  # type: ignore
import matplotlib  # type: ignore
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.patches as mpatches  # type: ignore

st.set_page_config(
    page_title="Compliance Risk Register Dashboard",
    page_icon="📊",
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
  .badge { display:inline-block; padding:3px 12px; border-radius:12px; font-size:.8rem; font-weight:700; }
  .badge-critical{ background:#e74c3c22;color:#e74c3c;border:1px solid #e74c3c }
  .badge-high    { background:#e67e2222;color:#e67e22;border:1px solid #e67e22 }
  .badge-medium  { background:#f1c40f22;color:#f1c40f;border:1px solid #f1c40f }
  .badge-low     { background:#2ecc7122;color:#2ecc71;border:1px solid #2ecc71 }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────

TIER_COLORS = {"CRITICAL":"#e74c3c","HIGH":"#e67e22","MEDIUM":"#f1c40f","LOW":"#2ecc71"}
TIER_ICONS  = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}
STYLE       = {"bg":"#0d1117","text":"#e6edf3","grid":"#21262d"}

def get_tier(score):
    if score >= 20: return "CRITICAL"
    elif score >= 12: return "HIGH"
    elif score >= 6:  return "MEDIUM"
    else:             return "LOW"

def days_until(date_str):
    try:
        return (datetime.date.fromisoformat(date_str) - datetime.date.today()).days
    except Exception:
        return None

def load_csv(content):
    risks = []
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items()}
        likelihood = int(row.get("likelihood", 1))
        impact     = int(row.get("impact", 1))
        score      = likelihood * impact
        tier       = get_tier(score)
        days       = days_until(row.get("review_date",""))
        risks.append({
            "id":           row.get("risk_id","—"),
            "title":        row.get("risk_title","—"),
            "category":     row.get("category","—"),
            "owner":        row.get("risk_owner","—"),
            "likelihood":   likelihood,
            "impact":       impact,
            "score":        score,
            "tier":         tier,
            "controls":     row.get("existing_controls","—"),
            "action":       row.get("remediation_action","—"),
            "review_date":  row.get("review_date","—"),
            "status":       row.get("status","—"),
            "framework_ref":row.get("framework_ref","—"),
            "review_days":  days,
            "overdue":      days is not None and days < 0,
            "due_soon":     days is not None and 0 <= days <= 30,
        })
    return risks

# ─── Charts ───────────────────────────────────────────────────────────────────

def chart_heatmap(risks):
    plt.rcParams.update({"text.color":STYLE["text"],"axes.labelcolor":STYLE["text"],
                          "xtick.color":STYLE["text"],"ytick.color":STYLE["text"]})
    fig, ax = plt.subplots(figsize=(6,5), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    ax.set_xlim(0.5,5.5); ax.set_ylim(0.5,5.5)
    ax.set_xlabel("Impact →", fontsize=10)
    ax.set_ylabel("← Likelihood", fontsize=10)
    ax.set_title("Risk Heatmap", color=STYLE["text"], fontsize=12, pad=12)
    for l in range(1,6):
        for i in range(1,6):
            color = TIER_COLORS[get_tier(l*i)]
            ax.add_patch(plt.Rectangle((i-0.5,l-0.5),1,1,color=color,alpha=0.2))
    for r in risks:
        ax.scatter(r["impact"], r["likelihood"],
                   color=TIER_COLORS[r["tier"]], s=120, zorder=5,
                   edgecolors=STYLE["text"], linewidths=0.5)
        ax.annotate(r["id"],(r["impact"],r["likelihood"]),
                    textcoords="offset points",xytext=(6,4),
                    fontsize=7, color=STYLE["text"])
    ax.set_xticks(range(1,6)); ax.set_yticks(range(1,6))
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(STYLE["grid"])
    ax.yaxis.grid(True,color=STYLE["grid"],linewidth=0.3)
    ax.xaxis.grid(True,color=STYLE["grid"],linewidth=0.3)
    ax.set_axisbelow(True)
    patches = [mpatches.Patch(color=TIER_COLORS[t],label=t,alpha=0.7)
               for t in ["CRITICAL","HIGH","MEDIUM","LOW"]]
    ax.legend(handles=patches,facecolor=STYLE["bg"],labelcolor=STYLE["text"],
              framealpha=0.5,fontsize=8,loc="upper left")
    fig.tight_layout()
    return fig

def chart_bar(risks):
    plt.rcParams.update({"text.color":STYLE["text"],"axes.labelcolor":STYLE["text"],
                          "xtick.color":STYLE["text"],"ytick.color":STYLE["text"]})
    tiers  = ["CRITICAL","HIGH","MEDIUM","LOW"]
    counts = [sum(1 for r in risks if r["tier"]==t) for t in tiers]
    fig, ax = plt.subplots(figsize=(5,4), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    bars = ax.bar(tiers,[c for c in counts],
                  color=[TIER_COLORS[t] for t in tiers],alpha=0.85,width=0.5)
    for bar, count in zip(bars,counts):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                str(count),ha="center",va="bottom",
                color=STYLE["text"],fontsize=10,fontweight="bold")
    ax.set_ylabel("Count"); ax.set_ylim(0,max(counts)+2 if counts else 5)
    ax.set_title("Risk Distribution", color=STYLE["text"], fontsize=12, pad=12)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(STYLE["grid"])
    ax.yaxis.grid(True,color=STYLE["grid"],linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig

def chart_donut(risks):
    plt.rcParams.update({"text.color":STYLE["text"],"axes.labelcolor":STYLE["text"],
                          "xtick.color":STYLE["text"],"ytick.color":STYLE["text"]})
    cats = {}
    for r in risks: cats[r["category"]] = cats.get(r["category"],0)+1
    if not cats: return None
    palette = ["#58a6ff","#e74c3c","#2ecc71","#f1c40f","#e67e22","#9b59b6","#1abc9c"]
    fig, ax = plt.subplots(figsize=(5,5), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    _, texts, autotexts = ax.pie(
        list(cats.values()), labels=list(cats.keys()),
        colors=[palette[i%len(palette)] for i in range(len(cats))],
        autopct="%1.0f%%", startangle=90,
        wedgeprops={"width":0.5,"edgecolor":STYLE["bg"],"linewidth":2},
        textprops={"color":STYLE["text"],"fontsize":9},
    )
    for at in autotexts: at.set_color(STYLE["bg"]); at.set_fontweight("bold")
    ax.set_title("Risks by Category", color=STYLE["text"], fontsize=12, pad=15)
    fig.tight_layout()
    return fig

# ─── Main App ─────────────────────────────────────────────────────────────────

def main():
    if "risks" not in st.session_state:
        sample = os.path.join(os.path.dirname(__file__),"sample_data","risk_register.csv")
        if os.path.exists(sample):
            with open(sample, encoding="utf-8") as f:
                st.session_state.risks = load_csv(f.read())
        else:
            st.session_state.risks = []

    # Sidebar
    st.sidebar.markdown("## 📂 Load Risk Register")
    uploaded = st.sidebar.file_uploader("Upload risk_register.csv", type=["csv"])
    if uploaded:
        try:
            content = uploaded.read().decode("utf-8")
            st.session_state.risks = load_csv(content)
            st.sidebar.success(f"✓ {len(st.session_state.risks)} risks loaded")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("## ➕ Add a Risk")
    with st.sidebar.form("add_risk", clear_on_submit=True):
        rid    = st.text_input("Risk ID (e.g. R011)")
        title  = st.text_input("Risk Title")
        cat    = st.selectbox("Category",["Cyber Security","Third-Party Risk",
                  "Regulatory","AI Governance","Data Privacy",
                  "Operational Resilience","Cloud Security","Other"])
        owner  = st.text_input("Risk Owner")
        like   = st.slider("Likelihood", 1, 5, 3)
        impact = st.slider("Impact",     1, 5, 3)
        ctrl   = st.text_area("Existing Controls", height=60)
        action = st.text_area("Remediation Action", height=60)
        rev    = st.date_input("Review Date",
                   value=datetime.date.today()+datetime.timedelta(days=90))
        status = st.selectbox("Status",["Open","In Progress","Closed"])
        fref   = st.text_input("Framework Reference")
        sub    = st.form_submit_button("Add Risk")

    if sub and rid and title:
        score = like * impact
        days  = days_until(str(rev))
        st.session_state.risks.append({
            "id":rid,"title":title,"category":cat,"owner":owner,
            "likelihood":like,"impact":impact,"score":score,
            "tier":get_tier(score),"controls":ctrl,"action":action,
            "review_date":str(rev),"status":status,"framework_ref":fref,
            "review_days":days,
            "overdue":days is not None and days < 0,
            "due_soon":days is not None and 0 <= days <= 30,
        })
        st.sidebar.success(f"✓ {rid} added")

    # Header
    st.markdown("# 📊 Compliance Risk Register Dashboard")
    st.markdown(
        "<div style='color:#8b949e;font-size:.9rem;margin-bottom:24px'>"
        f"Report Date: {datetime.date.today().strftime('%d %B %Y')} &nbsp;·&nbsp; "
        "ISO 27001:2022 &nbsp;·&nbsp; NIST CSF &nbsp;·&nbsp; FCA SYSC &nbsp;·&nbsp; UK GDPR"
        "</div>", unsafe_allow_html=True
    )

    if not st.session_state.risks:
        st.info("No risks loaded. Upload a CSV or add risks using the sidebar.")
        return

    risks = st.session_state.risks
    sorted_r = sorted(risks, key=lambda x: x["score"], reverse=True)

    # KPIs
    st.markdown("### Risk Portfolio Dashboard")
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    for col, val, color, label in [
        (k1, len(risks),                                             "#58a6ff","Total Risks"),
        (k2, sum(1 for r in risks if r["tier"]=="CRITICAL"),         "#e74c3c","🔴 Critical"),
        (k3, sum(1 for r in risks if r["tier"]=="HIGH"),             "#e67e22","🟠 High"),
        (k4, sum(1 for r in risks if r["overdue"]),                  "#f1c40f","Overdue"),
        (k5, sum(1 for r in risks if r["due_soon"]),                 "#f1c40f","Due Soon"),
        (k6, sum(1 for r in risks if r["status"]=="Open"),           "#58a6ff","Open"),
    ]:
        col.markdown(
            f'<div class="kpi-card"><div class="kpi-num" style="color:{color}">{val}</div>'
            f'<div class="kpi-label">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Overdue alerts
    overdue  = [r for r in risks if r["overdue"]]
    due_soon = [r for r in risks if r["due_soon"]]
    if overdue or due_soon:
        for r in overdue:
            st.error(f"⚠ **{r['id']} — {r['title']}** — review overdue by {abs(r['review_days'])} days")
        for r in due_soon:
            st.warning(f"⚠ **{r['id']} — {r['title']}** — review due in {r['review_days']} days")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Charts","📋 Risk Register","🔍 Risk Detail","📄 Export"])

    # Tab 1 — Charts
    with tab1:
        c1, c2, c3 = st.columns(3)
        with c1: st.pyplot(chart_heatmap(risks))
        with c2: st.pyplot(chart_bar(risks))
        with c3:
            fig = chart_donut(risks)
            if fig: st.pyplot(fig)

    # Tab 2 — Register
    with tab2:
        st.markdown("#### Full Risk Register")
        tf = st.multiselect("Filter by Tier",["CRITICAL","HIGH","MEDIUM","LOW"],
                             default=["CRITICAL","HIGH","MEDIUM","LOW"])
        sf = st.multiselect("Filter by Status",["Open","In Progress","Closed"],
                             default=["Open","In Progress","Closed"])
        filtered = [r for r in sorted_r if r["tier"] in tf and r["status"] in sf]

        for r in filtered:
            color = TIER_COLORS[r["tier"]]
            rd = r["review_date"]
            if r["overdue"]:   rd += f" ⚠ OVERDUE"
            elif r["due_soon"]:rd += f" ⚠ due in {r['review_days']}d"
            with st.expander(
                f"{TIER_ICONS[r['tier']]}  {r['id']} — {r['title']}  |  "
                f"Score: {r['score']}/25  |  {r['tier']}  |  {r['status']}"
            ):
                ca, cb = st.columns(2)
                with ca:
                    st.markdown(f"**Category:** {r['category']}")
                    st.markdown(f"**Owner:** {r['owner']}")
                    st.markdown(f"**Likelihood:** {r['likelihood']}/5")
                    st.markdown(f"**Impact:** {r['impact']}/5")
                    st.markdown(f"**Score:** {r['score']}/25")
                    st.markdown(f"**Framework Ref:** `{r['framework_ref']}`")
                with cb:
                    st.markdown(f"**Review Date:** {rd}")
                    st.markdown(f"**Status:** {r['status']}")
                    st.markdown(f"**Existing Controls:** {r['controls']}")
                    st.markdown(f"**Remediation Action:** {r['action']}")

    # Tab 3 — Detail
    with tab3:
        names    = [f"{r['id']} — {r['title']}" for r in risks]
        selected = st.selectbox("Select Risk", names)
        r = next(x for x in risks if f"{x['id']} — {x['title']}" == selected)

        c1,c2,c3 = st.columns(3)
        c1.metric("Risk Score",  f"{r['score']}/25")
        c2.metric("Likelihood",  f"{r['likelihood']}/5")
        c3.metric("Impact",      f"{r['impact']}/5")

        color = TIER_COLORS[r["tier"]]
        st.markdown(
            f"<div style='font-size:1.6rem;color:{color};margin:12px 0'>"
            f"{TIER_ICONS[r['tier']]} {r['tier']}</div>",
            unsafe_allow_html=True
        )
        st.markdown(f"**Category:** {r['category']}  |  **Owner:** {r['owner']}  |  **Status:** {r['status']}")
        st.markdown(f"**Framework Reference:** `{r['framework_ref']}`")
        st.markdown(f"**Review Date:** {r['review_date']}")
        if r["overdue"]:   st.error(f"Review overdue by {abs(r['review_days'])} days")
        elif r["due_soon"]:st.warning(f"Review due in {r['review_days']} days")
        st.markdown("---")
        st.markdown(f"**Existing Controls:** {r['controls']}")
        st.markdown(f"**Remediation Action:** {r['action']}")

    # Tab 4 — Export
    with tab4:
        st.markdown("#### Export Reports")
        today = datetime.date.today().strftime("%d %B %Y")
        top5  = sorted(risks, key=lambda x: x["score"], reverse=True)[:5]

        # Markdown
        lines = [
            "# Compliance Risk Register — Committee Pack",
            f"**Report Date:** {today}  ",
            "**Framework:** ISO 27001:2022 · NIST CSF · FCA SYSC · UK GDPR",
            "","---","",
            "| Tier | Count |","|---|---|",
        ]
        for t in ["CRITICAL","HIGH","MEDIUM","LOW"]:
            lines.append(f"| {t} | {sum(1 for r in risks if r['tier']==t)} |")
        lines += ["","---","","## Top 5 Risks",""]
        for r in top5:
            lines += [
                f"### {TIER_ICONS[r['tier']]} {r['id']} — {r['title']}",
                f"**Score:** {r['score']}/25  |  **Tier:** {r['tier']}  |  **Owner:** {r['owner']}  ",
                f"**Action:** {r['action']}  ","",
            ]
        lines += ["---","","## Full Register",""]
        for r in sorted_r:
            lines += [
                f"### {r['id']} — {r['title']}",
                f"| Field | Value |","|---|---|",
                f"| Score | {r['score']}/25 |",
                f"| Tier | {r['tier']} |",
                f"| Owner | {r['owner']} |",
                f"| Status | {r['status']} |",
                f"| Action | {r['action']} |",
                f"| Framework | {r['framework_ref']} |","",
            ]
        lines.append("*Generated by Compliance Risk Register Dashboard — Ajibola Yusuff*")

        st.download_button("⬇ Download Committee Pack (Markdown)",
            data="\n".join(lines),
            file_name=f"committee_pack_{datetime.date.today()}.md",
            mime="text/markdown")

        # CSV
        csv_buf = io.StringIO()
        writer  = csv.DictWriter(csv_buf, fieldnames=[
            "id","title","category","owner","likelihood","impact",
            "score","tier","status","review_date","framework_ref","action"
        ])
        writer.writeheader()
        for r in risks:
            writer.writerow({k: r[k] for k in [
                "id","title","category","owner","likelihood","impact",
                "score","tier","status","review_date","framework_ref","action"
            ]})
        st.download_button("⬇ Download Risk Register (CSV)",
            data=csv_buf.getvalue(),
            file_name=f"risk_register_{datetime.date.today()}.csv",
            mime="text/csv")

        st.markdown("---")
        if st.button("🗑 Clear All Risks"):
            st.session_state.risks = []
            st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='color:#8b949e;font-size:.8rem'>"
        "Compliance Risk Register Dashboard &nbsp;·&nbsp; Ajibola Yusuff &nbsp;·&nbsp; "
        "ISO 27001 | ISO 42001 | CompTIA Security+"
        "</div>", unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()