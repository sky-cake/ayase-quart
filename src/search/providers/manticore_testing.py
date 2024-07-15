import decimal
import json
import time

import manticoresearch
import mysql.connector
import requests
from manticoresearch.api import search_api
from manticoresearch.model import SortOrder
from manticoresearch.model.search_request import SearchRequest

from configs import CONSTS

config = manticoresearch.Configuration(host="http://127.0.0.1:9308")
client = manticoresearch.ApiClient(config)
indexApi = manticoresearch.IndexApi(client)
searchApi = manticoresearch.SearchApi(client)

board_cols_to_type = {
    'doc_id': 'INTEGER',
    'media_id': 'INTEGER',
    'poster_ip': 'TEXT',
    'num': 'INTEGER',
    'subnum': 'INTEGER',
    'thread_num': 'INTEGER',
    'op': 'INTEGER',
    '`timestamp`': 'INTEGER',
    'timestamp_expired': 'INTEGER',
    'preview_orig': 'TEXT',
    'preview_w': 'INTEGER',
    'preview_h': 'INTEGER',
    'media_filename': 'TEXT',
    'media_w': 'INTEGER',
    'media_h': 'INTEGER',
    'media_size': 'INTEGER',
    'media_hash': 'TEXT',
    'media_orig': 'TEXT',
    'spoiler': 'INTEGER',
    'deleted': 'INTEGER',
    'capcode': 'TEXT',
    'email': 'TEXT',
    'name': 'TEXT',
    'trip': 'TEXT',
    'title': 'TEXT',
    'comment': 'TEXT',
    'delpass': 'TEXT',
    'sticky': 'INTEGER',
    'locked': 'INTEGER',
    'poster_hash': 'TEXT',
    'poster_country': 'TEXT',
    'exif': 'TEXT',
}

class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super().default(o)
    
    def encode(self, obj, *args, **kwargs):
        lines = []
        for each in obj:
            line = super(Encoder, self).encode(each, *args, **kwargs)
            lines.append(line)
        return '\n'.join(lines)


def search(sql_string, verbose=False):
    url = 'http://localhost:9308/cli'
    response = requests.post(url, data=sql_string)

    if response.status_code != 200:
        raise ValueError(vars(response))
    if verbose: print(vars(response))
    return response


def get_asagi_sql_cols():
    return ', '.join(board_cols_to_type.keys())


# required since manticore doesn't like nulls.
def get_sql_cols_with_default_val(default=''):
    fields = [f"case when {k} is null then '{default}' else {k} end as {k}" for k in board_cols_to_type.keys()]
    return ', '.join(fields)


def fetch_from_mysql_and_slam_into_manticoresearch(index_name, board, batch_size=50_000):
    conn = mysql.connector.connect(**CONSTS.db_configs)
    cursor = conn.cursor(buffered=True, dictionary=True)
    cursor.execute(f"SELECT '{board}' as board, {get_sql_cols_with_default_val()} FROM `{board}`;")

    piped_rows = 0
    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch: break

        docs = []
        for row in batch:
            doc = {"insert": {"index": index_name, "id": 0, "doc": row}}
            docs.append(doc)
        docs = json.dumps(docs, cls=Encoder)
        result = indexApi.bulk(docs)
        assert not result.error and not result.errors # This does not guarantee it worked. We do another check later to see if records were populated or not
        piped_rows += len(batch)
        print(f'Piped rows: {piped_rows:,}')

    cursor.close()
    conn.close()

    return piped_rows


def setup(index_name, boards):
    search(f"drop table IF EXISTS {index_name}")

    asagi_cols_and_types = ', '.join(f'{k} {v}' for k, v in board_cols_to_type.items())
    sql_create = f"""
    create table IF NOT EXISTS {index_name}
    (
        board string,
        {asagi_cols_and_types}
    )
    html_strip='1'
    morphology='stem_en'
    """

    search(sql_create)

    for board in boards:
        is_empty_result = search(f"select board, {get_asagi_sql_cols()} from {index_name} where board='{board}' limit 10")._content.decode()
        assert 'Empty set ' in is_empty_result, is_empty_result

        fetch_from_mysql_and_slam_into_manticoresearch(index_name, board)

        is_not_empty_result = search(f"select board, {get_asagi_sql_cols()} from {index_name} where board='{board}' limit 10")._content.decode()
        assert 'Empty set ' not in is_not_empty_result, is_not_empty_result


def search_comment(boards, search_string):
    chars_to_escape = ['\\', '!', '"', '$', "'", '(', ')', '-', '/', '<', '@', '^', '|', '~']
    for char in chars_to_escape:
        search_string = search_string.replace(char, f'\{char}')

    with manticoresearch.ApiClient(config) as api_client:
        api_instance = search_api.SearchApi(api_client)

        search_request = SearchRequest(
            index=CONSTS.index_name,
            query={
                "bool": {
                    "must": [
                        { "match" : { "comment" : search_string } },
                        { "in": { "board": boards } }
                    ],
                }
            },
            limit=CONSTS.max_results,
            sort=SortOrder('timestamp', 'desc'),
            source=['doc_id', 'board', 'num', 'thread_num', 'comment'],
            max_matches=CONSTS.max_results,
        )
        api_response = api_instance.search(search_request)
        results = [x['_source'] for x in api_response.hits.hits]
    return results


if __name__=='__main__':
    # look for CONSTS. for config dependencies
    
    search_string = 'animalistic'
    boards = ['t']

    # setup('monolith', boards)

    start = time.time()
    results = search_comment(boards, search_string)
    print(f"{len(results)} results for '{search_string}' in {time.time()-start:.4f} seconds.")
    
    for r in results:
        print(r)