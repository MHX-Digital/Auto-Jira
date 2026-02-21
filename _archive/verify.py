import urllib.request, json, base64

email = 'neomaike@gmail.com'
token = 'ATATT3xFfGF0w6aylQmBgS_VLbk0LxTj-nMdCk3bY4sFxW16YlH3XLyqL-h2WEk-XN_aDmLo-ef_erml3A2M5Lx0tzoN63FfVnAPDnGjwaTOtJVWbFKf2Oku9uI1sXeTBn8s-zEWpORytg8Xt9M5PWw4MGLaYOF0Y8onpj6rl6mpvMDdrymYWeM=3FB9BC3D'
cred = base64.b64encode(f'{email}:{token}'.encode()).decode()
headers = {'Authorization': f'Basic {cred}', 'Accept': 'application/json'}

for key in ['KAN-4', 'KAN-55', 'KAN-99', 'KAN-100', 'KAN-113', 'KAN-126']:
    url = f'https://mhxdigital.atlassian.net/rest/api/3/issue/{key}?fields=summary,issuetype,components,labels,parent'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            f = d['fields']
            comp = f['components'][0]['name'] if f.get('components') else '-'
            parent = f.get('parent', {}).get('key', '-') if f.get('parent') else '-'
            lbls = ','.join(f.get('labels', []))
            itype = f['issuetype']['name']
            summ = f['summary'][:55]
            print(f"{key:8} | {itype:8} | {comp:12} | parent={parent:8} | {lbls:15} | {summ}")
    except Exception as e:
        print(f"{key}: ERRO {e}")

# Count totals
print()
for jql_label, jql in [
    ("Total issues", "project=KAN"),
    ("Epics", "project=KAN AND issuetype=Epic"),
    ("Tasks", "project=KAN AND issuetype=Tarefa"),
    ("Label p1", "project=KAN AND labels=p1"),
    ("Label p2", "project=KAN AND labels=p2"),
]:
    encoded = urllib.parse.quote(jql)
    url = f'https://mhxdigital.atlassian.net/rest/api/3/search/jql?jql={encoded}&maxResults=0'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            total = len(d.get('issues', []))
            print(f"  {jql_label}: {total}")
    except Exception as e:
        print(f"  {jql_label}: ERRO {e}")
