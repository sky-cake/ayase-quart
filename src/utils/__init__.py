import os
from time import perf_counter

from werkzeug.exceptions import NotFound


def make_src_path(*file_path):
    """Make a file path starting from src/."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', *file_path))

class Perf:
    __slots__ = ('previous', 'checkpoints', 'topic')

    def __init__(self, topic: str=None):
        self.topic = topic
        self.checkpoints = []
        self.previous = perf_counter()

    def check(self, name: str=""):
        now = perf_counter()
        elapsed = now - self.previous
        self.previous = now
        self.checkpoints.append((name, elapsed))

    # todo: call from logger for mass disabling
    def __repr__(self) -> str:
        total = sum(point[1] for point in self.checkpoints)
        longest = max(max(len(point[0]) for point in self.checkpoints), 5) # 5 is len of 'total'
        topic = f'[{self.topic}]\n' if self.topic else ''
        return topic + '\n'.join(
            f'{name:<{longest}}: {elapsed:.4f} {elapsed / total * 100 :.1f}%'
            for name, elapsed in self.checkpoints
        ) + f'\n{"total":<{longest}}: {total:.4f}'
