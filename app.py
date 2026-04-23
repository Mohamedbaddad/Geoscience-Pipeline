import os
import numpy as np
import pandas as pd
import segyio
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

st.set_page_config(layout="wide", page_title="High-Def Interactive Geoscience Visualizer")

# --- CUSTOM CSS FOR HIGH-DEF AESTHETICS ---
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    h1, h2, h3 {color: #2c3e50;}
</style>
""", unsafe_allow_html=True)

st.title("🛢️ High-Definition Interactive Geoscience Visualizer")
st.markdown("Combines the interactive slicing/cross-plotting logic from the referenced repositories with the **High-Definition, Industry-Standard Plotting Aesthetics** developed in our pipeline.")

tab1, tab2 = st.tabs(["Well Logs (LAS) Interactive Visualization", "Seismic Data (SEGY) Interactive Visualization"])

# ==========================================
# TAB 1: WELL LOGS
# ==========================================
with tab1:
    st.header("Interactive Well Log Cross-Plots")
    
    # Load available processed well data
    well_data_dir = "outputs/data"
    if os.path.exists(well_data_dir):
        well_files = [f for f in os.listdir(well_data_dir) if f.endswith(".csv")]
    else:
        well_files = []
        
    if not well_files:
        st.warning("No processed well data (.csv) found in outputs/data/. Please run the pipeline first.")
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            selected_well = st.selectbox("Select Well", well_files)
            df = pd.read_csv(os.path.join(well_data_dir, selected_well))
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            x_ax = st.selectbox("X-Axis", numeric_cols, index=numeric_cols.index("NPHI") if "NPHI" in numeric_cols else 0)
            y_ax = st.selectbox("Y-Axis", numeric_cols, index=numeric_cols.index("RHOB") if "RHOB" in numeric_cols else 0)
            c_ax = st.selectbox("Color Code", numeric_cols, index=numeric_cols.index("GR") if "GR" in numeric_cols else 0)
            
        with col2:
            st.subheader(f"High-Def Crossplot: {y_ax} vs {x_ax}")
            fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
            
            # Use high-def scatter with edgecolors
            scatter = ax.scatter(df[x_ax], df[y_ax], c=df[c_ax], cmap='nipy_spectral', 
                                 edgecolors='black', linewidths=0.2, alpha=0.8, s=40)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
            cbar.set_label(c_ax, fontsize=12, weight='bold')
            
            # High-def styling
            ax.set_xlabel(x_ax, fontsize=12, weight='bold')
            ax.set_ylabel(y_ax, fontsize=12, weight='bold')
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.set_facecolor('#f0f0f0')
            
            # Industry standards for NPHI and RHOB
            if x_ax == "NPHI":
                ax.set_xlim(0.45, -0.15)
            if y_ax == "RHOB":
                ax.set_ylim(3.0, 1.9)
                
            st.pyplot(fig, use_container_width=False)


# ==========================================
# TAB 2: SEISMIC DATA
# ==========================================
def identify_seismic_data_parameters(filepath_in):
    """Adapted from AB-Blue interactive notebook to parse 3D SEGY geometry."""
    with segyio.open(filepath_in, ignore_geometry=True) as f:
        data_format = f.format
    inline_xline = [[189,193], [9,13], [9,21], [5,21]]
    state = False
    
    for k, byte_loc in enumerate(inline_xline):
        try:
            with segyio.open(filepath_in, iline=byte_loc[0], xline=byte_loc[1], ignore_geometry=False) as f:
                seismic_data = segyio.tools.cube(f)
                n_traces = f.tracecount    
                tr = f.attributes(segyio.TraceField.TraceNumber)[-1]
                if not isinstance(tr, int):
                    tr = f.attributes(segyio.TraceField.TraceNumber)[-2] + 1
                tr = int(tr[0])
                twt = f.samples
                sample_rate = segyio.tools.dt(f) / 1000
                
                Inline_3D, Crossline_3D = [], []
                for i in range(n_traces):
                    Inline_3D.append(f.attributes(segyio.TraceField.INLINE_3D)[i])
                    Crossline_3D.append(f.attributes(segyio.TraceField.CROSSLINE_3D)[i])
                inline3d = np.unique(Inline_3D)
                crossline3d = np.unique(Crossline_3D)
                state = True
        except:
            pass
            
        if state:
            data_type = 'Post-stack 3D' if len(seismic_data.shape) == 3 and seismic_data.shape[0] != 1 else 'Post-stack 2D'
            inline_number = inline3d
            xline_number = crossline3d
            diff_inline = np.diff(inline_number)[0] if len(inline_number)>1 else 1
            diff_xline = np.diff(xline_number)[0] if len(xline_number)>1 else 1
            
            if data_type == 'Post-stack 2D':
                # Simplified for 2D
                inline, cdp, samples = seismic_data.shape if len(seismic_data.shape)==3 else (1, n_traces, len(twt))
                data_display = seismic_data.reshape(cdp, samples).T
            else:
                inline, cdp, samples = seismic_data.shape
                data_display = seismic_data.reshape(inline, cdp, samples).T
                
            return data_display, data_type, twt, inline_number, xline_number, diff_inline, diff_xline, sample_rate
            
    # Fallback to pure 2D raw loading if geometry fails
    with segyio.open(filepath_in, ignore_geometry=True) as f:
        data_display = f.trace.raw[:].T
        return data_display, 'Post-stack 2D', f.samples, [1], np.arange(f.tracecount), 1, 1, 1

with tab2:
    st.header("Interactive Seismic Visualization")
    
    # Gather all unzipped SEGY files
    segy_files = []
    if os.path.exists("../extracted_zips"):
        for root, dirs, files in os.walk("../extracted_zips"):
            for file in files:
                if file.endswith((".sgy", ".segy")):
                    segy_files.append(os.path.join(root, file))
                    
    if not segy_files:
        st.warning("No SEGY files found. Please unzip your segy files first.")
    else:
        selected_segy = st.selectbox("Select SEGY File", segy_files)
        
        try:
            data_display, data_type, twt, inline_number, xline_number, diff_inline, diff_xline, sample_rate = identify_seismic_data_parameters(selected_segy)
            
            st.info(f"Detected Data Type: **{data_type}** | Dimensions: {data_display.shape}")
            
            if data_type == 'Post-stack 3D':
                slice_type = st.radio("Select Slice Type", ["Inline", "Crossline", "Time-Slice"], horizontal=True)
                
                if slice_type == "Inline":
                    inline_val = st.slider("Select Inline", int(min(inline_number)), int(max(inline_number)), int(np.median(inline_number)), step=int(diff_inline))
                    idx = np.where(inline_number == inline_val)[0][0]
                    slice_data = data_display[:, :, idx]
                    extent = [min(xline_number), max(xline_number), max(twt), min(twt)]
                    xlabel, ylabel = "Crossline No.", "Time (ms)"
                    
                elif slice_type == "Crossline":
                    xline_val = st.slider("Select Crossline", int(min(xline_number)), int(max(xline_number)), int(np.median(xline_number)), step=int(diff_xline))
                    idx = np.where(xline_number == xline_val)[0][0]
                    slice_data = data_display[:, idx, :]
                    extent = [min(inline_number), max(inline_number), max(twt), min(twt)]
                    xlabel, ylabel = "Inline No.", "Time (ms)"
                    
                elif slice_type == "Time-Slice":
                    time_val = st.slider("Select TWT (ms)", int(min(twt)), int(max(twt)), int(np.median(twt)), step=int(sample_rate))
                    idx = np.where(twt >= time_val)[0][0]
                    slice_data = data_display[idx, :, :]
                    extent = [min(inline_number), max(inline_number), max(xline_number), min(xline_number)]
                    xlabel, ylabel = "Inline No.", "Crossline No."
            else:
                st.write("Displaying 2D Seismic Section")
                slice_data = data_display
                extent = [0, slice_data.shape[1], max(twt), min(twt)]
                xlabel, ylabel = "Trace No.", "Time (ms)"
            
            # --- HIGH DEF PLOTTING ---
            fig_s, ax_s = plt.subplots(figsize=(14, 8), dpi=150)
            
            # 95th percentile clipping for high contrast
            vmax = np.percentile(np.abs(slice_data), 95)
            
            # High-Def interpolation and colormap
            im = ax_s.imshow(slice_data, cmap='seismic', aspect='auto', interpolation='bicubic',
                             vmin=-vmax, vmax=vmax, extent=extent)
            
            cbar = plt.colorbar(im, ax=ax_s, pad=0.01)
            cbar.set_label('Amplitude', rotation=270, labelpad=15, weight='bold')
            
            ax_s.set_xlabel(xlabel, fontsize=12, weight='bold')
            ax_s.set_ylabel(ylabel, fontsize=12, weight='bold')
            ax_s.set_title(f"High-Definition Seismic Visualization ({os.path.basename(selected_segy)})", fontsize=14, weight='bold')
            
            st.pyplot(fig_s, use_container_width=False)
            
        except Exception as e:
            st.error(f"Error reading SEGY geometry: {e}. Some files require specialized byte mapping.")
