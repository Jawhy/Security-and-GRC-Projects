import json
import os
import base64
import datetime
import io
from typing import Any, Dict, List, Tuple

try:
    import matplotlib  # type: ignore[reportMissingModuleSource]
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt  # type: ignore[reportMissingModuleSource]
except ImportError as e:
    raise ImportError(
        "matplotlib is required. Install with:\n"
        "  python3 -m pip install matplotlib\n"
        "Tip: ensure your venv is activated first."
    ) from e

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.rule import Rule
from rich import box


# Record terminal output so we can export an HTML "terminal snapshot"
console = Console(record=True)

# ─── Scoring Tables ───────────────────────────────────────────────────────────

DATA_SENSITIVITY: Dict[str, Dict[str, Any]] = {
    "public":              {"score": 0,  "label": "Public",              "control": "A.5.12"},
    "internal":            {"score": 10, "label": "Internal",            "control": "A.5.12"},
    "confidential":        {"score": 20, "label": "Confidential",        "control": "A.8.10"},
    "highly_confidential": {"score": 30, "label": "Highly Confidential", "control": "A.8.10"},
}
HOSTING_LOCATION: Dict[str, Dict[str, Any]] = {
    "uk":        {"score": 5,  "label": "United Kingdom",         "gdpr_risk": False},
    "eu":        {"score": 5,  "label": "European Union",         "gdpr_risk": False},
    "us":        {"score": 10, "label": "United States",          "gdpr_risk": True},
    "other":     {"score": 15, "label": "Other Jurisdiction",     "gdpr_risk": True},
    "high_risk": {"score": 20, "label": "High-Risk Jurisdiction", "gdpr_risk": True},
}
AI_USAGE: Dict[str, Dict[str, Any]] = {
    "none":        {"score": 0,  "label": "No AI Usage"},
    "internal":    {"score": 5,  "label": "Internal AI Tools"},
    "third_party": {"score": 10, "label": "Third-Party AI"},
    "autonomous":  {"score": 15, "label": "Autonomous AI Decision-Making"},
}
SUBCONTRACTORS: Dict[str, Dict[str, Any]] = {
    "none":   {"score": 0,  "label": "None"},
    "low":    {"score": 5,  "label": "1–2 Subcontractors"},
    "medium": {"score": 10, "label": "3–5 Subcontractors"},
    "high":   {"score": 15, "label": "5+ Subcontractors"},
}
SERVICE_CRITICALITY: Dict[str, Dict[str, Any]] = {
    "low":      {"score": 5,  "label": "Low"},
    "medium":   {"score": 10, "label": "Medium"},
    "high":     {"score": 15, "label": "High"},
    "critical": {"score": 20, "label": "Critical"},
}
CERTIFICATIONS: Dict[str, Dict[str, Any]] = {
    "iso_27001":        {"reduction": 10, "label": "ISO 27001:2022"},
    "soc2_type2":       {"reduction": 8,  "label": "SOC 2 Type II"},
    "pci_dss":          {"reduction": 7,  "label": "PCI DSS"},
    "gdpr":             {"reduction": 5,  "label": "GDPR Compliance"},
    "iso_42001":        {"reduction": 5,  "label": "ISO 42001 (AI Governance)"},
    "cyber_essentials": {"reduction": 3,  "label": "Cyber Essentials Plus"},
}

# Banking-friendly wording
OUTSOURCING_LABELS: Dict[str, str] = {
    "non-material": "Non-Material",
    "material":     "Material",
    "critical":     "Critical / Material",
}

CONTROL_DOMAIN_MAP: Dict[str, Dict[str, str]] = {
    "data_sensitivity":    {"domain": "Information Classification",     "ref": "ISO 27001 A.5.12 / A.8.10"},
    "hosting_location":    {"domain": "Cross-Border Transfer Controls", "ref": "UK GDPR Art.44 / ISO 27001 A.5.19"},
    "ai_usage":            {"domain": "AI Governance & Oversight",      "ref": "ISO 42001 / FCA AI Principles"},
    "subcontractors":      {"domain": "Supplier Relationship Mgmt",     "ref": "ISO 27001 A.5.19–A.5.22"},
    "service_criticality": {"domain": "Business Continuity / DR",       "ref": "ISO 27001 A.5.29–A.5.30"},
}

EVIDENCE_MAP: Dict[str, List[str]] = {
    "iso_27001":  [
        "ISO 27001 certificate + Statement of Applicability (SoA)",
        "Most recent internal audit report (or surveillance audit summary)",
    ],
    "soc2_type2": [
        "SOC 2 Type II report (confirm scope + coverage period)",
        "Bridge letter if report is > 6 months old",
    ],
    "pci_dss": [
        "PCI DSS Attestation of Compliance (AoC)",
        "Cardholder data environment scope diagram",
    ],
    "gdpr": [
        "Data Processing Agreement (DPA)",
        "Record of Processing Activities (RoPA) extract (or equivalent evidence)",
    ],
    "iso_42001": [
        "ISO 42001 certificate",
        "AI governance documentation (model cards, oversight, change management)",
    ],
}

BASE_EVIDENCE: List[str] = [
    "Completed Third-Party Security Questionnaire",
    "Business Continuity and Disaster Recovery test results (within 12 months)",
    "Penetration test summary (within 12 months)",
    "Subprocessor / fourth-party list",
    "Data flow and hosting architecture diagram",
]

AI_DUE_DILIGENCE: List[str] = [
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

# HTML chart palette (kept consistent across exports)
TIER_COLORS: Dict[str, str] = {
    "LOW": "#2ecc71",
    "MEDIUM": "#f1c40f",
    "HIGH": "#e67e22",
    "CRITICAL": "#e74c3c",
}

INHERENT_COLOR = "#5b8dd9"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def short_label(s: str, n: int = 16) -> str:
    """Short label for charts; keeps output readable with larger vendor sets."""
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ─── Core Logic ───────────────────────────────────────────────────────────────

def get_risk_tier(score: int) -> Tuple[str, str, str]:
    if score <= 25:
        return ("LOW", "green", "🟢")
    elif score <= 50:
        return ("MEDIUM", "yellow", "🟡")
    elif score <= 75:
        return ("HIGH", "orange3", "🟠")
    return ("CRITICAL", "red", "🔴")


def days_until(date_str: str):
    try:
        return (datetime.date.fromisoformat(date_str) - datetime.date.today()).days
    except Exception:
        return None


def calculate_scores(vendor: Dict[str, Any]) -> Tuple[int, int]:
    raw = (
        DATA_SENSITIVITY.get(vendor.get("data_sensitivity", ""), {}).get("score", 0)
        + HOSTING_LOCATION.get(vendor.get("hosting_location", ""), {}).get("score", 0)
        + AI_USAGE.get(vendor.get("ai_usage", ""), {}).get("score", 0)
        + SUBCONTRACTORS.get(vendor.get("subcontractors", ""), {}).get("score", 0)
        + SERVICE_CRITICALITY.get(vendor.get("service_criticality", ""), {}).get("score", 0)
    )
    inherent = round((raw / MAX_INHERENT) * 100)
    reduction = sum(
        CERTIFICATIONS[c]["reduction"]
        for c in vendor.get("certifications", [])
        if c in CERTIFICATIONS
    )
    residual = max(0, inherent - reduction)
    return inherent, residual


def get_evidence_required(vendor: Dict[str, Any]) -> List[str]:
    ev = list(BASE_EVIDENCE)

    for c in vendor.get("certifications", []):
        ev.extend(EVIDENCE_MAP.get(c, []))

    if vendor.get("ai_usage") in ["third_party", "autonomous"]:
        ev.append("AI governance pack (model cards, DPIA, evaluation results)")

    if HOSTING_LOCATION.get(vendor.get("hosting_location", ""), {}).get("gdpr_risk", False):
        ev.append("Standard Contractual Clauses (SCCs) / adequacy evidence + Transfer Impact Assessment (TIA)")

    if vendor.get("subcontractors") in ["medium", "high"]:
        ev.append("Fourth-party risk management policy / subcontractor oversight evidence")

    return _dedupe_preserve_order(ev)


def get_control_domains(vendor: Dict[str, Any]) -> List[Dict[str, str]]:
    domains: List[Dict[str, str]] = []
    checks = [
        ("data_sensitivity",    DATA_SENSITIVITY,    20),
        ("hosting_location",    HOSTING_LOCATION,    10),
        ("ai_usage",            AI_USAGE,            10),
        ("subcontractors",      SUBCONTRACTORS,      10),
        ("service_criticality", SERVICE_CRITICALITY, 15),
    ]
    for field, table, threshold in checks:
        if table.get(vendor.get(field, ""), {}).get("score", 0) >= threshold:
            domains.append(CONTROL_DOMAIN_MAP[field])
    return domains


def assess_vendor(vendor: Dict[str, Any]) -> Dict[str, Any]:
    inherent, residual = calculate_scores(vendor)
    i_tier, i_col, i_icon = get_risk_tier(inherent)
    r_tier, r_col, r_icon = get_risk_tier(residual)

    certs = vendor.get("certifications", [])
    ai_flag = vendor.get("ai_usage") in ["third_party", "autonomous"] and "iso_42001" not in certs
    gdpr_flag = HOSTING_LOCATION.get(vendor.get("hosting_location", ""), {}).get("gdpr_risk", False)

    days = days_until(vendor.get("review_date", ""))
    critical_jurisdiction = (
        vendor.get("service_criticality") == "critical"
        and vendor.get("hosting_location") == "high_risk"
    )

    return {
        "name":                  vendor.get("vendor_name", "Unknown"),
        "service":               vendor.get("service_type", "—"),
        "inherent_score":        inherent,
        "inherent_tier":         i_tier,
        "inherent_color":        i_col,
        "inherent_icon":         i_icon,
        "residual_score":        residual,
        "residual_tier":         r_tier,
        "residual_color":        r_col,
        "residual_icon":         r_icon,
        "ai_flag":               ai_flag,
        "gdpr_flag":             gdpr_flag,
        "critical_jurisdiction": critical_jurisdiction,
        "certifications":        certs,
        "data_sensitivity":      DATA_SENSITIVITY.get(vendor.get("data_sensitivity", ""), {}).get("label", "—"),
        "hosting":               HOSTING_LOCATION.get(vendor.get("hosting_location", ""), {}).get("label", "—"),
        "ai_usage":              AI_USAGE.get(vendor.get("ai_usage", ""), {}).get("label", "—"),
        "subcontractors":        SUBCONTRACTORS.get(vendor.get("subcontractors", ""), {}).get("label", "—"),
        "criticality":           SERVICE_CRITICALITY.get(vendor.get("service_criticality", ""), {}).get("label", "—"),
        "outsourcing_type":      OUTSOURCING_LABELS.get(vendor.get("outsourcing_type", ""), vendor.get("outsourcing_type", "—")),
        "risk_owner":            vendor.get("risk_owner", "—"),
        "review_date":           vendor.get("review_date", "—"),
        "review_days":           days,
        "review_overdue":        days is not None and days < 0,
        "review_due_soon":       days is not None and 0 <= days <= 30,
        "status":                vendor.get("status", "—"),
        "evidence_required":     get_evidence_required(vendor),
        "control_domains":       get_control_domains(vendor),
    }


# ─── Charts (exported into HTML as base64) ────────────────────────────────────

def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def make_charts_b64(results: List[Dict[str, Any]], vendors: List[Dict[str, Any]]) -> Dict[str, str]:
    """Generate charts from already-loaded inputs (no re-reading from disk)."""
    charts: Dict[str, str] = {}

    style = {"bg": "#0d1117", "text": "#e6edf3", "grid": "#21262d"}
    plt.rcParams.update({
        "text.color": style["text"],
        "axes.labelcolor": style["text"],
        "xtick.color": style["text"],
        "ytick.color": style["text"],
    })

    # Chart 1 — Residual tier distribution (donut)
    tiers = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    counts = [sum(1 for r in results if r["residual_tier"] == t) for t in tiers]
    colors = [TIER_COLORS[t] for t in tiers]
    non_zero = [(t, c, col) for t, c, col in zip(tiers, counts, colors) if c > 0]

    if non_zero:
        fig, ax = plt.subplots(figsize=(5, 5), facecolor=style["bg"])
        ax.set_facecolor(style["bg"])
        wedges, texts, autotexts = ax.pie(
            [x[1] for x in non_zero],
            labels=[x[0] for x in non_zero],
            colors=[x[2] for x in non_zero],
            autopct="%1.0f%%",
            startangle=90,
            wedgeprops={"width": 0.5, "edgecolor": style["bg"], "linewidth": 2},
            textprops={"color": style["text"], "fontsize": 11},
        )
        for at in autotexts:
            at.set_color(style["bg"])
            at.set_fontweight("bold")
        ax.set_title("Residual Risk Distribution", color=style["text"], fontsize=13, pad=15)
        charts["donut"] = _fig_to_b64(fig)

    # Chart 2 — Inherent vs Residual (bars)
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=style["bg"])
    ax.set_facecolor(style["bg"])

    x = list(range(len(results)))
    names = [short_label(r["name"], 18).replace(" ", "\n") for r in results]

    ax.bar(
        [i - 0.2 for i in x],
        [r["inherent_score"] for r in results],
        width=0.35,
        label="Inherent",
        color=INHERENT_COLOR,
        alpha=0.85,
    )
    ax.bar(
        [i + 0.2 for i in x],
        [r["residual_score"] for r in results],
        width=0.35,
        label="Residual",
        color=[TIER_COLORS[r["residual_tier"]] for r in results],
        alpha=0.9,
    )

    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("Risk Score (0–100)")
    ax.set_ylim(0, 115)
    ax.axhline(75, color=TIER_COLORS["CRITICAL"], linestyle="--", linewidth=0.8, alpha=0.5, label="Critical threshold")
    ax.axhline(50, color=TIER_COLORS["HIGH"], linestyle="--", linewidth=0.8, alpha=0.5, label="High threshold")

    ax.legend(facecolor=style["bg"], labelcolor=style["text"], framealpha=0.5)
    ax.set_title("Inherent vs Residual Risk by Vendor", color=style["text"], fontsize=13, pad=12)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(style["grid"])
    ax.yaxis.grid(True, color=style["grid"], linewidth=0.5)
    ax.set_axisbelow(True)
    fig.tight_layout()
    charts["bars"] = _fig_to_b64(fig)

    # Chart 3 — Risk factor heatmap (vendors x factors)
    factors = ["Data\nSensitivity", "Hosting\nLocation", "AI\nUsage", "Subcontractors", "Service\nCriticality"]
    factor_keys = ["data_sensitivity", "hosting_location", "ai_usage", "subcontractors", "service_criticality"]
    factor_tables = [DATA_SENSITIVITY, HOSTING_LOCATION, AI_USAGE, SUBCONTRACTORS, SERVICE_CRITICALITY]

    vendor_names = [short_label(v.get("vendor_name", "Unknown"), 20) for v in vendors]
    matrix: List[List[float]] = []

    for v in vendors:
        row: List[float] = []
        for key, tbl in zip(factor_keys, factor_tables):
            score = tbl.get(v.get(key, ""), {}).get("score", 0)
            max_s = max(t["score"] for t in tbl.values()) or 1
            row.append(score / max_s)
        matrix.append(row)

    if matrix:
        fig, ax = plt.subplots(figsize=(9, 4), facecolor=style["bg"])
        ax.set_facecolor(style["bg"])
        im = ax.imshow(matrix, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=1)
        ax.set_xticks(range(len(factors)))
        ax.set_xticklabels(factors, fontsize=9)
        ax.set_yticks(range(len(vendor_names)))
        ax.set_yticklabels(vendor_names, fontsize=9)

        for i in range(len(vendor_names)):
            for j in range(len(factors)):
                val = matrix[i][j]
                ax.text(
                    j, i, f"{val:.0%}",
                    ha="center", va="center",
                    color="black" if 0.3 < val < 0.8 else style["text"],
                    fontsize=8, fontweight="bold"
                )

        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
        cbar.ax.yaxis.set_tick_params(color=style["text"])
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=style["text"])

        ax.set_title("Risk Factor Heatmap (Normalised per Factor)", color=style["text"], fontsize=12, pad=12)
        fig.tight_layout()
        charts["heatmap"] = _fig_to_b64(fig)

    return charts


# ─── Terminal Display ─────────────────────────────────────────────────────────

def print_header():
    console.print()
    console.print(Panel.fit(
        "[bold white]TPRM Risk Scoring Engine[/bold white]\n"
        "[dim]Third-Party Risk Management Assessment Tool[/dim]\n"
        "[dim]ISO 27001:2022  ·  ISO 42001:2023  ·  FCA SS2/21  ·  EBA GL/2019/02  ·  UK GDPR[/dim]\n"
        f"[dim]Assessment Date: {datetime.date.today().strftime('%d %B %Y')}[/dim]",
        border_style="blue", padding=(1, 4)
    ))
    console.print()


def print_kpis(results: List[Dict[str, Any]]):
    total = len(results)
    critical = sum(1 for r in results if r["residual_tier"] == "CRITICAL")
    high = sum(1 for r in results if r["residual_tier"] == "HIGH")
    ai = sum(1 for r in results if r["ai_flag"])
    gdpr = sum(1 for r in results if r["gdpr_flag"])
    overdue = sum(1 for r in results if r["review_overdue"])

    grid = Table.grid(expand=True)
    for _ in range(6):
        grid.add_column(justify="center")

    grid.add_row(
        Panel(f"[bold cyan]{total}[/bold cyan]\n[dim]Total Vendors[/dim]", border_style="cyan"),
        Panel(f"[bold red]{critical}[/bold red]\n[dim]Critical[/dim]", border_style="red"),
        Panel(f"[bold orange3]{high}[/bold orange3]\n[dim]High Risk[/dim]", border_style="orange3"),
        Panel(f"[bold yellow]{overdue}[/bold yellow]\n[dim]Overdue Reviews[/dim]", border_style="yellow"),
        Panel(f"[bold yellow]{ai}[/bold yellow]\n[dim]AI Flags 🤖[/dim]", border_style="yellow"),
        Panel(f"[bold red]{gdpr}[/bold red]\n[dim]GDPR Flags 🌍[/dim]", border_style="red"),
    )
    console.print(grid)
    console.print()


def print_vendor_detail(r: Dict[str, Any]):
    sc = {"Open": "yellow", "In Remediation": "orange3", "Accepted": "blue", "Closed": "green"}.get(r["status"], "white")
    console.print(Rule(
        f"[bold]{r['name']}[/bold]  ·  {r['service']}  ·  [{sc}]{r['status']}[/{sc}]",
        style="blue"
    ))
    console.print()

    factors = Table(title="Risk Factor Breakdown", box=box.ROUNDED, header_style="bold blue", padding=(0, 1))
    factors.add_column("Factor", style="white", min_width=22)
    factors.add_column("Value", style="cyan", min_width=26)
    factors.add_column("Framework Ref", style="dim", min_width=28)
    factors.add_row("Data Sensitivity", r["data_sensitivity"], "ISO 27001 A.5.12 / A.8.10")
    factors.add_row("Hosting Location", r["hosting"], "UK GDPR Art.44 / FCA SS2/21")
    factors.add_row("AI Usage", r["ai_usage"], "ISO 42001 / FCA AI Principles")
    factors.add_row("Subcontractors", r["subcontractors"], "ISO 27001 A.5.19–A.5.22")
    factors.add_row("Service Criticality", r["criticality"], "EBA GL/2019/02")
    factors.add_row("Outsourcing Type", r["outsourcing_type"], "FCA SS2/21")

    scores = Table(title="Risk Scores", box=box.ROUNDED, header_style="bold blue", padding=(0, 1))
    scores.add_column("Type", style="white", min_width=18)
    scores.add_column("Score", justify="center", min_width=8)
    scores.add_column("Tier", justify="center", min_width=14)
    scores.add_row(
        "Inherent Risk",
        str(r["inherent_score"]),
        f"{r['inherent_icon']} [{r['inherent_color']}]{r['inherent_tier']}[/{r['inherent_color']}]",
    )
    scores.add_row(
        "Residual Risk",
        str(r["residual_score"]),
        f"{r['residual_icon']} [{r['residual_color']}][bold]{r['residual_tier']}[/bold][/{r['residual_color']}]",
    )

    console.print(Columns([factors, scores], padding=2))

    gov = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    gov.add_column("Field", style="dim", min_width=26)
    gov.add_column("Value", style="white")
    gov.add_row("Risk Owner", r["risk_owner"])

    rd = r["review_date"]
    if r["review_overdue"]:
        rd = f"[bold red]⚠  {rd}  (OVERDUE by {abs(r['review_days'])} days)[/bold red]"
    elif r["review_due_soon"]:
        rd = f"[yellow]⚠  {rd}  (due in {r['review_days']} days)[/yellow]"
    gov.add_row("Review Date", rd)
    gov.add_row("Outsourcing Classification", r["outsourcing_type"])
    console.print(gov)
    console.print()

    if r["ai_flag"]:
        console.print(Panel(
            "[bold yellow]⚠  AI VENDOR FLAG — ISO 42001 Gap[/bold yellow]\n"
            "Vendor uses third-party or autonomous AI without ISO 42001 certification.\n\n"
            "[bold]AI Enhanced Due Diligence Checklist:[/bold]\n"
            + "\n".join(f"  [dim]□[/dim]  {q}" for q in AI_DUE_DILIGENCE)
            + "\n\n[dim]Action: Request AI governance pack including model cards, DPIA, and evaluation results.[/dim]",
            border_style="yellow", padding=(0, 2)
        ))

    if r["gdpr_flag"]:
        console.print(Panel(
            "[bold red]⚠  GDPR CROSS-BORDER TRANSFER FLAG[/bold red]\n"
            "Data hosted outside UK/EU. International transfer safeguards required.\n"
            "[dim]Action: Validate SCCs / adequacy + perform Transfer Impact Assessment (TIA).[/dim]",
            border_style="red", padding=(0, 2)
        ))

    if r["critical_jurisdiction"]:
        console.print(Panel(
            "[bold red]🔴  CRITICAL SERVICE IN HIGH-RISK JURISDICTION[/bold red]\n"
            "Critical service hosted in high-risk jurisdiction — immediate escalation required.\n"
            "[dim]Action: Escalate to Risk Committee. Consider alternative provider assessment.[/dim]",
            border_style="red", padding=(0, 2)
        ))

    if r["control_domains"]:
        cd = Table(
            title="ISO 27001 / Governance Domains Impacted",
            box=box.SIMPLE,
            header_style="bold blue",
            padding=(0, 1),
        )
        cd.add_column("Control Domain", style="white", min_width=30)
        cd.add_column("Reference", style="dim", min_width=40)
        for d in r["control_domains"]:
            cd.add_row(d["domain"], d["ref"])
        console.print(cd)

    ev = Table(
        title="Evidence Required for Assurance Review",
        box=box.SIMPLE,
        header_style="bold blue",
        padding=(0, 1),
    )
    ev.add_column("#", style="dim", width=4)
    ev.add_column("Evidence Item", style="white", min_width=70)
    for i, e in enumerate(r["evidence_required"], 1):
        ev.add_row(str(i), e)
    console.print(ev)

    console.print()
    if r["certifications"]:
        labels = [CERTIFICATIONS[c]["label"] for c in r["certifications"] if c in CERTIFICATIONS]
        console.print(f"  [green]✓  Certifications held:[/green] {', '.join(labels)}")
    else:
        console.print("  [red]✗  No certifications held — no residual risk reduction applied[/red]")
    console.print()


def print_summary(results: List[Dict[str, Any]]):
    console.print(Rule("[bold]Third-Party Portfolio — Risk Summary[/bold]", style="blue"))
    console.print()

    tbl = Table(box=box.ROUNDED, header_style="bold white on blue", padding=(0, 1))
    tbl.add_column("Vendor", style="white", min_width=20)
    tbl.add_column("Service", style="cyan", min_width=20)
    tbl.add_column("Outsourcing", style="dim", min_width=14)
    tbl.add_column("Owner", style="dim", min_width=18)
    tbl.add_column("Inherent", justify="center", min_width=9)
    tbl.add_column("Residual", justify="center", min_width=9)
    tbl.add_column("Tier", justify="center", min_width=14)
    tbl.add_column("Review", justify="center", min_width=12)
    tbl.add_column("Status", justify="center", min_width=14)
    tbl.add_column("Flags", justify="center", min_width=6)

    for r in sorted(results, key=lambda x: x["residual_score"], reverse=True):
        flags = ("🤖 " if r["ai_flag"] else "") + ("🌍 " if r["gdpr_flag"] else "") + ("🔴" if r["critical_jurisdiction"] else "")
        rd = r["review_date"]
        if r["review_overdue"]:
            rd = f"[red]{rd}[/red]"
        elif r["review_due_soon"]:
            rd = f"[yellow]{rd}[/yellow]"

        sc = {"Open": "yellow", "In Remediation": "orange3", "Accepted": "blue", "Closed": "green"}.get(r["status"], "white")
        tbl.add_row(
            r["name"], r["service"], r["outsourcing_type"], r["risk_owner"],
            str(r["inherent_score"]), str(r["residual_score"]),
            f"{r['residual_icon']} [{r['residual_color']}][bold]{r['residual_tier']}[/bold][/{r['residual_color']}]",
            rd,
            f"[{sc}]{r['status']}[/{sc}]",
            flags or "—",
        )

    console.print(tbl)
    console.print()

    overdue = [r for r in results if r["review_overdue"]]
    due_soon = [r for r in results if r["review_due_soon"]]
    if overdue or due_soon:
        alerts: List[str] = []
        for r in overdue:
            alerts.append(f"[red]⚠  {r['name']} — overdue by {abs(r['review_days'])} days[/red]")
        for r in due_soon:
            alerts.append(f"[yellow]⚠  {r['name']} — due in {r['review_days']} days[/yellow]")

        console.print(Panel(
            "\n".join(alerts),
            title="[bold]Committee Attention — Review Schedule Alerts[/bold]",
            border_style="red",
            padding=(0, 2),
        ))
        console.print()

    dist = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
    dist.add_column("Tier")
    dist.add_column("Count", justify="center")
    for tier in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        n = sum(1 for r in results if r["residual_tier"] == tier)
        col = {"CRITICAL": "red", "HIGH": "orange3", "MEDIUM": "yellow", "LOW": "green"}[tier]
        icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}[tier]
        dist.add_row(f"{icon} [{col}]{tier}[/{col}]", str(n))

    console.print(Panel(dist, title="[bold]Portfolio Risk Distribution[/bold]", border_style="blue", padding=(0, 2)))
    console.print()

    console.print(Panel(
        "[dim]Assessment aligned to:\n"
        "· ISO/IEC 27001:2022 — Information Security Management\n"
        "· ISO/IEC 42001:2023 — AI Management Systems\n"
        "· FCA SS2/21         — Outsourcing and Third Party Risk Management\n"
        "· EBA GL/2019/02     — ICT and Security Risk Management\n"
        "· UK GDPR            — International Data Transfer Requirements[/dim]",
        title="[bold]Methodology Reference[/bold]",
        border_style="dim",
        padding=(0, 2),
    ))
    console.print()


# ─── Exports ──────────────────────────────────────────────────────────────────

def export_committee_report(results: List[Dict[str, Any]]):
    os.makedirs("reports", exist_ok=True)
    today = datetime.date.today().strftime("%d %B %Y")

    lines = [
        "# TPRM Committee Pack",
        f"**Assessment Date:** {today}  ",
        "**Classification:** Internal — Risk Committee  ",
        "**Framework:** ISO 27001:2022 · ISO 42001:2023 · FCA SS2/21 · EBA GL/2019/02 · UK GDPR",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"This report covers the third-party risk assessment of **{len(results)} vendors**.",
        "",
        "### Portfolio Risk Distribution",
        "",
        "| Tier | Count |",
        "|---|---|",
    ]

    for t in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        lines.append(f"| {t} | {sum(1 for r in results if r['residual_tier'] == t)} |")

    lines += ["", "---", "", "## Vendor Risk Register", ""]

    for r in sorted(results, key=lambda x: x["residual_score"], reverse=True):
        lines += [
            f"### {r['residual_icon']} {r['name']}",
            f"**Service:** {r['service']}  ",
            f"**Risk Owner:** {r['risk_owner']}  ",
            f"**Outsourcing Type:** {r['outsourcing_type']}  ",
            f"**Status:** {r['status']}  ",
            f"**Review Date:** {r['review_date']}  ",
            "",
            "| Score Type | Score | Tier |",
            "|---|---|---|",
            f"| Inherent Risk | {r['inherent_score']}/100 | {r['inherent_tier']} |",
            f"| Residual Risk | {r['residual_score']}/100 | {r['residual_tier']} |",
            "",
        ]

        flags: List[str] = []
        if r["ai_flag"]:
            flags.append("⚠ AI Governance Flag — ISO 42001 certification absent")
        if r["gdpr_flag"]:
            flags.append("⚠ GDPR Cross-Border Transfer Flag")
        if r["critical_jurisdiction"]:
            flags.append("🔴 Critical service in high-risk jurisdiction")

        if flags:
            lines.append("**Flags:**")
            lines += [f"- {f}" for f in flags]
            lines.append("")

        if r["control_domains"]:
            lines.append("**Control Domains Impacted:**")
            lines += [f"- {d['domain']} ({d['ref']})" for d in r["control_domains"]]
            lines.append("")

        lines.append("**Evidence Required:**")
        lines += [f"- {e}" for e in r["evidence_required"]]
        lines += ["", "---", ""]

    overdue = [r for r in results if r["review_overdue"]]
    due_soon = [r for r in results if r["review_due_soon"]]
    if overdue or due_soon:
        lines += ["## Review Schedule Alerts", ""]
        for r in overdue:
            lines.append(f"- ⚠ **{r['name']}** — overdue by {abs(r['review_days'])} days")
        for r in due_soon:
            lines.append(f"- ⚠ **{r['name']}** — due in {r['review_days']} days")
        lines += ["", "---", ""]

    lines += [
        "## Methodology",
        "",
        "Inherent risk scored across five weighted factors: Data Sensitivity, Hosting Location, AI Usage, Subcontractor Exposure, Service Criticality.",
        "Residual risk adjusted by control strength reductions from verified vendor certifications.",
        "Risk Tiers: Low (0–25) · Medium (26–50) · High (51–75) · Critical (76–100)",
        "",
        "*Generated by TPRM Risk Scoring Engine*",
    ]

    out_path = os.path.join("reports", "committee_pack.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    console.print("  [green]✓  Committee report exported → reports/committee_pack.md[/green]")


def export_html(results: List[Dict[str, Any]], charts: Dict[str, str]):
    os.makedirs("reports", exist_ok=True)
    today = datetime.date.today().strftime("%d %B %Y")

    def tier_badge(t: str) -> str:
        return f'<span class="badge badge-{t.lower()}">{t}</span>'

    # Top risks (committee-friendly)
    top_risks = sorted(results, key=lambda x: x["residual_score"], reverse=True)[:3]
    top_html = ""
    for r in top_risks:
        flags = ("🤖 " if r["ai_flag"] else "") + ("🌍 " if r["gdpr_flag"] else "") + ("🔴" if r["critical_jurisdiction"] else "")
        top_html += f"""
        <div class="toprisk">
          <div class="toprisk-title">{r['residual_icon']} {r['name']}</div>
          <div class="toprisk-meta">
            <span class="pill">Residual: <strong>{r['residual_score']}</strong></span>
            <span class="pill">Inherent: <strong>{r['inherent_score']}</strong></span>
            {tier_badge(r['residual_tier'])}
            <span class="pill">Flags: {flags or "—"}</span>
          </div>
        </div>
        """

    vendor_rows = ""
    for r in sorted(results, key=lambda x: x["residual_score"], reverse=True):
        flags = ("🤖 " if r["ai_flag"] else "") + ("🌍 " if r["gdpr_flag"] else "") + ("🔴" if r["critical_jurisdiction"] else "")
        vendor_rows += f"""
        <tr>
          <td><strong>{r['name']}</strong></td>
          <td>{r['service']}</td>
          <td>{r['outsourcing_type']}</td>
          <td>{r['risk_owner']}</td>
          <td class="score">{r['inherent_score']}</td>
          <td class="score">{r['residual_score']}</td>
          <td>{tier_badge(r['residual_tier'])}</td>
          <td>{r['review_date']}</td>
          <td>{r['status']}</td>
          <td>{flags or '—'}</td>
        </tr>
        """

    kpi_data = [
        ("Total Vendors",   len(results),                                              "#58a6ff"),
        ("Critical",        sum(1 for r in results if r["residual_tier"] == "CRITICAL"), TIER_COLORS["CRITICAL"]),
        ("High Risk",       sum(1 for r in results if r["residual_tier"] == "HIGH"),     TIER_COLORS["HIGH"]),
        ("Overdue Reviews", sum(1 for r in results if r["review_overdue"]),              TIER_COLORS["MEDIUM"]),
        ("AI Flags",        sum(1 for r in results if r["ai_flag"]),                     TIER_COLORS["MEDIUM"]),
        ("GDPR Flags",      sum(1 for r in results if r["gdpr_flag"]),                   TIER_COLORS["CRITICAL"]),
    ]
    kpi_html = "".join(
        f'<div class="kpi-card"><div class="kpi-num" style="color:{c}">{n}</div><div class="kpi-label">{l}</div></div>'
        for l, n, c in kpi_data
    )

    # Only render charts that exist
    chart_blocks = ""
    if charts.get("donut") or charts.get("bars"):
        chart_blocks += '<div class="chart-grid">'
        if charts.get("donut"):
            chart_blocks += f'<img src="data:image/png;base64,{charts["donut"]}" alt="Risk Distribution">'
        if charts.get("bars"):
            chart_blocks += f'<img src="data:image/png;base64,{charts["bars"]}" alt="Inherent vs Residual">'
        chart_blocks += "</div>"
    if charts.get("heatmap"):
        chart_blocks += f'<div class="chart-wide"><img src="data:image/png;base64,{charts["heatmap"]}" alt="Risk Heatmap"></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TPRM Risk Scoring Engine — Committee Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0d1117;color:#e6edf3;font-family:'Segoe UI',Arial,sans-serif;padding:32px}}
  h1{{font-size:1.8rem;color:#58a6ff;margin-bottom:4px}}
  .subtitle{{color:#8b949e;font-size:.9rem;margin-bottom:24px}}
  .kpi-grid{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:28px}}
  .kpi-card{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:20px 28px;min-width:130px;text-align:center}}
  .kpi-num{{font-size:2rem;font-weight:700}}
  .kpi-label{{font-size:.8rem;color:#8b949e;margin-top:4px}}
  .section{{margin-bottom:36px}}
  .section h2{{font-size:1.1rem;color:#58a6ff;margin-bottom:14px;border-bottom:1px solid #21262d;padding-bottom:8px}}
  .toprisk{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px 18px;margin:10px 0}}
  .toprisk-title{{font-weight:700;margin-bottom:8px}}
  .toprisk-meta{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
  .pill{{background:#0d1117;border:1px solid #21262d;border-radius:999px;padding:6px 10px;color:#c9d1d9;font-size:.8rem}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  thead th{{position:sticky;top:0;z-index:1}}
  th{{background:#161b22;color:#8b949e;text-align:left;padding:10px 12px;font-weight:600;border-bottom:1px solid #21262d}}
  td{{padding:10px 12px;border-bottom:1px solid #21262d}}
  tr:hover td{{background:#161b22}}
  .score{{font-weight:700;text-align:center}}
  .badge{{padding:3px 10px;border-radius:12px;font-size:.75rem;font-weight:700}}
  .badge-critical{{background:#e74c3c22;color:#e74c3c;border:1px solid #e74c3c}}
  .badge-high{{background:#e67e2222;color:#e67e22;border:1px solid #e67e22}}
  .badge-medium{{background:#f1c40f22;color:#f1c40f;border:1px solid #f1c40f}}
  .badge-low{{background:#2ecc7122;color:#2ecc71;border:1px solid #2ecc71}}
  .chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
  .chart-wide{{margin-bottom:20px}}
  .chart-grid img,.chart-wide img{{width:100%;border-radius:10px;border:1px solid #21262d}}
  .footer{{color:#8b949e;font-size:.8rem;margin-top:40px;border-top:1px solid #21262d;padding-top:16px}}
</style>
</head>
<body>
<h1>TPRM Risk Scoring Engine</h1>
<div class="subtitle">
  Assessment Date: {today} &nbsp;·&nbsp; ISO 27001:2022 &nbsp;·&nbsp;
  ISO 42001:2023 &nbsp;·&nbsp; FCA SS2/21 &nbsp;·&nbsp; EBA GL/2019/02 &nbsp;·&nbsp; UK GDPR
</div>

<div class="section">
  <h2>Portfolio KPI Dashboard</h2>
  <div class="kpi-grid">{kpi_html}</div>
</div>

<div class="section">
  <h2>Committee Attention — Top Risks</h2>
  {top_html if top_html else "<div class='subtitle'>No risks identified.</div>"}
</div>

<div class="section">
  <h2>Risk Visualisation</h2>
  {chart_blocks if chart_blocks else "<div class='subtitle'>Charts unavailable (no data).</div>"}
</div>

<div class="section">
  <h2>Vendor Risk Register</h2>
  <table>
    <thead><tr>
      <th>Vendor</th><th>Service</th><th>Outsourcing</th><th>Owner</th>
      <th>Inherent</th><th>Residual</th><th>Tier</th>
      <th>Review Date</th><th>Status</th><th>Flags</th>
    </tr></thead>
    <tbody>{vendor_rows}</tbody>
  </table>
</div>

<div class="footer">
  Generated by TPRM Risk Scoring Engine
</div>
</body></html>
"""

    out_path = os.path.join("reports", "tprm_report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    console.print("  [green]✓  HTML report exported  → reports/tprm_report.html[/green]")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    print_header()

    data_path = os.path.join(os.path.dirname(__file__), "sample_data", "vendors.json")
    try:
        with open(data_path, encoding="utf-8") as f:
            vendors: List[Dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        console.print("[red]Error:[/red] sample_data/vendors.json not found.")
        return
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] vendors.json is not valid JSON: {e}")
        return

    if not vendors:
        console.print("[yellow]No vendors found in vendors.json[/yellow]")
        return

    console.print(f"[dim]› {len(vendors)} vendors loaded for assessment[/dim]\n")

    results = [assess_vendor(v) for v in vendors]

    print_kpis(results)
    for r in results:
        print_vendor_detail(r)
    print_summary(results)

    console.print(Rule("[bold]Exporting Reports[/bold]", style="blue"))
    console.print()

    charts = make_charts_b64(results, vendors)
    export_committee_report(results)
    export_html(results, charts)

    os.makedirs("reports", exist_ok=True)
    console.save_html(os.path.join("reports", "terminal_output.html"), inline_styles=True)
    console.print("  [green]✓  Terminal snapshot exported → reports/terminal_output.html[/green]")
    console.print("[dim]Tip: open reports/tprm_report.html in your browser for the visual dashboard.[/dim]\n")


if __name__ == "__main__":
    main()
