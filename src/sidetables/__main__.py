import asyncio
import sys

from .tables_indexes import run_table_command
from .populate import run_populate

help_text = '''
usage: python -m sidetables COMMAND [args]
commands:

create board1 [board2 [board3 ...]]
    create side tables for selected boards
    only primary keys set, no other indexes
drop board1 [board2 [board3 ...]]
    drop side tables for selected boards
dropindex board1 [board2 [board3 ...]]
    drop indexes for selected boards side tables
    ensure that side tables exist beforehand
addindex board1 [board2 [board3 ...]]
    add indexes on side tables for selected boards 
    ensure that side tables exist beforehand
populate board
    populates a board's side tables from its main post table
    may take a while, remember to add indexes after
'''

def help_exit():
    print(help_text)
    sys.exit()

def main(args: list[str]):
    if not args: help_exit()
    command, args = args[0], args[1:]
    match command:
        case 'create' | 'drop' | 'dropindex' | 'addindex':
            if not args: help_exit()
            boards = args
            asyncio.run(run_table_command(command, boards))
        case 'populate':
            if not args: help_exit()
            board = args[0]
            run_populate(board)
        case _:
            help_exit()

if __name__ == "__main__":
    main(sys.argv[1:])
