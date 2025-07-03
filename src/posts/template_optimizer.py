from enum import StrEnum
from html import escape
from functools import cache, lru_cache

from configs import media_conf
from posts.capcodes import Capcode
from utils.timestamps import ts_2_formatted

THUMB_URI: str = media_conf.get('thumb_uri', '').rstrip('/')
IMAGE_URI: str = media_conf.get('image_uri', '').rstrip('/')
BOARDS_WITH_THUMB: tuple[str] = tuple(media_conf['boards_with_thumb'])
BOARDS_WITH_IMAGE: tuple[str] = tuple(media_conf['boards_with_image'])
TRY_FULL_SRC_TYPE_ON_404: bool = media_conf.get('try_full_src_type_on_404', False)

# TODO: move these 2 to config
ANONYMOUS_NAME = 'Anonymous'
CANONICAL_HOST = 'https://boards.4chan.org'.rstrip('/')

type QuotelinkD = dict[int, list[int]]

class MediaType(StrEnum):
    image = 'image'
    thumb = 'thumb'

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
        t_mobile=get_mobile_t(post),
        t_name=get_name_t(post),
        t_poster_hash=get_poster_hash_t(post),
        t_since4pass=get_since4pass_t(post),
        t_filedeleted=get_filedeleted_t(post),
        t_header=get_header_t(post),
        t_quotelink=get_quotelink_t(post),
        t_report=get_report_t(post),
    )
    if post.get('comment') is None:
        post['comment'] = ''
    return post

### BEGIN post_t crisis
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

    if not any(rare_vals): # basic text/image reply post
        esc_user_data(post) # not sure this is the correct logic...
        return render_post_t_basic(post)

    # anything remotely special uses official wrap_post_t
    return render_wrapped_post_t(wrap_post_t(post))

def get_posts_t_thread(posts: list[dict], post_2_quotelinks: QuotelinkD):
    set_posts_quotelinks(posts, post_2_quotelinks)
    return ''.join(render_wrapped_post_t_thread(p) for p in posts)

def render_post_t_basic(post: dict):
    num = post['num']
    thread_num = post['thread_num']
    comment = post['comment'] or ''
    board = post['board_shortname']
    ts_unix = post['ts_unix']
    quotelinks_t = get_quotelink_t_thread(num, board, post['quotelinks'])
    media_t = get_media_t_thread(post, num, board)
    post_path_t = get_post_path(board, thread_num, num)
    return f'''
    <div id="pc{num}">
        <div class="sideArrows">&gt;&gt;</div>
        <div id="p{num}" class="post reply">
            <div class="postInfoM mobile" id="pim{num}">
                <span class="nameBlock"><span class="name">{ANONYMOUS_NAME}</span><br></span>
                <span class="dateTime inblk" data-utc="{ts_unix}"></span>
                <a href="#{num}">No. {num}</a>
            </div>
            <div class="postInfo" id="pi{num}">
                <span class="inblk"><b>/{board}/</b></span>
                <span class="name N">{ANONYMOUS_NAME}</span>
                <span class="dateTime inblk" data-utc="{ts_unix}"></span>
                <span class="postNum"><a href="/{post_path_t}">No.{num}</a></span>
                <button class="btnlink" onclick="copy_link(this, '/{post_path_t}')">⎘</button>
                <span class="inblk">
                    [<button class="rbtn" report_url="/report/{board}/{thread_num}/{num}">Report</button>]
                    [<a href="/{post_path_t}" target="_blank">View</a>]
                    [<a href="{CANONICAL_HOST}/{post_path_t}" rel="noreferrer" target="_blank">Source</a>]
                </span>
            </div>
            <div>
                {media_t}
                <blockquote class="postMessage" id="m{num}">{comment}</blockquote>
            </div>
            <div style="clear:both;"></div>
            {quotelinks_t}
        </div>
    </div>
    '''

def get_quotelink_t_thread(num: int, board: str, quotelinks: list[int]):
    if not quotelinks:
        return ''
    quotelink_gen = (
        f'<span class="quotelink"><a href="#p{quotelink}" class="quotelink" data-board_shortname="{board}">&gt;&gt;{quotelink}</a></span>'
        for quotelink in quotelinks
    )
    return f'<div id="bl_{num}" class="backlink">Replies: {" ".join(quotelink_gen)}</div>'

@lru_cache(maxsize=2048)
def get_thread_path(board: str, thread_num: int) -> str:
    return f'{board}/thread/{thread_num}'

def get_post_path(board: str, thread_num: int, num: int) -> str:
    return f'{get_thread_path(board, thread_num)}#p{num}'

@cache
def board_has_image(board: str) -> bool:
    return board in BOARDS_WITH_IMAGE and IMAGE_URI

@cache
def board_has_thumb(board: str) -> bool:
    return board in BOARDS_WITH_THUMB and THUMB_URI

@cache
def get_image_baseuri(board: str) -> str:
    return IMAGE_URI.format(board_shortname=board)

@cache
def get_thumb_baseuri(board: str) -> str:
    return THUMB_URI.format(board_shortname=board)


@cache
def ext_is_image(ext: str) -> bool:
    return ext in ('jpg', 'jpeg', 'png', 'bmp', 'webp') # gifs not included

@cache
def ext_is_video(ext: str) -> bool:
    return ext in ('webm', 'mp4')

def get_media_t_thread(post: dict, num: int, board: str):
    if not (media_filename := post['media_filename']):
        return ''

    media_orig = post['media_orig']
    preview_orig = post['preview_orig']
    md5h = post['media_hash']

    is_spoiler = post['spoiler']
    spoiler = 'Spoiler,' if is_spoiler else ''
    classes = 'spoiler' if is_spoiler else ''

    full_src = get_image_path(board, media_orig)
    thumb_src = get_thumb_path(board, preview_orig)

    return f"""
	<div class="file" id="f{num}">
        <div class="fileText" id="fT{num}">
            File:
            <a href="{full_src}" title="{media_orig}">{media_filename}</a>
            (<span title="{md5h}">
                {spoiler}
                {media_metadata_t(post['media_size'], post['media_w'], post['media_h'])}
            </span>)
        </div>
        {get_media_img_t(post, full_src=full_src, thumb_src=thumb_src, classes=classes)}
    </div>
	"""

def get_image_path(board: str, filename: str) -> str:
    if not(filename and board_has_image(board)):
        return ''
    return f'{get_image_baseuri(board)}/{media_fs_partition(filename)}'

def get_thumb_path(board: str, filename: str) -> str:
    if not(filename and board_has_thumb(board)):
        return ''
    return f'{get_thumb_baseuri(board)}/{media_fs_partition(filename)}'

# should move to configs or somewhere else for customizability
def media_fs_partition(filename: str) -> str:
    return f'{filename[0:4]}/{filename[4:6]}/{filename}'

### END post_t crisis

def get_posts_t(posts: list[dict], post_2_quotelinks: QuotelinkD) -> str:
    set_posts_quotelinks(posts, post_2_quotelinks)
    posts_t = ''.join(render_wrapped_post_t(wrap_post_t(p)) for p in posts)
    return posts_t


def get_report_t(post: dict) -> str:
    return f"""[<button class="rbtn" report_url="/report/{post['board_shortname']}/{post['thread_num']}/{post['num']}">
        Report
    </button>]"""


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


cc_t_admin = '<strong class="capcode hand id_admin" title="Highlight posts by Administrators">## Admin</strong> <img src="/static/images/adminicon.gif" alt="Admin Icon" title="This user is a 4chan Administrator." class="identityIcon retina">'
cc_t_founder = '<strong class="capcode hand id_founder" title="Highlight posts by the Founder">## Founder</strong> <img src="/static/images/foundericon.gif" alt="Founder Icon" title="This user is the 4chan Founder." class="identityIcon retina">'
cc_t_moderator = '<strong class="capcode hand id_moderator" title="Highlight posts by Moderators">## Mod</strong> <img src="/static/images/modicon.gif" alt="Mod Icon" title="This user is a 4chan Moderator." class="identityIcon retina">'
cc_t_dev = '<strong class="capcode hand id_developer" title="Highlight posts by Developers">## Developer</strong> <img src="/static/images/developericon.gif" alt="Developer Icon" title="This user is a 4chan Developer." class="identityIcon retina">'
cc_t_manager = '<strong class="capcode hand id_manager" title="Highlight posts by Managers">## Manager</strong> <img src="/static/images/managericon.gif" alt="Manager Icon" title="This user is a 4chan Manager." class="identityIcon retina">'
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


def get_media_path(media_filename: str, board: str, media_type: MediaType) -> str:
    if not media_filename or not (THUMB_URI or IMAGE_URI):
        return ''

    uri = IMAGE_URI if media_type == MediaType.image else THUMB_URI

    return f'{uri.format(board_shortname=board)}/{media_fs_partition(media_filename)}'


def get_media_img_t(post: dict, full_src: str=None, thumb_src: str=None, classes: str=None, is_search=False, is_catalog=False):
    """Will render image with object-fit: cover by default"""

    if not (media_filename := post['media_filename']):
        return ''

    ext = media_filename.rsplit('.', 1)[-1]
    is_img = ext in ('jpg', 'jpeg', 'png') # gifs not included
    is_video = ext in ('webm', 'mp4')

    board = post['board_shortname']

    if classes is None:
        classes = 'cover spoiler' if post['spoiler'] else 'cover'
    if full_src is None:
        full_src = get_media_path(post['media_orig'], board, MediaType.image) if not BOARDS_WITH_IMAGE or board in BOARDS_WITH_IMAGE else ''
    if thumb_src is None:
        thumb_src = get_media_path(post['preview_orig'], board, MediaType.thumb) if not BOARDS_WITH_THUMB or board in BOARDS_WITH_THUMB else ''

    onerror = 'onerror="p2other(this)"' if TRY_FULL_SRC_TYPE_ON_404 and is_img else ''

    _id = f'{post['board_shortname']}{post['num']}media'

    media_link = f"""<span class="c{ext}">{ext}</span> [<a href="/{board}/thread/{post['thread_num']}#p{post['num']}" rel="noreferrer" target="_blank" class="click">Post</a>]""" if is_search and not is_catalog else ''
    media_togg = f"""[<span class="media_togg click" onclick="expandMedia(document.getElementById('{_id}'))">Play</span>]""" if is_video and not is_catalog else ''
    br = '<br>' if media_link or media_togg else ''
    onclick = '' if is_catalog else 'onclick="expandMedia(this)"'
    # data-media_hash="{ post['media_hash'] }" # not used by anything, so omitting
    return f"""<div class="media_cont fileThumb">{media_link}{media_togg}{br}
<img
  id="{_id}"
  src="{thumb_src}"
  data-full_media_src="{full_src}" data-thumb_src="{thumb_src}" data-ext="{ext}"
  class="{classes}"
  width="{ post['preview_w'] }" height="{ post['preview_h'] }"
  data-expanded="false"
  {onclick} {onerror}
  loading="lazy"
/>
</div>
"""


def get_media_t(post: dict):
    if not (media_filename := post['media_filename']):
        return ''

    media_orig = post['media_orig']
    preview_orig = post['preview_orig']
    num = post['num']
    md5h = post['media_hash']
    board = post['board_shortname']
    spoiler = 'Spoiler,' if post['spoiler'] else ''

    classes = 'spoiler' if post['spoiler'] else ''
    full_src = get_media_path(media_orig, board, MediaType.image) if board in BOARDS_WITH_IMAGE else ''
    thumb_src = get_media_path(preview_orig, board, MediaType.thumb) if board in BOARDS_WITH_THUMB else ''

    return f"""
	<div class="file" id="f{num}">
        <div class="fileText" id="fT{num}">
            File:
            <a href="{full_src}" title="{media_orig}">{media_filename}</a>
            (<span title="{md5h}">
                {spoiler}
                {media_metadata_t(post['media_size'], post['media_w'], post['media_h'])}
            </span>)
        </div>
        {get_media_img_t(post, full_src=full_src, thumb_src=thumb_src, classes=classes)}
    </div>
	"""


def set_links(post: dict):
    board = post['board_shortname']
    num = post['num']
    thread_num = post['thread_num']
    post['t_thread_link_rel'] = f'/{board}/thread/{thread_num}'
    post['t_thread_link_src'] = f'{CANONICAL_HOST}/{board}/thread/{thread_num}'
    post['t_post_link_rel'] = f'/{board}/thread/{thread_num}#p{num}'
    post['t_post_link_src'] = f'{CANONICAL_HOST}/{board}/thread/{thread_num}#p{num}'


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


def get_mobile_t(post: dict):
    timestamp = post['ts_unix']
    return f"""
	<span class="nameBlock">
        <span class="name">{post['name']}</span>
        <br>
    </span>
    <span class="dateTime inblk" data-utc="{timestamp}"></span>
    <a href="#{post['num']}">No. {post['num']}</a>
	"""


def get_exif_title(post: dict):
    if not (exif := post.get('exif')):
        return ''
    return f'title="Exif: {exif}"'


def get_poster_hash_t(post: dict):
    if not (poster_hash := post.get('poster_hash')):
        return ''
    return f'<span class="posteruid id_{poster_hash}">(ID: <a title="." href="#">{poster_hash}</a>)</span>'


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
    return f"""<div id="pc{num}"> {'<div class="sideArrows">&gt;&gt;</div>' if not post['op'] else ''} <div id="p{num}" class="post reply">"""


def get_quotelink_t(post: dict):
    if not (quotelinks := post['quotelinks']):
        return ''
    board = post['board_shortname']
    quotelinks = ' '.join(f'<span class="quotelink"><a href="#p{ quotelink }" class="quotelink" data-board_shortname="{board}">&gt;&gt;{ quotelink }</a></span>' for quotelink in quotelinks)
    return f'<div id="bl_{post["num"]}" class="backlink">Replies: {quotelinks}</div>'


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
def render_wrapped_post_t(wpt: dict): # wrapped_post_t
    is_op = wpt['op']
    num = wpt['num']
    ts_unix = wpt['ts_unix']
    return f"""
    { wpt['t_header'] }
    <div class="postInfoM mobile" id="pim{num}">
        { wpt['t_sub'] }
        { wpt['t_mobile'] }
    </div>
    { wpt['t_media'] if is_op else '' }
    <div class="postInfo" id="pi{num}">
        <span class="inblk"><b>/{wpt['board_shortname']}/</b> { op_label if is_op else '' }</span>
        { wpt['t_filedeleted'] }
        { wpt['t_sub'] }
        { wpt['t_name'] }
        <span class="nameBlock { wpt['t_cc_class'] }">
            { wpt['t_cc'] }
        </span>
        { wpt['t_poster_hash'] }
        { wpt['t_since4pass'] }
        { wpt['t_country'] }
        { wpt['t_troll_country'] }
        <span class="dateTime inblk" data-utc="{ts_unix}"></span>
        <span class="postNum">
            <a href="{wpt['t_post_link_rel']}">No.{num}</a>
            { wpt['t_sticky'] + wpt['t_closed'] if is_op else '' }
        </span>
        <button class="btnlink" onclick="copy_link(this, '{wpt['t_post_link_rel']}')">⎘</button>
        <span class="inblk">
        { wpt['t_report'] }
        [<a href="{ wpt['t_thread_link_rel'] if is_op else wpt['t_post_link_rel'] }" target="_blank">View</a>]
        [<a href="{ wpt['t_thread_link_src'] if is_op else wpt['t_post_link_src'] }" rel="noreferrer" target="_blank">Source</a>]
        </span>
    </div>
    <div>
        { wpt['t_media'] if not is_op else '' }
        <blockquote class="postMessage" id="m{num}">{wpt['comment']}</blockquote>
    </div>
    <div style="clear:both;"></div>
    { wpt['t_quotelink'] }
    </div>
    </div>
    """


def render_catalog_card(wpt: dict) -> str: # a thread card is just the op post
    num = wpt['num']
    board = wpt['board_shortname']
    title_t = get_title_t(wpt)
    ts_unix = wpt['ts_unix']
    classes = 'spoiler' if wpt['spoiler'] else ''
    nl = '<br>' if wpt['t_cc'] else ''

    return f"""
    <div id="{ num }" class="thread doc_id_{ num }" tabindex="0">
        <div class="post_data">
        /{board}/<br>
        <span class="post_controls">
            [<a href="/{ board }/thread/{ num }" class="btnr parent" >View</a>]
            [<a href="{CANONICAL_HOST}/{ board }/thread/{ num }" class="btnr parent" rel="noreferrer" target="_blank" >Source</a>]
        </span>
        { wpt['t_cc'] }{nl}
        <span class="dateTime inblk" data-utc="{ts_unix}"></span>
        <span class="postNum">
            <a href="/{ board }/thread/{ num }#p{ num }" data-function="highlight" data-post="{ num }">No. { num }</a>
        </span>
        </div>
    <a href="/{ board }/thread/{ num }" rel="noreferrer">{get_media_img_t(wpt, classes=classes, is_catalog=True)}</a>
    {get_thread_stats_t(wpt)}
    <div class="teaser">
        { title_t }
        { wpt.get('comment', '')}
    </div>
    </div>
    """


def render_catalog_card_archiveposting(wpt: dict) -> str: # a thread card is just the op post
    num = wpt['num']
    board = wpt['board_shortname']
    title_t = get_title_t(wpt)
    ts_unix = wpt['ts_unix']
    classes = 'spoiler' if wpt['spoiler'] else ''
    nl = '<br>' if wpt['t_cc'] else ''

    return f"""<div id="{ num }" class="form thread doc_id_{ num }" tabindex="0">
      <a href="/{ board }/thread/{ num }" class="btnr parent">
      <div class="post_data">
        { wpt['t_filedeleted'] }
        { wpt['t_cc'] }{nl}
        <span class="postNum">No. { num }</span>
        <span class="dateTime inblk" data-utc="{ts_unix}">{ts_2_formatted(ts_unix)}</span>
      </div>
      <a href="/{ board }/thread/{ num }" rel="noreferrer">{get_media_img_t(wpt, classes=classes, is_catalog=True)}</a>
      <div class="teaser">
        { title_t + '<br>' if title_t else '' }
        { wpt.get('comment', '')}
      </div>
      </a>
    </div>
    """


def get_posts_t_archiveposting(posts: list[dict], post_2_quotelinks: QuotelinkD) -> str:
    set_posts_quotelinks(posts, post_2_quotelinks)
    posts_t = ''.join(render_wrapped_post_t_archiveposting(wrap_post_t(p)) for p in posts)
    return posts_t


def render_wrapped_post_t_archiveposting(wpt: dict): # wrapped_post_t
    is_op = wpt['op']
    num = wpt['num']
    ts_unix = wpt['ts_unix']
    thread_num_label = f'<div id="op_thread_num" data-num="{num}" class="hidden"></div>' if is_op else ''
    return f"""{ thread_num_label }
    { wpt['t_header'] }
    <div class="postInfoM mobile" id="pim{num}">
        { wpt['t_sub'] }
        { wpt['t_mobile'] }
    </div>
    <div class="postInfo" id="pi{num}">
        { op_label if is_op else '' }
        { wpt['t_filedeleted'] }
        { wpt['t_sub'] }
        { wpt['t_name'] }
        <span class="nameBlock { wpt['t_cc_class'] }">
            { wpt['t_cc'] }
        </span>
        <span class="dateTime inblk" data-utc="{ts_unix}">{ts_2_formatted(ts_unix)}</span>
        <span class="postNum">
            <a href="{wpt['t_post_link_rel']}">No.{num}</a>
            { wpt['t_sticky'] + wpt['t_closed'] if is_op else '' }
        </span>
        <button class="btnlink" onclick="copy_link(this, '{wpt['t_post_link_rel']}')">⎘</button>
        <span class="inblk">
        { wpt['t_report'] }
        </span>
    </div>
    <div>
        { wpt['t_media'] if not is_op else '' }
        <blockquote class="postMessage" id="m{num}">{wpt.get('comment', '') if wpt.get('comment', '') else ''}</blockquote>
    </div>
    <div style="clear:both;"></div>
    { wpt['t_quotelink'] }
    </div>
    </div>
    """

def get_title_t(thread: dict):
    if not (title := thread.get('title', '')):
        return ''
    return f"""<span class="post_title">{ title }</span>"""

# almost same as threads.render_thread_stats...
def get_thread_stats_t(thread: dict) -> str:
    return f"""
    <div class="meta">
        Replies: <b>{ thread['nreplies'] }</b> / Images: <b>{ thread['nimages'] }</b> / Posters: <b>{ thread.get('posters', '?') }
        </b>
    </div>
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
