from html import escape
from re import DOTALL, IGNORECASE, MULTILINE, compile

from posts.quotelinks import html_quotelinks, html_uneqscaped_quotelinks
from search.highlighting import html_highlight
from configs import archive_conf

'''
html_comment replaced restore_comment

assume that:
    comments passed in are not null
    comments are already stripped by the archiver

logic:
    escape first for malicious user input
    then highlight searchterms if they exist
    then wrap the quotelinks with link
    then wrap quotelines to green text
    then convert the bbcode tags
    then make links clickable
    finally replace all the newlines with <br>
'''

def html_comment(comment: str, op_num: int, board: str, highlight=False):
    """Yes, there are multiple `in comment` statements, but this is 1-2ms faster than looping over `comment` once, believe it or not."""

    # lainchan
    if archive_conf['name'][0] == 'l':
        """Lainchan's API has already has escaped the html. It's ready to be displayed."""

        comment = comment.replace('<br/>', '\n')
        has_angle_r = '>' in comment
        has_square_l = '[' in comment
        # if highlight:
        #     comment = html_highlight(comment)
        if has_angle_r:
            comment = html_uneqscaped_quotelinks(comment, board, op_num)
        if has_square_l:
            comment = comment.replace('[code]', '').replace('[/code]', '')
        if has_angle_r:
            comment = html_unescaped_greentext(comment)
        if 'http' in comment:
            comment = clickable_links(comment)
        comment = comment.replace('\n', '<br>')

    # 4chan
    else:
        has_angle_r = '>' in comment
        has_square_l = '[' in comment
        if has_angle_r or '<' in comment:
            comment = escape(comment)
        # if highlight:
        #     comment = html_highlight(comment)
        if has_angle_r:
            comment = html_quotelinks(comment, board, op_num)
        if has_square_l:
            comment = html_bbcode(comment)
        if has_angle_r:
            comment = html_greentext(comment)
        if 'http' in comment:
            comment = clickable_links(comment)
        comment = comment.replace('\n', '<br>')

    return comment


bbcode_re = compile(r'.*\[(spoiler|code|banned)\].+\[/(spoiler|code|banned)\].*')

spoiler_re = compile(r'\[spoiler\](.*?)\[/spoiler\]', DOTALL)
spoiler_sub = r'<span class="spoiler">\1</span>'
code_re = compile(r'\[code\](.*?)\[/code\]', DOTALL)
code_sub = r'<code><pre>\1</pre></code>'
banned_re = compile(r'\[banned\](.*?)\[/banned\]', DOTALL)
banned_sub = r'<span class="banned">\1</span>'
def html_bbcode(comment: str):
    if not bbcode_re.fullmatch(comment):
        return comment
    comment = spoiler_re.sub(spoiler_sub, comment)
    comment = code_re.sub(code_sub, comment)
    comment = banned_re.sub(banned_sub, comment)
    return comment


greentext_re = compile(r'^&gt;(?!&gt;\d)(.*)$', MULTILINE)
greentext_sub = r'<span class="quote">&gt;\1</span>'
def html_greentext(comment: str):
    return greentext_re.sub(greentext_sub, comment)


unescaped_greentext_re = compile(r'^>(?!>\d)(.*)$', MULTILINE)
unescaped_greentext_sub = r'<span class="quote">>\1</span>'
def html_unescaped_greentext(comment: str):
    return unescaped_greentext_re.sub(unescaped_greentext_sub, comment)


link_re = compile(r'(https?://([a-z0-9]+\.)+[a-z]{2,}[a-z0-9/\?&=\-_\(\)\+\.;,]+)[.,]?', IGNORECASE)
link_sub = r'<a href="\1">\1</a>'
def clickable_links(comment: str):
    return link_re.sub(link_sub, comment)
