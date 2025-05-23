import streamlit as st
import subprocess
import os
import time
import pandas as pd

def run_command(command):
    """Run a command and return its output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode()

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
    st.title("UK Dental Regions Pipeline")
    
    # Get active clinic count
    total_active_clinics = get_active_clinic_count()
    
    # Sidebar controls
    st.sidebar.header("Pipeline Controls")
    
    # Clinic selection
    clinic_selection = st.sidebar.radio(
        "Clinic Selection",
        ["All Active Clinics", "Sample Clinics"],
        help=f"Choose whether to use all active clinics ({total_active_clinics} available) or a sample"
    )
    
    if clinic_selection == "Sample Clinics":
        n_clinics = st.sidebar.slider(
            "Number of Clinics",
            min_value=10,
            max_value=min(total_active_clinics, 500),  # Cap at either total active or 500
            value=min(30, total_active_clinics),  # Default to 30 or max available
            step=10,
            help=f"Number of clinics to randomly sample (max {total_active_clinics} available)"
        )
    
    # Grid parameters
    grid_size = st.sidebar.slider(
        "Grid Size (km)",
        min_value=10,
        max_value=50,
        value=20,
        step=5,
        help="Size of each clinic's service area grid"
    )
    
    merge_distance = st.sidebar.slider(
        "Merge Distance (km)",
        min_value=1,
        max_value=20,
        value=5,
        step=1,
        help="Distance threshold for merging nearby grids"
    )
    
    if st.sidebar.button("Run Pipeline"):
        # Create a placeholder for progress updates
        progress_placeholder = st.empty()
        
        # Step 1: Select/Downsample clinics
        progress_placeholder.write("Step 1: Preparing clinic data...")
        if clinic_selection == "Sample Clinics":
            cmd = f"python downsample_clinics.py --n_clinics {n_clinics}"
        else:
            cmd = "python downsample_clinics.py"  # No n_clinics means use all active clinics
        stdout, stderr = run_command(cmd)
        if stderr:
            st.error(f"Error in downsample_clinics.py: {stderr}")
            return
        progress_placeholder.write("✓ Clinic data prepared successfully")
        
        # Step 2: Generate and merge grids
        progress_placeholder.write("Step 2: Generating and merging grids...")
        cmd = f"python generate_grids.py --grid_size {grid_size} --merge_distance {merge_distance}"
        stdout, stderr = run_command(cmd)
        if stderr:
            st.error(f"Error in generate_grids.py: {stderr}")
            return
        progress_placeholder.write("✓ Grids generated and merged successfully")
        
        # Step 3: Generate regions
        progress_placeholder.write("Step 3: Generating regions...")
        cmd = "python generate_regions.py"
        stdout, stderr = run_command(cmd)
        if stderr:
            st.error(f"Error in generate_regions.py: {stderr}")
            return
        progress_placeholder.write("✓ Regions generated successfully")
        
        # Step 4: Launch visualization
        progress_placeholder.write("Step 4: Launching visualization...")
        st.success("Pipeline completed successfully! Launching visualization...")
        
        # Run the visualization in a new process
        cmd = "streamlit run visualize_regions.py"
        subprocess.Popen(cmd, shell=True)
        
        # Give some time for the visualization to start
        time.sleep(2)
        
        # Clear the progress placeholder
        progress_placeholder.empty()
        
        st.info("Visualization launched in a new window. You can close this window once the visualization is open.")

if __name__ == "__main__":
    main() 