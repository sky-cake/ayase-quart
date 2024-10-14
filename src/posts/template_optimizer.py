from enum import StrEnum
from html import escape

from configs import media_conf
from posts.capcodes import Capcode
from utils.timestamps import ts_2_formatted

IMAGE_URI = media_conf.get('image_uri')
THUMB_URI = media_conf.get('thumb_uri')

class MediaType(StrEnum):
    image = 'image'
    thumb = 'thumb'


def pre_html_comment(post: str):
    pass


def post_html_comment(comment: str):
    pass


needed_keys = {
    'num',
    'ts_unix',
    'board_shortname',
    'quotelinks',
    'comment',
}


def wrap_post_t(post: dict):
    esc_user_data(post)
    set_links(post)
    post.update(
        dict(
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
        )
    )
    return post


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
cc_t_unknown = lambda capcode: f'<strong class="capcode hand id_unknown" title="Highlight posts by Unknown Capcode">## {capcode}</strong>'


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
    if not media_filename or not THUMB_URI or not IMAGE_URI:
        return ''

    uri = THUMB_URI

    if media_type == MediaType.image:
        uri = IMAGE_URI

    return f'{uri.format(board_shortname=board).rstrip('/')}/{media_filename[0:4]}/{media_filename[4:6]}/{media_filename}'


def get_gallery_media_t(post: dict):
    if not (media_filename := post['media_filename']):
        return ''
    ext = media_filename.rsplit('.', 1)[-1]
    media_orig = post['media_orig']
    preview_orig = post['preview_orig']
    md5h = post['media_hash']
    board = post['board_shortname']
    full_src = get_media_path(media_orig, board, MediaType.image)
    thumb_src = get_media_path(preview_orig, board, MediaType.thumb)
    classes = ['replyImg', 'postImg']
    if post['spoiler']:
        classes.append('spoiler')
    return f"""
		<img
			src="{thumb_src}"
			class="{" ".join(classes)}"
			data-media_hash="{ md5h }"
			width="{ post['preview_w'] }"
			height="{ post['preview_h'] }"
			loading="lazy"
			data-ext="{ext}"
			data-thumb_src="{thumb_src}"
			data-full_media_src="{full_src}"
			onclick="expandMedia(this)"
			onerror="pointToOtherMediaOnError(this)"
			data-expanded="false"
		/>
	"""


def get_media_t(post: dict):
    if not (media_filename := post['media_filename']):
        return ''
    ext = media_filename.rsplit('.', 1)[-1]
    media_orig = post['media_orig']
    preview_orig = post['preview_orig']
    num = post['num']
    md5h = post['media_hash']
    board = post['board_shortname']
    spoiler = 'Spoiler,' if post['spoiler'] else ''
    full_src = get_media_path(media_orig, board, MediaType.image)
    thumb_src = get_media_path(preview_orig, board, MediaType.thumb)
    classes = ['replyImg', 'postImg']
    if post['spoiler']:
        classes.append('spoiler')
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
        <a class="fileThumb">
			<img
				src="{thumb_src}"
				class="{" ".join(classes)}"
				data-media_hash="{ md5h }"
				width="{ post['preview_w'] }"
				height="{ post['preview_h'] }"
				loading="lazy"
				data-ext="{ext}"
				data-thumb_src="{thumb_src}"
				data-full_media_src="{full_src}"
				onclick="expandMedia(this)"
				onerror="pointToOtherMediaOnError(this)"
				data-expanded="false"
			/>
        </a>
    </div>
	"""


def set_links(post: dict):
    board = post['board_shortname']
    num = post['num']
    thread = post['op_num']
    post['t_thread_link'] = f'/{board}/thread/{thread}'
    post['t_post_link'] = f'/{board}/thread/{thread}#p{num}'


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
    <span class="dateTime postNum" data-utc="{timestamp}">
        {ts_2_formatted(timestamp)}
        <a href="#{post['num']}" title="Link to this post">No. {post['num']}</a>
    </span>
	"""


def get_exif_title(post: dict):
    if not (exif := post.get('exif')):
        return ''
    return f'title="Exif: {exif}"'


def get_poster_hash_t(post: dict):
    if not (poster_hash := post.get('poster_hash')):
        return ''
    return f'<span class="posteruid id_{poster_hash}">(ID: <a title="." href="#">{poster_hash}</a>) </span>'


def get_since4pass_t(post: dict):
    if not (since4pass := post.get('since4pass')):
        return ''
    return f'<span class="n-pu" title="Pass user since {since4pass}."></span>'


def get_filedeleted_t(post: dict):
    if not post.get('deleted'):
        return ''
    msg = f'deleted on {ts_2_formatted(del_time)}' if (del_time := post.get('ts_expired')) else 'prematurely deleted.'
    return f'<strong class="warning" title="This post was {msg}.">[Deleted]</strong>'


def get_header_t(post: dict):
    num = post['num']
    return f"""
	<div class="postContainer replyContainer" id="pc{num}">
	<div class="sideArrows" id="sa{num}">&gt;&gt;</div>

	<div id="p{num}" class="post reply">
	"""


def get_quotelink_t(post: dict):
    if not (quotelinks := post['quotelinks']):
        return ''
    board = post['board_shortname']
    quotelinks = ' '.join(f'<span class="quotelink"><a href="#p{ quotelink }" class="quotelink" data-board_shortname="{board}">&gt;&gt;{ quotelink }</a></span>' for quotelink in quotelinks)
    return f'<div id="bl_{post["num"]}" class="backlink">{quotelinks}</div>'


user_keys = (
    'name',
    'email',
)


def esc_user_data(post: dict):
    for user_key in user_keys:
        if val := post.get(user_key):
            post[user_key] = escape(val)


def get_name_t(post: dict):
    name_t = f"""
	<span class="name {post.get('capcode', '')}" {get_exif_title(post)}>{post['name']}</span>
	"""
    return email_wrap(post, name_t)


def email_wrap(post: dict, val: str):
    if (not (email := post.get('email'))) or email == 'noko':
        return val
    return f'<a href="mailto:{ email }">{val}</a>'
