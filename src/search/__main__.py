import asyncio
import sys

from .loader import main as load
from .providers import get_search_provider

help_text = """
usage: python -m search COMMAND [args]
commands:
	create
		create search indexes
	load board1 [board2 [board3 ...]]
		index boards (ensure indexes have been created)
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
            if not (boards := args[1:]):
                print("missing boards")
                print_help()
                sys.exit()
            asyncio.run(load(boards))
        case 'create':
            asyncio.run(create_index())
        case 'delete':
            asyncio.run(delete_index())
        case _:
            print_help()
            sys.exit()


if __name__ == "__main__":
    main(sys.argv[1:])
