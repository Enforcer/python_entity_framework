from typing import Dict, Type

from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.entity import Entity


class Registry:
    # TODO: Think of refactoring, so that this does not have semantics of a global variable
    entities_models: Dict[Type[Entity], Type[DeclarativeMeta]] = {}
