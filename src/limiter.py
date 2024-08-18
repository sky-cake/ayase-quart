from flask import request
from flask_limiter import Limiter

from configs import CONSTS


def get_ip_address():
    ip = request.headers.get("X-Forwarded-For", None)
    if ip:
        return ip

    if request.remote_addr:
        return request.remote_addr

    return "127.0.0.1"


limiter = Limiter(
    get_ip_address,
    storage_uri=CONSTS.redis_url,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)
