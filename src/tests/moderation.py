import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from unittest.mock import AsyncMock, patch

from moderation.filter_cache import fc

import_str_mod_conf = 'moderation.mod.mod_conf'
import_str_get_board_num_pairs = 'moderation.filter_cache.fc.get_board_num_pairs'


class TestFilterReportedPosts(unittest.IsolatedAsyncioTestCase):

    async def test_filter_reported_posts_no_moderation(self):
        with patch(import_str_mod_conf, {'moderation': False}):
            posts = [dict(board_shortname='a', num=1)]
            result = await fc.filter_reported_posts(posts)
            self.assertEqual(result, posts)


    async def test_filter_reported_posts_no_posts(self):
        with patch(import_str_mod_conf, {'moderation': True}):
            posts = []
            result = await fc.filter_reported_posts(posts)
            self.assertEqual(result, [])


    async def test_filter_reported_posts_with_removed_posts(self):
        with patch(import_str_mod_conf, {'moderation': True}), patch(import_str_get_board_num_pairs, AsyncMock(return_value={('a', 1), ('b', 2)})):
            posts = [
                dict(board_shortname='a', num=1, thread_num=3),
                dict(board_shortname='b', num=2, thread_num=4),
                dict(board_shortname='c', num=3, thread_num=5),
            ]
            result = await fc.filter_reported_posts(posts)
            expected = [dict(board_shortname='c', num=3, thread_num=5)]
            self.assertEqual(result, expected)


    async def test_filter_reported_posts_with_remove_op_replies(self):
        with patch(import_str_mod_conf, {'moderation': True}), patch(import_str_get_board_num_pairs, AsyncMock(return_value={('a', 1), ('c', 3)})):
            posts = [
                dict(board_shortname='a', num=1, thread_num=3),
                dict(board_shortname='b', num=2, thread_num=4),
                dict(board_shortname='c', num=3, thread_num=5),
            ]
            result = await fc.filter_reported_posts(posts, remove_op_replies=True)
            expected = [dict(board_shortname='b', num=2, thread_num=4)]
            self.assertEqual(result, expected)


    async def test_filter_reported_posts_no_remove_op_replies(self):
        with patch(import_str_mod_conf, {'moderation': True}), patch(import_str_get_board_num_pairs, AsyncMock(return_value={('a', 1), ('a', 3)})):
            posts = [
                dict(board_shortname='a', num=1, thread_num=3),
                dict(board_shortname='b', num=2, thread_num=4),
                dict(board_shortname='c', num=3, thread_num=5),
            ]
            result = await fc.filter_reported_posts(posts, remove_op_replies=False)
            expected = [
                dict(board_shortname='b', num=2, thread_num=4),
                dict(board_shortname='c', num=3, thread_num=5),
            ]
            self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
