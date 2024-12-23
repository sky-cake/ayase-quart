from asagi_converter import generate_post
from posts.template_optimizer import wrap_post_t
from templates import template_search_post_t


async def generate_post_html(board_shortname: str, num: int) -> str:
    """Removes [Report]"""
    post_2_quotelinks, post = await generate_post(board_shortname, num)
    if not post:
        return 'Error fetching post.'
    post_t = wrap_post_t(post | dict(quotelinks={})) | dict(t_report='')
    return template_search_post_t.render(**post_t)
