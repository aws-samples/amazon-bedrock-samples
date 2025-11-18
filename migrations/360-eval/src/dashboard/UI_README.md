# 360-Eval Dashboard Tutorial & User Guide

A Streamlit-based web interface for running, monitoring, and analyzing LLM benchmark evaluations using the LLM-as-a-JURY methodology.

## 🚀 Getting Started

### Prerequisites
- Install dependencies from the main README.md
- Configure AWS credentials for Bedrock access

### Launch the Dashboard
```bash
# Navigate to the project directory
cd poc-to-prod/360-eval

# Run the dashboard
python -m streamlit run src/streamlit_dashboard.py
```

The dashboard will be available at `http://localhost:8501`

<img src="/migrations/360-eval/assets/main_ui.png" alt="Alt Text" width="700" height="300">

*Main dashboard interface showing the 4-tab navigation structure*

### Close the Dashboard
To stop the dashboard:
- Press `Ctrl+C` in the terminal where the dashboard is running
---

## 📚 Step-by-Step Tutorial

### Step 1: Setting Up Your First Evaluation

#### 1.1 Navigate to Setup Tab
The Setup tab contains three sub-tabs:

<img src="/migrations/360-eval/assets/model_config.png" alt="Alt Text" width="700" height="300">

*Setup tab showing the three configuration sub-tabs: Evaluation Setup, Model Configuration, and Advanced Configuration*

**🔧 Evaluation Setup Tab**
1. **Name Your Evaluation**
   - Enter a descriptive name (e.g., "Customer_Support_Bot_V2")
   - This name identifies your results and reports

2. **Upload Your Dataset**
   - Click "Upload CSV with prompts and golden answers"
   - Your CSV should have at least two columns:
     - One for prompts (questions/inputs)
     - One for golden answers (expected responses)
   - Example CSV structure:
     ```csv
     prompt,golden_answer
     "What is the capital of France?","Paris"
     "Explain machine learning","Machine learning is..."
     ```

<img src="/migrations/360-eval/assets/csv_labeling.png" alt="Alt Text" width="700" height="300">

*CSV file upload interface with column selection dropdowns*

3. **Select Data Columns**
   - Choose the "Prompt Column" (contains your test questions)
   - Choose the "Golden Answer Column" (contains expected responses)
   - Preview your data to verify selections

4. **Vision Model Configuration** (Optional)
   - Enable the "Vision Model" checkbox if testing vision-capable models
   - Select the "Image Column" containing base64-encoded images or image file paths
   - This allows evaluation of multimodal models that process both text and images


5. **Configure Multiple Task Evaluations**
   - Use "Number of Task Evaluations" to create multiple tests
   - For each task evaluation, specify:
     - **Task Type**: e.g., "Question-Answering", "Summarization", "Translation"
     - **Task Criteria**: Detailed evaluation instructions
     - **Temperature**: Controls response creativity (0.01 = deterministic, 1.0 = very creative)
     - **User-Defined Metrics**: Optional custom criteria (e.g., "professional tone")

**Example Multi-Task Setup:**
- Task 1: Question-Answering, Temperature 0.3, Focus on factual accuracy
- Task 2: Creative Writing, Temperature 0.8, Focus on engagement and creativity

<img src="/migrations/360-eval/assets/task_def.png" alt="Alt Text" width="700" height="300">

*Multiple task evaluation setup showing task type, criteria, temperature, and custom metrics*

#### 1.2 Configure Models (Model Configuration Tab)
1. **Select Models to Evaluate**
   - Choose from available LLM models
   - Configure regions and inference profiles
   - Set cost parameters for each model

<img src="/migrations/360-eval/assets/model_config.png" alt="Alt Text" width="700" height="300">

*Model configuration interface showing region selector, model dropdown, and cost settings*

2. **Choose Judge Models**
   - Select models that will evaluate the responses
   - Judges assess quality based on your task criteria
   - Can use different models as judges than those being evaluated
   - Configure input/output costs for accurate cost tracking

3. **Load Previous Configurations** (Optional)
   - Use the "Load Config" button from completed evaluations to reuse settings
   - This copies all parameters from a previous evaluation
   - Useful for testing variations or running similar evaluations

*Display of selected models and judge models with cost information and clear buttons*

#### 1.3 Set Parameters (Advanced Configuration Tab)
Fine-tune execution parameters:
- **Parallel API Calls**: Start with 4 for most use cases (range: 1-20)
- **Invocations per Scenario**: Use 3-5 for reliable results (range: 1-20)
- **Pass|Failure Threshold**: Set evaluation pass/fail cutoff (range: 2-4)
- **Sleep Between Invocations**: 60-120 seconds for production APIs (range: 0-300)
- **Experiment Counts**: Number of runs (use 1 for testing, 3-5 for production, range: 1-10)
- **Temperature Variations**: Test additional temperature settings automatically (range: 0-5)
- **Experiment Wait Time**: Time between experiment runs (dropdown: 0 minutes to 3 hours)

<img src="/migrations/360-eval/assets/advance_config.png" alt="Alt Text" width="700" height="300">

*Advanced configuration tab showing all parameter controls with ranges and help text*

**💾 Save Your Configuration**
Click "Save Configuration" to store your setup.

**⚠️ Model Access Validation**
When you run an evaluation, the system will first check access to all selected models in parallel:
- ✅ Accessible models will be included in the evaluation
- ⚠️ If some models fail access check, evaluation continues with available models
- ❌ If no models are accessible, evaluation fails with clear error messages

### Step 2: Running Evaluations

#### 2.1 Navigate to Monitor Tab
The Monitor tab shows "Processing Evaluations" and execution controls.

<img src="/migrations/360-eval/assets/monitor.png" alt="Alt Text" width="700" height="400">

*Monitor tab showing status, evaluation table, and execution controls*

#### 2.2 Queue Your Evaluations
1. **Select Evaluations to Run**
   - Use the dropdown to select from available (not yet processed) evaluations
   - Only shows evaluations that haven't been completed, failed, or are currently running
   - Multiple evaluations can be selected for batch processing

2. **Add to Execution Queue**
   - Click "🚀 Add to Execution Queue"
   - Evaluations run sequentially (one at a time) for stability
   - Monitor queue status and currently running evaluation

#### 2.3 Monitor Progress
- **Queue Status**: Shows currently running and queued evaluations
- **Manual Refresh**: Click "Refresh Evaluations" to update status (no auto-refresh)
- **Status Badges**: Color-coded indicators (Running=blue, Completed=green, Failed=red, Queued=yellow)
- **Progress Bars**: Real-time completion percentage for running evaluations
- **Log Monitoring**: Check the logs directory for detailed progress


#### 2.4 Delete Evaluations
- **Select Evaluations**: Use multi-select to choose evaluations to remove
- **Delete Process**: Click "🗑️ Delete Selected Evaluations"
- **Confirmation**: Action removes evaluations from all lists and cleans up files

### Step 3: Analyzing Results

#### 3.1 Navigate to Evaluations Tab
View all completed evaluations with detailed information.

**Filter Options**: Use filter buttons to show:
- **All**: All evaluations regardless of status
- **Successful**: Only completed evaluations
- **Failed**: Only failed evaluations

<img src="/migrations/360-eval/assets/evaluations.png" alt="Alt Text" width="700" height="400">

*Evaluations tab showing filter buttons and completed evaluations list*

#### 3.2 Review Evaluation Data
The main table shows:
- **Name**: Evaluation identifier
- **Task Type**: What was being tested
- **Data File**: Original CSV filename used
- **Temperature**: Temperature setting used
- **Custom Metrics**: Whether custom metrics were applied
- **Models**: Number of models tested
- **Judges**: Number of judge models used
- **Completed**: Completion timestamp

#### 3.3 Detailed Analysis
1. **Select an Evaluation**: Choose from the dropdown
2. **Review Configuration**: See all parameters used, including:
   - Basic info (task type, criteria, status, duration)
   - Models evaluated (displayed as DataFrame with costs)
   - Judge models (displayed as DataFrame with costs)
   - Results files and configuration details
3. **Model Performance**: Analyze results by model and judge
4. **Error Analysis**: Check for any issues or failures
5. **Action Buttons**: 
   - **📋 Load Config**: Reuse this evaluation's settings for new evaluation
   - **🗑️ Delete**: Remove this evaluation
   - **📊 View Report**: Open associated HTML report


### Step 4: Viewing Reports

#### 4.1 Navigate to Reports Tab
Location for viewing HTML reports that are automatically generated when evaluations complete.

#### 4.2 Automatic Report Generation
**Important**: Reports are automatically created during the evaluation process, not manually generated:
- Each completed evaluation has an associated HTML report
- Reports are generated automatically when the benchmark process finishes
- You cannot manually create new reports - they are tied to completed evaluations

**⚠️ Report Generation Requirement:**
For HTML reports to be generated, you must have access to the `us.amazon.nova-premier-v1:0` model in your AWS account. This model is used to analyze evaluation results and create the report content. If this model is not accessible, evaluations will complete successfully but HTML reports will not be generated.

#### 4.3 View Reports
1. **Select Evaluation**: Choose from dropdown of completed evaluations that have reports
2. **View Report**: HTML reports display within the dashboard interface showing:
   - Performance charts comparing models
   - Cost analysis and budget tracking
   - Response time distributions
   - Success rate matrices
   - Error categorization and analysis

<img src="/migrations/360-eval/assets/report.png" alt="Alt Text" width="700" height="400">

*Reports tab showing evaluation selector and HTML report viewer*

#### 4.4 Report Access
- Reports are linked to their source evaluations
- If an evaluation is deleted, its report may also be removed
- Reports combine data from the evaluation's CSV output files

---

## 🔄 Workflow Example

### Scenario: Testing a Customer Service Chatbot

#### Step 1: Prepare Your Data
Create a CSV file with customer service scenarios:
```csv
customer_query,expected_response_type
"How do I return a product?","Provide clear return policy steps"
"What are your business hours?","State specific hours and timezone"
"I'm having trouble with my order","Show empathy and offer specific help"
```

#### Step 2: Configure Evaluation
1. **Upload CSV** and select columns
2. **Create Multiple Tasks**:
   - Task 1: "Accuracy" - Temperature 0.2 - "Provide factually correct information"
   - Task 2: "Helpfulness" - Temperature 0.5 - "Be helpful and customer-friendly"
   - Task 3: "Brand Voice" - Temperature 0.4 - Custom metrics: "professional tone, brand consistency"

#### Step 3: Select Models and Judges
- **Models**: Test various LLM models
- **Judges**: Use different models as judges
- **Settings**: 3 invocations per scenario, 2 experiment counts

#### Step 4: Execute and Monitor
1. Save configuration and go to Monitor tab
2. Add evaluation to queue and monitor progress
3. Use logs to track detailed execution

#### Step 5: Analyze Results
1. View completed evaluation in Evaluations tab
2. Compare model performance across different tasks
3. Review temperature impact and custom metrics

#### Step 6: Review Reports
1. Navigate to Reports tab to view automatically generated reports
2. Review visualizations and performance metrics for each completed evaluation
3. Reports are automatically created and available immediately after evaluation completion

---

## 🔧 Features

### Multi-Task Evaluations
Create tests by configuring multiple task types with different:
- Evaluation criteria
- Temperature settings
- Custom metrics
- Success measures

### Temperature Testing
- **Factual Tasks**: Use low temperature (0.1-0.3)
- **Creative Tasks**: Use higher temperature (0.7-0.9)
- **Mixed Tasks**: Test multiple temperatures automatically

### Custom Metrics
Add domain-specific evaluation criteria:
- Brand voice consistency
- Technical accuracy
- Emotional appropriateness
- Regulatory compliance

### Queue Management
- **Batch Processing**: Add multiple evaluations to queue
- **Priority Handling**: Queue processes in selection order
- **Resource Management**: Sequential execution prevents conflicts

### Vision Model Support
- **Multimodal Testing**: Evaluate models that process both text and images
- **Image Input**: Support for base64-encoded images or image file paths
- **Vision-Specific Configuration**: Dedicated settings for image-based evaluations

### Configuration Reuse
- **Load Previous Settings**: Reuse configurations from completed evaluations
- **Template Creation**: Save successful configurations as templates
- **Variation Testing**: Create variations of proven configurations

---

## 📊 Results and Reports

### CSV Output Files
The evaluation process generates CSV files containing:
- **Model responses**: Raw outputs from each tested model
- **Judge scores**: Numerical ratings and assessments
- **Latency data**: Response time measurements
- **Cost tracking**: Token usage and pricing information
- **Error logs**: Any failures or issues encountered
- **Configuration data**: Parameters used for each test

### HTML Reports
Reports are automatically generated for each completed evaluation and provide visual analysis including:
- Performance charts comparing models
- Cost analysis and budget tracking
- Response time distributions
- Success rate matrices
- Error categorization and analysis

Each report is specific to one evaluation and combines data from that evaluation's CSV output files.

---

## 🚨 Troubleshooting

### Common Issues and Solutions

**Issue**: Evaluation gets stuck in "queued" status
- **Solution**: Check logs for API errors or rate limiting
- **Prevention**: Use appropriate sleep intervals between calls

**Issue**: CSV upload fails
- **Solution**: Verify CSV format and column headers
- **Check**: Ensure file encoding is UTF-8

**Issue**: Models not available or access denied
- **Solution**: Verify AWS credentials and region settings
- **Check**: Ensure Bedrock model access is enabled in your AWS account
- **Note**: The system performs parallel model access checks before evaluation starts

**Issue**: Reports not available
- **Solution**: Reports are auto-generated, not manually created
- **Check**: Ensure evaluation completed successfully and CSV files are present
- **Check**: Verify access to `us.amazon.nova-premier-v1:0` model (required for report generation)
- **Note**: Each evaluation automatically creates its own report

### Debug Tools
- **Sidebar Debug Panel**: Session information and log access
- **Log Files**: Detailed execution logs in `logs/` directory
- **Status Files**: Check evaluation state in status JSON files
- **Manual Refresh**: Use refresh buttons (no auto-refresh available)
- **Model Access Check**: Parallel validation provides immediate feedback on model availability


### Performance Tips
- **Parallel Calls**: Adjust based on API rate limits
- **Sleep Intervals**: Increase if experiencing rate limiting
- **Batch Size**: Process smaller evaluation sets for faster feedback
- **Resource Monitoring**: Watch CPU and memory usage during execution

---

## 🎯 Best Practices

### Data Preparation
- **Clear Prompts**: Write specific, unambiguous test prompts
- **Quality Golden Answers**: Provide detailed expected responses
- **Balanced Dataset**: Include various difficulty levels and scenarios
- **Consistent Format**: Maintain uniform CSV structure

### Evaluation Configuration
- **Start Small**: Begin with 1-2 models and simple criteria
- **Iterative Approach**: Add complexity gradually
- **Temperature Testing**: Use different temperatures for different task types
- **Multiple Judges**: Use 2+ judge models for reliable assessment

### Execution Management
- **Sequential Processing**: Let evaluations run one at a time
- **Monitor Resources**: Watch for API rate limits and costs
- **Log Review**: Check logs for detailed progress and error information
- **Patience**: Large evaluations can take significant time

### Report Usage
- **Automatic Generation**: Reports are created automatically for each evaluation
- **Immediate Access**: Reports available as soon as evaluation completes
- **Evaluation-Specific**: Each report corresponds to exactly one evaluation

---

## 📸 Screenshot Requirements

To complete this documentation, the following screenshots should be captured and placed in a `screenshots/` directory:

### Main Interface Screenshots
1. **dashboard-home.png** - Main dashboard showing 4-tab navigation
2. **setup-tab-overview.png** - Setup tab with three sub-tabs visible
3. **monitor-tab-overview.png** - Monitor tab showing queue status and controls
4. **evaluations-tab.png** - Evaluations tab with filter buttons
5. **reports-tab.png** - Reports tab with evaluation selector and viewer

### Setup Process Screenshots
6. **csv-upload.png** - CSV upload interface with column selection
7. **vision-model-config.png** - Vision model checkbox and image column selector
8. **task-configuration.png** - Multiple task setup form
9. **model-selection.png** - Model configuration with region and cost settings
10. **selected-models-display.png** - Models and judges display tables
11. **advanced-configuration.png** - Advanced parameters tab

### Monitoring Screenshots
12. **evaluation-progress.png** - Evaluation table with status badges and progress bars
13. **log-viewer.png** - Log viewer with expandable sections

### Results Screenshots
14. **evaluation-details.png** - Detailed evaluation view with action buttons
15. **complete-workflow.png** - Overview showing end-to-end process

### Utility Screenshots
16. **debug-panel.png** - Sidebar debug panel expanded

### Screenshot Guidelines
- Use consistent browser window size (1440x900 recommended)
- Capture with sample data that demonstrates features
- Ensure UI elements are clearly visible
- Use light theme for better documentation visibility
- Include realistic evaluation names and data in examples

---

