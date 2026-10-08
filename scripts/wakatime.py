"""Validate and summarize the public WakaTime daily share feed."""
from datetime import date, datetime, timedelta
from html import escape
import json
import math
from pathlib import Path
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SHARE_URL = 'https://wakatime.com/share/@1453e851-ce52-44af-8af2-165ce587bc3b/6cd26999-b894-4de2-a8c3-58874efcfe66.json'
TIMEZONE = 'America/Los_Angeles'


def summarize(payload, today):
    """Use the last 30 completed local dates; reject gaps rather than invent zeroes."""
    rows = payload.get('data')
    if not isinstance(rows, list):
        raise ValueError('Expected a WakaTime daily data list')
    start, end = today - timedelta(days=30), today - timedelta(days=1)
    daily = {}
    for row in rows:
        day = date.fromisoformat(row['range']['date'])
        if not start <= day <= end:
            continue
        if day in daily:
            raise ValueError('Duplicate date in WakaTime feed')
        if row['range'].get('timezone') != TIMEZONE:
            raise ValueError('Unexpected WakaTime timezone')
        seconds = float(row['grand_total']['total_seconds'])
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Invalid tracked time')
        daily[day] = seconds
    if len(daily) != 30:
        raise ValueError('Incomplete or stale feed; retaining the previous card')
    days = sorted(daily.items())
    return start, end, days

