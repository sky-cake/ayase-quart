from quart import current_app
import manticoresearch
import orjson
import httpx

config = manticoresearch.Configuration(host="http://127.0.0.1:9308")
client = manticoresearch.ApiClient(config)
indexApi = manticoresearch.IndexApi(client)
searchApi = manticoresearch.SearchApi(client)
utilsApi = manticoresearch.UtilsApi(client)

async def search(sql_string):
	url = 'http://localhost:9308/cli'
	response = await httpx.post(url, data=sql_string)
	# response = requests.post(url, data=sql_string)

	if response.status_code != 200:
		raise ValueError(vars(response))
	print(vars(response))
	return response

async def fetch_from_mysql_and_slam_into_manticoresearch(board='g', batch_size=50_000):
	async with current_app.db_pool.acquire() as connection:
		async with connection.cursor(buffered=True) as cursor:
			await cursor.execute(f"SELECT title, comment FROM {board} limit 123456;")

		while True:
			batch = await cursor.fetchmany(batch_size)
			if not batch: break

			docs = []
			for row in batch:
				doc = {"insert": {"index": 'monolith', "id": 0, "doc": {"board": board, "title": row[0] if row[0] else '', "comment": row[1] if row[1] else ''}}}
				docs.append(doc)
			docs = orjson.dumps(docs)
			res = indexApi.bulk(docs)
			print(vars(res))

		cursor.close()
	# conn.close()

# result = search("create table IF NOT EXISTS monolith (board text, title text, comment text) html_strip='1' morphology='stem_en'")
fetch_from_mysql_and_slam_into_manticoresearch()
# result = search("select * from monolith")

from manticoresearch.api import search_api
from manticoresearch.model.search_request import SearchRequest

result = search("select board, comment from monolith where match('wireguard network') limit 2").content.decode()
# +-----
# | board | comment		  |
# +-----
# | g	 | >>96481209  |
# |	   | you need 0.0.0.0 to route everything to the wireguard peer.   |
# |	   | if you check the "exclude private IPs" I assume it won't route everything, only internet destinations. Since I use wireguard to reach my locally run services I would never check that box, but it might let you reach the local printers since it won't forward private addresses to your wireguard network. |
# | g	 | >>96481209			 |
# |	   | you need 0.0.0.0 to route everything to the wireguard peer.		 |
# |	   | if you check the "exclude private IPs" I assume it won't route everything, only internet destinations. Since I use wireguard to reach my locally run services I would never check that box, but it might let you reach the local printers since it won't forward private addresses to your wireguard network. |
# +---
with manticoresearch.ApiClient(config) as api_client:
	api_instance = search_api.SearchApi(api_client)
	search_request = SearchRequest(
		index='monolith',
		query={'query_string': '@comment \"wireguard network\"'},
		limit=2,
	)
	api_response = api_instance.search(search_request)
	print(api_response)
# {'aggregations': None,
#  'hits': {'hits': [{'_id': 8217302394799675003,
#		 '_score': 2643,
#		'_source': {'board': 'g',
#		  'comment': '>>96481209\n'
#	   'you need 0.0.0.0 to route '
#	   'everything to the wireguard peer.\n'