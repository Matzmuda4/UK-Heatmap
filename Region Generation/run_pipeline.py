import streamlit as st
import subprocess
import os
import time

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

def main():
    st.title("UK Dental Regions Pipeline")
    
    # Sidebar controls
    st.sidebar.header("Pipeline Controls")
    n_clinics = st.sidebar.slider("Number of Clinics", min_value=10, max_value=100, value=30, step=5)
    grid_size = st.sidebar.slider("Grid Size (km)", min_value=10, max_value=50, value=20, step=5)
    
    if st.sidebar.button("Run Pipeline"):
        # Create a placeholder for progress updates
        progress_placeholder = st.empty()
        
        # Step 1: Downsample clinics
        progress_placeholder.write("Step 1: Downsampling clinics...")
        cmd = f"python downsample_clinics.py --n_clinics {n_clinics}"
        stdout, stderr = run_command(cmd)
        if stderr:
            st.error(f"Error in downsample_clinics.py: {stderr}")
            return
        progress_placeholder.write("✓ Clinics downsampled successfully")
        
        # Step 2: Generate grids
        progress_placeholder.write("Step 2: Generating grids...")
        cmd = f"python generate_grids.py --grid_size {grid_size}"
        stdout, stderr = run_command(cmd)
        if stderr:
            st.error(f"Error in generate_grids.py: {stderr}")
            return
        progress_placeholder.write("✓ Grids generated successfully")
        
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