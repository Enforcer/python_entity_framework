import typing

from entity_framework.abstract_entity_tree import (
    Visitor,
    FieldNode,
    EntityNode,
    ValueObjectNode,
    ListOfEntitiesNode,
    ListOfValueObjectsNode,
)


class PopulatingAggregateVisitor(Visitor):
    EMPTY_PREFIX = ""

    def __init__(self, db_result: object) -> None:
        self._db_result = db_result
        self._prefix = self.EMPTY_PREFIX
        self._entities_stack: typing.List[EntityNode] = []
        self._ef_objects_stack: typing.List[typing.Union[EntityNode, ValueObjectNode]] = []
        self._ef_dicts_stack: typing.List[dict] = []
        self._result: typing.Any = None

    @property
    def result(self) -> typing.Any:
        return self._result

    def visit_field(self, field: FieldNode) -> None:
        if isinstance(self._ef_objects_stack[-1], EntityNode):
            field_name = field.name
        else:
            field_name = f"{self._prefix}{field.name}"

        db_object = self._db_result
        for index, entity in enumerate(self._entities_stack[:-1]):
            next_entity = self._entities_stack[index + 1]
            db_object = getattr(db_object, next_entity.name)

        self._ef_dicts_stack[-1][field.name] = getattr(db_object, field_name)

    def visit_entity(self, entity: EntityNode) -> None:
        self._entities_stack.append(entity)
        self._stack_complex_object(entity)

    def leave_entity(self, entity: EntityNode) -> None:
        self._entities_stack.pop()
        self._construct_complex_object(entity)

    def visit_value_object(self, value_object: ValueObjectNode) -> None:
        self._prefix = f"{value_object.name}_"
        self._stack_complex_object(value_object)

    def leave_value_object(self, value_object: ValueObjectNode) -> None:
        self._prefix = self.EMPTY_PREFIX
        self._construct_complex_object(value_object)

    def _stack_complex_object(self, vo_or_entity: typing.Union[ValueObjectNode, EntityNode]) -> None:
        self._ef_objects_stack.append(vo_or_entity)
        self._ef_dicts_stack.append({})

    def _construct_complex_object(self, vo_or_entity: typing.Union[ValueObjectNode, EntityNode]) -> None:
        self._ef_objects_stack.pop()
        entity_dict = self._ef_dicts_stack.pop()
        if vo_or_entity.optional and entity_dict and all(v is None for v in entity_dict.values()):
            # One is not able to tell the difference between optional object with all its fields = None or
            # an absence of entire vo_or_entity
            instance = None
        else:
            instance = vo_or_entity.type(**entity_dict)
        if self._ef_dicts_stack:
            self._ef_dicts_stack[-1][vo_or_entity.name] = instance
        else:
            self._result = instance

    def visit_list_of_entities(self, list_of_entities: ListOfEntitiesNode) -> None:
        raise NotImplementedError

    def leave_list_of_entities(self, list_of_entities: ListOfEntitiesNode) -> None:
        raise NotImplementedError

    def visit_list_of_value_objects(self, list_of_value_objects: ListOfValueObjectsNode) -> None:
        raise NotImplementedError

    def leave_list_of_value_objects(self, list_of_value_objects: ListOfValueObjectsNode) -> None:
        raise NotImplementedError
