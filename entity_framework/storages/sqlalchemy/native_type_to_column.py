import uuid
import typing
from datetime import datetime

from sqlalchemy import Integer, String, Float, DateTime
from sqlalchemy.dialects import postgresql as postgresql_dialect


# TODO: Support other dialects, not only PostgreSQL
mapping = {int: Integer, str: String(255), uuid.UUID: postgresql_dialect.UUID, float: Float, datetime: DateTime}


def convert(arg: typing.Type) -> typing.Any:
    try:
        return mapping[arg]
    except KeyError:
        raise TypeError(f"Unsupported type - {arg}")
