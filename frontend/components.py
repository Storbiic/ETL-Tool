"""
Reusable UI components for the Streamlit frontend
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Any
import datetime


def add_log(message: str):
    """Add a timestamped log entry"""
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")


def display_logs():
    """Display activity logs with export functionality"""
    from api_client import api_client
    from datetime import datetime

    with st.sidebar:
        st.subheader("📋 Activity Logs")

        # Display session logs
        if st.session_state.get('logs', []):
            # Show log count
            total_logs = len(st.session_state.logs)
            st.caption(f"📊 Showing last 15 of {total_logs} session logs")

            # Show last 15 logs in reverse order (newest first)
            for log in reversed(st.session_state.logs[-15:]):
                # Color code different log types
                if "ERROR" in log or "❌" in log:
                    st.error(log, icon="❌")
                elif "SUCCESS" in log or "✅" in log:
                    st.success(log, icon="✅")
                elif "WARNING" in log or "⚠️" in log:
                    st.warning(log, icon="⚠️")
                else:
                    st.info(log, icon="ℹ️")
        else:
            st.info("No activity yet...", icon="📝")

        # View all session logs
        if st.session_state.get('logs', []) and len(st.session_state.logs) > 15:
            with st.expander(f"📜 View All {len(st.session_state.logs)} Session Logs"):
                for log in reversed(st.session_state.logs):
                    st.text(log)

        # Log Export Section
        st.markdown("---")
        st.subheader("📥 Comprehensive Log Export")
        st.caption("Export detailed backend logs including LOCKUP process details")

        # Get log summary from backend
        log_summary = api_client.get_log_summary()

        if log_summary.get("session_logs_count", 0) > 0:
            # Show log statistics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Backend Logs", log_summary.get("session_logs_count", 0),
                         help="Application-level logs from backend")
            with col2:
                st.metric("Operation Logs", log_summary.get("detailed_logs_count", 0),
                         help="Detailed operation logs (LOCKUP, processing, etc.)")

            # Export format selection
            export_format = st.selectbox(
                "Export format:",
                ["text", "csv", "json"],
                help="Choose format for comprehensive log export",
                key="log_export_format"
            )

            # Export button
            if st.button("📥 Export All Logs", type="primary", key="export_logs_btn"):
                with st.spinner("Exporting comprehensive logs..."):
                    log_content = api_client.export_logs(export_format)
                    if log_content:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"etl_comprehensive_logs_{timestamp}.{export_format}"

                        st.download_button(
                            label=f"📥 Download {filename}",
                            data=log_content,
                            file_name=filename,
                            mime=f"text/{export_format}" if export_format != "json" else "application/json",
                            key="download_logs_btn"
                        )
                        add_log(f"Comprehensive logs exported as {export_format}")

            # Clear backend logs button
            if st.button("🗑️ Clear Backend Logs", type="secondary", key="clear_backend_logs"):
                clear_result = api_client.clear_logs()
                if clear_result.get("success"):
                    add_log("Backend logs cleared")
                    st.success("Backend logs cleared successfully")
                    st.rerun()
        else:
            st.info("No backend logs available for export")

        st.markdown("---")

        # Clear session logs button
        if st.button("🗑️ Clear Session Logs", key="clear_session_logs"):
            st.session_state.logs = []
            add_log("Session logs cleared")
            st.rerun()


def display_kpi_metrics(kpi_counts: Dict[str, int], total_records: int):
    """Display KPI metrics in columns"""
    st.subheader("📊 Activation Status KPIs")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Records", total_records)
    with col2:
        st.metric("Status '0'", kpi_counts.get('0', 0))
    with col3:
        st.metric("Status 'D'", kpi_counts.get('D', 0))
    with col4:
        st.metric("Status 'X'", kpi_counts.get('X', 0))
    with col5:
        st.metric("Not Found", kpi_counts.get('NOT_FOUND', 0))


def create_status_chart(kpi_counts: Dict[str, int]):
    """Create a bar chart for activation status distribution"""
    if not kpi_counts:
        return None

    # Prepare data for chart
    labels = list(kpi_counts.keys())
    values = list(kpi_counts.values())

    # Create bar chart
    fig = px.bar(
        x=labels,
        y=values,
        title="Activation Status Distribution",
        color=labels,
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig.update_layout(
        showlegend=False,
        height=400,
        font=dict(size=12),
        xaxis_title="Activation Status",
        yaxis_title="Count"
    )

    # Add value labels on bars
    fig.update_traces(texttemplate='%{y}', textposition='outside')

    return fig


def fix_dataframe_types(df: pd.DataFrame) -> pd.DataFrame:
    """Fix DataFrame data types to prevent PyArrow serialization errors"""
    df = df.copy()

    for col in df.columns:
        # Convert all object columns to string to avoid mixed type issues
        if df[col].dtype == 'object':
            # Handle mixed types by converting everything to string
            df[col] = df[col].astype(str)
            # Replace 'nan' strings with empty strings for cleaner display
            df[col] = df[col].replace(['nan', 'None', 'NaN'], '')

        # Handle numeric columns that might have mixed types
        elif df[col].dtype in ['int64', 'float64']:
            # Ensure numeric columns are properly typed
            try:
                # Try to convert to numeric, coercing errors to NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Fill NaN with 0 for display purposes
                df[col] = df[col].fillna(0)
            except:
                # If conversion fails, convert to string
                df[col] = df[col].astype(str)

    return df


def display_dataframe_with_search(df: pd.DataFrame, key: str):
    """Display dataframe with search functionality"""
    if df.empty:
        st.warning("No data to display")
        return

    # Fix data types for Arrow compatibility
    df = fix_dataframe_types(df)

    # Search functionality
    search_term = st.text_input(
        "🔍 Search in data:",
        key=f"search_{key}",
        help="Search across all columns"
    )

    # Filter dataframe based on search
    if search_term:
        # Create a mask for rows containing the search term in any column
        mask = df.astype(str).apply(
            lambda x: x.str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        filtered_df = df[mask]

        if filtered_df.empty:
            st.warning(f"No results found for '{search_term}'")
            return
        else:
            st.info(f"Found {len(filtered_df)} results for '{search_term}'")
    else:
        filtered_df = df

    # Display total count
    st.write(f"**Total records:** {len(filtered_df)}")

    # Display the dataframe
    st.dataframe(filtered_df, use_container_width=True, height=400)


def create_distribution_chart(distribution: Dict[str, int], title: str = "Status Distribution"):
    """Create a pie chart for status distribution"""
    if not distribution or sum(distribution.values()) == 0:
        return None

    # Filter out zero values for cleaner chart
    filtered_dist = {k: v for k, v in distribution.items() if v > 0}

    if not filtered_dist:
        return None

    # Create pie chart
    fig = px.pie(
        values=list(filtered_dist.values()),
        names=list(filtered_dist.keys()),
        title=title,
        color_discrete_map={
            'X': '#ff6b6b',      # Red for X (active)
            'D': '#4ecdc4',      # Teal for D (discontinued)
            '0': '#45b7d1',      # Blue for 0 (inactive)
            'OTHER': '#96ceb4'   # Green for other
        }
    )

    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )

    fig.update_layout(
        showlegend=True,
        height=400,
        font=dict(size=12)
    )

    return fig


def create_comparison_chart(original_dist: Dict[str, int], new_dist: Dict[str, int]):
    """Create a comparison bar chart showing before vs after"""
    if not original_dist or not new_dist:
        return None

    # Prepare data for comparison
    categories = list(set(original_dist.keys()) | set(new_dist.keys()))
    original_values = [original_dist.get(cat, 0) for cat in categories]
    new_values = [new_dist.get(cat, 0) for cat in categories]

    fig = go.Figure(data=[
        go.Bar(name='Before Processing', x=categories, y=original_values,
               marker_color='lightblue', text=original_values, textposition='auto'),
        go.Bar(name='After Processing', x=categories, y=new_values,
               marker_color='darkblue', text=new_values, textposition='auto')
    ])

    fig.update_layout(
        title='Distribution Comparison: Before vs After Processing',
        xaxis_title='Status Categories',
        yaxis_title='Number of Items',
        barmode='group',
        height=400,
        showlegend=True
    )

    return fig


def create_processing_flow_chart(processing_stats: Dict[str, Any]):
    """Create a flow chart showing processing statistics"""
    if not processing_stats:
        return None

    # Create a sankey diagram showing the flow
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=["Total Items", "In Target", "Not in Target", "Status X", "Status Other", "Updated to D", "Kept as X"],
            color=["blue", "green", "orange", "red", "gray", "teal", "red"]
        ),
        link=dict(
            source=[0, 0, 2, 2, 3, 3],  # indices correspond to labels
            target=[1, 2, 3, 4, 5, 6],
            value=[
                processing_stats.get("total_checked", 0) - processing_stats.get("not_in_target_count", 0),  # In target
                processing_stats.get("not_in_target_count", 0),  # Not in target
                processing_stats.get("updated_count", 0),  # Status X (to be updated)
                processing_stats.get("not_in_target_count", 0) - processing_stats.get("updated_count", 0),  # Other status
                processing_stats.get("updated_count", 0),  # Updated to D
                0  # Kept as X (calculated)
            ]
        )
    )])

    fig.update_layout(
        title_text="Pre-existing Items Processing Flow",
        font_size=10,
        height=400
    )

    return fig


def create_progress_bar(current_step: int, total_steps: int, step_names: List[str]):
    """Create a progress bar showing current step"""
    progress = current_step / total_steps

    st.progress(progress)

    # Show step indicators
    cols = st.columns(total_steps)
    for i, (col, step_name) in enumerate(zip(cols, step_names)):
        with col:
            if i < current_step:
                st.success(f"✅ {step_name}")
            elif i == current_step:
                st.info(f"🔄 {step_name}")
            else:
                st.write(f"⏳ {step_name}")


def display_file_info(filename: str, sheet_names: List[str]):
    """Display file information in an info box"""
    st.info(f"""
    **File:** {filename}  
    **Sheets:** {len(sheet_names)}  
    **Sheet Names:** {', '.join(sheet_names)}
    """)


def create_download_section(download_url: str, filename: str, data_preview: List[Dict]):
    """Create download section with preview"""
    st.subheader("📥 Download Results")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**File:** {filename}")
        st.write(f"**Records:** {len(data_preview)}")
    
    with col2:
        st.download_button(
            label="📥 Download CSV",
            data="",  # This would be populated with actual data
            file_name=filename,
            mime="text/csv",
            help="Download the complete processed dataset"
        )


def display_error_message(error: str, details: str = None):
    """Display error message with optional details"""
    st.error(f"❌ {error}")
    if details:
        with st.expander("Error Details"):
            st.code(details)


def display_success_message(message: str):
    """Display success message"""
    st.success(f"✅ {message}")


def create_sidebar_navigation():
    """Create sidebar navigation menu"""
    with st.sidebar:
        st.title("🔧 ETL Automation Tool")
        
        # Navigation menu
        selected = st.selectbox(
            "Navigation",
            ["📁 File Upload", "🧹 Data Cleaning", "🔍 Data Lookup", "📊 Results"],
            key="navigation"
        )
        
        return selected.split(" ", 1)[1]  # Return just the text part
