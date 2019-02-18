import typing
import uuid
from functools import singledispatch

import attr

from entity_framework.entity import Identity
from entity_framework.abstract_entity_tree import _is_generic, _get_wrapped_type


@singledispatch
def to_storage(argument: typing.Any) -> typing.Any:
    return argument


@to_storage.register(uuid.UUID)
def _(argument: uuid.UUID) -> str:
    return str(argument)


mapping = {uuid.UUID: uuid.UUID}


def from_storage(argument: typing.Any, field: attr.Attribute) -> typing.Any:
    field_type = field.type
    if _is_generic(field):
        if Identity.is_identity(field):
            field_type = _get_wrapped_type(field)
        else:
            raise Exception("Unhandled branch")

    try:
        return mapping[field_type](argument)
    except KeyError:
        return argument
