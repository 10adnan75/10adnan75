"""Build original, theme-aware neofetch profile cards from public aggregate data."""
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path
import urllib.request
from zoneinfo import ZoneInfo
from wakatime import SHARE_URL, summarize

ROOT = Path(__file__).resolve().parents[1]
USER = '10adnan75'


def fetch(url):
    headers = {'User-Agent': '10adnan75-neofetch-profile/1.0'}
    token = os.environ.get('GH_TOKEN')
    if url.startswith('https://api.github.com/'):
        headers['Accept'] = 'application/vnd.github+json'
        if token:
            headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def collect():
    user = fetch(f'https://api.github.com/users/{USER}')
    repos = []
    for page in range(1, 101):
        batch = fetch(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch, list):
            raise ValueError('Unexpected repository response')
        repos.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError('Repository pagination exceeded supported bound')
    search = fetch(f'https://api.github.com/search/issues?q=author%3A{USER}%20type%3Apr%20is%3Amerged%20is%3Apublic&per_page=1')
    if search.get('incomplete_results', False):
        raise ValueError('GitHub returned an incomplete PR count')
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date()
    start, end, days = summarize(fetch(SHARE_URL), today)
    mins = int(sum(seconds for _, seconds in days) // 60)
    return {
        'repos': len(repos),
        'stars': sum(r['stargazers_count'] for r in repos if not r['fork']),
        'followers': user['followers'],
        'merged_prs': search['total_count'],
        'since': datetime.fromisoformat(user['created_at'].replace('Z', '+00:00')).strftime('%b %Y'),
        'time': f'{mins // 60}h {mins % 60}m',
        'active': sum(seconds > 0 for _, seconds in days),
        'window': f'{start:%b %d} - {end:%b %d, %Y}',
        'updated': today.isoformat(),
    }


def render(stats, dark=True):
    c = {'bg':'#161b22','text':'#c9d1d9','label':'#e7b46b','value':'#9bd5ff','muted':'#687889','line':'#303b49','accent':'#8fdda5'} if dark else {'bg':'#f6f8fa','text':'#24292f','label':'#925700','value':'#075b93','muted':'#657384','line':'#d4dce5','accent':'#176f3c'}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="600" viewBox="0 0 1080 600" role="img" aria-labelledby="title desc"><title id="title">Adnan Shaikh terminal profile</title><desc id="desc">Software developer at Easley-Dunn Productions, USC MS Computer Science. ASCII portrait, technical tools, AI tools, contact details, and public activity. Updated {stats["updated"]}.</desc><rect width="1080" height="600" rx="12" fill="{c["bg"]}"/>']
    def text(x,y,value,color=None,size=14,weight='400'):
        parts.append(f'<text x="{x}" y="{y}" fill="{color or c["text"]}" font-family="Consolas, Menlo, DejaVu Sans Mono, monospace" font-size="{size}" font-weight="{weight}" xml:space="preserve">{escape(str(value))}</text>')
    text(24,31,'$ whoami',c['accent'],14)
    for i,line in enumerate((ROOT/'assets/portrait.txt').read_text().splitlines()):
        text(22,65+i*13,line,c['text'],13)
    text(24,538,'ADNAN SHAIKH',c['accent'],19,'700')
    text(24,562,'Code. Football. Curiosity.',c['muted'],12)
    x=378
    text(x,31,'adnan@10adnan75',c['accent'],16,'700')
    parts.append(f'<path d="M{x} 45 H1055" stroke="{c["line"]}"/>')
    def row(y,key,value):
        text(x,y,'. '+key,c['label'])
        # Each row uses a fixed monospace column, with dots connecting its label and value.
        total=77
        dots=max(2,total-len(key)-len(value)-4)
        text(x+(len(key)+3)*8.43,y,'.'*dots,c['muted'])
        text(1055-len(value)*8.43,y,value,c['value'])
    def section(y,name):
        text(x,y,'- '+name,c['text'],14,'700')
        parts.append(f'<path d="M{x+len(name)*8.43+30} {y-4} H1055" stroke="{c["line"]}"/>')
    row(70,'Role','Software Developer')
    row(91,'Host','Easley-Dunn Productions / MGI')
    row(112,'Education','MS Computer Science / USC')
    row(133,'Focus','Full stack, systems, game services')
    row(154,'Languages','Java, Python, C#, C/C++, Go, TypeScript')
    row(175,'Web','React, Next.js, Spring Boot, Flask, FastAPI')
    row(196,'Build','Unity, Docker, GCP, GitHub Actions')
    row(217,'GitHub.Since',stats['since'])
    section(251,'AI toolkit')
    row(276,'Tools','Codex, ChatGPT, Cursor, Antigravity')
    row(297,'Also','Grok, Muse')
    row(318,'Contribution','CA2A / delegation conformance tests')
    section(352,'Contact')
    row(377,'Web','adnanshaikh.space')
    row(398,'Email','hey@adnanshaikh.space')
    row(419,'LinkedIn','in/10adnan75')
    section(453,'Public GitHub stats')
    row(478,'Repos / Stars',f'{stats["repos"]} public / {stats["stars"]} on original repos')
    row(499,'Merged PRs / Followers',f'{stats["merged_prs"]} public / {stats["followers"]} followers')
    section(533,'WakaTime / 30 completed days')
    row(558,'Tracked / Active',f'{stats["time"]} / {stats["active"]} of 30 days')
    text(x,583,f'{stats["window"]} | Refreshed {stats["updated"]}',c['muted'],11)
    parts.append('</svg>\n')
    return '\n'.join(parts)


def main():
    stats = collect()
    # Validate and render both variants before replacing either published card.
    cards = {name:render(stats,dark) for name,dark in [('profile-dark.svg',True),('profile-light.svg',False)]}
    import xml.etree.ElementTree as ET
    for value in cards.values(): ET.fromstring(value)
    for name,value in cards.items():
        path=ROOT/'assets'/name
        temporary=path.with_suffix('.tmp')
        temporary.write_text(value,encoding='utf-8')
        temporary.replace(path)
    print('Updated both theme cards with public aggregates.')

if __name__ == '__main__':
    main()
