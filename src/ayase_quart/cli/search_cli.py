import asyncio
from argparse import Namespace

from .lite_utils import get_confirm

async def search_index_cli(args: Namespace) -> None:
    cmd: str = args.cmd_2
    if not get_confirm(f'{cmd.title()} search index?'):
        return
    from ..search.providers import get_index_search_provider
    sp = get_index_search_provider()
    match cmd:
        case 'delete':
            await sp.posts_wipe()
            print('Index data wiped')
        case 'create':
            await sp.init_indexes()
            await sp.finalize()
            print('Indexes created')
        case 'reset':
            await sp.posts_wipe()
            await sp.init_indexes()
            await sp.finalize()
            print('Index data reset')
    await sp.close()

async def search_load_cli(args: Namespace) -> None:
    from ..search.loader import load_full, incremental_index_single_thread
    boards = args.boards
    match args.cmd_2:
        case 'full': await load_full(boards)
        case 'incr':
            from ..search import get_index_search_provider
            from ..db import db_q
            cron = args.cron
            sp = get_index_search_provider()
            while True:
                try:
                    await incremental_index_single_thread(sp, boards)
                    if not cron:
                        break
                    await asyncio.sleep(cron)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(e) # TODO: logger
                    break # break or 'continue'?
            await sp.close()
            await db_q.close_db_pool()

async def search_cli(args: Namespace) -> None:
    match args.cmd_1:
        case 'index': await search_index_cli(args)
        case 'load': await search_load_cli(args)
