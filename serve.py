#!/usr/bin/env python3
"""Local preview for the rebuilt site.

    python3 serve.py               # http://localhost:8080, mock /api/* that logs to preview-submissions.jsonl
    python3 serve.py --port 9000
    python3 serve.py --no-api      # /api/* answers 503, to see the "not configured" fallbacks

Serves public/ the way Cloudflare Pages / Netlify do: /foo -> /foo/index.html, unknown paths -> 404.html,
and applies the redirects in public/_redirects (simple "from to status" lines).
"""
import argparse, json, os, posixpath, sys, time, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ROOT, 'public')
LOG = os.path.join(ROOT, 'preview-submissions.jsonl')

def load_redirects():
    rules = {}
    p = os.path.join(PUBLIC, '_redirects')
    if os.path.exists(p):
        for line in open(p):
            line = line.split('#', 1)[0].strip()
            parts = line.split()
            if len(parts) >= 2 and '*' not in parts[0] and ':' not in parts[0]:
                rules[parts[0].rstrip('/') or '/'] = (parts[1], int(parts[2]) if len(parts) > 2 else 301)
    return rules

class Handler(SimpleHTTPRequestHandler):
    api_enabled = True
    redirects = {}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=PUBLIC, **kw)

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.command, fmt % args))

    def _resolve(self):
        path = urllib.parse.urlsplit(self.path).path
        key = path.rstrip('/') or '/'
        if key in self.redirects:
            return ('redirect',) + self.redirects[key]
        fs = os.path.join(PUBLIC, posixpath.normpath(urllib.parse.unquote(path)).lstrip('/'))
        if os.path.isfile(fs):
            return ('file', path)
        if os.path.isdir(fs) and os.path.isfile(os.path.join(fs, 'index.html')):
            return ('file', path.rstrip('/') + '/index.html')
        if os.path.isfile(fs + '.html'):
            return ('file', path + '.html')
        return ('404', None)

    def do_GET(self):
        if self.path.startswith('/api/'):
            return self._json(405, {'ok': False, 'error': 'Use POST'})
        kind, *rest = self._resolve()
        if kind == 'redirect':
            self.send_response(rest[1]); self.send_header('Location', rest[0]); self.end_headers(); return
        if kind == '404':
            body = open(os.path.join(PUBLIC, '404.html'), 'rb').read()
            self.send_response(404); self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body); return
        q = urllib.parse.urlsplit(self.path).query
        self.path = rest[0] + ('?' + q if q else '')
        return super().do_GET()

    def do_HEAD(self):
        return self.do_GET()

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if not path.startswith('/api/'):
            return self._json(405, {'ok': False})
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n)
        try:
            data = json.loads(raw or b'{}')
        except Exception:
            return self._json(400, {'ok': False, 'error': 'Bad JSON'})
        if not self.api_enabled:
            return self._json(503, {'ok': False, 'error': 'Not configured (preview --no-api)'})
        if data.get('website'):
            return self._json(200, {'ok': True})  # honeypot: pretend success
        with open(LOG, 'a') as f:
            f.write(json.dumps({'at': time.strftime('%Y-%m-%d %H:%M:%S'), 'endpoint': path, 'data': data}) + '\n')
        print('  -> logged submission to', os.path.basename(LOG), file=sys.stderr)
        return self._json(200, {'ok': True, 'preview': True})

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b))); self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(b)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--no-api', action='store_true')
    a = ap.parse_args()
    Handler.api_enabled = not a.no_api
    Handler.redirects = load_redirects()
    print(f'Previewing {PUBLIC} at http://{a.host}:{a.port}/  (api {"off" if a.no_api else "mock"})')
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()

if __name__ == '__main__':
    main()
