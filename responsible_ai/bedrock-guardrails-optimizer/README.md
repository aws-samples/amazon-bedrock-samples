### Amazon Bedrock Guardrails Evaluation and Optimization Framework

This project provides a framework for evaluating and optimizing Amazon Bedrock Guardrails configurations
for AI assistants. The files `failed_guardrail_results.json` and `passed_guardrail_results.json` contain test cases
with expected results that define the desired guardrail behavior.

The goal is to iteratively find the optimal Bedrock Guardrails configuration that maximizes test accuracy
by correctly allowing legitimate queries while blocking off-topic or harmful content.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPTIMIZATION WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
  │  1. DEFINE   │      │  2. EVALUATE │      │  3. OPTIMIZE │
  │  TEST INPUTS │ ───▶ │   BASELINE   │ ───▶ │   ITERATE    │
  └──────────────┘      └──────────────┘      └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
   CSV or Manual         Deploy & Test        Agent analyzes
   test queries          against initial      failures, adjusts
   with expected         guardrail config     config parameters
   pass/reject                                      │
                                                    ▼
                                            ┌──────────────┐
  ┌──────────────┐      ┌──────────────┐    │   Repeat     │
  │  5. DEPLOY   │      │  4. REVIEW   │    │   until      │
  │  BEST CONFIG │ ◀─── │   REPORTS    │ ◀──│   target     │
  └──────────────┘      └──────────────┘    │   accuracy   │
        │                     │             └──────────────┘
        ▼                     ▼
   Production-ready      HTML/PDF reports
   guardrail on AWS      with metrics and
                         iteration history
```

All configurations are validated against AWS documentation.
Uses Standard Tier with Cross-region endpoints for Guardrails.
When agents are required, uses Strands Agents SDK.
When models are required, uses Amazon Bedrock via Converse API with modelId "global.anthropic.claude-opus-4-5-20251101-v1:0". You can change this for any other model you want to use for the optimization agent.

## Setup

```bash
pip install -r requirements.txt
```

Ensure AWS credentials are configured with Bedrock access.

## Usage

### Web Interface (Recommended)

Start the web server for a visual interface:

```bash
cd src
python api_server.py
```

Then open http://localhost:8080 in your browser.

The web interface provides:
- **Test Inputs**: Add manually, upload CSV, or load sample inputs
- **Guardrail Config**: Use default, existing ID, upload JSON, or visual editor with content filters, denied topics, and word filters
- **Evaluation**: Test inputs against guardrails and generate passed/failed JSON files
- **Optimization**: Run with configurable iterations, metrics, and stop/resume control
- **Live Logs**: Real-time streaming logs panel (click 📋 button)
- **Reports**: View HTML reports, iteration details, and best configurations
- **Deploy**: Deploy optimized guardrail to AWS

### Command Line

#### 1. Deploy Baseline Guardrail
```bash
cd src
python deploy_baseline.py [region]
```

#### 2. Evaluate a Guardrail
```bash
python run_evaluation.py <guardrail_id> [region]
```

#### 3. Run Optimization Agent
```bash
python run_optimization.py [options]
```

Options:
- `-n, --max-iterations N` - Maximum iterations (default: 5)
- `-r, --region REGION` - AWS region (default: us-east-1)
- `-b, --start-from-baseline` - Start from baseline config instead of best previous
- `-m, --metrics METRICS` - Target metrics: accuracy, latency, generalization, all (default: accuracy)
- `-p, --passed-file FILE` - Path to passed test cases JSON
- `-f, --failed-file FILE` - Path to failed test cases JSON

Examples:
```bash
# Default: 5 iterations, optimize accuracy
python run_optimization.py

# Use custom test files
python run_optimization.py -p custom_passed.json -f custom_failed.json

# 10 iterations, optimize for accuracy and latency
python run_optimization.py -n 10 -m accuracy latency

# Start fresh from baseline, optimize all metrics
python run_optimization.py --start-from-baseline --metrics all
```

#### 4. Generate Test Results from CSV
```bash
python generate_test_results.py <csv_file> [options]
```

Converts a CSV of test inputs into passed/failed JSON files.

Options:
- `-g, --guardrail-id ID` - Existing guardrail ID to test against
- `-r, --region REGION` - AWS region (default: us-east-1)
- `-o, --output-dir DIR` - Output directory (default: project root)
- `--deploy-baseline` - Deploy baseline guardrail if no ID provided

CSV Format:
```csv
input,expected
"What is the CPU usage?",pass
"Write me a poem",reject
```

Examples:
```bash
# Test against existing guardrail
python generate_test_results.py ../sample_test_inputs.csv -g abc123xyz

# Deploy baseline guardrail and test
python generate_test_results.py ../sample_test_inputs.csv --deploy-baseline
```

Output files are timestamped (e.g., `passed_guardrail_results_20260129_143000.json`).

#### 5. Generate Reports (standalone)
```bash
python -m report_generator [report_directory]
```

## Customizing for Your Use Case

1. **Define Test Cases**: Create `passed_guardrail_results.json` and `failed_guardrail_results.json` with:
   - `input`: The user query to test
   - `expected`: Either "pass" or "reject"

2. **Configure Baseline**: Modify `src/guardrail_config.py` for your domain

3. **Run Optimization**: The agent iteratively improves the configuration

## Output Files

All outputs are stored in `evaluation_reports/`:

- `eval_YYYYMMDD_HHMMSS_iterN.json` - Per-iteration reports
- `best_config_YYYYMMDD_HHMMSS.json` - Best performing configuration
- `optimization_report_YYYYMMDD_HHMMSS.html` - Final report with charts
- `optimization_report_YYYYMMDD_HHMMSS.pdf` - PDF version (requires weasyprint)

## Generalization Testing

The `test_generalization` tool uses an LLM to generate novel test cases similar to denied topics but not in the test dataset. This detects overfitting.

Score interpretation:
- `>80%`: Good generalization
- `50-80%`: Moderate - consider broadening topic definitions  
- `<50%`: Poor - topics may be overfitting to examples

## Project Structure

- `index.html` - Web interface for the optimizer
- `src/api_server.py` - Flask API server for web interface
- `src/guardrail_config.py` - Baseline guardrail configuration
- `src/evaluator.py` - Test case evaluation
- `src/guardrail_manager.py` - Guardrail CRUD operations
- `src/optimization_agent.py` - Strands agent for optimization
- `src/report_generator.py` - HTML/PDF report generation
- `src/generate_test_results.py` - CSV to JSON converter
- `src/run_optimization.py` - CLI for optimization
- `sample_test_inputs.csv` - Example CSV with all test inputs
- `evaluation_reports/` - Output directory
