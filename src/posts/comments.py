from html import escape
from re import DOTALL, compile

from posts.quotelinks import html_quotelinks
from search.highlighting import html_highlight

'''
html_comment to replace restore_comment

assume that:
    comments passed in are not null
    comments are already stripped by the archiver

logic:
    escape first for malicious user input
    then highlight searchterms if they exist
    then wrap the quotelinks with link
    then wrap quotelines to green text
    then convert the bbcode tags
    finally replace all the newlines with <br>
'''

def html_comment(comment: str, op_num: int, board: str, highlight=False):
    comment = escape(comment)
    if highlight:
        comment = html_highlight(comment)
    comment = html_quotelinks(comment, board, op_num)
    comment = html_bbcode(comment)
    comment = html_greentext(comment)
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


greentext_re = compile(r'^&gt;(?!&gt;)(.*)$')
greentext_sub = r'<span class="quote">\1</span>'
def html_greentext(comment: str):
    return greentext_re.sub(greentext_sub, comment)