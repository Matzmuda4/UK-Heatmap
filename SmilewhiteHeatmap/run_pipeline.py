import streamlit as st
import subprocess
import os
import time
from datetime import datetime

def run_command(command):
    """Run a shell command and return its output."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr

def main():
    st.set_page_config(layout="wide", page_title="Dental Region Pipeline")
    st.title("Dental Region Generation Pipeline")
    
    # Sidebar controls
    st.sidebar.header("Pipeline Parameters")
    n_clinics = st.sidebar.slider("Number of Clinics", 10, 100, 30)
    grid_size = st.sidebar.slider("Grid Size (km)", 10, 50, 20)
    
    if st.sidebar.button("Run Pipeline"):
        # Create progress container
        progress_container = st.empty()
        status_container = st.empty()
        
        # Step 1: Downsample clinics
        progress_container.progress(0)
        status_container.text("Step 1/4: Downsampling clinics...")
        code, out, err = run_command(f"python downsample_clinics.py --n_clinics {n_clinics}")
        if code != 0:
            st.error(f"Error in downsample_clinics.py:\n{err}")
            return
        progress_container.progress(25)
        
        # Step 2: Generate grids
        status_container.text("Step 2/4: Generating clinic grids...")
        code, out, err = run_command(f"python generate_grids.py --grid_size {grid_size}")
        if code != 0:
            st.error(f"Error in generate_grids.py:\n{err}")
            return
        progress_container.progress(50)
        
        # Step 3: Generate regions
        status_container.text("Step 3/4: Processing regions...")
        code, out, err = run_command("python generate_regions.py")
        if code != 0:
            st.error(f"Error in generate_regions.py:\n{err}")
            return
        progress_container.progress(75)
        
        # Step 4: Process customer data
        status_container.text("Step 4/4: Processing customer data...")
        code, out, err = run_command("python process_customers.py")
        if code != 0:
            st.error(f"Error in process_customers.py:\n{err}")
            return
        progress_container.progress(100)
        
        # Pipeline complete
        status_container.text("Pipeline complete! Launching visualization...")
        time.sleep(2)
        
        # Launch visualization in a new process
        subprocess.Popen(["streamlit", "run", "visualize_regions.py"])
        
        st.success("Pipeline completed successfully! The visualization should open in a new window.")

if __name__ == "__main__":
    main() 