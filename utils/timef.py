from datetime import datetime, timezone, timedelta


def time_cst():
    cst = (datetime.now(timezone(timedelta(seconds=-18000))))
    timestamp = cst.strftime("(%H:%M:%S) ")
    return timestamp


def time_index():
    current_time = datetime.utcnow()
    return current_time


def time_offset(offset_amount):
    offset = timedelta(seconds=offset_amount)
    return offset
