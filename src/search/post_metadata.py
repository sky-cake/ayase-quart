from datetime import datetime
from functools import lru_cache
# from base64 import a85encode, a85decode # 20% overhead vs 33% for base64, nvm so slow

# from zlib import compress, decompress
# from brotlicffi import compress, decompress # too slow
from zlib_ng.zlib_ng import compress, decompress # avx-512
# from orjson import loads, dumps
from msgpack import Packer, Unpacker # 90% smaller than json
from pybase64 import b64decode, b64encode
from posts.capcodes import id_2_capcode

'''
we don't want to hit the db for search queries (they're random and hard to use the indexes)
    keeping all the data in the search engine takes up space, which is worse at scale
    the current compression pipeline:
        keep only the values, because the keys are static
        encode them in messagepack as its over 90% smaller than json
            mostly because most of the values are going to be None, 0 and empty string
        compress the message pack with zlib_ng
            brotli is slow and its dictionary advantages are lost without json
            zlib_ng is the accelerated implementation of zlib, similar to orjson vs json
            since we have all the data, we should pursue training a zstd dictionary
        encode the compressed bytes with base64
            because lnx doesn't support byte fields yet (hopefully soon, tantivy has had support for a while now)
            would have prefered ascii85
                it's 4 bytes packed into 5 characters (20% overhead), vs 3 bytes packed into 4 characters for base64 (33% overhead)
                but the built-in version is incredibly slow, and pybase64 is incredibly fast
    
    pack_metadata goes through the compression pipeline for a dict
    
    unpack_metadata reverts it
        zlib decompresses at 400 MB/s vs zstd at 2 GB/s
            https://github.com/facebook/zstd#benchmarks

only keep fields needed to render search result posts
    start with fields from asagi_converter.py:get_selector but only those needed for:
        index_search_post_t.html
        template_optimizer.py
    remove fields used for indexing
        op
        deleted
        timestamp (time/now)
        mediahash (md5)
        no (num)
        board (board_shortname)

since the keys/fields are always the same, some optimisations:
    since its a single layer dict, we can just keep the values in a list
    the values must be kept in the same order, otherwise unpacking will be incorrect
        if the keys/fields are changed, everything must re-indexed

optimal order: zero values first, then common values, finally uncommon values
    compression relies on repeated patterns, the more similar the data, the better the compression
    example of zero values: null, 0, empty string, empty list
    example of common values: board_shortname, capcodes, countries
    example of uncommon values: file sizes, replies, timestamps

'''
fields = (
    'sticky',
    'closed',
    'spoiler',
    'trip',
    'since4pass',
    'poster_hash',
    'country',
    'troll_country',
    'sub',
    'name',
    'email',
    'capcode',
    'filedeleted',
    'board_shortname',
    'filename',
    'asagi_filename',
    'asagi_preview_filename',
    'exif',
    'md5',
    'ext',
    'fsize',
    'w',
    'h',
    'tn_w',
    'tn_h',
    'replies',
    'no',
    'resto',
    'deleted_time',
    'time',
)

# never tz aware
#  _fmt = '10/29/15 (Thu) 22:33:37'
now_fmt = '%m/%d/%y (%a) %H:%M:%S'
def ts_2_now(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime(now_fmt)

def now_2_ts(now: str) -> int:
    return int(datetime.strptime(now, now_fmt).timestamp())

msgp_p = Packer()
def pack_metadata(row: dict) -> str:
    row['board_shortname'] = board_2_int(row['board_shortname'])
    if row['name'] == 'Anonymous':
        row['name'] = None
    if del_time := row['deleted_time']:
        # something wrong with the dumps
        row['deleted_time'] = 0 if del_time.startswith('12/31/69') else now_2_ts(del_time)
    return b64encode(compress(msgp_p.pack([row.get(f) for f in fields]), level=9, wbits=-15)).decode()

DECOMP_BUFFER_SIZE = 128
msgp_u = Unpacker()
from time import perf_counter_ns
def unpack_metadata(data: str, comment: str) -> dict:
    msgp_u.feed(decompress(b64decode(data, validate=True), wbits=-15, bufsize=DECOMP_BUFFER_SIZE))
    data = msgp_u.unpack()
    post = {k:v for k,v in zip(fields, data)}
    post['now'] = ts_2_now(data[-1])
    post['board_shortname'] = int_2_board(post['board_shortname'])
    post['capcode'] = id_2_capcode(post['capcode'])
    post['comment'] = comment
    return post

# START PRIMARY KEY GENERATION
'''
64 bits unsigned int primary key
    lower 32 bits for num
    upper 32 bits for board
1 null + 10 digits + 26 letters = 37 possibilities => round up to 64 => 6 bits_per_char
    0 is null
    1-10 is 0-9
    11-36 is a-z
32 bits / 6 bits_per_char = 5 chars max
'''
@lru_cache()
def board_2_int(board: str) -> int:
    '''encode a str board to u32'''
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

@lru_cache()
def int_2_board(board_int: int) -> str:
    '''decode a u32 board to str'''
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
    '''combine str board + u32 num to u64 pk'''
    board_bits = board_2_int(board)
    return (board_bits << 32) + num

def board_int_num_2_pk(board_int: int, num: int) -> int:
    '''
    combine u32 board + u32 num to u64 pk
    
    useful if the u32 board has been generated already
    '''
    return (board_int << 32) + num

board_mask = 0xFFFFFFFF << 32
num_mask = 0xFFFFFFFF
def pk_2_board_num(pk: int) -> tuple[str, int]:
    '''revert u64 pk to str board and u32 num tuple'''
    num = pk & num_mask
    board = int_2_board((pk & board_mask) >> 32)
    return board, num
# END PRIMARY KEY GENERATION
