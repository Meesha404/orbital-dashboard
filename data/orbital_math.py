"""
orbital_math.py — SGP4 orbital propagation and pass prediction

Uses the Skyfield library for accurate satellite position calculations.
Provides:
  - Current geographic positions for all tracked satellites
  - Pass predictions (AOS/TCA/LOS) for a given ground station
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import math
import logging

logger = logging.getLogger(__name__)

# Try to import Skyfield; fall back to simplified math if unavailable
try:
    from skyfield.api import EarthSatellite, load, wgs84
    from skyfield.positionlib import Geocentric
    SKYFIELD_AVAILABLE = True
    ts = load.timescale()
except ImportError:
    SKYFIELD_AVAILABLE = False
    logger.warning("Skyfield not installed — using simplified orbital math. "
                   "Install with: pip install skyfield")

from data.tle_fetcher import TLERecord


# ─── Current Positions ────────────────────────────────────────────────────────

def get_current_positions(satellites: List[TLERecord],
                           at_time: datetime) -> pd.DataFrame:
    """
    Compute current subpoint (lat, lon, altitude) for all satellites.

    Returns a DataFrame with columns:
      name, norad_id, lat, lon, altitude_km, inclination, mean_motion
    """
    if SKYFIELD_AVAILABLE:
        return _positions_skyfield(satellites, at_time)
    else:
        return _positions_simplified(satellites, at_time)


def _positions_skyfield(satellites: List[TLERecord],
                         at_time: datetime) -> pd.DataFrame:
    """Accurate SGP4 propagation via Skyfield."""
    t = ts.from_datetime(at_time)
    rows = []

    for sat_rec in satellites:
        try:
            sat = EarthSatellite(sat_rec.line1, sat_rec.line2, sat_rec.name, ts)
            geocentric = sat.at(t)
            subpoint = wgs84.subpoint(geocentric)

            rows.append({
                'name': sat_rec.name,
                'norad_id': sat_rec.norad_id,
                'lat': subpoint.latitude.degrees,
                'lon': subpoint.longitude.degrees,
                'altitude_km': subpoint.elevation.km,
                'inclination': sat_rec.inclination,
                'mean_motion': sat_rec.mean_motion
            })
        except Exception as e:
            logger.debug(f"Position failed for {sat_rec.name}: {e}")
            continue

    return pd.DataFrame(rows)


def _positions_simplified(satellites: List[TLERecord],
                            at_time: datetime) -> pd.DataFrame:
    """
    Simplified circular orbit approximation (no Skyfield required).
    Less accurate than SGP4 but sufficient for portfolio demos.
    """
    rows = []
    epoch = datetime(at_time.year, 1, 1, tzinfo=timezone.utc)
    t_sec = (at_time - epoch).total_seconds()

    for sat in satellites:
        period_sec = 86400.0 / sat.mean_motion
        # Mean anomaly at current time
        phase = ((sat.mean_anomaly + (t_sec / period_sec) * 360.0) % 360.0) * math.pi / 180.0

        inc_rad = sat.inclination * math.pi / 180.0
        raan_rad = sat.raan * math.pi / 180.0

        # Direction cosines
        x = math.cos(raan_rad) * math.cos(phase) - math.sin(raan_rad) * math.sin(phase) * math.cos(inc_rad)
        y = math.sin(raan_rad) * math.cos(phase) + math.cos(raan_rad) * math.sin(phase) * math.cos(inc_rad)
        z = math.sin(phase) * math.sin(inc_rad)

        lon = (math.atan2(y, x) * 180.0 / math.pi) % 360.0
        lat = math.asin(max(-1.0, min(1.0, z))) * 180.0 / math.pi

        # Earth rotation offset
        earth_rotation = (t_sec / 86400.0 * 360.0) % 360.0
        lon = (lon - earth_rotation + 360.0) % 360.0
        if lon > 180.0:
            lon -= 360.0

        # Altitude estimate from mean motion (vis-viva approximation)
        mu = 398600.4418  # km^3/s^2
        T_sec = period_sec
        a_km = (mu * (T_sec / (2 * math.pi)) ** 2) ** (1 / 3)
        alt_km = a_km - 6371.0

        rows.append({
            'name': sat.name,
            'norad_id': sat.norad_id,
            'lat': lat,
            'lon': lon,
            'altitude_km': alt_km,
            'inclination': sat.inclination,
            'mean_motion': sat.mean_motion
        })

    return pd.DataFrame(rows)


# ─── Pass Prediction ──────────────────────────────────────────────────────────

def compute_passes(satellites: List[TLERecord],
                   observer_lat: float,
                   observer_lon: float,
                   start_time: datetime,
                   hours: float = 6.0,
                   min_elevation: float = 15.0,
                   time_step_sec: int = 30) -> pd.DataFrame:
    """
    Predict upcoming satellite passes over a ground location.

    Scans forward `hours` from `start_time` in `time_step_sec` increments.
    Returns a DataFrame of pass events with AOS, TCA (peak), LOS, max elevation.

    Parameters
    ----------
    satellites      : list of TLERecord
    observer_lat    : ground station latitude (degrees)
    observer_lon    : ground station longitude (degrees)
    start_time      : UTC datetime to start prediction from
    hours           : how many hours forward to predict
    min_elevation   : minimum elevation angle (degrees) to count as a visible pass
    time_step_sec   : temporal resolution of the scan (smaller = more accurate, slower)
    """
    if SKYFIELD_AVAILABLE:
        return _passes_skyfield(satellites, observer_lat, observer_lon,
                                 start_time, hours, min_elevation)
    else:
        return _passes_simplified(satellites, observer_lat, observer_lon,
                                   start_time, hours, min_elevation, time_step_sec)


def _passes_skyfield(satellites, obs_lat, obs_lon, start_time, hours, min_el):
    """Full SGP4 pass prediction using Skyfield."""
    from skyfield.api import EarthSatellite, wgs84, load
    from skyfield.positionlib import Geocentric

    observer = wgs84.latlon(obs_lat, obs_lon)
    t0 = ts.from_datetime(start_time)
    t1 = ts.from_datetime(start_time + timedelta(hours=hours))

    passes = []
    for sat_rec in satellites:
        try:
            sat = EarthSatellite(sat_rec.line1, sat_rec.line2, sat_rec.name, ts)
            events_t, events_type = sat.find_events(observer, t0, t1, altitude_degrees=min_el)

            i = 0
            while i < len(events_t) - 2:
                if events_type[i] == 0 and events_type[i+1] == 1 and events_type[i+2] == 2:
                    aos_dt = events_t[i].utc_datetime()
                    tca_dt = events_t[i+1].utc_datetime()
                    los_dt = events_t[i+2].utc_datetime()

                    # Get max elevation at TCA
                    diff = sat - observer
                    topo = diff.at(events_t[i+1])
                    alt, az, _ = topo.altaz()

                    duration = (los_dt - aos_dt).total_seconds() / 60.0
                    passes.append({
                        'name': sat_rec.name,
                        'norad_id': sat_rec.norad_id,
                        'start_time': aos_dt,
                        'peak_time': tca_dt,
                        'end_time': los_dt,
                        'max_elevation': alt.degrees,
                        'duration_min': duration
                    })
                    i += 3
                else:
                    i += 1

        except Exception as e:
            logger.debug(f"Pass prediction failed for {sat_rec.name}: {e}")
            continue

    df = pd.DataFrame(passes)
    if not df.empty:
        df = df.sort_values('start_time').reset_index(drop=True)
    return df


def _passes_simplified(satellites, obs_lat, obs_lon, start_time, hours,
                        min_el, time_step_sec):
    """
    Simplified pass predictor (no Skyfield).
    Scans time forward and estimates elevation using spherical geometry.
    Accurate enough for demonstration purposes.
    """
    import math

    EARTH_RADIUS_KM = 6371.0
    OBS_LAT_RAD = math.radians(obs_lat)
    OBS_LON_RAD = math.radians(obs_lon)
    epoch = datetime(start_time.year, 1, 1, tzinfo=timezone.utc)

    def elevation_angle(sat_lat_deg, sat_lon_deg, alt_km):
        """Approximate elevation angle from observer to satellite."""
        sat_lat_rad = math.radians(sat_lat_deg)
        sat_lon_rad = math.radians(sat_lon_deg)
        cos_angle = (math.sin(OBS_LAT_RAD) * math.sin(sat_lat_rad) +
                     math.cos(OBS_LAT_RAD) * math.cos(sat_lat_rad) *
                     math.cos(sat_lon_rad - OBS_LON_RAD))
        cos_angle = max(-1.0, min(1.0, cos_angle))
        central_angle = math.acos(cos_angle)
        # Elevation from horizon
        Re = EARTH_RADIUS_KM
        h = alt_km
        el = math.atan2(math.cos(central_angle) - Re / (Re + h),
                         math.sin(central_angle))
        return math.degrees(el)

    total_steps = int(hours * 3600 / time_step_sec)
    passes = []

    for sat_rec in satellites[:150]:  # Limit for performance
        in_pass = False
        aos_t = None
        max_el = 0.0
        tca_t = None
        t_sec_base = (start_time - epoch).total_seconds()

        for step in range(total_steps):
            t_sec = t_sec_base + step * time_step_sec
            current_dt = start_time + timedelta(seconds=step * time_step_sec)

            period_sec = 86400.0 / sat_rec.mean_motion
            phase = ((sat_rec.mean_anomaly + (t_sec / period_sec) * 360.0) % 360.0) * math.pi / 180.0
            inc_rad = sat_rec.inclination * math.pi / 180.0
            raan_rad = sat_rec.raan * math.pi / 180.0

            x = math.cos(raan_rad) * math.cos(phase) - math.sin(raan_rad) * math.sin(phase) * math.cos(inc_rad)
            y = math.sin(raan_rad) * math.cos(phase) + math.cos(raan_rad) * math.sin(phase) * math.cos(inc_rad)
            z = math.sin(phase) * math.sin(inc_rad)

            lon_eci = math.atan2(y, x) * 180.0 / math.pi
            lat_deg = math.asin(max(-1.0, min(1.0, z))) * 180.0 / math.pi

            earth_rot = (t_sec / 86400.0 * 360.0) % 360.0
            lon_deg = (lon_eci - earth_rot + 360.0) % 360.0
            if lon_deg > 180.0:
                lon_deg -= 360.0

            mu = 398600.4418
            a_km = (mu * (period_sec / (2 * math.pi)) ** 2) ** (1 / 3)
            alt_km = a_km - EARTH_RADIUS_KM

            el = elevation_angle(lat_deg, lon_deg, alt_km)

            if el >= min_el:
                if not in_pass:
                    in_pass = True
                    aos_t = current_dt
                    max_el = el
                    tca_t = current_dt
                else:
                    if el > max_el:
                        max_el = el
                        tca_t = current_dt
            else:
                if in_pass:
                    in_pass = False
                    los_t = current_dt
                    duration = (los_t - aos_t).total_seconds() / 60.0
                    if duration >= 1.0:
                        passes.append({
                            'name': sat_rec.name,
                            'norad_id': sat_rec.norad_id,
                            'start_time': aos_t,
                            'peak_time': tca_t,
                            'end_time': los_t,
                            'max_elevation': max_el,
                            'duration_min': duration
                        })

    df = pd.DataFrame(passes)
    if not df.empty:
        df = df.sort_values('start_time').reset_index(drop=True)
    return df
