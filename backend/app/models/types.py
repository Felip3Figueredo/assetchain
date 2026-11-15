from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class WeiInt(TypeDecorator):
    """Stores arbitrarily large ints (wei amounts) as decimal strings; exact on every DB."""

    impl = String(80)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(int(value))

    def process_result_value(self, value, dialect):
        return None if value is None else int(value)
