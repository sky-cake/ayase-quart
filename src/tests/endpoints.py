import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import subprocess

import requests

from boards import board_shortnames
from configs import app_conf
from utils import make_src_path, printr


class ExistingEndpoints(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        printr('Hypercorn, starting')
        os.chdir(make_src_path())
        cls.server_process = subprocess.Popen(['hypercorn', 'main:app', '-b', f'127.0.0.1:{app_conf.get('port')}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        printr('Hypercorn, started')
        print()

    @classmethod
    def tearDownClass(cls):
        printr('Hypercorn, terminating')
        cls.server_process.kill()
        printr('Hypercorn, terminated')
        print()

    async def test_all_endpoints(self):
        test_board = board_shortnames[0]
        endpoints = [
            '/',
            f'/{test_board}',
            f'/{test_board}/catalog',
            '/login',
            '/search',
            '/index_search',
            '/index_search_config',
            '/stats',
        ]

        for endpoint in endpoints:
            url = f'http://127.0.0.1:{app_conf.get('port')}{endpoint}'
            response = requests.get(url, timeout=5)
            self.assertEqual(response.status_code, 200, f'{response.status_code} {endpoint=}')


if __name__ == '__main__':
    unittest.main()

