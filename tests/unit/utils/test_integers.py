from utils.integers import (
    startswith_uint,
    startswith_uint_no0,
    is_uint,
    get_prefix_uint,
    get_prefix_uint_no0,
    clamp_positive_int,
)

def test_startswith_uint():
    assert startswith_uint('1') == True
    assert startswith_uint('1x') == True
    assert startswith_uint('x') == False
    assert startswith_uint('x0') == False
    assert startswith_uint('10') == True
    assert startswith_uint('123') == True
    assert startswith_uint('0123') == True
    assert startswith_uint('01') == True
    assert startswith_uint('01203') == True
    assert startswith_uint('12300') == True
    assert startswith_uint('123.') == True
    assert startswith_uint('123x') == True
    assert startswith_uint('x123') == False
    assert startswith_uint('123⑨⑨45') == True
    assert startswith_uint('⑨') == False
    assert startswith_uint('-123') == False
    assert startswith_uint('-00123') == False
    assert startswith_uint('xx') == False
    assert startswith_uint('') == False

def test_startswith_uint_no0():
    assert startswith_uint_no0('1') == True
    assert startswith_uint_no0('1x') == True
    assert startswith_uint_no0('x') == False
    assert startswith_uint_no0('x0') == False
    assert startswith_uint_no0('10') == True
    assert startswith_uint_no0('123') == True
    assert startswith_uint_no0('0123') == False
    assert startswith_uint_no0('01') == False
    assert startswith_uint_no0('01203') == False
    assert startswith_uint_no0('12300') == True
    assert startswith_uint_no0('123.') == True
    assert startswith_uint_no0('123x') == True
    assert startswith_uint_no0('x123') == False
    assert startswith_uint_no0('123⑨⑨45') == True
    assert startswith_uint_no0('⑨') == False
    assert startswith_uint_no0('-123') == False
    assert startswith_uint_no0('-00123') == False
    assert startswith_uint_no0('xx') == False
    assert startswith_uint_no0('') == False

def test_is_uint():
    assert is_uint('123') == True
    assert is_uint('0123') == True
    assert is_uint('01203') == True
    assert is_uint('12300') == True
    assert is_uint('123.') == False
    assert is_uint('123x') == False
    assert is_uint('x123') == False
    assert is_uint('123⑨⑨45') == False
    assert is_uint('-123') == False
    assert is_uint('-00123') == False
    assert is_uint('hi') == False
    assert is_uint('') == False

def test_get_prefix_uint():
    assert get_prefix_uint('01') == 1
    assert get_prefix_uint('1x') == 1
    assert get_prefix_uint('1') == 1
    assert get_prefix_uint('123') == 123
    assert get_prefix_uint('0123') == 123
    assert get_prefix_uint('01203') == 1203
    assert get_prefix_uint('12300') == 12300
    assert get_prefix_uint('123.') == 123
    assert get_prefix_uint('123x') == 123
    assert get_prefix_uint('x123') == None
    assert get_prefix_uint('123⑨⑨45') == 123
    assert get_prefix_uint('-123') == None
    assert get_prefix_uint('-00123') == None
    assert get_prefix_uint('hi') == None
    assert get_prefix_uint('') == None

def test_get_prefix_uint_no0():
    assert get_prefix_uint_no0('1') == 1
    assert get_prefix_uint_no0('1x') == 1
    assert get_prefix_uint_no0('x') == None
    assert get_prefix_uint_no0('x0') == None
    assert get_prefix_uint_no0('10') == 10
    assert get_prefix_uint_no0('123') == 123
    assert get_prefix_uint_no0('0123') == None
    assert get_prefix_uint_no0('01') == None
    assert get_prefix_uint_no0('01203') == None
    assert get_prefix_uint_no0('12300') == 12300
    assert get_prefix_uint_no0('123.') == 123
    assert get_prefix_uint_no0('123x') == 123
    assert get_prefix_uint_no0('x123') == None
    assert get_prefix_uint_no0('123⑨⑨45') == 123
    assert get_prefix_uint_no0('⑨') == None
    assert get_prefix_uint_no0('-123') == None
    assert get_prefix_uint_no0('-00123') == None
    assert get_prefix_uint_no0('xx') == None
    assert get_prefix_uint_no0('') == None

def test_clamp_positive_int():
    assert clamp_positive_int(5) == 5
    assert clamp_positive_int(-5) == 5
    assert clamp_positive_int(10, lower=5) == 10
    assert clamp_positive_int(10, lower=5, upper=15) == 10
    assert clamp_positive_int(20, lower=5, upper=15) == 15

    assert clamp_positive_int(5.5) == 5
    assert clamp_positive_int(-5.5) == 5
    assert clamp_positive_int(10.5, lower=5) == 10
    assert clamp_positive_int(10.5, lower=5, upper=15) == 10
    assert clamp_positive_int(20.5, lower=5, upper=15) == 15

    assert clamp_positive_int('5') == 5
    assert clamp_positive_int('-5') == 5
    assert clamp_positive_int('10', lower=5) == 10
    assert clamp_positive_int('10', lower=5, upper=15) == 10
    assert clamp_positive_int('20', lower=5, upper=15) == 15

    assert clamp_positive_int(0) == 0
    assert clamp_positive_int(-0) == 0
    assert clamp_positive_int(0, lower=5) == 5
    assert clamp_positive_int(0, lower=5, upper=10) == 5
