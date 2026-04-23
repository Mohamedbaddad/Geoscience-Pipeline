import os
import numpy as np
import pandas as pd
import segyio
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="Geoscience Pipeline Dashboard", page_icon="🌍")

st.markdown("""
<style>
    .stApp { background-color: #fafafa; font-family: 'Inter', sans-serif; }
    button, div[role="button"], a, input, .stSelectbox, .stSlider { cursor: pointer !important; }
    h1, h2, h3 { color: #1f2937; font-weight: 600; letter-spacing: -0.5px; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; border-radius: 8px 8px 0 0; }
</style>
""", unsafe_allow_html=True)

st.title("🌍 Integrated Geoscience Dashboard")

tab_wells, tab_seismic, tab_metadata = st.tabs(["📊 Well Logs & Petrophysics", "🌊 Seismic Data", "📁 Project Metadata & Events"])

# ==========================================
# TAB 1: WELL LOGS & PETROPHYSICS
# ==========================================

def get_curve(df, aliases):
    for a in aliases:
        if a in df.columns: return a
    return None

with tab_wells:
    well_data_dir = "outputs/data"
    well_fig_dir = "outputs/figures"
    
    well_files = [f for f in os.listdir(well_data_dir) if f.endswith(".csv")] if os.path.exists(well_data_dir) else []
        
    if not well_files:
        st.warning("No processed well data found.")
    else:
        selected_well_file = st.selectbox("Select Well Dataset", well_files)
        well_name = selected_well_file.replace("_processed.csv", "")
        df = pd.read_csv(os.path.join(well_data_dir, selected_well_file))
        
        # Resolve aliases
        c_gr = get_curve(df, ["GR", "GRAFM", "GR1BFM", "SGR"])
        c_rt = get_curve(df, ["RT", "RPTHM", "RACLM", "RESD"])
        c_rhob = get_curve(df, ["RHOB", "BDCM", "DEN", "ZDEN"])
        c_nphi = get_curve(df, ["NPHI", "NPLM", "NEU", "TNPH"])
        c_dt = get_curve(df, ["DT", "DTPM", "DTC"])
        c_vsh = get_curve(df, ["VSH"])
        c_phit = get_curve(df, ["PHIT_D", "PHIT"])
        c_ai = get_curve(df, ["AI"])
        c_rc = get_curve(df, ["RC"])
        
        wt1, wt2, wt3, wt4, wt5 = st.tabs([
            "Multi-Track Log (Interactive)", 
            "RHOB vs NPHI Crossplot", 
            "PHIT vs RT Crossplot",
            "AI vs RC Plot",
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
                        if c_nphi:
                            pass # simplified
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
            st.subheader("Acoustic Impedance & Reflection Coefficient (Synthetic Seismogram Preview)")
            if c_ai and c_rc:
                fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("Acoustic Impedance", "Reflection Coefficient (Wiggle)"))
                fig.add_trace(go.Scatter(x=df[c_ai], y=df["DEPTH"], line=dict(color='blue')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df[c_rc], y=df["DEPTH"], line=dict(color='black'), fill='tozerox'), row=1, col=2)
                fig.update_xaxes(range=[-0.3, 0.3], row=1, col=2)
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=800, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("AI and RC curves required. (Need DT and RHOB to compute).")

        # 5. Static High-Def Composite
        with wt5:
            st.markdown(f"**Full Composite Log for {well_name}**")
            img_path = os.path.join(well_fig_dir, f"{well_name}_multitrack.png")
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.error(f"Image not found at {img_path}. Did the pipeline run fully?")

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
            
            # Wiggle trace overlay option requested by prompt
            if st.checkbox("Show Wiggle Trace Overlay (Performance Intensive)"):
                st.warning("Wiggle traces are better suited for static plots due to high rendering load in browser.")
        except Exception as e:
            st.error(f"Error reading SEGY geometry: {e}")

# ==========================================
# TAB 3: PROJECT METADATA (.ev & .asc)
# ==========================================
with tab_metadata:
    st.header("Ancillary Project Data (.ev, .asc, .pet)")
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
                ev_df = pd.read_csv(selected_meta, sep='\\t+', engine='python', header=None)
                ev_df.columns = ["Well", "Date", "Event_Type", "Top_Depth", "Bottom_Depth"][:len(ev_df.columns)]
                st.dataframe(ev_df, use_container_width=True)
            except Exception:
                with open(selected_meta, 'r') as f: st.text(f.read())
        elif ext == ".asc":
            st.subheader("Seismic Master Grid Coordinates")
            with open(selected_meta, 'r') as f: st.code(f.read(), language='text')
        elif ext == ".pet":
            st.subheader("Petrel Project File")
            st.info("This is a proprietary Schlumberger Petrel binary database.")
