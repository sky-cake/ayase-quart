import re

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
	if not value: return value
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