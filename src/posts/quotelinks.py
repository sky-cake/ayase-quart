from collections import defaultdict
from html import escape


def get_quotelink_lookup(rows: list[dict]) -> dict[int, list[int]]:
    """
    Returns a dict of post numbers to reply post numbers.
    Not multi board safe (`num`s are reused across boards).
    """
    post_2_quotelinks = defaultdict(list)
    for row in rows:
        if not (comment := row.get('comment')):
            continue
        num = row['num']
        for quotelink in extract_quotelinks(comment):
            post_2_quotelinks[quotelink].append(num)
    return post_2_quotelinks

def extract_quotelinks(comment: str, html=False) -> list[int]:
    """Given some escaped post/comment, `text`, returns a list of all the quotelinks (>>123456) in it."""
    quotelinks = []

    # if the comment is not already html escaped, escape it
    comment_esc = comment if html else escape(comment)
    
    # text = '>>20074095\n>>20074101\nYou may be buying the wrong eggs'
    lines = comment_esc.split("\n")

    GTGT = "&gt;&gt;"
    for line in lines:
        if not line.startswith(GTGT):
            continue
        tokens = line.split(" ")
        for token in tokens:
            if token[:8] == GTGT and token[8:].isdigit():
                quotelinks.append(int(token[8:]))

    return quotelinks  # quotelinks = [20074095, 20074101]