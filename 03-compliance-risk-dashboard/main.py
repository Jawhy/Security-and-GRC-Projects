import csv
import os
import datetime
import io
import base64

import matplotlib  # type: ignore
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.patches as mpatches  # type: ignore

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich import box

console = Console(record=True)

# ─── Constants ────────────────────────────────────────────────────────────────

LIKELIHOOD_MAP  = {"1":1,"2":2,"3":3,"4":4,"5":5}
IMPACT_MAP      = {"1":1,"2":2,"3":3,"4":4,"5":5}
TIER_COLORS_HEX = {"CRITICAL":"#e74c3c","HIGH":"#e67e22","MEDIUM":"#f1c40f","LOW":"#2ecc71"}
STYLE           = {"bg":"#0d1117","text":"#e6edf3","grid":"#21262d"}

def get_tier(score):
    if score >= 20: return ("CRITICAL","red","🔴")
    elif score >= 12: return ("HIGH","orange3","🟠")
    elif score >= 6:  return ("MEDIUM","yellow","🟡")
    else:             return ("LOW","green","🟢")

def days_until(date_str):
    try:
        return (datetime.date.fromisoformat(date_str) - datetime.date.today()).days
    except Exception:
        return None


# ─── Data Loading ─────────────────────────────────────────────────────────────

def load_register(path):
    risks = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            likelihood = int(LIKELIHOOD_MAP.get(row.get("likelihood","1"), 1))
            impact     = int(IMPACT_MAP.get(row.get("impact","1"), 1))
            score      = likelihood * impact
            tier, col, icon = get_tier(score)
            days  = days_until(row.get("review_date",""))
            risks.append({
                "id":            row.get("risk_id","—"),
                "title":         row.get("risk_title","—"),
                "category":      row.get("category","—"),
                "owner":         row.get("risk_owner","—"),
                "likelihood":    likelihood,
                "impact":        impact,
                "score":         score,
                "tier":          tier,
                "tier_color":    col,
                "tier_icon":     icon,
                "controls":      row.get("existing_controls","—"),
                "action":        row.get("remediation_action","—"),
                "review_date":   row.get("review_date","—"),
                "status":        row.get("status","—"),
                "review_days":   days,
                "overdue":       days is not None and days < 0,
                "due_soon":      days is not None and 0 <= days <= 30,
                "framework_ref": row.get("framework_ref","—"),
            })
    return risks


# ─── Charts ───────────────────────────────────────────────────────────────────

def _fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def _apply_style():
    plt.rcParams.update({
        "text.color":       STYLE["text"],
        "axes.labelcolor":  STYLE["text"],
        "xtick.color":      STYLE["text"],
        "ytick.color":      STYLE["text"],
    })

def chart_heatmap(risks):
    _apply_style()
    fig, ax = plt.subplots(figsize=(7,6), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    ax.set_xlim(0.5,5.5); ax.set_ylim(0.5,5.5)
    ax.set_xlabel("Impact →", fontsize=10)
    ax.set_ylabel("← Likelihood", fontsize=10)
    ax.set_title("Risk Heatmap (Likelihood × Impact)", color=STYLE["text"], fontsize=12, pad=12)

    for l in range(1,6):
        for i in range(1,6):
            s = l*i
            _, _, _ = get_tier(s)
            t = get_tier(s)
            color = TIER_COLORS_HEX[t[0]]
            ax.add_patch(plt.Rectangle((i-0.5,l-0.5),1,1,color=color,alpha=0.25))

    for r in risks:
        ax.scatter(r["impact"], r["likelihood"],
                   color=TIER_COLORS_HEX[r["tier"]], s=120, zorder=5,
                   edgecolors=STYLE["text"], linewidths=0.5)
        ax.annotate(r["id"], (r["impact"], r["likelihood"]),
                    textcoords="offset points", xytext=(6,4),
                    fontsize=7, color=STYLE["text"])

    ax.set_xticks(range(1,6)); ax.set_yticks(range(1,6))
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(STYLE["grid"])
    ax.yaxis.grid(True, color=STYLE["grid"], linewidth=0.3)
    ax.xaxis.grid(True, color=STYLE["grid"], linewidth=0.3)
    ax.set_axisbelow(True)

    patches = [mpatches.Patch(color=TIER_COLORS_HEX[t], label=t, alpha=0.7)
               for t in ["CRITICAL","HIGH","MEDIUM","LOW"]]
    ax.legend(handles=patches, facecolor=STYLE["bg"], labelcolor=STYLE["text"],
              framealpha=0.5, fontsize=8, loc="upper left")
    fig.tight_layout()
    return _fig_to_b64(fig)

def chart_tier_bar(risks):
    _apply_style()
    tiers  = ["CRITICAL","HIGH","MEDIUM","LOW"]
    counts = [sum(1 for r in risks if r["tier"]==t) for t in tiers]
    colors = [TIER_COLORS_HEX[t] for t in tiers]
    fig, ax = plt.subplots(figsize=(6,4), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    bars = ax.bar(tiers, counts, color=colors, alpha=0.85, width=0.5)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
                str(count), ha="center", va="bottom",
                color=STYLE["text"], fontsize=10, fontweight="bold")
    ax.set_ylabel("Number of Risks")
    ax.set_title("Risk Distribution by Tier", color=STYLE["text"], fontsize=12, pad=12)
    ax.set_ylim(0, max(counts)+2 if counts else 5)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color(STYLE["grid"])
    ax.yaxis.grid(True, color=STYLE["grid"], linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return _fig_to_b64(fig)

def chart_category_donut(risks):
    _apply_style()
    cats   = {}
    for r in risks:
        cats[r["category"]] = cats.get(r["category"],0) + 1
    if not cats: return None
    fig, ax = plt.subplots(figsize=(5,5), facecolor=STYLE["bg"])
    ax.set_facecolor(STYLE["bg"])
    palette = ["#58a6ff","#e74c3c","#2ecc71","#f1c40f","#e67e22","#9b59b6","#1abc9c"]
    colors  = [palette[i % len(palette)] for i in range(len(cats))]
    wedges, texts, autotexts = ax.pie(
        list(cats.values()), labels=list(cats.keys()),
        colors=colors, autopct="%1.0f%%", startangle=90,
        wedgeprops={"width":0.5,"edgecolor":STYLE["bg"],"linewidth":2},
        textprops={"color":STYLE["text"],"fontsize":9},
    )
    for at in autotexts:
        at.set_color(STYLE["bg"]); at.set_fontweight("bold")
    ax.set_title("Risks by Category", color=STYLE["text"], fontsize=12, pad=15)
    fig.tight_layout()
    return _fig_to_b64(fig)


# ─── Terminal Display ─────────────────────────────────────────────────────────

def print_header():
    console.print()
    console.print(Panel.fit(
        "[bold white]Compliance Risk Register Dashboard[/bold white]\n"
        "[dim]Governance, Risk & Compliance — Committee Reporting Tool[/dim]\n"
        "[dim]ISO 27001:2022  ·  NIST CSF  ·  FCA SYSC  ·  UK GDPR[/dim]\n"
        f"[dim]Report Date: {datetime.date.today().strftime('%d %B %Y')}[/dim]",
        border_style="blue", padding=(1,4)
    ))
    console.print()

def print_kpis(risks):
    total    = len(risks)
    critical = sum(1 for r in risks if r["tier"]=="CRITICAL")
    high     = sum(1 for r in risks if r["tier"]=="HIGH")
    overdue  = sum(1 for r in risks if r["overdue"])
    due_soon = sum(1 for r in risks if r["due_soon"])
    open_r   = sum(1 for r in risks if r["status"].lower()=="open")

    grid = Table.grid(expand=True)
    for _ in range(6): grid.add_column(justify="center")
    grid.add_row(
        Panel(f"[bold cyan]{total}[/bold cyan]\n[dim]Total Risks[/dim]",      border_style="cyan"),
        Panel(f"[bold red]{critical}[/bold red]\n[dim]Critical[/dim]",        border_style="red"),
        Panel(f"[bold orange3]{high}[/bold orange3]\n[dim]High[/dim]",        border_style="orange3"),
        Panel(f"[bold yellow]{overdue}[/bold yellow]\n[dim]Overdue[/dim]",    border_style="yellow"),
        Panel(f"[bold yellow]{due_soon}[/bold yellow]\n[dim]Due Soon[/dim]",  border_style="yellow"),
        Panel(f"[bold white]{open_r}[/bold white]\n[dim]Open[/dim]",          border_style="white"),
    )
    console.print(grid)
    console.print()

def print_top_risks(risks):
    console.print(Rule("[bold]Top 5 Critical & High Risks[/bold]", style="blue"))
    console.print()
    top = sorted(risks, key=lambda x: x["score"], reverse=True)[:5]
    tbl = Table(box=box.ROUNDED, header_style="bold white on blue", padding=(0,1))
    tbl.add_column("ID",        style="dim",    width=8)
    tbl.add_column("Risk",      style="white",  min_width=28)
    tbl.add_column("Category",  style="cyan",   min_width=16)
    tbl.add_column("Owner",     style="dim",    min_width=18)
    tbl.add_column("L",         justify="center", width=4)
    tbl.add_column("I",         justify="center", width=4)
    tbl.add_column("Score",     justify="center", width=6)
    tbl.add_column("Tier",      justify="center", min_width=12)
    tbl.add_column("Status",    justify="center", min_width=14)
    for r in top:
        tc = r["tier_color"]
        sc = {"Open":"yellow","In Progress":"blue","Closed":"green"}.get(r["status"],"white")
        tbl.add_row(
            r["id"], r["title"], r["category"], r["owner"],
            str(r["likelihood"]), str(r["impact"]), str(r["score"]),
            f"{r['tier_icon']} [{tc}]{r['tier']}[/{tc}]",
            f"[{sc}]{r['status']}[/{sc}]",
        )
    console.print(tbl)
    console.print()

def print_full_register(risks):
    console.print(Rule("[bold]Full Risk Register[/bold]", style="blue"))
    console.print()
    for r in sorted(risks, key=lambda x: x["score"], reverse=True):
        tc = r["tier_color"]
        sc = {"Open":"yellow","In Progress":"blue","Closed":"green"}.get(r["status"],"white")
        console.print(Rule(
            f"[bold]{r['id']}[/bold]  ·  {r['title']}  ·  "
            f"[{tc}]{r['tier_icon']} {r['tier']}[/{tc}]",
            style="dim"
        ))
        det = Table(box=box.ROUNDED, show_header=False, padding=(0,1))
        det.add_column("Field", style="dim",   min_width=22)
        det.add_column("Value", style="white", min_width=40)
        det.add_row("Category",        r["category"])
        det.add_row("Risk Owner",       r["owner"])
        det.add_row("Likelihood",       str(r["likelihood"]) + "/5")
        det.add_row("Impact",           str(r["impact"]) + "/5")
        det.add_row("Risk Score",       f"{r['score']}/25")
        det.add_row("Risk Tier",        f"{r['tier_icon']} {r['tier']}")
        det.add_row("Existing Controls",r["controls"])
        det.add_row("Remediation Action",r["action"])
        det.add_row("Framework Ref",    r["framework_ref"])
        rd = r["review_date"]
        if r["overdue"]:   rd += f" [bold red](OVERDUE by {abs(r['review_days'])} days)[/bold red]"
        elif r["due_soon"]:rd += f" [yellow](due in {r['review_days']} days)[/yellow]"
        det.add_row("Review Date",      rd)
        det.add_row("Status",           f"[{sc}]{r['status']}[/{sc}]")
        console.print(det)
        console.print()

def print_overdue(risks):
    overdue  = [r for r in risks if r["overdue"]]
    due_soon = [r for r in risks if r["due_soon"]]
    if not overdue and not due_soon: return
    alerts = []
    for r in overdue:
        alerts.append(f"[red]⚠  {r['id']} — {r['title']} — overdue by {abs(r['review_days'])} days[/red]")
    for r in due_soon:
        alerts.append(f"[yellow]⚠  {r['id']} — {r['title']} — due in {r['review_days']} days[/yellow]")
    console.print(Panel(
        "\n".join(alerts),
        title="[bold]Committee Attention — Review Schedule Alerts[/bold]",
        border_style="red", padding=(0,2)
    ))
    console.print()


# ─── Export ───────────────────────────────────────────────────────────────────

def export_markdown(risks):
    today = datetime.date.today().strftime("%d %B %Y")
    top5  = sorted(risks, key=lambda x: x["score"], reverse=True)[:5]
    lines = [
        "# Compliance Risk Register — Committee Pack",
        f"**Report Date:** {today}  ",
        "**Classification:** Internal — Risk Committee  ",
        "**Framework:** ISO 27001:2022 · NIST CSF · FCA SYSC · UK GDPR",
        "","---","","## Executive Summary","",
        f"Total risks assessed: **{len(risks)}**","",
        "| Tier | Count |","|---|---|",
    ]
    for t in ["CRITICAL","HIGH","MEDIUM","LOW"]:
        lines.append(f"| {t} | {sum(1 for r in risks if r['tier']==t)} |")

    overdue = [r for r in risks if r["overdue"]]
    if overdue:
        lines += ["","### ⚠ Overdue Reviews"]
        for r in overdue:
            lines.append(f"- **{r['id']}** — {r['title']} (overdue by {abs(r['review_days'])} days)")

    lines += ["","---","","## Top 5 Risks",""]
    for r in top5:
        lines += [
            f"### {r['tier_icon']} {r['id']} — {r['title']}",
            f"**Category:** {r['category']}  |  **Owner:** {r['owner']}  ",
            f"**Score:** {r['score']}/25  |  **Tier:** {r['tier']}  |  **Status:** {r['status']}  ",
            f"**Controls:** {r['controls']}  ",
            f"**Action:** {r['action']}  ",
            f"**Framework Ref:** {r['framework_ref']}  ","",
        ]

    lines += ["---","","## Full Risk Register",""]
    for r in sorted(risks, key=lambda x: x["score"], reverse=True):
        lines += [
            f"### {r['id']} — {r['title']}",
            f"| Field | Value |","|---|---|",
            f"| Category | {r['category']} |",
            f"| Owner | {r['owner']} |",
            f"| Likelihood | {r['likelihood']}/5 |",
            f"| Impact | {r['impact']}/5 |",
            f"| Score | {r['score']}/25 |",
            f"| Tier | {r['tier']} |",
            f"| Controls | {r['controls']} |",
            f"| Action | {r['action']} |",
            f"| Framework Ref | {r['framework_ref']} |",
            f"| Review Date | {r['review_date']} |",
            f"| Status | {r['status']} |","",
        ]
    lines.append("*Generated by Compliance Risk Register Dashboard — Ajibola Yusuff*")
    path = os.path.join("reports","committee_pack.md")
    with open(path,"w",encoding="utf-8") as f:
        f.write("\n".join(lines))
    console.print("  [green]✓  Committee pack exported → reports/committee_pack.md[/green]")

def export_html(risks, charts):
    today = datetime.date.today().strftime("%d %B %Y")
    top5  = sorted(risks, key=lambda x: x["score"], reverse=True)[:5]

    def badge(tier):
        return f'<span class="badge badge-{tier.lower()}">{tier}</span>'

    rows = ""
    for r in sorted(risks, key=lambda x: x["score"], reverse=True):
        rd = r["review_date"]
        if r["overdue"]:   rd = f'<span style="color:#e74c3c">⚠ {rd}</span>'
        elif r["due_soon"]:rd = f'<span style="color:#f1c40f">⚠ {rd}</span>'
        rows += f"""<tr>
          <td>{r['id']}</td><td>{r['title']}</td><td>{r['category']}</td>
          <td>{r['owner']}</td><td>{r['likelihood']}</td><td>{r['impact']}</td>
          <td><strong>{r['score']}</strong></td><td>{badge(r['tier'])}</td>
          <td>{rd}</td><td>{r['status']}</td>
        </tr>"""

    top_html = ""
    for r in top5:
        top_html += f"""<div class="toprisk">
          <div class="toprisk-title">{r['tier_icon']} {r['id']} — {r['title']}</div>
          <div class="toprisk-meta">
            <span class="pill">Score: <strong>{r['score']}/25</strong></span>
            {badge(r['tier'])}
            <span class="pill">Owner: {r['owner']}</span>
            <span class="pill">Status: {r['status']}</span>
          </div>
          <div style="color:#8b949e;font-size:.85rem;margin-top:8px">
            Action: {r['action']}
          </div>
        </div>"""

    kpis = [
        (len(risks),                                    "#58a6ff","Total Risks"),
        (sum(1 for r in risks if r["tier"]=="CRITICAL"),"#e74c3c","Critical"),
        (sum(1 for r in risks if r["tier"]=="HIGH"),    "#e67e22","High"),
        (sum(1 for r in risks if r["overdue"]),         "#f1c40f","Overdue"),
        (sum(1 for r in risks if r["due_soon"]),        "#f1c40f","Due Soon"),
        (sum(1 for r in risks if r["status"]=="Open"),  "#58a6ff","Open"),
    ]
    kpi_html = "".join(
        f'<div class="kpi-card"><div class="kpi-num" style="color:{c}">{n}</div>'
        f'<div class="kpi-label">{l}</div></div>'
        for n,c,l in kpis
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Compliance Risk Register Dashboard</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',Arial,sans-serif;padding:32px}}
  h1{{font-size:1.8rem;color:#58a6ff;margin-bottom:4px}}
  .subtitle{{color:#8b949e;font-size:.9rem;margin-bottom:24px}}
  .kpi-grid{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px}}
  .kpi-card{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:20px 28px;min-width:120px;text-align:center}}
  .kpi-num{{font-size:2rem;font-weight:700}}
  .kpi-label{{font-size:.8rem;color:#8b949e;margin-top:4px}}
  .section{{margin-bottom:36px}}
  .section h2{{font-size:1.1rem;color:#58a6ff;margin-bottom:14px;border-bottom:1px solid #21262d;padding-bottom:8px}}
  .toprisk{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px 18px;margin:10px 0}}
  .toprisk-title{{font-weight:700;margin-bottom:8px}}
  .toprisk-meta{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
  .pill{{background:#0d1117;border:1px solid #21262d;border-radius:999px;padding:4px 10px;color:#c9d1d9;font-size:.8rem}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  th{{background:#161b22;color:#8b949e;text-align:left;padding:10px 12px;font-weight:600;border-bottom:1px solid #21262d}}
  td{{padding:10px 12px;border-bottom:1px solid #21262d}}
  tr:hover td{{background:#161b22}}
  .badge{{padding:3px 10px;border-radius:12px;font-size:.75rem;font-weight:700}}
  .badge-critical{{background:#e74c3c22;color:#e74c3c;border:1px solid #e74c3c}}
  .badge-high{{background:#e67e2222;color:#e67e22;border:1px solid #e67e22}}
  .badge-medium{{background:#f1c40f22;color:#f1c40f;border:1px solid #f1c40f}}
  .badge-low{{background:#2ecc7122;color:#2ecc71;border:1px solid #2ecc71}}
  .chart-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-bottom:20px}}
  .chart-grid img{{width:100%;border-radius:10px;border:1px solid #21262d}}
  .footer{{color:#8b949e;font-size:.8rem;margin-top:40px;border-top:1px solid #21262d;padding-top:16px}}
</style>
</head>
<body>
<h1>Compliance Risk Register Dashboard</h1>
<div class="subtitle">
  Report Date: {today} &nbsp;·&nbsp; ISO 27001:2022 &nbsp;·&nbsp;
  NIST CSF &nbsp;·&nbsp; FCA SYSC &nbsp;·&nbsp; UK GDPR
</div>

<div class="section">
  <h2>Portfolio KPI Dashboard</h2>
  <div class="kpi-grid">{kpi_html}</div>
</div>

<div class="section">
  <h2>Risk Visualisation</h2>
  <div class="chart-grid">
    <img src="data:image/png;base64,{charts.get('heatmap','')}" alt="Heatmap">
    <img src="data:image/png;base64,{charts.get('bar','')}" alt="Distribution">
    <img src="data:image/png;base64,{charts.get('donut','')}" alt="Categories">
  </div>
</div>

<div class="section">
  <h2>Top 5 Risks</h2>
  {top_html}
</div>

<div class="section">
  <h2>Full Risk Register</h2>
  <table>
    <thead><tr>
      <th>ID</th><th>Risk</th><th>Category</th><th>Owner</th>
      <th>L</th><th>I</th><th>Score</th><th>Tier</th>
      <th>Review Date</th><th>Status</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>

<div class="footer">
  Compliance Risk Register Dashboard &nbsp;·&nbsp; Ajibola Yusuff &nbsp;·&nbsp;
  ISO 27001 | ISO 42001 | CompTIA Security+
</div>
</body></html>"""

    with open(os.path.join("reports","risk_dashboard.html"),"w",encoding="utf-8") as f:
        f.write(html)
    console.print("  [green]✓  HTML dashboard exported  → reports/risk_dashboard.html[/green]")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    print_header()
    path = os.path.join(os.path.dirname(__file__),"sample_data","risk_register.csv")
    try:
        risks = load_register(path)
    except FileNotFoundError:
        console.print("[red]Error:[/red] sample_data/risk_register.csv not found."); return

    console.print(f"[dim]› {len(risks)} risks loaded from register[/dim]\n")
    print_kpis(risks)
    print_top_risks(risks)
    print_overdue(risks)
    print_full_register(risks)

    console.print(Rule("[bold]Exporting Reports[/bold]", style="blue"))
    console.print()
    os.makedirs("reports", exist_ok=True)
    charts = {
        "heatmap": chart_heatmap(risks),
        "bar":     chart_tier_bar(risks),
        "donut":   chart_category_donut(risks),
    }
    export_markdown(risks)
    export_html(risks, charts)
    console.save_html(os.path.join("reports","terminal_output.html"), inline_styles=True)
    console.print("  [green]✓  Terminal snapshot exported → reports/terminal_output.html[/green]")
    console.print("\n[dim]Tip: open reports/risk_dashboard.html in your browser.[/dim]\n")

if __name__ == "__main__":
    main()