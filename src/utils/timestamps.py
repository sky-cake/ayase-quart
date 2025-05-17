from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

'''
Timestamps in asagi are always stored as u32 unix timestamps in the db.
Timestamps in asagi are not timezones aware.
'''

# now_fmt = '%m/%d/%y (%a) %H:%M:%S'  # '10/29/15 (Thu) 22:33:37'
now_fmt = '%b %d, %Y (%a) %I:%M %p'  # Oct 29, 2015 (Thu) 10:33:37 PM

iso_fmt = '%Y-%m-%d %H:%M:%S', # '2024-09-18 14:30:00'
formats = (
    now_fmt,
    iso_fmt,
)

# def ts_2_formatted(ts: int) -> str:
#     return datetime.fromtimestamp(ts).strftime(now_fmt)


def ts_2_formatted(ts: int):
    ts = datetime.fromtimestamp(ts, tz=timezone.utc)
    now = datetime.now(tz=timezone.utc)
    delta = relativedelta(now, ts)
    post_dt = ts.strftime(now_fmt)

    time_units = [
        (delta.years, "year"),
        (delta.months, "month"),
        (delta.days, "day"),
        (delta.hours, "hour"),
        (delta.minutes, "min"),
        (delta.seconds, "sec"),
    ]

    for value, unit in time_units:
        if value > 0:
            return f"{post_dt} UTC ({value} {unit}{'s' if value > 1 else ''} ago)"

    return f"{post_dt} (now)"


def formatted_2_ts(datetime_str: str) -> int:
    for fmt in formats:
        try:
            return int(datetime.strptime(datetime_str, fmt).timestamp())
        except ValueError:
            pass
    raise ValueError(f"Date format not recognized for: {datetime_str}")
