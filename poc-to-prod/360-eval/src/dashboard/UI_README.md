# 360-Eval Dashboard user-guide:

A modern Streamlit-based web interface for running, monitoring, and analyzing LLM benchmark evaluations using the LLM-as-a-JURY methodology.


## 🚀 Quick Start

### Launch
These steps come after installing requirements for 360-Eval, please consult README.md for those steps.
```bash
# Navigate to the project directory
cd poc-to-prod/360-eval

# Run the dashboard
python -m streamlit run src/streamlit_dashboard.py
```

The dashboard will be rendered in `http://localhost:8501`

## 📋 Features

### 🛠️ **Setup Tab**
Create and configure new benchmark evaluations with:

**Evaluation Setup:**
- Upload CSV datasets with **prompts** and **golden answers**
- Configure evaluation parameters (parallel calls, invocations, temperature)
- Set experiment counts and custom metrics
- Define task types and evaluation criteria

**Model Configuration:**
- Select and configure LLM models for evaluation
- Choose judge models for assessment
- Set region preferences and cost parameters
- Configure inference profiles

### 📊 **Monitor Tab**
Real-time monitoring of evaluation execution:

- **Execution Queue Status:** Track currently running and queued evaluations
- **Linear Processing:** Evaluations run sequentially to ensure stability
- **Live Status Updates:** Real-time progress tracking by **manual refresh**
- **Active & Recent Evaluations:** View in-progress, completed, and failed evaluations
- **Log Access:** Direct access to evaluation logs
- **Report Generation:** Create individual or aggregated reports

### 📈 **Results Tab**
Detailed analysis of completed evaluations:

- **Evaluation Overview:** Status, timing, and configuration details
- **Model & Judge Information:** Complete details including costs and regions
- **Configuration Display:** All parameters used during evaluation
  - Parallel API Calls
  - Invocations per Scenario
  - Experiment Counts
  - Temperature Variations
  - User-Defined Metrics
- **Performance Metrics:** Duration, success rates, and error analysis

### 📊 **Reports Tab**
Centralized report management and viewing:

- **Report Library:** Table view of all available reports
- **Creation Tracking:** Timestamps and file sizes
- **Evaluation Traceability:** See which evaluations contributed to each report
- **In-App Viewing:** Display HTML reports within the dashboard
- **Download Options:** Export reports for external use

## 🏗️ Architecture

### File Organization
```
360-eval/
├── src/
│   ├── streamlit_dashboard.py          # Main application entry
│   └── dashboard/
│       ├── components/                 # UI components
│       │   ├── evaluation_setup.py    # Setup configuration
│       │   ├── model_configuration.py # Model selection
│       │   ├── evaluation_monitor.py  # Execution monitoring
│       │   ├── results_viewer.py      # Results analysis
│       │   └── report_viewer.py       # Report management
│       └── utils/                      # Core utilities
│           ├── benchmark_runner.py    # Evaluation execution
│           ├── state_management.py    # Session & persistence
│           ├── csv_processor.py       # Data processing
│           └── constants.py           # Configuration
├── benchmark_results/                  # Evaluation outputs
├── prompt-evaluations/                # Evaluation definitions
├── config/                            # Model/judge profiles
└── logs/                              # Execution logs
```

### Data Flow
1. **Setup:** Configure evaluations and models through the UI
2. **Execution:** Evaluations run linearly with queue management
3. **Storage:** Results stored in status files with full configuration
4. **Analysis:** Data loaded from consolidated status files
5. **Reporting:** HTML reports generated and tracked

## 💾 Data Persistence

### Status Files
Each evaluation creates a status file (`eval_{id}_{name}_status.json`) containing:

```json
{
  "status": "completed",
  "results": "/path/to/report.html",
  "models_data": [...],
  "judges_data": [...],
  "evaluation_config": {
    "parallel_calls": 8,
    "invocations_per_scenario": 3,
    "experiment_counts": 2,
    "temperature_variations": 0.7,
    "user_defined_metrics": "accuracy, latency, cost"
  },
  "evaluations_used_to_generate": ["file1.csv", "file2.csv"]
}
```

### Session Management
- **Cross-Session Persistence:** Monitor and Results tabs retain data between browser sessions
- **Configuration Reset:** Setup tab starts fresh each session
- **File-Based Recovery:** Evaluations loaded from status files on startup
- **Automatic Cleanup:** Profile files consolidated into status files after completion

## 🔧 Key Features

### Linear Evaluation Processing
- **Queue-Based Execution:** Evaluations process one at a time
- **Thread Safety:** Eliminates race conditions and resource conflicts
- **Error Isolation:** Failed evaluations don't affect others
- **Progress Tracking:** Real-time status updates with detailed logging

### Smart File Management
- **Consolidated Storage:** All evaluation data stored in status files
- **Automatic Cleanup:** Separate profile files removed after completion
- **Composite Naming:** `{eval_id}_{eval_name}` pattern for easy identification
- **Backward Compatibility:** Legacy file formats supported

### Report Management
- **Centralized Repository:** All reports accessible from dedicated tab
- **Evaluation Tracking:** Clear mapping of reports to source evaluations
- **In-App Viewing:** HTML reports displayed within the dashboard
- **Creation History:** Timestamps and metadata for all reports

## 🚦 Usage Workflow

1. **Configure Evaluation:**
   - Upload CSV dataset in Setup tab
   - Select models and judges
   - Set evaluation parameters

2. **Monitor Execution:**
   - Switch to Monitor tab
   - Add evaluations to execution queue
   - Track progress and view logs

3. **Analyze Results:**
   - View completed evaluations in Results tab
   - Examine model performance and configuration
   - Generate individual reports

4. **Review Reports:**
   - Access all reports in Reports tab
   - View aggregated analysis
   - Download for external use

## 🔍 Troubleshooting

### Common Issues
- **Port Conflicts:** Dashboard runs on `localhost:8501` by default
- **Log Access:** Logs available in `logs/` directory and through UI
- **Session State:** Use manual refresh if auto-updates aren't working
- **File Permissions:** Ensure write access to `benchmark_results/` directory

### Debug Information
- **Log Files:** Detailed execution logs in `logs/` directory
- **Status Files:** Check `logs/*_status.json` for evaluation state
- **Debug Panel:** Available in sidebar for session information

## 📊 Report Features

### Visualization Types
- **Performance Metrics:** Latency, throughput, and cost analysis
- **Success Rate Heatmaps:** Model vs. task performance matrices
- **Error Analysis:** Detailed failure categorization
- **Regional Performance:** Geographic analysis with time zones
- **Judge Score Radars:** Multi-dimensional evaluation criteria

### Export Options
- **HTML Reports:** Interactive charts and tables
- **Download Support:** Export reports for presentations
- **Data Tables:** Integrated analysis with filtering

## 🛡️ Security & Performance

### Session Management
- **Isolated Sessions:** Each browser session maintains separate state
- **Memory Efficient:** Automatic cleanup of completed evaluations
- **Thread Safe:** Concurrent access protection

### Resource Management
- **Linear Processing:** Prevents resource exhaustion
- **Automatic Cleanup:** Removes temporary files after completion
- **Error Handling:** Graceful degradation on failures

