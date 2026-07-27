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

# ─── Fallback Data ─────────────────────────────────────────────────────────
# Bundled synthetic-but-orbitally-valid TLE snapshot, used ONLY when the live
# CelesTrak fetch fails (network block, timeout, rate limit). These are labeled
# satellites (catalog numbers 90000+, outside real NORAD's active range) with
# correct TLE checksums, verified against the real sgp4 propagation library —
# they produce realistic Starlink-shell orbits (53.2 deg inclination, ~550km),
# but they are NOT live data. The UI must always disclose when this is in use.
FALLBACK_TLE_TEXT = """STARLINK-9000 [DEMO]
1 90000U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    14
2 90000  53.2160   0.0000 0001200  90.0000   0.0000 15.06000000 10003
STARLINK-9001 [DEMO]
1 90001U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    26
2 90001  53.2160   9.0000 0001200  90.0000  63.0000 15.06000000 10013
STARLINK-9002 [DEMO]
1 90002U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    38
2 90002  53.2160  18.0000 0001200  90.0000 126.0000 15.06000000 10025
STARLINK-9003 [DEMO]
1 90003U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    40
2 90003  53.2160  27.0000 0001200  90.0000 189.0000 15.06000000 10036
STARLINK-9004 [DEMO]
1 90004U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    52
2 90004  53.2160  36.0000 0001200  90.0000 252.0000 15.06000000 10049
STARLINK-9005 [DEMO]
1 90005U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    64
2 90005  53.2160  45.0000 0001200  90.0000 315.0000 15.06000000 10051
STARLINK-9006 [DEMO]
1 90006U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    76
2 90006  53.2160  54.0000 0001200  90.0000  18.0000 15.06000000 10063
STARLINK-9007 [DEMO]
1 90007U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    88
2 90007  53.2160  63.0000 0001200  90.0000  81.0000 15.06000000 10075
STARLINK-9008 [DEMO]
1 90008U 26001A   26208.50000000  .00002182  00000-0  16538-3 0    90
2 90008  53.2160  72.0000 0001200  90.0000 144.0000 15.06000000 10087
STARLINK-9009 [DEMO]
1 90009U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   103
2 90009  53.2160  81.0000 0001200  90.0000 207.0000 15.06000000 10099
STARLINK-9010 [DEMO]
1 90010U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   116
2 90010  53.2160  90.0000 0001200  90.0000 270.0000 15.06000000 10103
STARLINK-9011 [DEMO]
1 90011U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   128
2 90011  53.2160  99.0000 0001200  90.0000 333.0000 15.06000000 10114
STARLINK-9012 [DEMO]
1 90012U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   130
2 90012  53.2160 108.0000 0001200  90.0000  36.0000 15.06000000 10127
STARLINK-9013 [DEMO]
1 90013U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   142
2 90013  53.2160 117.0000 0001200  90.0000  99.0000 15.06000000 10138
STARLINK-9014 [DEMO]
1 90014U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   154
2 90014  53.2160 126.0000 0001200  90.0000 162.0000 15.06000000 10141
STARLINK-9015 [DEMO]
1 90015U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   166
2 90015  53.2160 135.0000 0001200  90.0000 225.0000 15.06000000 10153
STARLINK-9016 [DEMO]
1 90016U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   178
2 90016  53.2160 144.0000 0001200  90.0000 288.0000 15.06000000 10164
STARLINK-9017 [DEMO]
1 90017U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   180
2 90017  53.2160 153.0000 0001200  90.0000 351.0000 15.06000000 10177
STARLINK-9018 [DEMO]
1 90018U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   192
2 90018  53.2160 162.0000 0001200  90.0000  54.0000 15.06000000 10189
STARLINK-9019 [DEMO]
1 90019U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   205
2 90019  53.2160 171.0000 0001200  90.0000 117.0000 15.06000000 10191
STARLINK-9020 [DEMO]
1 90020U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   218
2 90020  53.2160 180.0000 0001200  90.0000 180.0000 15.06000000 10205
STARLINK-9021 [DEMO]
1 90021U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   220
2 90021  53.2160 189.0000 0001200  90.0000 243.0000 15.06000000 10216
STARLINK-9022 [DEMO]
1 90022U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   232
2 90022  53.2160 198.0000 0001200  90.0000 306.0000 15.06000000 10228
STARLINK-9023 [DEMO]
1 90023U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   244
2 90023  53.2160 207.0000 0001200  90.0000   9.0000 15.06000000 10231
STARLINK-9024 [DEMO]
1 90024U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   256
2 90024  53.2160 216.0000 0001200  90.0000  72.0000 15.06000000 10243
STARLINK-9025 [DEMO]
1 90025U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   268
2 90025  53.2160 225.0000 0001200  90.0000 135.0000 15.06000000 10255
STARLINK-9026 [DEMO]
1 90026U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   270
2 90026  53.2160 234.0000 0001200  90.0000 198.0000 15.06000000 10266
STARLINK-9027 [DEMO]
1 90027U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   282
2 90027  53.2160 243.0000 0001200  90.0000 261.0000 15.06000000 10279
STARLINK-9028 [DEMO]
1 90028U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   294
2 90028  53.2160 252.0000 0001200  90.0000 324.0000 15.06000000 10281
STARLINK-9029 [DEMO]
1 90029U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   307
2 90029  53.2160 261.0000 0001200  90.0000  27.0000 15.06000000 10293
STARLINK-9030 [DEMO]
1 90030U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   310
2 90030  53.2160 270.0000 0001200  90.0000  90.0000 15.06000000 10307
STARLINK-9031 [DEMO]
1 90031U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   322
2 90031  53.2160 279.0000 0001200  90.0000 153.0000 15.06000000 10318
STARLINK-9032 [DEMO]
1 90032U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   334
2 90032  53.2160 288.0000 0001200  90.0000 216.0000 15.06000000 10320
STARLINK-9033 [DEMO]
1 90033U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   346
2 90033  53.2160 297.0000 0001200  90.0000 279.0000 15.06000000 10331
STARLINK-9034 [DEMO]
1 90034U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   358
2 90034  53.2160 306.0000 0001200  90.0000 342.0000 15.06000000 10345
STARLINK-9035 [DEMO]
1 90035U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   360
2 90035  53.2160 315.0000 0001200  90.0000  45.0000 15.06000000 10357
STARLINK-9036 [DEMO]
1 90036U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   372
2 90036  53.2160 324.0000 0001200  90.0000 108.0000 15.06000000 10369
STARLINK-9037 [DEMO]
1 90037U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   384
2 90037  53.2160 333.0000 0001200  90.0000 171.0000 15.06000000 10371
STARLINK-9038 [DEMO]
1 90038U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   396
2 90038  53.2160 342.0000 0001200  90.0000 234.0000 15.06000000 10383
STARLINK-9039 [DEMO]
1 90039U 26001A   26208.50000000  .00002182  00000-0  16538-3 0   409
2 90039  53.2160 351.0000 0001200  90.0000 297.0000 15.06000000 10394"""


def load_fallback_tles() -> str:
    """Return the bundled offline demo constellation as raw TLE text."""
    return FALLBACK_TLE_TEXT
