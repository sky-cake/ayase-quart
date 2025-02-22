import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import click
from typing import Optional
from functools import wraps
from datetime import datetime

from boards import board_shortnames
from enums import ModStatus, PublicAccess, ReportAction, SubmitterCategory
from moderation.report import (
    reports_action_routine,
    edit_report_if_exists,
    delete_report_if_exists,
    get_reports,
    get_report_count
)
from cli.utils import run_coroutine, print_list_of_dict, print_result, MockAdmin
from configs import app_conf


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
def cli_get_report_count(**kwargs):
    report_count = run_coroutine(get_report_count(**kwargs))
    click.echo(f'Report count: {report_count}')


@cli_group_report.command()
@report_filters
@report_options
@report_filters_formatter
def cli_get_reports(**kwargs):
    reports = run_coroutine(get_reports(**kwargs))
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
def cli_edit_report(report_parent_id: int, public_access: Optional[str], mod_status: Optional[str], mod_notes: Optional[str]):
    report = run_coroutine(edit_report_if_exists(report_parent_id, public_access, mod_status, mod_notes))
    if report:
        click.echo('Updated')
        return
    click.echo('Report not found')


@cli_group_report.command()
@click.option('--report_parent_id', '-id', required=True, type=int)
def cli_delete_report(report_parent_id: int):
    report = run_coroutine(delete_report_if_exists(report_parent_id))
    if report:
        click.echo('Deleted')
        return
    click.echo('Report not found')


@cli_group_report.command()
@click.option('--report_parent_id', '-id', required=True, type=int)
@click.option('--action', '-action', required=True, type=click.Choice([e.value for e in ReportAction]))
@click.option('--mod_notes', '-notes', required=False, type=str, default=None)
def cli_reports_action(report_parent_id: int, action: str, mod_notes: Optional[str] = None):
    msg, code = run_coroutine(
        reports_action_routine(MockAdmin(), report_parent_id, action, mod_notes=mod_notes)
    )
    print_result(msg, code)


if __name__ == '__main__':
    cli_group_report()
