import re
import html
from posts.quotelinks import html_quotelinks
from configs import archive_conf


def html_comment(comment: str, thread_num: int, board: str):
    """Will escape html if needed.
    
    Note: Yes, there are multiple `in comment` statements,
    but this is 1-2ms faster than looping over `comment` once, believe it or not.
    """
    if not comment:
        return comment

    # lainchan
    if archive_conf['name'][0] == 'l':
        """Lainchan's API has already has escaped the html. It's ready to be displayed."""

        has_angle_r = '<a' in comment
        if has_angle_r:
            # before: <a onclick="highlightReply('14202', event);" href="/sec/res/14192.html#14202">&gt;&gt;14202</a>
            # after: <a class="quotelink" data-board_shortname="sec" href="/sec/thread/14192#p14202">&gt;&gt;14202</a>

            comment = re.sub(r'\s*onclick="[^"]*"', '', comment)

            pattern = r'(<a)([^>]*\bhref="/)([^/]+)(/res/)([^"]*?)(\.html)?(#)?(\d+)(")'
            replacement = r'\1 class="quotelink" data-board_shortname="\3"\2\3/thread/\5\7p\8\9'
            comment = re.sub(pattern, replacement, comment)

    # 4chan
    else:
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


bbcode_re = re.compile(r'.*\[(spoiler|code|banned)\].+\[/(spoiler|code|banned)\].*', re.DOTALL)
spoiler_re = re.compile(r'\[spoiler\](.*?)\[/spoiler\]', re.DOTALL)
spoiler_sub = r'<span class="spoiler">\1</span>'
code_re = re.compile(r'\[code\](.*?)\[/code\]', re.DOTALL)
code_sub = r'<code>\1</code>'
banned_re = re.compile(r'\[banned\](.*?)\[/banned\]', re.DOTALL)
banned_sub = r'<span class="banned">\1</span>'
def html_bbcode(comment: str):
    if not bbcode_re.fullmatch(comment):
        return comment
    comment = spoiler_re.sub(spoiler_sub, comment)
    comment = code_re.sub(code_sub, comment)
    comment = banned_re.sub(banned_sub, comment)
    return comment


greentext_re = re.compile(r'^&gt;(?!&gt;\d)(.*)$', re.MULTILINE)
greentext_sub = r'<span class="quote">&gt;\1</span>'
def html_greentext(comment: str):
    return greentext_re.sub(greentext_sub, comment)


link_re = re.compile(r'(https?://(?:[a-z0-9\-]+\.)+[a-z]{2,}(?:/[^\s<>"\']*)?)', re.IGNORECASE)
def clickable_links(comment: str):
    def replace_link(match):
        url = match.group(1)
        return f'<a href="{url.rstrip('.,!?')}">{url}</a>'
    return link_re.sub(replace_link, comment)
