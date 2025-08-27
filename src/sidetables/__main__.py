import asyncio
import sys

from . import SideTableCmd as Cmd
from .populate import run_populate
from .tables_indexes import run_table_command

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
    command, boards = args[0], args[1:]

    if not isinstance(boards, list):
        raise ValueError(f'Boards should be a list, got {type(boards)} {boards=}')

    if not boards: help_exit()

    match command:
        case Cmd.table_create | Cmd.table_drop | Cmd.table_backup | Cmd.index_drop | Cmd.index_add:
            asyncio.run(run_table_command(command, boards))
        case 'populate':
            run_populate(boards)
        case _:
            help_exit()

if __name__ == "__main__":
    main(sys.argv[1:])
