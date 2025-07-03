from hypercorn.logging import Logger


ignore_path_startswith = '/srv' # can also use a tuple[str] like ('/srv', '/static/css', ...)


class CustomLogger(Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ignore_path_startswith = ignore_path_startswith

        if self.ignore_path_startswith:
            assert isinstance(self.ignore_path_startswith, str) or isinstance(self.ignore_path_startswith, tuple)

    async def access(self, request, response, request_time: float):
        if request and (request_path := request.get('path')):
            if not self.ignore_path_startswith:
                # log everything
                await super().access(request, response, request_time)
                return

            if not request_path.startswith(self.ignore_path_startswith):
                # avoid logging specific url paths like /srv/media, /static/css, etc
                await super().access(request, response, request_time)
                return
