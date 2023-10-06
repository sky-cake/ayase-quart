from pydantic import BaseModel
from typing import List, Optional

class Board(BaseModel):
    shortname: str
    name: str

class Skins(BaseModel):
    slug: str
    name: str

class Schema(BaseModel):
    name: str = "asagi"

class ImageLocation(BaseModel):
    image: str = "/img/{board_name}/image"
    thumb: str = "/img/{board_name}/thumb"

class MySQL(BaseModel):
    host: str
    port: int
    db: str
    user: str
    password: str
    charset: str

class Post(BaseModel):
    no: int = 4042624
    closed: int = 0
    now: str = "02/11/22(Fri)06:01:47"
    name: str = "Anonymous"
    sticky: int = 0
    sub: str = "Lain Thread Layer 124: Powered by CoplandOS"
    w: Optional[int] = 500
    h: Optional[int] = 357
    tn_w: Optional[int] = 250
    tn_h: Optional[int] = 178
    time: int = 1644577307
    asagi_preview_filename: Optional[str] = "1644595307853s.jpg"
    asagi_filename: Optional[str] = "1644595307853.png"
    tim: str = "1644595307853"
    md5: Optional[str] = "dfYGkvF04lbrH2SrZCIiLw=="
    fsize: Optional[int] = 170614
    filename: Optional[str] = "1384669273"
    ext: Optional[str] = "png"
    resto: int = 0
    capcode: Optional[str] = None
    trip: Optional[str] = None
    spoiler: int = 0
    country: Optional[str] = None
    filedeleted: int = 0
    exif: str = "{\"uniqueIps\":\"30\"}"
    com: Optional[str] = "Old Thread:\n>>4027469"
    replies: Optional[int] = 96
    images: Optional[int] = 95

class CatalogResponse(BaseModel):
    page: int
    threads: List[Post]

class ThreadResponse(BaseModel):
    posts: List[Post]

class BoardIndexResponse(BaseModel):
    threads: List[ThreadResponse]