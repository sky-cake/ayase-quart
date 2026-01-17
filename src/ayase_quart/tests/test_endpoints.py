import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# import subprocess
import unittest

import requests

from boards import board_shortnames
from configs import app_conf


class TestExistingEndpoints(unittest.IsolatedAsyncioTestCase):

    async def test_all_endpoints(self):
        test_board = board_shortnames[0]
        endpoints = [
            '/',
            f'/{test_board}',
            f'/{test_board}/catalog',
            f'/{app_conf.get('login_endpoint')}',
            '/sql',
            '/fts',
            '/stats',
        ]

        # print('Did you start the server manually with `python main.py`?')
        for endpoint in endpoints:
            url = f'http://127.0.0.1:{app_conf.get('port')}{endpoint}'
            response = requests.get(url)

            self.assertEqual(response.status_code, 200, f'{response.status_code} {endpoint=}')



if __name__ == '__main__':
    unittest.main()
