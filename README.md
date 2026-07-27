# 🛰 Orbital Infrastructure Observability & Capacity Planning Dashboard

**Portfolio Project — Data Center Strategy / Edge Computing / Infrastructure TPM**

A real-time satellite constellation observability tool that applies data center capacity planning principles to orbital infrastructure — demonstrating fluency in the next frontier of distributed systems.

---

## What This Project Demonstrates

| Skill | How It's Demonstrated |
|---|---|
| Infrastructure capacity planning | Satellite-count-to-demand modeling, growth projections |
| Distributed systems thinking | Multi-node (3,800+ sats) availability, handoff architecture |
| Observability & telemetry | Real-time position tracking, pass windows, coverage metrics |
| Cost vs. latency trade-off modeling | LEO vs. ground DC comparison framework |
| Data pipeline engineering | CelesTrak API → SGP4 propagation → dashboard |
| Edge computing strategy | LEO as ultra-low-latency edge node analysis |

---

## Quick Start (Local)

```bash
# 1. Clone / download the project
cd orbital_dashboard

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dashboard
streamlit run app.py
```

The app opens at **http://localhost:8501**

---

## Deploy to Streamlit Cloud (Free, Public URL)

1. Push this folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo, set `app.py` as the entry point
4. Click **Deploy** — you'll have a public URL in ~2 minutes

**Your LinkedIn post URL:** `https://your-name-orbital-dashboard.streamlit.app`

---

## Project Structure

```
orbital_dashboard/
├── app.py                    # Main Streamlit dashboard
├── requirements.txt
├── README.md
└── data/
    ├── __init__.py
    ├── tle_fetcher.py        # CelesTrak API client + TLE parser
    ├── orbital_math.py       # SGP4 propagation + pass prediction
    └── cost_model.py         # Infrastructure cost/latency comparison
```

---

## Data Sources

| Source | What It Provides | Refresh Rate |
|---|---|---|
| [CelesTrak](https://celestrak.org) | Starlink TLE orbital elements | Every 30 min (cached) |
| Skyfield (SGP4) | Accurate position propagation | Real-time computation |
| SpaceX / AWS / Azure public pricing | Cost model baseline | Manual update |

**TLE API endpoint:**
```
https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle
```

---

## How SGP4 Works (For Interview Discussions)

SGP4 (Simplified General Perturbations 4) is the standard algorithm for propagating satellite orbital elements over time. Given a Two-Line Element (TLE) set that encodes:

- **Inclination** — orbital plane tilt relative to equator
- **RAAN** — right ascension of ascending node (where orbit crosses equator)
- **Eccentricity** — how elliptical the orbit is
- **Mean motion** — revolutions per day (~15.5 for Starlink)
- **Mean anomaly** — position within the orbit at epoch

...SGP4 integrates atmospheric drag, lunar/solar perturbations, and J2 oblateness effects to compute accurate lat/lon/altitude at any future time.

**This is the same algorithm used by NORAD, NASA, and every satellite operator.**

---

## Capacity Planning Logic

The dashboard's capacity model estimates required constellation size using:

```
Satellites needed = (Demand_Tbps × Redundancy_Factor × 1000) / Per_Satellite_Capacity_Gbps
```

This mirrors how data center capacity planners estimate server counts:
```
Servers needed = (Peak_Demand × N+1 Redundancy) / Per_Server_Capacity
```

The orbital case adds complexity: capacity varies by orbital position, satellite handoffs introduce latency variance, and coverage density is non-uniform (higher near orbital inclination boundaries).

---

## LinkedIn Post Template

> Just shipped a portfolio project that applies **data center capacity planning principles to orbital infrastructure**.
>
> The dashboard tracks **3,800+ Starlink satellites in real time**, predicts pass windows over any city, and models the cost vs. latency trade-offs between LEO satellite nodes and traditional cloud/DC infrastructure.
>
> **Why this matters for infrastructure strategy:**
> Companies like SpaceX, Amazon Kuiper, and Starcloud are building constellations of thousands of moving compute nodes at LEO altitudes. The capacity planning frameworks we use for ground DCs — demand modeling, redundancy budgets, latency SLAs — apply directly to orbital infrastructure, just with orbital mechanics layered on top.
>
> **Tech stack:** Python · Streamlit · Skyfield (SGP4) · CelesTrak API · Plotly
>
> 🔗 [Live demo link] | 💻 [GitHub repo link]
>
> #DataCenter #InfrastructureStrategy #EdgeComputing #Starlink #CapacityPlanning #TPM #SpaceTech

---

## Key Talking Points for Hiring Managers

**"Walk me through this project"**
> "I wanted to demonstrate that data center capacity planning skills transfer directly to the next generation of distributed infrastructure. The core problem is identical — you have a set of compute nodes with limited capacity, variable availability, and cost/latency trade-offs. The difference is the nodes are moving at 7.5 km/s and you need orbital mechanics to know when they're available."

**"What was the hardest technical challenge?"**
> "Pass prediction at scale. You can't just check if a satellite is 'above' a location — you need to solve for the elevation angle from the observer, accounting for Earth's curvature and the satellite's altitude. I used the Skyfield library's SGP4 implementation, which handles atmospheric drag and orbital perturbations that would otherwise cause multi-kilometer position errors within hours."

**"How does this relate to data center strategy work?"**
> "The capacity model in the dashboard is a direct translation of standard DC capacity planning. Instead of 'servers per rack per MW', it's 'satellites per orbital shell per coverage zone.' The cost model compares LEO's $/GB against AWS CloudFront and traditional DC interconnects — the same framework a DC strategist uses to decide between colocation, cloud, and edge."

**"What would you build next?"**
> "Three things: First, add inter-satellite link (ISL) latency modeling — Starlink's laser links between satellites create a mesh that can route traffic faster than fiber for long-haul routes. Second, integrate real Starlink coverage data to show actual throughput by location. Third, build a proper demand forecasting model that projects when specific orbital shells reach capacity saturation."

---

## Extensions (Days 4–5 or V2)

- [ ] **ISL (Inter-Satellite Link) topology** — model the laser mesh network as a graph, compute shortest paths
- [ ] **Coverage heat map** — show throughput density by lat/lon using satellite footprint geometry
- [ ] **Outage simulation** — model partial constellation failure, compute coverage degradation
- [ ] **Kuiper vs. Starlink comparison** — side-by-side shell architecture analysis
- [ ] **Real Starlink speed data** — integrate community-sourced performance data (Ookla dataset)
- [ ] **Regulatory layer** — ITU filing zones, frequency coordination constraints per region

---

*Built as a portfolio project for data center strategy, infrastructure planning, and edge computing roles.*
*Data: CelesTrak (public domain) | Orbital math: Skyfield (MIT license)*
