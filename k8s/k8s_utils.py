#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess

def run(script, quiet=False):
    if quiet is False:
        print(f"====== {script} ======")
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    stdout_str = stdout.decode('utf-8').rstrip('\n')
    stderr_str = stderr.decode('utf-8').rstrip('\n')
    if quiet is False:
        print(f'{stdout_str}')
        print(f'{stderr_str}', file=sys.stderr)
        if proc.returncode:
            raise Exception('Exit Code: %s' % proc.returncode)
    return stdout_str
