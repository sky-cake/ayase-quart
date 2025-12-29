from typing import Any

from orjson import dumps, loads

from configs import index_search_conf

from . import POST_PK, IndexSearchQuery, SearchIndexField, search_index_fields
from .baseprovider import BaseSearch

pk = POST_PK
lnx_conf = index_search_conf.get('lnx', {})


def get_term_query(fieldname: str, terms: str) -> list[dict]:
    query = []

    # split and loop because lnx 0.9.0 uses tantivy 0.18 https://docs.rs/tantivy/0.18.1/tantivy/query/struct.QueryParser.html
    # require format for "barack obama": ["title:barack", "body:barack", "title:obama", "body:obama"]
    # terms = terms.replace('"', '')
    if terms:
        query.append({ # quoted terms can't use the fields: [] combo, must OR search fields
            'occur': 'must',
            'normal': {
                'ctx': f'{fieldname}:{terms.strip()}',
            },
        })
    return query


class LnxSearch(BaseSearch):
    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)

    def _get_index_url(self, index: str):
        return f'{self.host}/indexes/{index}'

    async def _create_index(self, index: str):
        url = self.host + '/indexes'
        payload = {
            "override_if_exists": True,
            "index": {
                "name": index,
                "storage_type": "filesystem",
                'fields': {f.field: get_lnx_field(f) for f in search_index_fields},
                # https://github.com/miyachan/torako/blob/master/src/storage/search_lnx/posts.json
                # "fields": {
                #     "property1": {
                #         "type": "f64",
                #         "stored": True,
                #         "indexed": True,
                #         "multi": False,
                #         "fast": False
                #     }
                # },
                'search_fields': ['title', 'comment', 'media_filename'],
                "boost_fields": {},
                "max_concurrency": lnx_conf.get('max_concurrency', 4),  # keep low for larger datasets in config.toml
                "reader_threads": lnx_conf.get('reader_threads', 4),  # set to number of vcpus in config.toml
                "writer_threads": lnx_conf.get('writer_threads', 4),  # set to number of vcpus in config.toml
                "writer_buffer": lnx_conf.get('writer_buffer', 268_435_456),  # 256MB
                "set_conjunction_by_default": True,  # default AND instead of OR for queries
                "use_fast_fuzzy": False,  # only exact match
                "strip_stop_words": False,  # keep words like 'the' and 'with'
                "auto_commit": 0,
            },
        }
        resp = await self.client.post(url, data=dumps(payload))
        resp = loads(await resp.read())

        if resp['status'] != 200:
            print(resp)

        await self._commit_write(index)


    async def _index_clear(self, index: str):
        url = self._get_index_url(index) + '/documents/clear'
        resp = await self.client.delete(url)
        return loads(await resp.read())

    async def _index_delete(self, index: str):
        url = self._get_index_url(index)
        await self.client.delete(url)
        # return loads(await resp.read())

    async def _index_ready(self, index: str):
        return True

    async def _index_stats(self, index: str):
        url = self._get_index_url(index) + '/stats'
        resp = await self.client.get(url)
        return loads(await resp.read())

    async def _add_docs(self, index: str, docs: list[Any]):
        # await self._remove_docs(index, get_doc_pks(docs))
        url = self._get_index_url(index) + '/documents'
        docs = [
            {k: [str(v)] for k, v in downcast_fields(doc).items()}
            for doc in docs
        ]
        await self.client.post(url, data=dumps(docs))
        # await self._commit_write(index)
        # return loads(await resp.read())

    async def _add_docs_bytes(self, index: str, docs: bytes):
        url = self._get_index_url(index) + '/documents'
        await self.client.post(url, data=docs)

    async def _remove_docs(self, index: str, pk_ids: list[str]):
        if not pk_ids:
            return
        url = self._get_index_url(index) + '/documents'
        resp = await self.client.delete(url, data=dumps({pk: pk_ids}))
        resp = loads(await resp.read())
        await self._commit_write(index)
        return resp

    async def _commit_write(self, index: str):
        url = self._get_index_url(index) + '/commit'
        resp = await self.client.post(url)
        resp = loads(await resp.read())
        if resp['status'] != 200:
            print(resp) # this can be 400 if the index does not exist yet, which is not an issue here
        return resp

    async def _finalize(self, index: str):
        await self._commit_write(index)

    def _get_post_pack_fn(self):
        return pack_post

    async def _search_index(self, index: str, q: IndexSearchQuery):
        url = self._get_index_url(index) + '/search'
        payload = {
            'query': self._query_builder(q),
            'limit': q.hits_per_page,
            'offset': 0 if q.page == 1 else (q.page - 1) * q.hits_per_page,
            'order_by': q.sort_by,
            'sort': q.sort,
        }
        resp = await self.client.post(url, data=dumps(payload))
        parsed = loads(await resp.read())

        if parsed['status'] != 200:
            print(parsed)

        parsed = parsed['data']
        if isinstance(parsed, str):
            raise ValueError(parsed)

        total = parsed.get('count', 0)
        hits = (_restore_result(r['doc']) for r in parsed['hits'])
        return hits, total

    def _query_builder(self, q: IndexSearchQuery):
        query = []
        if comment := q.comment:
            query.extend(get_term_query('comment', comment))

        if title := q.title:
            query.extend(get_term_query('title', title))

        if q.thread_nums:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': " OR ".join(f"thread_num:{thread_num}" for thread_num in q.thread_nums),
                    },
                }
            )
        if q.boards:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': " OR ".join(f"board:{b}" for b in q.boards),
                        # 'ctx': f'({" ".join(f"{b}" for b in q.boards)})',
                        # 'ctx': f" OR ".join(q.boards),
                        # 'ctx': f'board: IN [{" ".join(q.boards)}]',
                    },
                }
            )
        if q.board_2_nums:
            pair_strs = []
            for board, nums in q.board_2_nums.items():
                nums_str = ' OR '.join(f'num:{int(num)}' for num in nums)
                pair_str = f'(board:{board}) AND ({nums_str})'
                pair_strs.append(pair_str)
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': ' OR '.join(pair_strs),
                    },
                }
            )
        if q.tl:
            operator = q.tlop if hasattr(q, 'tlop') and q.tlop else '='
            if operator == '=':
                ctx = f'title_length:{q.tl}'
            else:
                ctx = f'title_length:{operator}{q.tl}'
            query.append({
                'occur': 'must',
                'normal': {
                    'ctx': ctx,
                },
            })
        if q.cl:
            operator = q.clop if hasattr(q, 'clop') and q.clop else '='
            if operator == '=':
                ctx = f'comment_length:{q.cl}'
            else:
                ctx = f'comment_length:{operator}{q.cl}'
            query.append({
                'occur': 'must',
                'normal': {
                    'ctx': ctx,
                },
            })
        if q.before is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'timestamp:<{q.before}',
                    },
                }
            )
        if q.after is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'timestamp:>{q.after}',
                    },
                }
            )
        if q.nums:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': " OR ".join(f"num:{num}" for num in q.nums),
                    },
                }
            )
        if q.num is not None and not q.nums:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'num:{q.num}',
                    },
                }
            )
        if q.op is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'op:{int(q.op)}',
                    },
                }
            )
        if q.deleted is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'deleted:{int(q.deleted)}',
                    },
                }
            )
        if q.sticky is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'sticky:{int(q.sticky)}',
                    },
                }
            )
        if q.capcode is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'capcode:{q.capcode}',
                    },
                }
            )
        if (q.has_file is not None) or (q.has_no_file is not None):
            query.append(
                {
                    'occur': 'mustnot' if q.has_file or (not q.has_no_file) else 'must',
                    'normal': {
                        'ctx': 'media_filename:None',
                        # 'ctx': f'{"" if q.has_file else "-"}(media_filename:None)',
                    },
                }
            )
        if q.media_hash is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'media_hash:{q.media_hash}',
                    },
                }
            )
        if q.media_filename:
            query.extend(get_term_query('media_filename', q.media_filename))
        if q.trip is not None:
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': f'trip:{q.trip}',
                    },
                }
            )
        if q.width: # anything not 0
            operator = q.wop if hasattr(q, 'wop') and q.wop else '='
            if operator == '=':
                ctx = f'media_w:{q.width}'
            else:
                ctx = f'media_w:{operator}{q.width}'
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': ctx,
                    },
                }
            )
        if q.height: # anything not 0
            operator = q.hop if hasattr(q, 'hop') and q.hop else '='
            if operator == '=':
                ctx = f'media_h:{q.height}'
            else:
                ctx = f'media_h:{operator}{q.height}'
            query.append(
                {
                    'occur': 'must',
                    'normal': {
                        'ctx': ctx,
                    },
                }
            )
        return query


def get_lnx_field(field: SearchIndexField):
    ftype = _get_field_type(field)
    lnx_field = {
        'type': ftype,
        'stored': field.field in ('comment', 'data'),
    }
    not_text = ftype not in ('string', 'text')
    filt_sort = any((field.filterable, field.sortable))
    if not_text and filt_sort:
        lnx_field['indexed'] = True
        lnx_field['fast'] = False
    if field.sortable:
        lnx_field['fast'] = True
    return lnx_field


def _get_field_type(field: SearchIndexField):
    if field.searchable:
        return 'text'
    elif field.field_type is str:
        return 'string'
    elif field.field_type is int:
        return 'u64'
    elif field.field_type is float:
        return 'f64'
    elif field.field_type is bool:
        return 'u64'


def _restore_result(doc: dict):
    if doc['comment'] == '':
        doc['comment'] = None
    return doc
    # return {'comment': doc['comment'], **loads(doc['data'])}


def pack_post(post: dict) -> dict:
    post = downcast_fields(post)
    return {k: [str(v)] for k, v in post.items()}


# bool_fields = ('op', 'deleted', 'sticky',)
bool_fields = tuple(f.field for f in search_index_fields if f.field_type is bool)
# str_fields = ('comment', 'title', 'media_filename', 'media_hash')
str_fields = tuple(f.field for f in search_index_fields if f.field_type is str)
do_not_downcast_str_fields = ('media_filename',)
def downcast_fields(post: dict):
    for field in bool_fields:
        post[field] = int(bool(post[field]))
    for field in str_fields:
        if post[field] is None and field not in do_not_downcast_str_fields:
            post[field] = ''
    return post
