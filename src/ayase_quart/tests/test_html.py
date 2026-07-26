import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ayase_quart.posts.comments import clickable_links, html_bbcode


def test_clickable_links():
    cases = [
        # typical url
        ('text http://example.com text',
         'text <a href="http://example.com">http://example.com</a> text'),


        # ending sentences / punctuation
        ('text http://example.com/.',
         'text <a href="http://example.com/">http://example.com/</a>.'),

        ('text http://example.com. ..',
         'text <a href="http://example.com">http://example.com</a>. ..'),

        ('text http://example.com...',
        'text <a href="http://example.com">http://example.com</a>...'),

        ('text http://example.com/...',
        'text <a href="http://example.com/">http://example.com/</a>...'),

        ('text http://example.com!',
         'text <a href="http://example.com">http://example.com</a>!'),

        ('http://example.com',
        '<a href="http://example.com">http://example.com</a>'),

        ('text http://example.com/page, text',
         'text <a href="http://example.com/page">http://example.com/page</a>, text'),


        # tld needs to be 2+ chars
        ('text http://e.c?',
         'text http://e.c?'),


        # multiple tlds
        ('text http://sub.example.co.uk text',
         'text <a href="http://sub.example.co.uk">http://sub.example.co.uk</a> text'),


        # various edge cases
        ('text http://example.co!.. m! text',
         'text <a href="http://example.co">http://example.co</a>!.. m! text'),

        ('text http://example.com/?',
        'text <a href="http://example.com/?">http://example.com/?</a>'),

        ('text http://a.com, http://b.org!',
         'text <a href="http://a.com">http://a.com</a>, <a href="http://b.org">http://b.org</a>!'),

        ('text http://example.com/page/,/ text',
         'text <a href="http://example.com/page/,/">http://example.com/page/,/</a> text'),


        # ports
        ('http://beastie.sdf.org:4200/',
         '<a href="http://beastie.sdf.org:4200/">http://beastie.sdf.org:4200/</a>'),

        ('http://beastie.sdf.org:4200/q',
         '<a href="http://beastie.sdf.org:4200/q">http://beastie.sdf.org:4200/q</a>'),


        # text
        ('text text',
         'text text'),

        ('text https:// text',
         'text https:// text'),

        ('text https://s. text',
         'text https://s. text'),

        ('',
        ''),


        # query parms
        ('text http://example.com/page?id=123 text',
         'text <a href="http://example.com/page?id=123">http://example.com/page?id=123</a> text'),

        ('text http://example.com/page?id=123, text',
         'text <a href="http://example.com/page?id=123">http://example.com/page?id=123</a>, text'),

        ('text http://example.com/page?id=123,. text',
         'text <a href="http://example.com/page?id=123">http://example.com/page?id=123</a>,. text'),
    ]

    for comment, expected in cases:
        result = clickable_links(comment)
        assert result == expected, f'Failed for input: {comment}\nExpected: {expected}\nGot: {result}'


# 4chan api returns HTML:
# <a href="#p109368221" class="quotelink">&gt;&gt;109368221</a><br>Depends, can old forums handle parsing?<br><br><span class="quote">&gt;greentext</span><br> <span class="quote">&gt; spacey</span><br> <span class="quote">&gt; multiple &gt;</span><br><span class="deadlink">&gt;&gt;1</span><br><span class="deadlink">&gt;&gt;1</span> text <span class="deadlink">&gt;&gt;2</span><br><span class="quote">&gt;1</span><br><span class="quote">&gt;123 numeric</span><br><span class="quote">&gt;www.url.com/</span><br><span class="quote">&gt;&gt;www.url.com/</span><br>www.url.com/1/a/!/&amp;/6/;/55<br><pre class="prettyprint">count&lt;&lt;&quot;hello&quot;&lt;&lt;endl;</pre><br> <span class="quote">&gt; </span><br><pre class="prettyprint"> &gt; text </pre><br><pre class="prettyprint"> <span class="deadlink">&gt;&gt;123456</span> </pre><br>[spoiler]glowie[/spoiler]<br>[spoiler]&gt;glowie[/spoiler]<br>[spoiler]<pre class="prettyprint">&gt;glowie</pre>[/spoiler]<br><pre class="prettyprint">[spoiler]&gt;glowie[/spoiler]</pre>


def test_html_bbcode():
    cases = [
        # tags
        ('[spoiler]glowie[/spoiler]', '<span class="spoiler">glowie</span>'),
        ('[code]glowie[/code]', '<code>glowie</code>'),

        # :lit tags
        ('[spoiler:lit]glowie[/spoiler:lit]', '<span class="spoiler">glowie</span>'),
        ('[code:lit]glowie[/code:lit]', '<code>glowie</code>'),

        # mixed
        ('[spoiler:lit]a[/spoiler:lit] [spoiler]b[/spoiler]', '<span class="spoiler">a</span> <span class="spoiler">b</span>'),

        # no bb code
        ('text', 'text'),
        ('', ''),
        (None, None),

        # imbalanced :lit
        ('[spoiler:lit]text[/spoiler]', '<span class="spoiler">text</span>'),

        # straddle
        ('[spoiler][code]text[/spoiler][/code]', '<span class="spoiler">[code]text</span>[/code]'),
        ('[code][spoiler]text[/code][/spoiler]', '[code]<span class="spoiler">text[/code]</span>'),

        # nested
        ('[spoiler:lit][code]text[/code][/spoiler:lit]', '<span class="spoiler">[code]text[/code]</span>'),
        ('[spoiler:lit][code:lit]text[/code:lit][/spoiler:lit]', '<span class="spoiler">[code]text[/code]</span>'),
        ('[spoiler:lit][spoiler:lit]text[/spoiler:lit][/spoiler:lit]', '<span class="spoiler"><span class="spoiler">text</span></span>'),

        # real tag wrapping :lit content
        ('[code][spoiler:lit]text[/spoiler:lit][/code]', '[code]<span class="spoiler">text</span>[/code]'),

        # multiline content
        ('[spoiler]line1\nline2[/spoiler:lit]', '<span class="spoiler">line1\nline2</span>'),
        ('[code]line1\nline2[/code]', '<code>line1\nline2</code>'),
    ]

    for comment, expected in cases:
        result = html_bbcode(comment)
        assert result == expected, f'Failed for input: {comment!r}\nExpected: {expected!r}\nGot: {result!r}'


if __name__ == "__main__":
    test_clickable_links()
    test_html_bbcode()
    print('Passed')
