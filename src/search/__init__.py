import mimetypes
import os
from time import perf_counter, time_ns

from PIL import Image
from quart import abort, current_app, flash
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest

from asagi_converter import get_board_2_nums_from_board_2_filenames, search_posts
from configs import index_search_conf, tag_conf, vanilla_search_conf, media_conf
from enums import SearchType
from search.post_metadata import board_2_int
from search.providers import get_index_search_provider
from search.query import IndexSearchQuery, get_index_search_query
from tagging.db import get_board_2_media_origs_by_tag_ids, get_image_count, make_tag_data, get_image_filenames_by_sha256_and_boards
from tagging.enums import SafeSearch
from tagging.utils import get_sha256_from_bytesio_and_write
from utils import make_src_path, Perf
import asyncio


if tag_conf['enabled'] and tag_conf['allow_file_search']:
    from timm.data import create_transform, resolve_data_config

    from tagging.processor import load_model, process_images_from_imgs
    from tagging.utils import get_torch_device
    import torch

    print(f'{torch.cuda.is_available()=}')
    print(f'{torch.cuda.device_count()=}')

    print('Loading model, started')
    tag_data = make_tag_data()
    torch_device = get_torch_device(tag_conf['use_cpu'])
    model = load_model(tag_conf['tag_model_repo_id']).to(torch_device, non_blocking=True)
    transform = create_transform(**resolve_data_config(model.pretrained_cfg, model=model))
    print('Loading model, done')


async def _get_posts_and_total_hits_fts(form_data: dict) -> tuple[list[dict], int]:
    if not isinstance(form_data['boards'], list):
        raise ValueError(form_data['boards'])

    index_searcher = get_index_search_provider()
    board_ints = [board_2_int(board) for board in form_data['boards']]

    if form_data['op_title'] or form_data['op_comment']:
        q = IndexSearchQuery(
            op=True,
            comment=form_data['op_comment'] if form_data['op_comment'] else None,
            title=form_data['op_title'] if form_data['op_title'] else None,
            boards=board_ints,
            hits_per_page=index_search_conf['max_hits'], # max_hits due to facet search
        )
        boards_2_threadnums, total_threads_hits = await index_searcher.search_posts_get_thread_nums(q)
        posts = []
        total_hits = 0
        for board, thread_nums in boards_2_threadnums.items():
            # must go one board at a time to maintain board:thread_num integrity
            # if we want, we can limit faceted search to 1 board in the form validation
            form_data['boards'] = [board]
            form_data['thread_nums'] = thread_nums
            query = get_index_search_query(form_data)
            _posts, _total_hits = await index_searcher.search_posts(query)
            posts.extend(_posts)
            total_hits += _total_hits
        return posts, total_hits

    query = get_index_search_query(form_data, board_ints=board_ints)
    return await index_searcher.search_posts(query)


async def get_posts_and_total_hits_fts(form_data: dict):
    if form_data.get('tag_ids'):

        # facet search means we need total hits, and we get it with [0, max_hits]
        page = form_data['page']
        per_page = form_data['hits_per_page']
        form_data['page'] = 0
        form_data['hits_per_page'] = index_search_conf['max_hits']

        board_2_media_origs = await get_board_2_media_origs_by_tag_ids(
            form_data['tag_ids'],
            0.2,
            form_data['safe_search'],
            form_data['boards'],
            form_data['page'],
            form_data['hits_per_page'],
        )

        # revert to original values
        form_data['page'] = page
        form_data['hits_per_page'] = per_page

        calls = []
        for b, media_origs in board_2_media_origs.items():
            if media_origs:
                form_data['boards'] = [b]
                form_data['media_origs'] = media_origs
                calls.append(_get_posts_and_total_hits_fts(form_data))
        results = await asyncio.gather(*calls)

        all_posts = []
        total_hits = 0
        if results:
            for posts, b_total_hits in results:
                if posts:
                    all_posts.extend(posts)
                    total_hits += b_total_hits

        form_data['media_origs'] = None
        return all_posts, total_hits

    return await _get_posts_and_total_hits_fts(form_data)


async def get_posts_and_total_hits_sql(form_data: dict):
    return await search_posts(form_data, vanilla_search_conf['max_hits'])


async def get_posts_and_total_hits(search_type: SearchType, form_data: dict) -> tuple[list[dict], int]:
    if not isinstance(form_data['boards'], list):
        raise ValueError(form_data['boards'])

    # do not provide gallery results for boards that have non-served media
    if form_data.get('gallery_mode'):
        b_i = len(form_data['boards'])
        form_data['boards'] = [b for b in form_data['boards'] if (b in media_conf['boards_with_thumb'] or b in media_conf['boards_with_image'])]
        b_f = len(form_data['boards'])
        if b_i > b_f:
            await flash('Some boards have media disabled, there may be fewer results than expected.')
        if not form_data['boards']:
            return [], 0

    if search_type == SearchType.idx:
        return await get_posts_and_total_hits_fts(form_data)
    return await get_posts_and_total_hits_sql(form_data)


async def get_posts_from_filenames(form_data, board_2_filenames, search_type: SearchType) -> tuple[list[dict], int]:
    total_hits = 0
    posts = []
    count = 0

    board_2_nums = await get_board_2_nums_from_board_2_filenames(board_2_filenames)

    for board, nums in board_2_nums.items():
        form_data['boards'] = [board]
        form_data['nums'] = nums
        _posts, _total_hits = await get_posts_and_total_hits(search_type, form_data)
        posts.extend(_posts)
        total_hits += _total_hits

    # print(f'{count=}', f'{len(posts)=}', len(board_2_medias['g']), len(board_2_nums['g']))
    count += 1

    if len(posts) > form_data["hits_per_page"]:
        return posts[:form_data["hits_per_page"]], form_data["hits_per_page"]

    return posts, total_hits


async def get_posts_from_tag_ids(tag_ids, form_data: dict, search_type: SearchType) -> tuple[list[dict], int]:
    total_hits = 0
    posts = []

    count = 0

    # maybe the tagging db has media that are not in asagi, resulting in less than
    # <hits_per_page> being returned despite more existing.
    # a migration solution to add an exists-in-asagi flag has been issued, but until the tagger
    # is updated with that, we will keep this.
    while count <= tag_conf['max_page_retries'] and len(posts) < form_data["hits_per_page"]:
        board_2_filenames = await get_board_2_media_origs_by_tag_ids(
            tag_ids,
            0.2,
            SafeSearch(int(form_data["safe_search"])),
            form_data["boards"],
            page=form_data["page"] * (count + 1),
            per_page=form_data["hits_per_page"],
        )

        if not board_2_filenames or not any(board_2_filenames):
            return posts, total_hits

        board_2_nums = await get_board_2_nums_from_board_2_filenames(board_2_filenames)

        for board, nums in board_2_nums.items():
            form_data['boards'] = [board]
            form_data['nums'] = nums
            _posts, _total_hits = await get_posts_and_total_hits(search_type, form_data)
            posts.extend(_posts)
            total_hits += _total_hits

        # print(f'{count=}', f'{len(posts)=}', len(board_2_medias['g']), len(board_2_nums['g']))
        count += 1

    if len(posts) > form_data["hits_per_page"]:
        return posts[:form_data["hits_per_page"]], form_data["hits_per_page"]

    return posts, total_hits


def make_pills(d: dict[str, int], class_: str):
    r = ''
    for k, v in d.items():
        r += f'<span class="pill {class_}">{k}: {v}</span>'
    return r


async def get_tags_ids_and_html_pills_from_image_path(img_path: str) -> tuple:
    img = Image.open(img_path)
    rating_tags, char_tags, gen_tags = process_images_from_imgs([img], model, transform, torch_device, tag_data, 0.2, 0.2, by_idx=True)[0]
    tags = [*char_tags, *gen_tags]

    d = dict(
        rat={tag_data.names[k]: v for k, v in rating_tags.items()},
        char={tag_data.names[k]: v for k, v in char_tags.items()},
        gen={tag_data.names[k]: v for k, v in gen_tags.items()},
    )
    pills = ''.join(make_pills(v, k) for k, v in d.items())

    return tags, pills


async def app_process_images_from_paths(form_data: dict, img_path: str, search_type: SearchType) -> dict:
    i1 = perf_counter()
    img = Image.open(img_path)
    rating_tags, char_tags, gen_tags = process_images_from_imgs([img], model, transform, torch_device, tag_data, 0.2, 0.2, by_idx=True)[0]
    tags = [*char_tags, *gen_tags]

    i2 = perf_counter()
    f1 = i2 - i1
    posts, total_hits = await get_posts_from_tag_ids(tags, form_data, search_type)
    f2 = perf_counter() - i2

    d = dict(
        rat={tag_data.names[k]: v for k, v in rating_tags.items()},
        char={tag_data.names[k]: v for k, v in char_tags.items()},
        gen={tag_data.names[k]: v for k, v in gen_tags.items()},
    )

    image_count = await get_image_count()
    message = f'Tagged your image in {f1:,.3f}s. Searched {image_count:,} images in {f2:.3f}s. Found {total_hits:,} results.'

    return dict(
        posts=posts,
        total_hits=total_hits,
        message=message,
        api_response='<br>'.join(make_pills(v, k) for k, v in d.items())
    )


async def get_posts_from_sha256(sha256, form_data, search_type):
    posts = []
    total_hits = 0

    i1 = perf_counter()
    rows = await get_image_filenames_by_sha256_and_boards(form_data['boards'], sha256)

    if rows:
        board_2_filenames = dict()
        for board, filename in rows:
            board_2_filenames[board] = filename

        posts, total_hits = await get_posts_from_filenames(form_data, board_2_filenames, search_type)
    f1 = perf_counter() - i1

    image_count = await get_image_count()

    message = f'SHA256\'d your image in <0.001s. Searched {image_count:,} images in {f1:.3f}s. Found {total_hits:,} exact matches.'
    return dict(
        posts=posts,
        total_hits=total_hits,
        message=message,
        api_response=f'SHA256: {sha256}'
    )


def count_files(directory: str):
    return sum(
        1 for entry in os.scandir(directory)
        if entry.is_file() and os.path.splitext(entry.name)[1].lower() in tag_conf['exts']
    )


async def search_w_file(form_data: dict, file_image: FileStorage, search_type: SearchType) -> dict:
    if not file_image:
        abort(BadRequest.code)

    queue_count = count_files(make_src_path('static', 'uploads'))
    if queue_count > 20:
        dict(
            posts=[],
            total_hits=0,
            message=f'The image search queue is currently full. Please try again in ~{queue_count:,:2f}s',
            api_response='',
        )

    ext = mimetypes.guess_extension(file_image.mimetype)
    image_path = make_src_path('static', 'uploads', f'{time_ns()}{ext}')

    try:
        p = Perf('tag search', enabled=current_app.testing)
        sha256 = get_sha256_from_bytesio_and_write(image_path, file_image.stream)
        p.check('sha gen')
        posts1, total_hits1 = [], 0
        if sha256:
            form_data['sha256'] = sha256
        posts1, total_hits1 = await get_posts_and_total_hits(SearchType.sql, form_data) # no sha256 in fts
        p.check('sha search')
        del form_data['sha256']

        tag_ids, pills = await get_tags_ids_and_html_pills_from_image_path(image_path)
        p.check('tag gen')
        posts2, total_hits2 = [], 0
        if tag_ids:
            form_data['tag_ids'] = tag_ids
            posts2, total_hits2 = await get_posts_and_total_hits(search_type, form_data)
        p.check('tag search')
        print(p)

        # [tag search]
        # sha gen   : 0.0002 0.0%
        # sha search: 1.2985 51.1%
        # tag gen   : 0.2152 8.5%
        # tag search: 1.0288 40.5%
        # total     : 2.5426

        # merge the two posts
        posts = []
        nums = set()
        for p in posts1 + posts2:
            if p['num'] in nums:
                continue
            posts.append(p)
            nums.add(p['num'])

        # delete uploaded files
        if os.path.isfile(image_path):
            os.remove(image_path)

        return dict(
            posts=posts,
            total_hits=len(posts),
            message=f'SHA256 hits: {total_hits1}, Tag hits: {total_hits2}',
            api_response=f'{sha256}<br>{pills}'
        )

    except Exception as e:
        if os.path.isfile(image_path):
            os.remove(image_path)
        raise e
