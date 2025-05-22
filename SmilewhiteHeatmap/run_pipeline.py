import streamlit as st
import subprocess
import os
import pandas as pd

def get_active_clinic_count(input_file='dentist_data_map_random_hours.csv'):
    """Get the number of active clinics from the input file."""
    try:
        df = pd.read_csv(input_file)
        return len(df[df['active'] == 1])
    except Exception as e:
        st.error(f"Error reading clinic data: {e}")
        return 30  # Default fallback value

def run_command(command):
    """Run a command and return its output."""
    try:
        process = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return process.stdout, process.stderr
    except subprocess.CalledProcessError as e:
        return None, str(e)

def main():
    st.title("UK Dental Regions Pipeline")
    
    # Get active clinic count
    total_active_clinics = get_active_clinic_count()
    
    # Sidebar controls
    st.sidebar.header("Pipeline Configuration")
    
    # Clinic selection
    n_clinics = st.sidebar.slider(
        "Number of Clinics",
        min_value=10,
        max_value=total_active_clinics,
        value=min(50, total_active_clinics),
        step=10,
        help=f"Number of clinics to sample (max {total_active_clinics} active clinics)"
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
        min_value=0,
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
        stdout, stderr = run_command(f"python downsample_clinics.py --n_clinics {n_clinics}")
        if stderr:
            st.error(f"Error in downsample_clinics.py: {stderr}")
            return
        progress_placeholder.write("✓ Clinic data prepared successfully")
        
        # Step 2: Generate and merge grids
        progress_placeholder.write("Step 2: Generating and merging grids...")
        stdout, stderr = run_command(f"python generate_grids.py --grid_size {grid_size} --merge_distance {merge_distance}")
        if stderr:
            st.error(f"Error in generate_grids.py: {stderr}")
            return
        progress_placeholder.write("✓ Grids generated and merged successfully")
        
        # Step 3: Generate regions
        progress_placeholder.write("Step 3: Generating regions...")
        stdout, stderr = run_command("python generate_regions.py")
        if stderr:
            st.error(f"Error in generate_regions.py: {stderr}")
            return
        progress_placeholder.write("✓ Regions generated successfully")
        
        # Step 4: Launch visualization
        progress_placeholder.write("Step 4: Launching visualization...")
        st.success("Pipeline completed successfully! Launching visualization...")
        
        # Run the visualization in a new process
        subprocess.Popen("streamlit run visualize_regions.py", shell=True)
        
        # Clear the progress placeholder
        progress_placeholder.empty()
        
        st.info("Visualization launched in a new window. You can close this window once the visualization is open.")

if __name__ == "__main__":
    main() 