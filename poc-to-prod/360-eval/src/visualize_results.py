import logging, glob, re, ast, os
from pathlib import Path
from plotly.subplots import make_subplots
from jinja2 import Template
from collections import Counter
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pytz


# Configuration
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Setup logger
logger = logging.getLogger(__name__)

with open("./assets/html_template.txt", 'r') as file:
    HTML_TEMPLATE = file.read()


def extract_model_name(model_id):
    """Extract clean model name from ID."""
    if '.' in model_id:
        parts = model_id.split('.')
        if len(parts) >= 2:
            model_name = parts[-1].split(':')[0].split('-v')[0]
            return model_name
    return model_id.split(':')[0]

def parse_json_string(json_str):
    try:
        if isinstance(json_str, list):
            json_str = json_str[0]
        # Use ast.literal_eval to safely evaluate the string as a Python literal
        # This handles the single-quoted JSON-like strings
        dict_data = ast.literal_eval(json_str)
        return dict_data
    except Exception as e:
        # Return error information if parsing fails
        return {"error": str(e)}


def load_data(directory):
    """Load and prepare benchmark data."""
    # Load CSV files
    files = glob.glob(str(directory / "invocations_*.csv"))
    if not files:
        raise FileNotFoundError(f"No invocation CSVs found in {directory}")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    # Clean and prepare data
    df = df[df['api_call_status'] == 'Success'].reset_index(drop=True)
    df['model_name'] = df['model_id'].apply(extract_model_name)
    parsed_dicts = df['performance_metrics'].apply(parse_json_string)
    del df['performance_metrics']
    # Convert the Series of dictionaries to a DataFrame
    unpacked_findings = pd.DataFrame(list(parsed_dicts))
    df = pd.concat([df, unpacked_findings], axis=1)
    df['task_success'] = df['judge_success']
    # Calculate tokens per second
    df['OTPS'] = df['output_tokens'] / (df['time_to_last_byte'] + 0.001)

    return df


def calculate_metrics_by_model_task(df):
    """Calculate detailed metrics for each model-task combination."""
    # Group by model and task
    metrics = df.groupby(['model_name', 'task_types']).agg({
        'task_success': ['mean', 'count'],
        'time_to_first_byte': ['mean', 'min', 'max'],
        'time_to_last_byte': ['mean', 'min', 'max'],
        'OTPS': ['mean', 'min', 'max'],
        'response_cost': ['mean', 'sum'],
        'output_tokens': ['mean', 'sum'],
        'input_tokens': ['mean', 'sum']
    })

    # Flatten multi-level column index
    metrics.columns = ['_'.join(col).strip() for col in metrics.columns.values]

    # Rename columns for clarity
    metrics = metrics.rename(columns={
        'task_success_mean': 'success_rate',
        'task_success_count': 'sample_count',
        'time_to_first_byte_mean': 'avg_ttft',
        'time_to_last_byte_mean': 'avg_latency',
        'OTPS_mean': 'avg_otps',
        'response_cost_mean': 'avg_cost',
        'output_tokens_mean': 'avg_output_tokens',
        'input_tokens_mean': 'avg_input_tokens'
    })

    max_raw_ratio = metrics['success_rate'].max() / (metrics['avg_cost'].min() + 0.001)
    metrics['value_ratio'] = 10 * (metrics['success_rate'] / (metrics['avg_cost'] + 0.001)) / max_raw_ratio

    return metrics.reset_index()


def calculate_latency_metrics(df):
    """Calculate aggregated latency metrics by model."""
    latency = df.groupby(['model_name']).agg({
        'time_to_first_byte': ['mean', 'min', 'max', 'std'],
        'time_to_last_byte': ['mean', 'min', 'max', 'std'],
        'OTPS': ['mean', 'min', 'max', 'std']
    })

    # Flatten multi-level column index
    latency.columns = ['_'.join(col).strip() for col in latency.columns.values]

    # Rename columns for clarity
    latency = latency.rename(columns={
        'time_to_first_byte_mean': 'avg_ttft',
        'time_to_last_byte_mean': 'avg_latency',
        'OTPS_mean': 'avg_otps'
    })

    return latency.reset_index()


def calculate_cost_metrics(df):
    """Calculate aggregated cost metrics by model."""
    cost = df.groupby(['model_name']).agg({
        'response_cost': ['mean', 'min', 'max', 'sum'],
        'input_tokens': ['mean', 'sum'],
        'output_tokens': ['mean', 'sum']
    })

    # Flatten multi-level column index
    cost.columns = ['_'.join(col).strip() for col in cost.columns.values]

    # Rename columns for clarity
    cost = cost.rename(columns={
        'response_cost_mean': 'avg_cost',
        'response_cost_sum': 'total_cost',
        'input_tokens_mean': 'avg_input_tokens',
        'output_tokens_mean': 'avg_output_tokens'
    })

    return cost.reset_index()


def create_visualizations(df, model_task_metrics, latency_metrics, cost_metrics):
    """Create visualizations for the report."""
    visualizations = {}

    latency_metrics_round = latency_metrics
    average_cost_round = latency_metrics_round.round({'avg_ttft': 4})
    # 1. TTFT Comparison
    ttft_fig = px.bar(
        average_cost_round.sort_values('avg_ttft'),
        template="plotly_dark",  # Use the built-in dark template as a base
        x='model_name',
        y='avg_ttft',
        # error_y=latency_metrics['time_to_first_byte_std'],
        labels={'model_name': 'Model', 'avg_ttft': 'Time to First Token (Secs)'},
        title='Time to First Token by Model',
        color='avg_ttft',
        color_continuous_scale='Viridis_r'  # Reversed so lower is better (green)
    )

    # Improve overall chart visibility
    ttft_fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
    )

    visualizations['ttft_comparison'] = ttft_fig

    tokens_per_sec_round = latency_metrics
    tokens_per_sec_round = tokens_per_sec_round.round({'avg_otps': 2})

    # 2. OTPS Comparison
    otps_fig = px.bar(
        tokens_per_sec_round.sort_values('avg_otps', ascending=False),
        template="plotly_dark",  # Use the built-in dark template as a base
        x='model_name',
        y='avg_otps',
        error_y=tokens_per_sec_round['OTPS_std'],
        labels={'model_name': 'Model', 'avg_otps': 'Tokens/sec'},
        title='Output Tokens Per Second by Model',
        color='avg_otps',
        color_continuous_scale='Viridis'
    )

    # Improve overall chart visibility
    otps_fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
    )

    visualizations['otps_comparison'] = otps_fig
    average_cost_round = cost_metrics
    average_cost_round = average_cost_round.sort_values('avg_cost')
    average_cost_round = average_cost_round.round({'avg_cost': 5})
    # 3. Cost Comparison
    cost_fig = px.bar(
        average_cost_round.sort_values('avg_cost'),
        template="plotly_dark",  # Use the built-in dark template as a base
        x='model_name',
        y='avg_cost',
        labels={'model_name': 'Model', 'avg_cost': 'Cost per Response (USD)'},
        # title='Average Cost per Response by Model',
        color='avg_cost',
        color_continuous_scale='Viridis_r'  # Reversed so lower is better (green)
    )

    # Improve overall chart visibility
    cost_fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
    )

    visualizations['cost_comparison'] = cost_fig

    # 5. Task-Model Success Rate Heatmap
    # Pivot to create model vs task matrix
    pivot_success = pd.pivot_table(
        model_task_metrics,
        values='success_rate',
        index='model_name',
        columns='task_types',
        aggfunc='mean'
    ).fillna(0)

    heatmap_fig = px.imshow(
        pivot_success,
        template="plotly_dark",  # Use the built-in dark template as a base
        labels={'x': 'Task Type', 'y': 'Model', 'color': 'Success Rate'},
        title='Success Rate by Model and Task Type',
        color_continuous_scale='Earth', #'Viridis',
        text_auto='.2f',
        aspect='auto'
    )
    # Improve overall chart visibility
    heatmap_fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
    )

    visualizations['model_task_heatmap'] = heatmap_fig

    model_task_metrics_round = model_task_metrics
    average_cost_round = model_task_metrics_round.round({'avg_otps': 2, 'value_ratio': 2})
    # 6. Model-Task Bubble Chart
    bubble_fig = px.scatter(
        average_cost_round,
        template="plotly_dark",  # Keep the dark template for the base layout
        x='avg_latency',
        y='success_rate',
        size='avg_otps',
        color='avg_cost',
        facet_col='task_types',
        facet_col_wrap=3,
        hover_data=['model_name', 'value_ratio'],
        labels={
            'avg_latency': 'Latency (Secs)',
            'success_rate': 'Success Rate',
            'avg_cost': 'Cost (USD)',
            'avg_otps': 'Tokens/sec'
        },
        title='Model Performance by Task Type',
        color_continuous_scale='Earth',  # Use a brighter color scale
        opacity=0.85  # Slightly increase transparency for better contrast
    )

    # Additional customizations to improve visibility
    bubble_fig.update_traces(
        marker=dict(
            line=dict(width=1, color="rgba(255, 255, 255, 0.3)")  # Add subtle white outline
        )
    )

    # You can also brighten the color bar
    bubble_fig.update_layout(
        coloraxis_colorbar=dict(
            title_font_color="#ffffff",
            tickfont_color="#ffffff",
        )
    )

    # Make facet titles more visible
    bubble_fig.for_each_annotation(lambda a: a.update(font=dict(color="#90caf9", size=12)))

    # Improve overall chart visibility
    bubble_fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
        font=dict(color="#e0e0e0"),
        title_font=dict(color="#90caf9", size=18)
    )
    visualizations['model_task_bubble'] = bubble_fig

    # 7. Error Analysis
    if 'judge_explanation' in df.columns:
        fails = df[df['task_success'] == False].copy()
        if not fails.empty:
            fails['error'] = fails['judge_explanation'].fillna("Unknown").replace("", "Unknown")
            # Extract error categories using regex
            fails['error_category'] = fails['error'].apply(
                lambda x: ' - '.join(list(set(re.findall(r'[A-Za-z]+', str(x))))) if pd.notnull(x) else "Unknown"
            )

            counts = fails.groupby(['model_name', 'task_types', 'error_category']).size().reset_index(name='count')
            # counts['error_category'] = counts['error_category']

            error_fig = px.treemap(
                counts,
                template="plotly_dark",  # Use the built-in dark template as a base
                path=['task_types', 'model_name', 'error_category'],
                values='count',
                title='Error Analysis by Task, Model, and Error Type',
                color='count',
                color_continuous_scale='Reds'
            )
            error_fig.update_traces(
                hovertemplate='<br>Error Judgment: %{label}<br>Count: %{value:.0f}<br>Model: %{parent}<extra></extra>'
            )
            # Improve overall chart visibility
            error_fig.update_layout(
                paper_bgcolor="#1e1e1e",
                plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
                )

            visualizations['error_analysis'] = error_fig
        else:
            visualizations['error_analysis'] = go.Figure()
    else:
        visualizations['error_analysis'] = go.Figure()

    # Add this inside create_visualizations() function
    # Extract judge scores from the DataFrame

    df['parsed_scores'] = df['judge_scores'].apply(extract_judge_scores)

    # Create one radar chart per model (combining all tasks)
    radar_charts = {}

    # Get all unique models and categories
    unique_models = df['model_name'].unique()
    all_categories = set()

    # First, collect all categories across all data
    for _, row in df.iterrows():
        if pd.notnull(row.get('parsed_scores')):
            score_dict = row['parsed_scores']
            for key in score_dict:
                if key.startswith('AVG_'):
                    category = key.replace('AVG_', '')
                    all_categories.add(category)

    all_categories = sorted(list(all_categories))

    # Create one chart per model with all tasks
    for model in unique_models:
        # Filter data for this model
        model_data = df[df['model_name'] == model]

        if model_data.empty:
            continue

        # Get all tasks for this model
        tasks = model_data['task_types'].unique()

        # Create figure for this model
        fig = go.Figure()

        # Add one trace per task
        for task in tasks:
            task_data = model_data[model_data['task_types'] == task]

            # Extract scores for this task
            scores_dicts = task_data['parsed_scores'].dropna().tolist()

            if not scores_dicts:
                continue

            # Calculate average scores for each category
            avg_scores = {}

            for score_dict in scores_dicts:
                for key, value in score_dict.items():
                    if key.startswith('AVG_'):
                        category = key.replace('AVG_', '')
                        if category not in avg_scores:
                            avg_scores[category] = []
                        avg_scores[category].append(value)

            # Fill in values for each category
            values = []
            for category in all_categories:
                scores = avg_scores.get(category, [])
                if scores:
                    values.append(sum(scores) / len(scores))
                else:
                    values.append(0)

            # Add trace for this task
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],  # Close the polygon
                theta=all_categories + [all_categories[0]],  # Close the polygon
                fill='toself',
                name=task,
                opacity=0.7
            ))

        # Update layout
        fig.update_layout(
            template="plotly_dark",  # Use the built-in dark template as a base
            paper_bgcolor="#1e1e1e",
            plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5]  # Assuming scores are on a 0-5 scale
                )
            ),
            title=f"Eval Scores Across All Tasks",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            ),
            height=500,
            width=850,
            margin=dict(l=20, r=20, b=80, t=50)  # Added bottom margin for legend
        )

        # Store the chart
        radar_charts[model] = fig
    visualizations['judge_score_radars'] = radar_charts

    # 8. Task-specific charts
    task_charts = {}
    for task in df['task_types'].unique():
        task_data = model_task_metrics[model_task_metrics['task_types'] == task]

        if not task_data.empty:
            # Create subplot with 2x2 grid
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=("Success Rate", "Latency (Secs)", "Cost per Response (USD)", "Tokens per Second")
            )

            # Sort data for each subplot
            by_success = task_data.sort_values('success_rate', ascending=False)
            by_latency = task_data.sort_values('avg_latency')
            by_cost = task_data.sort_values('avg_cost')
            by_otps = task_data.sort_values('avg_otps', ascending=False)

            # Add traces for each subplot
            fig.add_trace(
                go.Bar(x=by_success['model_name'], y=by_success['success_rate'], marker_color='green'),
                row=1, col=1
            )

            fig.add_trace(
                go.Bar(x=by_latency['model_name'], y=by_latency['avg_latency'], marker_color='orange'),
                row=1, col=2
            )

            fig.add_trace(
                go.Bar(x=by_cost['model_name'], y=by_cost['avg_cost'], marker_color='red'),
                row=2, col=1
            )

            fig.add_trace(
                go.Bar(x=by_otps['model_name'], y=by_otps['avg_otps'], marker_color='blue'),
                row=2, col=2
            )

            fig.update_layout(
                height=725,
                title_text=f"Performance Metrics for {task}",
                showlegend=False,
                template="plotly_dark",
                paper_bgcolor="#1e1e1e",
                plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast
                              )

            task_charts[task] = fig

    visualizations['task_charts'] = task_charts
    visualizations['integrated_analysis_table'] = create_integrated_analysis_table(model_task_metrics)
    visualizations['regional_performance'] = create_regional_performance_analysis(df)

    return visualizations


def generate_task_findings(df, model_task_metrics):
    """Generate key findings for each task type."""
    task_findings = {}

    for task in df['task_types'].unique():
        task_data = model_task_metrics[model_task_metrics['task_types'] == task]
        findings = []

        if not task_data.empty:
            # Best accuracy model
            best_acc_idx = task_data['success_rate'].idxmax()
            best_acc = task_data.loc[best_acc_idx]
            findings.append(f"{best_acc['model_name']} had the highest success rate ({best_acc['success_rate']:.1%})")

            # Best speed model
            best_speed_idx = task_data['avg_latency'].idxmin()
            best_speed = task_data.loc[best_speed_idx]
            findings.append(
                f"{best_speed['model_name']} was the fastest with {best_speed['avg_latency']:.2f}s average latency")

            # Best throughput model
            best_otps_idx = task_data['avg_otps'].idxmax()
            best_otps = task_data.loc[best_otps_idx]
            findings.append(
                f"{best_otps['model_name']} had the highest throughput ({best_otps['avg_otps']:.1f} tokens/sec)")

            # Best value model
            best_value_idx = task_data['value_ratio'].idxmax()
            best_value = task_data.loc[best_value_idx]
            findings.append(
                f"{best_value['model_name']} offered the best value (success/cost ratio: {best_value['value_ratio']:.2f})")

            # Average success rate
            avg_success = task_data['success_rate'].mean()
            findings.append(f"Average success rate for this task was {avg_success:.1%}")

            # Error analysis
            fails = df[(df['task_types'] == task) & (df['task_success'] == False)]
            if not fails.empty and 'judge_explanation' in fails.columns:
                # Extract common error patterns
                error_patterns = []
                unique_explanations = fails['judge_explanation'].dropna()
                all_errors = unique_explanations.apply(lambda x: [i for i in x.split(';') if i != '']).tolist()
                [error_patterns.extend(exp) for exp in all_errors]
                if error_patterns:
                    common_errors = Counter(error_patterns).most_common(2)
                    errors_text = ", ".join([f"{err[0]} ({err[1]} occurrences)" for err in common_errors])
                    findings.append(f"Most common errors: {errors_text}")

        task_findings[task] = findings

    return task_findings


def generate_task_recommendations(model_task_metrics):
    """Generate task-specific model recommendations."""
    recommendations = []

    for task in model_task_metrics['task_types'].unique():
        task_data = model_task_metrics[model_task_metrics['task_types'] == task]

        if not task_data.empty:
            # Find best models by different metrics
            best_suc = task_data['success_rate'].max()
            best_acc_model = '<br>'.join(task_data[task_data['success_rate'] == best_suc]['model_name'].tolist())

            best_lat = task_data['avg_latency'].min()
            best_speed_model = '<br>'.join(task_data[task_data['avg_latency'] == best_lat]['model_name'].tolist())

            best_value = task_data['value_ratio'].max()
            best_value_model = '<br>'.join(task_data[task_data['value_ratio'] == best_value]['model_name'].tolist())

            # Create recommendation entry
            recommendations.append({
                'task': task,
                'best_accuracy_model': best_acc_model,
                'accuracy': f"{best_suc:.1%}",
                'best_speed_model': best_speed_model,
                'speed': f"{best_lat:.2f}s",
                'best_value_model': best_value_model,
                'value': f"{best_value:.2f}"
            })

    return sorted(recommendations, key=lambda x: x['task'])



def create_html_report(output_dir, timestamp):
    """Generate HTML benchmark report with task-specific analysis."""
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging for report generation
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    report_log_file = f"{log_dir}/report_generation-{timestamp}.log"
    logger.info(f"Report generation logs will be saved to: {report_log_file}")

    # Load and process data
    logger.info("Loading and processing data...")

    df = load_data(output_dir)

    # Calculate metrics
    logger.info("Calculating model-task metrics...")
    model_task_metrics = calculate_metrics_by_model_task(df)

    logger.info("Calculating latency metrics...")
    latency_metrics = calculate_latency_metrics(df)

    logger.info("Calculating cost metrics...")
    cost_metrics = calculate_cost_metrics(df)

    # Create visualizations
    logger.info("Creating visualizations...")
    visualizations = create_visualizations(df, model_task_metrics, latency_metrics, cost_metrics)

    # Generate findings and recommendations
    logger.info("Generating task findings...")
    task_findings = generate_task_findings(df, model_task_metrics)

    logger.info("Generating recommendations...")
    task_recommendations = generate_task_recommendations(model_task_metrics)

    # Prepare task analysis data for template
    task_analysis = []
    for task, chart in visualizations['task_charts'].items():
        task_analysis.append({
            'name': task,
            'chart': chart.to_html(full_html=False),
            'findings': task_findings.get(task, ["No specific findings available."])
        })

    # Render HTML template
    logger.info("Rendering HTML report...")

    # Parse the string into a datetime object
    datetime_object = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")

    # Format the datetime object into the desired string representation
    formatted_date = datetime_object.strftime("%B %d, %Y at %I:%M %p")
    # Add this to extract unique models
    unique_models = df['model_name'].unique().tolist()
    html = Template(HTML_TEMPLATE).render(
        timestamp=formatted_date,

        # Latency charts
        ttft_comparison_div=visualizations['ttft_comparison'].to_html(full_html=False),
        otps_comparison_div=visualizations['otps_comparison'].to_html(full_html=False),

        # Cost charts
        cost_comparison_div=visualizations['cost_comparison'].to_html(full_html=False),

        # Task analysis
        task_analysis=task_analysis,

        # Model-Task performance
        model_task_heatmap_div=visualizations['model_task_heatmap'].to_html(full_html=False),
        model_task_bubble_div=visualizations['model_task_bubble'].to_html(full_html=False),

        unique_models = unique_models,
        judge_score_radars = {key: chart.to_html(full_html=False) for key, chart in
                              visualizations.get('judge_score_radars', {}).items()},

        # Error and regional Analysis
        error_analysis_div=visualizations['error_analysis'].to_html(full_html=False),
        integrated_analysis_table_div=visualizations['integrated_analysis_table'].to_html(full_html=False),
        regional_performance_div=visualizations['regional_performance'].to_html(full_html=False),
        # Recommendations
        task_recommendations=task_recommendations,
    )

    # Write report to file
    out_file = output_dir / f"llm_benchmark_report_{timestamp}.html"
    out_file.write_text(html, encoding="utf-8")
    logger.info(f"HTML report written to: {out_file}")

    return out_file

#############################
#############################

def extract_judge_scores(json_str):
    try:
        if isinstance(json_str, dict):
            return json_str
        if isinstance(json_str, list):
            json_str = json_str[0]
        # Use ast.literal_eval to safely evaluate the string as a Python literal
        dict_data = ast.literal_eval(json_str)
        return dict_data
    except Exception as e:
        return {}



##############################
##############################
def create_integrated_analysis_table(model_task_metrics):
    """
    Creates an interactive table that integrates performance, speed, and cost metrics
    for each model and task type with optimal range highlighting.
    """
    # Define optimal ranges for each metric
    optimal_ranges = {
        'success_rate': 0.95,  # Success rate >= 95% is considered good
        'avg_latency': 1,  # Latency <= 1s is considered good
        'avg_cost': 0.5,  # Cost <= $0.5 is considered good
    }

    # Prepare the data for the table
    table_data = model_task_metrics.copy()

    # Format metrics for display
    table_data['success_rate_fmt'] = table_data['success_rate'].apply(lambda x: f"{x:.1%}")
    table_data['avg_latency_fmt'] = table_data['avg_latency'].apply(lambda x: f"{x:.2f}s")
    table_data['avg_cost_fmt'] = table_data['avg_cost'].apply(lambda x: f"${x:.4f}")
    table_data['avg_otps_fmt'] = table_data['avg_otps'].apply(lambda x: f"{x:.1f}")

    # Calculate composite score (higher is better)
    # Normalize metrics to 0-1 range and combine them
    max_latency = table_data['avg_latency'].max() or 1
    max_cost = table_data['avg_cost'].max() or 1

    table_data['composite_score'] = (
            table_data['success_rate'] +
            (1 - (table_data['avg_latency'] / max_latency)) * 0.5 +
            (1 - (table_data['avg_cost'] / max_cost)) * 0.5
    )

    # Create figure
    fig = go.Figure()

    # Create table cells with conditional formatting
    fig.add_trace(go.Table(
        header=dict(
            values=['Model', 'Task Type', 'Success Rate', 'Latency', 'Cost', 'Tokens/sec', 'Score'],
            font=dict(size=12, color='white'),
            fill_color='#2E5A88',
            align='left'
        ),
        cells=dict(
            values=[
                table_data['model_name'],
                table_data['task_types'],
                table_data['success_rate_fmt'],
                table_data['avg_latency_fmt'],
                table_data['avg_cost_fmt'],
                table_data['avg_otps_fmt'],
                table_data['composite_score'].apply(lambda x: f"{x:.2f}")
            ],
            align='left',
            font=dict(size=11),
            # Conditional formatting based on optimal ranges
            fill_color=[
                ['white'] * len(table_data),  # Model column (no coloring)
                ['white'] * len(table_data),  # Task column (no coloring)
                # Success rate coloring
                ['#c6efce' if sr >= optimal_ranges['success_rate'] else '#ffcccc' for sr in table_data['success_rate']],
                # Latency coloring (lower is better)
                ['#c6efce' if lt <= optimal_ranges['avg_latency'] else '#ffcccc' for lt in table_data['avg_latency']],
                # Cost coloring (lower is better)
                ['#c6efce' if cost <= optimal_ranges['avg_cost'] else '#ffcccc' for cost in table_data['avg_cost']],
                # OTPS coloring (just use white)
                ['white'] * len(table_data),
                # Composite score coloring based on quartiles
                ['#c6efce' if score >= table_data['composite_score'].quantile(0.75) else
                 '#fde9d9' if score >= table_data['composite_score'].quantile(0.5) else
                 '#ffcccc' for score in table_data['composite_score']]
            ]
        )
    ))

    # Update layout with title and size
    fig.update_layout(
        title='Integrated Analysis: Performance vs Speed vs Cost',
        title_font=dict(size=16),
        width=900,
        height=len(table_data) * 25 + 100,  # Dynamic height based on number of rows
        margin=dict(l=20, r=20, b=20, t=40),
        template="ggplot2",  # Use the built-in dark template as a base
    )

    return fig


def create_regional_performance_analysis(df):
    """
    Creates a plot showing latency and cost metrics grouped by region,
    including time of day analysis and region-specific recommendations.
    """

    # Map regions to their time zones
    region_timezones = {
        # North America
        'us-east-1': pytz.timezone('America/New_York'),  # N. Virginia
        'us-east-2': pytz.timezone('America/Chicago'),  # Ohio
        'us-west-1': pytz.timezone('America/Los_Angeles'),  # N. California
        'us-west-2': pytz.timezone('America/Los_Angeles'),  # Oregon

        # Africa
        'af-south-1': pytz.timezone('Africa/Johannesburg'),  # Cape Town

        # Asia Pacific
        'ap-east-1': pytz.timezone('Asia/Hong_Kong'),  # Hong Kong
        'ap-south-2': pytz.timezone('Asia/Kolkata'),  # Hyderabad
        'ap-southeast-3': pytz.timezone('Asia/Jakarta'),  # Jakarta
        'ap-southeast-5': pytz.timezone('Asia/Kuala_Lumpur'),  # Malaysia
        'ap-southeast-4': pytz.timezone('Australia/Melbourne'),  # Melbourne
        'ap-south-1': pytz.timezone('Asia/Kolkata'),  # Mumbai
        'ap-northeast-3': pytz.timezone('Asia/Tokyo'),  # Osaka
        'ap-northeast-2': pytz.timezone('Asia/Seoul'),  # Seoul
        'ap-southeast-1': pytz.timezone('Asia/Singapore'),  # Singapore
        'ap-southeast-2': pytz.timezone('Australia/Sydney'),  # Sydney
        'ap-southeast-7': pytz.timezone('Asia/Bangkok'),  # Thailand
        'ap-northeast-1': pytz.timezone('Asia/Tokyo'),  # Tokyo

        # Canada
        'ca-central-1': pytz.timezone('America/Toronto'),  # Central
        'ca-west-1': pytz.timezone('America/Edmonton'),  # Calgary

        # Europe
        'eu-central-1': pytz.timezone('Europe/Berlin'),  # Frankfurt
        'eu-west-1': pytz.timezone('Europe/Dublin'),  # Ireland
        'eu-west-2': pytz.timezone('Europe/London'),  # London
        'eu-south-1': pytz.timezone('Europe/Rome'),  # Milan
        'eu-west-3': pytz.timezone('Europe/Paris'),  # Paris
        'eu-south-2': pytz.timezone('Europe/Madrid'),  # Spain
        'eu-north-1': pytz.timezone('Europe/Stockholm'),  # Stockholm
        'eu-central-2': pytz.timezone('Europe/Zurich'),  # Zurich

        # Israel
        'il-central-1': pytz.timezone('Asia/Jerusalem'),  # Tel Aviv

        # Mexico
        'mx-central-1': pytz.timezone('America/Mexico_City'),  # Central

        # Middle East
        'me-south-1': pytz.timezone('Asia/Bahrain'),  # Bahrain
        'me-central-1': pytz.timezone('Asia/Dubai'),  # UAE

        # South America
        'sa-east-1': pytz.timezone('America/Sao_Paulo'),  # São Paulo

        # AWS GovCloud
        'us-gov-east-1': pytz.timezone('America/New_York'),  # US-East
        'us-gov-west-1': pytz.timezone('America/Los_Angeles'),  # US-West
    }

    df = df[~df['model_id'].str.contains('/', case=False, na=False)]
    # Add local time information
    def get_local_time(row):
        if row['region'] in region_timezones:
            try:
                # Parse ISO timestamp
                utc_time = datetime.strptime(row['job_timestamp_iso'], '%Y-%m-%dT%H:%M:%SZ')
                utc_time = utc_time.replace(tzinfo=pytz.UTC)
                # Convert to local time
                local_time = utc_time.astimezone(region_timezones[row['region']])
                # Return formatted time and hour for grouping
                return pd.Series({
                    'local_time': local_time.strftime('%H:%M:%S'),
                    'hour_of_day': local_time.hour
                })
            except (ValueError, TypeError):
                return pd.Series({'local_time': 'Unknown', 'hour_of_day': -1})
        return pd.Series({'local_time': 'Unknown', 'hour_of_day': -1})

    # Add local time columns
    time_data = df.apply(get_local_time, axis=1)
    df = pd.concat([df, time_data], axis=1)

    # Group data by region
    regional_metrics = df.groupby(['region', 'task_types']).agg({
        'time_to_first_byte': 'mean',
        'time_to_last_byte': 'mean',
        'response_cost': 'mean',
        # 'task_success': 'mean',
        'inference_request_count': 'mean',
        'throughput_tps': 'mean',
        'hour_of_day': lambda x: x.mode()[0] if not x.empty else -1,
        'local_time': lambda x: x.iloc[0] if not x.empty else 'Unknown'
    }).reset_index()

    # Calculate time of day periods
    def get_time_period(hour):
        if hour == -1:
            return "Unknown"
        if 5 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 22:
            return "Evening"
        else:
            return "Night"

    regional_metrics['time_period'] = regional_metrics['hour_of_day'].apply(get_time_period)

    # Calculate a composite score (lower latency, higher success, lower cost is better)
    max_latency = regional_metrics['time_to_last_byte'].max() or 1
    max_cost = regional_metrics['response_cost'].max() or 1

    regional_metrics['composite_score'] = (
            # regional_metrics['task_success'] +
            regional_metrics['inference_request_count'] +
            (1 - (regional_metrics['time_to_last_byte'] / max_latency)) +
            (1 - (regional_metrics['response_cost'] / max_cost))
    )

    regional_metrics['composite_label'] = regional_metrics['region'] + ":<br>" + regional_metrics['task_types']

    # Normalize the composite score
    min_score = regional_metrics['composite_score'].min()
    max_score = regional_metrics['composite_score'].max()
    regional_metrics['normalized_score'] = (regional_metrics['composite_score'] - min_score) / (max_score - min_score)

    # Create a figure with two subplots: latency vs cost, and time of day analysis
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Latency vs Cost by Region", "Hourly Performance by Region"),
        vertical_spacing=0.30,  # Increased for more space between plots
        specs=[[{"type": "scatter"}], [{"type": "bar"}]],
    )

    fig.update_layout(template="plotly_dark")

    # Add scatter plot for latency vs cost
    scatter = go.Scatter(
        x=regional_metrics['time_to_last_byte'],
        y=regional_metrics['response_cost'],
        mode='markers+text',
        marker=dict(
            # size=regional_metrics['task_success'] * 100, #Size based on success rate
            size=regional_metrics['inference_request_count'] * 50,
            color=regional_metrics['composite_score'],
            colorscale='Viridis',
            colorbar=dict(title="Composite Score", y=0.75, len=0.5),  # Positioned in top half
            showscale=True
        ),
        text=regional_metrics['composite_label'],
        textposition="top center",
        hovertemplate=
        '<b>%{text}</b><br>' +
        'Latency: %{x:.2f}s<br>' +
        'Cost: $%{y:.4f}<br>' +
        'Average Number of Retries: ' + regional_metrics['inference_request_count'].apply(lambda x: str(round(x,2)))+ '<br>' +  #%{marker.size:.1f}<br>' +
        'Local Time at Inference: ' + regional_metrics['local_time'] + '<br>' +
        'Time Period: ' + regional_metrics['time_period'] + '<br>',
        name='',
        showlegend=False
    )

    fig.add_trace(scatter, row=1, col=1)

    # Group data by region and hour for hourly analysis
    hourly_data = df.groupby(['region', 'hour_of_day']).agg({
        'throughput_tps': 'mean',
        'time_to_last_byte': 'mean'
    }).reset_index()

    hourly_data = hourly_data[hourly_data['hour_of_day'] != -1]  # Remove unknown hours

    # Add bar chart for hourly performance
    for region in regional_metrics['region'].unique():
        region_data = hourly_data[hourly_data['region'] == region]
        #### EQUALIZE N OF TASKS AND DATA PER REGION
        if not region_data.empty:
            bar = go.Bar(
                x=region_data['hour_of_day'],
                y=region_data['throughput_tps'],
                name=region,
                marker_color=px.colors.qualitative.Plotly[
                    list(regional_metrics['region']).index(region) % len(px.colors.qualitative.Plotly)],
                hovertemplate=
                'Region Inference Hour: %{x}:00<br>' +
                'Tokens Per Second: %{y:.2f}<br>' +
                'Avg Latency: ' + region_data['time_to_last_byte'].apply(lambda x: f"{x:.2f}s") + '<br>' +
                'Region: ' +  region_data['region']
            )

            fig.add_trace(bar, row=2, col=1)

    # Update layout with more spacing
    fig.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#2d2d2d",  # Slightly lighter than paper for contrast

        template="plotly_dark",  # Use the built-in dark template as a base
        title={
            'text': 'Regional Performance Analysis with Time of Day',
            'y': 0.98,  # Position title a bit lower from top
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        height=1000,  # Increased height
        legend_title_text='Region',
        # showlegend=False,
        margin=dict(t=150, b=150),   # More top and bottom margin
    legend=dict(
        y=0.30,  # Adjust this value to position the legend vertically (0.35 is approximately at the bottom subplot)
        x=1.05,  # Position legend to the right of the plot
        xanchor='left',  # Anchor legend to its left side
        yanchor='middle',  # Center legend vertically at the specified y position
        orientation='v'  # Arrange legend items vertically
    )
    )

    # Update x and y axes
    fig.update_xaxes(title_text="Average Latency (Secs)", row=1, col=1)
    fig.update_yaxes(title_text="Average Cost (USD)", row=1, col=1)

    fig.update_xaxes(
        title_text="Hour of Day (24-hour format)",
        tickmode='array',
        tickvals=list(range(0, 24, 3)),
        ticktext=[f"{h}:00" for h in range(0, 24, 3)],
        row=2, col=1
    )
    fig.update_yaxes(title_text="Throughput (TPS)", row=2, col=1)

    # Add recommendations based on data
    best_region_idx = regional_metrics['composite_score'].idxmax()
    best_region = regional_metrics.loc[best_region_idx]

    # Add annotations with recommendations - positioned with better spacing
    fig.add_annotation(
        x=0.5,
        y=0.99,  # Positioned right below title
        xref="paper",
        yref="paper",
        text=f"<b>Recommendation:</b> {best_region['region']} performed best with {str(round(best_region['throughput_tps'],3))} Tokens Per Second {best_region['local_time']} local time ({best_region['time_period']})",
        showarrow=False,
        font=dict(size=14, color="darkgreen"),
        bgcolor="rgba(200, 240, 200, 0.6)",
        bordercolor="green",
        borderwidth=2,
        borderpad=10,
        align="center"
    )


    return fig



if __name__ == "__main__":
    OUTPUT_DIR = Path(
        "./benchmark_results")
    logger.info(f"Starting LLM benchmark report generation with timestamp: {TIMESTAMP}")
    report_file = create_html_report(OUTPUT_DIR, TIMESTAMP)
    logger.info(f"Report generation complete: {report_file}")