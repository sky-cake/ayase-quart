from coredis import Redis

from configs import redis_conf


def get_redis(db: int) -> Redis:
    if not hasattr(get_redis, 'clients'):
        get_redis.clients = {}
    if db not in get_redis.clients:
        client = Redis(**redis_conf, db=db, decode_responses=False)
        get_redis.clients[db] = client
    return get_redis.clients[db]

def close_redis():
    if not hasattr(get_redis, 'clients'):
        return
    clients: dict[int, Redis] = get_redis.clients
    for client in clients.values():
        client.connection_pool.disconnect()
    del get_redis.clients
