"""Render the portfolio-style profile from public GitHub and WakaTime data."""
from datetime import datetime
from html import escape
import json
import os
import textwrap
from pathlib import Path
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from wakatime import SHARE_URL, summarize

ROOT = Path(__file__).resolve().parents[1]
USER = '10adnan75'
START, END = '<!-- CONTRIBUTIONS:START -->', '<!-- CONTRIBUTIONS:END -->'


def fetch(url):
    headers = {'User-Agent': '10adnan75-profile/3.0'}
    if url.startswith('https://api.github.com/'):
        headers['Accept'] = 'application/vnd.github+json'
        if os.environ.get('GH_TOKEN'):
            headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def collect():
    user = fetch(f'https://api.github.com/users/{USER}')
    repos = []
    for page in range(1, 101):
        batch = fetch(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch, list): raise ValueError('Invalid repository response')
        repos.extend(batch)
        if len(batch) < 100: break
    else: raise ValueError('Repository pagination exceeded supported bound')
    pulls = []
    for page in range(1,11):
        query = urllib.parse.urlencode({'q':f'author:{USER} is:pr is:public','per_page':100,'page':page})
        result = fetch('https://api.github.com/search/issues?' + query)
        if result.get('incomplete_results'): raise ValueError('Incomplete GitHub search results')
        if result['total_count'] > 1000: raise ValueError('PR search exceeds GitHub search limit')
        pulls.extend(result['items'])
        if len(pulls) >= result['total_count']: break
    else: raise ValueError('PR pagination exceeded supported bound')
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date()
    start, end, days = summarize(fetch(SHARE_URL), today)
    minutes = int(sum(seconds for _, seconds in days) // 60)
    external = [p for p in pulls if p['repository_url'].split('/repos/')[1].split('/')[0].lower() != USER.lower()]
    return {
        'repos':len(repos), 'stars':sum(r['stargazers_count'] for r in repos if not r['fork']),
        'followers':user['followers'], 'merged_prs':sum(bool(p['pull_request'].get('merged_at')) for p in pulls),
        'time':f'{minutes//60}h {minutes%60}m', 'active':sum(s > 0 for _, s in days),
        'updated':today.isoformat(), 'window':f'{start.isoformat()} to {end.isoformat()}',
        'external':external,
    }


def render(stats, dark=True):
    # Expand vertical spacing uniformly without stretching the typography.
    spacing = 1.05
    height = round(939 * spacing)
    c = ({'bg':'none','heading':'#e6edf3','text':'#8b949e','label':'#d29922','value':'#87ceeb','muted':'#484f58','line':'#30363d','accent':'#56d364','portrait':'#8b949e'}
         if dark else {'bg':'none','heading':'#1f2328','text':'#656d76','label':'#9a6700','value':'#5ba4cf','muted':'#8c959f','line':'#d0d7de','accent':'#2da44e','portrait':'#656d76'})
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{height}" viewBox="0 0 1080 {height}" role="img" aria-labelledby="title desc"><title id="title">10adnan75 | Adnan M Shaikh</title><desc id="desc">Software developer, USC MS Computer Science graduate. Five professional roles, systems and full-stack projects, AI tools, and public contributions. WakaTime reports the last 30 completed days. Data refreshed {stats["updated"]}.</desc><rect width="1080" height="{height}" rx="14" fill="{c["bg"]}"/>']
    def text(x,y,value,color='text',size=14,weight='400',anchor=None):
        extra=f' text-anchor="{anchor}"' if anchor else ''
        p.append(f'<text x="{x}" y="{y * spacing:.2f}" fill="{c[color]}" font-family="ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace" font-size="{size}" font-weight="{weight}" xml:space="preserve"{extra}>{escape(str(value))}</text>')
    def section(x,y,title,right):
        text(x,y,title,'heading',15,'700')
        start=x+len(title)*9.04+15
        if start<right:p.append(f'<path d="M{start:.2f} {y * spacing - 5:.2f} H{right}" stroke="{c["line"]}"/>')
    def row(y,key,value):
        if '.' not in key or '/' in key or '://' in value: raise ValueError('Use dotted keys and pipe separators')
        x,right=460,1052
        text(x,y,key,'label',13.5)
        text(right,y,value,'value',13.5,anchor='end')
        left_end=x+len(key)*8.14+10
        value_start=right-len(value)*8.14-10
        if value_start < left_end: raise ValueError(f'Row too long: {key}: {value}')
        if value_start-left_end>8:p.append(f'<path d="M{left_end:.2f} {y * spacing - 4:.2f} H{value_start:.2f}" stroke="{c["muted"]}" stroke-width="1.4" stroke-dasharray="1 5"/>')
    # 40:60 usable-width split: 394px left, 592px right, with a 40px gutter.
    section(26,35,'$ whoami',420)
    text(26,80,'Adnan M Shaikh','heading',26,'700')
    text(26,114,'I build stuff.','accent',17)
    text(26,140,'Then I test the weird parts.','text',15)
    section(26,207,'work.lore',420)
    jobs=[
      ('Easley-Dunn Productions','Software Developer | Jun 2026 - present',"Monster Gridiron's card collection and pack-opening system in Unity and C#; shared player identity; unit, integration, and scene smoke tests."),
      ('USC Games','Graduate Teaching Assistant | Aug 2025 - May 2026','Mentored 55+ students in game development and collaborative Git workflows; developed an HLSL mesh-reveal shader.'),
      ('USC Auxiliary Services','Full Stack Engineer | May 2025 - Sep 2025','React and Flask web development, Docker containerization, and CI/CD improvements.'),
      ('Lumina AI Health Institute','Software Engineer Intern | May 2025 - Aug 2025','ParkSense.ai web services, GCP deployment, and camera-to-browser streaming with Go, RTSP, and WebRTC.'),
      ('Persistent Systems','Software Development Engineer | Jun 2022 - Jul 2024','React and .NET insurance applications, SQL data migration, query optimization, and wellness features.'),
    ]
    y=245
    for name,role,description in jobs:
        text(26,y,name,'accent',15,'700')
        text(26,y+20,role,'muted',11.8)
        lines=textwrap.wrap(description,width=43,break_long_words=False,break_on_hyphens=False)
        for i,line in enumerate(lines):
            text(26,y+44+i*22,line,'text',15)
        y+=44+len(lines)*22+16
    if y>884:
        raise ValueError('Work descriptions exceed the left-column space')
    section(26,y,'off.clock',420)
    text(26,y+38,'Code. Football. Curiosity.','text',14)
    groups=[
      ('10adnan75',[
        ('current.role','Software Developer'),
        ('current.host','Easley-Dunn Productions | MGI'),
        ('degree.unlocked','MS Computer Science | USC 2026'),
        ('home.base','Los Angeles, CA'),
        ('build.focus','Full stack | distributed AI systems'),
      ]),
      ('stack.loadout',[
        ('code.core','Java | Python | C# | C | C++ | Go'),
        ('web.stack','TypeScript | Next.js | Spring Boot'),
        ('api.stack','Flask | FastAPI | .NET'),
        ('data.layer','PostgreSQL | MSSQL | MongoDB'),
        ('ship.stack','Unity | Docker | GCP | GitHub Actions'),
      ]),
      ('ai.stack',[
        ('tools.in.use','Codex | ChatGPT | Cursor | Antigravity'),
        ('also.in.rotation','Grok | Muse'),
      ]),
      ('open.source',[
        ('ca2a.tests','Agent delegation | 3 conformance tests'),
        ('dicedb.fix','Client state | watcher notifications'),
        ('pihole.cleanup','CLI cleanup | password-wrapper comment'),
        ('mgi.systems','Player identity | game-service tests'),
      ]),
      ('side.quests',[
        ('squad.space','Spring Boot | React | WebRTC'),
        ('raft.curp','Distributed key-value store | C++'),
        ('kernel.mode','Custom Weenix kernel | C'),
        ('from.scratch','HTTP server | DNS server | shell'),
      ]),
      ('github.stats',[
        ('repos.stars',f'{stats["repos"]} public repos | {stats["stars"]} original-repo stars'),
        ('prs.people',f'{stats["merged_prs"]} merged public PRs | {stats["followers"]} followers'),
      ]),
      ('coding.hours',[
        ('tracked.time',f'{stats["time"]} | {stats["active"]} active days | last 30 days'),
      ]),
    ]
    section_y=35
    for heading,entries in groups:
        section(460,section_y,heading,1052)
        row_y=section_y+38
        for key,value in entries:
            row(row_y,key,value)
            row_y+=24
        section_y=row_y-24+38
    p.append('</svg>\n')
    return '\n'.join(p)


def contributions_md(pulls):
    grouped={}
    for pull in pulls:
        repo=pull['repository_url'].split('/repos/')[1]
        grouped.setdefault(repo,[]).append(pull)
    parts=[]
    for repo in sorted(grouped,key=str.lower):
        parts.append(f'**[{repo}](https://github.com/{repo})**\n')
        for pull in sorted(grouped[repo],key=lambda p:p['number'],reverse=True):
            status='merged' if pull['pull_request'].get('merged_at') else ('open' if pull['state']=='open' else 'closed without merge')
            title=escape(pull['title']).replace('[','&#91;').replace(']','&#93;').replace('*','&#42;').replace('`','&#96;').replace('\n',' ')
            url=pull['html_url']
            if not url.startswith('https://github.com/'): raise ValueError('Unexpected PR URL')
            parts.append(f'- [#{pull["number"]}]({url}) | {title} | **{status}**')
        parts.append('')
    return '\n'.join(parts).strip()


def refresh_readme(original,pulls):
    if original.count(START)!=1 or original.count(END)!=1:raise ValueError('README contribution markers missing or duplicated')
    before,remainder=original.split(START)
    _,after=remainder.split(END)
    return before+START+'\n'+contributions_md(pulls)+'\n'+END+after


def main():
    stats=collect()
    files={ROOT/'assets'/f'profile-{name}.svg':render(stats,dark) for name,dark in [('dark',True),('light',False)]}
    for contents in files.values():ET.fromstring(contents)
    readme=ROOT/'README.md'
    files[readme]=refresh_readme(readme.read_text(),stats['external'])
    for path,contents in files.items():
        temporary=path.with_suffix(path.suffix+'.tmp')
        temporary.write_text(contents,encoding='utf-8');temporary.replace(path)
    print(f'Updated theme cards and {len(stats["external"])} public external PR entries.')

if __name__=='__main__':main()
