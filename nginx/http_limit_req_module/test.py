#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session
import threading

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "limit.req.hao.com"
})


burst_result = []

def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


def burst_client():
    r = get(api('/burst'))
    result = r.status_code == 200
    print(f'{threading.current_thread().name}: {result}/{r.status_code}')
    burst_result.append(result)


def run_script(script):
    """Returns (stdout, stderr), raises error on non-zero return code"""
    import subprocess
    # Note: by using a list here (['bash', ...]) you avoid quoting issues, as the
    # arguments are passed in exactly this order (spaces, quotes, and newlines won't
    # cause problems):
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode:
        raise Exception('exit code %s' % proc.returncode)
    return stdout, stderr


class UnitTest(unittest.TestCase):

    def setUp(self):
        print("Restart nginx ...")
        run_script('vagrant ssh -- sudo bash service nginx restart')
        pass

    def test_rate(self):
        r = get(api('/rate'))
        self.assertEqual(200, r.status_code)

        r = get(api('/rate'))
        self.assertEqual(501, r.status_code)


    def test_burst_nodelay(self):
        # rate 增大 burst 个
        r = get(api('/burst-nodelay'))
        self.assertEqual(200, r.status_code)
        r = get(api('/burst-nodelay'))
        self.assertEqual(200, r.status_code)
        r = get(api('/burst-nodelay'))
        self.assertEqual(200, r.status_code)
        r = get(api('/burst-nodelay'))
        self.assertEqual(200, r.status_code)


        r = get(api('/burst-nodelay'))
        self.assertEqual(501, r.status_code) # rate 再超，就直接报错


    def test_burst(self):
        r = get(api('/burst'))
        self.assertEqual(200, r.status_code)

        t1 = threading.Thread(target=burst_client, name='First Burst Client')  # 阻塞等待
        t2 = threading.Thread(target=burst_client, name='Second Burst Client')
        t3 = threading.Thread(target=burst_client, name='Third Burst Client')

        t1.start()
        t2.start()
        t3.start()

        r = get(api('/burst'))
        self.assertEqual(501, r.status_code)  # 即刻失败

        t1.join()
        t2.join()
        t3.join()

        self.assertTrue(all(burst_result))




if __name__ == '__main__':
    unittest.main(verbosity=2)