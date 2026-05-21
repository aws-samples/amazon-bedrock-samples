"""
Report generator module.
Creates HTML and PDF reports with accuracy graphs and insights.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Optional


def load_iteration_reports(report_dir: str = ".", session_id: str = None) -> list[dict[str, Any]]:
    """
    Load iteration reports from directory, optionally filtered by session.
    
    Args:
        report_dir: Directory containing evaluation report JSON files
        session_id: If provided, only load reports from this session
    
    Returns:
        List of report dictionaries sorted by iteration
    """
    reports = []
    
    if not os.path.exists(report_dir):
        return reports
    
    for filename in os.listdir(report_dir):
        if filename.endswith(".json") and ("eval_" in filename or "evaluation_report" in filename):
            filepath = os.path.join(report_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    report = json.load(f)
                
                # Extract iteration number and session from filename
                # Format: eval_YYYYMMDD_HHMMSS_iterN.json or evaluation_report_iterN.json
                iter_match = re.search(r'iter(\d+)', filename)
                session_match = re.search(r'eval_(\d{8}_\d{6})', filename)
                
                if iter_match:
                    report["iteration"] = int(iter_match.group(1))
                if session_match:
                    report["session_id"] = session_match.group(1)
                
                report["filename"] = filename
                
                # Filter by session_id if provided
                if session_id is None or report.get("session_id") == session_id:
                    reports.append(report)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {filename}: {e}")
    
    # Sort by iteration number
    return sorted(reports, key=lambda x: x.get("iteration", 0))


def generate_html_report(
    reports: list[dict[str, Any]],
    output_path: str = "optimization_report.html",
    best_config: dict[str, Any] = None,
    best_accuracy: float = None,
    iteration_changes: list[dict[str, Any]] = None
) -> str:
    """
    Generate HTML report with multi-metric graphs, insights, iteration changes, and config appendix.
    
    Args:
        reports: List of iteration reports
        output_path: Output HTML file path
        best_config: Best guardrail configuration to include as appendix
        best_accuracy: Best accuracy achieved
        iteration_changes: List of changes made per iteration
    
    Returns:
        Path to generated HTML file
    """
    # Extract metrics for charting
    iterations = [r.get("iteration", i+1) for i, r in enumerate(reports)]
    accuracies = [r.get("metrics", {}).get("accuracy", 0) * 100 for r in reports]
    false_positives = [r.get("metrics", {}).get("false_positives", 0) for r in reports]
    false_negatives = [r.get("metrics", {}).get("false_negatives", 0) for r in reports]
    
    # Extract new metrics
    latencies = [r.get("metrics", {}).get("avg_latency_ms", 0) for r in reports]
    generalization_scores = [r.get("metrics", {}).get("generalization_score", 0) * 100 for r in reports]
    
    # Find best iteration from reports
    if accuracies:
        best_idx = accuracies.index(max(accuracies))
        best_report = reports[best_idx]
    else:
        best_report = {}
    
    # Use provided best_config or extract from best report
    final_best_config = best_config or best_report.get('configuration', {})
    
    # Calculate best accuracy - use max from reports (already in percentage)
    # If no reports, use provided best_accuracy (which is 0.0-1.0 decimal, needs *100)
    if accuracies and max(accuracies) > 0:
        final_best_accuracy = max(accuracies)  # Already in percentage (0-100)
    elif best_accuracy is not None and best_accuracy > 0:
        # best_accuracy from agent is 0.0-1.0, convert to percentage
        final_best_accuracy = best_accuracy * 100
    else:
        final_best_accuracy = 0
    
    # Best latency and generalization
    best_latency = min(latencies) if latencies and any(l > 0 for l in latencies) else 0
    best_generalization = max(generalization_scores) if generalization_scores else 0
    
    # Generate insights
    insights = generate_insights(reports)
    
    # Generate config appendix
    config_appendix = generate_config_appendix(final_best_config)
    
    # Generate iteration changes table
    changes_table = generate_iteration_changes_table(reports, iteration_changes)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guardrail Optimization Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://d1.awsstatic.com/fonts/amazon-ember.css">
    <style>
        body {{
            font-family: 'Amazon Ember', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            max-width: 1200px;
            margin: 0 auto;
            padding: 16px;
            background: #f5f5f5;
            line-height: 1.4;
        }}
        .header {{
            background: linear-gradient(135deg, #232f3e 0%, #37475a 100%);
            color: white;
            padding: 24px;
            border-radius: 8px;
            margin-bottom: 16px;
        }}
        .header h1 {{ margin: 0; font-size: 1.6em; font-weight: 500; }}
        .header p {{ margin: 8px 0 0 0; opacity: 0.9; font-size: 0.9em; }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #232f3e;
            border-bottom: 2px solid #ff9900;
            padding-bottom: 8px;
            font-size: 1.1em;
            font-weight: 500;
        }}
        .card h3 {{
            font-size: 0.95em;
            font-weight: 500;
            color: #37475a;
            margin: 12px 0 8px 0;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }}
        .metric-box {{
            background: #f8f9fa;
            padding: 14px;
            border-radius: 6px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 1.8em;
            font-weight: 500;
            color: #ff9900;
        }}
        .metric-label {{
            color: #545b64;
            margin-top: 4px;
            font-size: 0.85em;
        }}
        .chart-container {{
            position: relative;
            height: 260px;
            margin: 16px 0;
        }}
        .insight {{
            background: #e8f4fd;
            border-left: 3px solid #0073bb;
            padding: 10px 12px;
            margin: 8px 0;
            border-radius: 0 6px 6px 0;
            font-size: 0.9em;
        }}
        .insight.warning {{
            background: #fff3cd;
            border-left-color: #ff9900;
        }}
        .insight.success {{
            background: #d4edda;
            border-left-color: #1d8102;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 0.9em;
        }}
        th, td {{
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid #e1e4e8;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 500;
            color: #232f3e;
        }}
        .config-json {{
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 14px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
            line-height: 1.4;
            white-space: pre-wrap;
            max-height: 500px;
            overflow-y: auto;
        }}
        .topic-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .topic-list li {{
            padding: 8px 10px;
            margin: 4px 0;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .topic-name {{
            font-weight: 500;
            color: #0073bb;
        }}
        .footer {{
            text-align: center;
            color: #545b64;
            padding: 16px;
            font-size: 0.8em;
        }}
        .appendix {{
            page-break-before: always;
        }}
        small {{
            color: #545b64;
        }}
        @media print {{
            body {{ font-size: 11px; }}
            .card {{ break-inside: avoid; }}
            .appendix {{ page-break-before: always; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ Guardrail Optimization Report</h1>
        <p>AI Assistant - Amazon Bedrock Guardrails</p>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="card">
        <h2>📊 Summary Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-box">
                <div class="metric-value">{final_best_accuracy:.1f}%</div>
                <div class="metric-label">Best Accuracy</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{best_latency:.0f}ms</div>
                <div class="metric-label">Best Latency</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{best_generalization:.1f}%</div>
                <div class="metric-label">Best Generalization</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{len(reports)}</div>
                <div class="metric-label">Iterations</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{best_report.get('metrics', {}).get('total_tests', 'N/A')}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{best_report.get('metrics', {}).get('false_positives', 'N/A')}/{best_report.get('metrics', {}).get('false_negatives', 'N/A')}</div>
                <div class="metric-label">FP/FN (Best)</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>📈 Metrics Over Iterations</h2>
        <div class="chart-container">
            <canvas id="metricsChart"></canvas>
        </div>
    </div>

    <div class="card">
        <h2>📉 Error Analysis</h2>
        <div class="chart-container">
            <canvas id="errorChart"></canvas>
        </div>
    </div>

    <div class="card">
        <h2>💡 Key Insights</h2>
        {insights}
    </div>

    <div class="card">
        <h2>🏆 Best Configuration Summary</h2>
        {format_config_html(final_best_config)}
    </div>

    <div class="card">
        <h2>📋 Iteration Changes & Insights</h2>
        {changes_table}
    </div>

    <div class="card">
        <h2>❌ Remaining Failed Cases (Best Iteration)</h2>
        {format_failed_cases_html(best_report.get('failed_cases', []))}
    </div>

    <div class="card appendix">
        <h2>📎 Appendix: Best Guardrail Configuration (JSON)</h2>
        {config_appendix}
    </div>

    <div class="footer">
        <p>Generated by Guardrail Optimization Agent | Amazon Bedrock Guardrails</p>
    </div>

    <script>
        // Multi-Metrics Chart (Accuracy, Generalization on left axis; Latency on right)
        new Chart(document.getElementById('metricsChart'), {{
            type: 'line',
            data: {{
                labels: {iterations},
                datasets: [
                    {{
                        label: 'Accuracy (%)',
                        data: {accuracies},
                        borderColor: '#ff9900',
                        backgroundColor: 'rgba(255, 153, 0, 0.1)',
                        fill: false,
                        tension: 0.3,
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Generalization (%)',
                        data: {generalization_scores},
                        borderColor: '#1d8102',
                        backgroundColor: 'rgba(29, 129, 2, 0.1)',
                        fill: false,
                        tension: 0.3,
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Latency (ms)',
                        data: {latencies},
                        borderColor: '#0073bb',
                        backgroundColor: 'rgba(0, 115, 187, 0.1)',
                        fill: false,
                        tension: 0.3,
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        min: 0,
                        max: 100,
                        title: {{ display: true, text: 'Percentage (%)' }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        title: {{ display: true, text: 'Latency (ms)' }},
                        grid: {{ drawOnChartArea: false }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: true, position: 'top' }}
                }}
            }}
        }});

        // Error Chart
        new Chart(document.getElementById('errorChart'), {{
            type: 'bar',
            data: {{
                labels: {iterations},
                datasets: [
                    {{
                        label: 'False Positives',
                        data: {false_positives},
                        backgroundColor: '#ffc107'
                    }},
                    {{
                        label: 'False Negatives',
                        data: {false_negatives},
                        backgroundColor: '#dc3545'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    return output_path


def generate_iteration_changes_table(
    reports: list[dict[str, Any]],
    iteration_changes: list[dict[str, Any]] = None
) -> str:
    """Generate HTML table showing key changes and insights per iteration."""
    if not reports:
        return '<p>No iteration data available.</p>'
    
    # Build changes lookup from provided changes
    changes_lookup = {}
    if iteration_changes:
        for change in iteration_changes:
            changes_lookup[change.get("iteration", 0)] = change.get("changes", "")
    
    rows = []
    for i, r in enumerate(reports):
        iteration = r.get("iteration", i + 1)
        metrics = r.get("metrics", {})
        
        acc = metrics.get("accuracy", 0) * 100
        latency = metrics.get("avg_latency_ms", 0)
        gen = metrics.get("generalization_score", 0) * 100
        fp = metrics.get("false_positives", 0)
        fn = metrics.get("false_negatives", 0)
        
        # Get changes for this iteration
        changes = changes_lookup.get(iteration, "")
        if not changes and i == 0:
            changes = "Initial configuration"
        
        # Generate insight based on metrics change
        insight = ""
        if i > 0:
            prev_metrics = reports[i-1].get("metrics", {})
            prev_acc = prev_metrics.get("accuracy", 0) * 100
            acc_diff = acc - prev_acc
            if acc_diff > 0:
                insight = f"↑ +{acc_diff:.1f}% accuracy"
            elif acc_diff < 0:
                insight = f"↓ {acc_diff:.1f}% accuracy"
            else:
                insight = "→ No change"
        
        rows.append(f'''<tr>
            <td>{iteration}</td>
            <td>{acc:.1f}%</td>
            <td>{latency:.0f}ms</td>
            <td>{gen:.1f}%</td>
            <td>{fp}/{fn}</td>
            <td>{changes[:80]}{"..." if len(changes) > 80 else ""}</td>
            <td>{insight}</td>
        </tr>''')
    
    return f'''<table>
        <thead>
            <tr>
                <th>Iter</th>
                <th>Accuracy</th>
                <th>Latency</th>
                <th>Generalization</th>
                <th>FP/FN</th>
                <th>Changes Made</th>
                <th>Impact</th>
            </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
    </table>'''


def generate_insights(reports: list[dict[str, Any]]) -> str:
    """Generate HTML insights from reports."""
    insights = []
    
    if not reports:
        return '<div class="insight">No reports available for analysis.</div>'
    
    if len(reports) < 2:
        return '<div class="insight">Not enough iterations for trend analysis.</div>'
    
    # Accuracy trend
    first_acc = reports[0].get("metrics", {}).get("accuracy", 0) * 100
    last_acc = reports[-1].get("metrics", {}).get("accuracy", 0) * 100
    best_acc = max(r.get("metrics", {}).get("accuracy", 0) * 100 for r in reports)
    
    if last_acc > first_acc:
        improvement = last_acc - first_acc
        insights.append(f'<div class="insight success">✅ Accuracy improved by {improvement:.1f}% from {first_acc:.1f}% to {last_acc:.1f}%</div>')
    elif last_acc < first_acc:
        decline = first_acc - last_acc
        insights.append(f'<div class="insight warning">⚠️ Accuracy declined by {decline:.1f}% - consider reverting to iteration with {best_acc:.1f}% accuracy</div>')
    else:
        insights.append(f'<div class="insight">📊 Accuracy remained stable at {last_acc:.1f}%</div>')
    
    # False positive/negative analysis
    best_report = max(reports, key=lambda r: r.get("metrics", {}).get("accuracy", 0))
    fp = best_report.get("metrics", {}).get("false_positives", 0)
    fn = best_report.get("metrics", {}).get("false_negatives", 0)
    
    if fp > fn:
        insights.append(f'<div class="insight warning">⚠️ More false positives ({fp}) than false negatives ({fn}) - topic definitions may be too broad</div>')
    elif fn > fp:
        insights.append(f'<div class="insight warning">⚠️ More false negatives ({fn}) than false positives ({fp}) - consider adding more denied topics or word filters</div>')
    
    if fp == 0:
        insights.append('<div class="insight success">✅ No false positives - legitimate queries are passing correctly</div>')
    if fn == 0:
        insights.append('<div class="insight success">✅ No false negatives - off-topic queries are being blocked correctly</div>')
    
    # Convergence check
    if len(reports) >= 3:
        last_three = [r.get("metrics", {}).get("accuracy", 0) for r in reports[-3:]]
        if max(last_three) - min(last_three) < 0.01:
            insights.append('<div class="insight">📊 Accuracy has stabilized - optimization may have converged</div>')
    
    return '\n'.join(insights) if insights else '<div class="insight">No specific insights available.</div>'


def generate_config_appendix(config: dict[str, Any]) -> str:
    """Generate JSON appendix for the configuration."""
    if not config:
        return '<p>Configuration not available.</p>'
    
    # Pretty print JSON with syntax highlighting simulation
    json_str = json.dumps(config, indent=2)
    # Escape HTML characters
    json_str = json_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    return f'<div class="config-json">{json_str}</div>'


def format_config_html(config: dict[str, Any]) -> str:
    """Format configuration summary as HTML."""
    if not config:
        return '<p>Configuration not available.</p>'
    
    html_parts = []
    
    # Topic policies
    topics = config.get("topicPolicyConfig", {}).get("topicsConfig", [])
    if topics:
        html_parts.append(f'<h3>Denied Topics ({len(topics)})</h3><ul class="topic-list">')
        for topic in topics:
            definition = topic.get("definition", "No definition")
            if len(definition) > 150:
                definition = definition[:150] + "..."
            html_parts.append(f'''<li>
                <span class="topic-name">{topic.get("name", "Unknown")}</span><br>
                <small>{definition}</small>
            </li>''')
        html_parts.append('</ul>')
    
    # Content filters
    filters = config.get("contentPolicyConfig", {}).get("filtersConfig", [])
    if filters:
        html_parts.append('<h3>Content Filters</h3><table><tr><th>Type</th><th>Input Strength</th><th>Output Strength</th></tr>')
        for f in filters:
            html_parts.append(f'<tr><td>{f.get("type", "Unknown")}</td><td>{f.get("inputStrength", "N/A")}</td><td>{f.get("outputStrength", "N/A")}</td></tr>')
        html_parts.append('</table>')
    
    # Word filters
    words = config.get("wordPolicyConfig", {}).get("wordsConfig", [])
    if words:
        word_list = [w.get("text", "") for w in words[:20]]
        html_parts.append(f'<h3>Word Filters ({len(words)})</h3><p>{", ".join(word_list)}{"..." if len(words) > 20 else ""}</p>')
    
    return '\n'.join(html_parts) if html_parts else '<p>No configuration details available.</p>'


def format_failed_cases_html(failed_cases: list[dict[str, Any]]) -> str:
    """Format failed cases as HTML table."""
    if not failed_cases:
        return '<p class="insight success">✅ No failed cases!</p>'
    
    # Group by type
    fp_cases = [c for c in failed_cases if c.get("expected") == "pass"]
    fn_cases = [c for c in failed_cases if c.get("expected") == "reject"]
    
    html = ""
    
    if fp_cases:
        html += f'<h3>False Positives ({len(fp_cases)} - should pass but rejected)</h3>'
        html += '<table><tr><th>Input</th><th>Blocked By</th></tr>'
        for c in fp_cases[:10]:
            blocked_by = ", ".join(c.get("violated_policies", []) + c.get("violated_filters", []))
            input_text = c.get("input", "")[:80]
            html += f'<tr><td>{input_text}...</td><td>{blocked_by}</td></tr>'
        if len(fp_cases) > 10:
            html += f'<tr><td colspan="2"><em>... and {len(fp_cases) - 10} more</em></td></tr>'
        html += '</table>'
    
    if fn_cases:
        html += f'<h3>False Negatives ({len(fn_cases)} - should reject but passed)</h3>'
        html += '<table><tr><th>Input</th></tr>'
        for c in fn_cases[:10]:
            input_text = c.get("input", "")[:100]
            html += f'<tr><td>{input_text}...</td></tr>'
        if len(fn_cases) > 10:
            html += f'<tr><td><em>... and {len(fn_cases) - 10} more</em></td></tr>'
        html += '</table>'
    
    return html


def generate_pdf_report(html_path: str, pdf_path: str = "optimization_report.pdf") -> Optional[str]:
    """
    Generate PDF from HTML report.
    
    Tries multiple methods:
    1. pdfkit (wkhtmltopdf) - renders JavaScript charts
    2. playwright - headless browser rendering
    3. Falls back to manual browser print instructions
    
    Args:
        html_path: Path to HTML report
        pdf_path: Output PDF path
    
    Returns:
        Path to generated PDF or None if no method available
    """
    # Method 1: Try pdfkit (wkhtmltopdf) - renders JS
    try:
        import pdfkit
        options = {
            'enable-javascript': None,
            'javascript-delay': '2000',  # Wait for charts to render
            'no-stop-slow-scripts': None,
            'enable-local-file-access': None
        }
        pdfkit.from_file(html_path, pdf_path, options=options)
        return pdf_path
    except (ImportError, OSError):
        pass
    
    # Method 2: Try playwright (headless Chrome)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{os.path.abspath(html_path)}")
            page.wait_for_timeout(2000)  # Wait for charts
            page.pdf(path=pdf_path, format="A4", print_background=True)
            browser.close()
        return pdf_path
    except (ImportError, Exception):
        pass
    
    # No automated method available
    print(f"\nTo generate PDF with charts, either:")
    print(f"  Option 1: Install pdfkit + wkhtmltopdf:")
    print(f"    pip install pdfkit")
    print(f"    brew install wkhtmltopdf  # macOS")
    print(f"  Option 2: Install playwright:")
    print(f"    pip install playwright")
    print(f"    playwright install chromium")
    print(f"  Option 3: Open {html_path} in browser and print to PDF")
    return None


def generate_final_report(
    report_dir: str = ".",
    best_config: dict[str, Any] = None,
    best_accuracy: float = None,
    iteration_changes: list[dict[str, Any]] = None,
    session_id: str = None
) -> tuple[Optional[str], Optional[str]]:
    """
    Generate final HTML and PDF reports for a specific session.
    
    Args:
        report_dir: Directory containing iteration reports
        best_config: Best guardrail configuration
        best_accuracy: Best accuracy achieved
        iteration_changes: List of changes made per iteration
        session_id: Session ID to filter reports (only include current session)
    
    Returns:
        Tuple of (html_path, pdf_path)
    """
    reports = load_iteration_reports(report_dir, session_id=session_id)
    
    if not reports:
        print("No iteration reports found.")
        return None, None
    
    print(f"Found {len(reports)} iteration reports")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_filename = f"optimization_report_{timestamp}.html"
    pdf_filename = f"optimization_report_{timestamp}.pdf"
    
    html_path = generate_html_report(
        reports, 
        os.path.join(report_dir, html_filename),
        best_config=best_config,
        best_accuracy=best_accuracy,
        iteration_changes=iteration_changes
    )
    print(f"Generated HTML report: {html_path}")
    
    pdf_path = generate_pdf_report(html_path, os.path.join(report_dir, pdf_filename))
    if pdf_path:
        print(f"Generated PDF report: {pdf_path}")
    
    return html_path, pdf_path


if __name__ == "__main__":
    import sys
    report_dir = sys.argv[1] if len(sys.argv) > 1 else "evaluation_reports"
    generate_final_report(report_dir)
