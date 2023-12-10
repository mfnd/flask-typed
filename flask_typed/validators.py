from datetime import datetime, date, time


def date_validator(value: str) -> date:
    return datetime.fromisoformat(value).date()


def datetime_validator(value: str) -> datetime:
    return datetime.fromisoformat(value)


def time_validator(value: str) -> time:
    return datetime.fromisoformat(value).time()


VALIDATORS = {
    datetime: datetime_validator,
    date: date_validator,
    time: time_validator,
}


