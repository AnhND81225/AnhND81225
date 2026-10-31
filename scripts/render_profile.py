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
    esc = lambda value: html.escape(str(value), quote=True)
    projects = []
    for repo in data['projects']:
        desc = (repo.get('description') or 'Explore the source code, documentation, and project structure.')
        if len(desc) > 140:
            desc = desc[:137].rsplit(' ', 1)[0] + '…'
        edges = repo.get('languages', {}).get('edges', [])
        language = edges[0]['node']['name'] if edges else 'Source code'
        projects.append(
            '<td width="50%" valign="top"><h3>↗ <a href="' + esc(repo['url']) + '">' +
            esc(repo['name']) + '</a></h3><p>' + esc(desc) +
            '</p><p><code>' + esc(language) + '</code> · ★ ' +
            str(repo['stargazerCount']) + '</p></td>'
        )
    rows = []
    for i in range(0, len(projects), 2):
        cells = projects[i:i+2]
        if len(cells) == 1:
            cells.append('<td width="50%"></td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    project_table = '<table>\n' + '\n'.join(rows) + '\n</table>' if rows else 'Public projects are coming soon.'
    languages = '\n'.join('| ' + esc(name) + ' | ' + f'{pct:.1f}%' + ' |' for name,pct,_ in data['languages'])
    now = dt.datetime.now(dt.timezone.utc).strftime('%d %b %Y · %H:%M UTC')
    readme = f'''<h1 align="center">Nguyen Duc Anh</h1>
<p align="center"><strong>Backend-focused Full-stack Developer</strong><br>Building useful products with Java, Spring Boot, and React.<br><sub>Vietnam · FPT University</sub></p>

<p align="center">
  <a href="#about">About</a> &nbsp; / &nbsp;
  <a href="#toolbox">Toolbox</a> &nbsp; / &nbsp;
  <a href="#projects">Projects</a> &nbsp; / &nbsp;
  <a href="#activity">Activity</a>
</p>

---

<table>
<tr>
<td width="25%" align="center"><h2>{data['repos']}</h2><sub>PUBLIC REPOSITORIES</sub></td>
<td width="25%" align="center"><h2>{data['stars']}</h2><sub>STARS EARNED</sub></td>
<td width="25%" align="center"><h2>{data['total']}</h2><sub>CONTRIBUTIONS / YEAR</sub></td>
<td width="25%" align="center"><h2>{data['streak']} days</h2><sub>CURRENT STREAK</sub></td>
</tr>
</table>

<h2 id="about">01 &nbsp; About</h2>

I work across backend, web, and mobile, with a focus on Java and Spring Boot. I enjoy turning product ideas into applications with clear APIs, secure access, and maintainable code.

<table>
<tr>
<td width="50%" valign="top"><h3>⚙️ Backend &amp; Systems</h3><p>REST APIs, authentication, database design, and performance.</p></td>
<td width="50%" valign="top"><h3>🧠 AI &amp; Product</h3><p>Practical AI features for learning, travel, and everyday experiences.</p></td>
</tr>
</table>

<h2 id="toolbox">02 &nbsp; Toolbox</h2>

| Backend | Frontend & Mobile | Data & Delivery |
| :--- | :--- | :--- |
| `Java` · `Spring Boot` | `React` · `TypeScript` | `PostgreSQL` · `Flyway` |
| `Spring Security` · `JWT` | `React Native` · `Expo` | `Docker` · `GitHub Actions` |
| `JPA / Hibernate` · `REST` | `TanStack Query` · `Zustand` | `Vercel` · `Render` |

<details>
<summary><strong>▸ Explore language breakdown</strong></summary>

<br>

| Language | Share of code |
| :--- | ---: |
{languages}

<sub>Based on code bytes in owned public repositories, excluding forks. This measures repository composition, rather than proficiency.</sub>

</details>

<h2 id="projects">03 &nbsp; Public Repositories</h2>

{project_table}

<p align="right"><a href="https://github.com/{LOGIN}?tab=repositories">Browse all repositories ↗</a></p>

<details>
<summary><strong>▸ Explore my product interests</strong></summary>

<br>

| Project | Focus |
| :--- | :--- |
| 🧭 **travAIy** | Trip planning, itineraries, budgets, and group coordination. |
| 📚 **AI Study Assistant** | Learning from images, step-by-step explanations, and study history. |
| 🎓 **AIVES** | Oral exam management, rubrics, and lecturer workflows. |
| 👕 **FitMe AI** | Virtual try-on and AI-assisted outfit previews. |

</details>

<h2 id="activity">04 &nbsp; Activity</h2>

<table>
<tr>
<td width="33%" align="center"><h3>🔥 {data['streak']} days</h3><sub>CURRENT STREAK</sub></td>
<td width="33%" align="center"><h3>📅 {data['top']}</h3><sub>TOP CONTRIBUTION DAY</sub></td>
<td width="33%" align="center"><h3>🤝 {data['followers']}</h3><sub>FOLLOWERS</sub></td>
</tr>
</table>

<details>
<summary><strong>▸ View activity details</strong></summary>

- **{data['total']} contributions** over the last year.
- **{data['top_count']} contributions** on {data['top']} across the year.
- **{data['years']} full years** since the account was created.
- Streak uses GitHub's contribution calendar and allows today to be unfinished.

[View GitHub activity →](https://github.com/{LOGIN}?tab=overview)

</details>

---

<p align="center"><a href="https://github.com/{LOGIN}?tab=repositories">Explore my work ↗</a><br><sub>Public GitHub data · Updated {now}</sub></p>
'''
    assert '<img' not in readme and '<svg' not in readme
    Path('README.md').write_text(readme, encoding='utf-8')


if __name__ == '__main__':
    render(fetch())
