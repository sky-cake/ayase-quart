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
    assert startswith_uint('1')        == True
    assert startswith_uint('1x')       == True
    assert startswith_uint('x')        == False
    assert startswith_uint('x0')       == False
    assert startswith_uint('10')       == True
    assert startswith_uint('123')      == True
    assert startswith_uint('0123')     == True
    assert startswith_uint('01')       == True
    assert startswith_uint('01203')    == True
    assert startswith_uint('12300')    == True
    assert startswith_uint('123.')     == True
    assert startswith_uint('123x')     == True
    assert startswith_uint('x123')     == False
    assert startswith_uint('123⑨⑨45') == True
    assert startswith_uint('⑨')       == False
    assert startswith_uint('-123')     == False
    assert startswith_uint('-00123')   == False
    assert startswith_uint('xx')       == False
    assert startswith_uint('')         == False
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
    assert startswith_uint_no0('1')        == True
    assert startswith_uint_no0('1x')       == True
    assert startswith_uint_no0('x')        == False
    assert startswith_uint_no0('x0')       == False
    assert startswith_uint_no0('10')       == True
    assert startswith_uint_no0('123')      == True
    assert startswith_uint_no0('0123')     == False
    assert startswith_uint_no0('01')       == False
    assert startswith_uint_no0('01203')    == False
    assert startswith_uint_no0('12300')    == True
    assert startswith_uint_no0('123.')     == True
    assert startswith_uint_no0('123x')     == True
    assert startswith_uint_no0('x123')     == False
    assert startswith_uint_no0('123⑨⑨45') == True
    assert startswith_uint_no0('⑨')       == False
    assert startswith_uint_no0('-123')     == False
    assert startswith_uint_no0('-00123')   == False
    assert startswith_uint_no0('xx')       == False
    assert startswith_uint_no0('')         == False
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
    assert is_uint('123')      == True
    assert is_uint('0123')     == True
    assert is_uint('01203')    == True
    assert is_uint('12300')    == True
    assert is_uint('123.')     == False
    assert is_uint('123x')     == False
    assert is_uint('x123')     == False
    assert is_uint('123⑨⑨45') == False
    assert is_uint('-123')     == False
    assert is_uint('-00123')   == False
    assert is_uint('hi')       == False
    assert is_uint('')         == False
    ```
    """
    if not characters:
        return False
    return all(c in string_of_uints for c in characters)


def get_prefix_uint(characters: str) -> int | None:
    """
    ```
    assert get_prefix_uint('01')       == 1
    assert get_prefix_uint('1x')       == 1
    assert get_prefix_uint('1')        == 1
    assert get_prefix_uint('123')      == 123
    assert get_prefix_uint('0123')     == 123
    assert get_prefix_uint('01203')    == 1203
    assert get_prefix_uint('12300')    == 12300
    assert get_prefix_uint('123.')     == 123
    assert get_prefix_uint('123x')     == 123
    assert get_prefix_uint('x123')     == None
    assert get_prefix_uint('123⑨⑨45') == 123
    assert get_prefix_uint('-123')     == None
    assert get_prefix_uint('-00123')   == None
    assert get_prefix_uint('hi')       == None
    assert get_prefix_uint('')         == None
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
    """This function exists because we want a way to skip a fake quotelinks like >>0123.
    Quotelinks don't have left-0 padding.
    ```
    assert get_prefix_uint_no0('1')        == 1
    assert get_prefix_uint_no0('1x')       == 1
    assert get_prefix_uint_no0('x')        == None
    assert get_prefix_uint_no0('x0')       == None
    assert get_prefix_uint_no0('10')       == 10
    assert get_prefix_uint_no0('123')      == 123
    assert get_prefix_uint_no0('0123')     == None
    assert get_prefix_uint_no0('01')       == None
    assert get_prefix_uint_no0('01203')    == None
    assert get_prefix_uint_no0('12300')    == 12300
    assert get_prefix_uint_no0('123.')     == 123
    assert get_prefix_uint_no0('123x')     == 123
    assert get_prefix_uint_no0('x123')     == None
    assert get_prefix_uint_no0('123⑨⑨45') == 123
    assert get_prefix_uint_no0('⑨')       == None
    assert get_prefix_uint_no0('-123')     == None
    assert get_prefix_uint_no0('-00123')   == None
    assert get_prefix_uint_no0('xx')       == None
    assert get_prefix_uint_no0('')         == None
    ```
    """
    if not characters:
        return None

    if not (number := characters[0]) in string_of_uints_no0:
        return None

    # surprisingly, [1:] is never out of bounds when len(charactes) == 1
    for c in characters[1:]:
        if c in string_of_uints:
            number += c
        else:
            # streak of real digits broken
            break
    return int(number)
