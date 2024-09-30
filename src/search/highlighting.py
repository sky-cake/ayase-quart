import re
from html import escape

# should not be change when html escaped
mark_pre = '||sr_hl_cls_start||'
mark_post = '||sr_hl_cls_end||'

pre_mark_esc = re.escape(mark_pre)
post_mark_esc = re.escape(mark_post)

hl_mark_sub = f'{mark_pre}\\1{mark_post}'

hl_mark_re = re.compile(f'{pre_mark_esc}(.+?){post_mark_esc}')
hl_html_sub = r'<span class="search_highlight_comment">\1</span>'


# first stage, mark plain text
def mark_highlight(term_re: re.Pattern, value: str):
    if not value:
        return value
    return term_re.sub(hl_mark_sub, value)


# second stage, convert html text with marks to html with html marks
def html_highlight(value: str):
    return hl_mark_re.sub(hl_html_sub, value)


def get_term_re(terms: str):
    if not terms:
        return None

    tokens = [re.escape(t) for t in terms.split()]
    if len(tokens) > 1:
        return re.compile(f"({'|'.join(tokens)})", re.IGNORECASE)

    return re.compile(f"({tokens[0]})", re.IGNORECASE)

# used for non-index search
def highlight_search_results(form, posts: list[dict]):
    """`posts = {'posts': [{...}, {...}, ...]}`"""

    field_names = []
    if form.comment.data:
        field_names.append('comment')
    if form.title.data:
        field_names.append('title')

    for i, post in enumerate(posts['posts']):

        for field_name in field_names:

            escaped_field = escape(form[field_name].data)

            indices = [m.start() for m in re.finditer(escaped_field.lower(), post[field_name].lower())]

            for j in indices[::-1]:
                original_str = post[field_name][j : j + len(escaped_field)]

                highlight_str = f'<span class="search_highlight_{field_name}">{original_str}</span>'

                posts['posts'][i][field_name] = post[field_name][:j] + highlight_str + post[field_name][j + len(escaped_field) :]

    return posts