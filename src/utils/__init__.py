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


string_of_uints = '0123456789'
string_of_uints_no0 = '123456789'


def startswith_uint(characters: str) -> bool:
    """
    ```
    characters = '123'      --> True
    characters = '0123'     --> True
    characters = '123⑨⑨45' --> True
    characters = '-123'     --> False
    characters = '-00123'   --> False
    characters = 'hi'       --> False
    characters = ''         --> False
    ```
    """

    for c in characters:

        if c in string_of_uints:
            return True
        
        # stop iterating if the streak of ints broken
        # avoids subcript range checks on `characters`
        return False

    return False


def startswith_uint_no0(characters: str) -> bool:
    """
    ```
    characters = '123'      --> True
    characters = '0123'     --> False
    characters = '123⑨⑨45' --> True
    characters = '-123'     --> False
    characters = '-00123'   --> False
    characters = 'hi'       --> False
    characters = ''         --> False
    ```
    """

    for c in characters:

        if c in string_of_uints_no0:
            return True
        
        # stop iterating if the streak of ints broken
        # avoids subcript range checks on `characters`
        return False

    return False


def is_uint(characters: str) -> bool:
    """
    The replacement for `str.isdigit()`.

    ```
    characters = '123'      --> True
    characters = '0123'     --> True
    characters = '123⑨⑨45' --> False
    characters = '-123'     --> False
    characters = '-00123'   --> False
    characters = 'hi'       --> False
    characters = ''         --> False
    ```
    """
    if not len(characters):
        return False

    for c in characters:
        if c not in string_of_uints:
            return False
    return True


def get_prefix_uint(characters: str) -> int | None:
    """
    ```
    characters = '123'      --> 123
    characters = '0123'     --> 123
    characters = '123⑨⑨45' --> 123
    characters = '-123'     --> None
    characters = '-00123'   --> None
    characters = 'hi'       --> None
    characters = ''         --> None
    ```
    """
    number = ''
    for c in characters:
        if c in string_of_uints:
            number += c
        else:
            # streak of real digits broken
            break
    return int(number) if number else None


def get_prefix_uint_no0(characters: str) -> int | None:
    """
    ```
    characters = '123'      --> 123
    characters = '0123'     --> None
    characters = '123⑨⑨45' --> 123
    characters = '-123'     --> None
    characters = '-00123'   --> None
    characters = 'hi'       --> None
    characters = ''         --> None
    ```
    """
    number = ''
    for c in characters:
        if c in string_of_uints_no0:
            number += c
        else:
            # streak of real digits broken
            break
    return int(number) if number else None
