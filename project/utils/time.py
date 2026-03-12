from __future__ import annotations

from datetime import datetime

from dateutil import parser


def parse_datetime(value: str) -> datetime:
    dt = parser.parse(value)
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt
