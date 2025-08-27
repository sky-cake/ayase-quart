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

# to normalize paths from configs
def strip_slashes(path: str, both=False):
    if not path:
        return path
    path = path.strip()
    return path.strip('/') if both else path.rstrip('/')


class Perf:
    __slots__ = ('previous', 'checkpoints', 'topic', 'enabled')

    def __init__(self, topic: str=None, enabled=False):
        self.enabled = enabled
        if self.enabled:
            self.topic = topic
            self.checkpoints = []
            self.previous = perf_counter()

    def check(self, name: str=""):
        if self.enabled:
            now = perf_counter()
            elapsed = now - self.previous
            self.previous = now
            self.checkpoints.append((name, elapsed))

    # todo: call from logger for mass disabling
    def __repr__(self) -> str:
        if self.enabled:
            total = sum(point[1] for point in self.checkpoints)
            longest = max(max(len(point[0]) for point in self.checkpoints), 5) # 5 is len of 'total'
            topic = f'[{self.topic}]\n' if self.topic else ''
            return topic + '\n'.join(
                f'{name:<{longest}}: {elapsed:.4f} {elapsed / total * 100 :.1f}%'
                for name, elapsed in self.checkpoints
            ) + f'\n{"total":<{longest}}: {total:.4f}'
        else:
            return ''
