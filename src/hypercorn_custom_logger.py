from hypercorn.logging import Logger
class CustomLogger(Logger):
    async def access(self, request, response, request_time):
        if request and not request.get('path', '').startswith('/srv'):
            await super().access(request, response, request_time)
