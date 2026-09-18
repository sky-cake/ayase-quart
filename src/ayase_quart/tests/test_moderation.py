import os
import sys
from msgspec.structs import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from unittest.mock import AsyncMock, patch

from quart import Quart

from configs.structs import ModerationConfig
from moderation.filter_cache import get_filter_cache


class TestFilterReportedPosts(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = Quart(__name__)

        self.mod_conf = ModerationConfig.from_dict({
            'enabled': True,
            'hide_upstream_deleted_posts': True,
            'remove_replies_to_hidden_op': True,
            'filter_cache_type': 'sqlite',
            'regex_filter': '',
        })
        self.fc = get_filter_cache(self.mod_conf)

        self.mock_get_board_num_pairs = AsyncMock()
        self.patcher_get_board_num_pairs = patch.object(self.fc, 'get_board_num_pairs', self.mock_get_board_num_pairs)
        self.patcher_get_board_num_pairs.start()

    def tearDown(self):
        self.patcher_get_board_num_pairs.stop()

    async def test_filter_reported_posts_no_moderation(self):
        fc = get_filter_cache(replace(self.mod_conf, enabled=False))
        posts = [{"board_shortname": "a", "num": 1, "thread_num": 1}]
        async with self.app.test_request_context(path='/'):
            result = await fc.filter_reported_posts(posts)
        self.assertEqual(result, posts)

    async def test_filter_reported_posts_empty_posts(self):
        posts = []
        async with self.app.test_request_context(path='/'):
            result = await self.fc.filter_reported_posts(posts)
        self.assertEqual(result, posts)

    async def test_filter_reported_posts_as_authority(self):
        self.mock_get_board_num_pairs.return_value = {("a", 1)}
        posts = [
            {"board_shortname": "a", "num": 1, "thread_num": 1},
            {"board_shortname": "b", "num": 2, "thread_num": 2}
        ]
        async with self.app.test_request_context(path='/'):
            result = await self.fc.filter_reported_posts(posts, is_authority=True)

        expected = [
            {"board_shortname": "a", "num": 1, "thread_num": 1, "deleted": "Only visible to AQ staff."},
            {"board_shortname": "b", "num": 2, "thread_num": 2}
        ]
        self.assertEqual(result, expected)

    async def test_filter_reported_posts_not_authority(self):
        self.mock_get_board_num_pairs.return_value = {("a", 1)}
        posts = [
            {"board_shortname": "a", "num": 1, "thread_num": 1},
            {"board_shortname": "b", "num": 2, "thread_num": 1}
        ]
        async with self.app.test_request_context(path='/'):
            result = await self.fc.filter_reported_posts(posts)
        expected = [
            {"board_shortname": "b", "num": 2, "thread_num": 1},
        ]
        self.assertEqual(result, expected)

    async def test_filter_reported_posts_remove_op_replies(self):
        self.mock_get_board_num_pairs.return_value = {("a", 1)}
        posts = [
            {"board_shortname": "a", "num": 1, "thread_num": 0},
            {"board_shortname": "a", "num": 2, "thread_num": 1},
            {"board_shortname": "b", "num": 3, "thread_num": 3},
        ]
        async with self.app.test_request_context(path='/'):
            result = await self.fc.filter_reported_posts(posts, is_authority=True)
        expected = [
            {"board_shortname": "a", "num": 1, "thread_num": 0, "deleted": "Only visible to AQ staff."},
            {"board_shortname": "a", "num": 2, "thread_num": 1, "deleted": "Only visible to AQ staff."},
            {"board_shortname": "b", "num": 3, "thread_num": 3,},
        ]
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
