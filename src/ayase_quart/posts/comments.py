import html
import re

from ..configs import archive_conf
from .quotelinks import html_quotelinks


COMMENTS_PREESCAPED = archive_conf['comments_preescaped']


BBCODE_TAGS = {
    'spoiler': '<span class="spoiler">{}</span>',
    'code': '<code>{}</code>',
}


code_re = re.compile(r'\[(code)\](.*?)\[/\1\]', re.DOTALL)
spoiler_re = re.compile(r'\[(spoiler)\](.*?)\[/\1\]', re.DOTALL)


def bbcode_sub(m: re.Match):
    tag, content = m.group(1), m.group(2)
    return BBCODE_TAGS[tag].format(content)


def html_bbcode(comment: str) -> str:
    if not comment or '[' not in comment:
        return comment

    comment = comment.replace(':lit]', ']')

    # only render one type of bbcode until a solution for straddling bbcode tags is decided
    # prioritize spoilers before codes because 4chan uses <pre> and not [code] in api responses
    found_bbcode = False
    i = 0
    while spoiler_re.search(comment):
        found_bbcode = True
        comment = spoiler_re.sub(bbcode_sub, comment)
        if i > 5:
            break
        i+=1

    if found_bbcode:
        return comment

    i = 0
    while code_re.search(comment):
        comment = code_re.sub(bbcode_sub, comment)
        if i > 5:
            break
        i+=1

    return comment


def html_title(title: str) -> str:
    return html.escape(title) if title else title


def html_comment(comment: str, thread_num: int, board: str) -> str:
    if not comment:
        return comment

    if COMMENTS_PREESCAPED:
        return _html_comment_vichan(comment)

    return _html_comment_yotsuba(comment, thread_num, board)


def _html_comment_yotsuba(comment: str, thread_num: int, board: str):
    """Will escape html if needed.

    Note: Yes, there are multiple `in comment` statements,
    but this is 1-2ms faster than looping over `comment` once, believe it or not.
    """
    has_angle_r = '>' in comment
    has_square_l = '[' in comment
    if has_angle_r or '<' in comment:
        comment = html.escape(comment)
    if has_angle_r:
        comment = html_quotelinks(comment, board, thread_num)
    if has_square_l:
        comment = html_bbcode(comment)
    if has_angle_r:
        comment = html_greentext(comment)
    if 'http' in comment:
        comment = clickable_links(comment)

    if has_square_l: # only do expensive [code] processing if there were bbtags at all
        comment = replace_newlines_except_in_code(comment)
    else:
        comment = comment.replace('\n', '<br>')
    return comment


vichan_comment_re = re.compile(r'\s*onclick="[^"]*"')
vichan_ql_pat_re = re.compile(r'(<a)([^>]*\bhref="/)([^/]+)(/res/)([^"]*?)(\.html)?(#)?(\d+)(")')
def _html_comment_vichan(comment: str):
    """Vichan's API has already has escaped the html. It's ready to be displayed."""
    # only a few tweaks needed
    has_angle_r = '<a' in comment
    if has_angle_r:
        # before: <a onclick="highlightReply('14202', event);" href="/sec/res/14192.html#14202">&gt;&gt;14202</a>
        # after: <a class="quotelink" data-board="sec" href="/sec/thread/14192#p14202">&gt;&gt;14202</a>

        comment = vichan_comment_re.sub('', comment)

        replacement = r'\1 class="quotelink" data-board="\3"\2\3/thread/\5\7p\8\9'
        comment = vichan_ql_pat_re.sub(replacement, comment)
    return comment


def replace_newlines_except_in_code(html: str):
    if not html:
        return html

    parts = re.split(r'(<code>.*?</code>)', html, flags=re.DOTALL)
    for i, part in enumerate(parts):
        if not part.startswith('<code>'):
            parts[i] = part.replace('\n', '<br>')
    return ''.join(parts)


def html_highlight(html: str, term: str, klass: str='hl_magenta') -> str:
    if not term or not html:
        return html

    pattern = re.compile(re.escape(term.strip().strip('\"')), re.IGNORECASE)

    def highlight_match(match):
        return f'<span class="{klass}">{match.group(0)}</span>'

    parts = re.split(r'(<[^>]+>)', html)
    highlighted_parts = [
        pattern.sub(highlight_match, part) if not part.startswith('<') else part
        for part in parts
    ]
    return ''.join(highlighted_parts)


greentext_re = re.compile(r'^[\t ]*&gt;(?!&gt;\d)(.*)$', re.MULTILINE)
greentext_sub = r'<span class="quote">&gt;\1</span>'
def html_greentext(comment: str):
    return greentext_re.sub(greentext_sub, comment)


link_re = re.compile(r'(https?://(?:[a-z0-9\-]+\.)+[a-z]{2,}(?:(?:\:|/)[^\s<>\"\']*)?)', re.IGNORECASE)
punc_ending_re = re.compile(r'^(.*?)(?=((?:\.|,)+(?:\s|$)))', re.IGNORECASE)
def clickable_links(comment: str):
    def replace_link(match):
        url: str = match.group(1)
        if punc_groups := punc_ending_re.match(url):
            url = punc_groups.group(1)
            punc = punc_groups.group(2)
            return f'<a href="{url}">{url}</a>{punc}'
        return f'<a href="{url}">{url}</a>'
    return link_re.sub(replace_link, comment)
