import abc
import inspect
import typing
from collections import deque

import attr
import inflection

from entity_framework.entity import Entity, Identity, ValueObject, EntityOrVo, EntityOrVoType


def _is_generic(field_type: typing.Type) -> bool:
    return hasattr(field_type, "__origin__")


def _get_wrapped_type(wrapped_type: typing.Optional) -> typing.Type:
    return wrapped_type.__args__[0]


def _is_field_nullable(field_type: typing.Type) -> bool:
    return field_type.__origin__ == typing.Union and isinstance(None, field_type.__args__[1])


def _is_nested_entity_or_vo(field_type: typing.Type) -> bool:
    return issubclass(field_type, (Entity, ValueObject)) or _is_nullable_entity_or_vo(field_type)


def _is_nullable_entity_or_vo(field_type: typing.Type) -> bool:
    if _is_generic(field_type) and _is_field_nullable(field_type):
        return issubclass(_get_wrapped_type(field_type), (Entity, ValueObject))
    return False


def _is_identity(field_type: typing.Type) -> bool:
    return getattr(field_type, "__origin__", None) == Identity


def _is_list_of_entities_or_vos(field_type: typing.Type) -> bool:
    return (
        _is_generic(field_type)
        and field_type.__origin__ == typing.List
        and issubclass(_get_wrapped_type(field_type), (Entity, ValueObject))
    )


class Visitor:
    def traverse_from(self, node: "Node") -> None:
        node.accept(self)
        for child in node.children:
            self.traverse_from(child)
        node.farewell(self)

    def visit_field(self, field: "Field") -> None:
        pass

    def leave_field(self, field: "Field") -> None:
        pass

    def visit_entity(self, entity: "EntityNode") -> None:
        pass

    def leave_entity(self, entity: "EntityNode") -> None:
        pass

    def visit_value_object(self, value_object: "ValueObjectNode") -> None:
        pass

    def leave_value_object(self, value_object: "ValueObjectNode") -> None:
        pass

    def visit_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        pass

    def leave_list_of_entities(self, list_of_entities: "ListOfEntitiesNode") -> None:
        pass

    def visit_list_of_value_objects(self, list_of_value_objects: "ListOfValueObjectsNode") -> None:
        pass

    def leave_list_of_value_objects(self, list_of_value_objects: "ListOfValueObjectsNode") -> None:
        pass


class NodeMeta(type):
    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> typing.Type:
        cls = super().__new__(mcs, name, bases, namespace)
        if inspect.isabstract(cls):
            return cls
        return attr.s(auto_attribs=True)(cls)


class Node(metaclass=NodeMeta):
    name: str
    type: typing.Type
    nullable: bool = False
    children: typing.List["Node"] = attr.Factory(list)

    @abc.abstractmethod
    def accept(self, visitor: Visitor) -> None:
        pass

    @abc.abstractmethod
    def farewell(self, visitor: Visitor) -> None:
        pass


class FieldNode(Node):
    is_identity: bool = False

    def accept(self, visitor: Visitor) -> None:
        visitor.visit_field(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_field(self)


class EntityNode(Node):
    def accept(self, visitor: Visitor) -> None:
        visitor.visit_entity(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_entity(self)


class ValueObjectNode(Node):
    def accept(self, visitor: Visitor) -> None:
        visitor.visit_value_object(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_value_object(self)


class ListOfEntitiesNode(Node):
    def accept(self, visitor: Visitor) -> None:
        visitor.visit_list_of_entities(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_list_of_entities(self)


class ListOfValueObjectsNode(Node):
    def accept(self, visitor: Visitor) -> None:
        visitor.visit_list_of_value_objects(self)

    def farewell(self, visitor: Visitor) -> None:
        visitor.leave_list_of_value_objects(self)


@attr.s(auto_attribs=True)
class AbstractEntityTree:
    root: EntityNode

    def __iter__(self) -> typing.Generator[Node, None, None]:
        def iterate_dfs() -> typing.Generator[Node, None, None]:
            nodes_left: typing.Deque[Node] = deque([self.root])

            while nodes_left:
                current = nodes_left.pop()
                yield current
                nodes_left.extend(current.children[::-1])

        return iterate_dfs()


def build(root: typing.Type[Entity]) -> AbstractEntityTree:
    def parse_node(current_root: EntityOrVoType, name: str) -> Node:
        node_name = name
        is_list = False
        if _is_list_of_entities_or_vos(current_root):
            node_nullable = False
            node_type = _get_wrapped_type(current_root)
            is_list = True
        elif _is_nullable_entity_or_vo(current_root):
            node_nullable = True
            node_type = _get_wrapped_type(current_root)
        else:
            node_nullable = False
            node_type = current_root
        node_children = []

        for field in attr.fields(node_type):
            field_type = field.type
            field_name = field.name

            if _is_nested_entity_or_vo(field_type) or _is_list_of_entities_or_vos(field_type):
                node_children.append(parse_node(field_type, field_name))
                continue

            field_nullable = False
            is_identity = False

            if _is_generic(field.type):
                if _is_identity(field_type):
                    field_type = _get_wrapped_type(field.type)
                    is_identity = True
                elif _is_field_nullable(field.type):
                    field_type = _get_wrapped_type(field.type)
                    field_nullable = True
                else:
                    raise Exception(f"Unhandled Generic type - {field_type}")

            node_children.append(FieldNode(field_name, field_type, field_nullable, [], is_identity))

        if issubclass(node_type, Entity):
            if is_list:
                return ListOfEntitiesNode(node_name, node_type, node_nullable, node_children)
            return EntityNode(node_name, node_type, node_nullable, node_children)

        if is_list:
            return ListOfValueObjectsNode(node_name, node_type, node_nullable, node_children)
        return ValueObjectNode(node_name, node_type, node_nullable, node_children)

    root_node = parse_node(root, inflection.underscore(root.__name__))
    return AbstractEntityTree(root_node)
