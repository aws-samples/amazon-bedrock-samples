"""Report viewer component for displaying HTML reports within the Streamlit app."""

import streamlit as st
import streamlit.components.v1
import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from ..utils.benchmark_runner import sync_evaluations_from_files

class ReportViewerComponent:
    """Component for viewing HTML reports within the app."""
    
    def render(self):
        """Render the report viewer component."""
        # Sync evaluation statuses from files
        sync_evaluations_from_files()
        
        st.subheader("📊 Available Reports")
        
        # Get all available reports from status files
        available_reports = self._get_available_reports()
        
        if not available_reports:
            st.info("No reports available. Generate some reports first to see them here.")
            return
        
        # Create a table showing available reports
        self._display_reports_table(available_reports)
        
        # Allow user to select and view a report
        selected_report = st.selectbox(
            "Select a report to view:",
            options=available_reports,
            format_func=lambda x: f"{x['report_name']} ({x['creation_time_formatted']})"
        )
        
        if selected_report:
            self._display_report(selected_report)
    
    def _get_available_reports(self):
        """Get all available reports from status files (now in logs directory)."""
        from ..utils.constants import DEFAULT_OUTPUT_DIR
        status_dir = Path(DEFAULT_OUTPUT_DIR)
        available_reports = []
        
        # Find all status files (both evaluation and comprehensive reports) in logs directory
        status_files = list(status_dir.glob("*_status.json"))
        
        for status_file in status_files:
            try:
                with open(status_file, 'r') as f:
                    status_data = json.load(f)
                
                # Check if this status file has a report
                if "results" in status_data and status_data["results"]:
                    report_path = status_data["results"]
                    
                    # Check if the report file still exists
                    if os.path.exists(report_path):
                        # Extract report information
                        report_info = {
                            "status_file": str(status_file),
                            "report_path": report_path,
                            "report_name": os.path.basename(report_path),
                            "creation_time": status_data.get("report_generated_at", "Unknown"),
                            "evaluations_used": status_data.get("evaluations_used_to_generate", []),
                            # "report_type": status_data.get("report_type", "evaluation-specific"),
                            "file_size": self._get_file_size(report_path)
                        }
                        
                        # Format creation time for display
                        if report_info["creation_time"] != "Unknown":
                            try:
                                dt = datetime.fromisoformat(report_info["creation_time"])
                                report_info["creation_time_formatted"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except:
                                report_info["creation_time_formatted"] = report_info["creation_time"]
                        else:
                            report_info["creation_time_formatted"] = "Unknown"
                        
                        available_reports.append(report_info)
                        
            except Exception as e:
                # Skip files that can't be read
                continue
        
        # Sort by creation time (newest first)
        available_reports.sort(key=lambda x: x["creation_time"], reverse=True)
        return available_reports
    
    def _get_file_size(self, file_path):
        """Get file size in human readable format."""
        try:
            size_bytes = os.path.getsize(file_path)
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        except:
            return "Unknown"
    
    def _display_reports_table(self, reports):
        """Display a table of available reports."""
        if not reports:
            return
        
        # Prepare data for the table
        table_data = []
        for report in reports:
            evaluations_count = len(report["evaluations_used"])
            evaluations_preview = ", ".join(report["evaluations_used"][:3])
            if len(report["evaluations_used"]) > 3:
                evaluations_preview += f" (and {len(report['evaluations_used']) - 3} more)"
            
            table_data.append({
                "Report Name": report["report_name"],
                "Created": report["creation_time_formatted"],
                # "Type": report["report_type"].replace("-", " ").title(),
                "Evaluations Used": f"{evaluations_count} evaluation(s)",
                "File Size": report["file_size"],
                "CSV Files": evaluations_preview if evaluations_preview else "None"
            })
        
        # Display the table
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show detailed information about evaluations used
        with st.expander("📋 Evaluations Used by Report"):
            for i, report in enumerate(reports):
                st.write(f"**{report['report_name']}:**")
                if report["evaluations_used"]:
                    for eval_file in report["evaluations_used"]:
                        st.write(f"  • {eval_file}")
                else:
                    st.write("  • No evaluation files found")
                st.write("")
    
    def _display_report(self, report_info):
        """Display the HTML report for the selected report."""
        report_path = report_info["report_path"]
        
        if not os.path.exists(report_path):
            st.error("Report file not found or path is invalid.")
            return
        
        # Display report info
        st.write("#### Report Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Name:** {report_info['report_name']}")
            # st.write(f"**Type:** {report_info['report_type'].replace('-', ' ').title()}")
        with col2:
            st.write(f"**Created:** {report_info['creation_time_formatted']}")
            st.write(f"**Size:** {report_info['file_size']}")
        with col3:
            st.write(f"**Evaluations:** {len(report_info['evaluations_used'])}")

        
        st.divider()
        
        # Display the HTML report
        st.write("#### Report Content")
        
        try:
            # Read the HTML file
            with open(report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Display the HTML content using st.components.v1.html
            st.components.v1.html(html_content, height=1200, width=1100, scrolling=True)
            
        except Exception as e:
            st.error(f"Error loading report: {str(e)}")
            
        # Add option to download the report
        st.divider()
        st.write("#### Download Report")
        
        try:
            with open(report_path, 'rb') as f:
                report_data = f.read()
            
            st.download_button(
                label="📥 Download HTML Report",
                data=report_data,
                file_name=os.path.basename(report_path),
                mime="text/html"
            )
        except Exception as e:
            st.error(f"Error preparing download: {str(e)}")