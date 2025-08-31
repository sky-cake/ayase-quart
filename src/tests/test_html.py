import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from posts.comments import clickable_links


def test_clickable_links():
    cases = [
        # typical url
        ('text http://example.com text',
         'text <a href="http://example.com">http://example.com</a> text'),


        # ending sentences / punctuation
        ('text http://example.com/.',
         'text <a href="http://example.com/">http://example.com/</a>.'),

        ('text http://example.com. ..',
         'text <a href="http://example.com">http://example.com</a>. ..'),

        ('text http://example.com...',
        'text <a href="http://example.com">http://example.com</a>...'),

        ('text http://example.com/...',
        'text <a href="http://example.com/">http://example.com/</a>...'),

        ('text http://example.com!',
         'text <a href="http://example.com">http://example.com</a>!'),

        ('http://example.com',
        '<a href="http://example.com">http://example.com</a>'),

        ('text http://example.com/page, text',
         'text <a href="http://example.com/page">http://example.com/page</a>, text'),


        # tld needs to be 2+ chars
        ('text http://e.c?',
         'text http://e.c?'),


        # multiple tlds
        ('text http://sub.example.co.uk text',
         'text <a href="http://sub.example.co.uk">http://sub.example.co.uk</a> text'),


        # various edge cases
        ('text http://example.co!.. m! text',
         'text <a href="http://example.co">http://example.co</a>!.. m! text'),

        ('text http://example.com/?',
        'text <a href="http://example.com/?">http://example.com/?</a>'),

        ('text http://a.com, http://b.org!',
         'text <a href="http://a.com">http://a.com</a>, <a href="http://b.org">http://b.org</a>!'),

        ('text http://example.com/page/,/ text',
         'text <a href="http://example.com/page/,/">http://example.com/page/,/</a> text'),


        # text
        ('text text',
         'text text'),

        ('text https:// text',
         'text https:// text'),

        ('text https://s. text',
         'text https://s. text'),

        ('',
        ''),


        # query parms
        ('text http://example.com/page?id=123 text',
         'text <a href="http://example.com/page?id=123">http://example.com/page?id=123</a> text'),

        ('text http://example.com/page?id=123, text',
         'text <a href="http://example.com/page?id=123">http://example.com/page?id=123</a>, text'),

        ('text http://example.com/page?id=123,. text',
         'text <a href="http://example.com/page?id=123">http://example.com/page?id=123</a>,. text'),
    ]

    for comment, expected in cases:
        result = clickable_links(comment)
        assert result == expected, f'Failed for input: {comment}\nExpected: {expected}\nGot: {result}'


if __name__ == "__main__":
    test_clickable_links()
    print('Passed')
