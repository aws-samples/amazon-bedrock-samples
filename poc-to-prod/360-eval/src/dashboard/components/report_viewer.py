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
        
        # Add Generate Report section at the top
        st.subheader("🔄 Generate New Report")
        
        # Report generation options
        report_scope = st.radio(
            "Report Scope:",
            ["All Evaluations", "Selected Evaluations"],
            index=0,
            help="Choose whether to generate a report from all completed evaluations or only selected ones"
        )
        
        selected_eval_names = []
        if report_scope == "Selected Evaluations":
            # Get completed evaluations (don't require existing results since we're generating a new report)
            completed_with_results = [
                e for e in st.session_state.evaluations 
                if e.get("status") == "completed"
            ]
            
            if completed_with_results:
                selected_eval_names = st.multiselect(
                    "Select evaluations for report:",
                    options=[e["name"] for e in completed_with_results],
                    help="Select which completed evaluations to include in the report"
                )
                
                if selected_eval_names:
                    st.info(f"Report will include {len(selected_eval_names)} evaluation(s): {', '.join(selected_eval_names)}")
                else:
                    st.warning("Please select at least one evaluation for the report.")
            else:
                st.warning("No completed evaluations with results found.")
        else:
            st.info("Report will include all completed evaluations.")
        
        # Generate report button
        can_generate = (report_scope == "All Evaluations" or 
                      (report_scope == "Selected Evaluations" and selected_eval_names))
        
        if st.button("🔄 Generate Report", key="gen_comprehensive_report", type="primary", disabled=not can_generate):
            if report_scope == "Selected Evaluations":
                self._generate_comprehensive_report(selected_evaluations=selected_eval_names)
            else:
                self._generate_comprehensive_report()
        
        st.divider()

        # No notifications or auto-refresh - just a manual refresh button
        st.button("Refresh Report List", on_click=sync_evaluations_from_files)

        # Available Reports section
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
            # Add delete button for the selected report
            col1, col2 = st.columns([3, 1])
            with col2:
                # Show confirmation warning if delete was clicked once
                if st.session_state.get("confirm_delete", False):
                    st.warning("⚠️ This will permanently delete the report and all related files. Click 'Delete Report' again to confirm.")
                
                if st.button("🗑️ Delete Report", type="secondary", key="delete_report_btn"):
                    if st.session_state.get("confirm_delete", False):
                        # Second click - actually delete
                        self._delete_report(selected_report)
                        st.session_state.confirm_delete = False
                        return  # Exit early to prevent displaying the deleted report
                    else:
                        # First click - set confirmation flag
                        st.session_state.confirm_delete = True
                        # No st.rerun() needed - Streamlit handles this automatically
            
            # Only display report if it still exists
            if os.path.exists(selected_report["report_path"]):
                self._display_report(selected_report)
            else:
                st.info("Report has been deleted. Please select another report or refresh the page.")
    
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
    
    def _generate_comprehensive_report(self, selected_evaluations=None):
        """Generate a comprehensive report from evaluation results in the directory.
        
        Args:
            selected_evaluations: Optional list of evaluation names to filter by
        """
        try:
            # Import the visualize_results module
            from ...visualize_results import create_html_report
            from ..utils.constants import PROJECT_ROOT, DEFAULT_OUTPUT_DIR
            
            # Use the default output directory to look for all results
            output_dir = DEFAULT_OUTPUT_DIR
            if not os.path.isabs(output_dir):
                output_dir = os.path.join(PROJECT_ROOT, output_dir)
            
            # Check if output directory exists and has any CSV files
            if not os.path.exists(output_dir):
                st.error(f"Output directory not found: {output_dir}")
                return
                
            # Look for CSV result files
            csv_files = list(Path(output_dir).glob("*.csv"))
            if not csv_files:
                st.warning(f"No CSV result files found. Please run some evaluations first.")
                return
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create status indicator with appropriate message
            if selected_evaluations:
                spinner_msg = f"Generating report from {len(selected_evaluations)} selected evaluation(s)... This may take a moment."
            else:
                spinner_msg = f"Generating report from {len(csv_files)} result files... This may take a moment."
                
            with st.spinner(spinner_msg):
                # Call the report generator with the output directory and optional evaluation filter
                report_path = create_html_report(output_dir, timestamp, selected_evaluations)
                
                # Find which CSV files were used to generate this comprehensive report
                import glob
                all_csv_files = glob.glob(str(Path(output_dir) / "invocations_*.csv"))
                
                # Filter CSV files if specific evaluations were selected
                if selected_evaluations:
                    csv_files_used = []
                    for csv_file in all_csv_files:
                        csv_filename = os.path.basename(csv_file)
                        # Check if any selected evaluation name is in the filename
                        if any(eval_name in csv_filename for eval_name in selected_evaluations):
                            csv_files_used.append(csv_file)
                else:
                    csv_files_used = all_csv_files
                
                csv_filenames = [os.path.basename(f) for f in csv_files_used]
                
                # Create a comprehensive report status entry (use timestamp as ID)
                evals_status = {
                    "status": "completed",
                    "results": str(report_path),
                    "evaluations_used_to_generate": csv_filenames,
                    "report_generated_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().timestamp(),
                    "progress": 100
                }
                
                # Save comprehensive report status
                evals_status_file = Path(output_dir) / f"evaluation_report_{timestamp}_status.json"
                try:
                    with open(evals_status_file, 'w') as f:
                        json.dump(evals_status, f)
                except Exception as e:
                    print(f"Error saving comprehensive report status: {str(e)}")

                # Create appropriate success message based on scope
                if selected_evaluations:
                    scope_description = f"data from {len(selected_evaluations)} selected evaluation(s): {', '.join(selected_evaluations)}"
                else:
                    scope_description = f"data from {len(csv_files_used)} evaluation result files"
                
                st.success(f"✅ **Report generated successfully!**  \n"
                          f"📁 **File:** {os.path.basename(str(report_path))}  \n"
                          f"📊 **Scope:** {scope_description}  \n"
                          f"🔄 **Refresh:** The new report will appear in the Available Reports section below.")
                
        except Exception as e:
            st.error(f"Error generating comprehensive report: {str(e)}")
            print(f"Error generating comprehensive report: {str(e)}")
    
    def _delete_report(self, report_info):
        """Delete a report and its status file (but keep the CSV evaluation results).
        
        Args:
            report_info: Dictionary containing report information
        """
        try:
            report_path = report_info["report_path"]
            status_file_path = report_info["status_file"]
            
            files_deleted = []
            errors = []
            
            # Delete the HTML report file
            if os.path.exists(report_path):
                try:
                    os.remove(report_path)
                    files_deleted.append(f"Report: {os.path.basename(report_path)}")
                except Exception as e:
                    errors.append(f"Failed to delete report file: {str(e)}")
            
            # Delete the status file
            if os.path.exists(status_file_path):
                try:
                    os.remove(status_file_path)
                    files_deleted.append(f"Status file: {os.path.basename(status_file_path)}")
                except Exception as e:
                    errors.append(f"Failed to delete status file: {str(e)}")
            
            # Remove the evaluation from session state if it exists
            # (Only remove the reference to this specific report, not the entire evaluation)
            for eval_config in st.session_state.evaluations:
                if eval_config.get("results") == report_path:
                    try:
                        # Clear the results reference but keep the evaluation
                        eval_config["results"] = None
                        files_deleted.append(f"Report reference cleared for: {eval_config.get('name', 'Unknown')}")
                    except Exception as e:
                        errors.append(f"Failed to clear report reference: {str(e)}")
            
            # Show results
            if files_deleted:
                st.success(f"✅ **Successfully deleted:**\n" + "\n".join([f"• {item}" for item in files_deleted]))
                st.info("📋 **Note:** CSV evaluation result files were preserved and can be used to generate new reports.")
            
            if errors:
                st.error(f"❌ **Errors occurred:**\n" + "\n".join([f"• {error}" for error in errors]))
            
            if not files_deleted and not errors:
                st.warning("No files were found to delete.")
                
        except Exception as e:
            st.error(f"Error deleting report: {str(e)}")