#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import http.server
import socketserver
import re
import unittest
from requests import get, Session
import threading
import time

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "mirror.hao.com"
})

mirrored = False

def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


def run_script(script):
    """Returns (stdout, stderr), raises error on non-zero return code"""
    import subprocess
    # Note: by using a list here (['bash', ...]) you avoid quoting issues, as the
    # arguments are passed in exactly this order (spaces, quotes, and newlines won't
    # cause problems):
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    print(f"RUNNING: {script} ...")
    stdout, stderr = proc.communicate()
    if proc.returncode:
        raise Exception('exit code %s' % proc.returncode)
    return stdout, stderr


class SimpleRestfulHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if None != re.search('/hello', self.path):
            global mirrored
            mirrored = True
            self.send_response(200)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write(bytes("mirrored /hello", 'utf-8'))
            return
        else:
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        return

class UnitTest(unittest.TestCase):

    def test_mirror(self):
        print()
        run_script("""vagrant ssh -- "lsof -i :12345 | tail -n +2 | awk '{system("kill -9 " $2)}'" """)
        run_script('vagrant ssh -- -R 12345:127.0.0.1:48081 echo')
        r = get(api('/hello'))
        self.assertEqual(200, r.status_code)
        self.assertEqual("hello page", r.text.strip())
        self.assertTrue(mirrored)


if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", 48081), SimpleRestfulHandler) as httpd:
        t = threading.Thread(target=httpd.serve_forever, name='HTTPD')
        t.setDaemon(True)
        t.start()
        time.sleep(2)
        unittest.main(verbosity=2)
