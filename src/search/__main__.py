import asyncio
import sys

from .loader import main as load
from .providers import get_search_provider

help_text = """
usage: python -m search COMMAND [args]
commands:
	create board1 [board2 [board3 ...]]
		create indexes for the search provider
	load board1 [board2 [board3 ...]]
		index boards in the search provider indexes
	delete
		delete the indexes of the search provider
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
            asyncio.run(load(args[1:]))
        case 'create':
            asyncio.run(create_index())
        case 'delete':
            asyncio.run(delete_index())
        case _:
            print_help()
            sys.exit()


if __name__ == "__main__":
    main(sys.argv[1:])
