from datetime import datetime, timedelta, timezone
from typing import Tuple

def day_window_ms_for_local_date(tz_offset_min: int, y: int, m: int, d: int) -> Tuple[int, int]:
    tz = timezone(timedelta(minutes=tz_offset_min))
    start = datetime(y, m, d, 0, 0, 0, 0, tzinfo=tz)
    end   = datetime(y, m, d, 23, 59, 59, 999000, tzinfo=tz)
    return int(start.timestamp()*1000), int(end.timestamp()*1000)