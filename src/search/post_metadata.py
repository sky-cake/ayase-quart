from functools import cache

from msgpack import Packer, Unpacker  # 90% smaller than json
from pybase64 import b64decode, b64encode
from zlib_ng.zlib_ng import compress, decompress  # avx-512

from posts.capcodes import id_2_capcode

"""
To avoid frequent mysql/sqlite database lookups for random search queries, we store records in the search engine using generated, static PKs, and optimize for space using the following compression pipeline:

1. **MessagePack**: Encodes values, reducing size by over 90% compared to JSON (most values are `None`, `0`, or empty strings).
2. **Zlib_ng**: Compresses the MessagePack (chosen for speed over Brotli, which is slow without JSON). Analogous to orjson vs json.
3. **Base64**: Encodes the compressed data (due to lack of support for byte fields).

We focus on retaining only fields needed for rendering search results (fields consumed by: `index_search/post_t.html` and `template_optimizer.py`), so we  remove the following fields.

- op
- deleted
- ts_unix
- mediahash
- num
- board (board_shortname)

The data is packed into a list for faster access, and we ensure values stay in order for correct unpacking. Common and zero values are placed first to maximize compression efficiency. If the keys/fields are changed, everything must re-indexed.

Notes:

- zlib decompresses at 400 MB/s vs zstd at 2 GB/s. See https://github.com/facebook/zstd#benchmarks.
- zero values: null, 0, empty string, empty list
- common values: board_shortname, capcodes, countries
- uncommon values: file sizes, quotelinks, timestamps
"""

fields = (
    'sticky',
    'locked',
    'spoiler',
    'op',
    'trip',
    'since4pass',
    'poster_hash',
    'poster_country',
    'troll_country',
    'title',
    'name',
    'email',
    'capcode',
    'deleted',
    'board_shortname',
    'media_filename',
    'media_orig',
    'preview_orig',
    'exif',
    'media_hash',
    'media_size',
    'media_w',
    'media_h',
    'preview_w',
    'preview_h',
    'quotelinks',
    'num',
    'thread_num',
    'ts_expired',
    'ts_unix',
)

msg_packer: Packer = Packer()
def pack_metadata(row: dict) -> str:
    row['board_shortname'] = board_2_int(row['board_shortname'])
    if row['name'] == 'Anonymous':
        row['name'] = None
    return b64encode(compress(msg_packer.pack([row.get(f) for f in fields]), level=9, wbits=-15)).decode()


DECOMP_BUFFER_SIZE: int = 128
msg_unpacker: Unpacker = Unpacker()
def unpack_metadata(data: str, comment: str) -> dict:
    msg_unpacker.feed(decompress(b64decode(data, validate=True), wbits=-15, bufsize=DECOMP_BUFFER_SIZE))
    data = msg_unpacker.unpack()
    post = {k:v for k,v in zip(fields, data)}
    post['board_shortname'] = int_2_board(post['board_shortname'])
    post['capcode'] = id_2_capcode(post['capcode'])
    post['comment'] = comment
    return post


# START SEARCH ENGINE'S PRIMARY KEY GENERATION
"""
64 bits unsigned int primary key
    lower 32 bits for num
    upper 32 bits for board

1 null + 10 digits + 26 letters = 37 possibilities => round up to 64 => 6 bits_per_char
    0 is null
    1-10 is 0-9
    11-36 is a-z

32 bits / 6 bits_per_char = 5 chars max
"""
@cache
def board_2_int(board: str) -> int:
    """Encode a str board to u32"""
    if not (board := board.strip().lower()):
        return 0
    bits = []
    for char in reversed(board):
        if char.isalpha():
            bits.append(ord(char) - 86)
        elif char.isdigit():
            bits.append(int(char) + 1)
    res = 0
    for i, val in enumerate(bits):
        res |= (val << (i * 6))
    return res


@cache
def int_2_board(board_int: int) -> str:
    """Decode a u32 board to str"""
    chars = []
    mask = 63 # 0b111111
    while True:
        val = board_int & mask
        if val == 0:
            break
        if val <= 10:
            chars.append(str(val - 1))
        else:
            chars.append(chr(val + 86))
        board_int = board_int >> 6
    return ''.join(reversed(chars))


def board_num_2_pk(board: str, num: int) -> int:
    """Combine str board + u32 num to u64 pk"""
    board_bits = board_2_int(board)
    return (board_bits << 32) + num


def board_int_num_2_pk(board_int: int, num: int) -> int:
    """
    Combine u32 board + u32 num to u64 pk.
    Useful if the u32 board has been generated already.

    Example:

    If `board_int` = 0x12345678 and `num` = 0x9ABCDEF0, the function would perform:

    board_int << 32 --> 0x1234567800000000
    Add num --> 0x123456789ABCDEF0

    The result is a 64-bit integer (pk) where the upper 32 bits represent `board_int` and the lower 32 bits represent `num`.
    """
    return (board_int << 32) + num


board_mask = 0xFFFFFFFF << 32
num_mask = 0xFFFFFFFF
def pk_2_board_num(pk: int) -> tuple[str, int]:
    """Reverse of `board_int_num_2_pk()`.

    Reverts u64 `pk` to str `board` and u32 `num` tuple
    """
    num = pk & num_mask
    board = int_2_board((pk & board_mask) >> 32)
    return board, num

# END SEARCH ENGINE'S PRIMARY KEY GENERATION
