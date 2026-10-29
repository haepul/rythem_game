"""Read-only local browser fixtures: /empty/, /failure/, /delay/ prefixes.
Run from repo root: python tests/serve_menu_cases.py (127.0.0.1:8783).
Does not modify catalog files or browser storage.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parts = self.path.split('/', 2)
        case = parts[1] if len(parts) > 2 else ''
        if case in ('empty', 'failure', 'delay'):
            self.path = '/' + parts[2]
            if self.path.split('?')[0] == '/next-stage/data/catalog.json':
                if case == 'failure':
                    self.send_error(503, 'Intentional catalog fixture')
                    return
                if case == 'empty':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'[]')
                    return
                time.sleep(20)
        super().do_GET()

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8783), Handler).serve_forever()
