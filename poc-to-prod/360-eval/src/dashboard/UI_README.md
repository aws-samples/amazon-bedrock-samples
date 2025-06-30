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

### Close the Dashboard
To stop the dashboard:
- Press `Ctrl+C` in the terminal where the dashboard is running
---

## 📚 Step-by-Step Tutorial

### Step 1: Setting Up Your First Evaluation

#### 1.1 Navigate to Setup Tab
The Setup tab contains three sub-tabs:

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

3. **Select Data Columns**
   - Choose the "Prompt Column" (contains your test questions)
   - Choose the "Golden Answer Column" (contains expected responses)
   - Preview your data to verify selections

4. **Configure Multiple Task Evaluations**
   - Use "Number of Task Evaluations" to create multiple tests
   - For each task evaluation, specify:
     - **Task Type**: e.g., "Question-Answering", "Summarization", "Translation"
     - **Task Criteria**: Detailed evaluation instructions
     - **Temperature**: Controls response creativity (0.01 = deterministic, 1.0 = very creative)
     - **User-Defined Metrics**: Optional custom criteria (e.g., "professional tone")

**Example Multi-Task Setup:**
- Task 1: Question-Answering, Temperature 0.3, Focus on factual accuracy
- Task 2: Creative Writing, Temperature 0.8, Focus on engagement and creativity

#### 1.2 Configure Models (Model Configuration Tab)
1. **Select Models to Evaluate**
   - Choose from available LLM models
   - Configure regions and inference profiles
   - Set cost parameters for each model

2. **Choose Judge Models**
   - Select models that will evaluate the responses
   - Judges assess quality based on your task criteria
   - Can use different models as judges than those being evaluated

#### 1.3 Set Parameters (Third Configuration Tab)
Fine-tune execution parameters:
- **Parallel API Calls**: Start with 4 for most use cases
- **Invocations per Scenario**: Use 3-5 for reliable results
- **Sleep Between Invocations**: 60-120 seconds for production APIs
- **Experiment Counts**: Number of runs (use 1 for testing, 3-5 for production)
- **Temperature Variations**: Test additional temperature settings automatically

**💾 Save Your Configuration**
Click "Save Evaluation Configuration" to store your setup.

### Step 2: Running Evaluations

#### 2.1 Navigate to Monitor Tab
The Monitor tab shows "Processing Evaluations" and execution controls.

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
- **Manual Refresh**: Click "Refresh Evaluations" to update status
- **Log Monitoring**: Check the logs directory for detailed progress

### Step 3: Analyzing Results

#### 3.1 Navigate to Evaluations Tab
View all completed evaluations with detailed information.

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
2. **Review Configuration**: See all parameters used
3. **Model Performance**: Analyze results by model and judge
4. **Error Analysis**: Check for any issues or failures

### Step 4: Generating and Managing Reports

#### 4.1 Navigate to Reports Tab
Location for all report generation and management.

#### 4.2 Generate New Reports
1. **Choose Report Scope**:
   - **All Evaluations**: Include all completed evaluations
   - **Selected Evaluations**: Choose specific evaluations to include

2. **Select Evaluations** (if using Selected Evaluations):
   - Pick which completed evaluations to include
   - Useful for focused analysis or comparison

3. **Generate Report**:
   - Click "🔄 Generate Report"
   - Wait for processing (may take a few moments)
   - New report appears in Available Reports section

#### 4.3 View Reports
1. **Available Reports Table**: Shows all generated reports with:
   - Report name and creation time
   - Number of evaluations included
   - File size information
   - Which CSV files were used

2. **Select and View**: Choose a report to view within the dashboard
3. **Download**: Export HTML reports for external use

#### 4.4 Delete Reports
1. **Select a Report**: Choose the report you want to remove
2. **Delete Process**:
   - Click "🗑️ Delete Report"
   - First click shows confirmation warning
   - Second click permanently deletes the report

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

#### Step 6: Generate Reports
1. Create report including all tasks
2. Review visualizations and performance metrics
3. Download report for stakeholder presentation

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
Reports provide visual analysis including:
- Performance charts comparing models
- Cost analysis and budget tracking
- Response time distributions
- Success rate matrices
- Error categorization and analysis

The reports combine data from multiple CSV files to show patterns and comparisons across different evaluations.

---

## 🚨 Troubleshooting

### Common Issues and Solutions

**Issue**: Evaluation gets stuck in "queued" status
- **Solution**: Check logs for API errors or rate limiting
- **Prevention**: Use appropriate sleep intervals between calls

**Issue**: CSV upload fails
- **Solution**: Verify CSV format and column headers
- **Check**: Ensure file encoding is UTF-8

**Issue**: Models not available
- **Solution**: Verify AWS credentials and region settings
- **Check**: Ensure Bedrock model access is enabled

**Issue**: Reports not generating
- **Solution**: Verify completed evaluations exist
- **Check**: Ensure evaluation CSV files are present

### Debug Tools
- **Sidebar Debug Panel**: Session information and log access
- **Log Files**: Detailed execution logs in `logs/` directory
- **Status Files**: Check evaluation state in status JSON files
- **Manual Refresh**: Use refresh buttons if auto-updates fail

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

### Report Generation
- **Focused Reports**: Create targeted reports for specific analysis
- **Regular Cleanup**: Delete outdated reports to manage storage
- **Documentation**: Include evaluation context in report names

---

