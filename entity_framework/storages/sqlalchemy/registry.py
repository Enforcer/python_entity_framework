from typing import Dict, Type

from sqlalchemy.ext.declarative import DeclarativeMeta

from entity_framework.entity import Entity


class Registry:
    entities_models: Dict[Type[Entity], Type[DeclarativeMeta]] = {}
