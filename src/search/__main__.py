import asyncio
import sys

from .loader import main as load
from .providers import get_search_provider

help_text = """
usage: python -m search COMMAND [args]
commands:
	create
		create search indexes
	load [--reset] board1 [board2 [board3 ...]]
		index boards (ensure indexes have been created)
        passing --reset causes a delete and recreate of the index before loading
	delete
		delete search indexes
"""


def print_help():
    print(help_text)


async def create_index():
    if input('Create index? (y/n): ').strip().lower() != 'y': return
    sp = get_search_provider()
    await sp.init_indexes()
    await sp.close()
    print('Indexes created')


async def delete_index():
    if input('Wipe index? (y/n): ').strip().lower() != 'y': return
    sp = get_search_provider()
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
                print("Missing boards.")
                print_help()
                sys.exit()
            if args[0] == '--reset':
                reset = True
                boards = args[1:]
            else:
                reset = False
                boards = args
            asyncio.run(load(boards, reset))
        case 'create':
            asyncio.run(create_index())
        case 'delete':
            asyncio.run(delete_index())
        case _:
            print_help()
            sys.exit()


if __name__ == "__main__":
    main(sys.argv[1:])
