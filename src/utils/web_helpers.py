from quart import Response, Quart
from pathlib import Path
from io import BytesIO
import mimetypes
import aiofiles
from datetime import datetime
from werkzeug.exceptions import NotFound
from werkzeug.utils import safe_join


ATTACHMENT_FILENAME: str = 'ayase_quart'


async def send_bytesio_no_headers(
    buffer: BytesIO,
    mimetype: str | None = None,
    as_attachment: bool = False,
    attachment_filename: str | None = None,
) -> Response:
    data = buffer.getvalue()
    content_length = len(data)
    if not mimetype:
        mimetype = 'application/octet-stream'

    response = Response(data, mimetype=mimetype)
    response.content_length = content_length

    if as_attachment:
        if not attachment_filename:
            attachment_filename = ATTACHMENT_FILENAME
        response.headers['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'

    return response


async def send_file_no_headers(
    filename: str,
    mimetype: str | None = None,
    as_attachment: bool = False,
    attachment_filename: str | None = None,
) -> Response:

    file_path = Path(filename)
    async with aiofiles.open(file_path, mode='rb') as f:
        data = await f.read()
    content_length = len(data)

    if not mimetype:
        mimetype = mimetypes.guess_type(file_path.name)[0] or 'application/octet-stream'

    response = Response(data, mimetype=mimetype)
    response.content_length = content_length

    if as_attachment:
        if not attachment_filename:
            attachment_filename = file_path.name or ATTACHMENT_FILENAME

        response.headers['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'

    return response


async def send_file_from_directory_no_headers(
    directory: str,
    file_name: str,
    mimetype: str | None = None,
    as_attachment: bool = False,
    attachment_filename: str | None = None,
) -> Response:
    
    raw_file_path = safe_join(str(directory), file_name)
    if raw_file_path is None:
        raise NotFound()

    file_path = Path(raw_file_path)

    if not file_path.is_file():
        raise NotFound()

    return await send_file_no_headers(
        file_path,
        mimetype=mimetype,
        as_attachment=as_attachment,
        attachment_filename=attachment_filename,
    )


class Quart2(Quart):
    async def send_static_file(self, filename: str) -> Response:
        """Ovverriding this method is necessary because we don't want to set Cache-Control headers via methods that use
        `quart.helpers.send_file()`. Cache-Control headers should be set per-endpoint via NGINX. Setting these headers
        per endpoint here is less desirable.
        """
        if not self.has_static_folder:
            raise RuntimeError("No static folder for this object")
        return await send_file_from_directory_no_headers(self.static_folder, filename)
