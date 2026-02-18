import json
import os
import csv
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich import box

console = Console(record=True)

# ─── Validation Schema ────────────────────────────────────────────────────────

MANDATORY_FIELDS = [
    "vendor_name", "service_type", "data_classification",
    "encryption_at_rest", "encryption_in_transit", "mfa_enforced",
    "incident_response_plan", "bcdr_tested", "penetration_test_date",
    "subprocessors_disclosed", "data_residency",
    "vulnerability_management", "access_control_policy", "contact_name",
]
# Note: certifications removed from mandatory — treated as amber risk only

RED_RISKS = {
    "encryption_at_rest":      {"fail_values":["no","false",False],"message":"No encryption at rest — data exposure risk","ref":"ISO 27001 A.8.24"},
    "encryption_in_transit":   {"fail_values":["no","false",False],"message":"No encryption in transit — interception risk","ref":"ISO 27001 A.8.24"},
    "mfa_enforced":            {"fail_values":["no","false",False],"message":"MFA not enforced — unauthorised access risk","ref":"ISO 27001 A.5.17"},
    "incident_response_plan":  {"fail_values":["no","false",False],"message":"No incident response plan — regulatory breach risk","ref":"ISO 27001 A.5.26"},
    "bcdr_tested":             {"fail_values":["no","false",False],"message":"BCP/DR not tested — resilience risk","ref":"ISO 27001 A.5.30"},
    "subprocessors_disclosed": {"fail_values":["no","false",False],"message":"Subprocessors not disclosed — fourth-party risk","ref":"ISO 27001 A.5.19 / UK GDPR Art.28"},
    "vulnerability_management":{"fail_values":["no","false",False],"message":"No vulnerability management process — patching risk","ref":"ISO 27001 A.8.8"},
    "access_control_policy":   {"fail_values":["no","false",False],"message":"No access control policy — privilege escalation risk","ref":"ISO 27001 A.5.15"},
}

HIGH_RISK_JURISDICTIONS = [
    "china","prc","mainland china","hong kong",
    "russia","russian federation","ru",
    "iran","iran (tehran)","ir",
    "north korea","dprk","kp",
    "belarus","by",
]

STATUS_COLORS  = {"Approved":"green","Conditional":"yellow","Reject":"red"}
STATUS_ICONS   = {"Approved":"✅","Conditional":"⚠️","Reject":"❌"}
MATERIALITY    = ["non-material","material","critical"]


# ─── Validation Logic ─────────────────────────────────────────────────────────

def check_missing(q):
    """Only treat None, empty string, empty list as missing — not False."""
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

    # Pen test age — stricter for material/critical suppliers
    pt = q.get("penetration_test_date","")
    if pt:
        try:
            age = (datetime.date.today() - datetime.date.fromisoformat(pt)).days
            if age > 365:
                flags.append({
                    "field":   "penetration_test_date",
                    "message": f"Pen test is {age} days old (>12 months)",
                    "ref":     "ISO 27001 A.8.8 / FCA SS2/21",
                    "escalate_to_red": is_mat,
                })
        except Exception:
            flags.append({"field":"penetration_test_date","message":"Invalid pen test date format","ref":"—","escalate_to_red":False})
    else:
        flags.append({"field":"penetration_test_date","message":"No pen test date provided","ref":"ISO 27001 A.8.8","escalate_to_red":is_mat})

    # Certifications — amber only
    if not q.get("certifications"):
        flags.append({"field":"certifications","message":"No certifications held — limited independent assurance","ref":"ISO 27001 A.5.19","escalate_to_red":False})

    # Jurisdiction
    residency = q.get("data_residency","").lower()
    for jr in HIGH_RISK_JURISDICTIONS:
        if jr in residency:
            flags.append({
                "field":   "data_residency",
                "message": f"Data residency in high-risk jurisdiction: {q.get('data_residency')}",
                "ref":     "UK GDPR Art.44 / FCA SS2/21",
                "escalate_to_red": is_mat,
            })
            break

    return flags

def determine_status(missing, red, amber):
    if missing or red:
        return "Reject"
    # Escalate amber to Reject for material/critical suppliers
    if any(a.get("escalate_to_red") for a in amber):
        return "Reject"
    if amber:
        return "Conditional"
    return "Approved"

def build_rationale(missing, red, amber, status):
    if status == "Reject":
        reasons = []
        if missing: reasons.append(f"{len(missing)} mandatory field(s) missing")
        if red:     reasons.append(f"{len(red)} critical control failure(s)")
        escalated = [a for a in amber if a.get("escalate_to_red")]
        if escalated: reasons.append(f"{len(escalated)} amber risk(s) escalated due to materiality")
        return "Rejected because: " + "; ".join(reasons)
    elif status == "Conditional":
        return f"Conditional because: {len(amber)} amber risk(s) require remediation within agreed timeframe"
    return "Approved: all mandatory controls satisfied and no risks identified"

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
        "status_color":   STATUS_COLORS[status],
        "status_icon":    STATUS_ICONS[status],
        "rationale":      build_rationale(missing, red, amber, status),
    }


# ─── Display ──────────────────────────────────────────────────────────────────

def print_header():
    console.print()
    console.print(Panel.fit(
        "[bold white]Supplier Due Diligence Validator[/bold white]\n"
        "[dim]Third-Party Onboarding Assessment Tool[/dim]\n"
        "[dim]ISO 27001:2022  ·  FCA SS2/21  ·  EBA GL/2019/02  ·  UK GDPR Art.28[/dim]\n"
        f"[dim]Assessment Date: {datetime.date.today().strftime('%d %B %Y')}[/dim]",
        border_style="blue", padding=(1,4)
    ))
    console.print()

def print_vendor_result(r):
    sc = r["status_color"]
    console.print(Rule(
        f"[bold]{r['vendor_name']}[/bold]  ·  {r['service_type']}  ·  "
        f"[{sc}]{r['status_icon']} {r['status']}[/{sc}]",
        style="blue"
    ))
    console.print()

    ov = Table(box=box.ROUNDED, show_header=False, padding=(0,1))
    ov.add_column("Field", style="dim",   min_width=24)
    ov.add_column("Value", style="white", min_width=32)
    ov.add_row("Contact",               r["contact"])
    ov.add_row("Data Classification",   r["data_class"])
    ov.add_row("Data Residency",        r["data_residency"])
    ov.add_row("Outsourcing Type",      r["outsourcing"])
    certs = ", ".join(r["certifications"]) if r["certifications"] else "[red]None[/red]"
    ov.add_row("Certifications",        certs)
    ov.add_row("Assurance Status",      f"[{sc}][bold]{r['status_icon']} {r['status']}[/bold][/{sc}]")
    ov.add_row("Rationale",             f"[dim]{r['rationale']}[/dim]")
    console.print(ov)
    console.print()

    if r["missing_fields"]:
        mf = Table(title="[red]Missing Mandatory Fields[/red]", box=box.SIMPLE,
                   header_style="bold red", padding=(0,1))
        mf.add_column("#",      style="dim",   width=4)
        mf.add_column("Field",  style="white", min_width=30)
        mf.add_column("Action", style="dim",   min_width=35)
        for i, f in enumerate(r["missing_fields"], 1):
            mf.add_row(str(i), f.replace("_"," ").title(), "Request from vendor before proceeding")
        console.print(mf)
        console.print()

    if r["red_risks"]:
        console.print(Panel(
            "[bold red]🔴 RED RISKS — REJECT[/bold red]\n"
            "Critical control failures requiring immediate remediation:\n\n" +
            "\n".join(
                f"  [red]✗[/red]  {rk['message']}\n     [dim]Ref: {rk['ref']}[/dim]"
                for rk in r["red_risks"]
            ),
            border_style="red", padding=(0,2)
        ))
        console.print()

    escalated = [a for a in r["amber_risks"] if a.get("escalate_to_red")]
    standard_amber = [a for a in r["amber_risks"] if not a.get("escalate_to_red")]

    if escalated:
        console.print(Panel(
            "[bold red]🔴 AMBER RISKS ESCALATED TO RED (Material/Critical Supplier)[/bold red]\n" +
            "\n".join(
                f"  [red]✗[/red]  {a['message']}\n     [dim]Ref: {a['ref']}[/dim]"
                for a in escalated
            ),
            border_style="red", padding=(0,2)
        ))
        console.print()

    if standard_amber:
        console.print(Panel(
            "[bold yellow]⚠  AMBER RISKS — CONDITIONAL[/bold yellow]\n"
            "Items requiring review or remediation within agreed timeframe:\n\n" +
            "\n".join(
                f"  [yellow]△[/yellow]  {a['message']}\n     [dim]Ref: {a['ref']}[/dim]"
                for a in standard_amber
            ),
            border_style="yellow", padding=(0,2)
        ))
        console.print()

    if not r["missing_fields"] and not r["red_risks"] and not r["amber_risks"]:
        console.print(Panel(
            "[bold green]✅ ALL CONTROLS SATISFIED — APPROVED[/bold green]\n"
            "Vendor has met all mandatory due diligence requirements.",
            border_style="green", padding=(0,2)
        ))
    console.print()

def print_summary(results):
    console.print(Rule("[bold]Supplier Due Diligence — Portfolio Summary[/bold]", style="blue"))
    console.print()

    tbl = Table(box=box.ROUNDED, header_style="bold white on blue", padding=(0,1))
    tbl.add_column("Vendor",      style="white",  min_width=20)
    tbl.add_column("Service",     style="cyan",   min_width=18)
    tbl.add_column("Materiality", style="dim",    min_width=13)
    tbl.add_column("Data Class",  style="dim",    min_width=16)
    tbl.add_column("Residency",   style="dim",    min_width=16)
    tbl.add_column("Red",         justify="center", min_width=6)
    tbl.add_column("Amber",       justify="center", min_width=7)
    tbl.add_column("Missing",     justify="center", min_width=8)
    tbl.add_column("Status",      justify="center", min_width=14)

    for r in sorted(results, key=lambda x: ["Reject","Conditional","Approved"].index(x["status"])):
        sc = r["status_color"]
        tbl.add_row(
            r["vendor_name"], r["service_type"], r["outsourcing"],
            r["data_class"],  r["data_residency"],
            f"[red]{len(r['red_risks'])}[/red]"      if r["red_risks"]      else "[dim]0[/dim]",
            f"[yellow]{len(r['amber_risks'])}[/yellow]" if r["amber_risks"] else "[dim]0[/dim]",
            f"[red]{len(r['missing_fields'])}[/red]" if r["missing_fields"] else "[dim]0[/dim]",
            f"[{sc}][bold]{r['status_icon']} {r['status']}[/bold][/{sc}]",
        )
    console.print(tbl)
    console.print()

    dist = Table(box=box.SIMPLE, show_header=False, padding=(0,3))
    dist.add_column("Status"); dist.add_column("Count", justify="center")
    for s, col in [("Reject","red"),("Conditional","yellow"),("Approved","green")]:
        dist.add_row(f"[{col}]{STATUS_ICONS[s]} {s}[/{col}]",
                     str(sum(1 for r in results if r["status"]==s)))
    console.print(Panel(dist, title="[bold]Assessment Distribution[/bold]",
                        border_style="blue", padding=(0,2)))
    console.print()

    console.print(Panel(
        "[dim]Validation aligned to:\n"
        "· ISO/IEC 27001:2022 — Information Security Management\n"
        "· FCA SS2/21         — Outsourcing and Third Party Risk\n"
        "· EBA GL/2019/02     — ICT and Security Risk Management\n"
        "· UK GDPR Art.28     — Processor Due Diligence[/dim]",
        title="[bold]Methodology Reference[/bold]",
        border_style="dim", padding=(0,2)
    ))
    console.print()


# ─── Export ───────────────────────────────────────────────────────────────────

def export_markdown(results):
    today = datetime.date.today().strftime("%d %B %Y")
    lines = [
        "# Supplier Due Diligence Validation Report",
        f"**Assessment Date:** {today}  ",
        "**Classification:** Internal — Risk & Compliance  ",
        "**Framework:** ISO 27001:2022 · FCA SS2/21 · EBA GL/2019/02 · UK GDPR Art.28",
        "","---","","## Executive Summary","",
        f"Due diligence validation completed for **{len(results)} suppliers**.", "",
        "| Status | Count |","|---|---|",
    ]
    for s in ["Reject","Conditional","Approved"]:
        lines.append(f"| {STATUS_ICONS[s]} {s} | {sum(1 for r in results if r['status']==s)} |")
    lines += ["","---","","## Supplier Assessment Detail",""]
    for r in sorted(results, key=lambda x: ["Reject","Conditional","Approved"].index(x["status"])):
        lines += [
            f"### {r['status_icon']} {r['vendor_name']}",
            f"**Service:** {r['service_type']}  ",
            f"**Contact:** {r['contact']}  ",
            f"**Outsourcing Type:** {r['outsourcing']}  ",
            f"**Data Classification:** {r['data_class']}  ",
            f"**Data Residency:** {r['data_residency']}  ",
            f"**Assurance Status:** {r['status']}  ",
            f"**Rationale:** {r['rationale']}  ","",
        ]
        if r["missing_fields"]:
            lines.append("**Missing Mandatory Fields:**")
            lines += [f"- {f.replace('_',' ').title()}" for f in r["missing_fields"]]
            lines.append("")
        if r["red_risks"]:
            lines.append("**🔴 Red Risks:**")
            lines += [f"- {rk['message']} *(Ref: {rk['ref']})*" for rk in r["red_risks"]]
            lines.append("")
        if r["amber_risks"]:
            lines.append("**⚠ Amber Risks:**")
            lines += [f"- {a['message']} *(Ref: {a['ref']})*" for a in r["amber_risks"]]
            lines.append("")
        lines += ["---",""]
    lines += [
        "## Methodology","",
        "**Reject** — mandatory fields missing, red risks identified, or amber risks escalated due to materiality.",
        "**Conditional** — amber risks present requiring remediation within agreed timeframe.",
        "**Approved** — all mandatory controls satisfied, no risks identified.",
        "","*Generated by Supplier Due Diligence Validator — Ajibola Yusuff*",
    ]
    path = os.path.join("reports","validation_report.md")
    with open(path,"w",encoding="utf-8") as f:
        f.write("\n".join(lines))
    console.print("  [green]✓  Markdown report exported → reports/validation_report.md[/green]")

def export_csv(results):
    path = os.path.join("reports","validation_summary.csv")
    with open(path,"w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "vendor","service","outsourcing","data_class","residency",
            "red_count","amber_count","missing_count","status","rationale"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "vendor":        r["vendor_name"],
                "service":       r["service_type"],
                "outsourcing":   r["outsourcing"],
                "data_class":    r["data_class"],
                "residency":     r["data_residency"],
                "red_count":     len(r["red_risks"]),
                "amber_count":   len(r["amber_risks"]),
                "missing_count": len(r["missing_fields"]),
                "status":        r["status"],
                "rationale":     r["rationale"],
            })
    console.print("  [green]✓  CSV summary exported      → reports/validation_summary.csv[/green]")

def export_reports(results):
    os.makedirs("reports", exist_ok=True)
    export_markdown(results)
    export_csv(results)
    console.save_html(os.path.join("reports","terminal_output.html"), inline_styles=True)
    console.print("  [green]✓  Terminal snapshot exported → reports/terminal_output.html[/green]\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    print_header()
    path = os.path.join(os.path.dirname(__file__),"sample_data","questionnaires.json")
    try:
        with open(path, encoding="utf-8") as f:
            questionnaires = json.load(f)
    except FileNotFoundError:
        console.print("[red]Error:[/red] sample_data/questionnaires.json not found."); return
    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON: {e}"); return

    console.print(f"[dim]› {len(questionnaires)} supplier questionnaires loaded[/dim]\n")
    results = [validate(q) for q in questionnaires]
    for r in results:
        print_vendor_result(r)
    print_summary(results)

    console.print(Rule("[bold]Exporting Reports[/bold]", style="blue"))
    console.print()
    export_reports(results)

if __name__ == "__main__":
    main()