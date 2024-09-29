from enum import StrEnum
from html import escape

from configs import CONSTS


class MediaType(StrEnum):
    image = 'image'
    thumb = 'thumb'


def pre_html_comment(post: str):
    pass


def post_html_comment(comment: str):
    pass


needed_keys = {
    'no',
    'time',
    'now',
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
    if sub := post['sub']:
        return f'<span class="subject">{sub}</span>'
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
    cc = post.get('capcode')
    match cc:
        case None:
            return ''
        case 'V':
            return cc_t_verified
        case 'A':
            return cc_t_admin
        case 'F':
            return cc_t_founder
        case 'M':
            return cc_t_moderator
        case 'D':
            return cc_t_dev
        case 'G':
            return cc_t_manager
        case _:
            return cc_t_unknown(cc)


kb_d = 1024
mb_d = 1024 * 1024
mb_junc = 1048576


def media_metadata_t(fsize: int, w: int, h: int):
    if fsize >= mb_junc:
        return f'{fsize / mb_d :.2f} MB, {w}x{h}'
    return f'{fsize / kb_d :.1f} KB, {w}x{h}'


def get_media_path(filename: str, board: str, media_type: MediaType) -> str:
    if not filename or not CONSTS.thumb_uri or not CONSTS.image_uri:
        return ''

    uri = CONSTS.thumb_uri

    if media_type == MediaType.image:
        uri = CONSTS.image_uri

    return f'{uri.format(board_shortname=board).strip('/')}/{filename[0:4]}/{filename[4:6]}/{filename}'


def get_gallery_media_t(post: dict):
    if not post['filename']:
        return ''
    ext = post['ext']
    asagi_filename = post['asagi_filename']
    asagi_preview_filename = post['asagi_preview_filename']
    md5h = post['md5']
    board = post['board_shortname']
    full_src = get_media_path(asagi_filename, board, MediaType.image)
    thumb_src = get_media_path(asagi_preview_filename, board, MediaType.thumb)
    classes = ['replyImg', 'postImg']
    if post['spoiler']:
        classes.append('spoiler')
    return f"""
		<img
			src="{thumb_src}"
			class="{" ".join(classes)}"
			data-md5="{ md5h }"
			width="{ post['tn_w'] }"
			height="{ post['tn_h'] }"
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
    if not (filename := post['filename']):
        return ''
    ext = post['ext']
    asagi_filename = post['asagi_filename']
    asagi_preview_filename = post['asagi_preview_filename']
    no = post['no']
    md5h = post['md5']
    board = post['board_shortname']
    spoiler = 'Spoiler,' if post['spoiler'] else ''
    full_src = get_media_path(asagi_filename, board, MediaType.image)
    thumb_src = get_media_path(asagi_preview_filename, board, MediaType.thumb)
    classes = ['replyImg', 'postImg']
    if post['spoiler']:
        classes.append('spoiler')
    return f"""
	<div class="file" id="f{no}">
        <div class="fileText" id="fT{no}">
            File:
            <a href="{full_src}" title="{asagi_filename}">{filename}.{ext}</a>
            (<span title="{md5h}">
                {spoiler}
                {media_metadata_t(post['fsize'], post['w'], post['h'])}
            </span>)
        </div>
        <a class="fileThumb">
			<img
				src="{thumb_src}"
				class="{" ".join(classes)}"
				data-md5="{ md5h }"
				width="{ post['tn_w'] }"
				height="{ post['tn_h'] }"
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
    no = post['no']
    thread = resto if (resto := post['resto']) else no
    post['t_thread_link'] = f'/{board}/thread/{thread}'
    post['t_post_link'] = f'/{board}/thread/{thread}#p{no}'


sticky_t = '<img src="/static/images/sticky.gif" alt="Sticky" title="Sticky" class="stickyIcon retina">'


def get_sticky_t(post: dict):
    return sticky_t if post.get('sticky') else ''


closed_t = '<img src="/static/images/closed.gif" alt="Closed" title="Closed" class="closedIcon retina">'


def get_closed_t(post: dict):
    return closed_t if post.get('closed') else ''


def get_country_t(post: dict):
    if not (country := post['country']):
        return ''
    return f'<span title="{country}" class="flag flag-{country.lower()}"></span>'


def get_troll_country_t(post: dict):
    if not (troll_country := post.get('troll_country')):
        return ''
    return f'<span title="{post["country"]}" class="flag-pol2 flag-{troll_country.lower()}"></span>'


def get_trip_t(post: dict):
    if not (trip := post['trip']):
        return ''
    return f'<span class="postertrip">{trip}</span>'


def get_mobile_t(post: dict):
    return f"""
	<span class="nameBlock">
        <span class="name">{post['name']}</span>
        <br>
    </span>
    <span class="dateTime postNum" data-utc="{post['time']}">
        {post['now']}
        <a href="#{post['no']}" title="Link to this post">No. {post['no']}</a>
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
    if not post.get('filedeleted'):
        return ''
    msg = f'deleted on {del_time}' if (del_time := post.get('deleted_time')) else 'prematurely deleted.'
    return f'<strong class="warning" title="This post was {msg}.">[Deleted]</strong>'


def get_header_t(post: dict):
    no = post['no']
    return f"""
	<div class="postContainer replyContainer" id="pc{no}">
	<div class="sideArrows" id="sa{no}">&gt;&gt;</div>

	<div id="p{no}" class="post reply">
	"""


def get_quotelink_t(post: dict):
    if not (quotelinks := post['quotelinks']):
        return ''
    board = post['board_shortname']
    quotelinks = ' '.join(f'<span class="quotelink"><a href="#p{ quotelink }" class="quotelink" data-board_shortname="{board}">&gt;&gt;{ quotelink }</a></span>' for quotelink in quotelinks)
    return f'<div id="bl_{post["no"]}" class="backlink">{quotelinks}</div>'


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
