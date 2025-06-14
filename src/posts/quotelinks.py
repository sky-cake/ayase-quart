import re
from collections import defaultdict
from html import escape
from typing import Generator
from utils.integers import get_prefix_uint_no0


def get_quotelink_lookup_raw(posts: list[dict]) -> dict[int, list[int]]:
    # key is num, value is list of nums quoting it
    lookup = defaultdict(list)

    for post in posts:
        # asagi comments are nullable
        if not (comment := post.get('comment')):
            continue

        num = post['num']
        for quotelink in extract_quotelinks_raw(comment):
            lookup[quotelink].append(num)

    return lookup


def get_quotelink_lookup(rows: list[dict]) -> dict[int, list[int]]:
    """
    Returns a dict of post numbers to reply post numbers.
    Not multi board safe (`num`s are reused across boards).
    """
    post_2_quotelinks = defaultdict(list)
    for row in rows:
        if not (comment := row.get('comment')):
            continue
        num = row['num']
        for quotelink in extract_quotelinks(comment):
            post_2_quotelinks[quotelink].append(num)
    return post_2_quotelinks


def extract_quotelinks(comment: str, html=False) -> list[int]:
    """Given some escaped post/comment, `text`, returns a list of all the quotelinks (>>123456) in it."""
    quotelinks = []
    if not comment:
        return quotelinks

    # if the comment is not already html escaped, escape it
    comment_esc = comment if html else escape(comment)

    # text = '>>20074095\n>>20074101\nYou may be buying the wrong eggs'
    lines = comment_esc.split("\n")

    GTGT = "&gt;&gt;"
    for line in lines:
        if not line.startswith(GTGT):
            continue
        tokens = line.split(" ")
        for token in tokens:
            # decided quotelinks like `>>0` and `>>0123` are invalid
            if token[:8] == GTGT and (prefix_int := get_prefix_uint_no0(token[8:])) is not None:
                quotelinks.append(prefix_int)

    return quotelinks  # quotelinks = [20074095, 20074101]


# TODO: perhaps we don't need esc version, rename to extract_quotelinks in the future
raw_ql_re = re.compile(r'[^>]?>>(\d+)')
def extract_quotelinks_raw(comment: str) -> Generator[int, None, None]:
    for match in raw_ql_re.findall(comment):
        yield int(match)


esc_ql_re = re.compile(r'[^;]?&gt;&gt;(\d+)')
def extract_quotelinks_esc(comment: str) -> list[int]:
    return [
        int(match)
        for match in esc_ql_re.findall(comment)
    ]


def html_quotelinks(comment: str, board: str, thread_num: int):
    def replacer(match):
        post_num = match.group(1)
        op_tag = ' (OP)' if int(post_num) == thread_num else ''
        return f'<a href="/{board}/thread/{thread_num}#p{post_num}" class="quotelink" data-board_shortname="{board}">&gt;&gt;{post_num}{op_tag}</a>'

    esc_ql_re = re.compile(r'&gt;&gt;(\d+)')
    return esc_ql_re.sub(replacer, comment)
