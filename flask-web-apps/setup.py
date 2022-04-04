# setup.py
import os
from setuptools import setup, find_packages

folder = os.path.dirname(os.path.realpath(__file__))
requirements_path = folder + '/requirements.txt'
install_requires = [] # Here we'll get: ["gunicorn", "docutils>=0.3", "lxml==0.5a7"]
if os.path.isfile(requirements_path):
    with open(requirements_path) as f:
        install_requires = f.read().splitlines()

config = {
    'name' : 'flask_apps',
    'description' : '',
    'author' : 'Hao Ruan',
    'author_email' : 'haoru@cisco.com',
    'version' : '1.0',
    # 'packages' : ['nmlib'],
    'packages' : find_packages(),
    'install_requires': install_requires,
    'include_package_data': True,
    'setup_requires': ['wheel'],
}

setup(**config)
# end-of-setup.py
