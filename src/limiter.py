from flask import request
from flask_limiter import Limiter

from configs2 import redis_conf

REDIS_LIMITER_DB = f"redis://{redis_conf['host']}:{redis_conf['port']}/{redis_conf['db']}"

def get_ip_address():
    ip = request.headers.get("X-Forwarded-For", None)
    if ip:
        return ip

    if request.remote_addr:
        return request.remote_addr

    return "127.0.0.1"


limiter = Limiter(
    get_ip_address,
    storage_uri=REDIS_LIMITER_DB,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)
