import asyncio
import sys

from .tables_indexes import run_table_command
from .populate import run_populate
from . import SideTableCmd as Cmd

help_text = f'''
Usage: python -m sidetables COMMAND [args]
Commands:
    {Cmd.table_create} board1 [board2 [board3 ...]]
        create side tables for selected boards
        only primary keys set, no other indexes
    {Cmd.table_drop} board1 [board2 [board3 ...]]
        drop side tables for selected boards
    {Cmd.table_backup} board1 [board2 [board3 ...]]
        rename side tables for selected boards with _bak suffix
        ensure that side tables exist beforehand
    {Cmd.index_drop} board1 [board2 [board3 ...]]
        drop indexes for selected boards side tables
        ensure that side tables exist beforehand
    {Cmd.index_add} board1 [board2 [board3 ...]]
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
        case Cmd.table_create | Cmd.table_drop | Cmd.table_backup | Cmd.index_drop | Cmd.index_add:
            if not args: help_exit()
            boards = args
            asyncio.run(run_table_command(command, boards))
        case 'populate':
            if not args: help_exit()
            boards = args
            run_populate(boards)
        case _:
            help_exit()

if __name__ == "__main__":
    main(sys.argv[1:])
