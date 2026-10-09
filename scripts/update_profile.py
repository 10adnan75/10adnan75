"""Render the portfolio-style profile from public GitHub and WakaTime data."""
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from wakatime import SHARE_URL, summarize

ROOT = Path(__file__).resolve().parents[1]
USER = '10adnan75'
DENSITY = ' .:^~!7?JY5PGB#&@'
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


def portrait_lines(dark=False):
    lines = (ROOT/'assets/portrait.txt').read_text().splitlines()
    if not lines or len(lines) != 34:
        raise ValueError('Expected the supplied 34-line portrait')
    return lines


def render(stats, dark=True):
    c = ({'bg':'none','heading':'#e6edf3','text':'#8b949e','label':'#d29922','value':'#87ceeb','muted':'#484f58','line':'#30363d','accent':'#56d364','portrait':'#8b949e'}
         if dark else {'bg':'none','heading':'#1f2328','text':'#656d76','label':'#9a6700','value':'#5ba4cf','muted':'#8c959f','line':'#d0d7de','accent':'#2da44e','portrait':'#656d76'})
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="958" viewBox="0 0 1080 958" role="img" aria-labelledby="title desc"><title id="title">10adnan75 | Adnan M Shaikh</title><desc id="desc">Software developer, USC MS Computer Science graduate. Five professional roles, systems and full-stack projects, AI tools, and public contributions. WakaTime reports the last 30 completed days. Data refreshed {stats["updated"]}.</desc><rect width="1080" height="958" rx="14" fill="{c["bg"]}"/>']
    def text(x,y,value,color='text',size=14,weight='400',anchor=None):
        extra=f' text-anchor="{anchor}"' if anchor else ''
        p.append(f'<text x="{x}" y="{y}" fill="{c[color]}" font-family="ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace" font-size="{size}" font-weight="{weight}" xml:space="preserve"{extra}>{escape(str(value))}</text>')
    def section(x,y,title,right):
        text(x,y,title,'heading',15,'700')
        start=x+len(title)*9.04+15
        if start<right:p.append(f'<path d="M{start:.2f} {y-5} H{right}" stroke="{c["line"]}"/>')
    def row(y,key,value):
        if '.' not in key or '/' in key or '://' in value: raise ValueError('Use dotted keys and pipe separators')
        x,right=392,1052
        text(x,y,key,'label',13.5)
        text(right,y,value,'value',13.5,anchor='end')
        left_end=x+len(key)*8.14+10
        value_start=right-len(value)*8.14-10
        if value_start < left_end: raise ValueError(f'Row too long: {key}: {value}')
        if value_start-left_end>8:p.append(f'<path d="M{left_end:.2f} {y-4} H{value_start:.2f}" stroke="{c["muted"]}" stroke-width="1.4" stroke-dasharray="1 5"/>')
    section(26,35,'$ whoami',350)
    lines=portrait_lines(dark)
    p.append(f'<g fill="{c["portrait"]}" font-family="ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace" font-size="11" font-weight="400" xml:space="preserve">')
    for i,line in enumerate(lines):p.append(f'<text x="26" y="{64+i*9.8:.1f}">{escape(line)}</text>')
    p.append('</g>')
    text(26,420,'Adnan M Shaikh','heading',24,'700')
    text(26,448,'I build stuff.','accent',17)
    text(26,470,'Then I test the weird parts.','text',15)
    section(26,512,'work.lore',350)
    jobs=[
      ('Easley-Dunn Productions','Software Developer | Jun 2026 - now','Unity | card systems | integration'),
      ('USC Games','Graduate TA | Aug 2025 - May 2026','55+ students | game dev | Git'),
      ('USC Auxiliary Services','Full Stack | May 2025 - Sep 2025','React | Flask | Docker | CI + CD'),
      ('Lumina AI Health Institute','SWE Intern | May 2025 - Aug 2025','Parking AI | Go | WebRTC | GCP'),
      ('Persistent Systems','SDE | Jun 2022 - Jul 2024','React | .NET | SQL | insurance'),
    ]
    for i,(name,role,scope) in enumerate(jobs):
        y=544+i*68
        text(26,y,name,'accent',13.5,'700')
        text(26,y+19,role,'muted',11.7)
        text(26,y+37,scope,'text',11.7)
    section(26,906,'off.clock',350)
    text(26,932,'Code. Football. Curiosity.','text',14)
    section(392,35,'10adnan75',1052)
    row(73,'current.role','Software Developer')
    row(95,'current.host','Easley-Dunn Productions | MGI')
    row(117,'degree.unlocked','MS Computer Science | USC 2026')
    row(139,'home.base','Los Angeles, CA')
    row(161,'build.focus','Full stack | systems | game services')
    section(392,199,'stack.loadout',1052)
    row(225,'code.core','Java | Python | C# | C | C++ | Go')
    row(247,'web.stack','TypeScript | React | Next.js | Spring Boot')
    row(269,'api.stack','Flask | FastAPI | .NET')
    row(291,'data.layer','PostgreSQL | MSSQL | MongoDB')
    row(313,'ship.stack','Unity | Docker | GCP | GitHub Actions')
    section(392,351,'ai.stack',1052)
    row(377,'tools.in.use','Codex | ChatGPT | Cursor | Antigravity')
    row(399,'also.in.rotation','Grok | Muse')
    section(392,437,'open.source',1052)
    row(463,'ca2a.tests','Agent delegation | 3 conformance tests')
    row(485,'dicedb.fix','Client state | watcher notifications')
    row(507,'pihole.cleanup','CLI cleanup | password-wrapper comment')
    row(529,'mgi.systems','Player identity | game-service tests')
    section(392,589,'side.quests',1052)
    row(615,'squad.space','Spring Boot | React | WebRTC')
    row(637,'raft.curp','Distributed key-value store | C++')
    row(659,'kernel.mode','Weenix educational kernel | C')
    row(681,'from.scratch','HTTP server | DNS server | shell')
    section(392,719,'github.stats',1052)
    row(745,'repos.stars',f'{stats["repos"]} public repos | {stats["stars"]} original-repo stars')
    row(767,'prs.people',f'{stats["merged_prs"]} merged public PRs | {stats["followers"]} followers')
    section(392,805,'WakaTime',1052)
    row(831,'tracked.time',f'{stats["time"]} | {stats["active"]} active days | last 30 days')
    section(392,869,'say.hey',1052)
    row(895,'inbox.open','hey@adnanshaikh.space')
    row(917,'portfolio.live','adnanshaikh.space')
    row(939,'linkedin.handle','/in/10adnan75')
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
