import re
from html import escape

from jinja2 import Template
from quart import render_template
from werkzeug.exceptions import NotFound

from configs import CONSTS


def validate_board_shortname(board_shortname: str) -> None:
    if not board_shortname in CONSTS.board_shortnames:
        raise NotFound(board_shortname, CONSTS.board_shortnames)


def validate_threads(threads):
    if len(threads) < 1:
        raise NotFound(threads)


def validate_post(post):
    if not post:
        raise NotFound(post)


def get_title(board_shortname):
    title = f"/{board_shortname}/ - {CONSTS.board_shortname_to_name[board_shortname]}"
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

    form_to_asagi_field_names = []
    if form.comment.data:
        form_to_asagi_field_names.append({'form_name': 'comment', 'asagi_name': 'com'})
    if form.title.data:
        form_to_asagi_field_names.append({'form_name': 'title', 'asagi_name': 'sub'})

    for i, post in enumerate(posts['posts']):

        for field in form_to_asagi_field_names:
            asagi_name = field['asagi_name']
            form_name = field['form_name']

            escaped_field = escape(form[form_name].data)

            indices = [m.start() for m in re.finditer(escaped_field.lower(), post[asagi_name].lower())]

            for j in indices[::-1]:
                original_str = post[asagi_name][j : j + len(escaped_field)]

                highlight_str = f'<span class="search_highlight_{form_name}">{original_str}</span>'

                posts['posts'][i][asagi_name] = post[asagi_name][:j] + highlight_str + post[asagi_name][j + len(escaped_field) :]

    return posts
