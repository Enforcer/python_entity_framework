from typing import Dict, Type

import attr

from entity_framework.abstract_entity_tree import AbstractEntityTree
from entity_framework.entity import Entity


@attr.s(auto_attribs=True)
class Registry:
    entities_to_aets: Dict[Type[Entity], AbstractEntityTree] = attr.Factory(dict)
