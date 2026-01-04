from html import escape
from itertools import product

from configs import archive_conf, site_conf, mod_conf
from media import ext_is_video, get_image_path, get_thumb_path
from posts.capcodes import Capcode
from threads import get_thread_path
from utils.timestamps import ts_2_formatted
from enums import ImgTagClass

CANONICAL_HOST: str = archive_conf['canonical_host']
CANONICAL_NAME: str = archive_conf['canonical_name']
ANONYMOUS_NAME: str = site_conf['anonymous_username']


type QuotelinkD = dict[int, list[int]]


def wrap_post_t(post: dict):
    if not (post and post.get('num')): # Are there cases when post doesn't have a num?
        return post
    esc_user_data(post)
    set_links(post)
    post.update(
        t_sub=get_sub_t(post),
        t_cc=get_capcode_t(post),
        t_cc_class=get_cc_class_t(post),
        t_media=get_media_t(post),
        t_sticky=get_sticky_t(post),
        t_closed=get_closed_t(post),
        t_country=get_country_t(post),
        t_troll_country=get_troll_country_t(post),
        t_trip=get_trip_t(post),
        t_name=get_name_t(post),
        t_poster_hash=get_poster_hash_t(post),
        t_since4pass=get_since4pass_t(post),
        t_filedeleted=get_filedeleted_t(post),
        t_header=get_header_t(post),
        t_quotelink=get_quotelink_t(post),
        t_report=get_report_t(post),
    )
    return post


### BEGIN post_t
'''
For threads with large amounts of posts (1.5k+), things are slow (the crisis in question)
Threads are the only pages where we can't limit the amount of data on the page via pagination
The normal path should still be used everywhere else, ex:
    search results
    index & catalog view
    hovers

So I made a render_wrapped_post_t_thread that can switch for us
    If it's a plain jane reply post, we use the express lane:
        render_post_t_basic(post)
    Otherwise, we use the normal path:
        render_wrapped_post_t(wrap_post_t(post))

Other child functions had to be re-implemented for speed as well
    They are all suffixed with _thread

Anything that would complexify the templating is not "plain jane":
    ops, mod/admin capcodes, sticky, locked, deleted, tripcodes, emails, etc...

Despite media posts being complex, they return an empty string early if there is no media
    So we don't need to consider them as special
'''

def set_posts_quotelinks(posts: list[dict], post_2_quotelinks: QuotelinkD):
    for post in posts:
        post['quotelinks'] = post_2_quotelinks.get(post['num'], [])

rare_keys = (
    # 'media_filename', # not needed, get_media_t_thread exits early
    'title',
    'op',
    'sticky',
    'locked',
    'deleted',
    'poster_country',
    'troll_country',
    'poster_hash',
    'since4pass',
    'trip',
    'capcode', # should be last
)
def render_wrapped_post_t_thread(post: dict):
    rare_vals = [post.get(k) for k in rare_keys]
    if rare_vals[-1] == 'N': # in asagi, N is normal people capcode, which evals to true
        rare_vals[-1] = None

    # include_view_link should only be False on the /thread endpoint

    if not any(rare_vals): # basic text/image reply post
        esc_user_data(post) # not sure this is the correct logic...
        return render_post_t_basic(post)

    # anything remotely special uses official wrap_post_t
    return render_wrapped_post_t(wrap_post_t(post), include_view_link=False)


def get_posts_t_thread(posts: list[dict], post_2_quotelinks: QuotelinkD):
    set_posts_quotelinks(posts, post_2_quotelinks)
    return ''.join(render_wrapped_post_t_thread(p) for p in posts)


def render_post_t_basic(post: dict, include_view_link: bool=True):
    num = post['num']
    thread_num = post['thread_num']
    comment = post['comment']
    board = post['board_shortname']
    ts_unix = post['ts_unix']
    quotelinks_t = get_quotelink_t_thread(num, board, thread_num, post['quotelinks'])
    media_t = get_media_t_thread(post, num, board)
    post_path_t = get_post_path(board, thread_num, num)
    report_t = get_report_t(post)

    return f'''<div id="pc{num}"><div class="sideArrows"></div><div id="p{num}" class="post reply">
    <div class="postInfo" id="pi{num}">
        <b class="inblk">/{board}/</b> <span class="name N">{ANONYMOUS_NAME}</span>
        <span class="dateTime inblk" data-utc="{ts_unix}"></span> <a href="/{post_path_t}">No.{num}</a>
        {report_t}[<a class="sourcelink" href="{CANONICAL_HOST}/{post_path_t}" rel="noreferrer" target="_blank"></a>]
    </div>
    {media_t}<blockquote class="postMessage" id="m{num}">{comment}</blockquote>{quotelinks_t}
</div></div>'''


def get_quotelink_t_thread(num: int, board: str, thread_num: int, quotelinks: list[int]):
    if not quotelinks:
        return ''
    quotelink_gen = (
        f'<a href="/{get_post_path(board, thread_num, quotelink)}" class="quotelink inblk" data-board="{board}">&gt;&gt;{quotelink}</a>'
        for quotelink in quotelinks
    )
    return f'<div id="bl_{num}" class="clear_both backlink">Replies: {" ".join(quotelink_gen)}</div>'


def get_post_path(board: str, thread_num: int, num: int) -> str:
    return f'{get_thread_path(board, thread_num)}#p{num}'


def get_media_t_thread(post: dict, num: int, board: str):
    if not (media_filename := post['media_filename']):
        return ''

    media_orig = post['media_orig']
    preview_orig = post['preview_orig']
    md5h = post['media_hash']

    is_spoiler = post['spoiler']
    spoiler = 'Spoiler,' if is_spoiler else ''

    full_src = get_image_path(board, media_orig)
    thumb_src = get_thumb_path(board, preview_orig)

    return f"""<div class="file" id="f{num}">
        <div class="fileText" id="fT{num}">
            File: <a href="{full_src}" title="{media_orig}">{media_filename}</a>
            (<span title="{md5h}">{spoiler}{media_metadata_t(post['media_size'], post['media_w'], post['media_h'])}</span>)
        </div>
        {get_media_img_t(post, full_src=full_src, thumb_src=thumb_src)}
    </div>"""

### END post_t

def get_posts_t(posts: list[dict], post_2_quotelinks: QuotelinkD) -> str:
    set_posts_quotelinks(posts, post_2_quotelinks)
    posts_t = ''.join(render_wrapped_post_t(wrap_post_t(p)) for p in posts)
    return posts_t


def get_report_t(post: dict) -> str:
    if not mod_conf.get('enabled', False):
        return ''
    return f"""[<button class="rbtn" report_url="/report/{post['board_shortname']}/{post['thread_num']}/{post['num']}">Report</button>] """


def get_sub_t(post: dict):
    if title := post['title']:
        return f'<span class="subject">{title}</span>'
    return ''


cc_class = dict(
    A='capcodeAdmin',
    F='capcodeFounder',
    M='capcodeMod',
    D='capcodeDeveloper',
    G='capcodeManager',
    V='capcodeVerified',
)


def get_cc_class_t(post: dict):
    return cc_class.get(post['capcode'], '')


cc_t_admin = f'<strong class="capcode hand id_admin" title="Highlight posts by Administrators">## Admin</strong> <img src="/static/images/adminicon.gif" alt="Admin Icon" title="This user is a {CANONICAL_NAME} Administrator." class="identityIcon retina">'
cc_t_founder = f'<strong class="capcode hand id_founder" title="Highlight posts by the Founder">## Founder</strong> <img src="/static/images/foundericon.gif" alt="Founder Icon" title="This user is the {CANONICAL_NAME} Founder." class="identityIcon retina">'
cc_t_moderator = f'<strong class="capcode hand id_moderator" title="Highlight posts by Moderators">## Mod</strong> <img src="/static/images/modicon.gif" alt="Mod Icon" title="This user is a {CANONICAL_NAME} Moderator." class="identityIcon retina">'
cc_t_dev = f'<strong class="capcode hand id_developer" title="Highlight posts by Developers">## Developer</strong> <img src="/static/images/developericon.gif" alt="Developer Icon" title="This user is a {CANONICAL_NAME} Developer." class="identityIcon retina">'
cc_t_manager = f'<strong class="capcode hand id_manager" title="Highlight posts by Managers">## Manager</strong> <img src="/static/images/managericon.gif" alt="Manager Icon" title="This user is a {CANONICAL_NAME} Manager." class="identityIcon retina">'
cc_t_verified = '<strong class="capcode hand id_verified" title="Highlight posts by Verified Users">## Verified</strong>'
def cc_t_unknown(cc):
    return f'<strong class="capcode hand id_unknown" title="Highlight posts by Unknown Capcode">## {cc}</strong>'


def get_capcode_t(post: dict) -> str:
    cc: Capcode = post['capcode']
    match cc:
        case Capcode.user:
            return ''
        case Capcode.moderator:
            return cc_t_moderator
        case Capcode.verified:
            return cc_t_verified
        case Capcode.admin:
            return cc_t_admin
        case Capcode.founder:
            return cc_t_founder
        case Capcode.dev:
            return cc_t_dev
        case Capcode.manager:
            return cc_t_manager
        case _:
            return cc_t_unknown(cc)


kb_d = 1024
mb_d = 1024 * 1024
mb_junc = 1048576


def media_metadata_t(media_size: int, media_w: int, media_h: int):
    if media_size >= mb_junc:
        return f'{media_size / mb_d :.2f} MB, {media_w}x{media_h}'
    return f'{media_size / kb_d :.1f} KB, {media_w}x{media_h}'

def make_imgclassbf_lu() -> dict[int, str]:
    product_iter = (
        tuple(ImgTagClass(1 << i) for i, enabled in enumerate(combination) if enabled)
        for combination in product((True, False), repeat=len(ImgTagClass))
    )
    return {
        sum(flags): ' '.join(f.name for f in flags)
        for flags in product_iter
    }

imgclass_lu = make_imgclassbf_lu()
def get_media_img_t(post: dict, full_src: str=None, thumb_src: str=None, is_search=False, is_catalog=False):
    """Will render image with object-fit: cover by default"""

    if not (media_filename := post['media_filename']):
        return ''

    ext = media_filename.rsplit('.', 1)[-1]
    is_video = ext_is_video(ext)

    board = post['board_shortname']

    classes: int = 0 # bitfield/flags
    if post['spoiler']:
        classes += ImgTagClass.spoiler
    if not is_catalog:
        classes += ImgTagClass.mtog
    classes += ImgTagClass.is_video if is_video else ImgTagClass.is_image

    if full_src is None:
        full_src = get_image_path(board, post['media_orig'])
    if thumb_src is None:
        thumb_src = get_thumb_path(board, post['preview_orig'])

    _id = f'{post['board_shortname']}{post['num']}media'

    media_link = f"""<span class="c{ext}">{ext}</span> [<a href="/{board}/thread/{post['thread_num']}#p{post['num']}" rel="noreferrer" target="_blank" class="click">Post</a>]""" if is_search and not is_catalog else ''
    mtog = f"""[<span class="mtog play click">Play</span>]""" if is_video and not is_catalog else ''
    br = '<br>' if media_link or mtog else ''
    return f"""<div class="media_cont fileThumb">{media_link}{mtog}{br}
<img loading="lazy" src="{thumb_src}" width="{ post['preview_w'] }" height="{ post['preview_h'] }"
  id="{_id}" class="{imgclass_lu[classes]}" data-expanded="false" data-ext="{ext}"
  data-full_media_src="{full_src}" data-thumb_src="{thumb_src}"
/></div>"""


def get_media_t(post: dict):
    if not (media_filename := post['media_filename']):
        return ''

    media_orig = post['media_orig']
    preview_orig = post['preview_orig']
    num = post['num']
    md5h = post['media_hash']
    board = post['board_shortname']
    spoiler = 'Spoiler,' if post['spoiler'] else ''

    full_src = get_image_path(board, media_orig)
    thumb_src = get_thumb_path(board, preview_orig)

    return f"""
	<div class="file" id="f{num}">
        <div class="fileText" id="fT{num}">
            File: <a href="{full_src}" title="{media_orig}">{media_filename}</a>
            (<span title="{md5h}">{spoiler}{media_metadata_t(post['media_size'], post['media_w'], post['media_h'])}</span>)
        </div>
        {get_media_img_t(post, full_src=full_src, thumb_src=thumb_src)}
    </div>
	"""


def set_links(post: dict):
    board = post['board_shortname']
    num = post['num']
    thread_num = post['thread_num']
    thread_path = get_thread_path(board, thread_num)
    post_path = get_post_path(board, thread_num, num)
    post['t_thread_link_rel'] = thread_path
    post['t_thread_link_src'] = f'{CANONICAL_HOST}/{thread_path}'
    post['t_post_link_rel'] = post_path
    post['t_post_link_src'] = f'{CANONICAL_HOST}/{post_path}'


sticky_t = '<img src="/static/images/sticky.gif" alt="Sticky" title="Sticky" class="stickyIcon retina">'
def get_sticky_t(post: dict):
    return sticky_t if post.get('sticky') else ''


closed_t = '<img src="/static/images/closed.gif" alt="Closed" title="Closed" class="closedIcon retina">'
def get_closed_t(post: dict):
    return closed_t if post.get('locked') else ''


def get_country_t(post: dict):
    if not (poster_country := post['poster_country']):
        return ''
    return f'<span title="{poster_country}" class="flag flag-{poster_country.lower()}"></span>'


def get_troll_country_t(post: dict):
    if not (troll_country := post.get('troll_country')):
        return ''
    return f'<span title="{post["poster_country"]}" class="flag-pol2 flag-{troll_country.lower()}"></span>'


def get_trip_t(post: dict):
    if not (trip := post['trip']):
        return ''
    return f'<span class="postertrip">{trip}</span>'


def get_exif_title(post: dict):
    if not (exif := post.get('exif')):
        return ''
    return f'title="Exif: {exif}"'


def get_poster_hash_t(post: dict):
    if not (poster_hash := post.get('poster_hash')):
        return ''
    return f'(ID: {poster_hash})'


def get_since4pass_t(post: dict):
    if not (since4pass := post.get('since4pass')):
        return ''
    return f'<span class="n-pu" title="Pass user since {since4pass}."></span>'


def get_filedeleted_t(post: dict):
    if not (deleted := post.get('deleted')):
        return ''
    msg = f'deleted on {ts_2_formatted(del_time)}' if (del_time := post.get('ts_expired')) else 'prematurely deleted.'
    deleted = '[Deleted]' if deleted == 1 else escape(deleted)
    return f'<strong class="warning" title="This post was {msg}.">{deleted}</strong>'


def get_header_t(post: dict):
    num = post['num']
    return f"""<div id="pc{num}">{'<div class="sideArrows"></div>' if not post['op'] else ''} <div id="p{num}" class="post reply">"""


def get_quotelink_t(post: dict):
    if not (quotelinks := post['quotelinks']):
        return ''
    board = post['board_shortname']
    thread_num = post['thread_num']
    quotelinks = ' '.join(f'<a href="/{get_post_path(board, thread_num, quotelink)}" class="quotelink inblk" data-board="{board}">&gt;&gt;{quotelink}</a>' for quotelink in quotelinks)
    return f'<div id="bl_{post["num"]}" class="backlink clear_both">Replies: {quotelinks}</div>'


def esc_user_data(post: dict):
    post['name'] = escape(name) if (name := post.get('name')) else ANONYMOUS_NAME
    post['email'] = escape(email) if (email := post.get('email')) else ''


def get_name_t(post: dict):
    name_t = f"""<span class="name {post.get('capcode', '')}" {get_exif_title(post)}>{post.get('name', ANONYMOUS_NAME)}</span>"""
    return email_wrap(post, name_t)


def email_wrap(post: dict, val: str):
    email = post.get('email')
    if not email or email == 'noko':
        return val
    return f'<a href="mailto:{ email }">{val}</a>'

op_label = '<strong class="op_label">OP</strong>'
def render_wrapped_post_t(wpt: dict, include_view_link: bool=True): # wrapped_post_t
    is_op = wpt['op']
    num = wpt['num']
    ts_unix = wpt['ts_unix']

    return f"""
    { wpt['t_header'] }
    { wpt['t_media'] if is_op else '' }
    <div class="postInfo" id="pi{num}">
        <span class="inblk"><b>/{wpt['board_shortname']}/</b> { op_label if is_op else '' }</span>
        { wpt['t_filedeleted'] }
        { wpt['t_sub'] }
        { wpt['t_name'] }
        <span class="nameBlock { wpt['t_cc_class'] }">
            { wpt['t_cc'] }
        </span>{ wpt['t_poster_hash'] }
        { wpt['t_since4pass'] }
        { wpt['t_country'] }
        { wpt['t_troll_country'] }
        <span class="dateTime inblk" data-utc="{ts_unix}"></span>
        <a href="/{wpt['t_post_link_rel']}">No.{num}</a>
        { wpt['t_sticky'] + wpt['t_closed'] if is_op else '' }
        <span class="inblk">
        { wpt['t_report'] } [<a href="{ wpt['t_thread_link_src'] if is_op else wpt['t_post_link_src'] }" rel="noreferrer" target="_blank">Source</a>]
        </span>
    </div>
    <div>
        { wpt['t_media'] if not is_op else '' }
        <blockquote class="postMessage" id="m{num}">{wpt['comment']}</blockquote>
    </div>
    { wpt['t_quotelink'] }
    </div>
    </div>
    """


def render_catalog_card(wpt: dict, show_nuke_btn: bool=False, csrf_input: str=None) -> str: # a thread card is just the op post
    num = wpt['num']
    board = wpt['board_shortname']
    title_t = get_title_t(wpt)
    ts_unix = wpt['ts_unix']
    nl = '<br>' if wpt['t_cc'] else ''
    thread_path = get_thread_path(board, num)
    post_path = get_post_path(board, num, num)

    nuke_btn = ''
    if show_nuke_btn and csrf_input:
        # no js required
        nuke_btn = f"""[<form class="actionform form" action="/nuke/{board}/{num}" method="post">{csrf_input}<button class="rbtn" type="submit">Nuke</button></form>]"""

    return f"""
    <div id="{num}" class="thread doc_id_{num}" tabindex="0">
        <div class="post_data">
            <div class="post_controls">
                {nuke_btn} /{board}/ [<a href="{ wpt['t_thread_link_src'] }" class="btnr parent" rel="noreferrer" target="_blank">Source</a>]
            </div>
            { wpt['t_cc'] }{nl}
            <div class="dateTime inblk" data-utc="{ts_unix}"></div>
            <div><a href="/{post_path}" data-function="highlight" data-post="{num}">No. {num}</a>{get_thread_stats_t(wpt)}</div>
        </div>
    <a href="/{thread_path}" rel="noreferrer">{get_media_img_t(wpt, is_catalog=True)}</a>
    <div class="teaser">
        { title_t }
        { wpt.get('comment', '')}
    </div>
    </div>
    """


def get_title_t(thread: dict):
    if not (title := thread['title']):
        return ''
    return f"""<span class="post_title">{title}</span>"""

# almost same as threads.render_thread_stats...
def get_thread_stats_t(thread: dict) -> str:
    posters_t = f'/ P: <b>{posters}</b>' if (posters := thread.get('posters')) else ''
    return f"""
    <span class="meta">
        R: <b>{ thread['nreplies'] }</b> / I: <b>{ thread['nimages'] }</b> {posters_t}
    </span>
    """

def get_thread_sticky_locked_t(thread: dict) -> str:
    locked = thread['locked']
    sticky = thread['sticky']
    if not any((locked, sticky)):
        return ''
    sticky_t = '<span title="Sticky" class="threadIcon stickyIconCatalog"></span>' if sticky else ''
    locked_t = '<span title="Closed" class="threadIcon closedIconCatalog"></span>' if locked else ''
    return f"""
    <div class="threadIcons">
        {sticky_t}{locked_t}
    </div>
    """
