import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
import json
import segyio
from pathlib import Path

# Page Config
st.set_page_config(layout="wide", page_title="Geoscience Pipeline Dashboard", page_icon="🌍")

# Custom CSS for Premium Look
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
        cursor: pointer !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e9ecef;
        border-bottom: 2px solid #007bff;
    }
    /* Force cursor to pointer for all buttons and interactive elements */
    button, [role="button"], [role="tab"], .stSelectbox, .stSlider {
        cursor: pointer !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Integrated Geoscience Dashboard")

tab_wells, tab_seismic, tab_metadata = st.tabs([
    "📊 Well Logs & Petrophysics", 
    "🌊 Seismic Data", 
    "📁 Project Metadata & Events"
])

# ==========================================
# HELPERS
# ==========================================
def get_curve(df, aliases):
    for a in aliases:
        if a in df.columns: return a
    return None

@st.cache_data
def load_seismic_cube(file_path):
    try:
        with segyio.open(file_path, ignore_geometry=True) as f:
            data = segyio.tools.cube(f)
            samples = f.samples
            # Attempt to get geometry
            try:
                with segyio.open(file_path) as f_geom:
                    inlines = f_geom.ilines
                    xlines = f_geom.xlines
                    return data, samples, inlines, xlines
            except:
                return data, samples, np.arange(data.shape[0]), np.arange(data.shape[1])
    except Exception as e:
        return None, str(e), None, None

# ==========================================
# TAB 1: WELL LOGS & PETROPHYSICS
# ==========================================
with tab_wells:
    well_data_dir = "outputs/data"
    well_fig_dir = "outputs/figures"
    
    well_files = [f for f in os.listdir(well_data_dir) if f.endswith(".csv")] if os.path.exists(well_data_dir) else []
        
    if not well_files:
        st.warning("No processed well data found. Please run the pipeline first.")
    else:
        selected_well_file = st.selectbox("Select Well Dataset", well_files)
        well_name = selected_well_file.replace("_processed.csv", "")
        df = pd.read_csv(os.path.join(well_data_dir, selected_well_file))
        
        # Resolve aliases
        c_gr = get_curve(df, ["GR", "GRAFM", "GR1BFM", "SGR"])
        c_rt = get_curve(df, ["RT", "RPTHM", "RACLM", "RESD"])
        c_rhob = get_curve(df, ["RHOB", "BDCM", "DEN", "ZDEN", "BDCFM"])
        c_nphi = get_curve(df, ["NPHI", "NPLM", "NEU", "TNPH", "NPLFM"])
        c_dt = get_curve(df, ["DT", "DTPM", "DTC", "DTP4M"])
        c_vsh = get_curve(df, ["VSH"])
        c_phit = get_curve(df, ["PHIT_D", "PHIT"])
        c_ai = get_curve(df, ["AI"])
        c_rc = get_curve(df, ["RC"])
        
        wt1, wt2, wt3, wt4, wt5, wt6 = st.tabs([
            "Multi-Track Log (Interactive)", 
            "RHOB vs NPHI Crossplot", 
            "PHIT vs RT Crossplot",
            "AI vs RC Plot",
            "Custom Interactive Crossplot",
            "Static High-Def Composite"
        ])
        
        # 1. Interactive Multi-Track Log
        with wt1:
            st.subheader(f"Interactive Multi-Track Log: {well_name}")
            tracks = []
            if c_gr: tracks.append(("Gamma Ray", c_gr))
            if c_rt: tracks.append(("Resistivity", c_rt))
            if c_rhob: tracks.append(("Density/Neutron", c_rhob))
            if c_dt: tracks.append(("Sonic", c_dt))
            if c_vsh: tracks.append(("Computed", c_vsh))
            
            if not tracks:
                st.warning("No standard curves found to plot.")
            else:
                fig_log = make_subplots(rows=1, cols=len(tracks), shared_yaxes=True, horizontal_spacing=0.02, subplot_titles=[t[0] for t in tracks])
                for i, (name, curve) in enumerate(tracks, 1):
                    if curve == c_gr:
                        fig_log.add_trace(go.Scatter(x=df[c_gr], y=df["DEPTH"], line=dict(color='green', width=1), name=c_gr), row=1, col=i)
                        fig_log.update_xaxes(range=[0, 150], row=1, col=i)
                    elif curve == c_rt:
                        fig_log.add_trace(go.Scatter(x=df[c_rt], y=df["DEPTH"], line=dict(color='black', width=1), name=c_rt), row=1, col=i)
                        fig_log.update_xaxes(type="log", range=[-1, 3], row=1, col=i)
                    elif curve == c_rhob:
                        fig_log.add_trace(go.Scatter(x=df[c_rhob], y=df["DEPTH"], line=dict(color='red', width=1), name=c_rhob), row=1, col=i)
                        fig_log.update_xaxes(range=[1.65, 2.65], row=1, col=i)
                    elif curve == c_dt:
                        fig_log.add_trace(go.Scatter(x=df[c_dt], y=df["DEPTH"], line=dict(color='purple', width=1), name=c_dt), row=1, col=i)
                        fig_log.update_xaxes(range=[140, 40], row=1, col=i)
                    elif curve == c_vsh:
                        fig_log.add_trace(go.Scatter(x=df[c_vsh], y=df["DEPTH"], line=dict(color='saddlebrown', width=1), fill='tozerox', name=c_vsh), row=1, col=i)
                        if c_phit:
                            fig_log.add_trace(go.Scatter(x=df[c_phit], y=df["DEPTH"], line=dict(color='teal', width=1), name=c_phit), row=1, col=i)
                        fig_log.update_xaxes(range=[0, 1], row=1, col=i)
                
                fig_log.update_yaxes(autorange="reversed", title_text="Depth")
                fig_log.update_layout(height=800, plot_bgcolor='#ffffff', hovermode='y unified')
                st.plotly_chart(fig_log, use_container_width=True)

        # 2. RHOB vs NPHI
        with wt2:
            st.subheader("Density-Neutron Crossplot (Lithology & Fluid ID)")
            if c_rhob and c_nphi:
                color_col = c_gr if c_gr else "DEPTH"
                fig = px.scatter(df, x=c_nphi, y=c_rhob, color=color_col, color_continuous_scale="RdYlGn_r")
                fig.update_layout(height=600)
                fig.update_xaxes(range=[-0.05, 0.60])
                fig.update_yaxes(autorange="reversed", range=[3.0, 1.8])
                minerals = {"Quartz": (0.0, 2.65), "Calcite": (0.0, 2.71), "Dolomite": (0.02, 2.87)}
                for name, (nphi, rhob) in minerals.items():
                    fig.add_annotation(x=nphi, y=rhob, text=name, showarrow=True, arrowhead=2)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("RHOB and NPHI curves required.")

        # 3. PHIT vs RT Crossplot
        with wt3:
            st.subheader("Porosity vs Resistivity (Reservoir Quality)")
            if c_phit and c_rt:
                fig = px.scatter(df, x=c_phit, y=c_rt, color="DEPTH", color_continuous_scale="Viridis", log_y=True)
                fig.update_layout(height=600)
                fig.add_vrect(x0=0.10, x1=max(df[c_phit].max(), 0.15), fillcolor="green", opacity=0.1, layer="below", line_width=0)
                fig.add_hrect(y0=10, y1=max(df[c_rt].max(), 100), fillcolor="green", opacity=0.1, layer="below", line_width=0)
                fig.add_annotation(x=df[c_phit].max(), y=np.log10(max(df[c_rt].max(), 10)), text="Potential Pay Zone", showarrow=False, font=dict(color="green", size=14))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("PHIT_D and RT curves required.")

        # 4. AI vs RC Plot
        with wt4:
            st.subheader("Acoustic Impedance & Reflection Coefficient")
            if c_ai and c_rc:
                fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("Acoustic Impedance", "Reflection Coefficient"))
                fig.add_trace(go.Scatter(x=df[c_ai], y=df["DEPTH"], line=dict(color='blue')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df[c_rc], y=df["DEPTH"], line=dict(color='black'), fill='tozerox'), row=1, col=2)
                fig.update_xaxes(range=[-0.3, 0.3], row=1, col=2)
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=800, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("AI and RC curves required.")

        # 5. CUSTOM INTERACTIVE CROSSPLOT
        with wt5:
            st.subheader("Interactive Custom Crossplot (AB-Blue Style)")
            cols = list(df.columns)
            c1, c2, c3 = st.columns(3)
            with c1: x_ax = st.selectbox("X-Axis", cols, index=cols.index(c_nphi) if c_nphi in cols else 0)
            with c2: y_ax = st.selectbox("Y-Axis", cols, index=cols.index(c_rhob) if c_rhob in cols else 0)
            with c3: z_ax = st.selectbox("Color-Code", cols, index=cols.index(c_gr) if c_gr in cols else 0)
            
            fig = px.scatter(df, x=x_ax, y=y_ax, color=z_ax, color_continuous_scale="jet")
            fig.update_layout(height=600, title=f"{x_ax} vs {y_ax} coded by {z_ax}")
            st.plotly_chart(fig, use_container_width=True)

        # 6. Static High-Def Composite
        with wt6:
            st.markdown(f"**Full Composite Log for {well_name}**")
            img_path = os.path.join(well_fig_dir, f"{well_name}_multitrack.png")
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.error(f"Image not found at {img_path}. Please run the pipeline.")

# ==========================================
# TAB 2: SEISMIC DATA
# ==========================================
with tab_seismic:
    manifest_path = "outputs/data/pipeline_manifest.json"
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        
        segy_files = manifest.get("segy", [])
        if not segy_files:
            st.warning("No SEGY files found.")
        else:
            selected_segy = st.selectbox("Select Seismic Cube", segy_files)
            cube, samples, inlines, xlines = load_seismic_cube(selected_segy)
            
            if cube is None:
                st.error(f"Failed to load seismic data: {samples}")
            else:
                st.subheader("Interactive 3D Seismic Slicer")
                s1, s2 = st.columns([1, 4])
                with s1:
                    direction = st.radio("Slicing Direction", ["Inline", "Crossline", "Time-Slice"])
                    if direction == "Inline":
                        idx = st.slider("Inline Index", 0, cube.shape[0]-1, cube.shape[0]//2)
                        slice_data = cube[idx, :, :].T
                        xlabel, ylabel = "Crossline", "Time (ms)"
                    elif direction == "Crossline":
                        idx = st.slider("Crossline Index", 0, cube.shape[1]-1, cube.shape[1]//2)
                        slice_data = cube[:, idx, :].T
                        xlabel, ylabel = "Inline", "Time (ms)"
                    else:
                        idx = st.slider("Time Sample", 0, cube.shape[2]-1, cube.shape[2]//2)
                        slice_data = cube[:, :, idx].T
                        xlabel, ylabel = "Inline", "Crossline"
                    
                    cmap = st.selectbox("Colormap", ["RdBu", "seismic", "jet", "gray", "Viridis"])
                    contrast = st.slider("Contrast Level", 0.1, 5.0, 1.0)
                
                with s2:
                    v_max = np.percentile(np.abs(slice_data), 98) / contrast
                    fig = px.imshow(slice_data, color_continuous_scale=cmap, aspect='auto',
                                   zmin=-v_max, zmax=v_max if cmap in ["RdBu", "seismic"] else None,
                                   labels=dict(x=xlabel, y=ylabel, color="Amplitude"))
                    fig.update_layout(height=700, margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 3: PROJECT METADATA & EVENTS
# ==========================================
with tab_metadata:
    st.header("Ancillary Project Data (.ev, .asc, .pet)")
    meta_files = []
    for root, dirs, files in os.walk("../"):
        if "venv" in root or ".git" in root or "geoscience_pipeline" in root: continue
        for file in files:
            if file.endswith((".ev", ".asc", ".pet")):
                meta_files.append(os.path.join(root, file))
    
    if not meta_files:
        st.info("No Event or Grid metadata files found.")
    else:
        selected_meta = st.selectbox("Select Metadata File", meta_files)
        ext = os.path.splitext(selected_meta)[1].lower()
        if ext == ".ev":
            st.subheader("Well Events & Perforations")
            try:
                ev_df = pd.read_csv(selected_meta, sep='\\t+', engine='python', header=None)
                st.dataframe(ev_df, use_container_width=True)
            except:
                with open(selected_meta, 'r') as f: st.text(f.read())
        elif ext == ".asc":
            st.subheader("Seismic Master Grid Coordinates")
            with open(selected_meta, 'r') as f: st.code(f.read(), language='text')
        elif ext == ".pet":
            st.subheader("Petrel Project File")
            st.info("This is a proprietary Schlumberger Petrel binary database.")
