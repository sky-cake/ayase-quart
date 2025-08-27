import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from datetime import datetime
from functools import wraps
from typing import Optional

import click

from boards import board_shortnames
from cli.utils import MockAdmin, print_list_of_dict, print_result
from configs import app_conf
from db import close_all_databases
from enums import ModStatus, PublicAccess, ReportAction, SubmitterCategory
from moderation.report import (
    delete_report_if_exists,
    edit_report_if_exists,
    get_report_count,
    get_reports,
    reports_action_routine
)


@click.group(name='report')
def cli_group_report():
    pass


def report_filters(func):
    options = [
        click.option('--report_parent_id',   '-id',     default=None, type=int),
        click.option('--board_shortnames',   '-boards', default=None, multiple=True, type=click.Choice(board_shortnames)),
        click.option('--is_op',              '-op',     default=None, type=bool),
        click.option('--thread_num',         '-tno',    default=None, type=int),
        click.option('--num',                '-pno',    default=None, type=int),
        click.option('--submitter_category', '-cat',    default=None, type=click.Choice([e.value for e in SubmitterCategory])),
        click.option('--public_access',      '-access', default=None, type=click.Choice([e.value for e in PublicAccess])),
        click.option('--mod_status',         '-status', default=None, type=click.Choice([e.value for e in ModStatus])),
        click.option('--created_at_gte',     '-cgte',   default=None, type=click.DateTime(formats=['%Y-%m-%d'])),
        click.option('--created_at_lte',     '-clte',   default=None, type=click.DateTime(formats=['%Y-%m-%d'])),
    ]
    for option in options:
        func = option(func)
    return func


def report_options(func):
    options = [
        click.option('--page_num',           '-pgno',   default=0,    type=int),
        click.option('--page_size',          '-pgsize', default=20,   type=int),
    ]
    for option in options:
        func = option(func)
    return func


def report_filters_formatter(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs:
            for k, v in kwargs.items():
                if isinstance(v, datetime):
                    kwargs[k] = v.strftime('%Y-%m-%d')
        func(*args, **kwargs)
    return wrapper


@cli_group_report.command()
@report_filters
@report_filters_formatter
@close_all_databases
def cli_get_report_count(**kwargs):
    report_count = asyncio.run(get_report_count(**kwargs))
    click.echo(f'Report count: {report_count}')


@cli_group_report.command()
@report_filters
@report_options
@report_filters_formatter
@close_all_databases
def cli_get_reports(**kwargs):
    reports = asyncio.run(get_reports(**kwargs))
    for r in reports:
        r['link'] = f'{app_conf['url']}/{r.board_shortname}/thread/{r.thread_num}#p{r.num}'
        # do we need these if there is a link ?
        # del r['board_shortname']
        # del r['thread_num']
        # del r['num']
    print_list_of_dict(reports)


@cli_group_report.command()
@click.option('--report_parent_id', '-id', required=True, type=int)
@click.option('--public_access', '-access', type=click.Choice([e.value for e in PublicAccess]), default=None)
@click.option('--mod_status', '-status', type=click.Choice([e.value for e in ModStatus]), default=None)
@click.option('--mod_notes', '-notes', type=str, default=None)
@close_all_databases
def cli_edit_report(report_parent_id: int, public_access: Optional[str], mod_status: Optional[str], mod_notes: Optional[str]):
    report = asyncio.run(edit_report_if_exists(report_parent_id, public_access, mod_status, mod_notes))
    if report:
        click.echo('Updated')
        return
    click.echo('Report not found')


@cli_group_report.command()
@click.option('--report_parent_id', '-id', required=True, type=int)
@close_all_databases
def cli_delete_report(report_parent_id: int):
    report = asyncio.run(delete_report_if_exists(report_parent_id))
    if report:
        click.echo('Deleted')
        return
    click.echo('Report not found')


@cli_group_report.command()
@click.option('--report_parent_id', '-id', required=True, type=int)
@click.option('--action', '-action', required=True, type=click.Choice([e.value for e in ReportAction]))
@click.option('--mod_notes', '-notes', required=False, type=str, default=None)
@close_all_databases
def cli_reports_action(report_parent_id: int, action: str, mod_notes: Optional[str] = None):
    msg, code = asyncio.run(
        reports_action_routine(MockAdmin(), report_parent_id, action, mod_notes=mod_notes)
    )
    print_result(msg, code)


if __name__ == '__main__':
    cli_group_report()
