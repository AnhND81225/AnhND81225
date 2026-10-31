"""Render a self-contained Bento profile SVG using public GitHub data."""
import base64
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
        name login avatarUrl createdAt followers { totalCount }
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
    avatar = ''
    try:
        raw = request(user['avatarUrl'])
        mime = 'image/jpeg' if raw.startswith(b'\xff\xd8') else 'image/png'
        avatar = 'data:' + mime + ';base64,' + base64.b64encode(raw).decode()
    except Exception:
        pass
    return dict(name=user['name'] or LOGIN, repos=user['repositories']['totalCount'],
                stars=sum(r['stargazerCount'] for r in repos), followers=user['followers']['totalCount'],
                years=(dt.date.today()-dt.date.fromisoformat(user['createdAt'][:10])).days//365,
                languages=lang, streak=streak, top=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][top[0]],
                top_count=top[1], total=calendar['totalContributions'], weeks=calendar['weeks'],
                avatar=avatar)

def render(data):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="850" viewBox="0 0 1200 850" role="img" aria-labelledby="title desc">',
           '<title id="title">Nguyen Duc Anh — GitHub Bento Dashboard</title>',
           '<desc id="desc">GitHub profile, public repository statistics, language distribution and contribution calendar.</desc>',
           '<defs><clipPath id="avatar"><circle cx="74" cy="81" r="37"/></clipPath></defs>',
           '<rect width="1200" height="850" rx="16" fill="#050505"/>']
    def rect(x,y,w,h,fill='#0b0b0b',stroke='#252525',r=10):
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>')
    def text(x,y,value,size=16,color='#ededed',weight=400,anchor='start'):
        out.append(f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>')
    rect(20,20,570,224)
    rect(606,20,277,104); rect(899,20,281,104)
    rect(606,140,277,104); rect(899,140,281,104)
    if data.get('avatar'):
        out.append(f'<image xlink:href="{html.escape(data["avatar"],quote=True)}" x="37" y="44" width="74" height="74" clip-path="url(#avatar)"/>')
    else:
        out.append('<circle cx="74" cy="81" r="37" fill="#162726"/>')
        text(74,91,'DA',26,'#2dd4bf',700,'middle')
    text(130,72,data['name'],25,weight=700)
    text(130,98,'@'+LOGIN,17,'#969696')
    x = 44
    for name,pct,color in data['languages']:
        w = len(name)*7+24
        rect(x,138,w,26,'#111519',color,13)
        text(x+12,156,name,12,color)
        x += w+8
    text(44,200,'Backend-focused Full-stack Developer',16)
    text(44,223,'Java / Spring Boot  ·  React / React Native',13,'#969696')
    for x,y,value,label,color in [(744,64,data['repos'],'PUBLIC REPOSITORIES','#ededed'),(1039,64,data['stars'],'STARS EARNED','#f5a623'),(744,184,data['followers'],'FOLLOWERS','#2dd4bf'),(1039,184,data['years'],'YEARS ACTIVE','#9257ff')]:
        text(x,y,value,36,color,700,'middle'); text(x,y+25,label,11,'#969696',anchor='middle')
    rect(20,260,570,192); rect(606,260,574,192)
    text(44,295,'Top Languages',15,'#a0a0a0',600)
    out.append('<circle cx="91" cy="367" r="39" fill="none" stroke="#20252c" stroke-width="14"/>')
    offset = 0
    for i,(name,pct,color) in enumerate(data['languages']):
        length = pct/100*245.044
        out.append(f'<circle cx="91" cy="367" r="39" fill="none" stroke="{color}" stroke-width="14" stroke-dasharray="{length:.3f} {245.044-length:.3f}" stroke-dashoffset="{-offset:.3f}" transform="rotate(-90 91 367)"/>')
        offset += length
        out.append(f'<circle cx="166" cy="{326+i*23}" r="5" fill="{color}"/>')
        text(180,331+i*23,name,13); text(563,331+i*23,f'{pct:.1f}%',13,'#969696',anchor='end')
    text(630,295,'Productivity Insights',15,'#a0a0a0',600)
    rect(630,319,253,106,'#030303','#030303',16)
    rect(899,319,257,106,'#030303','#030303',16)
    text(648,348,'CURRENT STREAK',12,'#ff8500',600)
    text(648,391,str(data['streak'])+' days',26,weight=700)
    text(917,348,'TOP CONTRIBUTION DAY',12,'#2dd4bf',600)
    text(917,391,f'{data["top"]} ({data["top_count"]})',26,weight=700)
    text(20,491,'Contributions',20,weight=700)
    text(1180,491,f'{data["total"]} in the last year',14,'#a0a0a0',anchor='end')
    rect(20,510,1160,233)
    weeks = data.get('weeks', [])
    if weeks:
        colors = {'NONE':'#171c23','FIRST_QUARTILE':'#dbb900','SECOND_QUARTILE':'#f2ce00','THIRD_QUARTILE':'#ffe21c','FOURTH_QUARTILE':'#fff04a'}
        last_month = None
        for col,week in enumerate(weeks):
            for day in week['contributionDays']:
                date = dt.date.fromisoformat(day['date'])
                if date.day <= 7 and date.month != last_month:
                    text(73+col*20,537,date.strftime('%b'),10,'#777777'); last_month=date.month
                x,y=73+col*20,551+day['weekday']*22
                color=colors.get(day['contributionLevel'],'#171c23')
                out.append(f'<rect x="{x}" y="{y}" width="17" height="19" rx="4" fill="{color}"><title>{day["date"]}: {day["contributionCount"]} contributions</title></rect>')
        for row,label in [(1,'Mon'),(3,'Wed'),(5,'Fri')]: text(35,565+row*22,label,10,'#777777')
    else:
        text(600,622,'Contribution calendar will appear after the first workflow run.',16,'#969696',anchor='middle')
    text(36,727,'Last 52 weeks of activity',11,'#777777')
    text(20,784,'JAVA  /  SPRING BOOT  /  TYPESCRIPT  /  REACT',13,'#2dd4bf',600)
    text(20,813,'Public GitHub data · Language percentages are based on code bytes in owned, non-fork repositories.',11,'#777777')
    text(1180,833,'Updated '+dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d UTC'),10,'#777777',anchor='end')
    out.append('</svg>')
    Path('assets').mkdir(exist_ok=True)
    Path('assets/github-bento.svg').write_text('\n'.join(out),encoding='utf-8')

if __name__ == '__main__':
    if os.getenv('PROFILE_PREVIEW'):
        # Initial snapshot supplied by the profile owner; replaced on the first workflow run.
        data = dict(name='Nguyen Duc Anh',repos=15,stars=5,followers=1,years=2,
                    languages=[('TypeScript',38,'#3178c6'),('Java',30,'#b87911'),('JavaScript',25,'#f1e05a'),('CSS',4,'#9257ff'),('HTML',3,'#e34c26')],
                    streak=6,top='Wed',top_count=52,total=568,weeks=[])
        # The screenshot does not specify the remaining language shares.
        data['languages'] = data['languages'][:3]
    else:
        data = fetch()
    render(data)
