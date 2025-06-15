import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from search.loader import load_full, load_incremental
from search.providers import get_index_search_provider

help_text = """
Usage: python3.13 -m search COMMANDS [args]
       Run this from the directory `./ayase-quart/src`
Commands:
    create
        create search indexes
    load [--incr | --full [--reset] ] board1 [board2 [board3 ...]]
        passing `--full`  will index boards, it will ensure indexes have been created
        passing `--reset` will delete and recreate the index
        passing `--incr`  will only load posts that have not been indexed yet
    delete
        delete search indexes
All use cases:
    ./ayase-quart/src$ python3.13 -m search load --full         g ck biz
    ./ayase-quart/src$ python3.13 -m search load --full --reset g ck biz
    ./ayase-quart/src$ python3.13 -m search load --incr         g ck biz
    ./ayase-quart/src$ python3.13 -m search create
    ./ayase-quart/src$ python3.13 -m search delete
"""


def print_help():
    print(help_text)


def print_help_and_exit(msg: str=''):
    if msg:
        print(msg)
    print_help()
    sys.exit()


async def create_index():
    if input('Create index? (y/n): ').strip().lower() != 'y':
        return
    sp = get_index_search_provider()
    await sp.init_indexes()
    await sp.close()
    print('Indexes created')


async def delete_index():
    if input('Wipe index? (y/n): ').strip().lower() != 'y':
        return
    sp = get_index_search_provider()
    await sp.posts_wipe()
    await sp.close()
    print('Index data wiped')


def main(args):
    if not args:
        print_help()
        sys.exit()

    match args[0]:
        case 'load':
            if not (args := args[1:]):
                print_help_and_exit('Did not specify boards.')

            reset = '--reset' in args
            full = '--full' in args
            incremental = '--incr' in args

            options = ('--reset', '--full', '--incr')
            boards = [arg for arg in args if arg not in options]
            if not boards:
                print_help_and_exit('Did not specify boards.')
            print(f'Detected boards: {boards}')

            if not any((full, reset, incremental)):
                print_help_and_exit('You must specify a load option [--incr | --full [--reset] ].')

            if reset and incremental:
                print_help_and_exit('Cannot reset and increment index.')

            if incremental and full:
                print_help_and_exit('Cannot increment load and full load index.')

            if incremental:
                print('Doing incremental index load')
                asyncio.run(load_incremental(boards))
            elif full:
                print('Doing full index load' + (' after reseting index' if reset else ''))
                asyncio.run(load_full(boards, reset))
            else:
                print_help_and_exit('Neither incremental nor full load specified. Nothing to do.')

        case 'create':
            asyncio.run(create_index())
        case 'delete':
            asyncio.run(delete_index())
        case _:
            print_help_and_exit(f'Unknown COMMAND {args[0]} specified.')

    print('Done.')

if __name__ == "__main__":
    main(sys.argv[1:])
