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
    days = [d for w in data['weeks'] for d in w['contributionDays']]
    counts = [0]*7
    for day in days:
        counts[(day['weekday']+6)%7] += day['contributionCount']
    def bar(value):
        filled = round(value/100*25)
        return '█'*filled + '░'*(25-filled)
    total = sum(counts) or 1
    weekly = '\n'.join(f'{name:<12} {count:>5} contributions  {bar(count/total*100)} {count/total*100:6.2f} %'
                       for name,count in zip(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'], counts))
    languages = '\n'.join(f'{name:<14} {bar(pct)} {pct:6.2f} %' for name,pct,_ in data['languages'])
    now = dt.datetime.now(dt.timezone.utc)
    start = dt.datetime(now.year,1,1,tzinfo=dt.timezone.utc)
    end = dt.datetime(now.year+1,1,1,tzinfo=dt.timezone.utc)
    progress = (now-start)/(end-start)*100
    esc = lambda value: html.escape(str(value),quote=True)
    projects = '\n'.join('- <a href="'+esc(r['url'])+'"><strong>'+esc(r['name'])+'</strong></a> — '+esc(r.get('description') or 'Source code and project documentation.') for r in data['projects'])
    readme = f'''# Hi there, I'm Duc Anh! <img src="https://raw.githubusercontent.com/TheDudeThatCode/TheDudeThatCode/master/Assets/Hi.gif" width="35" alt="Waving hand" />

<p align="center">
  <a href="https://github.com/{LOGIN}?tab=repositories">💻 Projects</a> &nbsp; • &nbsp;
  <a href="#my-github-stats">📊 GitHub Stats</a> &nbsp; • &nbsp;
  <a href="https://checkmygit.com/{LOGIN}?template=bento">🌐 Portfolio</a>
</p>

<p align="center">
  <img src="https://media.giphy.com/media/SWoSkN6DxTszqIKEqv/giphy.gif" width="500" alt="Developer working at a computer" />
</p>

### <img src="https://raw.githubusercontent.com/TheDudeThatCode/TheDudeThatCode/master/Assets/Developer.gif" width="45" alt="" /> About Me

- 🎓 Studying Software Engineering at **FPT University, Vietnam**.
- 💻 **Backend-focused Full-stack Developer** working with Java and Spring Boot.
- 🛠️ I build REST APIs, web applications, and mobile experiences.
- 🧠 Interested in practical AI features, system design, and API performance.
- 🌱 Exploring **React Native / Expo**, backend architecture, and cloud deployment.
- 🧭 Product interests: **travAIy**, **AI Study Assistant**, **AIVES**, and **FitMe AI**.
- 🗣️ Vietnamese / English.

### 🧑‍💻 Tech I Work With

<p align="center">
  <img src="https://skillicons.dev/icons?i=java,spring,postgres,react,ts,js,html,css,docker,git,githubactions,vite&amp;perline=6" alt="Java, Spring, PostgreSQL, React, TypeScript, JavaScript, HTML, CSS, Docker, Git, GitHub Actions and Vite" />
</p>

---

### My GitHub Stats

| 📦 Public repositories | ⭐ Stars earned | 🔥 Current streak | 🤝 Followers |
| :---: | :---: | :---: | :---: |
| **{data['repos']}** | **{data['stars']}** | **{data['streak']} days** | **{data['followers']}** |

📅 **Most contributions on {data['top']}** · **{data['total']} contributions** over the last year

<pre>{weekly}</pre>

💻 **Language Breakdown**

<pre>{esc(languages)}</pre>

<sub>Language shares measure code bytes in owned public repositories, excluding forks. Activity counts use GitHub contributions, including commits, pull requests, reviews, and issues.</sub>

⏳ **Year Progress:** <code>{bar(progress)}</code> **{progress:.2f}%** · {now.strftime('%d %b %Y')}

<details>
<summary><strong>📈 More activity details</strong></summary>

- **{sum(d['contributionCount'] > 0 for d in days)} active days** over the last year.
- **{max((d['contributionCount'] for d in days),default=0)} contributions** on the busiest day.
- **{data['top_count']} contributions** on {data['top']} across the year.
- Current streak follows the GitHub calendar and allows today to be unfinished.

</details>

---

### 🚀 Explore My Repositories

{projects}

[View all repositories →](https://github.com/{LOGIN}?tab=repositories)

---

<p align="center"><strong>Learning, building, and improving — one project at a time.</strong><br><sub>Statistics updated daily from public GitHub data · {now.strftime('%d %b %Y %H:%M UTC')}</sub></p>
'''
    Path('README.md').write_text(readme,encoding='utf-8')


if __name__ == '__main__':
    render(fetch())
