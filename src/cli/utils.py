import click
import asyncio
from tabulate import tabulate

from moderation.user import User


class MockAdmin(User):
    is_admin = True


def run_coroutine(coro):
    return asyncio.run(coro)


def print_result(msg, code):
    click.echo(f'{code}: {msg}')


def print_result(msg: str, code: int):
    if code < 400:
        click.echo(f'Success ({code}): {msg}')
    else:
        click.echo(f'Error ({code}): {msg}')


def print_list_of_dict(data: list[dict]):
    if not data:
        click.echo('Empty')
        return
    
    headers = data[0].keys()
    rows = [list(d.values()) for d in data]

    table = tabulate(rows, headers=headers, tablefmt='orgtbl')
    click.echo(table)