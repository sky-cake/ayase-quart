# Do not import CONSTS

from werkzeug.exceptions import NotFound


def validate_threads(threads: list[dict]):
    if len(threads) < 1:
        raise NotFound(threads)

def validate_post(post: dict|None):
    if not post:
        raise NotFound(post)

def positive_int(value: int|float|str, lower: int=0, upper: int=None) -> int:
    """Clamps a value within the range:

    `lower <= abs(int(value)) <= upper`
    """
    value = max(abs(int(value)), lower)
    if upper is not None:
        value = min(value, upper)
    return value


def test_positive_int():
    assert positive_int(5) == 5
    assert positive_int(-5) == 5
    assert positive_int(10, lower=5) == 10
    assert positive_int(10, lower=5, upper=15) == 10
    assert positive_int(20, lower=5, upper=15) == 15
  
    assert positive_int(5.5) == 5
    assert positive_int(-5.5) == 5
    assert positive_int(10.5, lower=5) == 10
    assert positive_int(10.5, lower=5, upper=15) == 10
    assert positive_int(20.5, lower=5, upper=15) == 15
  
    assert positive_int('5') == 5
    assert positive_int('-5') == 5
    assert positive_int('10', lower=5) == 10
    assert positive_int('10', lower=5, upper=15) == 10
    assert positive_int('20', lower=5, upper=15) == 15
  
    assert positive_int(0) == 0
    assert positive_int(-0) == 0
    assert positive_int(0, lower=5) == 5
    assert positive_int(0, lower=5, upper=10) == 5

    print("All tests passed.")


