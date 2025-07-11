from quart import Response
from pathlib import Path
from io import BytesIO
import mimetypes
import aiofiles


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
