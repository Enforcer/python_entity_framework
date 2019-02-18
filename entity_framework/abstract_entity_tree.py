import abc
import inspect
import typing
from collections import deque

import attr

from entity_framework.entity import Entity, Identity, ValueObject, EntityOrVo


# @attr.s(auto_attribs=True)
# class AbstractEntityTree:
#     fields: typing.Dict[str, typing.Type] = attr.Factory(dict)
#     identity: typing.List[str] = attr.Factory(list)
#     nullables: typing.List[str] = attr.Factory(list)
#     nested_lists: typing.Dict[str, typing.Type] = attr.Factory(dict)
#
#
# def build(root: Entity) -> AbstractEntityTree:
#     aet = AbstractEntityTree()
#     nesteds: typing.Deque[typing.Tuple[attr.Attribute, str]] = deque()
#
#     def parse_fields(current_root: EntityOrVo, prefix: str = "", force_nullable=False) -> None:
#         for field in attr.fields(current_root):
#             field_type = field.type
#             field_name = f"{prefix}{field.name}"
#
#             if _is_nested_entity_or_vo(field):
#                 nesteds.append((field, f"{field_name}_"))
#                 continue
#
#             if _is_generic(field):
#                 if Identity.is_identity(field):
#                     field_type = _get_wrapped_type(field)
#                     if not prefix:
#                         aet.identity.append(field_name)
#                 elif _is_field_nullable(field):
#                     field_type = _get_wrapped_type(field)
#                     aet.nullables.append(field_name)
#                 elif _is_list_of_entities_or_vos(field):
#                     aet.nested_lists[field_name] = _get_wrapped_type(field)
#                     continue
#                 else:
#                     raise Exception(f"Unhandled generic type - {field_type}")
#
#             if force_nullable and not field_name in aet.nullables:
#                 aet.nullables.append(field_name)
#
#             aet.fields[field_name] = field_type
#
#     parse_fields(root)
#
#     while nesteds:
#         field, prefix = nesteds.popleft()
#         field_type = field.type
#         force_nullable = False
#         if _is_nullable_nested_entity_or_vo(field):
#             field_type = _get_wrapped_type(field)
#             force_nullable = True
#         parse_fields(field_type, prefix, force_nullable)
#
#     return aet
#
#
# def _is_generic(field: attr.Attribute) -> bool:
#     return hasattr(field.type, "__origin__")
#
#
# def _get_wrapped_type(field: attr.Attribute) -> typing.Type:
#     return field.type.__args__[0]
#
#
# def _is_field_nullable(field: attr.Attribute) -> bool:
#     return field.type.__origin__ == typing.Union and isinstance(None, field.type.__args__[1])
#
#
# def _is_nested_entity_or_vo(field: attr.Attribute) -> bool:
#     return issubclass(field.type, (Entity, ValueObject)) or _is_nullable_nested_entity_or_vo(field)
#
#
# def _is_nullable_nested_entity_or_vo(field: attr.Attribute) -> bool:
#     if _is_generic(field) and _is_field_nullable(field):
#         return issubclass(_get_wrapped_type(field), (Entity, ValueObject))
#     return False
#
#
# def _is_list_of_entities_or_vos(field: attr.Attribute) -> bool:
#     return field.type.__origin__ == typing.List and issubclass(_get_wrapped_type(field), (Entity, ValueObject))


class Visitor:

    def visit_field(self, field: 'Field') -> None:
        pass

    def leave_field(self, field: 'Field') -> None:
        pass

    def visit_nested_entity(self, nested_entity: 'NestedEntity') -> None:
        pass

    def leave_nested_entity(self, nested_entity: 'NestedEntity') -> None:
        pass

    def visit_nested_value_object(self, nested_entity: 'NestedValueObject') -> None:
        pass

    def leave_nested_value_object(self, nested_entity: 'NestedValueObject') -> None:
        pass

    def visit_list_of_entities(self, list_of_entities: 'ListOfEntities') -> None:
        pass

    def leave_list_of_entities(self, list_of_entities: 'ListOfEntities') -> None:
        pass

    def visit_list_of_value_objects(self, list_of_entities: 'ListOfValueObjects') -> None:
        pass

    def leave_list_of_value_objects(self, list_of_entities: 'ListOfValueObjects') -> None:
        pass


class NodeMeta(type):
    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> typing.Type:
        cls = super().__new__(mcs, name, bases, namespace)
        if inspect.isabstract(cls):
            return cls
        return attr.s(auto_attribs=True)(cls)


class Node(metaclass=NodeMeta):
    type: typing.Type
    nullable: bool
    children: typing.List['Node']

    @abc.abstractmethod
    def accept(self, visitor: Visitor) -> None:
        pass

    @abc.abstractmethod
    def farewell(self, visitor: Visitor) -> None:
        pass


class Field(Node):
    is_identity: bool

    def accept(self, visitor: Visitor) -> None:
        visitor.visit_field(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_field(self)


class NestedEntity(Node):

    def accept(self, visitor: Visitor) -> None:
        visitor.visit_nested_entity(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_nested_entity(self)


class NestedValueObject(Node):

    def accept(self, visitor: Visitor) -> None:
        visitor.visit_nested_value_object(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_nested_value_object(self)


class ListOfEntities(Node):

    def accept(self, visitor: Visitor) -> None:
        visitor.visit_list_of_entities(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_list_of_entities(self)


class ListOfValueObjects(Node):

    def accept(self, visitor: Visitor) -> None:
        visitor.visit_list_of_value_objects(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_list_of_value_objects(self)


@attr.s(auto_attribs=True)
class AbstractEntityTree:
    root: Node

