import streamlit as st
import sys
import logging
import os

# Add the project root to path to allow importing dashboard modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Configure logging
os.makedirs(os.path.join(project_root, 'logs'), exist_ok=True)
# Use in-memory logging instead of file-based logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('streamlit_dashboard')
logger.info("Starting Streamlit dashboard")

# Import dashboard components
from src.dashboard.components.evaluation_setup import EvaluationSetupComponent
from src.dashboard.components.model_configuration import ModelConfigurationComponent
from src.dashboard.components.evaluation_monitor import EvaluationMonitorComponent
from src.dashboard.components.results_viewer import ResultsViewerComponent
from src.dashboard.components.report_viewer import ReportViewerComponent
from src.dashboard.utils.state_management import initialize_session_state
from src.dashboard.utils.constants import APP_TITLE, SIDEBAR_INFO, PROJECT_ROOT

# Initialize session state at module level to ensure it's available before component rendering
if "evaluations" not in st.session_state:
    initialize_session_state()
    
# Debug session state
print("Session state initialized at module level:")
print(f"Evaluations: {len(st.session_state.evaluations)}")
print(f"Active evaluations: {len(st.session_state.active_evaluations)}")
print(f"Completed evaluations: {len(st.session_state.completed_evaluations)}")

def main():
    """Main Streamlit dashboard application."""
    try:
        # Set page title and layout with custom icon
        logger.info("Initializing Streamlit dashboard")
        
        icon_path = os.path.join(PROJECT_ROOT, "assets", "scale_icon.png")
        
        st.set_page_config(
            page_title=APP_TITLE,
            page_icon=icon_path,
            layout="wide"
        )
        
        # Initialize session state again to ensure all variables are set
        initialize_session_state()
        logger.info("Session state initialized")
        
        # Display log file path for debugging
        log_dir = os.path.join(PROJECT_ROOT, 'logs')
        
        # Add log information to sidebar
        with st.sidebar:
            with st.expander("📋 Debug Information"):
                st.info(f"Log Directory: {log_dir}")
                st.info(f"Project Root: {PROJECT_ROOT}")
                # Add button to show latest logs
                if st.button("Show Latest Logs"):
                    log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                    if log_files:
                        latest_log = max(log_files, key=lambda x: os.path.getmtime(os.path.join(log_dir, x)))
                        with open(os.path.join(log_dir, latest_log), 'r') as f:
                            log_content = f.read()
                        st.text_area("Latest Log Entries", log_content[-5000:], height=300)
                    else:
                        st.warning("No log files found")
        
        # Header with logo and title
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.image(icon_path, width=150)
        
        with col2:
            st.title(APP_TITLE)
            st.markdown("Create, manage, and visualize LLM benchmark evaluations using LLM-as-a-JURY methodology")
        
        # Sidebar with info
        with st.sidebar:
            st.markdown(SIDEBAR_INFO)
            st.divider()
            
            # Navigation tabs in sidebar - always include Reports tab
            tab_names = ["Setup", "Monitor", "Evaluations", "Reports"]
            
            # Check if we need to navigate to Setup tab
            if "navigate_to_setup" in st.session_state and st.session_state.navigate_to_setup:
                active_tab = st.radio("Navigation", tab_names, index=0, key="nav_radio")
                del st.session_state.navigate_to_setup  # Clear the flag after using it
            else:
                active_tab = st.radio("Navigation", tab_names, key="nav_radio")
            logger.info(f"Selected tab: {active_tab}")
        
        # Main area - show different components based on active tab
        if active_tab == "Setup":
            # Use tabs for the three setup sections
            setup_tab1, setup_tab2, setup_tab3 = st.tabs(["Evaluation Setup", "Model Configuration", "Advanced Configuration"])
            
            with setup_tab1:
                logger.info("Rendering Evaluation Setup component")
                EvaluationSetupComponent().render()
            
            with setup_tab2:
                logger.info("Rendering Model Configuration component")
                ModelConfigurationComponent().render()
            
            with setup_tab3:
                logger.info("Rendering Advanced Configuration component")
                EvaluationSetupComponent().render_advanced_config()
                
        elif active_tab == "Monitor":
            logger.info("Rendering Evaluation Monitor component")
            EvaluationMonitorComponent().render()
            
        elif active_tab == "Evaluations":
            logger.info("Rendering Results Viewer component")
            ResultsViewerComponent().render()
            
        elif active_tab == "Reports":
            logger.info("Rendering Report Viewer component")
            ReportViewerComponent().render()
            
    except Exception as e:
        logger.exception(f"Unhandled exception in main dashboard: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        st.info(f"Check logs for details at: {log_dir}")

if __name__ == "__main__":
    main()