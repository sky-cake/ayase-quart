from datetime import datetime
from async_lru import alru_cache
import asyncio
import csv
from tagging.enums import Ratings, TagData, TagType, SafeSearch
from tagging.utils import get_sha256_from_path, make_path
import sqlite3
from db import db_q


def make_tag_data() -> TagData:
    path = make_path('tags.csv')
    names = []
    rating, general, character = [], [], []
    with open(path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for idx, row in enumerate(reader):
            names.append(row['tag_name'])
            tag_type_id = int(row['tag_type_id'])
            if tag_type_id == TagType.rating.value:
                rating.append(idx)
            elif tag_type_id == TagType.general.value:
                general.append(idx)
            elif tag_type_id == TagType.character.value:
                character.append(idx)
    return TagData(names=names, rating=rating, general=general, character=character)


def get_phg(terms: list) -> str:
    if len(terms) < 1:
        raise ValueError(terms)
    return ','.join(['?'] * len(terms))


async def init_tagging():
    sqls = [
    """
        CREATE TABLE IF NOT EXISTS image (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            board TEXT,
            filename TEXT,
            sha256 TEXT,
            explicit REAL,
            sensitive REAL,
            questionable REAL,
            general REAL,
            ext TEXT,
            has_thumb INTEGER,
            UNIQUE(board, filename)
        );
    ""","""
        CREATE TABLE IF NOT EXISTS tag_type (
            pk INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_type_id INTEGER NOT NULL UNIQUE,
            tag_type_name TEXT NOT NULL UNIQUE
        )
    ""","""
        CREATE TABLE IF NOT EXISTS tag (
            pk INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id INTEGER NOT NULL UNIQUE, -- matches the csv row number
            tag_name TEXT NOT NULL,
            tag_type_id INTEGER NOT NULL,
            FOREIGN KEY (tag_type_id) REFERENCES tag_type(tag_type_id) ON DELETE CASCADE,
            UNIQUE (tag_name, tag_type_id)
        )
    ""","""
        CREATE TABLE IF NOT EXISTS image_tag (
            pk INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            prob REAL NOT NULL,
            FOREIGN KEY (image_id) REFERENCES image(image_id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tag(tag_id) ON DELETE CASCADE,
            UNIQUE (image_id, tag_id)
        )
    """
    ]

    idxs = """
    CREATE INDEX IF NOT EXISTS idx_image_explicit ON image (explicit);
    CREATE INDEX IF NOT EXISTS idx_image_sensitive ON image (sensitive);
    CREATE INDEX IF NOT EXISTS idx_image_questionable ON image (questionable);
    CREATE INDEX IF NOT EXISTS idx_image_general ON image (general);
    CREATE INDEX IF NOT EXISTS idx_tag_type_name ON tag_type (tag_type_name);
    CREATE INDEX IF NOT EXISTS idx_image_tag_image_id ON image_tag (image_id);
    CREATE INDEX IF NOT EXISTS idx_image_tag_tag_id ON image_tag (tag_id);
    CREATE INDEX IF NOT EXISTS idx_image_tag_image_id_prob ON image_tag (image_id, prob);
    CREATE INDEX IF NOT EXISTS idx_image_image_id ON image (image_id);
    CREATE INDEX IF NOT EXISTS idx_image_board_filename ON image(board, filename);
    CREATE INDEX IF NOT EXISTS idx_image_board_sha256 ON image(board, sha256);
    """

    sqls += [s.strip() for s in idxs.split('\n') if s.strip()]

    for s in sqls:
        await db_q.query_dict(s, commit=True)

    tags_exist = await is_tags_exist()

    if not tags_exist:
        s = """INSERT OR IGNORE INTO tag_type (tag_type_id, tag_type_name) VALUES (?, ?)"""
        for tag_type in TagType:
            await db_q.query_dict(s, (tag_type.value, tag_type.name), commit=True)

        await insert_tags()


async def is_tags_exist() -> bool:
    csv_tag_count = 10_861
    tag_count = (await db_q.query_tuple('SELECT COUNT(*) FROM tag'))[0][0]
    print(f'Found {tag_count}/{csv_tag_count} tags already in database.')
    return tag_count == csv_tag_count


async def insert_tags(tag_data: TagData=None):
    csv_tag_count = 10_861

    if not tag_data:
        tag_data = make_tag_data()

    params = [
        [(idx, tag_data.names[idx], TagType.rating.value) for idx in tag_data.rating],
        [(idx, tag_data.names[idx], TagType.general.value) for idx in tag_data.general],
        [(idx, tag_data.names[idx], TagType.character.value) for idx in tag_data.character],
    ]
    s = 'INSERT OR IGNORE INTO tag (tag_id, tag_name, tag_type_id) VALUES (?, ?, ?)'
    for p in params:
        await db_q.query_runner.run_query_many(s, p)

    tag_count = (await db_q.query_tuple('SELECT COUNT(*) FROM tag'))[0][0]
    if tag_count != csv_tag_count:
        raise ValueError()

    await db_q.pool_manager.save_all_pools()
    print()
    print('Inserted all tags from csv into db successfully.')
    print('Now you should populate the database. Run the tagging script agains some images.')


async def insert_image_tags(file_path: str, board: str, filename: str, ratings: dict, tag_id_2_prob: dict):
    sha256 = get_sha256_from_path(file_path)
    general, sensitive, questionable, explicit = ratings[Ratings.general.value], ratings[Ratings.sensitive.value], ratings[Ratings.questionable.value], ratings[Ratings.explict.value]
    s = """INSERT INTO image (board, filename, sha256, general, explicit, sensitive, questionable)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(board, filename)
        DO UPDATE
            SET
                sha256        = excluded.sha256,
                general       = excluded.general,
                explicit      = excluded.explicit,
                sensitive     = excluded.sensitive,
                questionable  = excluded.questionable
        RETURNING image_id
    """
    p = (board, filename, sha256, general, explicit, sensitive, questionable)
    row = (await db_q.query_tuple(s, p, commit=True))
    if not row:
        return []
    image_id = int(row[0][0])
    if not image_id:
        raise ValueError(image_id)
    params = [(image_id, tag_id, prob) for tag_id, prob in tag_id_2_prob.items()]
    try:
        await db_q.query_runner.run_query_many('INSERT INTO image_tag (image_id, tag_id, prob) VALUES (?, ?, ?)', params)
    except sqlite3.IntegrityError as e:
        error_msg = str(e).join('\n')[:256]
        print(f'Unique constraint failed: {image_id=} {tag_id_2_prob=} {error_msg=}')


async def _fetch_results(image_ids: list[int]) -> list[dict]:
    if len(image_ids) < 1:
        return []

    phg = get_phg(image_ids)
    rows = await db_q.query_tuple(f'SELECT image_id, image_path, general, explicit, sensitive, questionable FROM image WHERE image_id IN ({phg})', image_ids)
    if not rows:
        return []

    image_id_2_data = {row[0]: [row[1], row[2], row[3], row[4], row[5]] for row in rows}

    tags = await db_q.query_tuple(f"""
        SELECT image_tag.image_id, tag.tag_name, tag.tag_type_id, image_tag.prob
        FROM image_tag
            JOIN tag ON image_tag.tag_id = tag.tag_id
        WHERE image_tag.image_id IN ({phg})""",
        [k for k in image_id_2_data]
    )
    if not tags:
        return []

    results = {}
    tag_type_map = {TagType.rating.value: 'rating', TagType.general.value: 'general', TagType.character.value: 'character'}
    for image_id, (image_path, general, explicit, sensitive, questionable) in image_id_2_data.items():
        results[image_id] = {
            'image_id': image_id,
            'image_path': image_path,
            'rating': {'general': general, 'explicit': explicit, 'sensitive': sensitive, 'questionable': questionable},
            'general': {},
            'character': {},
        }

    for image_id, tag_name, tag_type_id, prob in tags:
        results[image_id][tag_type_map[tag_type_id]][tag_name] = prob

    return [results[image_id] for image_id in image_ids]


async def _fetch_result(image_id: int) -> dict:
    results = await _fetch_results([image_id])
    return results[0] if len(results) and results else None


async def get_tag_by_image_path(image_path: str) -> dict:
    row = (await db_q.query_tuple('SELECT image_id FROM image WHERE image_path = ?', (image_path,)))[0]
    if not row:
        return []
    result = await _fetch_result(row[0])
    return result


async def get_tag_by_sha256(sha256: str) -> dict:
    row = (await db_q.query_tuple('SELECT image_id FROM image WHERE sha256 = ?', (sha256,)))[0]
    if not row:
        return []
    result = await _fetch_result(row[0])
    return result


async def get_tags_by_tag_name(tag_name: str) -> list[dict]:
    s = """SELECT DISTINCT image_tag.image_id FROM tag JOIN image_tag ON tag.tag_id = image_tag.tag_id WHERE tag.tag_name = ?"""
    rows = await db_q.query_tuple(s, (tag_name,))
    if not rows:
        return []

    results = await _fetch_results([row[0] for row in rows])
    return results


@alru_cache(maxsize=2)
async def get_tags() -> list[tuple]:
    rows = await db_q.query_tuple('SELECT tag_id, lower(tag_name), tag_type_id FROM tag JOIN tag_type USING(tag_type_id)')
    if not rows:
        return []
    return rows


async def get_tags_by_type(tag_type: TagType):
    s = 'SELECT tag_id, tag_name FROM tag JOIN tag_type USING(tag_type_id) WHERE tag_type_id = ?'
    p = (tag_type.value,)
    rows = await db_q.query_tuple(s, p)
    if not rows:
        return []
    return rows


@alru_cache(maxsize=2)
async def _get_image_count(date: str) -> int:
    sql = """SELECT count(image_id) FROM image where general is not null;"""
    return int((await db_q.query_tuple(sql))[0][0])


async def get_image_count() -> int:
    """Utilizes a daily cache."""
    return await _get_image_count(datetime.now().strftime('%Y%m%d'))


async def _get_all_images() -> list[dict]:
    """Used for testing on small data sets"""
    rows = await db_q.query_tuple("""SELECT image_id FROM image ORDER BY image_id""")

    if not rows:
        return []

    image_ids = [row[0] for row in rows]

    results = await _fetch_results(image_ids)
    return results


async def get_board_2_media_origs_by_tag_ids(tag_ids: list[int], f_tag: float, safe_search: SafeSearch, board_shortnames: list[str], page: int=None, per_page: int=None) -> dict[str, list]:
    """Filenames are called `media_orig` in asagi"""
    sql_offset = ''
    if page is not None and per_page is not None:
        offset = int(max(page - 1, 0) * per_page)
        sql_offset = f'OFFSET {offset}'

    sql_limit = ''
    if per_page is not None:
        sql_limit = f'LIMIT {int(per_page)}'

    sql_tag_ids = ''
    if tag_ids:
        sql_tag_ids = f'AND image_tag.tag_id IN ({get_phg(tag_ids)})'

    sql_safe_search = ''
    f_nsfw_tags = 'image_tag.tag_id NOT IN (94, 113, 48)' # 'image_tag.tag_name NOT IN ('nude', 'penis', 'nipples')'
    if safe_search == SafeSearch.safe:
        sql_safe_search = f'AND (general >= 0.3) AND (explicit < 0.02) AND (questionable < 0.5) AND {f_nsfw_tags}'

    elif safe_search == SafeSearch.moderate:
        sql_safe_search = f'AND (general >= 0.1) AND (explicit < 0.1) AND (questionable < 0.92) AND {f_nsfw_tags}'

    params = tag_ids if tag_ids else None
    sql_calls = []
    for board_shortname in board_shortnames:
        sql = f"""
        SELECT
            filename
        FROM image
        WHERE image_id in (
            SELECT image_id
            FROM image JOIN image_tag USING(image_id)
            WHERE
                -- image_tag.prob >= {float(f_tag)} AND
                board = '{board_shortname}'
                {sql_tag_ids}
                {sql_safe_search}
            GROUP BY image_tag.image_id
            HAVING COUNT(image_tag.tag_id) >= {len(tag_ids)}
            ORDER BY image_tag.prob DESC {sql_limit} {sql_offset}
        )
        """
        # print(dedent(sql))
        sql_calls.append(db_q.query_tuple(sql, params))

    if not sql_calls:
        return {}

    rows = await asyncio.gather(*sql_calls)

    if not rows:
        return {}

    board_2_filenames = dict()
    for board_shortname, row in zip(board_shortnames, rows):
        if row:
            board_2_filenames[board_shortname] = [r[0] for r in row]
    return board_2_filenames


async def get_tags_like_tag_name(tag_name: str, tag_type_name: str) -> list[dict]:
    params = [f'%{tag_name}%']

    sql_tag_type_name = ''
    if tag_type_name:
        sql_tag_type_name = 'AND tag_type_name = ?'
        params.append(tag_type_name)

    s = f"""SELECT tag_id, tag_name, tag_type_name FROM tag JOIN tag_type USING(tag_type_id)
        WHERE tag.tag_name like ? {sql_tag_type_name}
    """
    rows = await db_q.query_tuple(s, params)
    if not rows:
        return []
    return rows


async def get_images_like_tag_name(tag_name: str) -> list[dict]:
    tag_name = f'%{tag_name}%'
    s = """SELECT DISTINCT image_tag.image_id FROM tag JOIN image_tag ON tag.tag_id = image_tag.tag_id
        WHERE tag.tag_name like ?
    """
    rows = await db_q.query_tuple(s, (tag_name,))
    if not rows:
        return []

    results = await _fetch_results([row[0] for row in rows])
    return results


async def get_image_has_tags_by_image_path(image_path: str) -> bool:
    sha256 = get_sha256_from_path(image_path)
    row = (await db_q.query_tuple('SELECT image_id FROM image WHERE sha256 = ?', (sha256,)))[0]
    return bool(row)


async def get_image_filenames_by_sha256_and_board(board: str, sha256: str) -> list:
    rows = await db_q.query_tuple('SELECT filename FROM image WHERE sha256 = ? and board = ?', (sha256, board,))
    if not rows:
        return []
    return rows


async def get_image_filenames_by_sha256_and_boards(boards: list[str], sha256: str) -> list:
    if not boards:
        return []

    sql = f'SELECT board, filename FROM image WHERE sha256 = ? and board IN ({get_phg(boards)})'
    params = [sha256] + boards
    rows = await db_q.query_tuple(sql, params)
    if not rows:
        return []
    return rows


async def get_sha256s() -> set[str]:
    return set(row[0] for row in (await db_q.query_tuple('SELECT sha256 FROM image')))


async def get_tagged_board_filename_pairs() -> set[str]:
    sql = """SELECT board, filename FROM image where board is not null and filename is not null"""
    return set((row[0], row[1]) for row in (await db_q.query_tuple(sql)))


async def get_untagged_board_filename_pairs(board: str) -> set[str]:
    sql = f"""SELECT board, filename FROM image where board = '{board}' and (general is null or sha256 is null) and ext not in ('webm', 'mp4');"""
    return set((row[0], row[1]) for row in (await db_q.query_tuple(sql)))
