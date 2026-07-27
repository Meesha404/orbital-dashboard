"""
tle_fetcher.py — CelesTrak TLE ingestion module

Fetches and parses Two-Line Element sets for the Starlink constellation.
Falls back to cached/demo data if the API is unavailable.
"""

import requests
import re
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle"
CELESTRAK_TIMEOUT = 15  # seconds

@dataclass
class TLERecord:
    """Parsed Two-Line Element record for a single satellite."""
    name: str
    line1: str
    line2: str
    norad_id: str
    epoch_year: int
    epoch_day: float
    inclination: float     # degrees
    raan: float            # right ascension of ascending node, degrees
    eccentricity: float
    arg_of_perigee: float  # degrees
    mean_anomaly: float    # degrees
    mean_motion: float     # revolutions per day


def fetch_starlink_tles(url: str = CELESTRAK_URL) -> str:
    """
    Fetch raw TLE text from CelesTrak API.

    Returns the raw multi-line text string (name, line1, line2 triplets).
    Raises requests.RequestException on network failure.
    """
    logger.info(f"Fetching TLE data from {url}")
    headers = {"User-Agent": "orbital-dashboard/1.0 (portfolio project; contact via GitHub)"}
    response = requests.get(url, headers=headers, timeout=CELESTRAK_TIMEOUT)
    if response.status_code == 403:
        raise ValueError(
            "CelesTrak returned 403 — rate limit active. "
            "Data updates every 2 hours. Using cached data if available."
        )
    response.raise_for_status()
    logger.info(f"Fetched {len(response.text)} bytes of TLE data")
    return response.text


def parse_tles(raw_text: str) -> List[TLERecord]:
    """
    Parse raw TLE text into structured TLERecord objects.

    TLE format: groups of 3 lines — name, line1, line2.
    CelesTrak delivers one constellation per request.
    """
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
    records = []

    for i in range(0, len(lines) - 2, 3):
        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if not (line1.startswith('1 ') and line2.startswith('2 ')):
            logger.warning(f"Malformed TLE block at index {i}, skipping")
            continue

        try:
            record = _parse_tle_lines(name, line1, line2)
            records.append(record)
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse TLE for {name}: {e}")
            continue

    logger.info(f"Parsed {len(records)} TLE records")
    return records


def _parse_tle_lines(name: str, line1: str, line2: str) -> TLERecord:
    """Parse individual TLE line1 and line2 into a TLERecord."""
    norad_id = line1[2:7].strip()

    # Epoch: YYDDD.DDDDDDDD
    epoch_str = line1[18:32].strip()
    epoch_year_2digit = int(epoch_str[:2])
    epoch_year = 2000 + epoch_year_2digit if epoch_year_2digit < 57 else 1900 + epoch_year_2digit
    epoch_day = float(epoch_str[2:])

    inclination = float(line2[8:16].strip())
    raan = float(line2[17:25].strip())
    eccentricity = float("0." + line2[26:33].strip())
    arg_of_perigee = float(line2[34:42].strip())
    mean_anomaly = float(line2[43:51].strip())
    mean_motion = float(line2[52:63].strip())

    return TLERecord(
        name=name,
        line1=line1,
        line2=line2,
        norad_id=norad_id,
        epoch_year=epoch_year,
        epoch_day=epoch_day,
        inclination=inclination,
        raan=raan,
        eccentricity=eccentricity,
        arg_of_perigee=arg_of_perigee,
        mean_anomaly=mean_anomaly,
        mean_motion=mean_motion
    )


def filter_active_starlinks(records: List[TLERecord],
                             min_motion: float = 14.0) -> List[TLERecord]:
    """
    Filter out deorbited or non-operational Starlink satellites.

    Starlink operational shells have mean motion ~15.0–15.6 rev/day.
    Below ~14 rev/day suggests a decaying or anomalous orbit.
    """
    return [r for r in records if r.mean_motion >= min_motion]