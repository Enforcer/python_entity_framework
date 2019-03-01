from typing import Dict, Tuple, Type

import attr
from sqlalchemy import Column
from sqlalchemy.orm import relationship


@attr.s(auto_attribs=True)
class RawModel:
    name: str
    bases: Tuple[Type, ...]
    namespace: Dict

    def append_column(self, name: str, column: Column) -> None:
        self.namespace[name] = column

    def append_relationship(self, name: str, related_model_name: str, nullable: bool) -> None:
        self.namespace[name] = relationship(related_model_name, innerjoin=not nullable)

    def materialize(self) -> Type:
        return type(self.name, self.bases, self.namespace)
