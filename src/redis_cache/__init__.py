from enum import Enum

from coredis import Redis

from configs import redis_conf


class RedisDbNumber(Enum):
    auth: int = 1

async def get_redis(db: RedisDbNumber) -> Redis:
    if not hasattr(get_redis, 'client'):
        get_redis.client = Redis(host=redis_conf['host'], port=redis_conf['port'], db=db.value)
        await get_redis.client.flushdb()
        return get_redis.client
    return get_redis.client
