import base64
from io import BytesIO
from random import random
from functools import lru_cache

from PIL import Image, ImageColor, ImageDraw, ImageFont


class MathCaptcha:
    """`tff_file_path` - Path to a .tff file containing the font you want to use."""

    def __init__(
        self,
        tff_file_path=None,
        size=(50, 25),
        font_size=25,
        font_color=ImageColor.getcolor("white", "RGB"),
        background_color=ImageColor.getcolor("black", "RGB"),
    ):
        self.size = size
        self.font = ImageFont.truetype(tff_file_path, font_size)
        self.font_color = font_color
        self.background_color = background_color

        self.delimiter = "+-*/"

    def is_valid(self, captcha_id, answer):
        if not captcha_id or not answer:
            return False
        try:
            decoded = base64.b64decode(captcha_id).decode()
            first, second = decoded.split(self.delimiter)
            first, second, answer = int(first), int(second), int(answer)
            return first + second == answer
        except Exception:
            return False

    @lru_cache
    @staticmethod
    def generate_image(text, size, background_color, font_color, font):
        img = Image.new("RGB", size, background_color)
        draw = ImageDraw.Draw(img)
        xy = (5, 0)
        draw.text(xy, text, font_color, font=font)

        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str

    @staticmethod
    def generate_random():
        """Returns a random int between 0 and 10 (inclusive)."""
        return int(random() * 10)

    def generate_captcha(self):
        first_num = MathCaptcha.generate_random()
        second_num = MathCaptcha.generate_random()

        captcha_id = base64.b64encode(f"{first_num}{self.delimiter}{second_num}".encode()).decode()
        text = f"{first_num} + {second_num}"
        captcha_b64_img_str = MathCaptcha.generate_image(text, self.size, self.background_color, self.font_color, self.font)

        return captcha_id, captcha_b64_img_str
