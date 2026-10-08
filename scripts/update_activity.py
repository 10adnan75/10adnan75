"""Generate a public, aggregate WakaTime card. No credentials or dependencies required."""
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


def render(payload, today):
    start, end, days = summarize(payload, today)
    total = sum(v for _, v in days)
    minutes = int(total // 60)
    duration = f'{minutes // 60}h {minutes % 60}m'
    active = sum(v > 0 for _, v in days)
    peak = max((v for _, v in days), default=0)
    dates = f'{start:%b %d, %Y} - {end:%b %d, %Y}'
    bars = []
    for i, (day, seconds) in enumerate(days):
        height = max(2, seconds / peak * 72) if peak else 2
        color = '#86dca5' if seconds else '#303b49'
        bars.append(f'<rect x="{34+i*31}" y="{223-height:.2f}" width="22" height="{height:.2f}" rx="3" fill="{color}"><title>{day}: {seconds/3600:.2f} tracked hours</title></rect>')
    description = f'{dates}. {duration} tracked, {active} active days. Last 30 completed days in {TIMEZONE}.'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="290" viewBox="0 0 1000 290" role="img" aria-labelledby="title desc">
<title id="title">WakaTime recent activity</title><desc id="desc">{escape(description)}</desc>
<rect width="1000" height="290" rx="18" fill="#10151d"/>
<g font-family="ui-monospace, SFMono-Regular, Consolas, monospace">
<text x="34" y="37" fill="#98a6b8" font-size="14">WAKATIME / LAST 30 COMPLETED DAYS</text>
<text x="34" y="84" fill="#f4f7fb" font-size="30" font-weight="700">{duration}</text>
<text x="34" y="111" fill="#98a6b8" font-size="14">tracked activity</text>
<text x="420" y="84" fill="#86dca5" font-size="30" font-weight="700">{active} / 30</text>
<text x="420" y="111" fill="#98a6b8" font-size="14">days with tracked activity</text>
{''.join(bars)}
<text x="34" y="253" fill="#c5cfdc" font-size="13">{dates} / {TIMEZONE}</text>
<text x="34" y="276" fill="#98a6b8" font-size="12">Connected-tool activity, not total work time. Refreshed {today.isoformat()}.</text>
</g></svg>\n'''


def main():
    req = urllib.request.Request(SHARE_URL, headers={'User-Agent': '10adnan75-profile-activity/1.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    today = datetime.now(ZoneInfo(TIMEZONE)).date()
    svg = render(payload, today)
    path = ROOT / 'assets' / 'activity.svg'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(svg, encoding='utf-8')
    temporary.replace(path)
    print('Updated aggregate activity card; raw telemetry was not written.')


if __name__ == '__main__':
    main()
