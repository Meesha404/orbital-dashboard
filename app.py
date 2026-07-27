"""
Orbital Infrastructure Observability & Capacity Planning Dashboard
Portfolio project — Data Center Strategy / Edge Computing
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
import time
import random

from data.tle_fetcher import fetch_starlink_tles, parse_tles
from data.orbital_math import compute_passes, get_current_positions
from data.cost_model import INFRASTRUCTURE_OPTIONS, compute_cost_latency_tradeoff
from data.workload_scheduler import generate_job_queue, schedule_jobs, summarize_schedule


def render_dark_table(df):
    """Render a dataframe as a dark-themed HTML table."""
    headers = "".join(
        f'<th style="text-align:left; padding:8px 12px; color:#3d7a5a; '
        f'letter-spacing:0.08em; border-bottom:1px solid #0d3320; '
        f'font-family:Space Mono,monospace; font-size:11px;">{c}</th>'
        for c in df.columns
    )
    rows = ""
    for _, row in df.iterrows():
        cells = "".join(
            f'<td style="padding:7px 12px; color:#7ecfa0; '
            f'font-family:Space Mono,monospace; font-size:11px; '
            f'border-bottom:1px solid #0a1f14;">{v}</td>'
            for v in row
        )
        rows += f"<tr>{cells}</tr>"
    html = (
        "<div style='overflow-x:auto; margin-bottom:16px;'>"
        "<table style='width:100%; border-collapse:collapse; background:#040f1a; "
        "border:1px solid #0d3320; border-radius:8px;'>"
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


st.set_page_config(
    page_title="Orbital Observability Platform",
    page_icon="🛰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Rajdhani:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #020b12 !important;
    color: #c8e6d4 !important;
}
[data-testid="stSidebar"] {
    background-color: #030f19 !important;
    border-right: 1px solid #0d3320 !important;
}
[data-testid="stSidebar"] * { color: #7ecfa0 !important; }

html, body, [class*="css"], p, div, span, label {
    font-family: 'Rajdhani', sans-serif !important;
    letter-spacing: 0.02em;
}
h1, h2, h3, h4 {
    font-family: 'Space Mono', monospace !important;
    color: #00ff88 !important;
    letter-spacing: 0.05em;
}

[data-testid="stTabs"] button {
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
    color: #3d7a5a !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #00ff88 !important;
    border-bottom: 2px solid #00ff88 !important;
}

[data-testid="stMetric"] {
    background: #040f1a !important;
    border: 1px solid #0d3320 !important;
    border-radius: 8px !important;
    padding: 16px !important;
}
[data-testid="stMetric"] label {
    font-family: 'Space Mono', monospace !important;
    font-size: 10px !important;
    color: #3d7a5a !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    color: #00ff88 !important;
    font-size: 28px !important;
}

[data-testid="stButton"] button {
    background: transparent !important;
    border: 1px solid #00ff88 !important;
    color: #00ff88 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    border-radius: 4px !important;
}
[data-testid="stButton"] button:hover {
    background: rgba(0,255,136,0.08) !important;
}

[data-testid="stSelectbox"] > div > div {
    background: #040f1a !important;
    border: 1px solid #0d3320 !important;
    color: #7ecfa0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
}

hr { border-color: #0d3320 !important; }

[data-testid="stAlert"] {
    background: #041a0d !important;
    border: 1px solid rgba(0,255,136,0.25) !important;
    color: #7ecfa0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
}

::-webkit-scrollbar { width: 4px; background: #020b12; }
::-webkit-scrollbar-thumb { background: #0d3320; border-radius: 2px; }

.orbital-header {
    border-bottom: 1px solid #0d3320;
    padding: 8px 0 16px 0;
    margin-bottom: 8px;
}
.orbital-title {
    font-family: 'Space Mono', monospace;
    font-size: 22px;
    font-weight: 700;
    color: #00ff88;
    letter-spacing: 0.1em;
    margin: 0;
}
.orbital-sub {
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    color: #3d7a5a;
    letter-spacing: 0.08em;
    margin: 4px 0 0 0;
}
.live-badge {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: #00ff88;
    border: 1px solid #00ff88;
    padding: 2px 10px;
    border-radius: 20px;
    letter-spacing: 0.1em;
    animation: pulse-border 2s infinite;
}
@keyframes pulse-border {
    0%, 100% { box-shadow: 0 0 4px rgba(0,255,136,0.4); }
    50% { box-shadow: 0 0 12px rgba(0,255,136,0.7); }
}
.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    color: #00ff88;
    letter-spacing: 0.08em;
    border-left: 3px solid #00ff88;
    padding-left: 10px;
    margin: 16px 0 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='font-family:Space Mono,monospace; font-size:13px; color:#00ff88;
                letter-spacing:0.1em; padding:8px 0 16px 0;
                border-bottom:1px solid #0d3320; margin-bottom:16px;'>
        ⬡ CONTROL PANEL
    </div>
    """, unsafe_allow_html=True)

    LOCATIONS = {
        "Seoul, South Korea":   (37.5665,  126.9780),
        "San Francisco, USA":   (37.7749, -122.4194),
        "London, UK":           (51.5074,   -0.1278),
        "Tokyo, Japan":         (35.6762,  139.6503),
        "Sydney, Australia":    (-33.8688, 151.2093),
        "São Paulo, Brazil":    (-23.5505,  -46.6333),
        "Nairobi, Kenya":       (-1.2921,   36.8219),
        "Mumbai, India":        (19.0760,   72.8777),
    }

    selected_location = st.selectbox("GROUND STATION", list(LOCATIONS.keys()))
    lat, lon = LOCATIONS[selected_location]

    st.markdown(f"""
    <div style='font-family:Space Mono,monospace; font-size:11px; color:#3d7a5a;
                padding:8px; background:#040f1a; border:1px solid #0d3320;
                border-radius:6px; margin:8px 0 16px 0;'>
        LAT &nbsp;<span style='color:#00ff88'>{lat:.4f}°</span>
        &nbsp;&nbsp;LON &nbsp;<span style='color:#00ff88'>{lon:.4f}°</span>
    </div>
    """, unsafe_allow_html=True)

    min_elevation = st.slider("MIN ELEVATION (°)", 5, 45, 15,
                              help="Satellites below this angle are blocked by terrain")
    horizon_hours = st.slider("PASS WINDOW (hrs)", 1, 24, 6)
    max_sats = st.slider("MAX SATELLITES", 50, 500, 200)

    st.markdown("<div style='border-top:1px solid #0d3320; margin:16px 0;'></div>",
                unsafe_allow_html=True)
    auto_refresh = st.toggle("AUTO-REFRESH (30s)", value=False)
    if st.button("⟳  REFRESH TLE DATA"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<div style='border-top:1px solid #0d3320; margin:16px 0;'></div>",
                unsafe_allow_html=True)
    st.markdown("""
    <div style='font-family:Space Mono,monospace; font-size:13px; color:#00ff88;
                letter-spacing:0.1em; padding:0 0 8px 0;'>
        ⬡ WORKLOAD QUEUE
    </div>
    """, unsafe_allow_html=True)
    n_jobs = st.slider("JOBS IN QUEUE", 5, 100, 30)
    job_seed = st.number_input("SEED", min_value=0, max_value=9999, value=42, step=1,
                                help="Same seed = same job mix, for reproducible demos")
    if st.button("⟳  REGENERATE JOB QUEUE"):
        st.session_state['job_seed'] = int(job_seed) + random.randint(1, 9999)
    effective_seed = st.session_state.get('job_seed', job_seed)

    st.markdown("""
    <div style='font-family:Space Mono,monospace; font-size:9px; color:#1d4a2a;
                margin-top:32px; letter-spacing:0.06em; line-height:1.8;'>
        DATA: CELESTRAK TLE API<br>
        PROP: SKYFIELD SGP4<br>
        UPD: EVERY 2 HOURS
    </div>
    """, unsafe_allow_html=True)

# ── Data Loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=7200)
def load_satellite_data(n_sats: int):
    raw_tles = fetch_starlink_tles()
    satellites = parse_tles(raw_tles)
    return satellites[:n_sats]

with st.spinner("INITIALIZING ORBITAL TELEMETRY..."):
    try:
        satellites = load_satellite_data(max_sats)
    except Exception as e:
        st.warning(f"⚠ CELESTRAK RATE LIMIT — data refreshes every 2 hours.\n\n{e}\n\nClick REFRESH TLE DATA in sidebar to retry.")
        st.stop()

now_utc = datetime.now(timezone.utc)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='orbital-header'>
    <div style='display:flex; align-items:center; justify-content:space-between;'>
        <div>
            <div class='orbital-title'>⬡ ORBITAL OBSERVABILITY PLATFORM</div>
            <div class='orbital-sub'>STARLINK CONSTELLATION · {selected_location.upper()} · SGP4 PROPAGATION</div>
        </div>
        <div style='text-align:right;'>
            <div class='live-badge'>● LIVE</div>
            <div style='font-family:Space Mono,monospace; font-size:11px;
                        color:#3d7a5a; margin-top:6px;'>
                {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Compute ───────────────────────────────────────────────────────────────────
with st.spinner("PROPAGATING ORBITAL ELEMENTS..."):
    positions_df = get_current_positions(satellites, now_utc)

with st.spinner(f"COMPUTING PASS WINDOWS OVER {selected_location.upper()}..."):
    passes_df = compute_passes(
        satellites=satellites,
        observer_lat=lat,
        observer_lon=lon,
        start_time=now_utc,
        hours=horizon_hours,
        min_elevation=min_elevation
    )

# ── Key Metrics ───────────────────────────────────────────────────────────────
overhead_count = len(positions_df[
    (abs(positions_df['lat'] - lat) < 15) &
    (abs(positions_df['lon'] - lon) < 20)
])
pass_count = len(passes_df)
next_pass = passes_df.iloc[0] if not passes_df.empty else None
next_pass_str = next_pass['start_time'].strftime('%H:%M UTC') if next_pass is not None else "NONE"
max_el = f"{passes_df['max_elevation'].max():.0f}°" if not passes_df.empty else "—"

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("TRACKED SATS", f"{len(satellites):,}")
m2.metric("OVERHEAD NOW", overhead_count, help="Within ~1500km footprint")
m3.metric(f"PASSES / {horizon_hours}H", pass_count)
m4.metric("NEXT PASS", next_pass_str)
m5.metric("BEST ELEVATION", max_el)

st.markdown("<div style='border-top:1px solid #0d3320; margin:16px 0 8px 0;'></div>",
            unsafe_allow_html=True)

# ── Plotly dark theme base ────────────────────────────────────────────────────
DARK = dict(
    paper_bgcolor='#020b12',
    plot_bgcolor='#040f1a',
    font=dict(family='Space Mono, monospace', color='#7ecfa0', size=11),
    xaxis=dict(gridcolor='#0d3320', zerolinecolor='#0d3320',
               tickfont=dict(color='#3d7a5a')),
    yaxis=dict(gridcolor='#0d3320', zerolinecolor='#0d3320',
               tickfont=dict(color='#3d7a5a')),
    legend=dict(bgcolor='#040f1a', bordercolor='#0d3320', borderwidth=1,
                font=dict(color='#7ecfa0')),
    margin=dict(l=0, r=0, t=40, b=0),
)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab5, tab1, tab2, tab3, tab4 = st.tabs([
    "⬡  WORKLOAD ORCHESTRATOR",
    "⬡  CONSTELLATION MAP",
    "⬡  PASS PREDICTIONS",
    "⬡  COST vs LATENCY",
    "⬡  CAPACITY PLANNING"
])

# ── Tab 1: Map ────────────────────────────────────────────────────────────────
with tab1:
    st.markdown("<div class='section-title'>REAL-TIME SATELLITE POSITIONS — SGP4 PROPAGATED</div>",
                unsafe_allow_html=True)

    map_df = positions_df.copy()
    map_df['type'] = map_df.apply(
        lambda r: 'OVERHEAD' if (abs(r['lat'] - lat) < 15 and abs(r['lon'] - lon) < 20)
        else 'IN ORBIT', axis=1
    )

    fig_map = px.scatter_geo(
        map_df, lat='lat', lon='lon', color='type',
        hover_name='name',
        hover_data={'lat': ':.2f', 'lon': ':.2f', 'altitude_km': ':.0f'},
        color_discrete_map={'OVERHEAD': '#00ff88', 'IN ORBIT': '#1d4a2a'},
        projection='natural earth',
    )
    fig_map.add_trace(go.Scattergeo(
        lat=[lat], lon=[lon],
        mode='markers+text',
        marker=dict(size=10, color='#ff4444', symbol='star',
                    line=dict(color='#ff4444', width=2)),
        text=[f"  {selected_location.split(',')[0].upper()}"],
        textfont=dict(family='Space Mono, monospace', size=11, color='#ff4444'),
        textposition='middle right',
        name='GROUND STATION',
        showlegend=True
    ))
    fig_map.update_layout(
        height=520,
        paper_bgcolor='#020b12',
        geo=dict(
            showland=True, landcolor='#071a10',
            showocean=True, oceancolor='#020b12',
            showframe=False, showcountries=True, countrycolor='#0d3320',
            showcoastlines=True, coastlinecolor='#0d3320',
            bgcolor='#020b12',
        ),
        font=dict(family='Space Mono, monospace', color='#7ecfa0'),
        legend=dict(bgcolor='#040f1a', bordercolor='#0d3320', borderwidth=1,
                    font=dict(color='#7ecfa0', size=11)),
        margin=dict(l=0, r=0, t=8, b=0),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='section-title'>ALTITUDE DISTRIBUTION</div>",
                    unsafe_allow_html=True)
        fig_alt = px.histogram(positions_df, x='altitude_km', nbins=30,
                               color_discrete_sequence=['#00ff88'])
        fig_alt.update_layout(height=240, xaxis_title="Altitude (km)",
                              yaxis_title="Count", **DARK)
        fig_alt.update_traces(marker_line_color='#020b12', marker_line_width=0.5)
        st.plotly_chart(fig_alt, use_container_width=True)

    with col_b:
        st.markdown("<div class='section-title'>INCLINATION DISTRIBUTION</div>",
                    unsafe_allow_html=True)
        fig_inc = px.histogram(positions_df, x='inclination', nbins=20,
                               color_discrete_sequence=['#00ccff'])
        fig_inc.update_layout(height=240, xaxis_title="Inclination (°)",
                              yaxis_title="Count", **DARK)
        fig_inc.update_traces(marker_line_color='#020b12', marker_line_width=0.5)
        st.plotly_chart(fig_inc, use_container_width=True)

# ── Tab 2: Pass Predictions ───────────────────────────────────────────────────
with tab2:
    st.markdown(
        f"<div class='section-title'>UPCOMING PASSES — {selected_location.upper()}</div>",
        unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-family:Space Mono,monospace; font-size:11px; color:#3d7a5a; "
        f"margin-bottom:12px;'>WINDOW: {horizon_hours}H &nbsp;|&nbsp; "
        f"MIN ELEVATION: {min_elevation}°</div>",
        unsafe_allow_html=True)

    if passes_df.empty:
        st.warning("NO PASSES IN CURRENT WINDOW — lower minimum elevation or expand time window")
    else:
        st.markdown(
            f"<div style='font-family:Space Mono,monospace; font-size:12px; "
            f"color:#00ff88; margin-bottom:12px;'>● {len(passes_df)} PASSES PREDICTED</div>",
            unsafe_allow_html=True)

        display_passes = passes_df[['name', 'start_time', 'peak_time', 'end_time',
                                    'max_elevation', 'duration_min']].copy()
        display_passes.columns = ['SATELLITE', 'AOS (UTC)', 'PEAK (UTC)', 'LOS (UTC)',
                                  'MAX ELEV', 'DURATION (MIN)']
        display_passes['MAX ELEV'] = display_passes['MAX ELEV'].apply(lambda x: f"{x:.1f}°")
        display_passes['DURATION (MIN)'] = display_passes['DURATION (MIN)'].apply(
            lambda x: f"{x:.1f}")
        render_dark_table(display_passes.head(30))

        st.markdown("<div class='section-title'>PASS TIMELINE</div>", unsafe_allow_html=True)
        gantt_data = passes_df.head(20).copy()
        fig_gantt = px.timeline(
            gantt_data, x_start='start_time', x_end='end_time',
            y='name', color='max_elevation',
            color_continuous_scale=[[0, '#0d3320'], [0.5, '#1D9E75'], [1, '#00ff88']],
        )
        fig_gantt.update_layout(
            height=420,
            coloraxis_colorbar=dict(
                title=dict(text='ELEV °', font=dict(color='#3d7a5a')),
                tickfont=dict(color='#3d7a5a')
            ),
            **DARK
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

        st.markdown("<div class='section-title'>HOURLY COVERAGE DENSITY</div>",
                    unsafe_allow_html=True)
        passes_df['hour'] = passes_df['start_time'].dt.hour
        hourly = passes_df.groupby('hour').size().reset_index(name='pass_count')
        fig_hourly = px.bar(hourly, x='hour', y='pass_count',
                            color_discrete_sequence=['#00ff88'],
                            labels={'hour': 'HOUR (UTC)', 'pass_count': 'PASSES'})
        fig_hourly.update_layout(height=240, **DARK)
        fig_hourly.update_traces(marker_line_color='#020b12', marker_line_width=0.5)
        st.plotly_chart(fig_hourly, use_container_width=True)

# ── Tab 3: Cost vs Latency ────────────────────────────────────────────────────
with tab3:
    st.markdown("<div class='section-title'>INFRASTRUCTURE TRADE-OFF MATRIX — LEO vs GROUND DC</div>",
                unsafe_allow_html=True)

    tradeoff_df = compute_cost_latency_tradeoff()

    fig_scatter = px.scatter(
        tradeoff_df,
        x='latency_ms', y='cost_per_gb',
        color='category', size='reliability_pct',
        hover_name='name',
        hover_data={'latency_ms': ':.0f', 'cost_per_gb': ':.3f',
                    'reliability_pct': ':.1f', 'throughput_mbps': True},
        labels={'latency_ms': 'LATENCY (ms)', 'cost_per_gb': 'COST / GB ($)'},
        color_discrete_map={
            'LEO Satellite': '#00ff88',
            'Ground DC':     '#00ccff',
            'GEO Satellite': '#ffaa00',
            'MEO Satellite': '#ff4444'
        }
    )
    fig_scatter.update_layout(height=460, **DARK)
    fig_scatter.update_traces(marker=dict(line=dict(width=1, color='#020b12')))
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("<div class='section-title'>DETAILED COMPARISON</div>", unsafe_allow_html=True)
    fmt_df = tradeoff_df.copy()
    fmt_df['latency_ms'] = fmt_df['latency_ms'].apply(lambda x: f"{x:.0f} ms")
    fmt_df['cost_per_gb'] = fmt_df['cost_per_gb'].apply(lambda x: f"${x:.3f}")
    fmt_df['reliability_pct'] = fmt_df['reliability_pct'].apply(lambda x: f"{x:.1f}%")
    fmt_df['throughput_mbps'] = fmt_df['throughput_mbps'].apply(lambda x: f"{x:.0f} Mbps")
    render_dark_table(fmt_df)

    st.markdown("<div class='section-title'>MULTI-DIMENSIONAL COMPARISON (NORMALIZED 0–100)</div>",
                unsafe_allow_html=True)
    categories = ['Cost Efficiency', 'Latency', 'Reliability', 'Throughput', 'Coverage']
    radar_data = {
        'LEO (Starlink)':     [85, 80, 95, 60, 90],
        'Regional Ground DC': [70, 95, 99, 100, 50],
        'Central Ground DC':  [60, 30, 98, 100, 55],
        'GEO Satellite':      [40, 20, 70, 40, 95],
    }
    colors = ['#00ff88', '#00ccff', '#7ecfa0', '#ffaa00']
    fig_radar = go.Figure()
    for (name, vals), color in zip(radar_data.items(), colors):
        fig_radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=categories + [categories[0]],
            fill='toself', name=name,
            line=dict(color=color, width=2),
            fillcolor=color,
            opacity=0.15
        ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor='#0d3320',
                            tickfont=dict(color='#3d7a5a'), linecolor='#0d3320'),
            angularaxis=dict(gridcolor='#0d3320', linecolor='#0d3320',
                             tickfont=dict(color='#7ecfa0')),
            bgcolor='#040f1a',
        ),
        paper_bgcolor='#020b12',
        font=dict(family='Space Mono, monospace', color='#7ecfa0'),
        legend=dict(bgcolor='#040f1a', bordercolor='#0d3320', borderwidth=1,
                    font=dict(color='#7ecfa0')),
        height=420,
        margin=dict(l=40, r=40, t=20, b=20)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# ── Tab 4: Capacity Planning ──────────────────────────────────────────────────
with tab4:
    st.markdown("<div class='section-title'>ORBITAL CAPACITY PLANNING MODEL</div>",
                unsafe_allow_html=True)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        target_coverage   = st.slider("TARGET COVERAGE (%)", 50, 99, 85)
        data_demand_tbps  = st.slider("PROJECTED DEMAND (Tbps)", 1, 500, 50)
        years_ahead       = st.slider("PLANNING HORIZON (years)", 1, 10, 5)
    with col_p2:
        sat_capacity_gbps = st.slider("PER-SATELLITE CAPACITY (Gbps)", 1, 20, 5)
        ground_stations   = st.slider("GROUND STATIONS", 10, 500, 100)
        redundancy_factor = st.slider("REDUNDANCY FACTOR", 1.0, 3.0, 1.5, step=0.1)

    demand_tbps_total = data_demand_tbps * redundancy_factor
    sats_needed   = int((demand_tbps_total * 1000) / sat_capacity_gbps)
    coverage_sats = int(sats_needed * (target_coverage / 100))

    st.markdown("<div style='border-top:1px solid #0d3320; margin:16px 0;'></div>",
                unsafe_allow_html=True)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("SATELLITES REQUIRED", f"{sats_needed:,}")
    r2.metric("FOR TARGET COVERAGE", f"{coverage_sats:,}")
    r3.metric("GROUND STATIONS", f"{int(ground_stations * redundancy_factor):,}")
    r4.metric("TOTAL CAPACITY", f"{sats_needed * sat_capacity_gbps / 1000:.1f} Tbps")

    st.markdown("<div class='section-title'>CONSTELLATION GROWTH PROJECTION (35% CAGR)</div>",
                unsafe_allow_html=True)
    years = list(range(2024, 2024 + years_ahead + 1))
    current_sats = len(satellites)
    projections = []
    for i, yr in enumerate(years):
        growth = current_sats * (1 + 0.35) ** i
        capacity_tbps = (growth * sat_capacity_gbps) / 1000
        projections.append({
            'Year': yr,
            'Satellites': int(growth),
            'Capacity (Tbps)': round(capacity_tbps, 1)
        })

    proj_df = pd.DataFrame(projections)

    fig_growth = go.Figure()
    fig_growth.add_trace(go.Bar(
        x=proj_df['Year'], y=proj_df['Satellites'],
        name='SATELLITES',
        marker_color='rgba(0,255,136,0.25)',
        marker_line_color='#00ff88',
        marker_line_width=1,
        yaxis='y'
    ))
    fig_growth.add_trace(go.Scatter(
        x=proj_df['Year'], y=proj_df['Capacity (Tbps)'],
        name='CAPACITY (Tbps)',
        line=dict(color='#00ccff', width=2),
        mode='lines+markers',
        marker=dict(color='#00ccff', size=6, line=dict(color='#020b12', width=1)),
        yaxis='y2'
    ))
    fig_growth.add_hline(
        y=sats_needed, line_dash='dash', line_color='#ffaa00', line_width=1,
        annotation_text=f"REQUIRED: {sats_needed:,}",
        annotation_font=dict(color='#ffaa00', family='Space Mono, monospace', size=10)
    )
    fig_growth.update_layout(
        height=360,
        yaxis=dict(title='SATELLITE COUNT', gridcolor='#0d3320',
                   tickfont=dict(color='#3d7a5a')),
        yaxis2=dict(title='CAPACITY (Tbps)', overlaying='y', side='right',
                    gridcolor='#0d3320', tickfont=dict(color='#3d7a5a')),
        legend=dict(orientation='h', y=1.08, bgcolor='#040f1a',
                    bordercolor='#0d3320', borderwidth=1, font=dict(color='#7ecfa0')),
        paper_bgcolor='#020b12',
        plot_bgcolor='#040f1a',
        font=dict(family='Space Mono, monospace', color='#7ecfa0'),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_growth, use_container_width=True)

    st.markdown("<div class='section-title'>YEAR-BY-YEAR PROJECTION</div>",
                unsafe_allow_html=True)
    render_dark_table(proj_df)

# ── Tab 5: Workload Orchestrator ──────────────────────────────────────────────
with tab5:
    st.markdown("<div class='section-title'>ORBITAL WORKLOAD SCHEDULER — "
                f"{selected_location.upper()}</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-family:Space Mono,monospace; font-size:11px; color:#3d7a5a; "
        "margin-bottom:12px; line-height:1.6;'>"
        "Assigns a mock job queue to the pass windows computed in "
        "PASS PREDICTIONS. INFERENCE jobs need one clean, uninterrupted pass. "
        "TRAINING jobs are chunked across as many passes as needed before "
        "their deadline — this is the actual capacity-planning problem, not "
        "just knowing where the satellites are."
        "</div>", unsafe_allow_html=True)

    jobs = generate_job_queue(n_jobs, now_utc, seed=effective_seed)
    schedule_df = schedule_jobs(jobs, passes_df)
    summary = summarize_schedule(schedule_df, jobs)

    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("JOBS QUEUED", summary['total_jobs'])
    s2.metric("FULLY SCHEDULED", summary['fully_scheduled'])
    s3.metric("PARTIAL", summary['partial'])
    s4.metric("UNSCHEDULED", summary['unscheduled'])
    s5.metric("SATELLITES USED", summary['satellites_used'])
    s6.metric("AVG WAIT (MIN)", summary['avg_wait_min'])

    if passes_df.empty:
        st.warning("NO PASS WINDOWS AVAILABLE — widen PASS WINDOW or lower MIN ELEVATION "
                   "in the sidebar so the scheduler has capacity to assign.")
    else:
        placed = schedule_df[schedule_df['status'] == 'SCHEDULED'].copy()

        st.markdown("<div class='section-title'>SCHEDULE — BY JOB</div>",
                    unsafe_allow_html=True)
        if placed.empty:
            st.info("No jobs could be placed in the current window. Try increasing "
                   "PASS WINDOW or lowering MIN ELEVATION in the sidebar.")
        else:
            placed['job_label'] = placed['job_id'] + " · " + placed['job_name']
            fig_job_gantt = px.timeline(
                placed, x_start='start_time', x_end='end_time',
                y='job_label', color='job_type',
                hover_data={'satellite': True, 'max_elevation': ':.1f',
                            'segment_duration_min': ':.1f', 'chunk_index': True},
                color_discrete_map={'inference': '#00ff88', 'training': '#00ccff'},
            )
            fig_job_gantt.update_layout(height=max(260, 22 * placed['job_label'].nunique()), **DARK)
            fig_job_gantt.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_job_gantt, use_container_width=True)

            st.markdown("<div class='section-title'>SCHEDULE — BY SATELLITE</div>",
                        unsafe_allow_html=True)
            fig_sat_gantt = px.timeline(
                placed, x_start='start_time', x_end='end_time',
                y='satellite', color='job_type',
                hover_data={'job_id': True, 'job_name': True, 'max_elevation': ':.1f'},
                color_discrete_map={'inference': '#00ff88', 'training': '#00ccff'},
            )
            fig_sat_gantt.update_layout(height=max(260, 22 * placed['satellite'].nunique()), **DARK)
            fig_sat_gantt.update_yaxes(autorange="reversed")
            st.plotly_chart(fig_sat_gantt, use_container_width=True)

        st.markdown("<div class='section-title'>JOB QUEUE DETAIL</div>", unsafe_allow_html=True)
        job_status = schedule_df.groupby('job_id').agg(
            job_name=('job_name', 'first'),
            job_type=('job_type', 'first'),
            priority=('priority', 'first'),
            status=('status', lambda s: 'SCHEDULED' if 'SCHEDULED' in set(s) and 'PARTIAL' not in set(s)
                    and 'UNSCHEDULED' not in set(s) else ('PARTIAL' if 'PARTIAL' in set(s) else 'UNSCHEDULED')),
            satellites=('satellite', lambda s: ', '.join(sorted(set(x for x in s if isinstance(x, str)))) or '—'),
            total_scheduled_min=('segment_duration_min', 'sum'),
        ).reset_index()
        job_status = job_status.merge(
            pd.DataFrame([{'job_id': j.job_id, 'required_min': j.duration_min,
                           'deadline_hours': j.deadline_hours} for j in jobs]),
            on='job_id'
        )
        job_status.columns = ['JOB ID', 'NAME', 'TYPE', 'PRIORITY', 'STATUS',
                              'SATELLITE(S)', 'SCHEDULED (MIN)', 'REQUIRED (MIN)', 'DEADLINE (H)']
        job_status['SCHEDULED (MIN)'] = job_status['SCHEDULED (MIN)'].apply(lambda x: f"{x:.1f}")
        job_status['REQUIRED (MIN)'] = job_status['REQUIRED (MIN)'].apply(lambda x: f"{x:.1f}")
        render_dark_table(job_status.sort_values('PRIORITY'))

# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(30)
    st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<div style='border-top:1px solid #0d3320; margin:24px 0 8px 0;'></div>",
            unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center; font-family:Space Mono,monospace; font-size:10px;
            color:#1d4a2a; letter-spacing:0.1em; padding-bottom:16px;'>
    DATA: CELESTRAK TLE API &nbsp;·&nbsp; PROPAGATION: SKYFIELD SGP4
    &nbsp;·&nbsp; ORBITAL INFRASTRUCTURE OBSERVABILITY &nbsp;·&nbsp; PORTFOLIO PROJECT
</div>
""", unsafe_allow_html=True)