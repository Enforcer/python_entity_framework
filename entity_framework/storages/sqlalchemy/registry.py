from typing import Dict, Type

import attr
from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.entity import Entity
from entity_framework.registry import Registry


@attr.s(auto_attribs=True)
class SaRegistry(Registry):
    # TODO: Think of refactoring, so that this does not have semantics of a global variable
    entities_models: Dict[Type[Entity], Type[DeclarativeMeta]] = attr.Factory(dict)
