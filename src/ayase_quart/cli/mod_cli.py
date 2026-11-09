import os
from argparse import Namespace

from ..configs import media_conf
from ..db import db_m
from ..enums import MediaFP
from ..media.filesystem import get_fs_path, MediaType
from .lite_utils import get_confirm

MAX_SAMPLES_PER_BOARD = 5


async def clean_deleted_media_cli(args: Namespace) -> None:
    """Supports Asagi and Sutra media paths with arg --fp.
    """

    if not media_conf.media_root_path:
        print(f'media_root_path is not set - cannot resolve local media paths.')
        return

    dry_run = args.dry_run

    print(f'Running clean_deleted_media {"(dry run)" if dry_run else ""}')
    if not dry_run and not get_confirm('Delete orphaned media files of deleted posts?'):
        print('Exiting')
        return

    sql = 'select board_shortname, num, thread_num, media_hash, media_orig, preview_orig from deleted_media'
    if args.boards:
        sql += f' where board_shortname in ({db_m.Phg().size(args.boards)});'
        rows = await db_m.query_dict(sql, params=args.boards)
    else:
        sql += ';'
        rows = await db_m.query_dict(sql)
    if not rows:
        print('No rows in deleted_media' + (f' for boards: {" ".join(args.boards)}' if args.boards else '') + '.')
        return
    print(f'Boards: {" ".join(sorted({row["board_shortname"] for row in rows}))}')

    media_fp = MediaFP(args.fp) if args.fp else media_conf.media_fp

    exts = media_conf.valid_extensions or ['jpg', 'jpeg', 'png', 'gif', 'webm', 'mp4']

    deleted = not_found = errors = skipped = 0
    seen_paths: set[str] = set()
    samples: dict[str, list[str]] = {}

    for row in rows:
        board = row['board_shortname']
        media_hash = row['media_hash']

        if media_fp == MediaFP.sutra:
            post = {'board_shortname': board, 'media_hash': media_hash, 'media_orig': f'{media_hash}.jpg'}
            candidates = [(MediaType.thumbnail, post)]
            candidates += [(MediaType.full_media, post | {'media_orig': f'{media_hash}.{ext}'}) for ext in exts]
        else:
            if not row['media_orig'] or not row['preview_orig']:
                skipped += 1
                continue
            post = {
                'board_shortname': board,
                'media_hash': media_hash,
                'media_orig': row['media_orig'],
                'preview_orig': row['preview_orig'],
            }
            candidates = [(MediaType.full_media, post), (MediaType.thumbnail, post)]

        for media_type, candidate_post in candidates:
            path = get_fs_path(candidate_post, media_type, hidden=True) or get_fs_path(candidate_post, media_type)
            if not path or path in seen_paths:
                continue
            seen_paths.add(path)

            if not os.path.isfile(path):
                not_found += 1
                continue

            sample = samples.setdefault(board, [])
            if len(sample) < MAX_SAMPLES_PER_BOARD:
                sample.append(path)

            if dry_run:
                deleted += 1
                continue

            try:
                os.remove(path)
                deleted += 1
            except OSError as e:
                errors += 1
                print(f'error deleting {path}: {e}')

    for board, paths in samples.items():
        print(f'{board} (up to {MAX_SAMPLES_PER_BOARD} sample paths):')
        for p in paths:
            print(f'  {p}')

    action = 'to delete' if dry_run else 'deleted'
    print(f'Files {action}: {deleted} | Not found: {not_found} | Skipped: {skipped} | Errors: {errors}')


async def mod_cli(args: Namespace) -> None:
    match args.cmd_1:
        case 'clean_deleted_media':
            await clean_deleted_media_cli(args)
            await db_m.close_db_pool()
        case _:
            print('Unimplemented.')
