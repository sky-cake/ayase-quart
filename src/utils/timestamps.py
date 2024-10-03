from datetime import datetime

'''
Timestamps in asagi are always stored as u32 unix timestamps in the db.
Timestamps in asagi are not timezones aware.
'''

now_fmt = '%m/%d/%y (%a) %H:%M:%S'  # '10/29/15 (Thu) 22:33:37'
iso_fmt = '%Y-%m-%d %H:%M:%S', # '2024-09-18 14:30:00'
formats = (
    now_fmt,
    iso_fmt,
)

def ts_2_formatted(ts: int) -> str:
    """Format: 10/29/15 (Thu) 22:33:37"""
    return datetime.fromtimestamp(ts).strftime(now_fmt)


def formatted_2_ts(datetime_str: str) -> int:
    for fmt in formats:
        try:
            return int(datetime.strptime(datetime_str, fmt).timestamp())
        except ValueError:
            pass
    raise ValueError(f"Date format not recognized for: {datetime_str}")