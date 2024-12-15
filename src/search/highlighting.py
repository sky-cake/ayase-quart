import re
from html import escape

# should not be change when html escaped
mark_pre = '||sr_hl_cls_start||'
mark_post = '||sr_hl_cls_end||'

pre_mark_esc = re.escape(mark_pre)
post_mark_esc = re.escape(mark_post)

hl_mark_sub = f'{mark_pre}\\1{mark_post}'

hl_mark_re = re.compile(f'{pre_mark_esc}(.+?){post_mark_esc}')
hl_html_sub_magenta = r'<span class="hl_magenta">\1</span>'
hl_html_sub_cyan = r'<span class="hl_cyan">\1</span>'


# first stage, mark plain text
def mark_highlight(term_re: re.Pattern, value: str):
    if not value:
        return value
    return term_re.sub(hl_mark_sub, value)


# second stage, convert html text with marks to html with html marks
def html_highlight(text: str, magenta=True):
    """If not magenta, then cyan."""
    if magenta:
        return hl_mark_re.sub(hl_html_sub_magenta, text)
    return hl_mark_re.sub(hl_html_sub_cyan, text)


def get_term_re(terms: str):
    if not terms:
        return None

    # tokens = [re.escape(t) for t in terms.split()]
    # if len(tokens) > 1:
    #     return re.compile(f"({'|'.join(tokens)})", re.IGNORECASE)

    # return re.compile(f"({tokens[0]})", re.IGNORECASE)
    return re.compile(f"({re.escape(terms)})", re.IGNORECASE)


# used for non-index search
def highlight_search_results(text: str, search_term: str, is_comment: bool = True) -> str:
    if not search_term:
        return text

    search_term = re.escape(search_term)

    color = 'hl_magenta' if is_comment else 'hl_cyan'

    matches = list(re.finditer(search_term, text, re.IGNORECASE))

    for m in reversed(matches):
        original = m.group(0)
        highlight = f'<span class="{color}">{original}</span>'
        text = text[:m.start()] + highlight + text[m.end():]

    return text