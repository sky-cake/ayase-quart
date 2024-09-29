import os
from time import perf_counter

from werkzeug.exceptions import NotFound


def make_src_path(*file_path):
    """Make a file path starting from src/."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', *file_path))


def validate_threads(threads):
    if len(threads) < 1:
        raise NotFound(threads)


def validate_post(post):
    if not post:
        raise NotFound(post)


class Perf:
    __slots__ = ('previous', 'total', 'longest')

    def __init__(self):
        self.previous = perf_counter()
        self.total = 0
        self.longest = 0

    def check(self, name: str=""):
        now = perf_counter()
        elapsed = now - self.previous
        self.previous = now
        self.total += elapsed
        self.longest = max(self.longest, len(name))
        print(f'{name:<{self.longest}}: {elapsed:.4f}')
