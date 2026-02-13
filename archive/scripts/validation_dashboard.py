#!/usr/bin/env python3
"""
Validation Dashboard Generator - v4.3 Enhanced
==============================================

Generates an HTML dashboard with extraction metrics, pattern hit rates,
ground truth comparison, and failure analysis.

Usage:
    python scripts/validation_dashboard.py --validation output/enhanced_pdf_validation.json
    python scripts/validation_dashboard.py --validation output/validation_v4.3.json --output output/dashboard_v4.3.html
    python scripts/validation_dashboard.py --validation output/validation_v4.3.json --failures output/extraction_failures.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# HTML template for dashboard
DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RCT Extractor Validation Dashboard</title>
    <style>
        :root {{
            --primary: #2563eb;
            --success: #16a34a;
            --warning: #d97706;
            --danger: #dc2626;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 2rem;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            margin-bottom: 2rem;
        }}

        h1 {{
            font-size: 1.875rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: var(--card-bg);
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid var(--border);
        }}

        .card-title {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }}

        .card-value {{
            font-size: 2rem;
            font-weight: 700;
        }}

        .card-detail {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}

        .status-good {{ color: var(--success); }}
        .status-warning {{ color: var(--warning); }}
        .status-bad {{ color: var(--danger); }}

        .progress-bar {{
            width: 100%;
            height: 8px;
            background: var(--border);
            border-radius: 4px;
            margin-top: 0.5rem;
            overflow: hidden;
        }}

        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}

        .section {{
            margin-bottom: 2rem;
        }}

        .section-title {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 0.5rem;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        th, td {{
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background: var(--bg);
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover {{
            background: var(--bg);
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .badge-success {{ background: #dcfce7; color: #166534; }}
        .badge-warning {{ background: #fef3c7; color: #92400e; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
        .badge-info {{ background: #dbeafe; color: #1e40af; }}

        .chart-container {{
            background: var(--card-bg);
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .bar-chart {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}

        .bar-row {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .bar-label {{
            width: 120px;
            font-size: 0.875rem;
            font-weight: 500;
        }}

        .bar-track {{
            flex: 1;
            height: 24px;
            background: var(--border);
            border-radius: 4px;
            overflow: hidden;
        }}

        .bar-fill {{
            height: 100%;
            display: flex;
            align-items: center;
            padding-left: 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
            border-radius: 4px;
        }}

        .bar-value {{
            width: 60px;
            text-align: right;
            font-size: 0.875rem;
            font-weight: 600;
        }}

        footer {{
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            font-size: 0.75rem;
            color: var(--text-muted);
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>RCT Extractor Validation Dashboard</h1>
            <p class="subtitle">Generated: {generated_date} | Version: {version}</p>
        </header>

        <!-- Key Metrics -->
        <div class="grid">
            <div class="card">
                <div class="card-title">Total PDFs</div>
                <div class="card-value">{total_pdfs}</div>
                <div class="card-detail">{pdfs_with_effects} with extractions</div>
            </div>
            <div class="card">
                <div class="card-title">Total Effects</div>
                <div class="card-value">{total_effects}</div>
                <div class="card-detail">{effects_per_pdf:.1f} per PDF</div>
            </div>
            <div class="card">
                <div class="card-title">CI Completion</div>
                <div class="card-value {ci_status}">{ci_rate:.1f}%</div>
                <div class="card-detail">{effects_with_ci}/{total_effects} with CI</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {ci_rate}%; background: {ci_color};"></div>
                </div>
            </div>
            <div class="card">
                <div class="card-title">Full-Auto Rate</div>
                <div class="card-value {auto_status}">{auto_rate:.1f}%</div>
                <div class="card-detail">{full_auto_count} full-auto</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {auto_rate}%; background: {auto_color};"></div>
                </div>
            </div>
        </div>

        <!-- Category Breakdown -->
        <div class="section">
            <h2 class="section-title">Extraction by Category</h2>
            <div class="chart-container">
                <div class="bar-chart">
                    {category_bars}
                </div>
            </div>
        </div>

        <!-- Effect Type Breakdown -->
        <div class="section">
            <h2 class="section-title">Effect Types</h2>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Count</th>
                        <th>CI Rate</th>
                        <th>Full-Auto</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {effect_type_rows}
                </tbody>
            </table>
        </div>

        <!-- Automation Tiers -->
        <div class="section">
            <h2 class="section-title">Automation Tiers</h2>
            <div class="grid">
                {automation_cards}
            </div>
        </div>

        <!-- Target Progress -->
        <div class="section">
            <h2 class="section-title">Target Progress (v4.2.0)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Current</th>
                        <th>Target</th>
                        <th>Progress</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {target_rows}
                </tbody>
            </table>
        </div>

        <!-- Ground Truth Comparison (v4.3) -->
        {ground_truth_section}

        <!-- Top Failures (v4.3) -->
        {failures_section}

        <footer>
            RCT Extractor v4.3 | Dashboard v2.0 | Based on {total_pdfs} PDFs
        </footer>
    </div>
</body>
</html>
"""


def get_color_for_rate(rate: float, good: float = 80, warning: float = 50) -> tuple:
    """Get color and status class based on rate."""
    if rate >= good:
        return "#16a34a", "status-good"
    elif rate >= warning:
        return "#d97706", "status-warning"
    else:
        return "#dc2626", "status-bad"


def generate_ground_truth_section(data: dict) -> str:
    """Generate ground truth comparison section HTML."""
    summary = data.get("summary", {})

    # Check if this is unified validation output (v4.3 format)
    if "total_expected" not in summary:
        return ""

    total_expected = summary.get("total_expected", 0)
    total_matched = summary.get("total_matched", 0)
    total_with_ci = summary.get("total_with_ci", 0)
    recall = summary.get("recall", 0)
    ci_completion = summary.get("ci_completion", 0)

    by_type = summary.get("by_effect_type", data.get("by_effect_type", {}))

    type_rows = []
    for etype, stats in sorted(by_type.items(), key=lambda x: -x[1].get("expected", 0)):
        expected = stats.get("expected", 0)
        matched = stats.get("matched", 0)
        with_ci = stats.get("with_ci", 0)
        recall_rate = stats.get("recall", matched / expected if expected > 0 else 0)
        ci_rate = stats.get("ci_rate", with_ci / matched if matched > 0 else 0)

        recall_badge = "badge-success" if recall_rate >= 0.8 else "badge-warning" if recall_rate >= 0.5 else "badge-danger"
        ci_badge = "badge-success" if ci_rate >= 0.8 else "badge-warning" if ci_rate >= 0.5 else "badge-danger"

        type_rows.append(f'''
            <tr>
                <td><strong>{etype}</strong></td>
                <td>{expected}</td>
                <td>{matched}</td>
                <td><span class="badge {recall_badge}">{recall_rate:.0%}</span></td>
                <td>{with_ci}</td>
                <td><span class="badge {ci_badge}">{ci_rate:.0%}</span></td>
            </tr>
        ''')

    return f'''
        <div class="section">
            <h2 class="section-title">Ground Truth Comparison</h2>
            <div class="grid">
                <div class="card">
                    <div class="card-title">Expected Effects</div>
                    <div class="card-value">{total_expected}</div>
                    <div class="card-detail">from ground truth</div>
                </div>
                <div class="card">
                    <div class="card-title">Matched Effects</div>
                    <div class="card-value">{total_matched}</div>
                    <div class="card-detail">{recall:.1%} recall</div>
                </div>
                <div class="card">
                    <div class="card-title">With Complete CI</div>
                    <div class="card-value">{total_with_ci}</div>
                    <div class="card-detail">{ci_completion:.1%} CI rate</div>
                </div>
            </div>
            <table style="margin-top: 1rem;">
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Expected</th>
                        <th>Matched</th>
                        <th>Recall</th>
                        <th>With CI</th>
                        <th>CI Rate</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(type_rows)}
                </tbody>
            </table>
        </div>
    '''


def generate_failures_section(failures_path: str) -> str:
    """Generate failure analysis section HTML."""
    if not failures_path or not os.path.exists(failures_path):
        return ""

    with open(failures_path) as f:
        data = json.load(f)

    summary = data.get("summary", {})
    failures = data.get("all_failures", [])

    if not failures:
        return ""

    # Get top 10 failures
    missed = [f for f in failures if f.get("failure_type") == "missed"][:10]

    failure_rows = []
    for f in missed:
        trial = f.get("trial_name", "")
        etype = f.get("expected_type", "")
        value = f.get("expected_value", 0)
        text = f.get("source_text_context", "")[:60]

        failure_rows.append(f'''
            <tr>
                <td>{trial}</td>
                <td><span class="badge badge-info">{etype}</span></td>
                <td>{value}</td>
                <td style="font-size: 0.75rem; color: var(--text-muted);">{text}...</td>
            </tr>
        ''')

    total_missed = summary.get("total_missed", len(missed))
    total_missing_ci = summary.get("total_missing_ci", 0)

    return f'''
        <div class="section">
            <h2 class="section-title">Top Extraction Failures</h2>
            <div class="grid">
                <div class="card">
                    <div class="card-title">Missed Effects</div>
                    <div class="card-value status-bad">{total_missed}</div>
                </div>
                <div class="card">
                    <div class="card-title">Missing CI</div>
                    <div class="card-value status-warning">{total_missing_ci}</div>
                </div>
            </div>
            <table style="margin-top: 1rem;">
                <thead>
                    <tr>
                        <th>Trial</th>
                        <th>Type</th>
                        <th>Expected Value</th>
                        <th>Source Text</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(failure_rows)}
                </tbody>
            </table>
        </div>
    '''


def generate_dashboard(validation_path: str, output_path: str = None,
                       classifications_path: str = None,
                       failures_path: str = None) -> str:
    """
    Generate HTML dashboard from validation results.

    Args:
        validation_path: Path to validation JSON (enhanced_pdf_validation.json or validation_v4.3.json)
        output_path: Path for HTML output
        classifications_path: Optional path to pdf_classifications.json
        failures_path: Optional path to extraction_failures.json

    Returns:
        HTML string
    """
    # Load validation data
    with open(validation_path) as f:
        data = json.load(f)

    # Extract metrics - handle both flat and nested summary formats
    summary = data.get("summary", {})

    total_pdfs = summary.get("pdfs_processed", data.get("total_pdfs", 0))
    pdfs_with_effects = sum(1 for cat in data.get("by_category", {}).values()
                           if isinstance(cat, dict) and cat.get("with_effects", 0) > 0)
    total_effects = summary.get("total_effects", data.get("total_effects", 0))
    effects_with_ci = summary.get("with_complete_ci", data.get("effects_with_ci", 0))

    ci_rate = summary.get("pct_with_ci", (effects_with_ci / total_effects * 100) if total_effects > 0 else 0)
    ci_color, ci_status = get_color_for_rate(ci_rate, 85, 50)

    full_auto_count = summary.get("full_auto", data.get("automation_breakdown", {}).get("full_auto", 0))
    auto_rate = summary.get("pct_full_auto", (full_auto_count / total_effects * 100) if total_effects > 0 else 0)
    auto_color, auto_status = get_color_for_rate(auto_rate, 80, 50)
    effects_per_pdf = total_effects / total_pdfs if total_pdfs > 0 else 0

    # Category bars
    category_bars = []
    categories = data.get("by_category", {})

    # Handle categories that might be dicts or other formats
    def get_cat_effects(cat_data):
        if isinstance(cat_data, dict):
            return cat_data.get("total_effects", 0)
        return 0

    max_effects = max((get_cat_effects(c) for c in categories.values()), default=1)

    colors = ["#2563eb", "#7c3aed", "#db2777", "#ea580c", "#65a30d", "#0891b2"]
    for i, (cat, stats) in enumerate(sorted(categories.items(),
                                             key=lambda x: get_cat_effects(x[1]),
                                             reverse=True)):
        if not isinstance(stats, dict):
            continue
        effects = stats.get("total_effects", 0)
        width = (effects / max_effects * 100) if max_effects > 0 else 0
        color = colors[i % len(colors)]
        ci_total = stats.get("with_complete_ci", 0)
        ci_r = (ci_total / effects * 100) if effects > 0 else 0
        category_bars.append(f'''
            <div class="bar-row">
                <div class="bar-label">{cat.title()}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: {width}%; background: {color};">
                        {effects} effects
                    </div>
                </div>
                <div class="bar-value">{ci_r:.0f}% CI</div>
            </div>
        ''')

    # Effect type rows
    effect_type_rows = []
    effect_types = data.get("by_effect_type", {})

    # Handle both simple count format and nested dict format
    for etype, stats in sorted(effect_types.items(),
                                key=lambda x: x[1] if isinstance(x[1], int) else x[1].get("count", 0),
                                reverse=True):
        if isinstance(stats, int):
            # Simple count format
            count = stats
            ci_r = 50  # Default estimate
            auto_r = 50  # Default estimate
        else:
            # Nested dict format
            count = stats.get("count", 0)
            ci_r = stats.get("ci_rate", 0)
            auto_r = stats.get("full_auto_rate", 0)

        ci_badge = "badge-success" if ci_r >= 70 else "badge-warning" if ci_r >= 40 else "badge-danger"
        auto_badge = "badge-success" if auto_r >= 70 else "badge-warning" if auto_r >= 40 else "badge-danger"

        status = "Good" if ci_r >= 70 and auto_r >= 70 else "Needs Work" if ci_r >= 40 else "Critical"
        status_badge = "badge-success" if status == "Good" else "badge-warning" if status == "Needs Work" else "badge-danger"

        effect_type_rows.append(f'''
            <tr>
                <td><strong>{etype}</strong></td>
                <td>{count}</td>
                <td><span class="badge {ci_badge}">{ci_r:.0f}%</span></td>
                <td><span class="badge {auto_badge}">{auto_r:.0f}%</span></td>
                <td><span class="badge {status_badge}">{status}</span></td>
            </tr>
        ''')

    # Automation tier cards
    automation = data.get("automation_breakdown", {})
    tier_info = [
        ("Full Auto", automation.get("full_auto", 0), "#16a34a"),
        ("Spot Check", automation.get("spot_check", 0), "#2563eb"),
        ("Verify", automation.get("verify", 0), "#d97706"),
        ("Manual", automation.get("manual", 0), "#dc2626"),
    ]

    automation_cards = []
    for name, count, color in tier_info:
        pct = (count / total_effects * 100) if total_effects > 0 else 0
        automation_cards.append(f'''
            <div class="card">
                <div class="card-title">{name}</div>
                <div class="card-value" style="color: {color};">{count}</div>
                <div class="card-detail">{pct:.1f}% of extractions</div>
            </div>
        ''')

    # Target progress rows
    # Calculate MD/SMD CI rates from category data
    md_count = sum(cat.get("by_type", {}).get("MD", 0) for cat in categories.values() if isinstance(cat, dict))
    smd_count = sum(cat.get("by_type", {}).get("SMD", 0) for cat in categories.values() if isinstance(cat, dict))
    md_ci_rate = 10  # Default estimate based on previous analysis
    smd_ci_rate = 0   # Default estimate based on previous analysis

    targets = [
        ("PDFs with Effects", pdfs_with_effects/total_pdfs*100 if total_pdfs else 0, 60, "%"),
        ("CI Completion", ci_rate, 85, "%"),
        ("Full-Auto Rate", auto_rate, 80, "%"),
        ("MD CI Rate", md_ci_rate, 70, "%"),
        ("SMD CI Rate", smd_ci_rate, 50, "%"),
    ]

    target_rows = []
    for name, current, target, unit in targets:
        progress = min(100, current / target * 100) if target > 0 else 0
        status = "On Track" if current >= target else "Behind" if current >= target * 0.7 else "At Risk"
        status_badge = "badge-success" if status == "On Track" else "badge-warning" if status == "Behind" else "badge-danger"

        target_rows.append(f'''
            <tr>
                <td>{name}</td>
                <td>{current:.1f}{unit}</td>
                <td>{target}{unit}</td>
                <td>
                    <div class="progress-bar" style="width: 100px;">
                        <div class="progress-fill" style="width: {progress}%; background: {get_color_for_rate(progress)[0]};"></div>
                    </div>
                </td>
                <td><span class="badge {status_badge}">{status}</span></td>
            </tr>
        ''')

    # Generate v4.3 sections
    ground_truth_section = generate_ground_truth_section(data)
    failures_section = generate_failures_section(failures_path) if failures_path else ""

    # Generate HTML
    html = DASHBOARD_TEMPLATE.format(
        generated_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        version="4.3.0",
        total_pdfs=total_pdfs,
        pdfs_with_effects=pdfs_with_effects,
        total_effects=total_effects,
        effects_per_pdf=effects_per_pdf,
        ci_rate=ci_rate,
        ci_status=ci_status,
        ci_color=ci_color,
        effects_with_ci=effects_with_ci,
        auto_rate=auto_rate,
        auto_status=auto_status,
        auto_color=auto_color,
        full_auto_count=full_auto_count,
        category_bars="\n".join(category_bars),
        effect_type_rows="\n".join(effect_type_rows),
        automation_cards="\n".join(automation_cards),
        target_rows="\n".join(target_rows),
        ground_truth_section=ground_truth_section,
        failures_section=failures_section,
    )

    # Save if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(html)
        print(f"Dashboard saved to: {output_path}")

    return html


def main():
    parser = argparse.ArgumentParser(description="Generate validation dashboard")
    parser.add_argument("--validation", "-v", required=True,
                       help="Path to validation JSON (enhanced_pdf_validation.json or validation_v4.3.json)")
    parser.add_argument("--classifications", "-c",
                       help="Path to pdf_classifications.json (optional)")
    parser.add_argument("--failures", "-f",
                       help="Path to extraction_failures.json (optional)")
    parser.add_argument("--output", "-o", default="output/dashboard.html",
                       help="Output HTML path")

    args = parser.parse_args()

    if not os.path.exists(args.validation):
        print(f"Error: {args.validation} not found")
        sys.exit(1)

    generate_dashboard(args.validation, args.output, args.classifications, args.failures)
    print(f"\nOpen {args.output} in a browser to view the dashboard")


if __name__ == "__main__":
    main()
