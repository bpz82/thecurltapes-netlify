#!/usr/bin/env python3
"""Checks every local href/src/srcset/poster/url() in public/ resolves, and that no Squarespace host is referenced."""
import os, re, sys, urllib.parse
from bs4 import BeautifulSoup
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
BAD_HOSTS = re.compile(r'squarespace-cdn|squarespace\.com|sqspcdn|sqsp\.net|(?<!bread)crumb', re.I)

def exists(url, base):
    u = urllib.parse.urlsplit(url)
    if u.scheme in ('mailto', 'tel', 'data', 'javascript') or (u.scheme and u.netloc and 'thecurltapes.com' not in u.netloc):
        return True
    path = urllib.parse.unquote(u.path)
    if not path:
        return True
    if u.netloc and 'thecurltapes.com' in u.netloc:
        pass
    elif not path.startswith('/'):
        path = os.path.normpath(os.path.join(os.path.dirname(base), path))
    fs = os.path.join(ROOT, path.lstrip('/'))
    return os.path.isfile(fs) or os.path.isfile(os.path.join(fs, 'index.html')) or path.startswith('/api/')

problems, external = [], set()
for dp, _, fns in os.walk(ROOT):
    for fn in fns:
        full = os.path.join(dp, fn)
        rel = '/' + os.path.relpath(full, ROOT)
        if fn.endswith(('.html', '.css', '.js', '_redirects', '_headers')):
            txt = open(full, encoding='utf-8', errors='replace').read()
            for m in BAD_HOSTS.finditer(txt):
                problems.append((rel, 'squarespace reference: ' + txt[max(0, m.start()-60):m.end()+40].replace('\n', ' ')))
        if fn.endswith('.html'):
            soup = BeautifulSoup(open(full, encoding='utf-8').read(), 'lxml')
            urls = []
            for tag in soup.find_all(True):
                for attr in ('href', 'src', 'poster'):
                    if tag.get(attr):
                        urls.append(tag[attr])
                for attr in ('srcset', 'data-srcset'):
                    if tag.get(attr):
                        urls += [p.strip().split(' ')[0] for p in tag[attr].split(',') if p.strip()]
                if tag.get('style'):
                    urls += re.findall(r'url\(["\']?([^"\')]+)', tag['style'])
                if tag.get('content') and tag.get('property', '').startswith('og:image') and tag['content'].startswith('http'):
                    urls.append(tag['content'])
            for tpl in soup.find_all('template'):
                pass
            for u in urls:
                if u.startswith('#'):
                    continue
                if urllib.parse.urlsplit(u).netloc and 'thecurltapes.com' not in u:
                    external.add(u)
                if not exists(u, rel):
                    problems.append((rel, 'missing: ' + u))
        if fn.endswith('.css'):
            for u in re.findall(r'url\(["\']?([^"\')]+)', open(full).read()):
                if not u.startswith('data:') and not exists(u, rel):
                    problems.append((rel, 'missing css url: ' + u))
for p in problems:
    print('PROBLEM', *p)
print('external links:')
for e in sorted(external):
    print('  ', e)
print(f'{len(problems)} problems')
sys.exit(1 if problems else 0)
