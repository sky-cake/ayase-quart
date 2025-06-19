string_of_uints = '0123456789'
string_of_uints_no0 = '123456789'

def startswith_uint(characters: str) -> bool:
    """
    See tests for behavior
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
    See tests for behavior
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
    See tests for behavior
    """
    if not characters:
        return False
    return all(c in string_of_uints for c in characters)


def get_prefix_uint(characters: str) -> int | None:
    """
    See tests for behavior
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
    See tests for behavior
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
