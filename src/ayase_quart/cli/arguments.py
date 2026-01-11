from datetime import datetime, date
from enum import StrEnum
from typing import Any, Self
from collections.abc import Sequence
from dataclasses import dataclass, field
from argparse import (
    Namespace,
    ArgumentParser,
    RawDescriptionHelpFormatter,
    _SubParsersAction,
    ArgumentTypeError,
)

type SubParser = _SubParsersAction[ArgumentParser]

CLI_DESC = 'Ayase-Quart Cli'

class Cmd(StrEnum):
    search = 'search'
    mod = 'mod'
    prep = 'prep'

@dataclass(slots=True, frozen=True, init=False)
class CmdArg:
    names: list[str] = field(default_factory=list)
    props: dict[str, Any] = field(default_factory=dict)

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, 'names', args)
        object.__setattr__(self, 'props', kwargs)

def add_args(parser: ArgumentParser, cmd_args: Sequence[CmdArg]):
    for cmd_arg in cmd_args:
        parser.add_argument(*cmd_arg.names, **cmd_arg.props)

@dataclass(slots=True, frozen=True)
class Command:
    name: Cmd
    desc: str
    sub_cmds: list[Self] = field(default_factory=list)
    pre_args: list[CmdArg] = field(default_factory=list)
    post_args: list[CmdArg] = field(default_factory=list)
    sub_cmd_required: bool = True

    def register(self, parent_sp: SubParser, level: int=0):
        parser = parent_sp.add_parser(self.name, help=self.desc)
        add_args(parser, self.pre_args)
        if self.sub_cmds:
            sub_parser = parser.add_subparsers(required=self.sub_cmd_required, dest=f'cmd_{level+1}')
            for sub_cmd in self.sub_cmds:
                sub_cmd.register(sub_parser, level+1)
        add_args(parser, self.post_args)

def valid_date(val: str) -> date:
    try:
        # '%Y' == YYYY %y == YY
        return datetime.strptime(val, '%y-%m-%d').date()
    except:
        raise ArgumentTypeError(f'Invalid date: {val}, expected format: YY-MM-DD')

board_arg = CmdArg(
    'boards', help='board(s) to operate on',
    nargs='+', metavar='BOARD',
)
report_arg = CmdArg(
    'report', help='report id(s) to operate on',
    type=int, nargs='+', metavar='REPORT',
)
note_arg = CmdArg(
    'note', help='new note (enclose in single or double quotes)',
    type=str, metavar='NOTE',
)
pub_access_flag = CmdArg(
    '-a', '--access', help='public access visiblity',
    choices=['v', 'h'],
    default=None, nargs='+', metavar='PUBVIS',
)
mod_status_flag = CmdArg(
    '-s', '--status', help='moderation status',
    choices=['o', 'c'],
    default=['o'], nargs='+', metavar='STATUS',
)
cron_flag = CmdArg(
    '--cron', help='run every N seconds',
    type=int, default=None, metavar='SECONDS',
)
report_category_flag = CmdArg(
    '-c', '--category', help='report category',
    choices=['illegal_content', 'dcma', 'underage', 'embedded_data', 'doxxing', 'work_safe', 'spamming', 'advertising', 'impersonation', 'bots', 'other',],
    default=None, nargs='+', metavar='CATEGORY',
)
op_flag = CmdArg(
    '--op', help='is op',
    action='store_true',
)
not_op_flag = CmdArg(
    '--nop', help='is not op',
    action='store_true',
)
board_flag = CmdArg(
    '-b', '--board', help='board(s)', dest='boards',
    type=str, default=None, nargs='+', metavar='BOARD',
)
num_flag = CmdArg(
    '-n', '--num', help='post num(s)',
    type=int, default=None, nargs='+', metavar='NUM',
)
thread_flag = CmdArg(
    '-t', '--thread', help='thread_num(s)',
    type=int, default=None, nargs='+', metavar='THREAD',
)
page_flag = CmdArg(
    '-p', '--page', help='page number',
    type=int, default=None, metavar='PAGE',
)
per_page_flag = CmdArg(
    '--pp', '--per-page', help='entries per page',
    type=int, default=None, metavar='QTY',
)
before_date_flag = CmdArg(
    '--before', help='before date',
    type=valid_date, default=None, metavar='YY-MM-DD',
)
after_date_flag = CmdArg(
    '--after', help='after date',
    type=valid_date, default=None, metavar='YY-MM-DD',
)

root_args = []
report_filter_flags = [
    per_page_flag,
    page_flag,
    before_date_flag,
    after_date_flag,
    op_flag,
    not_op_flag,
    report_category_flag,
    mod_status_flag,
    pub_access_flag,
    board_flag,
    thread_flag,
    num_flag,
]
report_edit_args = [
    report_category_flag,
    mod_status_flag,
    pub_access_flag,
    report_arg,
]

root_cmds = [
    Command(Cmd.prep, 'prepare system for launch', [
        Command('secret', 'generate secret in config.toml'),
        Command('hashjs', 'generate asset_hashes.json'),
        Command('boards', 'ensure boards defined in boards.toml exist in database'),
        Command('filtercache', 'populate moderation filter cache if enabled'),
    ]),
    Command(Cmd.search, 'search index management', [
        Command('index', 'instantiate or delete index', [
            Command('create', 'create index'),
            Command('delete', 'delete index'),
            Command('reset', 'delete and re-create index'),
        ]),
        Command('load', 'load posts into search index', [
            Command('full', 'load all posts for selected boards', post_args=[board_arg]),
            Command('incr', 'load posts not indexed yet for selected board',
                pre_args=[cron_flag],
                post_args=[board_arg],
            ),
        ]),
    ]),
    Command(Cmd.mod, 'moderation managemnt', [
        Command('report', 'manage user reports', [
            Command('list', 'list reports with filters', post_args=report_filter_flags),
            Command('count', 'show report counts'),
            Command('open', 'mark report(s) as open', post_args=[report_arg]),
            Command('close', 'mark report(s) as closed', post_args=[report_arg]),
            Command('addnote', 'add note to report(s)', post_args=[note_arg, report_arg]),
            Command('edit', 'edit report(s)', post_args=report_edit_args),
            Command('delete', 'delete report(s)', post_args=[report_arg]),
        ]),
        Command('post', 'manage reported posts', [
            Command('show', 'show post from report', post_args=[report_arg]),
            Command('hide', 'hide post from report', post_args=[report_arg]),
            Command('delete', 'delete post from report', post_args=[report_arg]),
        ]),
        Command('media', 'manage reported media', [
            Command('show', 'show media from report', post_args=[report_arg]),
            Command('hide', 'hide media from report', post_args=[report_arg]),
            Command('delete', 'delete media from report', post_args=[report_arg]),
        ]),
    ]),
]

def build_parser() -> ArgumentParser:
    root_parser = ArgumentParser(
        description=CLI_DESC,
        formatter_class=RawDescriptionHelpFormatter,
        exit_on_error=True,
    )
    add_args(root_parser, root_args)
    root_sp = root_parser.add_subparsers(required=True, dest='cmd_0')
    for cmd in root_cmds:
        cmd.register(root_sp)
    return root_parser

def get_args() -> Namespace:
    parser = build_parser()
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = get_args()
    print(args)
