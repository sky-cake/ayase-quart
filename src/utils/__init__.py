import os
from time import perf_counter


def printr(msg):
    print('\r\033[K', end='') # ANSI escape sequence to clear entire line
    print(f'\r{msg}', end='', flush=True)


def read_file(path: str) -> str:
    with open(path) as f:
        return f.read()


def make_src_path(*file_path):
    """Make a file path starting from src/."""
    if file_path:
        return os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), *file_path))

    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def split_csv(csv_vals: str=None):
    if not csv_vals:
        return []
    return [x.strip() for x in csv_vals.strip(',').split(',')]


# to normalize paths from configs
def strip_slashes(path: str, both=False):
    if not path:
        return path
    path = path.strip()
    return path.strip('/') if both else path.rstrip('/')
