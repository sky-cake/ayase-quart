import re
from functools import cache
from html import escape

from jinja2 import Template
from quart import render_template
from werkzeug.exceptions import NotFound

from configs import CONSTS


def validate_board_shortname(board_shortname: str) -> None:
    if not board_shortname in CONSTS.board_shortnames:
        raise NotFound(board_shortname, CONSTS.board_shortnames)

@cache
def get_title(board_shortname: str):
    title = f"/{board_shortname}/ - {CONSTS.boards[board_shortname]}"
    return title


async def render_controller(template: str | Template, **kwargs):
    """
    `template` should be a template file name (string), or a cached template (Template object).

    Using this function makes it easier to switch between debugging the UI, and maximizing performance.
    """

    if CONSTS.TESTING:
        return await render_template(template.name, **kwargs)

    if isinstance(template, Template):
        return template.render(**kwargs)
        # return await template.render_async(**kwargs) # not sure why quart's jinja2 env is setup like this...

    raise ValueError(CONSTS.TESTING, type(template), template)


def highlight_search_results(form, posts):
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