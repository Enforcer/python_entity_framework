from typing import Optional, List, DefaultDict, Set, Type
from collections import defaultdict

from sqlalchemy.orm import Query, joinedload

from entity_framework.abstract_entity_tree import Visitor, EntityNode
from entity_framework.storages.sqlalchemy.registry import Registry


class QueryBuildingVisitor(Visitor):
    def __init__(self) -> None:
        self._root_model: Optional[Type] = None
        self._models_stack: List[Type] = []
        self._models_to_join: DefaultDict[Type, List[str]] = defaultdict(list)
        self._all_models: Set[Type] = set()
        self._query: Optional[Query] = None

    @property
    def query(self) -> Query:
        if not self._root_model:
            raise Exception("No root model")

        # TODO: support more nesting levels than just one
        return Query(self._root_model).options(
            joinedload(getattr(self._root_model, rel_name)) for rel_name in self._models_to_join[self._root_model]
        )

    def visit_entity(self, entity: EntityNode) -> None:
        # TODO: decide what to do with fields used magically, like entity.name which is really just a node name
        model = Registry.entities_models[entity.type]
        if not self._root_model:
            self._root_model = model
        elif self._models_stack:
            self._models_to_join[self._models_stack[-1]].append(entity.name)

        self._models_stack.append(model)
        self._all_models.add(model)

    def leave_entity(self, entity: EntityNode) -> None:
        self._models_stack.pop()
