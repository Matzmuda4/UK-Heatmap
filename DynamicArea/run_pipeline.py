import streamlit as st
import subprocess
import os
import pandas as pd
from datetime import datetime
import time

def run_command(command):
    """Run a command and return its output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    )
    stdout, stderr = process.communicate()
    return stdout, stderr

def get_active_clinic_count(input_file='dentist_data_map_random_hours.csv'):
    """Get the number of active clinics from the input file."""
    try:
        # Look for the file in the parent directory
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(parent_dir, input_file)
        df = pd.read_csv(file_path)
        return len(df[df['active'] == 1])
    except Exception as e:
        st.error(f"Error reading clinic data: {e}")
        return 30  # Default fallback value

def main():
    st.set_page_config(layout="wide", page_title="UK Dental Regions Pipeline")
    st.title("UK Dental Regions Pipeline")

    # Get active clinic count
    total_active_clinics = get_active_clinic_count()

    # Create a placeholder for the pipeline status
    status_placeholder = st.empty()
    
    # Create columns for the controls
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pipeline Controls")
        
        # Clinic selection
        clinic_selection = st.radio(
            "Clinic Selection",
            ["All Active Clinics", "Sample Clinics"],
            help=f"Choose whether to use all active clinics ({total_active_clinics} available) or a sample"
        )
        
        if clinic_selection == "Sample Clinics":
            sample_size = st.slider(
                "Number of Clinics to Sample",
                min_value=10,
                max_value=min(total_active_clinics, 500),
                value=min(50, total_active_clinics),
                step=10,
                help=f"Number of clinics to randomly sample (max {total_active_clinics} available)"
            )
        else:
            sample_size = total_active_clinics

        # Merge distance control
        merge_distance = st.slider(
            "Merge Distance (km)",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            help="Distance threshold for merging nearby grids"
        )

    with col2:
        st.subheader("Pipeline Steps")
        st.write("""
        1. **Downsample Clinics**: Select a subset of clinics to analyze
        2. **Generate Grids**: Create service area grids for each clinic
        3. **Generate Regions**: Create regions from overlapping grids
        4. **Launch Visualization**: Open the interactive map
        """)

    # Add a run button
    if st.button("Run Pipeline", type="primary"):
        try:
            # Create output directory if it doesn't exist
            os.makedirs('output', exist_ok=True)

            # Step 1: Downsample clinics
            status_placeholder.info("Step 1/4: Downsampling clinics...")
            cmd = f"python downsample_clinics.py --n_clinics {sample_size}"
            stdout, stderr = run_command(cmd)
            if stderr:
                st.error(f"Error in downsample_clinics.py: {stderr}")
                return

            # Step 2: Generate grids
            status_placeholder.info("Step 2/4: Generating grids...")
            cmd = f"python generate_grids.py --merge_distance {merge_distance}"
            stdout, stderr = run_command(cmd)
            if stderr:
                st.error(f"Error in generate_grids.py: {stderr}")
                return

            # Step 3: Generate regions
            status_placeholder.info("Step 3/4: Generating regions...")
            cmd = "python generate_regions.py"
            stdout, stderr = run_command(cmd)
            if stderr:
                st.error(f"Error in generate_regions.py: {stderr}")
                return

            # Step 4: Launch visualization
            status_placeholder.success("Pipeline completed! Launching visualization...")
            
            # Run the visualization in a new process
            cmd = "streamlit run visualize_regions.py"
            process = subprocess.Popen(cmd, shell=True)
            
            # Give some time for the visualization to start
            time.sleep(2)
            
            st.success("""
            ✅ Pipeline completed successfully!
            
            The visualization should open in a new window. If it doesn't open automatically:
            1. Open a new terminal
            2. Navigate to this directory
            3. Run: `streamlit run visualize_regions.py`
            """)

        except Exception as e:
            st.error(f"Pipeline failed: {str(e)}")
            return

if __name__ == "__main__":
    main() 