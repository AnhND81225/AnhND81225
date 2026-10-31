"""Build a native, image-free GitHub profile README from public data."""
import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.request

LOGIN = 'AnhND81225'

def request(url, payload=None):
    headers = {'User-Agent': 'bento-profile', 'Accept': 'application/vnd.github+json'}
    if os.getenv('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    data = json.dumps(payload).encode() if payload else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as response:
        return response.read()

def fetch():
    query = '''query($login:String!, $cursor:String) {
      user(login:$login) {
        name login createdAt followers { totalCount }
        repositories(first:100, after:$cursor, privacy:PUBLIC, ownerAffiliations:OWNER) {
          totalCount pageInfo { hasNextPage endCursor }
          nodes { name description url stargazerCount isFork
            languages(first:10, orderBy:{field:SIZE,direction:DESC}) {
              edges { size node { name color } }
            }
          }
        }
        contributionsCollection {
          contributionCalendar { totalContributions weeks {
            contributionDays { date contributionCount weekday contributionLevel }
          } }
        }
      }
    }'''
    repos, cursor = [], None
    while True:
        result = json.loads(request('https://api.github.com/graphql', {'query':query, 'variables':{'login':LOGIN,'cursor':cursor}}))
        if result.get('errors'):
            raise RuntimeError(json.dumps(result['errors']))
        user = result['data']['user']
        repos.extend(user['repositories']['nodes'])
        page = user['repositories']['pageInfo']
        if not page['hasNextPage']:
            break
        cursor = page['endCursor']
    languages = collections.Counter()
    colors = {}
    for repo in repos:
        if not repo['isFork']:
            for edge in repo['languages']['edges']:
                name = edge['node']['name']
                languages[name] += edge['size']
                colors[name] = edge['node']['color'] or '#a0a0a0'
    total = sum(languages.values()) or 1
    lang = [(name, size/total*100, colors[name]) for name,size in languages.most_common(5)]
    calendar = user['contributionsCollection']['contributionCalendar']
    days = [d for w in calendar['weeks'] for d in w['contributionDays']]
    # Ignore an unfinished current day when it has no contributions.
    active = list(days)
    if active and active[-1]['contributionCount'] == 0:
        active.pop()
    streak = 0
    for day in reversed(active):
        if not day['contributionCount']:
            break
        streak += 1
    weekdays = collections.Counter()
    for day in days:
        weekdays[day['weekday']] += day['contributionCount']
    top = weekdays.most_common(1)[0] if weekdays else (0,0)
    return dict(name=user['name'] or LOGIN, repos=user['repositories']['totalCount'],
                stars=sum(r['stargazerCount'] for r in repos), followers=user['followers']['totalCount'],
                years=(dt.date.today()-dt.date.fromisoformat(user['createdAt'][:10])).days//365,
                languages=lang, streak=streak, top=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][top[0]],
                top_count=top[1], total=calendar['totalContributions'], weeks=calendar['weeks'],
                projects=sorted((r for r in repos if not r['isFork']), key=lambda r: (-r['stargazerCount'], r['name'].lower()))[:4])




def render(data):
    import statistics
    days = sorted([d for w in data['weeks'] for d in w['contributionDays']], key=lambda d:d['date'])[-30:]
    counts = [d['contributionCount'] for d in days]
    peak = max(days,key=lambda d:d['contributionCount']) if days else {'date':'—','contributionCount':0}
    maximum = max(counts,default=0) or 1
    # Each beat corresponds to one day; amplitude scales with its actual count.
    path = ['M 60 220']
    for i,count in enumerate(counts):
        x = 60+i*36
        amplitude = count/maximum*66
        path.extend([f'L {x+8} 220',f'L {x+15} {220-amplitude:.2f}',
                     f'L {x+21} {220+amplitude*.42:.2f}',f'L {x+28} 220',f'L {x+36} 220'])
    trace = ' '.join(path)
    font = 'font-family="monospace"'
    svg = [
      '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420" role="img" aria-labelledby="title desc">',
      '<title id="title">Duc Anh — Activity Pulse</title>',
      '<desc id="desc">Thirty days of GitHub contributions. Each heartbeat represents one day; height scales with the contribution count.</desc>',
      '<defs><filter id="glow" x="-20%" y="-100%" width="140%" height="300%"><feGaussianBlur stdDeviation="3"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter><linearGradient id="trace"><stop stop-color="#22c55e" stop-opacity=".4"/><stop offset=".5" stop-color="#86efac"/><stop offset="1" stop-color="#22c55e" stop-opacity=".4"/></linearGradient></defs>',
      '<rect width="1200" height="420" rx="18" fill="#091510"/>',
      '<rect x="1" y="1" width="1198" height="418" rx="18" fill="none" stroke="#163c29"/>',
      '<circle cx="64" cy="48" r="4" fill="#4ade80"><animate attributeName="opacity" values="1;.25;1" dur="2s" repeatCount="indefinite"/></circle>',
      f'<text x="80" y="52" {font} font-size="11" fill="#4ade80" letter-spacing="3">ACTIVITY PULSE</text>',
      f'<text x="1140" y="52" {font} font-size="11" fill="#719b81" text-anchor="end">LAST {len(days)} DAYS · GITHUB CONTRIBUTIONS</text>',
      '<text x="60" y="111" font-family="Arial,sans-serif" font-size="29" font-weight="700" fill="#dcfce7">Nguyen Duc Anh</text>',
      f'<text x="60" y="139" {font} font-size="12" fill="#719b81">@AnhND81225 · Backend-focused Full-stack Developer</text>',
      '<line x1="60" y1="220" x2="1140" y2="220" stroke="#163c29"/>',
      f'<path d="{trace}" fill="none" stroke="url(#trace)" stroke-width="2.5" stroke-linejoin="round" filter="url(#glow)"/>',
      '<circle cx="0" cy="0" r="4" fill="#dcfce7"><animateMotion dur="12s" repeatCount="indefinite" path="'+trace+'"/><animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.03;.97;1" dur="12s" repeatCount="indefinite"/></circle>',
      '<line x1="60" y1="300" x2="1140" y2="300" stroke="#163c29"/>'
    ]
    metrics = [
      ('PEAK DAY',str(peak['contributionCount']),peak['date']),
      ('AVERAGE / DAY',f'{statistics.mean(counts) if counts else 0:.1f}','last 30 days'),
      ('ACTIVE DAYS',str(sum(c>0 for c in counts)),f'of {len(days)} days'),
      ('CURRENT STREAK',str(data['streak'])+' days','GitHub calendar'),
      ('CONTRIBUTIONS',str(sum(counts)),'last 30 days')
    ]
    for i,(label,value,detail) in enumerate(metrics):
        x=60+i*222
        svg.extend([f'<text x="{x}" y="329" {font} font-size="10" fill="#719b81" letter-spacing="1.5">{html.escape(label)}</text>',
                    f'<text x="{x}" y="360" {font} font-size="23" font-weight="700" fill="#dcfce7">{html.escape(value)}</text>',
                    f'<text x="{x}" y="383" {font} font-size="11" fill="#719b81">{html.escape(detail)}</text>'])
    svg.append('</svg>')
    Path('assets').mkdir(exist_ok=True)
    Path('assets/activity-pulse.svg').write_text('\n'.join(svg),encoding='utf-8')
    now=dt.datetime.now(dt.timezone.utc).strftime('%d %b %Y')
    languages = ' · '.join(f"**{html.escape(name)}** {pct:.1f}%" for name,pct,_ in data['languages'])
    projects='\n'.join('- <a href="'+html.escape(r['url'],quote=True)+'">'+html.escape(r['name'])+'</a>' for r in data['projects'])
    readme=f'''<h1 align="center">Nguyen Duc Anh</h1>
<p align="center"><em>Java & Spring Boot · Web & Mobile · Building useful products</em></p>

<p align="center">
  <img src="./assets/activity-pulse.svg" alt="Activity Pulse — 30 days of real GitHub contributions with an animated heartbeat" width="100%" />
</p>

### How I work

- Backend-focused full-stack developer studying at **FPT University, Vietnam**.
- Building with **Java, Spring Boot, PostgreSQL, React, and React Native / Expo**.
- Exploring practical AI features, maintainable architecture, and API performance.

### Tech Sphere

<p align="center">
  <img src="./assets/tech-sphere.svg" alt="Nguyen Duc Anh — rotating Java, Spring, PostgreSQL, React, TypeScript, Docker and Expo sphere" width="100%" />
</p>

<details>
<summary>Language breakdown</summary>

{languages}

</details>

<details>
<summary>More technologies</summary>

Spring Security · JWT · JPA / Hibernate · Docker · Flyway · GitHub Actions · TanStack Query · Zustand

</details>

### Projects

{projects}

[All repositories →](https://github.com/{LOGIN}?tab=repositories)

---

<sub>The pulse uses GitHub contribution counts, including commits, pull requests, reviews, and issues. One beat per day; beat height reflects activity. Updated daily · {now}.</sub>

<sub>Visual inspiration: [Tech Sphere](https://github.com/beydemirfurkan/awesome-github-profile/tree/main/templates/03-3d-immersive/tech-sphere) · [Activity Pulse](https://github.com/beydemirfurkan/awesome-github-profile/tree/main/templates/05-dashboard/activity-pulse).</sub>
'''
    Path('README.md').write_text(readme,encoding='utf-8')


if __name__ == '__main__':
    render(fetch())
