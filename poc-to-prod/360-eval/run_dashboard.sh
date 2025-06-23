#!/bin/bash

# 360-Eval Dashboard Launcher
# This script launches the Streamlit dashboard with dark theme

echo "🚀 Starting 360-Eval Dashboard..."
echo "📊 Dashboard will be available at: http://localhost:8501"
echo ""

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Error: Streamlit is not installed or not in PATH"
    echo "💡 Please install streamlit: pip install streamlit"
    exit 1
fi

# Check if the dashboard file exists
if [ ! -f "src/streamlit_dashboard.py" ]; then
    echo "❌ Error: Dashboard file not found at src/streamlit_dashboard.py"
    echo "💡 Please ensure you're running this script from the 360-eval directory"
    exit 1
fi

# Launch the dashboard
echo "🔄 Launching dashboard..."
streamlit run src/streamlit_dashboard.py --theme.base dark

# Note: The script will continue running until the user stops it (Ctrl+C)