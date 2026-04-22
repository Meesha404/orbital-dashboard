"""
cost_model.py — Infrastructure cost and latency comparison model

Provides normalized cost, latency, reliability, and throughput data
for comparing LEO satellite infrastructure against traditional ground DC options.

Sources:
  - Starlink pricing: SpaceX published rates (enterprise/maritime tiers)
  - Cloud egress costs: AWS/Azure/GCP public pricing pages
  - GEO/MEO: Industry estimates (Intelsat, SES, Viasat public rate cards)
  - Ground DC interconnect: Equinix ECX, Megaport published pricing

Note: All costs are illustrative/normalized for comparison purposes.
Use this as a framework — always validate with current vendor pricing.
"""

import pandas as pd
from dataclasses import dataclass
from typing import List

@dataclass
class InfrastructureOption:
    name: str
    category: str              # 'LEO Satellite', 'Ground DC', 'GEO Satellite', 'MEO Satellite'
    latency_ms: float          # typical round-trip latency
    latency_min_ms: float      # best-case
    latency_max_ms: float      # worst-case
    cost_per_gb: float         # USD per GB transferred
    reliability_pct: float     # availability SLA (%)
    throughput_mbps: float     # typical per-beam or per-link throughput
    coverage_area: str         # qualitative description
    notes: str


INFRASTRUCTURE_OPTIONS: List[InfrastructureOption] = [
    InfrastructureOption(
        name="Starlink LEO (Shell 1, ~550km)",
        category="LEO Satellite",
        latency_ms=28,
        latency_min_ms=20,
        latency_max_ms=40,
        cost_per_gb=0.08,
        reliability_pct=98.4,
        throughput_mbps=150,
        coverage_area="Global (±90° lat)",
        notes="Best latency for orbital; degrades in rain; multi-sat handoffs"
    ),
    InfrastructureOption(
        name="Starlink LEO (Shell 2, ~340km)",
        category="LEO Satellite",
        latency_ms=22,
        latency_min_ms=16,
        latency_max_ms=35,
        cost_per_gb=0.09,
        reliability_pct=97.8,
        throughput_mbps=200,
        coverage_area="Mid-latitudes (±53°)",
        notes="Lower shell = lower latency; less polar coverage"
    ),
    InfrastructureOption(
        name="AWS CloudFront (Regional Edge)",
        category="Ground DC",
        latency_ms=8,
        latency_min_ms=2,
        latency_max_ms=20,
        cost_per_gb=0.085,
        reliability_pct=99.95,
        throughput_mbps=10000,
        coverage_area="500+ PoPs globally",
        notes="Excellent for cacheable content; egress cost dominates"
    ),
    InfrastructureOption(
        name="Azure CDN (Standard)",
        category="Ground DC",
        latency_ms=10,
        latency_min_ms=3,
        latency_max_ms=25,
        cost_per_gb=0.087,
        reliability_pct=99.95,
        throughput_mbps=8000,
        coverage_area="130 PoPs globally",
        notes="Strong in EU/APAC; integrated with Azure stack"
    ),
    InfrastructureOption(
        name="Ground DC — Central (Cross-continental)",
        category="Ground DC",
        latency_ms=120,
        latency_min_ms=60,
        latency_max_ms=200,
        cost_per_gb=0.02,
        reliability_pct=99.99,
        throughput_mbps=100000,
        coverage_area="Fixed datacenter location",
        notes="Lowest cost/GB; highest latency for remote users"
    ),
    InfrastructureOption(
        name="Ground DC — Regional Edge",
        category="Ground DC",
        latency_ms=12,
        latency_min_ms=3,
        latency_max_ms=30,
        cost_per_gb=0.05,
        reliability_pct=99.99,
        throughput_mbps=50000,
        coverage_area="Metro-level (~150km radius)",
        notes="Best overall for fixed users; no coverage in unserved areas"
    ),
    InfrastructureOption(
        name="GEO Satellite (Intelsat / Viasat)",
        category="GEO Satellite",
        latency_ms=600,
        latency_min_ms=550,
        latency_max_ms=700,
        cost_per_gb=0.27,
        reliability_pct=72.0,
        throughput_mbps=50,
        coverage_area="Global exc. poles",
        notes="Physics-limited latency (35,786km orbit); legacy maritime/aviation"
    ),
    InfrastructureOption(
        name="MEO Satellite (SES O3b mPOWER)",
        category="MEO Satellite",
        latency_ms=150,
        latency_min_ms=100,
        latency_max_ms=250,
        cost_per_gb=0.18,
        reliability_pct=85.0,
        throughput_mbps=100,
        coverage_area="±45° latitude",
        notes="Mid-ground between LEO and GEO; steerable beams"
    ),
    InfrastructureOption(
        name="VSAT / Maritime (traditional)",
        category="GEO Satellite",
        latency_ms=700,
        latency_min_ms=600,
        latency_max_ms=900,
        cost_per_gb=0.32,
        reliability_pct=65.0,
        throughput_mbps=10,
        coverage_area="Global (oceangoing)",
        notes="Legacy maritime standard; being displaced by Starlink Maritime"
    ),
    InfrastructureOption(
        name="Amazon Kuiper (projected, 2026+)",
        category="LEO Satellite",
        latency_ms=30,
        latency_min_ms=20,
        latency_max_ms=45,
        cost_per_gb=0.07,
        reliability_pct=97.0,
        throughput_mbps=180,
        coverage_area="Global (±56°)",
        notes="Projected specs; not yet operational at scale as of 2025"
    ),
]


def compute_cost_latency_tradeoff() -> pd.DataFrame:
    """Convert InfrastructureOption list to a comparison DataFrame."""
    rows = []
    for opt in INFRASTRUCTURE_OPTIONS:
        rows.append({
            'name': opt.name,
            'category': opt.category,
            'latency_ms': opt.latency_ms,
            'latency_min_ms': opt.latency_min_ms,
            'latency_max_ms': opt.latency_max_ms,
            'cost_per_gb': opt.cost_per_gb,
            'reliability_pct': opt.reliability_pct,
            'throughput_mbps': opt.throughput_mbps,
            'coverage_area': opt.coverage_area,
            'notes': opt.notes
        })
    return pd.DataFrame(rows)


def recommend_infrastructure(
    max_latency_ms: float,
    max_cost_per_gb: float,
    min_reliability_pct: float,
    needs_polar_coverage: bool = False
) -> pd.DataFrame:
    """
    Filter infrastructure options by user requirements.

    Returns ranked DataFrame of options meeting all constraints,
    sorted by cost ascending.

    Example usage (capacity planning tool):
        recommend_infrastructure(max_latency_ms=50, max_cost_per_gb=0.15,
                                  min_reliability_pct=95, needs_polar_coverage=False)
    """
    df = compute_cost_latency_tradeoff()

    filtered = df[
        (df['latency_ms'] <= max_latency_ms) &
        (df['cost_per_gb'] <= max_cost_per_gb) &
        (df['reliability_pct'] >= min_reliability_pct)
    ].copy()

    if needs_polar_coverage:
        # Only keep options with global / polar coverage
        polar_capable = ['LEO Satellite', 'GEO Satellite']
        filtered = filtered[filtered['category'].isin(polar_capable)]

    return filtered.sort_values('cost_per_gb').reset_index(drop=True)
