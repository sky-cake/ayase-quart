from ayase_quart.search.providers.lnx import sanitize_free_text, get_term_query


def test_sanitize_free_text():
    # lnx converts this to deg
    assert sanitize_free_text('°') == '°'

    assert sanitize_free_text("don't") == "don't"
    
    assert sanitize_free_text('sun and sky') == 'sun and sky'

    assert sanitize_free_text('foo(bar)') == 'foo bar'
    assert sanitize_free_text('3:30') == '3 30'
    assert sanitize_free_text('^a^b^') == 'a b'
    assert sanitize_free_text('{a}[b]') == 'a b'
    assert sanitize_free_text('a`b[]()') == 'a b'

    assert sanitize_free_text('"exact phrase"') == '"exact phrase"'
    assert sanitize_free_text('foo "bar baz"') == 'foo "bar baz"'
    assert sanitize_free_text('"search ""engine"') == '"search ""engine"'

    assert sanitize_free_text('he "llo') == 'he llo'
    assert sanitize_free_text('"unclosed') == 'unclosed'
    assert sanitize_free_text('""') == ''

    assert sanitize_free_text('>70') == '70'
    assert sanitize_free_text('>=5') == '=5'
    assert sanitize_free_text('<5') == '5'
    assert sanitize_free_text('<=10') == '=10'

    assert sanitize_free_text('a >b') == 'a b'
    assert sanitize_free_text('a<b') == 'a<b'

    assert sanitize_free_text('-z ') == 'z' # leading - errors for alpha
    assert sanitize_free_text('-66 ') == '66' # leading - ok for int
    assert sanitize_free_text('+35') == '+35'
    assert sanitize_free_text('-66+80') == '66+80'
    assert sanitize_free_text('-66 -80') == '66 -80'
    assert sanitize_free_text('-66 +80 ') == '66 +80'

    assert sanitize_free_text('e-mail') == 'e-mail'
    assert sanitize_free_text('+devices +usb-c +e-waste -adapter') == '+devices +usb-c +e-waste -adapter'

    # we'll just strip the symbols here
    assert sanitize_free_text(' ++35') == '35'
    assert sanitize_free_text('-+-+66') == '66'
    assert sanitize_free_text('--66+80') == '66+80' # could be unintentionally inversed, but oh well

    assert sanitize_free_text('c++') == 'c++'
    assert sanitize_free_text('c+-') == 'c+-'
    assert sanitize_free_text('c--') == 'c--'


    assert sanitize_free_text('- ') == ''
    assert sanitize_free_text(' +') == ''
    assert sanitize_free_text('+') == ''

    assert sanitize_free_text('*35') == '*35'

    # NOT results in nothing, but it's not an LNX error response, so we don't strip it
    assert sanitize_free_text('a AND b OR NOT c') == 'a AND b OR NOT c'

    assert sanitize_free_text('...') == '...'
    assert sanitize_free_text('a.b,c;d~e') == 'a.b,c;d~e'

    assert sanitize_free_text('::') == ''
    assert sanitize_free_text(':()[]:') == ''

    assert sanitize_free_text(':()[]:z') == 'z'

    assert sanitize_free_text('') == ''

    # lnx/deunicode will handle this
    # https://github.com/kornelski/deunicode/#examples
    assert sanitize_free_text('🎃☣ emoji') == '🎃☣ emoji'
    assert sanitize_free_text('étude') == 'étude'
    assert sanitize_free_text('37°C') == '37°C'


def test_get_term_query():
    assert get_term_query('comment', 'foo(bar) >70') == {
        'occur': 'must',
        'normal': {
            'ctx': 'comment:foo bar 70',
        },
    }

    assert get_term_query('comment', '::') is None
    assert get_term_query('comment', '') is None


if __name__=='__main__':
    test_sanitize_free_text()
    test_get_term_query()
