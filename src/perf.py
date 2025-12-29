from time import perf_counter
from logging import getLogger

from configs import TESTING

logger = getLogger('perf')

class DummyPerf:
    __slots__ = ()
    def __init__(self, topic: str=None): pass
    def check(self, name: str=""): pass
    def __repr__(self) -> str: return ''
    def emit(self) -> None: pass

class RealPerf:
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

    def __repr__(self) -> str:
        total = sum(point[1] for point in self.checkpoints)
        longest = max(max(len(point[0]) for point in self.checkpoints), 5) # 5 is len of 'total'
        topic = f'[{self.topic}]\n' if self.topic else ''
        return topic + '\n'.join(
            f'{name:<{longest}}: {elapsed:.4f} {elapsed / total * 100 :.1f}%'
            for name, elapsed in self.checkpoints
        ) + f'\n{"total":<{longest}}: {total:.4f}'

    # TODO: fix logging situation
    # nothing shows up even with hypercorn's default logging INFO level
    def emit(self) -> None:
        # logger.info(self)
        print(self)

Perf = RealPerf if TESTING else DummyPerf
