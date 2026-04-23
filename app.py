import os
import numpy as np
import pandas as pd
import segyio
import streamlit as st
import plotly.express as px

st.set_page_config(layout="wide", page_title="Geoscience Pipeline Dashboard", page_icon="🌍")

# --- CUSTOM CSS FOR MINIMALIST, FLEXIBLE AESTHETICS & CURSOR FIXES ---
st.markdown("""
<style>
    /* Clean Minimalist Background */
    .stApp {
        background-color: #fafafa;
        font-family: 'Inter', sans-serif;
    }
    
    /* Fix cursor pointers for interactive elements */
    button, div[role="button"], a, input[type="checkbox"], input[type="radio"], .stSelectbox, .stSlider {
        cursor: pointer !important;
    }
    
    /* Sleek typography */
    h1, h2, h3 {
        color: #1f2937;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    /* Card-like containers for flexible layout */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Integrated Geoscience Dashboard")
st.markdown("A minimalist, flexible environment to visualize Well Logs, Seismic Volumes, and Project Metadata interactively.")

# 3 Tabs now: Well Logs, Seismic, Metadata (for .ev and .asc)
tab_wells, tab_seismic, tab_metadata = st.tabs(["📊 Well Logs", "🌊 Seismic Data", "📁 Project Metadata & Events"])

# ==========================================
# TAB 1: WELL LOGS
# ==========================================
with tab_wells:
    well_data_dir = "outputs/data"
    well_fig_dir = "outputs/figures"
    
    if os.path.exists(well_data_dir):
        well_files = [f for f in os.listdir(well_data_dir) if f.endswith(".csv")]
    else:
        well_files = []
        
    if not well_files:
        st.warning("No processed well data found.")
    else:
        selected_well_file = st.selectbox("Select Well Dataset", well_files)
        well_name = selected_well_file.replace("_processed.csv", "")
        
        # Sub-tabs for the Crossplot vs the Multi-track Zig-Zag graph!
        wt1, wt2 = st.tabs(["Interactive Crossplot", "Multi-Track Well Log (High-Def)"])
        
        with wt1:
            df = pd.read_csv(os.path.join(well_data_dir, selected_well_file))
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            c1, c2, c3 = st.columns(3)
            x_ax = c1.selectbox("X-Axis", numeric_cols, index=numeric_cols.index("NPHI") if "NPHI" in numeric_cols else 0)
            y_ax = c2.selectbox("Y-Axis", numeric_cols, index=numeric_cols.index("RHOB") if "RHOB" in numeric_cols else 0)
            c_ax = c3.selectbox("Color Code", numeric_cols, index=numeric_cols.index("GR") if "GR" in numeric_cols else 0)
            
            fig = px.scatter(df, x=x_ax, y=y_ax, color=c_ax, color_continuous_scale='Turbo',
                             title=f"Interactive Crossplot: {y_ax} vs {x_ax}")
            fig.update_traces(marker=dict(size=6, line=dict(width=0.5, color='black')))
            fig.update_layout(height=650, margin=dict(l=40, r=40, t=60, b=40))
            if x_ax == "NPHI": fig.update_xaxes(autorange="reversed", range=[0.45, -0.15])
            if y_ax == "RHOB": fig.update_yaxes(autorange="reversed", range=[3.0, 1.9])
            st.plotly_chart(fig, use_container_width=True)
            
        with wt2:
            st.markdown(f"**Full Composite Log for {well_name}**")
            st.markdown("*This high-definition composite includes the specialized lithology shading, crossover fills, and vertical zig-zag curves computed by the pipeline.*")
            
            img_path = os.path.join(well_fig_dir, f"{well_name}_multitrack.png")
            if os.path.exists(img_path):
                # Flexible layout: allows the image to stretch to the container
                st.image(img_path, use_column_width=True)
            else:
                st.error("Could not find the multi-track image for this well.")

# ==========================================
# TAB 2: SEISMIC DATA
# ==========================================
def identify_seismic_data_parameters(filepath_in):
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
                inline, cdp, samples = seismic_data.shape if len(seismic_data.shape)==3 else (1, n_traces, len(twt))
                data_display = seismic_data.reshape(cdp, samples).T
            else:
                inline, cdp, samples = seismic_data.shape
                data_display = seismic_data.reshape(inline, cdp, samples).T
            return data_display, data_type, twt, inline_number, xline_number, diff_inline, diff_xline, sample_rate
    with segyio.open(filepath_in, ignore_geometry=True) as f:
        data_display = f.trace.raw[:].T
        return data_display, 'Post-stack 2D', f.samples, [1], np.arange(f.tracecount), 1, 1, 1

with tab_seismic:
    segy_files = []
    if os.path.exists("../extracted_zips"):
        for root, dirs, files in os.walk("../extracted_zips"):
            for file in files:
                if file.endswith((".sgy", ".segy")):
                    segy_files.append(os.path.join(root, file))
                    
    if not segy_files:
        st.info("No SEGY files currently available.")
    else:
        selected_segy = st.selectbox("Select SEGY File", segy_files)
        
        try:
            data_display, data_type, twt, inline_number, xline_number, diff_inline, diff_xline, sample_rate = identify_seismic_data_parameters(selected_segy)
            
            sc1, sc2 = st.columns([1, 2])
            sc1.metric("Data Type", data_type)
            sc2.metric("Dimensions", f"{data_display.shape}")
            
            if data_type == 'Post-stack 3D':
                slice_type = st.radio("Select Slice View", ["Inline", "Crossline", "Time-Slice"], horizontal=True)
                
                if slice_type == "Inline":
                    inline_val = st.slider("Inline Number", int(min(inline_number)), int(max(inline_number)), int(np.median(inline_number)), step=int(diff_inline))
                    idx = np.where(inline_number == inline_val)[0][0]
                    slice_data = data_display[:, :, idx]
                    x_range, y_range = [min(xline_number), max(xline_number)], [max(twt), min(twt)]
                    xlabel, ylabel = "Crossline No.", "Time (ms)"
                    
                elif slice_type == "Crossline":
                    xline_val = st.slider("Crossline Number", int(min(xline_number)), int(max(xline_number)), int(np.median(xline_number)), step=int(diff_xline))
                    idx = np.where(xline_number == xline_val)[0][0]
                    slice_data = data_display[:, idx, :]
                    x_range, y_range = [min(inline_number), max(inline_number)], [max(twt), min(twt)]
                    xlabel, ylabel = "Inline No.", "Time (ms)"
                    
                elif slice_type == "Time-Slice":
                    time_val = st.slider("TWT (ms)", int(min(twt)), int(max(twt)), int(np.median(twt)), step=int(sample_rate))
                    idx = np.where(twt >= time_val)[0][0]
                    slice_data = data_display[idx, :, :]
                    x_range, y_range = [min(inline_number), max(inline_number)], [max(xline_number), min(xline_number)]
                    xlabel, ylabel = "Inline No.", "Crossline No."
            else:
                slice_data = data_display
                x_range, y_range = [0, slice_data.shape[1]], [max(twt), min(twt)]
                xlabel, ylabel = "Trace No.", "Time (ms)"
            
            vmax = np.percentile(np.abs(slice_data), 95)
            fig_s = px.imshow(slice_data, zmin=-vmax, zmax=vmax, color_continuous_scale='RdBu_r', aspect='auto',
                              labels=dict(x=xlabel, y=ylabel, color="Amplitude"),
                              x=np.linspace(x_range[0], x_range[1], slice_data.shape[1]),
                              y=np.linspace(y_range[1], y_range[0], slice_data.shape[0]))
            
            fig_s.update_layout(height=750, margin=dict(l=40, r=40, t=40, b=40))
            if data_type != 'Post-stack 3D' or slice_type != "Time-Slice":
                fig_s.update_yaxes(autorange="reversed")
            
            st.plotly_chart(fig_s, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error reading SEGY geometry: {e}")

# ==========================================
# TAB 3: PROJECT METADATA (.ev & .asc)
# ==========================================
with tab_metadata:
    st.header("Ancillary Project Data (.ev, .asc, .pet)")
    
    # Gather EV and ASC files
    meta_files = []
    for root, dirs, files in os.walk("../"):
        if "venv" in root or ".git" in root: continue
        for file in files:
            if file.endswith((".ev", ".asc", ".pet")):
                meta_files.append(os.path.join(root, file))
                
    if not meta_files:
        st.info("No Event or Grid metadata files found.")
    else:
        selected_meta = st.selectbox("Select Metadata File to View", meta_files)
        
        ext = os.path.splitext(selected_meta)[1].lower()
        if ext == ".ev":
            st.subheader("Well Events & Perforations")
            try:
                # EV files are usually tab separated
                ev_df = pd.read_csv(selected_meta, sep='\\t+', engine='python', header=None)
                ev_df.columns = ["Well", "Date", "Event_Type", "Top_Depth", "Bottom_Depth"][:len(ev_df.columns)]
                st.dataframe(ev_df, use_container_width=True)
            except Exception as e:
                with open(selected_meta, 'r') as f:
                    st.text(f.read())
                    
        elif ext == ".asc":
            st.subheader("Seismic Master Grid Coordinates")
            st.markdown("*This defines the boundaries of the 3D seismic volume in physical UTM coordinates.*")
            with open(selected_meta, 'r') as f:
                st.code(f.read(), language='text')
                
        elif ext == ".pet":
            st.subheader("Petrel Project File")
            st.markdown("⚠️ **Proprietary Format Detected**")
            st.info("This is a binary Schlumberger Petrel project database. It cannot be visualized purely in Python without the Petrel Ocean API. The file is intact and ready for import into Petrel.")
