from typing import Iterable

class BasePlaceHolderGen():
    __slots__ = ()

    def size(self, items: Iterable):
        return ','.join(self() for _ in range(len(items)))

    def qty(self, qty: int):
        return ','.join(self() for _ in range(qty))