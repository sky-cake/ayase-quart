from itertools import batched
from time import perf_counter
import asyncio
from timm.data import create_transform, resolve_data_config

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from configs import tag_conf, db_conf

from tagging.db import insert_image_tags, init_tagging, make_tag_data, get_untagged_board_filename_pairs
from db import db_q
from processor import load_model, process_images_from_paths
from tagging.utils import (
    get_torch_device,
    printr
)
from asagi_converter import get_full_media_path


async def scan_and_store(root_path, board, batch_size=10_000):
    print(f'Scanning and storing {board=}')
    image_dir = os.path.join(root_path, board, 'image')
    thumb_dir = os.path.join(root_path, board, 'thumb')

    if not os.path.isdir(image_dir):
        print(f'No path found: {image_dir}. Done scanning and storing.')
        return

    batch = []
    count = 0

    sql = '''
    INSERT INTO image (board, filename, ext, has_thumb)
            VALUES (?,?,?,?)
        ON CONFLICT(board, filename)
    DO UPDATE
        SET
            ext = excluded.ext,
            has_thumb = excluded.has_thumb
    '''

    for _, _, filenames in os.walk(image_dir):
        for filename in filenames:
            if '.' not in filename:
                continue

            name, ext = filename.rsplit('.', 1)

            thumb_path = os.path.join(thumb_dir, name[:4], name[4:6], f'{name}s.jpg')
            has_thumb = 1 if os.path.isfile(thumb_path) else 0

            batch.append((board, filename, ext, has_thumb))
            count += 1

            if len(batch) >= batch_size:
                print(f'images: {count:,}')

                await db_q.query_runner.run_query_many(sql, batch, commit=True)
                batch.clear()

    if batch:
        await db_q.query_runner.run_query_many(sql, batch, commit=True)
    print(f'Scanning and storing {board=}, done')


async def main(
        root_path: str,
        boards: list[str],
        gmin: int=0.2,
        cmin: int=0.2,
        valid_extensions: str='png,jpeg,jpg,gif',
        bsize: int=1,
        nmax: int=0,
        db_name=db_conf['database'],
        idx: bool=True,
        save: bool=True,
        cpu: bool=False,
    ):

    save = save and idx

    valid_extensions = tuple([v.strip() for v in valid_extensions.split(',')])
    assert len(valid_extensions)

    assert os.path.isdir(root_path), root_path

    print(f'Using database {db_name=} with {tag_conf['load_sqlite_into_memory']=}')

    await init_tagging()

    tag_data = make_tag_data()

    printr('Loading model')
    torch_device = get_torch_device(cpu)
    model = load_model(tag_conf['tag_model_repo_id']).to(torch_device, non_blocking=True)
    transform = create_transform(**resolve_data_config(model.pretrained_cfg, model=model))
    printr('Loading model, complete')

    img_path = 'n/a'
    for board in boards:
        print('')
        print('='*50)
        print(f'{board=}')
        print('='*50)

        await scan_and_store(root_path, board)

        untagged_board_filename_pairs = await get_untagged_board_filename_pairs(board)
        print(f'Found {len(untagged_board_filename_pairs)} non-tagged images in database for {board=}')

        timesum = 0
        count = 0
        count_errors = 0
        count_completed = 0
        next_commit_count = 100
        next_commit_iter = 100
        for untagged_board_filename_pairs_i in batched(untagged_board_filename_pairs, bsize):
            count += len(untagged_board_filename_pairs_i)
            if nmax and count > nmax:
                break

            image_paths_2_board_filename_pairs = dict()
            for untagged_board_filename_pair in untagged_board_filename_pairs_i:

                if not untagged_board_filename_pair[1].endswith(valid_extensions):
                    continue

                img_path = get_full_media_path(root_path, untagged_board_filename_pair[0], 'image', untagged_board_filename_pair[1])
                if os.path.isfile(img_path):
                    image_paths_2_board_filename_pairs[img_path] = untagged_board_filename_pair
                else:
                    print(f'Expected file at: {img_path}')

            if len(image_paths_2_board_filename_pairs) < 1:
                continue

            start = perf_counter()

            try:
                info = process_images_from_paths(image_paths_2_board_filename_pairs.keys(), model, transform, torch_device, tag_data, gmin, cmin, by_idx=idx)
                count_completed += 1
            except Exception as e:
                count_errors += 1
                print('')
                print(e)
                continue

            if save:
                for board_filename_pair, (ratings, characters, generals) in zip(image_paths_2_board_filename_pairs.values(), info):
                    img_path = get_full_media_path(root_path, board_filename_pair[0], 'image', board_filename_pair[1])
                    await insert_image_tags(img_path, board_filename_pair[0], board_filename_pair[1], ratings, characters | generals)

                if count > next_commit_count:
                    await db_q.pool_manager.save_all_pools()
                    next_commit_count += next_commit_iter

            timesum += perf_counter() - start
            printr(f'Completed: {count_completed}  Errors: {count_errors}  Board: {board}  Last: {img_path}')
        printr(f'Completed: {count_completed}  Errors: {count_errors}  Board: {board}  Last: {img_path}')
        print()

        if save and count:
            await db_q.pool_manager.save_all_pools()

        print('Done processing images!')
        print(f'Total time: {timesum:.3f}s')
        print(f'Time per image: {timesum/max(count, 1):.3f}s')

    if save:
        await db_q.pool_manager.save_all_pools()
        await db_q.pool_manager.close_all_pools()

    return


if __name__ == '__main__':
    root_path = '/mnt/dl'

    boards = [
        '3','a','aco','adv','an','b','bant','biz','c','cgl','ck',
        'cm','co','d','diy','e','f','fa','fit','g','gd','gif','h','hc',
        'his','hm','hr','i','ic','int','jp','k','lgbt','lit','m','mlp','mu',
        'n','news','o','out','p','po','pol','pw','qa','qst','r','r9k','s','s4s',
        'sci','soc','sp','t','tg','toy','trv','tv','u','v','vg','vip','vm',
        'vmg','vp','vr','vrpg','vst','vt','w','wg','wsg','wsr','x','xs','y',
    ]
    call = main(
        root_path,
        boards,
        gmin=0.2,
        cmin=0.2,
        valid_extensions='png,jpeg,jpg,gif',
        bsize=1,
        nmax=0,
        db_name='/mnt/ritual/ritual.db', # db_conf['database'],
        idx=True,
        save=True,
        cpu=False,
    )
    asyncio.run(call)
