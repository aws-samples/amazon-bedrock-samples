import logging, glob, re, ast, os
import pytz
import sys
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from plotly.subplots import make_subplots
from jinja2 import Template
from collections import Counter
from datetime import datetime
from scipy import stats
from utils import run_inference, report_summary_template, convert_scientific_to_decimal

# Configuration constants
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Analysis constants
MIN_RECORDS_FOR_ANALYSIS = 1000
MIN_RECORDS_FOR_HISTOGRAM = 2000
EPSILON_DIVISION = 0.001  # Small value to prevent division by zero
VALUE_RATIO_MULTIPLIER = 10

# Statistical constants
PERCENTILES = [0.50, 0.90, 0.95, 0.99]
NORMAL_DISTRIBUTION_RANGE_MULTIPLIER = 0.5
NORMAL_DISTRIBUTION_POINTS = 100

# Visualization constants
COEFFICIENT_VARIATION_THRESHOLD = 0.3  # CV < 30% indicates good consistency
GRID_OPACITY = 0.3
COMPOSITE_SCORE_WEIGHTS = {
    'latency': 0.5,
    'cost': 0.5
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'success_rate': {'good': 0.95, 'medium': 0.85},
    'avg_latency': {'good': 0.6, 'medium': 1.2},
    'avg_cost': {'good': 0.5, 'medium': 1.0},
    'avg_otps': {'good': 100, 'medium': 35},
}

# LLM inference settings
INFERENCE_MAX_TOKENS = 750
INFERENCE_TEMPERATURE = 0.3
INFERENCE_REGION = 'us-west-2'

# Get project root directory
PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Setup logger
logger = logging.getLogger(__name__)
log_dir = PROJECT_ROOT / "logs"
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # filename=log_dir / f"visualize_results_{TIMESTAMP}.log",
    filemode='a'
)
logger.info(f"Starting visualization with project root: {PROJECT_ROOT}")

# Load HTML template with absolute path
template_path = PROJECT_ROOT / "assets" / "html_template.txt"
try:
    with open(template_path, 'r') as file:
        HTML_TEMPLATE = file.read()
    logger.info(f"Loaded HTML template from {template_path}")
except FileNotFoundError:
    logger.error(f"HTML template not found at {template_path}")
    HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head><title>LLM Benchmark Report</title></head>
<body><h1>LLM Benchmark Report</h1><p>Template not found, using fallback.</p></body>
</html>"""


def extract_model_name(model_id):
    """Extract clean model name from ID."""
    if '.' in model_id:
        parts = model_id.split('.')
        if len(parts) == 3:
            model_name = parts[-1].split(':')[0].split('-v')[0]
        else:
            model_name = parts[-2] + '.' + parts[-1]
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


def load_data(directory, evaluation_names=None):
    """Load and prepare benchmark data.
    
    Args:
        directory: Directory containing CSV files
        evaluation_names: Optional list of evaluation names to filter by
    """
    # Ensure directory is a Path object
    directory = Path(directory)
    logger.info(f"Looking for CSV files in: {directory}")
    
    # Load CSV files
    all_files = glob.glob(str(directory / "invocations_*.csv"))
    if not all_files:
        logger.error(f"No invocation CSVs found in {directory}")
        raise FileNotFoundError(f"No invocation CSVs found in {directory}")
    
    # Filter files by evaluation names if specified
    if evaluation_names:
        files = []
        for file_path in all_files:
            file_name = Path(file_path).name
            # Check if any evaluation name is in the filename
            if any(eval_name in file_name for eval_name in evaluation_names):
                files.append(file_path)
        
        if not files:
            logger.warning(f"No CSV files found matching evaluations: {evaluation_names}")
            logger.info(f"Available files: {[Path(f).name for f in all_files]}")
            raise FileNotFoundError(f"No CSV files found for evaluations: {evaluation_names}")
        
        logger.info(f"Filtered to {len(files)} CSV files matching evaluations {evaluation_names}: {[Path(f).name for f in files]}")
    else:
        files = all_files
        logger.info(f"Found {len(files)} CSV files (no filter applied): {[Path(f).name for f in files]}")
    
    dataframes = []
    
    for f in files:
        try:
            logger.info(f"Reading file: {f}")
            df_file = pd.read_csv(f)
            logger.info(f"Read {len(df_file)} rows from {f}")
            dataframes.append(df_file)
        except Exception as e:
            logger.error(f"Error reading {f}: {str(e)}")
            continue
    
    if not dataframes:
        logger.error("No valid data found in any CSV files")
        raise ValueError("No valid data found in any CSV files")
    
    df = pd.concat(dataframes, ignore_index=True)
    logger.info(f"Combined data has {len(df)} rows")

    # Clean and prepare data (optimized with method chaining)
    df = (df[df['api_call_status'] == 'Success']
          .reset_index(drop=True)
          .assign(model_name=lambda x: x['model_id'].apply(extract_model_name)))
    parsed_dicts = df['performance_metrics'].apply(parse_json_string)
    del df['performance_metrics']
    # Convert the Series of dictionaries to a DataFrame
    unpacked_findings = pd.DataFrame(list(parsed_dicts))
    df = pd.concat([df, unpacked_findings], axis=1)
    df['task_success'] = df['judge_success']
    # Calculate tokens per second
    df['OTPS'] = df['output_tokens'] / (df['time_to_last_byte'] + EPSILON_DIVISION)

    judge_scores = pd.DataFrame(df['judge_scores'].to_dict()).transpose()
    # Identify numeric index values
    numeric_index_mask = pd.to_numeric(judge_scores.index, errors='coerce').notna()
    # Filter and process judge scores (optimized with method chaining)
    judge_scores_df = (judge_scores[numeric_index_mask]
                       .reset_index(drop=True)
                       .assign(mean_scores=lambda x: x.mean(axis=1)))
    df = pd.concat([df, judge_scores_df], axis=1)
    # ── Cost summary ───────────────────────────────────────────────────────────
    cost_stats = (
        df.groupby(["model_name"])["response_cost"]
          .agg(avg_cost="mean", total_cost="sum", num_invocations="count")
    )

    # ── Latency percentiles (50/90/95/99) ──────────────────────────────────────
    latency_stats = (
        df.groupby(["model_name"])["time_to_last_byte"]
          .quantile(PERCENTILES)         # returns MultiIndex
          .unstack(level=-1)                          # percentiles → columns
    )
    latency_stats.columns = [f"p{int(q*100)}" for q in latency_stats.columns]

    # ── Combine both sets of metrics ──────────────────────────────────────────
    summary = cost_stats.join(latency_stats)

    # Optional: forecast spend per model/profile (30-day projection)
    summary["monthly_forecast"] = (
        summary["avg_cost"]
        * (summary["num_invocations"] / df.shape[0])
        * 30
    )
    df = pd.concat([df, summary], axis=1)

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

    max_raw_ratio = metrics['success_rate'].max() / (metrics['avg_cost'].min() + EPSILON_DIVISION)
    metrics['value_ratio'] = VALUE_RATIO_MULTIPLIER * (metrics['success_rate'] / (metrics['avg_cost'] + EPSILON_DIVISION)) / max_raw_ratio

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


def create_normal_distribution_histogram(df,
                                         key='time_to_first_byte',
                                         label='Time to First Token (seconds)'):
    """
    Creates overlapping histogram plots with normal distribution curves for time_to_first_byte by model.
    Only creates the plot if there are more than 2000 records available.
    
    Args:
        df: DataFrame containing the benchmark data
        label: label for the histogram plot
        key: data column to create the histogram plot
    Returns:
        Plotly figure or None if insufficient data
    """
    min_vals = MIN_RECORDS_FOR_ANALYSIS
    # Check if we have enough data
    # Check if we have enough data
    value_counts = df['model_name'].value_counts()
    # Get values that appear more than 2000 times
    frequent_values = value_counts[value_counts > min_vals].index
    # Filter the dataframe to only include rows where the column value is in our frequent_values list
    df_match = df[df['model_name'].isin(frequent_values)]

    if df_match.empty:
        logger.info(f"Insufficient data for {label} Distribution by Model histogram: {len(df)} records (need >{MIN_RECORDS_FOR_HISTOGRAM})")
        return None

    # Filter out any null values
    df_clean = df_match[df_match[key].notna()].copy()

    if df_clean.empty:
        return ["No valid time_to_first_byte data found"]
    
    logger.info(f"Creating {label} Distribution by Model histogram with {len(df)} records")

    # Create figure
    fig = go.Figure()
    
    # Get unique models and assign colors
    unique_models = df_clean['model_name'].unique()
    colors = px.colors.qualitative.Set1[:len(unique_models)]
    
    # Create histogram and normal distribution for each model
    for i, model in enumerate(unique_models):
        model_data = df_clean[df_clean['model_name'] == model][key]
        
        if len(model_data) < 10:  # Skip models with too few data points
            continue
            
        # Calculate statistics for normal distribution
        mean = model_data.mean()
        std = model_data.std()
        
        # Add histogram
        fig.add_trace(go.Histogram(
            x=model_data,
            name=f'{model} (n={len(model_data)})',
            opacity=0.6,
            marker_color=colors[i % len(colors)],
            histnorm='probability density',  # Normalize to match normal curve
            nbinsx=50,
            showlegend=True
        ))
        
        # Generate points for normal distribution curve
        x_range = np.linspace(
            model_data.min() - NORMAL_DISTRIBUTION_RANGE_MULTIPLIER * std,
            model_data.max() + NORMAL_DISTRIBUTION_RANGE_MULTIPLIER * std,
            NORMAL_DISTRIBUTION_POINTS
        )
        normal_curve = stats.norm.pdf(x_range, mean, std)
        
        # Add normal distribution curve
        fig.add_trace(go.Scatter(
            x=x_range,
            y=normal_curve,
            mode='lines',
            name=f'{model} Normal (μ={mean:.3f}, σ={std:.3f})',
            line=dict(
                color=colors[i % len(colors)],
                width=2,
                dash='dash'
            ),
            opacity=0.8,
            showlegend=True
        ))
    
    # Update layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#2d2d2d",
        title={
            'text': f'{label} Distribution by Model<br><sub>Histograms with Normal Distribution Overlays</sub>',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title=label,
        yaxis_title='Probability Density',
        barmode='overlay',  # Allow histograms to overlap
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        height=800,
        margin=dict(r=250)  # Extra margin for legend
    )

    # Update x and y axes
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=f'rgba(128,128,128,{GRID_OPACITY})')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=f'rgba(128,128,128,{GRID_OPACITY})')
    
    return fig


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
    average_cost_round = (cost_metrics
                          .sort_values('avg_cost')
                          .round({'avg_cost': 5}))
    # 3. Cost Comparison
    cost_fig = px.bar(
        average_cost_round.sort_values('avg_cost'),
        template="plotly_dark",  # Use the built-in dark template as a base
        x='model_name',
        y='avg_cost',
        labels={'model_name': 'Model', 'avg_cost': 'Cost per Response (USD)'},
        title='Using μ (Micro) Symbol for Small Numbers',
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
    ).infer_objects(copy=False).fillna(0)

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
                lambda x: '<br>'.join(list(set(re.findall(r'[A-Za-z-]+', str(x))))) if pd.notnull(x) else "Unknown"
            )

            counts = fails.groupby(['model_name', 'task_types', 'error_category']).size().reset_index(name='count')
            # counts['error_category'] = counts['error_category']
            # if counts
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

            visualizations['error_analysis'] = error_fig.to_html(full_html=False)
        else:
            visualizations['error_analysis'] = '<div id="not-found">No Errors found in the Evaluation</div>'
    else:
        visualizations['error_analysis'] = '<div id="not-found">No Jury Evaluation Found</div>'

    # Add this inside create_visualizations() function
    # Extract judge scores from the DataFrame

    df['parsed_scores'] = df['judge_scores'].apply(extract_judge_scores)
    # Create one radar chart per model (combining all tasks)
    radar_charts = {}

    # Get all unique models and categories
    unique_models = df['model_name'].dropna().unique()
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
                subplot_titles=("Success Rate", "Latency (Secs)", 'Cost per Response (USD)<br><span style="font-size: 12px;">Using μ (Micro) Symbol for Small Numbers</span>', "Tokens per Second")
            )

            # Sort data for each subplot (using method chaining for efficiency)
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
    visualizations['integrated_analysis_table'], analysis_df = create_integrated_analysis_table(model_task_metrics)



    visualizations['regional_performance'] = create_regional_performance_analysis(df)
    
    # Add TTFB histogram with normal distribution (only if sufficient data)
    ttfb_histogram = create_normal_distribution_histogram(df)
    if ttfb_histogram is not None:
        visualizations['ttfb_histogram'] = ttfb_histogram

    accuracy_histogram = create_normal_distribution_histogram(df, key='mean_scores', label='Accuracy Distribution by Model')
    if accuracy_histogram is not None:
        visualizations['accuracy_histogram'] = accuracy_histogram

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


def generate_histogram_findings(df, key='time_to_first_byte', label='Time to First Token'):
    """
    Generate key findings for the TTFB histogram analysis.
    Returns either meaningful findings or a message about insufficient data.

    Args:
        df: DataFrame containing the benchmark data
        key: Key used to measure
        label: Label used to label the findings
    Returns:
        List of finding strings or single message about insufficient data
    """
    min_records = MIN_RECORDS_FOR_ANALYSIS
    # Check if we have enough data
    value_counts = df['model_name'].value_counts()
    # Get values that appear more than 2000 times
    frequent_values = value_counts[value_counts > min_records].index
    # Filter the dataframe to only include rows where the column value is in our frequent_values list
    df_match = df[df['model_name'].isin(frequent_values)]
    if df_match.empty:
        return [f"Not enough data to perform measurements (need at minimum over {MIN_RECORDS_FOR_HISTOGRAM} measurements per model)"]

    # Filter out any null values
    df_clean = df_match[df_match[key].notna()].copy()

    if df_clean.empty:
        return [f"No valid {key} data found"]

    findings = []

    for model in df_clean['model_name'].unique().tolist():
        df_model = df_clean[df_clean['model_name'] == model]
        # Overall statistics
        overall_mean = df_model[key].mean()
        overall_std = df_model[key].std()
        findings.append(f"Model <b>{model}</b> {label}: μ={overall_mean:.3f}s, σ={overall_std:.3f}s across {len(df_model)} measurements")

    # Model-specific analysis (optimized with method chaining)
    model_stats = (df_clean.groupby('model_name')[key]
                   .agg(['mean', 'std', 'count'])
                   .reset_index()
                   .query(f'count >= {min_records}'))  # Only models with sufficient data

    if not model_stats.empty:
        # Fastest model (lowest mean)
        fastest_model = model_stats.loc[model_stats['mean'].idxmin()]
        findings.append(f"Highest achieving model: <b>{fastest_model['model_name']}</b> with {fastest_model['mean']:.3f}s average {label}")

        # Most consistent model (lowest standard deviation)
        most_consistent = model_stats.loc[model_stats['std'].idxmin()]
        findings.append(f"Most consistent model: <b>{most_consistent['model_name']}</b> with {most_consistent['std']:.3f}s standard deviation")

        # Model with highest variability
        most_variable = model_stats.loc[model_stats['std'].idxmax()]
        findings.append(f"Most variable model (fat-tails): <b>{most_variable['model_name']}</b> with {most_variable['std']:.3f}s standard deviation")

        # Distribution characteristics
        # Check for normality using coefficient of variation
        model_stats['cv'] = model_stats['std'] / model_stats['mean']  # Coefficient of variation

        # Models with good normal distribution characteristics (low CV)
        well_distributed = model_stats[model_stats['cv'] < COEFFICIENT_VARIATION_THRESHOLD]  # CV < 30% indicates good consistency
        if not well_distributed.empty:
            best_distributed = well_distributed.loc[well_distributed['cv'].idxmin()]
            findings.append(f"Best distribution characteristics: <b>{best_distributed['model_name']}</b> (Coefficient of Variation/CV={best_distributed['cv']:.2f})")

        # Performance spread analysis
        fastest_mean = model_stats['mean'].min()
        slowest_mean = model_stats['mean'].max()
        performance_spread = ((slowest_mean - fastest_mean) / fastest_mean) * 100
        findings.append(f"Performance spread: {performance_spread:.1f}% difference between best and worst achieving models")
        for model in df_clean['model_name'].unique().tolist():
            # Outlier detection
            df_model = df_clean[df_clean['model_name'] == model]
            q1 = df_model[key].quantile(0.25)
            q3 = df_model[key].quantile(0.75)
            iqr = q3 - q1
            outlier_threshold = q3 + 1.5 * iqr
            outliers = df_model[df_model[key] > outlier_threshold]
            if not outliers.empty:
                outlier_pct = (len(outliers) / len(df_clean)) * 100
                findings.append(f"Outliers for <b>{model}</b>: {len(outliers)} measurements ({outlier_pct:.1f}%) exceed {outlier_threshold:.3f}s")

    return findings


def create_html_report(output_dir, timestamp, evaluation_names=None):
    """Generate HTML benchmark report with task-specific analysis.
    
    Args:
        output_dir: Directory containing CSV files and where report will be saved
        timestamp: Timestamp for report filename
        evaluation_names: Optional list of evaluation names to filter by
    """
    # Ensure output_dir is an absolute path
    if isinstance(output_dir, str):
        if not os.path.isabs(output_dir):
            output_dir = PROJECT_ROOT / output_dir
        output_dir = Path(output_dir)
    
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using output directory: {output_dir}")

    # Use log directory from project root
    log_dir = PROJECT_ROOT / "logs"
    os.makedirs(log_dir, exist_ok=True)
    report_log_file = log_dir / f"report_generation-{timestamp}.log"
    logger.info(f"Report generation logs will be saved to: {report_log_file}")

    # Load and process data
    if evaluation_names:
        logger.info(f"Loading and processing data for evaluations: {evaluation_names}")
    else:
        logger.info("Loading and processing data for all evaluations...")
    try:
        df = load_data(output_dir, evaluation_names)
        evaluation_info = f" for evaluations {evaluation_names}" if evaluation_names else " (all evaluations)"
        logger.info(f"Loaded data with {len(df)} records from {output_dir}{evaluation_info}")
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise


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
    task_level_analysis = '# Task Level Analysis:\n'
    # Prepare task analysis data for template
    task_analysis = []
    for task, chart in visualizations['task_charts'].items():
        task_level_analysis += f'# Task Name: {task}\n\n'
        task_level_analysis += '- ' + '\n- '.join(task_findings.get(task, ["No specific findings available."])) + '\n\n'
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
    unique_models = df['model_name'].dropna().unique().tolist()

    logger.info("Generating TTFT histogram findings...")
    time_to_first_token_findings = generate_histogram_findings(df)
    perf_analysis = '# Performance Analysis across all models:\n- ' + '\n- '.join(time_to_first_token_findings)

    logger.info("Generating Accuracy histogram findings...")
    accuracy_findings = generate_histogram_findings(df, key='mean_scores', label="Average Accuracy")     #TODO: BY TASK??
    acc_analysis = '# Accuracy Analysis across all models:\n- ' + '\n- '.join(accuracy_findings)

    whole_number_cost_metrics = convert_scientific_to_decimal(cost_metrics)
    cost_analysis = '# Cost Analysis across all models on all Task:\n' + '\n'.join([str(i) for i in whole_number_cost_metrics.to_dict(orient='records')])

    recommendations = '# Recommendations:\n* ' + '\n* '.join([str(i) for i in task_recommendations])

    prompt_template = report_summary_template(models=unique_models, evaluations=f'{acc_analysis}\n\n{cost_analysis}\n\n{perf_analysis}\n\n{task_level_analysis}\n\n{recommendations}')  ## Append AND Format all evals ++ rename the columns to help the model
    inference = run_inference(model_name='bedrock/converse/us.amazon.nova-premier-v1:0',
                              prompt_text=prompt_template,
                              stream=False,
                              provider_params={"maxTokens": INFERENCE_MAX_TOKENS,
                                               "temperature": INFERENCE_TEMPERATURE,
                                               # "topP": 0.9,
                                               "aws_region_name": INFERENCE_REGION})['text']
    html = Template(HTML_TEMPLATE).render(
        timestamp=formatted_date,
        inference=inference,

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
        error_analysis_div=visualizations['error_analysis'],
        integrated_analysis_table_div=visualizations['integrated_analysis_table'].to_html(full_html=False),
        regional_performance_div=visualizations['regional_performance'].to_html(full_html=False),
        
        # TTFB histogram (only if sufficient data)
        ttfb_histogram_div=visualizations['ttfb_histogram'].to_html(full_html=False) if 'ttfb_histogram' in visualizations else '',
        ttfb_findings=time_to_first_token_findings,

        # Accuracy histogram (only if sufficient data)
        accuracy_histogram_div=visualizations['accuracy_histogram'].to_html(
            full_html=False) if 'accuracy_histogram' in visualizations else '',
        accuracy_findings=accuracy_findings,
        # Recommendations
        task_recommendations=task_recommendations,
    )

    # Write report to file with evaluation-specific naming
    if evaluation_names:
        eval_suffix = "_" + "_".join(evaluation_names[:3])  # Limit to first 3 for filename length
        if len(evaluation_names) > 3:
            eval_suffix += f"_and_{len(evaluation_names)-3}_more"
        out_file = output_dir / f"llm_benchmark_report_{timestamp}{eval_suffix}.html"
    else:
        out_file = output_dir / f"llm_benchmark_report_{timestamp}.html"
    
    logger.info(f"Writing HTML report to: {out_file}")
    out_file.write_text(html, encoding="utf-8")
    evaluation_scope = f"for {len(evaluation_names)} specific evaluations" if evaluation_names else "for all evaluations"
    logger.info(f"HTML report written successfully {evaluation_scope}")

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
    for each model and task type with optimal range highlighting using a green/yellow/red color scheme.
    """
    # Use predefined thresholds for each metric (good, medium, poor)
    thresholds = PERFORMANCE_THRESHOLDS

    # Define colors
    colors = {
        'good': '#c6efce',  # green
        'medium': '#ffffcc',  # yellow
        'poor': '#ffcccc'  # red
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
            (1 - (table_data['avg_latency'] / max_latency)) * COMPOSITE_SCORE_WEIGHTS['latency'] +
            (1 - (table_data['avg_cost'] / max_cost)) * COMPOSITE_SCORE_WEIGHTS['cost']
    )

    # Create figure
    fig = go.Figure()

    # Helper function to determine color based on value and thresholds
    def get_color(value, metric):
        if metric == 'success_rate' or metric == 'avg_otps':
            if value >= thresholds[metric]['good']:
                return colors['good']
            elif value >= thresholds[metric]['medium']:
                return colors['medium']
            else:
                return colors['poor']
        else:  # For latency and cost, lower is better
            if value <= thresholds[metric]['good']:
                return colors['good']
            elif value <= thresholds[metric]['medium']:
                return colors['medium']
            else:
                return colors['poor']

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
            # Conditional formatting based on thresholds
            fill_color=[
                ['white'] * len(table_data),  # Model column (no coloring)
                ['white'] * len(table_data),  # Task column (no coloring)
                # Success rate coloring (three-color)
                [get_color(sr, 'success_rate') for sr in table_data['success_rate']],
                # Latency coloring (three-color)
                [get_color(lt, 'avg_latency') for lt in table_data['avg_latency']],
                # Cost coloring (three-color)
                [get_color(cost, 'avg_cost') for cost in table_data['avg_cost']],
                # OTPS coloring (just use white)
                # ['white'] * len(table_data),
                [get_color(tps, 'avg_otps') for tps in table_data['avg_otps']],
                # Composite score coloring based on quantiles
                [colors['good'] if score >= table_data['composite_score'].quantile(0.67) else
                 colors['medium'] if score >= table_data['composite_score'].quantile(0.33) else
                 colors['poor'] for score in table_data['composite_score']]
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
        template="ggplot2",
    )

    return fig, table_data.to_dict(orient='records')


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

    # df = df[df['model_id'].str.contains('bedrock', case=False, na=False)]
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
    df['average_input_output_token_size'] = df['input_tokens'] + df['output_tokens']
    # Group data by region
    regional_metrics = df.groupby(['region', 'task_types']).agg({
        'average_input_output_token_size': 'mean',
        'time_to_first_byte': 'mean',
        'time_to_last_byte': 'mean',
        'response_cost': 'mean',
        'inference_request_count': 'mean',
        'throughput_tps': 'mean',
        'hour_of_day': lambda x: x.mode()[0] if not x.empty else -1,
        'local_time': lambda x: x.iloc[0] if not x.empty else 'Unknown'
    }).reset_index()

    regional_metrics['average_input_output_token_size'] = regional_metrics['average_input_output_token_size'].round(1).astype("string")
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

    regional_metrics['composite_label'] = regional_metrics['region'] + "<br>Mean of Total Token Size: " + regional_metrics['average_input_output_token_size']

    # Normalize the composite score
    min_score = regional_metrics['composite_score'].min()
    max_score = regional_metrics['composite_score'].max()
    regional_metrics['normalized_score'] = (regional_metrics['composite_score'] - min_score) / (max_score - min_score)

    # Create a figure with two subplots: latency vs cost, and time of day analysis
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Latency vs Cost by Region", 'Hourly Performance by Region<br><span style="font-size: 12px;">Using μ (Micro) Symbol for Small Numbers</span>'),
        vertical_spacing=0.30,  # Increased for more space between plots
        specs=[[{"type": "scatter"}], [{"type": "bar"}]],
    )

    fig.update_layout(template="plotly_dark")

    # Calculate min and max for scaling
    min_count = regional_metrics['inference_request_count'].min()
    max_count = regional_metrics['inference_request_count'].max()

    # Create a more dramatic size scale (20-100 instead of default)
    size_values = 20 + ((regional_metrics['inference_request_count'] - min_count) / (((max_count - min_count) * 50) + 1))

    # Add scatter plot for latency vs cost
    scatter = go.Scatter(
        x=regional_metrics['time_to_last_byte'],
        y=regional_metrics['response_cost'],
        mode='markers+text',
        marker=dict(
            size=size_values, #Size based on success rate
            # size=regional_metrics['inference_request_count'] * 50,
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
        'Average Number of Retries: ' + regional_metrics['inference_request_count'].apply(lambda x: str(round(x,2)))+ '<br>' +
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
    # Use absolute path relative to project root
    OUTPUT_DIR = PROJECT_ROOT / "benchmark-results"
    logger.info(f"Starting LLM benchmark report generation with timestamp: {TIMESTAMP}")
    try:
        report_file = create_html_report(OUTPUT_DIR, TIMESTAMP)
        logger.info(f"Report generation complete: {report_file}")
        print(f"Report generated successfully: {report_file}")
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        print(f"Error generating report: {str(e)}")
        sys.exit(1)